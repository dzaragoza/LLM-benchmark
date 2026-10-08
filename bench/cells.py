"""bench.cells -- the cell primitives (session 39, addendum 15: the
full_benchmark.py refactor). Every function here measures ONE cell
(model, rung, run) and returns its record; nothing here touches the
state file. Extracted verbatim from full_benchmark.py -- the addendum
citations in each docstring are the study's history and stay."""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import infra.llama_server as llama_server
import ruler_gate
import speed_gate

RUNG_BASE = 4096
MIN_RUNG_FAIL = 16384  # session 34 (addendum 19): a floor below the start
# rung means a base failure - the model is out, pending investigation


def kill_stale_server() -> None:
    """Session 34 (addendum 19, refinement 1): the pkill moves into the
    instrument. A stale llama-server would hold the port and the RAM;
    the sweep's own launches replace whatever was there. Session 40
    (addendum 5): the subprocess moved down into llama_server (bottom
    layer) - this is the thin middle-layer wrapper with its prints."""
    if llama_server.kill_stale_server():
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
        log_dir=results_dir,
    )
    # the launch's banner: when the server capped the -c DOWN to the
    # trained window, bench_model's banner guard refused to bench (no
    # turns) - the window rides in the verdict either way (addendum 19);
    # addendum 60: the log lives in the results tree, not the model dir
    server_log = os.path.join(results_dir, os.path.basename(model) + ".server.log")
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
    # session 41, addendum 37 (protocol v4.x): the speed verdict is
    # STRICTLY wps >= 5 - the stall-rate tolerance is obsolete (the
    # author's ruling); the stall rate stays recorded in the verdict
    # as diagnostic data, never a gate.
    worst = verdict.get("worst")
    if worst is not None and worst < 5.0:
        return False, verdict
    verdict["ceiling_rung"] = worst is not None and worst < 7.5
    return True, verdict


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
        log_dir=results_dir,
    )
    dump = os.path.join(results_dir, f"{label}-rung{rung}-speed-cell{run}.json")
    with open(dump, "w") as f:
        json.dump(turns, f)
    server_log = os.path.join(results_dir, os.path.basename(model) + ".server.log")
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
    """One VT cell (own server at
    exactly the rung's ctx, banner guard, memory census), the task
    swapped: one variable-tracking chain (RULER's 1 chain x 4 hops,
    5 five-letter names), pass = ALL 5 names, the 0..5 partial is
    the graded diagnostic stored per cell (the VT analogue of the
    FWE x/3 word count)."""
    label = os.path.splitext(os.path.basename(model))[0]
    depth = rung  # addendum 61: ctx = depth; the headroom is paid inside ruler_gate's budget
    os.makedirs(results_dir, exist_ok=True)
    csv_path = os.path.join(results_dir, f"{label}-{depth}-vt.csv")
    if os.path.exists(csv_path):
        os.remove(csv_path)
    log_path = os.path.join(results_dir, f"{label}-rung{rung}-vt-server.log")
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
        breakdown = llama_server.memory_breakdown_gib(log_path)
        if breakdown is not None:
            row["mem_census"] = breakdown
            print(
                f"    vt census (llama): weights {breakdown['weights_gib']:.2f} GiB, "
                f"context {breakdown['context_gib']:.2f} GiB, "
                f"compute {breakdown['compute_gib']:.2f} GiB"
                f" -> total {breakdown['total_gib']:.2f} GiB (addendum 11)"
            )
    finally:
        llama_server.stop_server(proc, port)
    # addendum 54: the vt cell grades at the GATE bar 4/5 (row["acc"] is
    # the 0..5 names as a fraction) - the same source of truth as the
    # stored re-grade and the medal bar, never a drifted 5/5
    from bench.constants import TASK_PASS_BARS

    return row["acc"] >= TASK_PASS_BARS["vt"] / 5.0, row
