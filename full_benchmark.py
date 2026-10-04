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
import csv
import glob
import json
import math
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
    kv_quant_k: str | None = None,
    kv_quant_v: str | None = None,
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
        kv_quant_k=kv_quant_k,
        kv_quant_v=kv_quant_v,
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
        return False, {
            "error": "no turns measured (server launch failed)",
            "launch_failed": True,
            "window_cap": window_cap,
        }
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
    kv_quant_k: str | None = None,
    kv_quant_v: str | None = None,
    min_words: int = 1,
) -> tuple[bool, dict[str, Any]]:
    """One FWE cell at depth=rung-2x headroom, n=1, on its own server
    launch at exactly the rung's ctx (ruler_gate's launch shape: one
    slot, banner guard). Session 34 (addendum 19): the launch's banner
    is read for the window cap too - the ladder's fwe-only midpoints
    (refinement 1.5) launch no speed server, so this is where a window
    between midpoints is caught."""
    label = os.path.splitext(os.path.basename(model))[0]
    depth = rung - 2 * ruler_gate.ANSWER_HEADROOM
    os.makedirs(results_dir, exist_ok=True)
    csv_path = os.path.join(results_dir, f"{label}-{depth}-fwe.csv")
    if os.path.exists(csv_path):
        os.remove(csv_path)
    log_path = os.path.join(results_dir, f"{label}-rung{rung}-fwe-server.log")
    llama_server.drop_file_cache(model)
    mem_before = llama_server.system_memavailable_gib()
    extra_args = ["-c", str(rung), "--parallel", "1"]
    # session 35, addendum 8: separate K/V (the combined flag is gone);
    # -fa takes a value on this build: "-fa on"
    if kv_quant_k or kv_quant_v:
        extra_args += ["-fa", "on"]
        if kv_quant_k:
            extra_args += ["--cache-type-k", kv_quant_k]
        if kv_quant_v:
            extra_args += ["--cache-type-v", kv_quant_v]
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
            port,
            label,
            depth,
            1,
            csv_path,
            seed0=seed,
            no_thinking=True,
            min_words=min_words,
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


def speed_cell(
    model: str,
    rung: int,
    corpus: str,
    results_dir: str,
    run: int,
    port: int,
    kv_quant_k: str | None = None,
    kv_quant_v: str | None = None,
) -> tuple[bool, dict[str, Any]]:
    """One speed-gate cell (session 38, addendum 2 - the redesigned
    gate): conversation `run` of the 21-conversation corpus, played on
    its own server at exactly the rung's ctx. The record is the stall
    count: how many of the conversation's turns stalled the reader
    (the binary per-turn event, the addendum-55/73 collision test).
    Gold bar = 0 stalls (the perfect record); the count is stored per
    cell (the speed analogue of FWE's x/3 and VT's x/5) so any bar can
    be re-graded later without re-measuring. Returns (passed_at_gold,
    record)."""
    label = os.path.splitext(os.path.basename(model))[0]
    os.makedirs(results_dir, exist_ok=True)
    turns, _, mem_reports = speed_gate.bench_model(
        model,
        corpus,
        port,
        rung,
        False,
        True,
        n_conversations=1,
        conversation_start=run - 1,
        kv_quant_k=kv_quant_k,
        kv_quant_v=kv_quant_v,
    )
    dump = os.path.join(results_dir, f"{label}-rung{rung}-speed-cell{run}.json")
    with open(dump, "w") as f:
        json.dump(turns, f)
    server_log = os.path.join(
        os.path.dirname(model) or ".", os.path.basename(model) + ".server.log"
    )
    window_cap = _banner_window(server_log)
    floor_hit = next((t for t in turns if t.get("error") == "rung below conversation floor"), None)
    if floor_hit is not None:
        return False, {"error": "rung below conversation floor", "window_cap": window_cap}
    if not turns or all(not t.get("server_wps") for t in turns):
        if window_cap is not None and window_cap < rung:
            return False, {"error": "capped to the window", "window_cap": window_cap}
        return False, {"error": "no turns measured", "launch_failed": True}
    bench_turns = [t for t in turns if t.get("deltas") is not None]
    stalls = sum(1 for t in bench_turns if t.get("reader_wall_fail"))
    record = {
        "stalls": stalls,
        "turns": len(bench_turns),
        "conv": run,
        "worst_wps": min(
            (t["server_wps"] for t in bench_turns if t.get("server_wps")), default=None
        ),
        "window_cap": window_cap,
    }
    return stalls == 0, record


