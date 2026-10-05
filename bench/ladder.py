"""bench.ladder -- the protocol-v4 ladder (session 39, addendum 15:
the full_benchmark.py refactor). The gallop + binary search to
1024-token resolution, the ceiling matrix and the scored rung.
Extracted verbatim."""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bench import cells as bench_cells
from bench import tournament as bench_tournament
from bench.cells import RUNG_BASE


def run_ladder(
    model: str,
    corpus: str,
    port: int = 8210,
    results_dir: str = "ladder-results",
    seed: int = 1024,
    max_rung: int | None = None,
    min_rung: int = RUNG_BASE,
    kv_quant_k: str | None = None,
    kv_quant_v: str | None = None,
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
        ok_s, sv = bench_cells.speed_pass(
            model, r, corpus, port, results_dir, kv_quant_k, kv_quant_v
        )
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
        if sv.get("launch_failed"):
            cell["launch_failed"] = True
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
        ok_f, fv = bench_cells.fwe_pass(model, r, results_dir, seed, port, kv_quant_k, kv_quant_v)
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
    # A LAUNCH failure (server never became healthy - bad flags, bad
    # build, OOM at load) is NOT a model score either, and it must not
    # be selectable: the run is FAILED with the reason (session 35,
    # addendum 7 - the false-zero selection bug).
    launch_failed = any(c.get("launch_failed") for c in rungs)
    if launch_failed:
        failed = True
        score = 0
        print(
            f"  {label}: FAILED - a server launch failed (bad flags/build or "
            "load-time crash); this is NOT a model score, the family stays "
            "unselected - fix the launch and re-run with --force"
        )
    if not launch_failed and (floor <= 0 or (ceiling is not None and ceiling < start)):
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
    flicker = bench_tournament.fwe_flicker(rungs)
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
        "launch_failed": launch_failed,
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
                "weights_gib": (cell.get("mem_census") or {}).get("weights_gib"),
                "context_gib": (cell.get("mem_census") or {}).get("context_gib"),
            }
    return {"depth": score, "worst_wps": None, "cold_cost_gib": None}
