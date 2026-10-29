#!/usr/bin/env python3
"""trek_run.py - protocol ei: the epitome of simplicity.

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

import infra.hf_download as hf_download
import infra.llama_server as llama_server
from bench import state_store as _state_store
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

    # PRE: the pair exists in the pool (fam on the roster, rung on the LADDER)
    warn_contract(
        "pre",
        "run_pair.pair",
        fam in {f for f, _ in roster_from_models_md()} and rung in LADDER,
        f"the pair ({fam}, {rung}) is not in the pool",
    )
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
                # the measured size when a file exists; None when the
                # acquire failed before producing one (gguf is None)
                "size_gib": (
                    round(os.path.getsize(gguf) / (2**30), 3)
                    if gguf and os.path.isfile(gguf)
                    else None
                ),
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
    # THE POST-QUANTIZATION SIZE CHECK (the author's ruling): the
    # file is on disk now - MEASURE it. The estimate chose the band
    # and gated the download; the measured size is the truth that
    # gates the LAUNCH: a file over the device budget cannot run
    # (the GPU can never hold it), so the sweep fans out the honest
    # too_large_measured verdict without paying 49 doomed launches;
    # the recovery then re-resolves the band. The measured size
    # also rides every record - the ledger's size column becomes
    # the measured truth, not the estimate.
    size_gib = round(os.path.getsize(gguf) / (2**30), 3)
    print(f"  [2] {rung}: measured {size_gib:.2f} GiB on disk")
    if size_gib > hf_download.DEVICE_LIMIT_GIB:
        print(
            f"  [2] {rung}: measured {size_gib:.2f} GiB exceeds the "
            f"device budget {hf_download.DEVICE_LIMIT_GIB:.0f} GiB - CANNOT RUN, "
            "skipping the launch (the measured gate)"
        )
        return _fail_all(
            "too_large_measured",
            f"measured {size_gib:.2f} GiB > {hf_download.DEVICE_LIMIT_GIB:.0f} GiB device budget",
        )

    ctx = bell_window(state, fam, models_dir) or 262144

    # THE SWEEP RESUME (the author's ruling): the state's results ARE
    # the kv-combo memory - every completed combo's record is in the
    # state the moment it lands (saved per combo below), so a stop
    # mid-sweep re-picks the pair and SKIPS the combos whose records
    # already exist; the sweep resumes at the next untested (k, v)
    # instead of starting from 0. The answer files stay too (per
    # combo, on disk), but the RECORD is the resume's truth: it
    # carries the verdict, not just the prose.
    prior_records = [
        r for r in state.get("results", []) if r.get("fam") == fam and r.get("rung") == rung
    ]
    done_combos = {(r.get("k_quant"), r.get("v_quant")) for r in prior_records}
    records: list[dict[str, Any]] = list(prior_records)
    n_resume = len(done_combos)

    # THE KV PROGRESS (the author's ruling): a dot per combination,
    # the count at every multiple of 7 - the 49-combo sweep reads
    # as ......7......14......21 ......49, live in the console.
    # A resumed sweep continues the count from its true position.
    n_kv_ladder = len(KV_LADDER)
    try:
        # THE FILLING DOTS (the author's ruling): the line starts
        # at 0 and a dot prints as each kv combo FINISHES - the
        # record landing in the state is the dot's truth. A resume
        # prints its already-done combos' dots up front (so 0..
        # reads instantly as 2 done), then fills the rest live; the
        # count prints at every multiple of 7.
        print("0", end="", flush=True)
        n_combo = 0
        for _ in range(n_resume):
            n_combo += 1
            print(".", end="", flush=True)
            if n_combo % n_kv_ladder == 0:
                print(n_combo, end="", flush=True)
        for k_quant in KV_LADDER:
            for v_quant in KV_LADDER:
                if (k_quant, v_quant) in done_combos:
                    continue  # already measured: the resume skips it
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
                # THE PER-COMBO PERSISTENCE: the record lands in the
                # state NOW - a crash after this combo keeps it, the
                # resume after the crash never re-runs it
                state.setdefault("results", []).append(rec)
                state["results"] = state["results"][-5000:]
                _state_store.save_state(TREK_STATE_FILE, state)
                # THE FILLING DOT: this combo finished - the dot is
                # its truth (and the count at every 7)
                n_combo += 1
                print(".", end="", flush=True)
                if n_combo % n_kv_ladder == 0:
                    print(n_combo, end="", flush=True)
        print()  # the sweep's line ends
        if n_resume:
            print(f"[trek] sweep resumed: {n_resume} combos already done, {n_combo} run")
    finally:
        # THE FILE RULE: a fully swept quant is deleted - no kv
        # combination of it remains, it will never be needed again.
        # The f16 stays (the quantization source); the gc deals with
        # the f16s and any leftover.
        if rung != "F16" and os.path.isfile(gguf):
            os.remove(gguf)
        # POST: the sweep produced one record per (k, v) combination -
        # 49 of them, all on this pair (the resume counts the prior
        # records in, so 49 holds even after a mid-sweep restart)
        combos_seen = {(r.get("k_quant"), r.get("v_quant")) for r in records}
        warn_contract(
            "post",
            "run_pair.sweep_complete",
            len(records) == len(KV_LADDER) ** 2 and len(combos_seen) == len(KV_LADDER) ** 2,
            f"sweep produced {len(records)} records, "
            f"{len(combos_seen)} distinct combos (expect {len(KV_LADDER) ** 2})",
        )
        warn_contract(
            "post",
            "run_pair.on_pair",
            all(r.get("fam") == fam and r.get("rung") == rung for r in records),
            "records from another pair in this sweep's result",
        )
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
    answers_dir = os.path.join("results", "trek", fam)
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
# ei-shaped): commit + push after EVERY pair - the full
# 49-combination (k, v) sweep of the model-quant lands in the
# ledger as one unit, a multi-hour run is readable remotely pair
# by pair


_MODELS_BY_ID: dict[str, dict[str, Any]] | None = None


def _est_size_gib_of(r: dict[str, Any]) -> float | None:
    """the candidate's weights size for the extended reporting's
    budget table: the MEASURED size_gib where the record carries it
    (the post-quantization truth), else the estimate from the
    roster (f16 x bpw/16). The catalog lookup is cached: the ledger
    writes call this per record, a rebuild per record was the
    table-render timeout."""
    from bench.trek import _est_size_gib_of as _trek_size

    return _trek_size(r)


def main(on_progress: Any = None) -> None:
    """The trek's run loop. The exam clock is the WALK's own: it
    starts at 1s per level and doubles when a trek converges (the
    teleport rule), up to 128s - see bench/trek.py's walk."""
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
    state_file = TREK_STATE_FILE
    os.makedirs("state", exist_ok=True)
    port = int(os.environ.get("EI_PORT", "8210"))

    state: dict[str, Any] = {}
    if os.path.isfile(state_file):
        with open(state_file, encoding="utf-8") as fh:
            state = json.load(fh)
    # the state's results list IS the ledger's memory; run_pair
    # appends per combo and may rebind the list on trim, so every
    # consumer re-reads state["results"] instead of caching a handle.
    # A fresh state may lack the keys - created here (the KeyError
    # crash on a fresh trek state).
    state.setdefault("results", [])
    state.setdefault("done", [])
    state.setdefault("walk", [])
    # the done keys are PER CLOCK ("index@clock"); the legacy keys
    # (bare indices, from the single-clock era) stay valid

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
        rows = [r for r in state["results"] if r.get("result") == "done"]
        done_pairs = len(done)

        # THE LEDGER (the author's rulings): the two practitioner
        # tables - the score-time frontier and the score-by-ram
        # budget - plus the footer. The time-tier crowns section is
        # REMOVED per the author's ruling (the walker has no PoI
        # target; the tables carry the practitioner information).
        lines = ["# trek.md - the trek ledger", ""]

        from bench.trek import (
            RAM_LADDER_GIB,
            TIME_LADDER_S,
        )

        # THE PRACTITIONER REPORTING: both tables are floors, not
        # ceilings - the grid is not fully measured, the bests can
        # only rise.
        timed = [
            r
            for r in rows
            if r.get("high_score_time_s") is not None and r.get("high_score") is not None
        ]
        if timed:
            lines.append("")
            lines.append("## the score-time frontier (practitioner reporting)")
            lines.append("")
            lines.append("the best score at a patience level (the high-score level's time);")
            lines.append("the ram column is the holder's memory TIER - the dyadic cut")
            lines.append("(1/2/4/8/16 GiB) its measured vulkan0 ram fits")
            lines.append("")
            lines.append("| patience | best score | holder | at | ram |")
            lines.append("|---|---|---|---|---|")
            for cap in TIME_LADDER_S:
                cands = [r for r in timed if r["high_score_time_s"] <= cap]
                if not cands:
                    continue
                best = max(r["high_score"] for r in cands)
                h = min(
                    (r for r in cands if r["high_score"] == best),
                    key=lambda r: r["high_score_time_s"],
                )
                ram = h.get("ram_gib")
                ram_tier = next(
                    (f"g{c:g}" for c in RAM_LADDER_GIB if ram is not None and ram <= c),
                    "-",
                )
                t_disp = f"{h['high_score_time_s']:.0f}"
                lines.append(
                    f"| <= {int(cap)}s | {best} | {h['fam']} {h['rung']} "
                    f"k={h['k_quant']} v={h['v_quant']} | {t_disp}s | {ram_tier} |"
                )
        rammed = [r for r in rows if r.get("ram_gib") is not None]
        if rammed:
            lines.append("")
            lines.append("## the score-by-ram-budget table (practitioner reporting)")
            lines.append("")
            lines.append("the best score whose MEASURED vulkan0 ram (model + kv + compute) fits")
            lines.append("a budget; the patience column is the holder's time tier - how long")
            lines.append("you wait per level at that memory size")
            lines.append("")
            lines.append("| ram budget | best score | holder | patience |")
            lines.append("|---|---|---|---|")
            for cap in RAM_LADDER_GIB:
                cands = [r for r in rammed if r["ram_gib"] <= cap]
                if not cands:
                    continue
                best = max(r["high_score"] for r in cands)
                h = min(
                    (r for r in cands if r["high_score"] == best),
                    key=lambda r: r["ram_gib"],
                )
                t_s = h.get("high_score_time_s")
                tier = next(
                    (f"t{int(c)}" for c in TIME_LADDER_S if t_s is not None and t_s <= c),
                    "-",
                )
                lines.append(
                    f"| <= {cap} GiB | {best} | {h['fam']} {h['rung']} "
                    f"k={h['k_quant']} v={h['v_quant']} | {tier} |"
                )
        lines.append("")
        lines.append(
            f"_{len(rows)} candidates measured, {done_pairs:,} of {len(pool):,} "
            "pairs swept; each pair one acquisition, the seed recorded in state._"
        )
        with open("md/trek.md", "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    print(
        f"[trek] pool: {total_pairs:,} (model, rung) pairs "
        f"(each pick sweeps {n_kv} x {n_kv} = {n_kv * n_kv} kv combinations), "
        f"no size gate - llama-server decides at launch, ONE chance each"
    )
    print(f"[trek] entropy: {_ENTROPY_DEV}")
    print(f"[trek] gc: /home free > {GC_THRESHOLD_GIB:g} GiB, {GC_INTERVAL_S:g}s watchdog")
    n = len(done)
    while len(done) < len(pool):
        # THE TREK STEP: bench/trek.py's deterministic walker - it
        # replays the walk from (0, 0) through the cached cells
        # (free) and hands back the FIRST cell needing evaluation.
        # kv quants are NOT searched: the picked cell's pair sweeps
        # all 49 (k, v) combinations in one acquisition. The
        # done-key is the cell's pool index.
        from bench import trek

        rec_pick = trek.walk(state_file)
        if rec_pick is None:
            print("[trek] the trek has ENDED: converged at the 128s clock")
            break
        pair_key = rec_pick["pool_index"]
        fam = rec_pick["fam"]
        rung = rec_pick["rung"]
        clock = rec_pick.get("clock_s", 1.0)
        # THE PER-CLOCK DONE-KEY: a cell measured at 1s re-opens at
        # 2s (the higher clock may score differently) - the key
        # carries the clock so the same cell can complete multiple
        # sweeps, one per clock
        key = f"{pair_key}@{clock:g}"
        # THE EXAM CLOCK FOLLOWS THE WALK: the sweep runs at the
        # walker's current clock (the LEVEL_TIMEOUT_S the per-level
        # deadline reads)
        global LEVEL_TIMEOUT_S
        LEVEL_TIMEOUT_S = float(clock)
        est = rec_pick.get("high_score")
        ep = rec_pick.get("epoch")
        mv = rec_pick.get("movements")
        print(
            f"[trek] clock {clock:g}s, epoch {ep}, movement {mv}: "
            f"evaluating {fam} {rung} (high {est}, best at {rec_pick.get('best')})"
        )
        if key in done:
            continue  # already measured at THIS clock (a resume's replay guard)
        print(
            f"[trek] #{n + 1} pair={key} -> {fam} {rung} (sweeping {n_kv * n_kv} kv combinations)"
        )
        recs = run_pair(fam, rung, models_dir, state, port)
        # THE WALK LOG: each step's pick (with the strategy that made
        # it, the estimate it acted on, and the realized score) rides
        # the state - the replayable record of exactly what the
        # walker did and why, and the checkpoint's raw material
        done_recs = [r for r in recs if r.get("result") == "done"]
        pick_score = (
            max((r.get("high_score") or -1 for r in done_recs), default=-1) if done_recs else -1
        )
        state.setdefault("walk", []).append(
            {
                "row": rec_pick.get("row"),
                "col": rec_pick.get("col"),
                "index": pair_key,
                "fam": fam,
                "rung": rung,
                "clock_s": rec_pick.get("clock_s", 1.0),
                "draws": rec_pick.get("draws", 0),
                "direction": rec_pick.get("direction"),
                "epoch": rec_pick.get("epoch"),
                "seed": rec_pick.get("seed"),
                "movements": rec_pick.get("movements"),
                "high_score_before": rec_pick.get("high_score"),
                "best_before": rec_pick.get("best"),
                "score": pick_score,
                "n_recs": len(recs),
            }
        )
        state["walk"] = state["walk"][-4000:]  # bounded
        # THE RESUME-SAFE EXTEND: the resumed records are ALREADY in
        # state["results"] (run_pair persisted them per combo), so
        # only the records NOT yet in the state extend it - the
        # fresh-sweep path (recs == all new) appends all, the
        # resumed path appends only what actually ran
        have = {
            (r.get("fam"), r.get("rung"), r.get("k_quant"), r.get("v_quant"), r.get("seed"))
            for r in state["results"]
        }
        for r in recs:
            k = (r.get("fam"), r.get("rung"), r.get("k_quant"), r.get("v_quant"), r.get("seed"))
            if k not in have:
                state["results"].append(r)
                have.add(k)
        state["results"] = state["results"][-5000:]  # the state stays bounded
        # INV: the done set only holds keys in the pool space, one
        # entry per swept pair, before the pair is marked done
        warn_contract(
            "inv",
            "driver.done_space",
            all(
                0 <= int(k.split("@")[0]) < len(pool)
                for k in done
                if "@" not in k or k.split("@")[0].lstrip("-").isdigit()
            ),
            "a done key outside the pool space",
        )
        warn_contract(
            "pre",
            "driver.pair_not_done",
            key not in done,
            f"the picked pair {key} was already in the done set (double sweep!)",
        )
        done.add(key)
        _GC_DONE_SET.add(key)
        state["done"] = sorted(done)
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
        print(f"[trek]   -> {summary}")
        # INV: THE STUCK-RETRY GUARD (the imatrix lesson): the same
        # (fam, rung, result, detail) signature repeating more than
        # twice means a stuck retry loop, not independent evidence -
        # the SameFileError flood produced 2,597 IDENTICAL failures
        # across 53 pairs before anyone looked. Warning only: we
        # decide whether it is our bug or our logic.
        sig_counts: dict[tuple, int] = {}
        for r in recs:
            if r.get("result") == "done":
                continue  # a done record is a SCORE, not a failure -
                # at the 1s clock every candidate scores -1 and 49
                # identical scores are NOT a stuck retry loop
            sig = (
                r.get("fam"),
                r.get("rung"),
                r.get("result"),
                (r.get("detail") or "")[:80],
            )
            sig_counts[sig] = sig_counts.get(sig, 0) + 1
        prior = {
            (
                r.get("fam"),
                r.get("rung"),
                r.get("result"),
                (r.get("detail") or "")[:80],
            )
            for r in state.get("results", [])[-2000:]
        }
        for sig, c in sig_counts.items():
            if sig in prior and c > 2:
                warn_contract(
                    "inv",
                    "driver.stuck_retry",
                    False,
                    f"{sig[0]} {sig[1]}: the failure '{sig[3]}' already fired "
                    f"before and repeats {c}x - a stuck retry loop, not evidence",
                )
        n += 1
        if on_progress is not None:
            try:
                on_progress(n)
            except Exception as e:
                print(f"[trek] progress push failed (ignored): {e}")
    print(f"[trek] the pool is drained: {len(done)} pairs, one chance each - complete")


if __name__ == "__main__":
    main()
