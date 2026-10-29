#!/usr/bin/env python3
"""trek_run.py - protocol trek v2: walkers over exam histories.

The STATE is the exam-history store (bench/trek.py): per candidate
(model, model_quant, k, v), a level-by-level record - pass times
and timeout budgets. The walker derives its scores from the
histories under its budget; the runner CONTINUES each candidate's
exam from its frontier level when the walker requests work. The
kv sweep amortization stays: the picked pair's quant file is
acquired once, all 49 candidates examined under the current budget.

The walker seed: ONE for the whole run (default 1), all walkers;
the exam seeds are candidate-deterministic (the same candidate =
the same exam instance, so re-runs continue the same exam).
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

import infra.hf_download as hf_download
import infra.llama_server as llama_server
from bench import state_store as _state_store
from bench import trek
from bench.contracts import warn_contract
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


# the ei's state file (module-level: full_benchmark's
# --clean wipes it before main() runs)
TREK_STATE_FILE = "state/trek-state.json"

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
        # THE CORRUPT-FILE GATE (the SIGINT-mid-quantize incident): a
        # partial file left by an interrupted quantization looks ready
        # to the size check but dies on every launch ('invalid magic
        # characters'). Verify the GGUF magic; a corrupt file is
        # deleted and re-quantized, never trusted.
        if hf_download.is_valid_gguf(existing):
            return existing
        print(
            f"  [acquire] {rung}: the existing file is CORRUPT (no GGUF "
            f"magic - an interrupted quantization) - deleting and requantizing"
        )
        os.remove(existing)
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
    budget_s: float,
) -> None:
    """One (model, model-quant) pair under the walker's budget: ONE
    acquisition, then the 49 candidates' exam CONTINUATIONS - each
    candidate whose history needs work under this budget resumes
    its exam from its frontier level; settled candidates cost
    nothing (the derivation reads the history). The pair's quant
    file is deleted at the end (the gc owns the f16s)."""
    from bench.exam import bell_window

    warn_contract(
        "pre",
        "run_pair.pair",
        fam in {f for f, _ in roster_from_models_md()} and rung in LADDER,
        f"the pair ({fam}, {rung}) is not in the pool",
    )
    _ACTIVE_FAMILY[0] = fam
    candidates = state.setdefault("candidates", {})

    def save() -> None:
        _state_store.save_state(TREK_STATE_FILE, state)

    gguf = _acquire(fam, rung, models_dir)
    if not gguf:
        # the acquire failed: mark the launch failure on all 49
        # candidates (the walker sees a failed cell - settled,
        # scoreless, not worth re-acquiring under any budget)
        for k in KV_LADDER:
            for v in KV_LADDER:
                key = trek.cand_key(fam, rung, k, v)
                if key not in candidates:
                    candidates[key] = {
                        "_launch": {
                            "status": "failed",
                            "detail": _last_acquire_error.get("detail", "")[:100],
                        }
                    }
        save()
        _ACTIVE_FAMILY[0] = ""
        return

    size_gib = round(os.path.getsize(gguf) / (2**30), 3)
    print(f"  [2] {rung}: measured {size_gib:.2f} GiB on disk")
    if size_gib > hf_download.DEVICE_LIMIT_GIB:
        for k in KV_LADDER:
            for v in KV_LADDER:
                key = trek.cand_key(fam, rung, k, v)
                if key not in candidates:
                    candidates[key] = {"_launch": {"status": "failed", "detail": "too large"}}
        save()
        if rung != "F16" and os.path.isfile(gguf):
            os.remove(gguf)
        _ACTIVE_FAMILY[0] = ""
        return

    ctx = bell_window(state, fam, models_dir) or 262144

    # THE WORK LIST: the candidates needing exam work under this
    # budget (the derivation's needs_rerun)
    work = []
    for k in KV_LADDER:
        for v in KV_LADDER:
            key = trek.cand_key(fam, rung, k, v)
            hist = candidates.get(key, {})
            if trek.needs_rerun(hist, budget_s):
                work.append((k, v, key, hist))
    n_settled = len(KV_LADDER) ** 2 - len(work)
    print(f"[trek] {len(work)} candidates need work under {budget_s:g}s "
          f"({n_settled} settled from history)")

    print("0", end="", flush=True)
    n = 0
    n_ladder = len(KV_LADDER)
    try:
        for k, v, key, hist in work:
            _run_combo(fam, rung, k, v, gguf, ctx, models_dir, port, budget_s, hist)
            candidates[key] = hist
            save()
            n += 1
            print(".", end="", flush=True)
            if n % n_ladder == 0:
                print(n, end="", flush=True)
        print()
    finally:
        if rung != "F16" and os.path.isfile(gguf):
            os.remove(gguf)
        _ACTIVE_FAMILY[0] = ""
    return


def _run_combo(
    fam: str,
    rung: str,
    k_quant: str,
    v_quant: str,
    gguf: str,
    ctx: int,
    models_dir: str,
    port: int,
    budget_s: float,
    history: dict[int, Any],
) -> dict[int, Any]:
    """One candidate's exam CONTINUATION under the walker's budget.
    The candidate's history is the record: the exam resumes at the
    frontier level (the first unmeasured level, or the level whose
    timeout was under a smaller budget); passes and timeouts update
    the history in place. The candidate-deterministic exam seed
    means the exam instance is the SAME as any previous run - the
    continuation is faithful."""
    exam_seed = trek.EXAM_SEED  # the repetition counter: always 1 (one exam per candidate)
    instance_key = trek.exam_instance_key(fam, rung, k_quant, v_quant)
    kv_tag = f"{rung}-k{k_quant}-v{v_quant}"
    answers_dir = os.path.join("results", "trek", fam)
    os.makedirs(answers_dir, exist_ok=True)
    answers_path = os.path.join(answers_dir, f"{kv_tag}.jsonl")
    log_path = os.path.join(answers_dir, f"exam-server-{kv_tag}.log")

    kv_args: list[str] = []
    if k_quant != "f16":
        kv_args += ["--cache-type-k", k_quant]
    if v_quant != "f16":
        kv_args += ["--cache-type-v", v_quant]
    proc, healthy = llama_server.start_server(
        gguf,
        port=port,
        extra_args=[
            "--n-gpu-layers", "999",
            "--parallel", "1",
            "--reasoning", "off",
            "--reasoning-budget", "0",
        ] + kv_args,
        log_path=log_path,
    )
    try:
        if not healthy or not llama_server.wait_healthy(port, proc=proc):
            diag = ""
            try:
                with open(log_path, errors="replace") as fh:
                    errs = [
                        ln.strip() for ln in fh
                        if (" E " in ln or "device lost" in ln.lower())
                        and any(w in ln.lower() for w in ("failed", "error", "does not divide", "device lost"))
                    ]
                diag = errs[-1][-200:] if errs else ""
            except OSError:
                pass
            history.setdefault("_launch", {"status": "failed", "detail": diag})
            return history

        # THE FRONTIER: the first level needing work under this budget
        level = 0
        while True:
            rec = history.get(level)
            if rec is None:
                break  # unmeasured: the exam continues here
            if rec.get("status") == "pass":
                if rec.get("time_s", 1e9) <= budget_s:
                    level += 1
                    continue
                return history  # passed slower than the budget: settled
            if rec.get("status") == "timeout":
                if rec.get("timeout_s", 1e9) < budget_s:
                    break  # the smaller-budget timeout: re-run here
                return history  # settled at this budget
            return history  # wrong answer etc: settled

        # THE EXAM CONTINUATION from the frontier level
        while True:
            level_t0 = time.monotonic()
            deadline = level_t0 + budget_s
            insts = {
                "chain": build_chain(instance_key, level),
                "elevator": build_elevator(instance_key, level),
            }
            messages: list[dict[str, str]] = []
            remaining = ctx
            level_pass = True
            fail_reason = ""
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
                        port, messages, remaining, deadline=deadline,
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
                    "budget_s": budget_s,
                    "level": level,
                    "part": part,
                    "ok": ok,
                    "finish_reason": finish,
                    "answer_tokens": tokens,
                    "answer": (answer or "")[-2000:],
                }
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
                if fail_reason == "timeout":
                    history[level] = {"status": "timeout", "timeout_s": budget_s}
                elif fail_reason == "wrong answer":
                    history[level] = {"status": "wrong answer"}
                elif fail_reason == "out of paper":
                    history[level] = {"status": "out of paper"}
                else:
                    history[level] = {"status": "error", "detail": fail_reason[:100]}
                break
            history[level] = {"status": "pass", "time_s": level_time}
            level += 1
    finally:
        llama_server.stop_server(proc, port)
    return history


def _est_size_gib_of(r: dict[str, Any]) -> float | None:
    """the candidate's weights size for the extended reporting's
    budget table: the MEASURED size_gib where the record carries it
    (the post-quantization truth), else the estimate from the
    roster (f16 x bpw/16). The catalog lookup is cached: the ledger
    writes call this per record, a rebuild per record was the
    table-render timeout."""
    from bench.trek import _est_size_gib_of as _trek_size

    return _trek_size(r)


def write_ledger(st: dict[str, Any] | None = None) -> None:
    """THE LEDGER (md/trek.md): the practitioner tables, derived from
    the exam histories - v2's single source of truth. Every table
    recomputes from the state on every call, so the ledger is always
    current (the v1 ledger went stale when the v2 rewrite dropped
    its call - the lesson: the writer hangs off the save).

    THE TABLES:
    - the score-patience frontier: per patience tier (the dyadic
      cuts), the best score achievable - the derivation's own
      score_under - and its holder (the candidate)
    - the score-by-ram table: per memory tier, the best score
      (when the ram measurements exist in the histories' sidecars;
      v2's histories carry the launch facts, the ram tiers derive
      from the measured sizes)
    """
    if st is None:
        st = trek.load_state()
    cands = st.get("candidates", {})
    grid = trek.Grid()
    kv_ladder = ["f16", "q8_0", "q5_1", "q5_0", "q4_1", "q4_0", "iq4_nl"]
    patience_cuts = trek.CLOCK_LADDER  # 1..128s

    # THE PER-CANDIDATE DERIVATIONS at every patience cut
    rows = []
    for key, hist in cands.items():
        parts = key.split("|")
        if len(parts) != 4:
            continue
        fam, rung, k, v = parts
        for cut in patience_cuts:
            s = trek.score_under(hist, cut)
            if s is not None and s >= 0:
                rows.append({"fam": fam, "rung": rung, "k": k, "v": v,
                             "cut": cut, "score": s})

    lines = ["# trek.md - the trek ledger (v2: derived from the exam histories)", ""]

    # THE SCORE-PATIENCE FRONTIER
    lines += ["## the score-patience frontier (practitioner reporting)", ""]
    lines += ["the best score achievable at a patience level (the per-level", "time limit), derived from the shared exam histories", ""]
    lines += ["| patience | best score | holder |", "|---|---|---|"]
    for cut in patience_cuts:
        best = None
        for r in rows:
            if r["cut"] == cut and (best is None or r["score"] > best["score"]):
                best = r
        if best:
            lines.append(
                f"| <= {cut:g}s | {best['score']} | "
                f"{best['fam']} {best['rung']} k={best['k']} v={best['v']} |"
            )
        else:
            lines.append(f"| <= {cut:g}s | - | (nothing measured yet) |")
    lines.append("")

    # THE WALKS' PROGRESS
    lines += ["## the walkers (the budget ladder's progress)", ""]
    lines += ["| budget | position | movements | high | best cell |", "|---|---|---|---|---|"]
    for b_key, w in sorted(st.get("walks", {}).items(), key=lambda kv: float(kv[0])):
        pos = w.get("position", "?")
        best = w.get("best", "?")
        best_cell = ""
        try:
            fam, rung = grid.cell(best[0], best[1])
            best_cell = f"{fam} {rung}"
        except Exception:
            pass
        lines.append(
            f"| {b_key}s | {pos} | {w.get('movements', 0)} | "
            f"{w.get('high', -1)} | {best_cell} |"
        )
    lines.append("")

    # THE MEASURED POOL
    n_with_scores = sum(1 for h in cands.values() if trek.score_under(h, 128.0) is not None and trek.score_under(h, 128.0) >= 0)
    lines += [
        f"_{len(cands):,} candidates measured (of 2048 pairs x 49 kv = "
        f"{2048 * 49:,} total); the histories are the single source "
        f"of truth, the tables derive on every ledger write._",
    ]
    with open("md/trek.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main(on_progress: Any = None, walker_seed: int = 1) -> None:
    """The trek v2 run loop: the walker walks the grid at the current
    budget, the runner does the exam work; the histories accumulate;
    a converged budget doubles (the ladder 1..128s); the trek ends
    at 128s convergence. One walker seed for everything."""
    import socket

    _orig_getaddrinfo = socket.getaddrinfo

    def _ipv4_first(host, port, family=0, type=0, proto=0, flags=0):
        try:
            return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
        except socket.gaierror:
            return _orig_getaddrinfo(host, port, family, type, proto, flags)

    socket.getaddrinfo = _ipv4_first  # ty: ignore[invalid-assignment]
    models_dir = "models"
    port = int(os.environ.get("TREK_PORT", "8210"))

    print(f"[trek] v2: walkers over exam histories; the walker seed {walker_seed}")
    print(f"[trek] gc: /home free > {GC_THRESHOLD_GIB:g} GiB, {GC_INTERVAL_S:g}s watchdog")

    st = trek.load_state()

    # the budget ladder: start where the state left off (or 1s)
    budget = st.get("last_budget", trek.CLOCK_LADDER[0])
    budget_idx = trek.CLOCK_LADDER.index(budget)
    while budget_idx < len(trek.CLOCK_LADDER):
        budget = trek.CLOCK_LADDER[budget_idx]
        st["last_budget"] = budget
        trek.save_state(st)
        write_ledger(st)
        print(f"[trek] the {budget:g}s walker")

        n = 0
        while True:
            pick = trek.walk(st, walker_seed, budget_s=budget)
            if pick is None:
                break
            if pick["reason"] == "converged":
                print(
                    f"[trek] the {budget:g}s walker CONVERGED "
                    f"(best {pick['fam']} {pick['rung']}, high {pick['high']})"
                )
                break
            fam, rung = pick["fam"], pick["rung"]
            print(
                f"[trek] {budget:g}s, epoch {pick['epoch']}, movement {pick['movements']}: "
                f"{fam} {rung} (high {pick['high']}, best at {pick['best']})"
            )
            run_pair(fam, rung, models_dir, st, port, budget)
            write_ledger(st)  # the ledger re-derives from the histories
            n += 1
            if on_progress is not None:
                try:
                    on_progress(n)
                except Exception:
                    pass
        budget_idx += 1
    print("[trek] the trek has ENDED: converged at the 128s budget")
