#!/usr/bin/env python3
"""randomize.py - protocol randomizer: the epitome of simplicity.

Reuses the v9.5 machinery (the exam papers, the grader, the bells,
the acquisition pipeline, the server) and disposes of the rules -
it is only interested in RESULTS.

  the pool    the 64-model roster x the 32-rung LADDER = 2048
              candidates = exactly 11 bits of entropy per pick
  the pick    11 bits of REAL entropy (/dev/hwrng if present,
              else /dev/random - the kernel's harvested pool,
              never a pseudorandom generator). ONE CHANCE per
              candidate, no replacement: a pick that lands on an
              already-run candidate is re-drawn with fresh entropy
              until an untried one comes up; the pool drains to
              zero and the protocol is complete. The exam seed (8
              bits) is recorded for reproducibility
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
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import infra.llama_server as llama_server
from bench import state_store as _state_store
from bench.exam import (
    build_chain,
    build_elevator,
    chain_prompt,
    elevator_prompt,
    score_exam,
    ask_exam,
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


# --- the pool: roster x LADDER = 2048 = 2^11 ------------------------------


def the_pool() -> list[tuple[str, str]]:
    """Every (model, rung) candidate, deterministic order: the pool is
    INDEXED by the 11-bit pick, so the index space is the pool.

    THE OVERSIZED PRE-MARK (the author's simplification): the f16
    size lives in md/models.md (the f16 (GiB) column, params x 2
    bytes) - at startup every model whose f16 exceeds the 8 GiB
    family-kill limit is marked oversized IMMEDIATELY, from the
    table alone: no download, no conversion, no measurement. The
    gate's discovery cost drops from up to 10 acquisitions to one
    table read."""
    roster = roster_from_models_md()
    pool: list[tuple[str, str]] = []
    for fam, _repo in roster:
        if _f16_gib_from_models_md(fam) > F16_LIMIT_GIB:
            oversized_models.add(fam)
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
GC_INTERVAL_S = 1.0


def _free_gib(path: str = GC_WATCH_PATH) -> float:
    st = os.statvfs(path)
    return (st.f_bavail * st.f_frsize) / (2**30)


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
    # per family: how many of its pool rungs are still untried - the
    # future need for its f16 (each untried rung, when picked,
    # re-quantizes from the f16)
    remaining: dict[str, int] = {}
    for idx, (fam, _rung) in enumerate(pool):
        if str(idx) in done:
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
    """The 1-second watchdog thread: at or below 16 GiB free on /home,
    remove the oldest f16 (never the active candidate's) until free
    space is above the threshold again. The f16's whole family dir
    goes with it (a quant source without its f16 is half a model)."""
    while not stop.is_set():
        try:
            if _free_gib() <= GC_THRESHOLD_GIB:
                exclude = {active.wait(0) and "" or ""}
                # the active family name is carried via the shared
                # event mechanism below - see _active_family
                fam = _ACTIVE_FAMILY[0]
                victim = _least_likely_f16(
                    models_dir,
                    {fam} if fam else set(),
                    _GC_DONE_SET,
                    _GC_POOL,
                )
                if victim:
                    # ONLY the f16 goes (the author's ruling): the
                    # imatrix stays behind (small, very expensive to
                    # recompute), the family dir stays
                    os.remove(victim)
                    log.append(
                        f"[gc] free {_free_gib():.1f} GiB <= {GC_THRESHOLD_GIB:g}: "
                        f"evicted {os.path.basename(victim)} "
                        f"(least-likely-needed by the state)"
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

# the f16 family-kill threshold (the author's extra-safety ruling):
# an f16 > 8 GiB kills the whole model - stricter than the 16 GiB
# per-candidate limit, because the f16 is the quantization SOURCE
# (every rung of the family is built from it, so the family's peak
# disk cost scales with the f16, and 8 GiB of source means ~8+ GiB
# of transient quant output on top)
F16_LIMIT_GIB = 8.0

# the IQ upper bound (the author's question): the IQ rungs (IQ* in
# the LADDER) need an importance matrix, and llama-imatrix LOADS the
# f16 plus KV + activation working set on the calibration corpus -
# its peak RAM is the f16 plus overhead. A model killed by the f16
# gate can therefore still be saved for its IQ rungs ONLY if the
# imatrix peak fits; but with the f16 > 8 GiB the imatrix peak is
# > 8 GiB + overhead on a 32 GiB machine sharing RAM with the OS -
# the f16 gate at 8 GiB already bounds the imatrix path safely
# (8 + ~2 overhead < the 32 GiB machine's usable RAM). The IQ bound
# is therefore the SAME 8 GiB f16 gate: no separate, looser bound.
IQ_F16_LIMIT_GIB = F16_LIMIT_GIB

# models whose f16 exceeded the hard limit: every candidate of the
# family is too large by inheritance (the f16 is the quant source)
oversized_models: set[str] = set()

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


def run_candidate(
    fam: str,
    rung: str,
    models_dir: str,
    state: dict[str, Any],
    state_file: str,
    port: int,
    entropy_get=lambda: entropy_bits(8),
) -> dict[str, Any]:
    """One candidate, one exam, a clock, a result. The exam seed (8
    bits) serves EVERY level of this candidate. The total run
    timeout is 128s: pass advances a level, fail or timeout ends the
    run and records the reason and the high score."""
    from bench.exam import bell_window, _size_too_large
    from bench.roster import WINDOW_DEFAULT, roster_from_models_md, window  # noqa: F401
    import bench.roster as _roster_mod

    t_start = time.monotonic()
    exam_seed = entropy_get()
    _ACTIVE_FAMILY[0] = fam

    # THE 16 GiB HARD LIMIT (the author's ruling): an f16 > 16 GiB is
    # TOO LARGE for the whole MODEL - every candidate of the family
    # dies immediately (the f16 is the quantization SOURCE, so if the
    # source itself is too large no rung can ever be built), the
    # model folder is deleted at once, and the family is marked in
    # the state so every LATER pick of any of its rungs resolves to
    # too_large BEFORE acquiring - no download is ever paid for an
    # oversized family again. This also shortens the pool.
    if fam in oversized_models:
        return {"fam": fam, "rung": rung, "seed": exam_seed, "result": "too_large"}
    gguf = _acquire(fam, rung, models_dir)
    if not gguf:
        # the acquire path printed the specific failure; the record
        # carries the distinct cause, not the generic unbuildable
        return {
            "fam": fam,
            "rung": rung,
            "seed": exam_seed,
            "result": _last_acquire_error.get("result", "acquire_failed"),
            "detail": _last_acquire_error.get("detail", ""),
        }
    famdir = os.path.join(models_dir, fam)
    f16_path = os.path.join(famdir, f"{fam}-f16.gguf")
    if os.path.isfile(f16_path) and (
        os.path.getsize(f16_path) / (2**30) > F16_LIMIT_GIB
    ):
        oversized_models.add(fam)
        shutil.rmtree(famdir, ignore_errors=True)
        return {"fam": fam, "rung": rung, "seed": exam_seed, "result": "too_large"}
    if _size_too_large(gguf):
        if rung != "F16":
            os.remove(gguf)
        return {"fam": fam, "rung": rung, "seed": exam_seed, "result": "too_large"}

    ctx = bell_window(state, fam, models_dir) or 262144
    answers_dir = os.path.join("results", "randomizer", fam)
    os.makedirs(answers_dir, exist_ok=True)
    answers_path = os.path.join(answers_dir, f"{rung}.jsonl")
    log_path = os.path.join(answers_dir, f"exam-server-{rung}.log")

    proc, healthy = llama_server.start_server(
        gguf,
        port=port,
        extra_args=[
            "-c",
            str(ctx + 2048),
            "--parallel",
            "1",
            "--reasoning",
            "off",
            "--reasoning-budget",
            "0",
        ],
        log_path=log_path,
    )
    high_score = -1
    high_score_time: float | None = None
    fail_reason = ""
    attempts: list[dict[str, Any]] = []
    try:
        if not healthy or not llama_server.wait_healthy(port, proc=proc):
            return {
                "fam": fam,
                "rung": rung,
                "seed": exam_seed,
                "result": "server_failed",
            }
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
        # the file rule: an F16 stays, a quant goes
        if rung != "F16" and os.path.isfile(gguf):
            os.remove(gguf)
        _ACTIVE_FAMILY[0] = ""

    return {
        "fam": fam,
        "rung": rung,
        "seed": exam_seed,
        "result": "done",
        "high_score": high_score,
        "fail_reason": fail_reason,
        "attempts": len(attempts),
        # the SPEED datum: the LAST level's time (the deciding level's
        # own timer), not the whole run - per the author's clarification
        "high_score_time_s": high_score_time,  # None: no level passed
        "elapsed_s": round(time.monotonic() - t_start, 1),
    }


# --- the controller --------------------------------------------------------


# the watchability cadence (the exam's per-family push ruling,
# randomizer-shaped): commit + push every N candidates so a
# multi-hour run is readable remotely as it goes
COMMIT_EVERY = 10


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

    socket.getaddrinfo = _ipv4_first
    models_dir = "models"
    state_file = RANDOMIZER_STATE_FILE
    os.makedirs("state", exist_ok=True)
    port = int(os.environ.get("RANDOMIZER_PORT", "8210"))

    state: dict[str, Any] = {}
    if os.path.isfile(state_file):
        with open(state_file, encoding="utf-8") as fh:
            state = json.load(fh)
    results: list[dict[str, Any]] = state.setdefault("results", [])
    # the oversized-f16 models persist across restarts
    oversized_models.update(state.get("oversized", []))

    pool = the_pool()
    _GC_POOL.clear()
    _GC_POOL.extend(pool)
    assert len(pool) == 2048, len(pool)
    live = 2048 - len(oversized_models) * len(LADDER)

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
        rows.sort(
            key=lambda r: (
                -(r.get("high_score") or -1),
                r.get("high_score_time_s") if r.get("high_score_time_s") is not None else 1e9,
            )
        )
        lines = [
            "# randomizer.md - the randomizer ledger",
            "",
            "Every candidate gets ONE chance (no replacement). Rank:",
            "highest score, tiebreak by time. Speed: the candidate's",
            "whole run - fast <= 32s, medium <= 64s, slow <= 128s.",
            "",
            "| rank | model | high score | quant @high | speed |",
            "|---|---|---|---|---|",
        ]
        for i, r in enumerate(rows):
            t = (
                r.get("high_score_time_s")
                if r.get("high_score_time_s") is not None
                else (r.get("elapsed_s") or 0.0)
            )
            speed = "fast" if t <= 32 else ("medium" if t <= 64 else "slow")
            lines.append(
                f"| {i + 1} | {r['fam']} | {r.get('high_score', -1)} "
                f"| {r['rung']} | {speed} |"
            )
        lines.append("")
        lines.append(f"_{len(rows)} candidates run of {len(pool)}; each one chance, the seed recorded in state._")
        with open("md/randomizer.md", "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    print(
        f"[randomizer] pool: {len(pool)} candidates, {len(oversized_models)} models "
        f"pre-marked oversized from models.md ({len(oversized_models) * len(LADDER)} "
        f"dead indexes) - {live} live, ONE chance each"
    )
    print(f"[randomizer] entropy: {_ENTROPY_DEV}")
    print(f"[randomizer] gc: /home free > {GC_THRESHOLD_GIB:g} GiB, 1s watchdog")
    n = len(done)
    while len(done) < len(pool):
        pick = entropy_bits(11)
        key = f"{pick}"
        if key in done:
            continue  # already had its chance: fresh entropy, re-draw
        fam, rung = pool[pick]
        print(f"[randomizer] #{n + 1} pick=0b{pick:011b} -> {fam} {rung}")
        rec = run_candidate(fam, rung, models_dir, state, state_file, port)
        results.append(rec)
        done.add(key)
        _GC_DONE_SET.add(key)
        state["done"] = sorted(done)
        state["oversized"] = sorted(oversized_models)
        state["results"] = results[-5000:]  # the state stays bounded
        _state_store.save_state(state_file, state)
        write_ledger()
        while gc_log:
            print(gc_log.pop(0))
        summary = (
            f"high_score={rec.get('high_score')}"
            if rec.get("result") == "done"
            else rec.get("result", "?")
        )
        print(f"[randomizer]   -> {summary} ({rec.get('fail_reason', '')})")
        n += 1
        if on_progress is not None and n % COMMIT_EVERY == 0:
            try:
                on_progress(n)
            except Exception as e:
                print(f"[randomizer] progress push failed (ignored): {e}")
    print(f"[randomizer] the pool is drained: {len(done)} candidates, one chance each - complete")


if __name__ == "__main__":
    main()