def vt_pass(
    model: str,
    rung: int,
    results_dir: str,
    seed: int,
    port: int,
    kv_quant_k: str | None = None,
    kv_quant_v: str | None = None,
) -> tuple[bool, dict[str, Any]]:
    """One VT cell - the same launch shape as fwe_pass (own server at
    exactly the rung's ctx, banner guard, memory census), the task
    swapped: one variable-tracking chain (RULER's 1 chain x 4 hops,
    5 five-letter names), pass = ALL 5 names, the 0..5 partial is
    the graded diagnostic stored per cell (the VT analogue of the
    FWE x/3 word count)."""
    label = os.path.splitext(os.path.basename(model))[0]
    depth = rung - 2 * ruler_gate.ANSWER_HEADROOM
    os.makedirs(results_dir, exist_ok=True)
    csv_path = os.path.join(results_dir, f"{label}-{depth}-vt.csv")
    if os.path.exists(csv_path):
        os.remove(csv_path)
    log_path = os.path.join(results_dir, f"{label}-rung{rung}-vt-server.log")
    llama_server.drop_file_cache(model)
    mem_before = llama_server.system_memavailable_gib()
    extra_args = ["-c", str(rung), "--parallel", "1"]
    if kv_quant_k or kv_quant_v:
        extra_args += ["-fa", "on"]
        if kv_quant_k:
            extra_args += ["--cache-type-k", kv_quant_k]
        if kv_quant_v:
            extra_args += ["--cache-type-v", kv_quant_v]
    proc, healthy = llama_server.start_server(
        model,
        port=port,
        extra_args=extra_args,
        log_path=log_path,
    )
    try:
        if not healthy or not llama_server.wait_healthy(port, proc=proc):
            print("    ERROR: vt server did not come up; log tail:")
            try:
                with open(log_path, encoding="utf-8", errors="replace") as f:
                    for ln in f.read().splitlines()[-15:]:
                        print(f"    [server] {ln}")
            except OSError:
                pass
            return False, {"error": "vt server did not come up", "depth": depth}
        row = ruler_gate.run_vt_depth(
            port,
            label,
            depth,
            1,
            csv_path,
            seed0=seed,
            no_thinking=True,
        )
        row["window_cap"] = _banner_window(log_path)
        smaps = llama_server.mapped_memory_gib(proc)
        if smaps is not None:
            row["mem_census"] = smaps
            print(
                f"    vt census: {smaps['resident_gib']:.2f} GiB resident "
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


def tournament_rank(fall_depths: list[int | None], depths: list[int]) -> dict[str, Any]:
    """The sigma-only rank (session 37, addendum 10: the mode is
    RETIRED - the author's ruling, n selection is based on sigma
    only): fall_depths is one entry per climb - the depth where that
    climb ended (the first non-perfect cell), or None for a climb
    that topped out at the highest step (full hold). The rank is the
    WILSON-basis statistics alone: the per-rung pass vector, the
    reliable depth (1 sigma), the conservative depth (2 sigma), the
    ceiling, and the per-rung 1-sigma Wilson bounds. No central
    tendency of the fall depths is computed; a model is what it
    reliably holds, not what it most often fell at."""
    passes: dict[int, int] = {}
    for d in depths:
        passes[d] = sum(
            1 for fall in fall_depths if fall is None or (fall is not None and fall > d)
        )
    return _rank_extra(
        {
            "passes": passes,
            "fall_depths": fall_depths,
            "full_holds": sum(1 for fall in fall_depths if fall is None),
        },
        depths,
    )


def wilson_interval(k: int, n: int, z: float = 1.0) -> tuple[float, float]:
    """The Wilson score interval at 1 sigma (addendum 42): the
    honest CI for a binomial hold fraction at tournament n. At n=15
    a 2-sigma interval is too wide to separate models - 1 sigma is
    the pre-registered choice."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return center - half, center + half


def _rank_extra(rank: dict[str, Any], depths: list[int]) -> dict[str, Any]:
    """The addendum-42/43 recommendation statistics: reliable depth
    (the deepest rung whose 1-sigma LOWER Wilson bound on the hold
    probability is >= 0.5 - the rung holds FWE on most seeds, with
    1-sigma confidence), conservative depth (the same at 2 sigma -
    the claim that survives skeptical review; addendum 43, n=21 puts
    the 2-sigma certify bar at 15/21 observed holds), ceiling (the
    deepest rung held EVER), and the per-rung 1-sigma Wilson bounds."""
    n = len(rank["fall_depths"])
    passes = rank["passes"]
    floor = math.ceil(0.5 * n) if n else 0
    reliable = 0
    conservative = 0
    bounds: dict[int, tuple[float, float]] = {}
    for d in depths:
        k = passes[d]
        lo, hi = wilson_interval(k, n)
        bounds[d] = (round(lo, 3), round(hi, 3))
        if k >= floor and lo >= 0.5:
            reliable = d
        if k >= floor and wilson_interval(k, n, 2.0)[0] >= 0.5:
            conservative = d
    rank["reliable_depth"] = reliable
    rank["conservative_depth"] = conservative
    rank["wilson_bounds"] = bounds
    climb_max = [depths[-1] if f is None else f for f in rank["fall_depths"]]
    rank["ceiling"] = max(climb_max) if climb_max else 0
    return rank


def tournament_family(
    spec: str,
    models_dir: str,
    state: dict[str, Any],
    state_path: str,
    port: int,
    dry_run: bool,
) -> dict[str, Any]:
    """One family's tournament turn (session 36, addenda 10/11): five
    climbs of the dyadic FWE ladder at upstream parameters, SEED =
    CLIMB NUMBER, early stop at the first non-perfect cell. Runs at
    the family's SELECTED rung - the PASS config - with its stored
    KV quants (the 2B's Q4_K_M carries q5_0, per the state). The
    speed gate is ASSUMED passed (author ruling: known at 256k for
    all participants, falsified after the tournament if a ranking
    step needs it)."""
    model_repo, _, source_repo = spec.partition("=")
    fam = os.path.basename(model_repo.rstrip("/"))
    fst = state["families"].get(fam, {})
    entry = fst.get("tournament_entry") or {}
    rung = fst.get("selected") or entry.get("rung")
    if not rung:
        return {"family": fam, "error": "no selected rung - not a PASS family"}
    run = fst.get("runs", {}).get(rung, {})
    famdir = os.path.join(models_dir, fam)
    model = run.get("file") or entry.get("file") or local_rung(famdir, rung)
    if (not model or not os.path.isfile(model)) and entry:
        # addendum 29: the tournament acquires its own entry files -
        # the same phase-1 path the main run uses (wow.md: the author
        # runs one command, not a download step per model)
        try:
            model_files = hf_download.list_repo_files(model_repo)
            source_repo_eff = source_repo or model_repo
            source_files = (
                model_files
                if source_repo_eff == model_repo
                else hf_download.list_repo_files(source_repo_eff)
            )
            path, plan = hf_download.acquire(
                fam, famdir, rung, model_repo, model_files, source_repo_eff, source_files, dry_run
            )
            if dry_run:
                print(f"  entry file absent - dry run plan: {plan}")
            path = path or convert_quant.create(fam, famdir, rung, plan, dry_run)
            if path and os.path.isfile(path):
                model = path
                entry["file"] = path
                save_state(state_path, state)
        except Exception as e:
            return {"family": fam, "error": f"entry acquisition failed: {e}"}
    if not model or not os.path.isfile(model):
        return {"family": fam, "error": f"rung file not found ({model})"}
    kv_k = run.get("kv_quant_k") or entry.get("kv_quant_k") or state.get("kv_quant_k")
    kv_v = run.get("kv_quant_v") or entry.get("kv_quant_v") or state.get("kv_quant_v")
    depths = TOURNAMENT_DEPTHS
    print()
    print("=" * 60)
    stamp(f"tournament: {fam} ({rung})")
    print(f"  file: {model}")
    if entry and not fst.get("selected"):
        pred = entry.get("predicted_ram_gib")
        print(
            f"  ENTRY CONFIG (predicted, addendum 16): {rung} + K/V "
            f"{kv_k or 'f16'}/{kv_v or 'f16'}" + (f" - predicted RAM {pred} GiB" if pred else "")
        )
    if dry_run:
        for s in range(1, TOURNAMENT_CLIMBS + 1):
            print(
                f"  would climb {s}/{TOURNAMENT_CLIMBS}: depths "
                f"{' '.join(str(d) for d in depths)} (seed {s}, early stop)"
            )
        return {"family": fam, "rung": rung, "dry_run": True}
    results_dir = os.path.join(models_dir, "tournament-results", fam)
    os.makedirs(results_dir, exist_ok=True)
    # addendum 37: the tournament is RESUMABLE - each climb's fall is
    # persisted in the family state (seed = climb number), so adding
    # climbs (5 -> 7) runs only the new seeds, never the old ones
    state["families"].setdefault(fam, fst)
    saved: dict[str, int | None] = dict(fst.get("tournament_falls") or {})
    fall_depths: list[int | None] = []
    for s in range(1, TOURNAMENT_CLIMBS + 1):
        key = str(s)
        if key in saved:
            fall_depths.append(saved[key])
            print(
                f"  climb {s}/{TOURNAMENT_CLIMBS}: RESUMED - "
                f"{'topped out' if saved[key] is None else f'fell at {saved[key]:,} tok'}"
            )
            continue
        climb_dir = os.path.join(results_dir, f"climb{s}")
        os.makedirs(climb_dir, exist_ok=True)
        fall = None
        for d in depths:
            row = fwe_pass(
                model,
                d + 2 * ruler_gate.ANSWER_HEADROOM,
                climb_dir,
                seed=s,
                port=port,
                kv_quant_k=kv_k,
                kv_quant_v=kv_v,
            )
            ok, fv = row
            words = fv.get("words_found", [fv.get("correct", 0)])
            partial = words[0] if words else 0
            print(
                f"  climb {s}/{TOURNAMENT_CLIMBS} @ {d} tok: "
                f"{partial}/{ruler_gate.FWE_TOP_K} words -> "
                f"{'HOLD' if ok else 'FALL'}"
            )
            if not ok:
                fall = d
                print(f"  CLIMB OVER at {d} tok (climb {s})")
                break
        if fall is None:
            print(f"  climb {s}/{TOURNAMENT_CLIMBS}: TOPPED OUT at {depths[-1]} tok")
        fall_depths.append(fall)
        saved[key] = fall
        fst["tournament_falls"] = saved
        save_state(state_path, state)
    rank = tournament_rank(fall_depths, depths)
    print(
        f"  {fam}: sigma rank - reliable {rank['reliable_depth']:,} "
        f"(1 sigma) | conservative {rank['conservative_depth']:,} "
        f"(2 sigma) | ceiling {rank['ceiling']:,} tokens "
        f"(falls: {[f if f else 'top' for f in fall_depths]})"
    )
    print(
        f"  {fam}: reliable depth {rank['reliable_depth']:,} tokens "
        f"(P>=0.5 at 1 sigma) | conservative {rank['conservative_depth']:,} "
        f"(2 sigma) | ceiling {rank['ceiling']:,} tokens"
    )
    return {
        "family": fam,
        "rung": rung,
        "model": model,
        "kv_quant_k": kv_k,
        "kv_quant_v": kv_v,
        "corpus": CORPUS_DEFAULT,
        **rank,
    }


def diagnose_fwe(models_dir: str, state: dict[str, Any]) -> None:
    """Session 37, addendum 9: the per-rank diagnostic - which of the
    three expected words does a partial pass actually find? Reads the
    climb cell CSVs (task rows carry the answer text and the rank-
    ordered top_k list; the zeta law makes rank 1 the ~4x/9x more
    frequent word, so a 1/3 pass that only ever finds rank 1 is a
    WEAKER claim than the threshold suggests). Also reports the pass
    rate at every threshold (>=1, >=2, 3 of 3) per family per rung:
    measure once, grade later."""
    import re as _re

    print("=" * 60)
    stamp("FWE DIAGNOSTIC (per-rank found; pass rates by threshold)")
    for fam, _fst in sorted((state.get("families") or {}).items()):
        results_dir = os.path.join(models_dir, "tournament-results", fam)
        if not os.path.isdir(results_dir):
            continue
        rank_found = [0, 0, 0]
        partials = [0, 0, 0, 0]
        cells = 0
        for climb_dir in sorted(os.listdir(results_dir)):
            cpath = os.path.join(results_dir, climb_dir)
            if not os.path.isdir(cpath) or not climb_dir.startswith("climb"):
                continue
            for name in os.listdir(cpath):
                if not name.endswith("-fwe.csv"):
                    continue
                with open(os.path.join(cpath, name), encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        ans = r.get("answer") or ""
                        top_k = (r.get("top_k") or "").split(";")
                        if not ans or not top_k or ans.startswith("ERROR"):
                            continue
                        clean = _re.sub(r"\s+", "", ans)
                        found = [i for i, w in enumerate(top_k) if w and w in clean]
                        cells += 1
                        partials[min(len(found), 3)] += 1
                        for i in found:
                            rank_found[i] += 1
        if not cells:
            continue
        print(f"  {fam}: {cells} cells (climb CSVs)")
        for i, c in enumerate(rank_found):
            print(f"    rank-{i + 1} word found in {c}/{cells} cells ({c / cells:.0%})")
        p1 = partials[1] + partials[2] + partials[3]
        p2 = partials[2] + partials[3]
        p3 = partials[3]
        print(
            f"    pass >=1/3: {p1}/{cells} ({p1 / cells:.0%}) | "
            f">=2/3: {p2}/{cells} ({p2 / cells:.0%}) | "
            f"3/3: {p3}/{cells} ({p3 / cells:.0%})"
        )
        if p1 and rank_found[0] / max(1, rank_found[0] + rank_found[1] + rank_found[2]) > 0.7:
            print(
                "    NOTE: found-words are overwhelmingly rank-1 - "
                "the >=1/3 claim is mostly 'finds the most frequent word'"
            )


def _climb_csv_partial(
    models_dir: str | None, fam: str | None, climb: int, depth: int
) -> int | None:
    """The climb's committed FWE CSV holds the actual `partial` word
    count for cell (climb, depth); None means no CSV (the cell is
    unmeasured at this depth and stays dropped at a stricter bar)."""
    if not models_dir or not fam:
        return None
    cdir = os.path.join(models_dir, "tournament-results", fam, f"climb{climb}")
    if not os.path.isdir(cdir):
        return None
    matches = glob.glob(os.path.join(cdir, f"*-{depth}-fwe.csv"))
    if len(matches) != 1:
        return None
    try:
        with open(matches[0], newline="") as fh:
            rows = list(csv.DictReader(fh))
    except OSError:
        return None
    if len(rows) != 1:
        return None
    try:
        return int(rows[0]["partial"])
    except (KeyError, TypeError, ValueError):
        return None


def certify_cells(
    fst: dict[str, Any],
    depth: int,
    min_words: int = 1,
    models_dir: str | None = None,
    fam: str | None = None,
) -> dict[int, bool]:
    """Session 37, addendum 8: the CELL model - a cell is (model, run
    number, step) and is NEVER measured twice. The historical cells
    come from the saved tournament_falls: climb s measured every
    rung up to and including its fall (fall == first FAILING rung),
    so cell (s, depth) PASSED iff the fall is None (topped out) or
    deeper than the rung, FAILED iff the fall IS the rung, and is
    UNMEASURED iff the climb stopped below it. The direct cells
    (certify runs) live in fst["certify"][str(depth)] as {run: pass}
    (or {run: words_found} once cells record word counts).
    Returns {run: passed} for every MEASURED cell.

    Re-grading (session 37, the 2/3 tightening): a direct cell that
    stored an INTEGER word count is graded at >= min_words exactly;
    cells stored as booleans were graded under the old 1/3 rule and
    are dropped from the measured set at a stricter bar - they are
    re-run, never silently trusted. Inherited tournament-fall cells
    are re-graded from their committed climb CSV (the `partial`
    word count) when models_dir/fam are given: the fall only says
    pass/fail at 3/3, but the CSV holds the actual words found, so
    the cell is MEASURED, not guessed."""
    cells: dict[int, bool] = {}
    for key, fall in (fst.get("tournament_falls") or {}).items():
        if min_words > 1:
            csv_words = _climb_csv_partial(models_dir, fam, int(key), depth)
            if csv_words is not None:
                cells[int(key)] = csv_words >= min_words
            continue
        if fall is None or fall > depth:
            cells[int(key)] = True
        elif fall == depth:
            cells[int(key)] = False
    direct = (fst.get("certify") or {}).get(str(depth)) or {}
    for key, ok in direct.items():
        if isinstance(ok, bool):
            if min_words > 1:
                continue
            cells[int(key)] = ok
        else:
            cells[int(key)] = int(ok) >= min_words
    return cells


def speed_cells(fst: dict[str, Any], depth: int) -> dict[int, int]:
    """The redesigned speed gate's cell model (session 38, addendum 2):
    cell = (model, rung, conversation r), stored in certify_speed as
    {run: stall count}. Gold bar = 0 stalls; the counts re-grade at
    any 'at most x stalls' bar later without re-measuring."""
    direct = (fst.get("certify_speed") or {}).get(str(depth)) or {}
    return {int(r): int(p) for r, p in direct.items()}


def vt_cells(fst: dict[str, Any], depth: int) -> dict[int, int]:
    """The VT cell model: a cell is (model, run, task) and is NEVER
    measured twice. VT inherits NOTHING from the tournament (the
    climbs were FWE) - every cell is fresh, stored in the separate
    certify_vt namespace as {run: partial 0..5} (the graded score,
    like the FWE x/3 word count; pass = 5, re-gradable at any bar
    later without re-measuring)."""
    direct = (fst.get("certify_vt") or {}).get(str(depth)) or {}
    return {int(r): int(p) for r, p in direct.items()}


CERTIFY_LEVELS = ["at_least_one", "1_sigma", "2_sigma"]


def certify_rung(
    depth: int,
    level: str,
    specs: list[str],
    models_dir: str,
    state: dict[str, Any],
    state_path: str,
    port: int,
    dry_run: bool,
    min_words: int = 1,
    task: str = "fwe",
) -> list[dict[str, Any]]:
    """Session 37, addendum 8 (the practitioner-certified map): fill
    ONE rung - the sequential controller of session-36 addendum 50.
    Session 37, addendum 18: the certification TYPE is chosen per
    rung - at_least_one (the practitioner's question 1: any model
    with a pass at the step), 1_sigma (reliable: 1-sigma Wilson
    lower bound >= 0.5, count >= half of n=21) or 2_sigma
    (conservative: the same bar at 2 sigma). Candidates are the
    given families, ordered by promise (existing passes at the
    rung, then reliable depth). Each candidate is tested cell by
    cell (direct single-rung FWE at the rung, seed = the run
    number, cells already measured are NEVER re-run) until EARLY
    ACCEPT or EARLY REJECT (mathematically dead: even passing
    every remaining cell cannot reach the bar).
    The RAM-ceiling assumption replaces the w/s measurement
    (session 37, addendum 15): a config selected under the ceiling
    has enough bandwidth to clear the 5 w/s reader line - w/s is
    not measured in the benchmark (a waste of time; the author's
    ruling); a speed falsification probe stays available for later
    if a recommendation is ever doubted. The first accepted
    candidate ANSWERS the rung; the rest are skipped (the
    practitioner wants ONE model per rung)."""
    if level not in CERTIFY_LEVELS:
        raise ValueError(f"unknown certify level {level!r}")
    n_total = TOURNAMENT_CLIMBS
    floor = 1 if level == "at_least_one" else math.ceil(0.5 * n_total)
    z = 0.0 if level == "at_least_one" else float(level.split("_")[0])
    order: list[tuple[str, dict[str, Any], dict[int, bool]]] = []
    for spec in specs:
        fam = os.path.basename(spec.partition("=")[0].rstrip("/"))
        fst = state["families"].get(fam, {})
        if task == "vt":
            cells = {r: p >= 5 for r, p in vt_cells(fst, depth).items()}
        elif task == "speed":
            cells = {r: p == 0 for r, p in speed_cells(fst, depth).items()}
        else:
            cells = certify_cells(fst, depth, min_words, models_dir, fam)
        order.append((fam, fst, cells))

    def promise(item):
        fam, fst, cells = item
        k = sum(1 for ok in cells.values() if ok)
        saved_rank = state.get("tournament") or []
        rd = 0
        for tr in saved_rank:
            if tr.get("family") == fam:
                rd = tr.get("reliable_depth") or 0
        return (-k, -rd, fam)

    order.sort(key=promise)
    results: list[dict[str, Any]] = []
    answered = False
    for fam, fst, cells0 in order:
        cells = dict(cells0)
        measured = len(cells)
        k = sum(1 for ok in cells.values() if ok)
        entry = {
            "family": fam,
            "depth": depth,
            "level": level,
            "historical_passes": k,
            "historical_cells": measured,
        }
        print()
        print("-" * 60)
        print(f"  {fam}: {k}/{measured} cells measured, {n_total - measured} unmeasured")
        if answered:
            entry["skipped"] = "rung already answered"
            print("  SKIPPED - the rung is already answered")
            results.append(entry)
            continue
        famdir = os.path.join(models_dir, fam)
        rung = fst.get("selected") or (fst.get("tournament_entry") or {}).get("rung")
        run = (fst.get("runs") or {}).get(rung or "", {})
        model = (
            run.get("file")
            or (fst.get("tournament_entry") or {}).get("file")
            or local_rung(famdir, rung)
        )
        if not model or not os.path.isfile(model):
            entry["error"] = f"model file not found ({model})"
            print(f"  ERROR: {entry['error']}")
            results.append(entry)
            continue
        kv_k = (
            run.get("kv_quant_k")
            or (fst.get("tournament_entry") or {}).get("kv_quant_k")
            or state.get("kv_quant_k")
        )
        kv_v = (
            run.get("kv_quant_v")
            or (fst.get("tournament_entry") or {}).get("kv_quant_v")
            or state.get("kv_quant_v")
        )
        results_dir = os.path.join(models_dir, "tournament-results", fam)
        os.makedirs(results_dir, exist_ok=True)
        ns = {"vt": "certify_vt", "speed": "certify_speed"}.get(task, "certify")
        direct = dict((fst.get(ns) or {}).get(str(depth)) or {})
        ran = 0
        verdict = None
        while True:
            lo, _ = wilson_interval(k, measured, z) if measured else (0.0, 0.0)
            remaining = n_total - measured
            # the plan: how many consecutive passes certify, how many
            # consecutive fails kill - the author's addendum-20 request
            to_accept = None
            to_dead = None
            if level == "at_least_one":
                if k >= 1:
                    verdict = "accept"
                    break
                if remaining == 0:
                    verdict = "dead"
                    break
                to_accept = 1
            else:
                if measured >= floor and lo >= 0.5:
                    verdict = "accept"
                    break
                best_k = k + remaining
                best_lo, _ = wilson_interval(best_k, n_total, z)
                if best_lo < 0.5 or best_k < floor:
                    verdict = "dead"
                    break
                for j in range(1, remaining + 1):
                    lo_j, _ = wilson_interval(k + j, measured + j, z)
                    if measured + j >= floor and lo_j >= 0.5:
                        to_accept = j
                        break
                for j in range(1, remaining + 1):
                    bk = k + (remaining - j)
                    bl, _ = wilson_interval(bk, n_total, z)
                    if bl < 0.5 or bk < floor:
                        to_dead = j
                        break
            if ran == 0:
                plan = (
                    f"  PLAN @ {depth:,}: {measured}/{n_total} cells measured, {remaining} left - "
                )
                plan += (
                    f"{to_accept if to_accept else remaining} consecutive pass(es) certify; "
                    if to_accept is not None or level == "at_least_one"
                    else ""
                )
                plan += (
                    f"{to_dead if to_dead else remaining} consecutive fail(s) kill"
                    if to_dead is not None
                    else f"cannot die this rung ({remaining} cells left)"
                )
                print(plan)
            if dry_run:
                verdict = "would-run"
                break
            next_run = min(r for r in range(1, n_total + 1) if r not in cells)
            if task == "speed":
                ok, fv = speed_cell(
                    model,
                    depth + 2 * ruler_gate.ANSWER_HEADROOM,
                    CORPUS_DEFAULT,
                    results_dir,
                    next_run,
                    port,
                    kv_quant_k=kv_k,
                    kv_quant_v=kv_v,
                )
                ran += 1
                cells[next_run] = ok
                stalls = int(fv.get("stalls") or 0)
                n_turns = int(fv.get("turns") or 0)
                direct[str(next_run)] = stalls
                measured += 1
                k += 1 if ok else 0
                fst.setdefault("certify_speed", {})[str(depth)] = direct
                save_state(state_path, state)
                print(
                    f"  speed cell (conv {next_run}, {depth:,} tok): "
                    f"{stalls} stall(s) in {n_turns} turns -> "
                    f"{'PASS' if ok else 'FAIL'} -> {k}/{measured} "
                    f"(1s lower bound {wilson_interval(k, measured)[0]:.3f})"
                )
                continue
            if task == "vt":
                ok, fv = vt_pass(
                    model,
                    depth + 2 * ruler_gate.ANSWER_HEADROOM,
                    results_dir,
                    seed=next_run,
                    port=port,
                    kv_quant_k=kv_k,
                    kv_quant_v=kv_v,
                )
                ran += 1
                cells[next_run] = ok
                partial = int((fv.get("words_found") or [0])[0] or 0)
                direct[str(next_run)] = partial
                measured += 1
                k += 1 if ok else 0
                fst.setdefault("certify_vt", {})[str(depth)] = direct
                save_state(state_path, state)
                print(
                    f"  vt cell (run {next_run}, {depth:,} tok): "
                    f"{partial}/5 names -> {'PASS' if ok else 'FAIL'} -> "
                    f"{k}/{measured} "
                    f"(1s lower bound {wilson_interval(k, measured)[0]:.3f})"
                )
                continue
            ok, fv = fwe_pass(
                model,
                depth + 2 * ruler_gate.ANSWER_HEADROOM,
                results_dir,
                seed=next_run,
                port=port,
                kv_quant_k=kv_k,
                kv_quant_v=kv_v,
                min_words=min_words,
            )
            ran += 1
            cells[next_run] = ok
            words = fv.get("words_found") or []
            direct[str(next_run)] = words[0] if words else int(ok)
            measured += 1
            k += 1 if ok else 0
            fst.setdefault("certify", {})[str(depth)] = direct
            save_state(state_path, state)
            print(
                f"  cell (run {next_run}, {depth:,} tok): "
                f"{'PASS' if ok else 'FAIL'} -> {k}/{measured} "
                f"(1s lower bound {wilson_interval(k, measured)[0]:.3f})"
            )
        entry["cells_measured"] = measured
        entry["passes"] = k
        entry["ran_now"] = ran
        if verdict == "accept":
            entry["verdict"] = "accept"
            if level == "at_least_one":
                print(
                    f"  ACCEPT at {k}/{measured} - at least one pass at "
                    f"{depth:,} - {fam} answers the {depth:,} rung"
                )
            else:
                lo = wilson_interval(k, measured, z)[0]
                print(
                    f"  ACCEPT at {k}/{measured} - {level.replace('_', ' ')} "
                    f"lower bound {lo:.3f} >= 0.5 - {fam} answers the {depth:,} rung"
                )
            answered = True
        elif verdict == "dead":
            entry["verdict"] = "dead"
            if level == "at_least_one":
                print(f"  DEAD - every cell measured, no pass at {depth:,}; next candidate")
            else:
                print(
                    f"  DEAD - even {best_k}/{n_total} cannot reach the bar "
                    f"(best {int(z)}s lower bound {best_lo:.3f} < 0.5); next candidate"
                )
        elif verdict == "would-run":
            entry["verdict"] = "would-run"
            nxt = min(r for r in range(1, n_total + 1) if r not in cells)
            print(f"  dry run - would test {remaining} cell(s) from run {nxt}")
        results.append(entry)
    return results


COMBINED_TASKS = ("speed", "fwe", "vt")


def _task_load(
    fst: dict[str, Any],
    depth: int,
    task: str,
    min_words: int,
    models_dir: str,
    fam: str,
) -> dict[int, bool]:
    """The pass/fail cell map for one task at one rung, from whatever
    evidence already exists (combined mode: a cell's task measurement
    is loaded if present, measured later only if missing)."""
    if task == "vt":
        return {r: p >= 5 for r, p in vt_cells(fst, depth).items()}
    if task == "speed":
        return {r: p == 0 for r, p in speed_cells(fst, depth).items()}
    return certify_cells(fst, depth, min_words, models_dir, fam)


def _task_store(fst: dict[str, Any], depth: int, task: str, run: int, value: int) -> None:
    """Persist one cell's graded record in its own namespace (the
    combined controller never re-measures a stored cell-task)."""
    ns = {"vt": "certify_vt", "speed": "certify_speed"}.get(task, "certify")
    fst.setdefault(ns, {}).setdefault(str(depth), {})[str(run)] = value


def _task_measure(
    task: str,
    model: str,
    depth: int,
    results_dir: str,
    run: int,
    port: int,
    kv_k: str | None,
    kv_v: str | None,
    min_words: int,
) -> tuple[bool, int, str]:
    """Measure one cell's one task. Returns (passed_at_gold, graded
    record, human line). The graded record is the speed stall count,
    the FWE word count, the VT 5-name count - all re-gradable at any
    bar later without re-measuring."""
    if task == "speed":
        ok, fv = speed_cell(
            model,
            depth + 2 * ruler_gate.ANSWER_HEADROOM,
            CORPUS_DEFAULT,
            results_dir,
            run,
            port,
            kv_quant_k=kv_k,
            kv_quant_v=kv_v,
        )
        stalls = int(fv.get("stalls") or 0)
        n_turns = int(fv.get("turns") or 0)
        return (
            ok,
            stalls,
            (f"speed: {stalls} stall(s) in {n_turns} turns -> {'PASS' if ok else 'FAIL'}"),
        )
    if task == "vt":
        ok, fv = vt_pass(
            model,
            depth + 2 * ruler_gate.ANSWER_HEADROOM,
            results_dir,
            seed=run,
            port=port,
            kv_quant_k=kv_k,
            kv_quant_v=kv_v,
        )
        partial = int((fv.get("words_found") or [0])[0] or 0)
        return ok, partial, f"vt: {partial}/5 names -> {'PASS' if ok else 'FAIL'}"
    ok, fv = fwe_pass(
        model,
        depth + 2 * ruler_gate.ANSWER_HEADROOM,
        results_dir,
        seed=run,
        port=port,
        kv_quant_k=kv_k,
        kv_quant_v=kv_v,
        min_words=min_words,
    )
    words = fv.get("words_found") or []
    count = words[0] if words else int(ok)
    return ok, count, f"fwe: {count}/{max(1, min_words)} word(s) -> {'PASS' if ok else 'FAIL'}"


def certify_rung_combined(
    depth: int,
    level: str,
    specs: list[str],
    models_dir: str,
    state: dict[str, Any],
    state_path: str,
    port: int,
    dry_run: bool,
    min_words: int = 1,
) -> list[dict[str, Any]]:
    """The combined controller (session 38, addendum 3 - the author's
    ruling): a cell is (model, rung, run) carrying THREE independent
    measurements - speed, FWE and VT. A cell's task is measured only
    if missing (never twice); the three tasks carry their own pass/fail
    tallies and their own accept/dead verdicts. The candidate certifies
    the rung when ALL THREE accept; it dies when ANY ONE is dead (the
    next candidate is picked up). Gold = all three at gold; silver =
    all three at least silver; bronze = any pass at all."""
    if level not in CERTIFY_LEVELS:
        raise ValueError(f"unknown certify level {level!r}")
    n_total = TOURNAMENT_CLIMBS
    floor = 1 if level == "at_least_one" else math.ceil(0.5 * n_total)
    z = 0.0 if level == "at_least_one" else float(level.split("_")[0])
    order: list[tuple[str, dict[str, Any], dict[str, dict[int, bool]]]] = []
    for spec in specs:
        fam = os.path.basename(spec.partition("=")[0].rstrip("/"))
        fst = state["families"].get(fam, {})
        cells = {t: _task_load(fst, depth, t, min_words, models_dir, fam) for t in COMBINED_TASKS}
        order.append((fam, fst, cells))

    def promise(item):
        fam, fst, cells = item
        k = sum(sum(1 for ok in t.values() if ok) for t in cells.values())
        saved_rank = state.get("tournament") or []
        rd = 0
        for tr in saved_rank:
            if tr.get("family") == fam:
                rd = tr.get("reliable_depth") or 0
        return (-k, -rd, fam)

    order.sort(key=promise)
    results: list[dict[str, Any]] = []
    answered = False
    for fam, fst, cells0 in order:
        cells = {t: dict(v) for t, v in cells0.items()}
        entry = {
            "family": fam,
            "depth": depth,
            "level": level,
            "task": "all",
        }
        for t in COMBINED_TASKS:
            m = len(cells[t])
            kp = sum(1 for ok in cells[t].values() if ok)
            entry[f"{t}_historical_passes"] = kp
            entry[f"{t}_historical_cells"] = m
        print()
        print("-" * 60)
        for t in COMBINED_TASKS:
            print(
                f"  {fam} {t}: {entry[f'{t}_historical_passes']}/"
                f"{entry[f'{t}_historical_cells']} cells measured, "
                f"{n_total - entry[f'{t}_historical_cells']} unmeasured"
            )
        if answered:
            entry["skipped"] = "rung already answered"
            print("  SKIPPED - the rung is already answered")
            results.append(entry)
            continue
        famdir = os.path.join(models_dir, fam)
        rung = fst.get("selected") or (fst.get("tournament_entry") or {}).get("rung")
        run = (fst.get("runs") or {}).get(rung or "", {})
        model = (
            run.get("file")
            or (fst.get("tournament_entry") or {}).get("file")
            or local_rung(famdir, rung)
        )
        if not model or not os.path.isfile(model):
            entry["error"] = f"model file not found ({model})"
            print(f"  ERROR: {entry['error']}")
            results.append(entry)
            continue
        kv_k = (
            run.get("kv_quant_k")
            or (fst.get("tournament_entry") or {}).get("kv_quant_k")
            or state.get("kv_quant_k")
        )
        kv_v = (
            run.get("kv_quant_v")
            or (fst.get("tournament_entry") or {}).get("kv_quant_v")
            or state.get("kv_quant_v")
        )
        results_dir = os.path.join(models_dir, "tournament-results", fam)
        os.makedirs(results_dir, exist_ok=True)
        ran = 0
        verdict = None
        verdicts = {t: None for t in COMBINED_TASKS}
        tallies = {
            t: {
                "measured": len(cells[t]),
                "k": sum(1 for ok in cells[t].values() if ok),
            }
            for t in COMBINED_TASKS
        }

        def task_lo(t, _tallies=tallies):
            ta = _tallies[t]
            return wilson_interval(ta["k"], ta["measured"], z)[0] if ta["measured"] else 0.0

        while True:
            # verdicts: per task, independent accept / dead
            for t in COMBINED_TASKS:
                if verdicts[t] is not None:
                    continue
                ta = tallies[t]
                k, measured = ta["k"], ta["measured"]
                remaining = n_total - measured
                lo = task_lo(t)
                if level == "at_least_one":
                    if k >= 1:
                        verdicts[t] = "accept"
                    elif remaining == 0:
                        verdicts[t] = "dead"
                else:
                    if measured >= floor and lo >= 0.5:
                        verdicts[t] = "accept"
                        continue
                    best_k = k + remaining
                    best_lo, _ = wilson_interval(best_k, n_total, z)
                    if best_lo < 0.5 or best_k < floor:
                        verdicts[t] = "dead"
            if all(v == "accept" for v in verdicts.values()):
                verdict = "accept"
                break
            if any(v == "dead" for v in verdicts.values()):
                verdict = "dead"
                dead_task = next(t for t in COMBINED_TASKS if verdicts[t] == "dead")
                break
            if dry_run:
                verdict = "would-run"
                break
            # pick the lowest unmeasured cell across the three tasks:
            # a cell run is shared, so measure the tasks the cell misses
            next_run = min(
                min(r for r in range(1, n_total + 1) if r not in cells[t])
                for t in COMBINED_TASKS
                if any(r not in cells[t] for r in range(1, n_total + 1))
            )
            for t in COMBINED_TASKS:
                if next_run in cells[t]:
                    continue
                ok, graded, line = _task_measure(
                    t, model, depth, results_dir, next_run, port, kv_k, kv_v, min_words
                )
                ran += 1
                cells[t][next_run] = ok
                tallies[t]["measured"] += 1
                tallies[t]["k"] += 1 if ok else 0
                _task_store(fst, depth, t, next_run, graded)
                save_state(state_path, state)
                print(
                    f"  cell {next_run} (rung {depth:,}) {line} -> {t} "
                    f"{tallies[t]['k']}/{tallies[t]['measured']} "
                    f"(1s lower bound {task_lo(t):.3f})"
                )
        entry["cells_measured"] = sum(tallies[t]["measured"] for t in COMBINED_TASKS)
        entry["ran_now"] = ran
        entry["medal"] = combined_medal(fst, depth, level)
        for t in COMBINED_TASKS:
            entry[f"{t}_passes"] = tallies[t]["k"]
            entry[f"{t}_cells"] = tallies[t]["measured"]
            entry[f"{t}_verdict"] = verdicts[t]
        tally_line = ", ".join(
            f"{t} {tallies[t]['k']}/{tallies[t]['measured']}" for t in COMBINED_TASKS
        )
        if verdict == "accept":
            entry["verdict"] = "accept"
            print(
                f"  ACCEPT at {depth:,} - all three tasks clear "
                f"({tally_line}) "
                f"- {fam} answers the {depth:,} rung"
            )
            answered = True
        elif verdict == "dead":
            entry["verdict"] = "dead"
            ta = tallies[dead_task]
            print(
                f"  DEAD - {dead_task} cannot reach the bar at {depth:,} "
                f"({ta['k']}/{ta['measured']}, best lower bound "
                f"{wilson_interval(ta['k'] + (n_total - ta['measured']), n_total, z)[0]:.3f} < 0.5)"
                "; next candidate"
            )
        elif verdict == "would-run":
            entry["verdict"] = "would-run"
            print("  dry run - would measure the missing cell-tasks above")
        results.append(entry)
    return results


TASK_GOLD_BARS = {"speed": 0, "fwe": 3, "vt": 5}
TASK_SILVER_BARS = {"speed": 1, "fwe": 2, "vt": 4}


def combined_medal(fst: dict[str, Any], depth: int, level: str) -> str | None:
    """The combined medal (session 38, addendum 3): re-grade the stored
    per-cell records at each task's gold and silver bars. Gold = all
    three tasks at gold; silver = at least silver in all three; bronze
    = any pass at all. A task with no measured cells has no medal
    contribution (None overall until every task has evidence)."""
    n_total = TOURNAMENT_CLIMBS
    floor = 1 if level == "at_least_one" else math.ceil(0.5 * n_total)
    z = 0.0 if level == "at_least_one" else float(level.split("_")[0])
    bars = {"gold": TASK_GOLD_BARS, "silver": TASK_SILVER_BARS}
    grades = {}
    for t in COMBINED_TASKS:
        if t == "fwe":
            raw = (fst.get("certify") or {}).get(str(depth)) or {}
            records = {}
            for r, p in raw.items():
                if isinstance(p, bool):
                    records[int(r)] = 3 if p else 0
                else:
                    records[int(r)] = int(p)
        elif t == "vt":
            records = vt_cells(fst, depth)
        else:
            records = speed_cells(fst, depth)
        if not records:
            return None
        grades[t] = {}
        for label in bars:
            bar = bars[label][t]
            k = sum(1 for p in records.values() if p >= bar)
            lo, _ = wilson_interval(k, len(records), z)
            grades[t][label] = k >= floor and lo >= 0.5
    if all(grades[t]["gold"] for t in COMBINED_TASKS):
        return "gold"
    if all(grades[t]["silver"] for t in COMBINED_TASKS):
        return "silver"
    if any(grades[t]["gold"] or grades[t]["silver"] for t in COMBINED_TASKS):
        return "bronze"
    return None


def rescore_tournament(
    models_dir: str,
    state: dict[str, Any],
    state_path: str,
    dry_run: bool,
) -> None:
    """Session 37, addendum 4 (the author's re-score ruling): the saved
    tournament_falls were collected under the 3/3 criterion; under the
    relaxed 1/3 criterion (addendum 2) every recorded fall is a LOWER
    BOUND on the true one (all recorded falls were 1/3 or 2/3 partials,
    addendum 26 - a 0/3 fall would fall under both criteria). This
    re-derives each climb's fall from the raw per-cell CSVs the climbs
    wrote: a cell passes at partial >= 1; the re-scored fall is the
    first rung whose cell fails; a climb whose every recorded cell
    passes re-runs from just above its old fall (the early stop never
    wrote the cells above). Without --rescore-apply the state is only
    REPORTED, never written; with it, tournament_falls is rewritten
    under the new criterion and the family's remaining depths run
    the next --tournament as fresh seeds' resume."""
    depths = TOURNAMENT_DEPTHS
    for fam, fst in sorted(state.get("families", {}).items()):
        saved = fst.get("tournament_falls") or {}
        if not saved:
            print(f"  {fam}: no saved climbs - nothing to re-score")
            continue
        results_dir = os.path.join(models_dir, "tournament-results", fam)
        print(f"  {fam}: re-scoring {len(saved)} climbs under the 1/3 criterion")
        changed = 0
        if dry_run:
            saved = dict(saved)
        for key in sorted(saved, key=int):
            s = int(key)
            climb_dir = os.path.join(results_dir, f"climb{s}")
            old_fall = saved[key]
            new_fall = None
            for d in depths:
                csv_path = os.path.join(climb_dir, f"-{d}-fwe.csv")
                if not os.path.isfile(csv_path):
                    matches = sorted(glob.glob(os.path.join(climb_dir, f"*-{d}-fwe.csv")))
                    csv_path = matches[0] if matches else csv_path
                if not os.path.isfile(csv_path):
                    if old_fall is not None and d <= old_fall:
                        print(
                            f"    climb {s}: MISSING cell at {d:,} tok "
                            f"({csv_path}) - cannot re-score; keeping the "
                            f"recorded fall"
                        )
                        new_fall = old_fall
                        break
                    break
                with open(csv_path, encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
                partial = None
                for r in rows:
                    if r.get("partial") not in (None, ""):
                        partial = int(r["partial"])
                if partial is None:
                    print(
                        f"    climb {s}: cell at {d:,} tok has no partial "
                        f"count - cannot re-score; keeping the recorded fall"
                    )
                    new_fall = old_fall
                    break
                if partial < 1:
                    new_fall = d
                    break
            if new_fall is None and old_fall is not None:
                # every recorded cell passes under 1/3 - the true fall is
                # ABOVE the recorded one, and the cells above were never
                # written (early stop). The climb needs re-running from
                # just above its old fall; the rescore marks it UNKNOWN
                # by dropping the saved entry so the next --tournament
                # run resumes it as a fresh climb.
                print(
                    f"    climb {s}: old fall {old_fall:,} is now a PASS "
                    f"chain - the true fall is above it and unmeasured; "
                    f"the saved fall is DROPPED so the next tournament "
                    f"run re-runs the whole climb under 1/3"
                )
                del saved[key]
                changed += 1
                continue
            if new_fall != old_fall:
                changed += 1
                o = "None" if old_fall is None else format(old_fall, ",")
                n = "None" if new_fall is None else format(new_fall, ",")
                print(f"    climb {s}: fall {o} -> {n} tok")
                saved[key] = new_fall
        if dry_run:
            print(f"  {fam}: dry run - {changed} climbs would change (state NOT written)")
        else:
            fst["tournament_falls"] = saved
            save_state(state_path, state)
            print(f"  {fam}: {changed} climbs changed - state saved")


def print_tournament_table(tours: list[dict[str, Any]]) -> None:
    """The tournament ranking (session 37, addendum 10: the mode is
    retired - sigma only): ranked by reliable depth (1 sigma), ties on
    conservative depth (2 sigma), then the pass vector at the steps
    above, then the ceiling."""
    print()
    print("=" * 60)
    stamp("TOURNAMENT TABLE (sigma rank - session 37 addendum 10)")
    done = [t for t in tours if "passes" in t]
    errs = [t for t in tours if "error" in t]
    for t in errs:
        print(f"  {t['family']}: SKIPPED - {t['error']}")
    order = sorted(
        done,
        key=lambda t: (
            -t.get("reliable_depth", 0),
            -t.get("conservative_depth", 0),
            [-t["passes"][d] for d in sorted(t["passes"], reverse=True)],
            -t.get("ceiling", 0),
        ),
    )
    for i, t in enumerate(order, 1):
        pv = " ".join(f"{t['passes'][d]}" for d in TOURNAMENT_DEPTHS)
        print(
            f"  {i}. {t['family']:24s} reliable "
            f"{t.get('reliable_depth', 0):>7,} tok | conservative "
            f"{t.get('conservative_depth', 0):>7,} tok | ceiling "
            f"{t.get('ceiling', 0):>7,} tok | passes/rung [{pv}]"
        )


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
        ok_s, sv = speed_pass(model, r, corpus, port, results_dir, kv_quant_k, kv_quant_v)
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
        ok_f, fv = fwe_pass(model, r, results_dir, seed, port, kv_quant_k, kv_quant_v)
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
                "resident_gib": (cell.get("mem_census") or {}).get("resident_gib"),
            }
    return {"depth": score, "worst_wps": None, "cold_cost_gib": None}


QUANTIZE_BIN = convert_quant.QUANTIZE_BIN
CORPUS_DEFAULT = speed_gate.CORPUS_DEFAULT
MODELS_DIR_DEFAULT = "./models"
STATE_FILE_DEFAULT = "./state/benchmark-state.json"
RESULTS_FILE_DEFAULT = "./benchmark-results.json"
# Q4_0 removed (author ruling, addendum 37): Q4_K_M is the single 4-bit
# rung - "there's a q4_0 that's unnecessary since we have q4_k_m".
# Addendum 86: the rung WALK is removed - one rung per run.
# The study's default rung stays Q8_0; --rung overrides it (session
# 34: the Q4 quants - context dominates this bw class, so the smaller
# file with the deeper ladder is the hypothesis to test).
RUNG_DEFAULT = "Q8_0"

# The tournament grid and climb count (session 36, addenda 10/11): a
# dyadic ladder from 4,096 to the 262,144 ceiling, five climbs per
# family, SEED = CLIMB NUMBER (1..5) so every competitor faces the
# same five task ladders. Upstream RULER FWE parameters exactly
# (k=3, alpha 2.0 - addendum 7/8 verification).
TOURNAMENT_DEPTHS = [4096, 8192, 16384, 32768, 65536, 131072, 262144]
TOURNAMENT_CLIMBS = 21
TOURNAMENT_MODEL_QUANTS = ["Q2_K", "Q3_K", "Q4_K", "Q5_K", "Q6_K", "Q8_0"]
TOURNAMENT_KV_QUANTS = ["q4_0", "q5_0", "q6_K", "q8_0", "f16"]
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
    # from disk (folder deleted/moved) while state/benchmark-state.json still
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
            max_rung=state.get("ladder_max_rung"),
            kv_quant_k=state.get("kv_quant_k"),
            kv_quant_v=state.get("kv_quant_v"),
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
        if ladder and ladder.get("launch_failed"):
            # session 35, addendum 7: a launch failure is not a score -
            # the family stays UNSELECTED (the false-zero bug: the
            # crashed witness runs recorded "PASS (ladder score 0)" and
            # the resume skipped the family)
            run["verdict"] = (
                "FAIL (server launch failed - bad flags/build or load-time "
                "crash; fix the launch and re-run with --force)"
            )
            run["rung"] = rung
            run["score"] = 0
            run["launch_failed"] = True
            run["phases_done"].append(4)
            save_state(state_path, state)
            stamp("      phase 4 done (launch failed - not selectable)")
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
        "--tournament",
        action="store_true",
        help="session 36, addenda 10/11: run the TOURNAMENT instead of the "
        "ladder sweep - every family at its SELECTED rung (the PASS "
        "config, its stored KV quants), five climbs of the dyadic FWE "
        "ladder 4096..262144, SEED = CLIMB NUMBER, early stop at the "
        "first non-perfect cell; the sigma rank (reliable/conservative depths) is the ranking",
    )
    ap.add_argument(
        "--rescore",
        action="store_true",
        help="session 37, addendum 4: re-derive every saved climb's fall "
        "from the raw per-cell CSVs under the relaxed 1/3 criterion "
        "(addendum 2) instead of running the tournament. Read-only by "
        "default; --rescore-apply rewrites tournament_falls (a climb "
        "whose recorded fall is now a pass chain is DROPPED so the next "
        "--tournament re-runs it under 1/3)",
    )
    ap.add_argument(
        "--rescore-apply",
        action="store_true",
        help="with --rescore: write the re-scored falls to the state file",
    )
    ap.add_argument(
        "--diagnose",
        action="store_true",
        help="session 37, addendum 9: read the climb cell CSVs and report "
        "the per-rank diagnostic (which of the 3 expected words a "
        "partial pass found) and the pass rate at >=1/3, >=2/3, 3/3 "
        "per family - measure once, grade at any threshold later",
    )
    ap.add_argument(
        "--certify",
        choices=CERTIFY_LEVELS,
        default=None,
        metavar="LEVEL",
        help="session 37, addendum 18: certify the rungs given by "
        "--rungs sequentially - the most promising candidate is tested "
        "cell by cell (a cell is model x run x step, NEVER re-measured; "
        "historical climb cells are inherited) until it certifies or is "
        "mathematically dead; the first accepted model answers the rung; "
        "the rest are skipped. LEVEL is the certification type: "
        "at_least_one (any model with a pass at the step), 1_sigma "
        "(reliable: 1-sigma Wilson lower bound >= 0.5, n=21), 2_sigma "
        "(conservative: the same bar at 2 sigma)",
    )
    ap.add_argument(
        "--rungs",
        type=str,
        default=None,
        metavar="D1,D2,...",
        help="session 37, addendum 18: comma-separated rung(s) to "
        "certify (e.g. --rungs 32768,65536), processed "
        "cheapest-first (sorted ascending); required with --certify. "
        "State is saved after each rung, so each rung's answers feed "
        "the next rung's predictions - a range is just multiple "
        "commands concatenated, no JSON needed. Comma form keeps the "
        "positional families list parseable (addendum 19: argparse's "
        "nargs='+' swallowed the families as depths)",
    )
    ap.add_argument(
        "--fwe-min-words",
        type=int,
        default=1,
        metavar="N",
        help="session 37 (the 2/3 tightening): the FWE pass bar - a cell "
        "passes when >= N of the 3 hidden words are found (default 1, "
        "the addendum-2 relaxation). N=2 tightens gold certification to "
        "2-of-3. Cells that stored an integer word count are re-graded "
        "exactly at the new bar; cells stored as booleans or inherited "
        "from tournament falls were graded under the old 1/3 rule and are "
        "re-run, never silently trusted",
    )
    ap.add_argument(
        "--task",
        default="fwe",
        choices=["fwe", "vt", "speed", "all"],
        help="session 37 (the VT certification): with --certify, run the "
        "variable-tracking task instead of FWE - same stack, n=21, "
        "seeds and sequential controller, but a separate cell namespace "
        "(certify_vt - the FWE evidence is never touched), pass = ALL "
        "5 chain names, the 0..5 partial stored per cell as the graded "
        "diagnostic (the VT analogue of the FWE x/3 word count). "
        "session 38 (addendum 3): 'all' is the combined controller - "
        "each cell carries speed, fwe and vt, measured only if missing, "
        "three independent tallies, accept when all three clear, dead "
        "when any one dies",
    )
    _KV_CHOICES = ["q8_0", "q4_0", "q4_1", "q5_0", "q5_1", "iq4_nl"]
    ap.add_argument(
        "--kv-quant-k",
        default=None,
        choices=_KV_CHOICES,
        help="session 35, addendum 7: quantize ONLY the K cache to this type "
        "(V keeps its own setting; both None = default f16).",
    )
    ap.add_argument(
        "--kv-quant-v",
        default=None,
        choices=_KV_CHOICES,
        help="session 35, addendum 7: quantize ONLY the V cache to this type "
        "(K keeps its own setting; both None = default f16).",
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
        "--max-rung",
        type=int,
        default=None,
        help="session 35 (addendum 9): the gallop's hard stop - the ladder "
        "never climbs past this rung. With --min-rung N --max-rung N the run "
        "is a single-rung probe: speed + fwe at exactly N, pass or fail, no "
        "search; stored in the state as ladder_max_rung",
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
    ap = build_parser()
    args = ap.parse_args()
    global DRY_RUN_ACTIVE
    DRY_RUN_ACTIVE = args.dry_run

    if args.thinking and args.no_thinking:
        ap.error("--thinking and --no-thinking are mutually exclusive")

    check_requirements()
    git_pull_head()
    tee_output.install()
    if not args.dry_run:
        kill_stale_server()
        check_tooling(args)

    state = load_state(args.state_file)
    if args.min_rung:
        state["ladder_min_rung"] = args.min_rung
    if args.max_rung:
        state["ladder_max_rung"] = args.max_rung
    if args.kv_quant_k:
        state["kv_quant_k"] = args.kv_quant_k
    if args.kv_quant_v:
        state["kv_quant_v"] = args.kv_quant_v

    if not args.families:
        ap.error("no family specs given")
    if args.rescore:
        rescore_tournament(args.models_dir, state, args.state_file, not args.rescore_apply)
        return
    if args.diagnose:
        diagnose_fwe(args.models_dir, state)
        return
    if args.certify:
        if not args.rungs:
            ap.error("--certify needs --rungs D1,D2,...")
        try:
            rung_list = [int(x) for x in args.rungs.split(",") if x.strip()]
        except ValueError:
            ap.error(f"--rungs must be comma-separated integers, got {args.rungs!r}")
        if not rung_list:
            ap.error("--rungs needs at least one depth")
        all_results: list[dict[str, Any]] = []
        for depth in sorted(rung_list):
            if args.task == "all":
                results = certify_rung_combined(
                    depth,
                    args.certify,
                    args.families,
                    args.models_dir,
                    state,
                    args.state_file,
                    state.get("ladder_port", 8210),
                    args.dry_run,
                    min_words=args.fwe_min_words,
                )
            else:
                results = certify_rung(
                    depth,
                    args.certify,
                    args.families,
                    args.models_dir,
                    state,
                    args.state_file,
                    state.get("ladder_port", 8210),
                    args.dry_run,
                    min_words=args.fwe_min_words,
                    task=args.task,
                )
            state["certify"] = results
            save_state(args.state_file, state)
            print()
            print("=" * 60)
            stamp(f"CERTIFY {args.certify} {depth:,} SUMMARY")
            for r in results:
                v = r.get("verdict", r.get("error", r.get("skipped", "?")))
                extra = f" w/s median {r['wps_median']}" if r.get("wps_median") else ""
                print(
                    f"  {r['family']}: {v} ({r.get('passes', 0)}/"
                    f"{r.get('cells_measured', 0)} cells, ran {r.get('ran_now', 0)} now){extra}"
                )
            all_results.extend(results)
        # the gold-run lesson (2026-10-03): the certify branch returned
        # bare and skipped the git tail - the artifacts (results.txt,
        # state) never committed and had to be pushed by hand
        if not args.no_git:
            tee_output.uninstall()
            git_tail(args)
        return
    if args.tournament:
        tours = []
        for spec in args.families:
            try:
                tours.append(
                    tournament_family(
                        spec,
                        args.models_dir,
                        state,
                        args.state_file,
                        state.get("ladder_port", 8210),
                        args.dry_run,
                    )
                )
            except Exception as e:
                tours.append({"family": spec, "error": repr(e)})
                stamp(f"TOURNAMENT FAMILY FAILED: {spec} - {e!r} (isolated; recorded)")
        state["tournament"] = tours
        save_state(args.state_file, state)
        print_tournament_table(tours)
        # session 37, addendum 15: the reliable-depth w/s measurement
        # (addendum 42) is RETIRED - the RAM-ceiling assumption
        # replaces it (a config selected under the ceiling has the
        # bandwidth to clear the reader line); w/s is not measured in
        # the benchmark. The historical wps medians in state stay as
        # records of what was measured under the old protocol.
        if not args.no_git:
            tee_output.uninstall()
            git_tail(args)
        stamp("tournament complete")
        sys.exit(0)

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


def git_pull_head() -> None:
    """The forgotten pull, made structural (session 36, addendum 32;
    wow.md section 6 - many errors come from missing steps like git
    pull). Runs BEFORE the state loads, so every run - real or dry -
    starts from the freshest state file and notebook the repo has:
    the author's artifact commits land on main between exchanges, and
    a stale checkout silently grades against old data. --no-git is
    the escape hatch (same as the tail); a failed pull is a HARD
    STOP, not a warning - running on a diverged tree measures the
    wrong thing with confidence."""
    if os.environ.get("BENCH_NO_GIT_PULL"):
        return
    r = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True
    )
    if r.returncode != 0 or r.stdout.strip() != "true":
        stamp("git pull skipped - not a git work tree")
        return
    r = subprocess.run(
        ["git", "pull", "--rebase", "--autostash", "--no-verify"], capture_output=True, text=True
    )
    if r.returncode != 0:
        stamp(f"git pull failed - FIX BEFORE RUNNING: {r.stderr.strip()[:200]}")
        raise SystemExit(1)
    out = r.stdout.strip()
    if out and "Already up to date" not in out:
        stamp(f"git pull: {out.splitlines()[0]}")
    else:
        stamp("git pull: already up to date")


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
    # wow.md section 9 lesson (2026-10-03): the tournament/certify cells
    # write their per-cell CSVs (with the `partial` word counts) to
    # models/tournament-results/ (one shared dir, per-family subdirs) -
    # a path this glob missed, so the certify runs' raw evidence never
    # committed and re-grading had to mine results.txt instead of the
    # state
    paths += glob.glob("models/tournament-results/**/*", recursive=True)
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
    # addendum 47: the artifact push can race origin (rules land on
    # main DURING a long run - the addendum-46 lesson: stale data on
    # my side for hours). Pull-rebase-autostash AFTER the commit and
    # BEFORE the push, so the artifact commit replays on top of
    # whatever landed meanwhile; the autostash covers tree dirt.
    r = subprocess.run(["git", "pull", "--rebase", "--autostash"], capture_output=True, text=True)
    if r.returncode != 0:
        hint = "run: git pull --rebase --autostash; and git push"
        stamp(f"pull before push failed: {r.stderr.strip()} - {hint}")
    r = subprocess.run(["git", "push"], capture_output=True, text=True)
    if r.returncode != 0:
        stamp(f"push failed: {r.stderr.strip()} - run: git pull --rebase --autostash; and git push")
    else:
        stamp("pushed")


if __name__ == "__main__":
    main()
