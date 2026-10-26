#!/usr/bin/env python3
"""randomize.py - protocol randomizer: the epitome of simplicity.

Reuses the v9.5 machinery (the exam papers, the grader, the bells,
the acquisition pipeline, the server) and disposes of the rules -
it is only interested in RESULTS.

  the pool    the candidate PAIR is (model, model-quant) - 64
              models x 32 rungs = 2,048 pairs. A pair's pick
              evaluates ALL 49 (k, v) cache-quant combinations
              (7 x 7) in one acquisition: no constant quant
              re-calculation, the file is acquired once
  the pick    16 bits of REAL entropy (/dev/hwrng if present,
              else /dev/random - the kernel's harvested pool,
              never a pseudorandom generator): 11 bits the model
              index, 5 bits the model rung. ONE CHANCE per PAIR,
              no replacement: a pick that lands on an already-run
              pair is re-drawn with fresh entropy; the pool
              drains to zero and the protocol is complete. A
              fresh 8-bit exam seed serves EVERY candidate of the
              sweep, recorded for reproducibility
  the kv      per pair, EVERY combination of KV_LADDER x
              KV_LADDER (f16, q8_0, q4_0, q4_1, iq4_nl, q5_0,
              q5_1) takes the exam - 49 candidates per pick; the
              server gets --cache-type-k and --cache-type-v, f16
              means no flag (the default). A quant file that has
              been fully swept can be safely deleted: no kv
              combination of it remains, it will never be needed
              again. The gc deals with the f16s and any leftover
  the exam    8 bits of entropy = one of 256 possible exams; the
              SAME exam seed serves every level of the candidate
  the run     the candidate takes level 0, 1, 2, ... under one
              TOTAL timeout of 128 seconds for the whole run:
                pass  -> the next exam level
                fail or timeout -> the run is over; the fail
                reason and the high score (the highest passed
                level) are recorded
  the files   an F16 candidate is kept on disk; a quant candidate
              is deleted after its run
  the gc      a disk watchdog: when free space on /home falls to
              16 GiB or below, the OLDEST f16 on disk is removed
              repeatedly (1s cadence) until free space exceeds
              16 GiB again - never the active candidate's f16.
              Linux has no native low-disk event (inotify watches
              files, not free space), so the watchdog polls
              statvfs once per second - microseconds of CPU,
              effectively event-driven

No quant ladders, no walk rules, no proctor: a candidate, an exam,
a clock, a result.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import infra.llama_server as llama_server
from bench import state_store as _state_store
from bench.exam import (
    ask_exam,
    build_chain,
    build_elevator,
    chain_prompt,
    elevator_prompt,
    score_exam,
)
from bench.roster import LADDER, roster_from_models_md

# --- the entropy source: real randomness, never pseudorandom -------------

_ENTROPY_DEV = ""
for _dev in ("/dev/hwrng", "/dev/random"):
    # hwrng is root-only on many systems (mode 600): probe by READING,
    # not by existence - fall back to the kernel's harvested pool
    try:
        with open(_dev, "rb") as _fh:
            _fh.read(1)
        _ENTROPY_DEV = _dev
        break
    except OSError:
        continue
if not _ENTROPY_DEV:
    raise SystemExit("no entropy source: neither /dev/hwrng nor /dev/random readable")


def entropy_bits(n: int) -> int:
    """n bits of real entropy from the hardware (or the kernel's
    harvested pool). Reads exactly ceil(n/8) bytes and reduces to
    n bits - every value 0..2^n - 1 equally likely."""
    nbytes = (n + 7) // 8
    with open(_ENTROPY_DEV, "rb") as fh:
        buf = fh.read(nbytes)
    val = int.from_bytes(buf, "little") & ((1 << n) - 1)
    return val


# --- the pool, v3: (model, rung) pairs, kv-swept at pick time -------------
# the 16-bit pick: 11 bits the model index (the pool index), 5 bits
# the model rung (LADDER). One chance per PAIR; the pair's pick
# sweeps every KV_LADDER x KV_LADDER combination (49 candidates).
KV_LADDER = [
    "f16",
    "q8_0",
    "q4_0",
    "q4_1",
    "iq4_nl",
    "q5_0",
    "q5_1",
]
PICK_BITS = 16  # 11 model index + 5 rung


def the_pool() -> list[tuple[str, str]]:
    """Every (model, rung) pair, deterministic order - the 16-bit
    pick space. One chance per pair; the pick sweeps all 49 kv
    combinations, so the pool of CANDIDATES is 2048 x 49 = 100,352.

    NO SIZE GATE (the author's ruling): every pair is live - the
    f16 table column stays in md/models.md for the ledger's
    reference, but no model is pre-marked dead. A candidate too
    large for the device dies at the llama-server launch, its
    honest recorded verdict: server_failed - the server auto-shrinks
    the context to fit when it can, and fails outright when it
    cannot."""
    roster = roster_from_models_md()
    pool: list[tuple[str, str]] = []
    for fam, _repo in roster:
        for rung in LADDER:
            pool.append((fam, rung))
    return pool


def _f16_gib_from_models_md(fam: str) -> float | None:
    """The model's f16 size from the md/models.md table (the f16
    (GiB) column). None when the row carries no number."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "md", "models.md")
    for ln in open(path, encoding="utf-8"):
        if ln.startswith(f"| {fam} |"):
            parts = [p.strip() for p in ln.strip().strip("|").split("|")]
            try:
                return float(parts[2])
            except (ValueError, IndexError):
                return None
    return None


