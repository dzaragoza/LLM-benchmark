#!/usr/bin/env python3
"""full_benchmark.py -- the end-to-end benchmark orchestrator.

One command: acquire each family's GGUF at the rung (default Q8_0, --rung
overrides; addendum 86 removed the WALK, not the choice of rung),
then run the PROTOCOL v4 ladder (speed gate + FWE per rung, addendum 4)
and print the depth-scored ladder table - the study's ranking. This
script owns the orchestration only - state/resume and the final results
file. Each stage lives in its own dedicated script:

  hf_download.py  every Hugging Face interaction - premade rung file,
                  f16 GGUF, or safetensors snapshot.
  convert_quant.py  everything that touches llama.cpp conversion tooling
                  - safetensors -> f16, f16 -> rung.
  speed_gate.py   the speed gate - the llama-server bench interface,
                  dumps, and the protocol v3.1 stall-rate verdict.
  ruler_gate.py   the FWE (frequent-words-extraction) cell.

  STAGE A (phases 1-4, per family, fixed Q8_0 rung):
    1. DOWNLOAD - premade rung file or the data to create it later.
    2. CREATE   - convert safetensors -> f16, quantize f16 -> rung.
    3. LADDER   - protocol v4: gallop 2x from the min rung, then binary
                  search to 1024-token resolution (speed gate + FWE at
                  every rung, the ceiling matrix 3.1/3.2/3.3, window
                  from the launch banners).
    4. SCORE    - the scored-rung row (worst-turn w/s + cold cost).

Everything is IDEMPOTENT and RESUMABLE: the state file is rewritten
after every phase; rerun the same command to resume. Files are never
re-downloaded/re-quantized. Every failure stops the script with reader
guidance.

ARC is RETIRED (session 34, addendum 22: the FWE ladder "demolishes arc
as a measurement" - the depth score is the ranking; arc_eval.py and
mcnemar.py are removed with it).

Hybrid non-thinking mode (--no-thinking): for hybrid models in the
non-thinking category - benchmarks with thinking disabled
(chat_template_kwargs enable_thinking=false).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import convert_quant
import hf_download
import llama_server
import ruler_gate
import speed_gate
import tee_output

# session 34 (addendum 32): the ladder floor is 4096 - the corpus's
# structural floor (the worst conversation's side is ~2,670 tokens +
# depth headroom + the noise reserve: 2048 cannot host it even
# blob-less, so below 4096 the speed gate measures nothing, it just
# fences - the 1k-grid HTTP 400s were exactly this)
RUNG_BASE = 4096
MIN_RUNG_FAIL = 16384  # session 34 (addendum 19): a floor below the start
# rung means a base failure - the model is out, pending investigation


def kill_stale_server() -> None:
    """Session 34 (addendum 19, refinement 1): the pkill moves into the
    instrument. A stale llama-server would hold the port and the RAM;
    the sweep's own launches replace whatever was there."""
    r = subprocess.run(
        ["pkill", "-f", "llama-server"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if r.returncode == 0:
        print("  [0] stale llama-server killed (pkill -f llama-server)")
    else:
        print("  [0] no stale llama-server found")


def _banner_window(log_path: str) -> int | None:
    """The trained window read from a server launch's own banner (session
    34, addendum 19, refinement 2): when llama-server caps the requested
    -c DOWN to the training window it prints the cap line. Returns None
    when the log shows no cap. THE PROBE IS GONE - the gallop's own
    launches double the -c until the cap line appears, and the first
    capped -c IS the ceiling (search below it)."""
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            log = f.read()
    except OSError:
        return None
    m = re.search(r"training context of the model \((\d+)\)", log)
    if m is None:
        m = re.search(r"n_ctx_train\s*=\s*(\d+)", log)
    if m is None:
        return None
    return int(m.group(1))


# midpoint rungs: 8k, 12k, 16k, 24k, 32k, 48k, 64k (addendum 7 corrected)
RUNG_MIDPOINT = True


def speed_pass(
    model: str,
    rung: int,
    corpus: str,
    port: int,
    results_dir: str,
    kv_quant: str | None = None,
) -> tuple[bool, dict[str, Any]]:
    """One speed-gate cell at ctx=rung, n=1 conversation: real blob,
    real turns, the v3.1 verdict from those turns only (reduced rules:
    a screen, not a podium number). bench_model launches the server
    itself (banner guard included); the verdict is the REAL analyze()
    on a temp dump - the phase-4 code path, not a re-implementation.
    Session 34 (addendum 19, refinement 2): the launch's banner is
    read for the training-window cap - when the server caps -c DOWN
    to n_ctx_train the rung is ABOVE the window, and the caller makes
    it the ceiling (the window itself is the search bound, not a
    benched rung)."""
    dropped = llama_server.drop_file_cache(model)
    if not dropped:
        print("    note: cache drop unavailable - cost may read warm (137k)")
    turns, _, mem_reports = speed_gate.bench_model(
        model,
        corpus,
        port,
        rung,
        False,
        True,
        n_conversations=1,
        kv_quant=kv_quant,
    )
    # the launch's banner: when the server capped the -c DOWN to the
    # trained window, bench_model's banner guard refused to bench (no
    # turns) - the window rides in the verdict either way (addendum 19)
    server_log = os.path.join(
        os.path.dirname(model) or ".", os.path.basename(model) + ".server.log"
    )
    window_cap = _banner_window(server_log)
    floor_hit = next((t for t in turns if t.get("error") == "rung below conversation floor"), None)
    if floor_hit is not None:
        print(
            f"    rung {rung}: below the conversation floor - the speed "
            "gate cannot run here (structural, addendum 31)"
        )
        return False, {"error": "rung below conversation floor", "window_cap": window_cap}
    if not turns:
        if window_cap is not None and window_cap < rung:
            print(f"    trained window {window_cap:,} caps the requested -c {rung:,}")
            return False, {"error": "capped to the window", "window_cap": window_cap}
        return False, {"error": "no turns measured", "window_cap": window_cap}
    label = os.path.splitext(os.path.basename(model))[0]
    dump = os.path.join(results_dir, f"{label}-rung{rung}-speed.json")
    with open(dump, "w") as f:
        json.dump(turns, f)
    verdict = speed_gate.analyze(model, no_thinking=True, dump_override=dump)
    verdict["window_cap"] = window_cap if (window_cap or 0) < rung else None
    cost = next(
        (m["mem_cost_gib"] for m in mem_reports if m.get("mem_cost_gib") is not None),
        None,
    )
    verdict["mem_cost_gib"] = cost
    # session 34 (addendum 18, refinement 3): the v4.2 speed verdict.
    # >= 7.5 w/s: clean pass. 5 <= w < 7.5: pass, but this rung is the
    # CEILING - the gallop stops here (every deeper rung is slower).
    # < 5: fail (below the reader line).
    stall_ok = verdict.get("stall_rate", 1.0) <= speed_gate.STALL_RATE_MAX
    worst = verdict.get("worst")
    if not stall_ok:
        return False, verdict
    if worst is not None and worst < 5.0:
        return False, verdict
    verdict["ceiling_rung"] = worst is not None and worst < 7.5
    return True, verdict


def fwe_pass(
    model: str,
    rung: int,
    results_dir: str,
    seed: int,
    port: int,
    kv_quant: str | None = None,
) -> tuple[bool, dict[str, Any]]:
    """One FWE cell at depth=rung-2x headroom, n=1, on its own server
    launch at exactly the rung's ctx (ruler_gate's launch shape: one
    slot, banner guard). Session 34 (addendum 19): the launch's banner
    is read for the window cap too - the ladder's fwe-only midpoints
    (refinement 1.5) launch no speed server, so this is where a window
    between midpoints is caught."""
    label = os.path.splitext(os.path.basename(model))[0]
    depth = rung - 2 * ruler_gate.ANSWER_HEADROOM
    csv_path = os.path.join(results_dir, f"{label}-{depth}-fwe.csv")
    if os.path.exists(csv_path):
        os.remove(csv_path)
    log_path = os.path.join(results_dir, f"{label}-rung{rung}-fwe-server.log")
    llama_server.drop_file_cache(model)
    mem_before = llama_server.system_memavailable_gib()
    extra_args = ["-c", str(rung), "--parallel", "1"]
    if kv_quant:
        extra_args += ["-fa", "--cache-type-k", kv_quant, "--cache-type-v", kv_quant]
    proc, healthy = llama_server.start_server(
        model,
        port=port,
        extra_args=extra_args,
        log_path=log_path,
    )
    try:
        if not healthy or not llama_server.wait_healthy(port, proc=proc):
            print("    ERROR: fwe server did not come up; log tail:")
            try:
                with open(log_path, encoding="utf-8", errors="replace") as f:
                    for ln in f.read().splitlines()[-15:]:
                        print(f"    [server] {ln}")
            except OSError:
                pass
            return False, {"error": "fwe server did not come up", "depth": depth}
        row = ruler_gate.run_fwe_depth(
            port, label, depth, 1, csv_path, seed0=seed, no_thinking=True
        )
        row["window_cap"] = _banner_window(log_path)
        smaps = llama_server.mapped_memory_gib(proc)
        if smaps is not None:
            row["mem_census"] = smaps
            print(
                f"    fwe census: {smaps['resident_gib']:.2f} GiB resident "
                f"(file {smaps['file_gib']:.2f} + anon {smaps['anon_gib']:.2f}; smaps)"
            )
        cost = llama_server.memory_cost_gib(mem_before, llama_server.system_memavailable_gib())
        if cost is not None:
            row["mem_cost_gib"] = cost
    finally:
        llama_server.stop_server(proc, port)
    return row["acc"] == 1.0, row


def fwe_flicker(rungs: list[dict[str, Any]]) -> tuple[int, int] | None:
    """The flicker rule (session 34, addendum 31, ruling b): FWE
    verdicts must be MONOTONE - depth only gets harder. Returns the
    (deep_pass, shallow_fail) rung pair when a run passes FWE at a
    deep rung but FAILS at a shallower one (an n=1 boundary
    coin-flip, the addendum-29 flicker), else None. Works on any
    ladder's rungs list - a live run_ladder result OR one re-read
    from a state file (cross-grid flicker: the Qwen3-4B shape, a
    2048 fail next to a 16384 pass)."""
    fwe_cells = [c for c in rungs if c.get("fwe_pass") is not None]
    for deep in fwe_cells:
        if deep["fwe_pass"] is not True:
            continue
        for shallow in fwe_cells:
            if shallow["rung"] < deep["rung"] and shallow["fwe_pass"] is False:
                return deep["rung"], shallow["rung"]
    return None


def run_ladder(
    model: str,
    corpus: str,
    port: int = 8210,
    results_dir: str = "ladder-results",
    seed: int = 1024,
    max_rung: int | None = None,
    min_rung: int = RUNG_BASE,
    kv_quant: str | None = None,
) -> dict[str, Any]:
    """One model's PROTOCOL v4.3 ladder (session 34 addendum 19): the
    gallop (2x steps) finds the floor and the ceiling, then a binary
    search finds the true value. THE PROBE IS GONE: the window is read
    from the gallop's own launch banners - the first -c the server
    caps down is ABOVE the window, so the window becomes the ceiling
    and the search runs below it. The floor rule (refinement 4): any
    ceiling below the start rung marks the run FAILED - the model is
    out pending investigation. Returns {"model", "score", "failed",
    "wall_min", "rungs"}. The scored rung's speed_worst_wps is the
    137n w/s anchor; its mem_cost_gib is the 137m cold cost anchor."""
    label = os.path.splitext(os.path.basename(model))[0]
    print(f"\n=== ladder: {label} ===")
    os.makedirs(results_dir, exist_ok=True)
    if not os.path.exists(model):
        print(f"  SKIP: file not found ({model}) - fix the path and re-run")
        return {
            "model": label,
            "score": None,
            "failed": False,
            "wall_min": 0.0,
            "rungs": [],
            "error": "file not found",
        }
    print(f"  gallop from {min_rung} in 2x steps, then binary search (protocol v4.3)")
    start = min_rung
    rung = min_rung
    rungs: list[dict[str, Any]] = []
    model_t0 = time.monotonic()

    def cell_for(r: int) -> dict[str, Any]:
        cell = next((c for c in rungs if c["rung"] == r), None)
        if cell is None:
            cell = {
                "rung": r,
                "speed_pass": None,  # not measured (refinement 3.2/3.3)
                "speed_worst_wps": None,
                "mem_cost_gib": None,
                "ceiling_rung": False,
            }
            rungs.append(cell)
        return cell

    def run_speed(r: int) -> tuple[dict[str, Any], int | None]:
        """Bench the speed gate at rung r. Returns (cell, window_cap):
        window_cap is the trained window when the server capped the -c
        DOWN (the rung is ABOVE the window - the window is the ceiling,
        this rung is not scored)."""
        cell = cell_for(r)
        t0 = time.monotonic()
        ok_s, sv = speed_pass(model, r, corpus, port, results_dir, kv_quant)
        t_speed = time.monotonic() - t0
        tag = " (ceiling)" if sv.get("ceiling_rung") else ""
        print(
            f"  rung {r}: speed {'PASS' if ok_s else 'FAIL'}{tag} [{t_speed:.0f}s]",
            flush=True,
        )
        cost = sv.get("mem_cost_gib")
        if cost is not None:
            print(f"    cold machine cost @ rung: {cost:.2f} GiB")
        cell.update(
            speed_pass=ok_s,
            speed_worst_wps=sv.get("worst"),
            mem_cost_gib=cost,
            speed_s=t_speed,
            ceiling_rung=bool(sv.get("ceiling_rung")),
        )
        if not ok_s:
            print(f"    speed verdict: {json.dumps(sv)[:200]}")
        cap = sv.get("window_cap")
        if cap is not None:
            print(
                f"    trained window {cap:,} caps the requested -c {r:,} - "
                "the window is the ceiling"
            )
        return cell, cap

    def run_fwe(r: int) -> tuple[dict[str, Any], int | None]:
        """Bench FWE at rung r. Returns (cell, window_cap)."""
        cell = cell_for(r)
        t0 = time.monotonic()
        ok_f, fv = fwe_pass(model, r, results_dir, seed, port, kv_quant)
        t_fwe = time.monotonic() - t0
        print(
            f"    fwe @ depth {fv.get('depth')}: "
            f"{fv.get('correct')}/{fv.get('n', 1)} -> "
            f"{'PASS' if ok_f else 'FAIL'} [{t_fwe:.0f}s]",
            flush=True,
        )
        cell.update(
            fwe_pass=ok_f,
            fwe_correct=fv.get("correct"),
            fwe_s=t_fwe,
        )
        if cell.get("mem_cost_gib") is None and fv.get("mem_cost_gib") is not None:
            cell["mem_cost_gib"] = fv["mem_cost_gib"]
        if fv.get("mem_census") is not None:
            cell["mem_census"] = fv["mem_census"]
        return cell, fv.get("window_cap")

    # ---- STAGE 1: the gallop (2x steps) - find the floor and the ceiling.
    # Ceiling kinds (session 34, addendum 19, refinements 3.1-3.3/4):
    #   speed < 5 w/s            -> ceiling; the search KEEPS measuring speed
    #   5 <= speed < 7.5         -> ceiling; speed NOT measured anymore
    #   speed >= 7.5 + fwe FAIL  -> ceiling; speed NOT measured anymore
    #   window cap (banner)      -> ceiling; speed NOT measured anymore
    floor = 0
    ceiling: int | None = None
    measure_speed = True  # the search measures speed only after a <5 fail
    failed = False
    while True:
        if measure_speed:
            cell, cap = run_speed(rung)
            if cap is not None:
                ceiling = cap
                measure_speed = False
                break
            if not cell["speed_pass"]:
                # 3.1: a <5 w/s fail - fwe is NOT run at this rung; the
                # search below measures speed again at every midpoint
                ceiling = rung
                break
            if cell["ceiling_rung"]:
                # 3.2: 5<=w<7.5 - this rung may still pass fwe (the
                # floor); deeper is slower, so nothing above is searched
                fwe_cell, fwe_cap = run_fwe(rung)
                if fwe_cap is not None:
                    ceiling = fwe_cap
                    measure_speed = False
                    if fwe_cell["fwe_pass"]:
                        floor = rung
                    break
                if fwe_cell["fwe_pass"]:
                    floor = rung
                    measure_speed = False
                    ceiling = None
                    break
                ceiling = rung
                measure_speed = False
                break
        fwe_cell, fwe_cap = run_fwe(rung)
        if fwe_cap is not None:
            ceiling = fwe_cap
            measure_speed = False
            if fwe_cell["fwe_pass"]:
                floor = rung
            break
        if not fwe_cell["fwe_pass"]:
            # 3.3: speed >= 7.5 passed here - midpoints pass it too
            ceiling = rung
            measure_speed = False
            break
        floor = rung
        if max_rung and rung >= max_rung:
            break
        rung = rung * 2

    score = floor
    # ---- STAGE 2: the binary search to the true value (1024 resolution).
    # Speed is measured at a midpoint only when the ceiling was a <5
    # fail (refinement 3.1); a 5-7.5 ceiling, an FWE ceiling, or a
    # window ceiling all had speed pass at or below their rung.
    if ceiling is not None and floor > 0:
        lo, hi = floor, ceiling  # lo passes both, hi fails (or is capped)
        mode = "speed+fwe" if measure_speed else "fwe only"
        print(f"  binary search between {lo} (pass) and {hi} (fail) - {mode}")
        while hi - lo > 1024:
            mid = (lo + hi) // 2
            mid = (mid // 1024) * 1024  # keep rungs on 1024-token boundaries
            if mid <= lo or mid >= hi:
                break
            if measure_speed:
                # 3.1: a <5 speed fail set the ceiling - speed is unknown
                # at the midpoints, so it is measured FIRST (a midpoint
                # that fails speed must not be scored, whatever fwe did)
                sc, sc_cap = run_speed(mid)
                if sc_cap is not None:
                    hi = min(sc_cap, hi)  # the window bounds from above
                    continue
                if not sc["speed_pass"]:
                    hi = mid
                    continue
            cell, cap = run_fwe(mid)
            if cap is not None:
                hi = min(cap, hi)  # the window bounds the search from above
                continue
            if cell["fwe_pass"]:
                lo = mid
            else:
                hi = mid
        score = lo

    # ---- the floor rule (refinement 4): any ceiling below the start
    # rung is a BASE FAILURE - not a score, a flag for the author.
    if floor <= 0 or (ceiling is not None and ceiling < start):
        failed = True
        score = 0
        why = ceiling if ceiling is not None else floor
        print(
            f"  {label}: FAILED - the ceiling ({why:,}) is at or below "
            f"the {start:,} start rung; the model is out pending investigation"
        )

    # ---- the flicker rule (session 34, addendum 31, ruling b): FWE
    # verdicts must be MONOTONE - depth only gets harder. A run that
    # passes FWE at a deep rung but FAILS at a shallower one is an
    # n=1 boundary coin-flip (the addendum-29 flicker), and the whole
    # ladder is INVALID: no score is recorded, the family re-benches.
    flicker = fwe_flicker(rungs)
    invalid_reason = None
    if flicker:
        invalid_reason = (
            f"fwe flicker: pass at {flicker[0]:,} but fail at {flicker[1]:,} "
            "- non-monotone n=1 boundary coin-flip; the run is invalid, re-bench"
        )
        failed = True
        score = 0
        print(f"  {label}: INVALID - {invalid_reason}")
    wall_min = (time.monotonic() - model_t0) / 60.0
    print(
        f"  {label}: SCORE = {score} tokens (last rung passing both) "
        f"[{wall_min:.1f} min wall, measured]"
    )
    ladder = {
        "model": label,
        "score": score,
        "failed": failed,
        "wall_min": wall_min,
        "rungs": rungs,
        "file_gib": round(os.path.getsize(model) / (1024**3), 3),
    }
    if invalid_reason:
        ladder["invalid"] = True
        ladder["invalid_reason"] = invalid_reason
    return ladder


def scored_row(ladder: dict[str, Any]) -> dict[str, Any]:
    """The 137n/137m picker row from a run_ladder result: the scored
    rung's (depth, worst-span w/s, cold cost), or unranked."""
    score = ladder.get("score") or 0
    for cell in ladder.get("rungs", []):
        if cell["rung"] == score and score:
            return {
                "depth": score,
                "worst_wps": cell.get("speed_worst_wps"),
                "cold_cost_gib": cell.get("mem_cost_gib"),
                "resident_gib": (cell.get("mem_census") or {}).get("resident_gib"),
            }
    return {"depth": score, "worst_wps": None, "cold_cost_gib": None}


QUANTIZE_BIN = convert_quant.QUANTIZE_BIN
CORPUS_DEFAULT = speed_gate.CORPUS_DEFAULT
MODELS_DIR_DEFAULT = "./models"
STATE_FILE_DEFAULT = "./benchmark-state.json"
RESULTS_FILE_DEFAULT = "./benchmark-results.json"
# Q4_0 removed (author ruling, addendum 37): Q4_K_M is the single 4-bit
# rung - "there's a q4_0 that's unnecessary since we have q4_k_m".
# Addendum 86: the rung WALK is removed - one rung per run.
# The study's default rung stays Q8_0; --rung overrides it (session
# 34: the Q4 quants - context dominates this bw class, so the smaller
# file with the deeper ladder is the hypothesis to test).
RUNG_DEFAULT = "Q8_0"
READER_WPS_DEFAULT = speed_gate.READER_WPS_DEFAULT
SERVER_BIN = llama_server.find_server()

local_rung = hf_download.local_rung
list_repo_files = hf_download.list_repo_files
GUIDE = {}
GUIDE[1] = hf_download.GUIDE[1]
GUIDE[2] = convert_quant.GUIDE[2]
GUIDE[3] = speed_gate.GUIDE[3]
GUIDE[4] = speed_gate.GUIDE[4]
fail = hf_download.fail


# =========================================================== timestamps
# Addendum 78, item 4: every phase line carries a wall-clock stamp and
# the elapsed sweep time - run 1's log had no durations, so every time
# estimate had to be bracketed from commit times.
_SWEEP_T0 = time.time()


def stamp(msg: str) -> None:
    elapsed_min = (time.time() - _SWEEP_T0) / 60.0
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')} +{elapsed_min:.0f}m] {msg}")


# --dry-run read-only guard (addendum 79): set in main(); save_state
# checks it so a pre-flight never mutates the state file.
DRY_RUN_ACTIVE = False


# =========================================================== estimator
# Addendum 83: the dry-run run-time estimate. Pure: state in, counts
# and minutes out. Extracted from main() for the test suite
# (addendum 87) - the classification-order rule (f16 BEFORE download)
# is the bug class the tests pin.

PLAN_COST_MIN = {
    "local": 15,
    "download": 30,
    "f16_quantize": 45,
    "convert_quantize": 60,
    "unknown": 45,
}


def classify_plan(plan: str) -> str:
    """One acquisition plan string -> its cost class."""
    if plan.startswith("local file"):
        return "local"
    if "f16 from" in plan:
        return "f16_quantize"
    if plan.startswith("download "):
        return "download"
    if "safetensors from" in plan or "pytorch_model.bin from" in plan:
        return "convert_quantize"
    return "unknown"


def estimate_runtime(state: dict[str, Any]) -> tuple[dict[str, int], int]:
    """State -> (plan_counts, total_min). Infeasible cells excluded."""
    counts, total = {}, 0
    for fst in state.get("families", {}).values():
        for run in fst.get("runs", {}).values():
            plan = run.get("plan", "") or ""
            verdict = run.get("verdict", "") or ""
            if not plan or verdict.startswith("FAIL (infeasible"):
                continue
            cls = classify_plan(plan)
            counts[cls] = counts.get(cls, 0) + 1
            total += PLAN_COST_MIN[cls]
    return counts, total


# =========================================================== state


def load_state(path: str) -> dict[str, Any]:
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return {"families": {}}


def save_state(path: str, state: dict[str, Any]) -> None:
    # --dry-run is a READ-ONLY pre-flight (addendum 79): a dry run must
    # never write the state file, or the pre-flight-then-real-run way
    # of working would poison the real run (phases marked done with no
    # file on disk). Guarded here at the single choke point.
    if DRY_RUN_ACTIVE:
        return
    with open(path, "w") as f:
        json.dump(state, f, indent=1)


# =========================================================== selection


def process_family(
    spec: str,
    corpus: str,
    models_dir: str,
    state: dict[str, Any],
    state_path: str,
    dry_run: bool,
    force: bool,
    thinking: bool = False,
    no_thinking: bool = False,
    reader_wps: float = READER_WPS_DEFAULT,
    rung: str = RUNG_DEFAULT,
) -> None:
    model_repo, _, source_repo = spec.partition("=")
    if not source_repo:
        source_repo = model_repo
    fam = os.path.basename(model_repo.rstrip("/"))
    famdir = os.path.join(models_dir, fam)
    fst = state["families"].setdefault(fam, {"spec": spec, "runs": {}, "selected": None})

    print()
    print("=" * 60)
    stamp(f"family: {fam}")
    print(f"  model repo : {model_repo}")
    print(f"  source repo: {source_repo}")
    print(f"  folder     : {famdir}")
    if fst["selected"] and not force:
        s = fst["runs"][fst["selected"]]
        # worst is None for a floor-rule-failed family (score 0 has no
        # scored rung) - the resume print must not format it (the
        # lineage-2 run's TypeError, addendum 27)
        worst_txt = "n/a" if s.get("worst") is None else f"{s['worst']:.1f}"
        print(
            f"  already selected: {fst['selected']} "
            f"({s['verdict']}, worst {worst_txt} t/s) - skipping "
            "(--force to redo)"
        )
        return
    if force:
        # --force re-benches: clear every rung's verdict and phases 3-4
        # (phases 1-2 stay done - the rung files exist and are reused;
        # the dumps are re-measured because speed_gate.bench gets force
        # too). Without this, the fixed-rung pass below would skip on the
        # STORED verdicts and --force would silently do nothing past
        # the family-level check (addendum 42).
        cleared = 0
        for run in fst["runs"].values():
            run["phases_done"] = [p for p in run.get("phases_done", []) if p in (1, 2)]
            if run.pop("verdict", None) is not None:
                cleared += 1
        fst["selected"] = None
        save_state(state_path, state)
        print(f"  --force: re-benching {rung} ({cleared} stored verdict(s) cleared; files reused)")

    # Stale-state guard (addendum 43): a stored rung file can vanish
    # from disk (folder deleted/moved) while benchmark-state.json still
    # marks phases 1-2 done. Trusting the state then crashes phase 3
    # with a bare FileNotFoundError. Invalidate those phases so the
    # walk re-acquires (re-download/re-quantize; both stages are
    # idempotent) instead of benching a path that is not there.
    for run in fst["runs"].values():
        f = run.get("file")
        if f and not os.path.isfile(f):
            run["phases_done"] = []
            run.pop("file", None)
            run.pop("plan", None)
            save_state(state_path, state)
            print(
                f"  stored rung file missing on disk ({f}) - "
                "phases 1-2 invalidated; will re-acquire"
            )

    # Session 34 (addendum 4): the LOCAL SHORTCUT. If the rung file is
    # already on disk, acquisition is DONE - no hub listing needed (the
    # author's models/ tree is the common case; the v4 WoW runs local
    # files). The hub is only a real dependency when the file must be
    # downloaded or converted.
    local_path = local_rung(famdir, rung)
    if local_path and 1 not in (fst["runs"].get(rung, {}).get("phases_done", [])):
        run = fst["runs"].setdefault(rung, {"phases_done": []})
        run["plan"] = "local file"
        run["file"] = local_path
        if 1 not in run["phases_done"]:
            run["phases_done"].append(1)
        if 2 not in run["phases_done"]:
            run["phases_done"].append(2)
        save_state(state_path, state)
        print(f"  [1] local rung file found - no download needed  ({local_path})")
        print(f"  [2] rung file ready  ({local_path})")
    model_files: list[str] = []
    source_files: list[str] = []
    if not local_path:
        hf_download.require_hub()
        assert list_repo_files is not None  # require_hub exits when the hub is missing
        try:
            model_files = list_repo_files(model_repo)
            source_files = (
                model_files if source_repo == model_repo else list_repo_files(source_repo)
            )
        except Exception as e:
            fail(1, "-", f"cannot list repo files for {model_repo}: {e}", GUIDE[1])

    run = fst["runs"].get(rung, {"phases_done": []})
    fst["runs"][rung] = run
    if str(run.get("verdict", "")).startswith("PASS") or run.get("verdict") == "FAIL":
        return
    print(f"\n  rung {rung}:")
    if 1 not in run["phases_done"]:
        path, plan = hf_download.acquire(
            fam, famdir, rung, model_repo, model_files, source_repo, source_files, dry_run
        )
        run["plan"] = plan
        run["phases_done"].append(1)
        save_state(state_path, state)
        print(f"  [1] downloads ok  (plan: {plan})")
        stamp("      phase 1 done (acquire)")
        if plan.startswith("infeasible"):
            run["verdict"] = "FAIL (infeasible: exceeds system RAM)"
            run["rung"] = rung
            save_state(state_path, state)
            return
    if 2 not in run["phases_done"]:
        path = convert_quant.create(fam, famdir, rung, run.get("plan", ""), dry_run)
        if path:
            run["file"] = path
        run["phases_done"].append(2)
        save_state(state_path, state)
        print(f"  [2] rung file ready  ({run.get('file', 'dry run')})")
        stamp("      phase 2 done (create)")
    path = run.get("file") or local_rung(famdir, rung)
    if dry_run:
        print(f"  [3] would run the PROTOCOL v4 ladder on {path or 'the rung file'}")
        print(
            "  [4] would record the ladder score (the deepest rung passing both; "
            "scored-rung w/s + cold cost per addendum 137n/137m)"
        )
        return
    assert path is not None  # real runs: phases 1-2 guarantee it
    # Session 34 (addendum 4): the 50-conv corpus wall is REPLACED
    # by the PROTOCOL v4 ladder as the family's bench. Per rung:
    # speed gate (n=1) then FWE (n=1); both pass -> score advances;
    # either fails -> the ladder stops. The verdict is the ladder
    # SCORE (0 = the counting floor / speed cliff at the base
    # rung). The corpus-wall phases 3-4 are retired (the author:
    # "we don't do 50 conv turns. We do run fwe as in ladder-bench").
    if 3 not in run["phases_done"] or force:
        ladder = run_ladder(
            path,
            corpus,
            port=state.get("ladder_port", 8210),
            results_dir=os.path.join(models_dir, "ladder-results"),
            seed=state.get("ladder_seed", 1024),
            min_rung=state.get("ladder_min_rung", RUNG_BASE),
            kv_quant=state.get("kv_quant"),
        )
        run["ladder"] = ladder
        run["phases_done"].append(3)
        save_state(state_path, state)
        print(f"  [3] ladder ok  (score: {ladder['score']} tokens)")
        stamp("      phase 3 done (ladder)")
    if 4 not in run["phases_done"]:
        # phase 4: the scored-rung row (the 137n/137m anchors)
        ladder = run.get("ladder")
        if ladder and ladder.get("invalid"):
            # the flicker rule (addendum 31): a non-monotone FWE run
            # scores NOTHING - the verdict is invalid, not a depth
            run["verdict"] = f"INVALID ({ladder.get('invalid_reason', 'fwe flicker')})"
            run["rung"] = rung
            run["score"] = 0
            run["invalid"] = True
            run["invalid_reason"] = ladder.get("invalid_reason")
            run["phases_done"].append(4)
            save_state(state_path, state)
            stamp("      phase 4 done (invalid - flicker)")
            return
        if ladder:
            row = scored_row(ladder)
            run["verdict"] = f"PASS (ladder score {ladder['score']} tokens)"
            run["rung"] = rung
            run["score"] = ladder["score"]
            run["worst"] = row["worst_wps"]
            run["mem_cost_gib"] = row["cold_cost_gib"]
            run["phases_done"].append(4)
            save_state(state_path, state)
            worst_txt = "n/a" if row["worst_wps"] is None else f"{row['worst_wps']:.1f}"
            cost_txt = "n/a" if row["cold_cost_gib"] is None else f"{row['cold_cost_gib']:.2f}"
            print(
                f"  [4] scored-rung row: depth {row['depth']} tokens, "
                f"worst {worst_txt} w/s, cold cost {cost_txt} GiB"
            )
            stamp("      phase 4 done (scored row)")
    if str(run.get("verdict", "")).startswith("PASS"):
        fst["selected"] = rung
        run["rung"] = rung
        save_state(state_path, state)
        print(f"  SELECTED {rung} for {fam} (ladder score {run.get('score')} tokens)")


# =========================================================== main


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="end-to-end benchmark: acquire each family's Q8_0 "
        "rung and run the protocol v4 ladder - the depth-scored "
        "ladder table is the ranking"
    )
    ap.add_argument(
        "families", nargs="+", help='family specs: "model_repo" or "model_repo=source_repo"'
    )
    ap.add_argument("--corpus", default=CORPUS_DEFAULT)
    ap.add_argument(
        "--reader-wps",
        type=float,
        default=READER_WPS_DEFAULT,
        help="the k=1 guarantee line in WORDS per second: "
        "worst turn at the reference depth must never "
        "fall below this (default 5.0 w/s = 300 wpm, "
        "Brysbaert 2019 - match the fast reader)",
    )
    ap.add_argument("--models-dir", default=MODELS_DIR_DEFAULT)
    ap.add_argument("--state-file", default=STATE_FILE_DEFAULT)
    ap.add_argument("--results-file", default=RESULTS_FILE_DEFAULT)
    ap.add_argument(
        "--rung",
        default=RUNG_DEFAULT,
        help="the quant to benchmark (default Q8_0; e.g. Q4_K_M - session 34's "
        "context-over-parameters test)",
    )
    ap.add_argument(
        "--roster",
        default=None,
        help="restrict the run's notes to these families "
        "(comma-separated, as named in the family specs); "
        "the state file accumulates across studies "
        "(addendum 41/56)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="READ-ONLY pre-flight (addendum 79): lists "
        "every repo, verifies tooling, runs the "
        "RAM/disk feasibility checks and reports each "
        "family's acquisition plan WITHOUT downloading, "
        "converting, benching or touching the state "
        "file. THE WAY OF WORKING: always run the "
        "command with --dry-run first, read the "
        "pre-flight report, then issue it without.",
    )
    ap.add_argument(
        "--force", action="store_true", help="redo families that already have a selection"
    )
    ap.add_argument(
        "--kv-quant",
        default=None,
        choices=["q8_0", "q4_0"],
        help="session 35: quantize the KV cache (K and V both) to this type - "
        "launches with -fa (required for quantized caches). Rides the state "
        "file (kv_quant) so every rung of the ladder launches the same way; "
        "use a FRESH --state-file/--results-file pair so the variant never "
        "contaminates the baseline grids.",
    )
    ap.add_argument(
        "--thinking",
        action="store_true",
        help="thinking-model category: benchmark with "
        "thinking enabled (same worst-turn gate; "
        "reasoning measured descriptively). Use separate "
        "--state-file/--results-file for this category.",
    )
    ap.add_argument(
        "--no-git",
        action="store_true",
        help="skip the git tail (session 34 addendum 15: the "
        "commit-and-push of the run's artifacts is now DEFAULT - "
        "the git interface is layer 3, like the hub and llama.cpp; "
        "the old --git-commit opt-in is superseded)",
    )
    ap.add_argument(
        "--min-rung",
        type=int,
        default=None,
        help="session 34 (addendum 9/10): the ladder's first rung "
        "(default: the protocol v4 base 8192); stored in the state "
        "as ladder_min_rung so every subsequent run of the family "
        "climbs the same grid",
    )
    ap.add_argument(
        "--no-thinking",
        action="store_true",
        help="hybrid models, non-thinking category: "
        "run with thinking disabled (chat-template "
        "kwargs enable_thinking=false; first-turn dump "
        "check confirms no reasoning appears)",
    )
    return ap


def main() -> None:
    tee_output.install()
    ap = build_parser()
    args = ap.parse_args()
    global DRY_RUN_ACTIVE
    DRY_RUN_ACTIVE = args.dry_run

    if args.thinking and args.no_thinking:
        ap.error("--thinking and --no-thinking are mutually exclusive")

    check_requirements()
    if not args.dry_run:
        kill_stale_server()
        check_tooling(args)

    state = load_state(args.state_file)
    if args.min_rung:
        state["ladder_min_rung"] = args.min_rung
    if args.kv_quant:
        state["kv_quant"] = args.kv_quant

    if not args.families:
        ap.error("no family specs given")

    failed_families = sweep_families(args, state)

    # Session 34 (addendum 4): the ladder is the bench; the scored
    # table prints from the ladder results in state (ARC and the
    # McNemar ranking are retired - addendum 22).
    if args.dry_run:
        # session 34 (addendum 36): a dry run WRITES results.txt (the tee
        # is installed from the first line) - it must be committed and
        # pushed like a real run's, so the git tail runs before the exit
        if not args.no_git:
            tee_output.uninstall()  # stop writing before committing
            git_tail(args)
        sys.exit(preflight_report(args, state, failed_families))
    roster = prepare_roster(args)
    report_roster_notes(args, state, roster, failed_families)
    print_ladder_table(state)
    write_results(args, state)
    write_results(args, state)

    # ---- addendum 78, item 5 / session 34 addendum 15: the git tail -
    # commit and push every artifact the study needs, force-added past
    # the .gitignore. Now DEFAULT (the author: "do the git work in full
    # benchmark. layer 3 is the right place to have a git interface,
    # same as the hugging face interface and the llama-cpp interface");
    # --no-git opts out.
    if not args.no_git:
        tee_output.uninstall()  # results.txt is complete - stop writing before it is committed
        git_tail(args)
    stamp("run complete")


REQ_PACKAGES = [
    "huggingface_hub",
    "transformers",
    "torch",
    "safetensors",
    "numpy",
    "gguf",
    "sentencepiece",
    "protobuf",
    "pandas",
    "pyarrow",
    "hf_transfer",
]


def check_requirements() -> None:
    """Verify every requirements.txt package the run needs is importable
    in THIS interpreter - the dry run included (the author: "I had to
    restart our latest run because I forgot to enable the venv"). The
    interpreter's own path is printed first so the wrong-venv (or
    system-python) case is visible at a glance; a missing package is a
    hard stop BEFORE any download or bench work begins."""
    from importlib.metadata import PackageNotFoundError, version

    print(f"  python : {sys.executable}")
    missing = []
    for name in REQ_PACKAGES:
        try:
            version(name)
        except PackageNotFoundError:
            missing.append(name)
    if missing:
        sys.exit(
            "missing python packages in this interpreter: "
            + ", ".join(missing)
            + " - interpreter: "
            + sys.executable
            + " - activate the study venv and/or: python3 -m pip install -r requirements.txt"
        )


def check_tooling(args: argparse.Namespace) -> None:
    """Verify the run's tooling (real runs only; addendum 79)."""

    for path, msg in [
        (
            args.corpus,
            f"corpus not found at {args.corpus} - build it: python3 speed_gate.py --make-corpus",
        ),
        (
            QUANTIZE_BIN,
            f"llama-quantize not found at {QUANTIZE_BIN} - place the b10964 build in the repo root",
        ),
        (
            "./llama.cpp/convert_hf_to_gguf.py",
            "converter not found - the llama.cpp checkout must be in the repo root",
        ),
        (SERVER_BIN or "", "llama-server not found - place the b10964 build in the repo root"),
    ]:
        if not os.path.isfile(path):
            sys.exit(msg)


def sweep_families(args: argparse.Namespace, state: dict[str, Any]) -> list[tuple[str, str]]:
    """Phase A: bench every family (per-family isolation, addendum 78)."""
    # Addendum 78, item 4: per-family isolation IN THE TOOL - a family
    # that dies (conversion OOM, unsupported architecture, a bad repo)
    # is recorded and the sweep CONTINUES; the author's "continue even
    # in failure" made structural, no shell wrapper needed.
    failed_families = []
    for spec in args.families:
        try:
            process_family(
                spec,
                args.corpus,
                args.models_dir,
                state,
                args.state_file,
                args.dry_run,
                args.force,
                args.thinking,
                args.no_thinking,
                args.reader_wps,
                args.rung,
            )
        except SystemExit as e:
            failed_families.append((spec, str(e) or "exit"))
            stamp(f"FAMILY FAILED: {spec} (recorded; the sweep continues - addendum 78)")
        except Exception as e:  # isolation is the point
            failed_families.append((spec, repr(e)))
            stamp(f"FAMILY FAILED: {spec} - {e!r} (recorded; the sweep continues - addendum 78)")
    return failed_families


def preflight_report(
    args: argparse.Namespace, state: dict[str, Any], failed_families: list[tuple[str, str]]
) -> int:
    """The --dry-run read-only report (addendum 79) + estimate (83).
    Returns the process exit code: 1 iff any family failed (author
    ruling, addendum 108 - the pre-flight is a scriptable gate)."""
    if args.dry_run:
        print()
        print("=" * 60)
        stamp("DRY RUN COMPLETE - READ-ONLY PRE-FLIGHT REPORT")
        print(f"  families checked : {len(args.families)}")
        print(
            f"  rung             : {args.rung} (one rung per run - addendum 86; --rung overrides)"
        )
        # Addendum 83: the run-time estimate. Per-cell costs from the
        # run-1 measurement (the qwen overnight sweep, ~8.5 h for 7
        # cells, acquisition-dominated), split by acquisition-plan
        # class. Pre-registered brackets, converted to measurements as
        # sweep 2's stamps land.
        plan_counts, total_min = estimate_runtime(state)
        if plan_counts:
            print("  run-time estimate (run-1 brackets by acquisition class):")
            for cls in ("local", "download", "f16_quantize", "convert_quantize", "unknown"):
                if cls in plan_counts:
                    print(
                        f"    {cls:16s} x{plan_counts[cls]:2d} "
                        f"@ ~{PLAN_COST_MIN[cls]} min = "
                        f"{plan_counts[cls] * PLAN_COST_MIN[cls]:4d} min"
                    )
            lo = round(total_min / 60)
            hi = round(total_min * 1.3 / 60)
            print(
                f"    TOTAL: ~{lo}-{hi} h for {len(args.families)} "
                "families (acquisition dominates; the v4 ladder "
                "cost scales with how deep each model climbs)"
            )
        if failed_families:
            print(
                f"  FAILED families  : {len(failed_families)} of "
                f"{len(args.families)} - fix these BEFORE the real "
                f"run (the sweep would skip them):"
            )
            for spec, err in failed_families:
                print(f"    {spec}: {err}")
        else:
            print(
                "  failures         : none - every family's plan "
                "verified (repos exist, sizes estimated, "
                "RAM/disk feasible)"
            )
        print()
        print("  The state file was NOT modified and no files were downloaded (addendum 79).")
        print("  If the report is clean, issue the SAME command without")
        print("  --dry-run to start the real run.")
        return 1 if failed_families else 0
    return 0


def prepare_roster(args: argparse.Namespace) -> list[str]:
    """The run's roster: the families named in this command (addendum 41/56)."""
    if args.roster:
        return [f.strip() for f in args.roster.split(",")]
    return [os.path.basename(s.partition("=")[0].rstrip("/")) for s in args.families]


def report_roster_notes(
    args: argparse.Namespace,
    state: dict[str, Any],
    roster: list[str],
    failed_families: list[tuple[str, str]],
) -> None:
    """The roster missing-note and the failed-families note."""
    if roster is not None:
        missing = [
            f
            for f in roster
            if f not in state.get("families", {}) or not state["families"][f].get("selected")
        ]
        if missing:
            print(
                f"  note: roster families without a selection "
                f"(excluded from the ranking): {', '.join(missing)}"
            )
    if failed_families:
        print()
        stamp("families failed this run (isolated; state preserved):")
        for spec, err in failed_families:
            print(f"  {spec}: {err}")


def print_ladder_table(state: dict[str, Any]) -> None:
    """The v4 ladder table (session 34, addendum 4): every benched
    family's ladder score with its scored-rung row (the 137n/137m
    anchors), sorted by depth - the ranking output of the merged
    full benchmark."""
    rows = []
    for fam, fst in state["families"].items():
        for rung, run in fst.get("runs", {}).items():
            lad = run.get("ladder")
            if lad is None:
                continue
            row = scored_row(lad)
            rows.append(
                (
                    lad["score"] or 0,
                    fam,
                    rung,
                    row["worst_wps"],
                    row["cold_cost_gib"],
                    lad["wall_min"],
                    bool(lad.get("failed")),
                )
            )
    if not rows:
        print("\nno ladder results in state - nothing benched yet")
        return
    print()
    print("=" * 60)
    stamp("PROTOCOL v4 ladder table (depth score; n=1 screen - addendum 137h)")
    for score, fam, _rung, wps, cost, wall, failed in sorted(rows, key=lambda r: (-r[0], r[1])):
        wps_txt = "n/a" if wps is None else f"{wps:.1f}"
        cost_txt = "n/a" if cost is None else f"{cost:.2f}"
        flag = "  FAILED (below the start rung - investigate)" if failed else ""
        print(
            f"  {fam:36s} score {score:>7,} tokens | "
            f"scored-rung worst {wps_txt:>5s} w/s | cold {cost_txt:>5s} GiB | "
            f"{wall:.1f} min{flag}"
        )


def write_results(args: argparse.Namespace, state: dict[str, Any]) -> None:
    """The results file: everything for later analysis."""
    # ---- results file: everything for later analysis
    results = []
    for fam, fst in state["families"].items():
        history = [dict(r, rung=rung) for rung, r in fst["runs"].items()]
        history.sort(key=lambda r: r["rung"])
        sel = fst["selected"]
        results.append(
            {
                "family": fam,
                "spec": fst["spec"],
                "history": history,
                "selected": (dict(fst["runs"][sel], rung=sel) if sel else None),
            }
        )
    doc = {"selection": results}
    with open(args.results_file, "w") as f:
        json.dump(doc, f, indent=1)
    print(f"\nresume state -> {args.state_file}")
    print(f"all data     -> {args.results_file}")


def print_wt_table(state: dict[str, Any]) -> None:
    """The per-model w/t calibration table (addendum 78, item 4)."""
    # ---- addendum 78, item 4: the per-model w/t calibration inline
    # (the addendum-74 lesson: grading waited on a manual extraction).
    # Single-sourced from speed_gate.analyze's own fields, already in
    # the state - no dump re-parsing, no second extraction pass.
    print()
    print("=" * 60)
    stamp("per-model w/t calibration (the gate's own p05 rule)")
    for fam, fst in state["families"].items():
        for rung, run in fst.get("runs", {}).items():
            if run.get("words_per_token_p05") is None:
                continue
            print(
                f"  {fam:36s} {rung:6s} "
                f"n={run.get('n_turns', 0):4d} "
                f"min={run.get('words_per_token_min') or 0:.3f} "
                f"p05={run['words_per_token_p05']:.3f} "
                f"mean={run.get('words_per_token') or 0:.3f}"
            )


# =========================================================== git tail


def git_tail(args: argparse.Namespace) -> None:
    stamp("committing artifacts to git (state, results, dumps, mem sidecars)")
    paths = [args.state_file, args.results_file, "results.txt"]
    # per-turn dumps + mem sidecars: the grading instrument's raw data
    # (p05, Delta, stall attribution, gen_words, memory shape) - small
    # JSON, force-added past the models/ ignore (addendum 78).
    paths += (
        glob.glob("models/*/*.live-dump*.json")
        + glob.glob("models/*/*.sentinel*.json")
        + glob.glob("models/*/*.mem.json")
    )
    # session 34 addendum 15: the ladder's raw data rides too - the
    # speed/fwe dumps and the window-probe logs (the addendum-6 cap's
    # evidence), plus the ruler CSVs.
    paths += (
        glob.glob("models/*/ladder-results/*")
        + glob.glob("ladder-results/*")
        + glob.glob("ruler-results/*")
    )
    existing = [p for p in paths if os.path.exists(p)]
    if not existing:
        stamp("nothing to commit - no artifacts found")
        return
    r = subprocess.run(["git", "add", "-f", "--"] + existing, capture_output=True, text=True)
    if r.returncode != 0:
        stamp(f"git add failed: {r.stderr.strip()}")
        return
    r = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if r.returncode == 0:
        stamp("nothing new to commit")
        return
    msg = (
        f"benchmark artifacts {time.strftime('%Y-%m-%d %H:%M')} "
        "(addendum 78 auto-commit): state, results, per-turn dumps, "
        "mem sidecars, ladder dumps"
    )
    r = subprocess.run(["git", "commit", "-m", msg], capture_output=True, text=True)
    if r.returncode != 0:
        stamp(f"commit failed: {r.stderr.strip()}")
        return
    stamp(f"committed: {r.stdout.strip().splitlines()[0]}")
    r = subprocess.run(["git", "push"], capture_output=True, text=True)
    if r.returncode != 0:
        stamp(f"push failed: {r.stderr.strip()} - run: git push")
    else:
        stamp("pushed")


if __name__ == "__main__":
    main()