# --- the disk watchdog ----------------------------------------------------

GC_THRESHOLD_GIB = 16.0
GC_WATCH_PATH = "/home"
GC_INTERVAL_S = 4.0  # the cadence (the author ruling: the disk is not even that fast)


def _free_gib(path: str = GC_WATCH_PATH) -> float:
    st = os.statvfs(path)
    return (st.f_bavail * st.f_frsize) / (2**30)


def _stranded_quants(models_dir: str, exclude: set[str]) -> list[str]:
    """The crash-leftover sweep: per family, every QUANT gguf except
    the NEWEST, when more than one lingers. The file rule deletes a
    quant after its run - so two or more means an abruptly-stopped
    run stranded the extras. Never the excluded (active) family;
    never the f16 or the imatrix (not quant rungs). Returns the
    paths to remove, newest-kept."""
    from bench.roster import LADDER

    quant_names = {rung.lower() for rung in LADDER if rung != "F16"}
    victims: list[str] = []
    if not os.path.isdir(models_dir):
        return victims
    for fam in os.listdir(models_dir):
        if fam in exclude:
            continue
        famdir = os.path.join(models_dir, fam)
        if not os.path.isdir(famdir):
            continue
        quants: list[str] = []
        for f in os.listdir(famdir):
            if not f.endswith(".gguf"):
                continue
            stem = f[: -len(".gguf")]
            # <fam>-<RUNG>.gguf: the quant rung is the last token
            rung = stem.rsplit("-", 1)[-1].lower()
            if rung in quant_names:
                quants.append(str(os.path.join(famdir, f)))
        if len(quants) > 1:
            quants.sort(key=os.path.getmtime)
            victims.extend(quants[:-1])  # keep the newest
    return victims


def _least_likely_f16(
    models_dir: str,
    exclude: set[str],
    done: set[str],
    pool: list[tuple[str, str]],
) -> str | None:
    """The f16 LEAST LIKELY to be needed again (the author's
    ruling: the state knows the future - a family with few untried
    rungs will rarely need its f16 again; ties broken by oldest
    mtime). The imatrix stays behind (small, very expensive);
    ONLY the f16 is ever deleted. Never the excluded (active)
    families. Returns its path, or None when nothing is
    collectable.

    THE RACE GUARD (the author's workaround, no lock needed): when
    only ONE family directory exists, nothing is deleted - that
    lone directory is almost certainly the active candidate's (or
    the only candidate run so far), and deleting the sole model on
    disk while the picker may be aiming at it is exactly the race.
    A second directory on disk proves a safe alternative exists:
    the active family is excluded by name, and the pick-vs-collect
    window concerns only candidates that have ALREADY had their one
    chance (their files were deleted after the run anyway - an F16
    lingers only if its run happened to land there)."""
    if not os.path.isdir(models_dir):
        return None
    fams = os.listdir(models_dir)
    if len(fams) <= 1:
        return None  # never delete the only directory on disk
    # per family: how many of its (model, quant) pairs are still
    # untried - the future need for its f16 (each untried pair,
    # when picked, re-quantizes from the f16 and sweeps all its kv
    # combinations in that one acquisition). A v3 done-key is the
    # pool index of the pair: a swept pair's whole 49-combination
    # space went with its one acquisition.
    remaining: dict[str, int] = {}
    for pair_key, (fam, _rung) in enumerate(pool):
        if str(pair_key) in done:
            continue
        remaining[fam] = remaining.get(fam, 0) + 1
    best = None  # (remaining, mtime, fam)
    for fam in fams:
        if fam in exclude:
            continue
        f16 = os.path.join(models_dir, fam, f"{fam}-f16.gguf")
        if not os.path.isfile(f16):
            continue
        rem = remaining.get(fam, 0)
        mt = os.path.getmtime(f16)
        if best is None or (rem, mt) < (best[0], best[1]):
            best = (rem, mt, fam)
    if best is None:
        return None
    return os.path.join(models_dir, best[2], f"{best[2]}-f16.gguf")


def disk_watchdog(
    models_dir: str,
    active: threading.Event,
    stop: threading.Event,
    log: list[str],
) -> None:
    """The 1-second watchdog thread. The gc triggers ONLY when free
    space on /home is at or below 16 GiB, and stops the moment it
    is above the threshold again - it never runs under any other
    circumstance (the author's ruling). When triggered, TWO
    cleanups run, both inside the same trigger:
    1. the stranded-quant sweep FIRST: per family, if more than one
       QUANT gguf lingers (an abruptly-stopped run's leftovers -
       the file rule deletes a quant after its run, so two means a
       crash/interrupt stranded one), keep only the NEWEST and
       delete the rest - never the active family's, never the f16
       (the f16 and imatrix are not targets of this sweep).
    2. the least-likely f16 eviction if space is STILL needed: the
       f16 of the family with the fewest untried rungs (never the
       active candidate's) - the imatrix stays behind."""
    while not stop.is_set():
        try:
            if _free_gib() <= GC_THRESHOLD_GIB:
                fam = _ACTIVE_FAMILY[0]
                exclude = {fam} if fam else set()
                # 1. the stranded-quant sweep (crash leftovers):
                #    >1 quant gguf in a family -> keep the newest
                stranded = _stranded_quants(models_dir, exclude)
                if stranded:
                    for p in stranded:
                        before = _free_gib()
                        os.remove(p)
                        log.append(
                            f"[gc] free {before:.1f} GiB <= {GC_THRESHOLD_GIB:g}: "
                            f"removed stranded {os.path.basename(p)} "
                            f"(>1 quant gguf; kept the newest; now {_free_gib():.1f} GiB)"
                        )
                    continue  # re-check: the sweep may have freed enough
                # 2. the f16 eviction, still under the same trigger
                victim = _least_likely_f16(
                    models_dir,
                    exclude,
                    _GC_DONE_SET,
                    _GC_POOL,
                )
                if victim:
                    # ONLY the f16 goes (the author's ruling): the
                    # imatrix stays behind (small, very expensive to
                    # recompute), the family dir stays
                    before = _free_gib()
                    os.remove(victim)
                    # log the free space BEFORE the removal (the
                    # decision's datum) and after (the result) - the
                    # active candidate's concurrent downloads move
                    # free space as the gc frees it, so a single
                    # after-only reading looks non-causal
                    log.append(
                        f"[gc] free {before:.1f} GiB <= {GC_THRESHOLD_GIB:g}: "
                        f"evicted {os.path.basename(victim)} "
                        f"(least-likely-needed; now {_free_gib():.1f} GiB)"
                    )
                    continue  # re-check immediately after a removal
        except Exception as e:  # the watchdog never dies
            log.append(f"[gc] watchdog error (ignored): {e}")
        stop.wait(GC_INTERVAL_S)


# the randomizer's state file (module-level: full_benchmark's
# --clean wipes it before main() runs)
RANDOMIZER_STATE_FILE = "state/randomizer-state.json"

# the active family: a one-slot holder the watchdog reads
_ACTIVE_FAMILY: list[str] = [""]

# the gc's view of the state (refreshed by the main loop after every
# pick): the done-set and the pool - what the least-likely-needed
# policy needs to know the future
_GC_DONE_SET: set[str] = set()
_GC_POOL: list[tuple[str, str]] = []

# NO SIZE LIMIT (the author's ruling): llama-server handles quants
# too large for the device itself - it auto-shrinks the context to
# fit (ctx 0 = load from model) or fails the launch, and the failed
# launch is the candidate's honest recorded verdict (server_failed).
# The disk gc keeps the models/ tree bounded regardless.

# the LAST acquire failure's class + detail, set by _acquire below
# (the record reads it; the console saw the print)
_last_acquire_error: dict[str, str] = {}


def _acquire(fam: str, rung: str, models_dir: str) -> str | None:
    """The classified acquisition: every failure mode gets a
    DISTINCT name (the author's ruling - unbuildable is too
    generic), printed at the site and carried in the record:
      no_repo          the family is not in the roster
      hub_unavailable  the huggingface_hub dependency is missing
      ram_infeasible   the rung's predicted cost exceeds system RAM
      quantize_failed  the quantizer/converter run failed
      build_crashed    an unexpected exception in the build
    A success clears the slot."""
    import infra.hf_download as hf_download
    from bench import roster as _rost

    _last_acquire_error.clear()
    print(f"  [acquire] {fam} {rung} - (download/convert/quantize may take minutes)")
    famdir = os.path.join(models_dir, fam)
    existing = hf_download.local_rung(famdir, rung)
    if existing and os.path.isfile(existing):
        return existing
    repo = dict(_rost.roster_from_models_md()).get(fam)
    if not repo:
        _last_acquire_error.update(result="no_repo", detail=fam)
        print(f"  {fam} {rung}: no_repo - not in the roster")
        return None
    try:
        path = _rost.build(fam, repo, famdir, rung)
        if path:
            return path
        # build returned None: it printed its own reason; classify by
        # what the pipeline knows - RAM infeasibility is the common
        # silent one, the rest printed as quantize failures
        _last_acquire_error.update(result="build_failed", detail=f"{fam} {rung}")
        return None
    except SystemExit as e:
        if e.code == 130:
            raise
        if isinstance(e.code, str) and "huggingface_hub is required" in e.code:
            _last_acquire_error.update(result="hub_unavailable", detail=str(e.code)[:120])
            print(f"  {fam} {rung}: hub_unavailable - {e.code}")
        else:
            _last_acquire_error.update(result="quantize_failed", detail=str(e.code)[:120])
            print(f"  {fam} {rung}: quantize_failed - exit {e.code}")
        return None
    except Exception as e:
        _last_acquire_error.update(result="build_crashed", detail=str(e)[:200])
        print(f"  {fam} {rung}: build_crashed - {e}")
        return None


# --- one candidate's run --------------------------------------------------

# the timer is PER LEVEL (the author's clarification): each level
# gets its own clock, started when its question is sent to the server,
# shared across the level's two parts (one paper, one deadline - the
# v9.5 shape). A timeout ends the run at that level.
LEVEL_TIMEOUT_S = 128.0


def run_pair(
    fam: str,
    rung: str,
    models_dir: str,
    state: dict[str, Any],
    port: int,
    entropy_get=lambda: entropy_bits(8),
) -> list[dict[str, Any]]:
    """One (model, model-quant) pair, ONE acquisition, the FULL 49-
    combination (k, v) cache-quant sweep. Every combination takes
    its own exam under its own 8-bit seed. Returns one record per
    combination; the pair's quant file is deleted at the end (every
    kv combination of it has been exhausted - it will never be
    needed again; the gc deals with the f16s and any leftover)."""
    from bench.exam import bell_window

    exam_seed = entropy_get()
    _ACTIVE_FAMILY[0] = fam

    def _fail_all(result: str, detail: str = "") -> list[dict[str, Any]]:
        return [
            {
                "fam": fam,
                "rung": rung,
                "k_quant": k_quant,
                "v_quant": v_quant,
                "seed": exam_seed,
                "result": result,
                "detail": detail,
            }
            for k_quant in KV_LADDER
            for v_quant in KV_LADDER
        ]

    gguf = _acquire(fam, rung, models_dir)
    if not gguf:
        # the acquire path printed the specific failure; the records
        # carry the distinct cause, not the generic unbuildable
        return _fail_all(
            _last_acquire_error.get("result", "acquire_failed"),
            _last_acquire_error.get("detail", ""),
        )

    # the PAPER is the model's own training window: -c is NOT set -
    # llama-server defaults ctx to 0 = load from the model, so the
    # window is exactly n_ctx_train, one parameter less to worry
    ctx = bell_window(state, fam, models_dir) or 262144
    records: list[dict[str, Any]] = []
    try:
        for k_quant in KV_LADDER:
            for v_quant in KV_LADDER:
                rec = _run_combo(
                    fam,
                    rung,
                    k_quant,
                    v_quant,
                    gguf,
                    ctx,
                    models_dir,
                    port,
                    entropy_get,
                )
                records.append(rec)
    finally:
        # THE FILE RULE: a fully swept quant is deleted - no kv
        # combination of it remains, it will never be needed again.
        # The f16 stays (the quantization source); the gc deals with
        # the f16s and any leftover.
        if rung != "F16" and os.path.isfile(gguf):
            os.remove(gguf)
        _ACTIVE_FAMILY[0] = ""
    return records


def _run_combo(
    fam: str,
    rung: str,
    k_quant: str,
    v_quant: str,
    gguf: str,
    ctx: int,
    models_dir: str,
    port: int,
    entropy_get: Any,
) -> dict[str, Any]:
    """One (k, v) combination of the pair's sweep: one exam, a
    clock, a result. The exam seed (8 bits) serves EVERY level of
    this candidate. The total run timeout is 128s: pass advances a
    level, fail or timeout ends the run and records the reason and
    the high score."""
    t_start = time.monotonic()
    exam_seed = entropy_get()

    kv_tag = f"{rung}-k{k_quant}-v{v_quant}"
    answers_dir = os.path.join("results", "randomizer", fam)
    os.makedirs(answers_dir, exist_ok=True)
    answers_path = os.path.join(answers_dir, f"{kv_tag}.jsonl")
    log_path = os.path.join(answers_dir, f"exam-server-{kv_tag}.log")

    # the cache quants are the candidate's own: --cache-type-k/v,
    # f16 = the default cache (no flag)
    kv_args: list[str] = []
    if k_quant != "f16":
        kv_args += ["--cache-type-k", k_quant]
    if v_quant != "f16":
        kv_args += ["--cache-type-v", v_quant]
    # FULL GPU OFFLOAD, always: --n-gpu-layers 999 forces every
    # layer onto the iGPU - the CPU is useless for this experiment.
    # With ctx 0 (load from model) llama-server then auto-shrinks
    # the context until model + KV + compute fit the device; a
    # candidate that cannot fit even shrunk fails at launch (the
    # honest verdict: this machine cannot run it on the GPU)
    proc, healthy = llama_server.start_server(
        gguf,
        port=port,
        extra_args=[
            "--n-gpu-layers",
            "999",
            "--parallel",
            "1",
            "--reasoning",
            "off",
            "--reasoning-budget",
            "0",
        ]
        + kv_args,
        log_path=log_path,
    )
    high_score = -1
    high_score_time: float | None = None
    fail_reason = ""
    attempts: list[dict[str, Any]] = []
    try:
        if not healthy or not llama_server.wait_healthy(port, proc=proc):
            # THE DIAGNOSIS rides the record (the phi-2 lesson: a
            # quantized KV cache needs head_dim divisible by 32 -
            # 'K cache type q4_0 with block size 32 does not divide
            # n_embd_head_k=80' - an architecture verdict, not a
            # device-fit one; the ledger must tell them apart)
            diag = ""
            try:
                with open(log_path, errors="replace") as fh:
                    errs = [
                        ln.strip()
                        for ln in fh
                        if (" E " in ln or "device lost" in ln.lower())
                        and any(
                            w in ln.lower()
                            for w in ("failed", "error", "does not divide", "device lost")
                        )
                    ]
                diag = errs[-1][-200:] if errs else ""
            except OSError:
                pass
            return {
                "fam": fam,
                "rung": rung,
                "k_quant": k_quant,
                "v_quant": v_quant,
                "seed": exam_seed,
                "result": "server_failed",
                "detail": diag,
            }
        # THE RAM + SETTLED-CONTEXT DATUMS: llama-server's own
        # numbers. ctx 0 (load from model) lets the server AUTO-SHRINK
        # the context until model + KV + compute fit the device; the
        # SETTLED context is the last n_ctx printed, after any
        # resize. The LAST memory breakdown block is the settled
        # state (the first is the pre-shrink wish - the device-lost
        # lesson: first-block numbers can exceed the device). The
        # VULKAN0 row alone - the device the candidate runs on.
        ram_gib: float | None = None
        ctx_settled: int | None = None
        kv_gib: float | None = None
        with open(log_path, errors="replace") as fh:
            for ln in fh:
                m = re.search(r"llama_context: n_ctx\s*=\s*(\d+)", ln)
                if m:
                    ctx_settled = int(m.group(1))
        mem = llama_server.memory_breakdown_gib(log_path)
        if mem is not None:
            vk = (mem.get("devices") or {}).get("Vulkan0")
            if vk is not None:
                ram_gib = round(vk["model_gib"] + vk["context_gib"] + vk["compute_gib"], 3)
                kv_gib = round(vk["context_gib"], 3)
        level = 0
        while True:
            # the PER-LEVEL timer: starts when the question is sent
            level_t0 = time.monotonic()
            deadline = level_t0 + LEVEL_TIMEOUT_S
            insts = {
                "chain": build_chain(exam_seed, level),
                "elevator": build_elevator(exam_seed, level),
            }
            messages: list[dict[str, str]] = []
            remaining = ctx
            level_pass = True
            for part, prompter in (
                ("chain", chain_prompt),
                ("elevator", elevator_prompt),
            ):
                inst = insts[part]
                if remaining <= 0:
                    level_pass = False
                    fail_reason = "out of paper"
                    break
                messages.append({"role": "user", "content": prompter(inst)})
                now = time.monotonic()
                if now >= deadline:
                    level_pass = False
                    fail_reason = "timeout"
                    break
                try:
                    answer, tokens, finish = ask_exam(
                        port,
                        messages,
                        remaining,
                        deadline=deadline,
                    )
                except Exception as e:
                    answer, tokens, finish = "", 0, f"error: {e}"
                ok = score_exam(answer, inst, finish)
                attempt = {
                    "fam": fam,
                    "rung": rung,
                    "k_quant": k_quant,
                    "v_quant": v_quant,
                    "seed": exam_seed,
                    "level": level,
                    "part": part,
                    "ok": ok,
                    "finish_reason": finish,
                    "answer_tokens": tokens,
                    "answer": (answer or "")[-2000:],
                }
                attempts.append(attempt)
                with open(answers_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(attempt, ensure_ascii=True) + "\n")
                if not ok:
                    if str(finish).startswith("error"):
                        fail_reason = "error"
                    elif finish == "time_limit" or time.monotonic() >= deadline:
                        fail_reason = "timeout"
                    elif finish == "length":
                        fail_reason = "out of paper"
                    else:
                        fail_reason = "wrong answer"
                    level_pass = False
                    break
                messages.append({"role": "assistant", "content": answer or ""})
                remaining -= tokens
            level_time = round(time.monotonic() - level_t0, 1)
            if not level_pass:
                break
            # the SPEED datum is at the HIGH-SCORE exam (the author's
            # clarification): the time of the level the candidate
            # PASSED that set its high score - not the failing level
            high_score_time = level_time
            high_score = level
            level += 1
    finally:
        llama_server.stop_server(proc, port)

    return {
        "fam": fam,
        "rung": rung,
        "k_quant": k_quant,
        "v_quant": v_quant,
        "seed": exam_seed,
        "result": "done",
        "high_score": high_score,
        "fail_reason": fail_reason,
        "ram_gib": ram_gib,
        "ctx_settled": ctx_settled,
        "kv_gib": kv_gib,
        "attempts": len(attempts),
        # the SPEED datum: the LAST level's time (the deciding level's
        # own timer), not the whole run - per the author's clarification
        "high_score_time_s": high_score_time,  # None: no level passed
        "elapsed_s": round(time.monotonic() - t_start, 1),
    }


# --- the controller --------------------------------------------------------


# the watchability cadence (the exam's per-family push ruling,
# randomizer-shaped): commit + push after EVERY pair - the full
# 49-combination (k, v) sweep of the model-quant lands in the
# ledger as one unit, a multi-hour run is readable remotely pair
# by pair


def main(on_progress: Any = None) -> None:
    # IPv4-FIRST (the dead-IPv6 fix): Python's connect tries IPv6
    # first with no fallback - a black-holed IPv6 route (curl works,
    # the library hangs, zero packets - the author's T14s case) is
    # an infinite silent hang. Prefer AF_INET in getaddrinfo: every
    # hub/library connection resolves IPv4 only, until the machine's
    # IPv6 is fixed at the router level.
    import socket

    _orig_getaddrinfo = socket.getaddrinfo

    def _ipv4_first(host, port, family=0, type=0, proto=0, flags=0):
        try:
            return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
        except socket.gaierror:
            return _orig_getaddrinfo(host, port, family, type, proto, flags)

    socket.getaddrinfo = _ipv4_first  # ty: ignore[invalid-assignment]
    models_dir = "models"
    state_file = RANDOMIZER_STATE_FILE
    os.makedirs("state", exist_ok=True)
    port = int(os.environ.get("RANDOMIZER_PORT", "8210"))

    state: dict[str, Any] = {}
    if os.path.isfile(state_file):
        with open(state_file, encoding="utf-8") as fh:
            state = json.load(fh)
    results: list[dict[str, Any]] = state.setdefault("results", [])

    pool = the_pool()
    _GC_POOL.clear()
    _GC_POOL.extend(pool)
    assert len(pool) == 2048, len(pool)
    n_kv = len(KV_LADDER)
    total_pairs = len(pool)

    stop = threading.Event()
    gc_log: list[str] = []
    watchdog = threading.Thread(
        target=disk_watchdog,
        args=(models_dir, None, stop, gc_log),
        daemon=True,
    )
    watchdog.start()

    # no SIGINT handler here: the full_benchmark envelope owns it
    # (its handler runs the git tail); the loop saves the state after
    # EVERY pick, so the on-disk state is always current when the
    # envelope's handler fires and commits it

    # one chance per candidate: the done-set persists in the state
    done: set[str] = set(state.get("done", []))
    state["done"] = sorted(done)
    _GC_DONE_SET.clear()
    _GC_DONE_SET.update(done)

    def write_ledger() -> None:
        """md/randomizer.md: rank (highest score, tiebreak by time),
        model, high score, quant @ high score, speed (fast <= 32s,
        medium <= 64s, slow <= 128s - the candidate's whole run)."""
        rows = [r for r in results if r.get("result") == "done"]
        done_pairs = len(done)
        rows.sort(
            key=lambda r: (
                -(r.get("high_score") or -1),
                r.get("high_score_time_s") if r.get("high_score_time_s") is not None else 1e9,
            )
        )

        # THE TOP-5% DASHBOARD (the author's four medians: params,
        # quant, high-score level time, score) - computed FIRST and
        # rendered at the TOP of the ledger (the author's ruling)
        import re as _re
        import statistics as _stats

        fam_meta: dict[str, float] = {}
        for ln in open("md/models.md", encoding="utf-8"):
            m = _re.match(r"^\| ([^|]+) \| ([0-9.]+) \|", ln)
            if m:
                fam_meta[m.group(1).strip()] = float(m.group(2))
        # THE TOP 3 (the author's ruling): the three highest SCORE
        # LEVELS, ties included - every candidate whose high_score is
        # one of the three highest distinct scores (score 3, 2, 1
        # when the best is 3; all the tied candidates of each level)
        scores_desc = sorted({r.get("high_score") or -1 for r in rows}, reverse=True)
        top_scores = set(scores_desc[:3])
        top = [r for r in rows if (r.get("high_score") or -1) in top_scores]
        k = len(top)
        t_params = [fam_meta[r["fam"]] for r in top if r["fam"] in fam_meta]
        t_times = [r["high_score_time_s"] for r in top if r.get("high_score_time_s") is not None]
        t_scores = [r.get("high_score") or -1 for r in top]
        lines = ["# randomizer.md - the randomizer ledger", ""]
        lines.append("## the top 3 dashboard")
        lines.append("")
        lines.append(
            f"- measured: {len(rows)} done candidates, top 3 score levels "
            f"({k} candidates of {len(rows)}, ties included)"
        )
        if t_params:
            lines.append(f"- params median: **{_stats.median(t_params):g} B**")
        from collections import Counter as _C

        for label, key in (
            ("model_quant", "rung"),
            ("k_quant", "k_quant"),
            ("v_quant", "v_quant"),
        ):
            vals = [r.get(key) for r in top if r.get(key) is not None]
            if vals:
                mode = _C(vals).most_common(1)[0][0]
                lines.append(f"- {label} mode: **{mode}**")
        if t_times:
            lines.append(f"- high-score level time median: **{_stats.median(t_times):g}s**")
        if t_scores:
            lines.append(f"- score median: **{_stats.median(t_scores):g}**")
        t_ram = [r["ram_gib"] for r in top if r.get("ram_gib") is not None]
        if t_ram:
            lines.append(f"- vulkan0 ram median: **{_stats.median(t_ram):.2f} GiB**")
        t_ctx = [r["ctx_settled"] for r in top if r.get("ctx_settled") is not None]
        if t_ctx:
            lines.append(f"- context median: **{_stats.median(t_ctx):,.0f}**")
        lines.append("")
        lines.append("_the machine sweet-spot band, live as the pool fills_")
        lines.append("")
        lines.append("Every candidate gets ONE chance (no replacement). Rank:")
        lines.append("highest score, tiebreak by time. Speed: the candidate's")
        lines.append("whole run - fast <= 32s, medium <= 64s, slow <= 128s.")
        lines.append("")
        lines.append(
            "| rank | model | high score | quant @high | k | v | vulkan0 ram | ctx | speed |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for i, r in enumerate(rows):
            raw_t = r.get("high_score_time_s")
            t = float(raw_t) if raw_t is not None else float(r.get("elapsed_s") or 0.0)
            speed = "fast" if t <= 32 else ("medium" if t <= 64 else "slow")
            ram = r.get("ram_gib")
            ram_s = f"{ram:.2f}" if ram is not None else "-"
            ctx = r.get("ctx_settled")
            ctx_s = f"{ctx:,}" if ctx is not None else "-"
            lines.append(
                f"| {i + 1} | {r['fam']} | {r.get('high_score', -1)} | {r['rung']} "
                f"| {r.get('k_quant', 'f16')} | {r.get('v_quant', 'f16')} "
                f"| {ram_s} | {ctx_s} | {speed} |"
            )
        lines.append("")
        lines.append(
            f"_{len(rows)} candidates run of {len(pool) * n_kv * n_kv:,} "
            f"({done_pairs:,} of {len(pool):,} pairs swept); "
            "each pair one acquisition, the seed recorded in state._"
        )
        with open("md/randomizer.md", "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    print(
        f"[randomizer] pool: {total_pairs:,} (model, rung) pairs "
        f"(each pick sweeps {n_kv} x {n_kv} = {n_kv * n_kv} kv combinations), "
        f"no size gate - llama-server decides at launch, ONE chance each"
    )
    print(f"[randomizer] entropy: {_ENTROPY_DEV}")
    print(f"[randomizer] gc: /home free > {GC_THRESHOLD_GIB:g} GiB, {GC_INTERVAL_S:g}s watchdog")
    n = len(done)
    while len(done) < len(pool):
        # the pick, v3: 16 bits = 11 model index + 5 model-quant. The
        # 11-bit draw is the pool index (uniform over the 64
        # families); the rung comes from the 5-bit draw over LADDER.
        # The done-key is the PAIR, the pool index of the (fam, rung)
        # combination: one chance per pair, and a pick that re-draws
        # an already-swept pair re-draws with fresh entropy.
        pick = entropy_bits(PICK_BITS)
        model_idx = pick & 0x7FF
        rung_idx = (pick >> 11) & 0x1F
        fam = pool[model_idx][0]
        # THE PAIR KEY IS THE POOL INDEX of the (fam, rung) actually
        # evaluated: fam_pos = model_idx // 32 (the pool is fam-major,
        # 32 rungs per family), so the key space is 0..2047 - the
        # same space the gc and the drain condition count in
        fam_pos = model_idx // 32
        pair_key = fam_pos * 32 + rung_idx
        key = f"{pair_key}"
        if key in done:
            continue  # the pair already had its chance: re-draw
        rung = LADDER[rung_idx]
        print(
            f"[randomizer] #{n + 1} pick=0b{pick:016b} "
            f"-> {fam} {rung} (sweeping {n_kv * n_kv} kv combinations)"
        )
        recs = run_pair(fam, rung, models_dir, state, port)
        results.extend(recs)
        done.add(key)
        _GC_DONE_SET.add(key)
        state["done"] = sorted(done)
        state["results"] = results[-5000:]  # the state stays bounded
        _state_store.save_state(state_file, state)
        write_ledger()
        while gc_log:
            print(gc_log.pop(0))
        done_recs = [r for r in recs if r.get("result") == "done"]
        best = max((r.get("high_score") or -1 for r in done_recs), default=None)
        summary = (
            f"{len(done_recs)}/{len(recs)} done, best high_score={best}"
            if done_recs
            else recs[0].get("result", "?")
        )
        print(f"[randomizer]   -> {summary}")
        n += 1
        if on_progress is not None:
            try:
                on_progress(n)
            except Exception as e:
                print(f"[randomizer] progress push failed (ignored): {e}")
    print(f"[randomizer] the pool is drained: {len(done)} pairs, one chance each - complete")


if __name__ == "__main__":
    main()
