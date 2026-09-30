#!/usr/bin/env python3
"""ladder_bench.py -- the depth-ladder orchestrator (addendum 137).

The ranking instrument for the addendum-136 frontier: a model's score
is the DEEPEST dyadic rung at which it BOTH serves the reader (speed
gate, the guarantee) AND counts (FWE, quality-at-depth) -- reduced
rules: n=1 per gate per rung, the author's screening speed tier.

Per model, the ladder climbs 8192, 16384, ... with NO ceiling
term (the author's 137g ruling: the speed gate is the deciding
factor - the ladder doubles until the reader wall stops it):
  1. speed gate at ctx = rung (n=1 conversation, the fastest honest
     shape: real blob prefill, real turns, real reader wall)
  2. if the speed gate passes: FWE at depth = rung - headroom (n=1)
  3. both pass -> the model's score advances to this rung; either
     fails -> the ladder STOPS (the author's rule: the score is the
     LAST rung both passed)

The speed gate and ruler gate are used AS LIBRARIES (their own
launch, banner guard, preflight, budgeting); nothing is re-implemented
here. There is no predicted or trained ceiling: the rungs double
from 8192 without limit and the SPEED GATE alone decides where the
ladder stops (the server's own memory manager refuses a launch that
does not fit - the honest mechanical wall, measured not predicted).
"""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any

import llama_server
import ruler_gate
import speed_gate
import tee_output

RUNG_BASE = 8192


def dry_run(args: argparse.Namespace) -> int:
    """The preflight the author asked for (session 34): verify every
    model path and the corpus BEFORE any server work, print the plan
    (rungs, corpus, ports), exit non-zero on any missing file. Never
    burns a launch on a bad command line."""
    missing = 0
    for model in args.models:
        if not os.path.exists(model):
            print(f"DRY-RUN FAIL: model not found: {model}")
            missing += 1
        else:
            print(f"ok: {model} ({os.path.getsize(model) / 1024**3:.2f} GiB)")
    if not os.path.exists(args.corpus):
        print(f"DRY-RUN FAIL: corpus not found: {args.corpus}")
        missing += 1
    else:
        print(f"ok: corpus {args.corpus}")
    if missing:
        print(f"dry run: {missing} missing file(s) - nothing launched")
        return 1
    rungs = []
    r = RUNG_BASE
    while not args.max_rung or r <= args.max_rung:
        rungs.append(r)
        r *= 2
    print(f"dry run OK - rungs {rungs} from {RUNG_BASE}, n=1 both (protocol v4)")
    print("per-rung wall time printed (the time command is retired, session 34)")
    return 0


def speed_pass(
    model: str, rung: int, corpus: str, port: int, results_dir: str
) -> tuple[bool, dict[str, Any]]:
    """One speed-gate cell at ctx=rung, n=1 conversation: real blob,
    real turns, the v3.1 verdict from those turns only (reduced rules:
    a screen, not a podium number). bench_model launches the server
    itself (banner guard included); the verdict is the REAL analyze()
    on a temp dump - the phase-4 code path, not a re-implementation."""
    dropped = llama_server.drop_file_cache(model)
    if not dropped:
        print("    note: cache drop unavailable - cost may read warm (137k)")
    turns, _, mem_reports = speed_gate.bench_model(
        model,
        corpus,
        port,
        rung,
        1,
        False,
        True,
        n_conversations=1,
    )
    if not turns:
        return False, {"error": "no turns measured"}
    label = os.path.splitext(os.path.basename(model))[0]
    dump = os.path.join(results_dir, f"{label}-rung{rung}-speed.json")
    with open(dump, "w") as f:
        json.dump(turns, f)
    verdict = speed_gate.analyze(model, no_thinking=True, dump_override=dump)
    cost = next(
        (m["mem_cost_gib"] for m in mem_reports if m.get("mem_cost_gib") is not None),
        None,
    )
    verdict["mem_cost_gib"] = cost
    return verdict.get("stall_rate", 1.0) <= speed_gate.STALL_RATE_MAX, verdict


def fwe_pass(
    model: str, rung: int, results_dir: str, seed: int, port: int
) -> tuple[bool, dict[str, Any]]:
    """One FWE cell at depth=rung-2x headroom, n=1, on its own server
    launch at exactly the rung's ctx (ruler_gate's launch shape: one
    slot, banner guard)."""
    label = os.path.splitext(os.path.basename(model))[0]
    depth = rung - 2 * ruler_gate.ANSWER_HEADROOM
    csv_path = os.path.join(results_dir, f"{label}-{depth}-fwe.csv")
    if os.path.exists(csv_path):
        os.remove(csv_path)
    log_path = os.path.join(results_dir, f"{label}-rung{rung}-fwe-server.log")
    llama_server.drop_file_cache(model)
    proc, healthy = llama_server.start_server(
        model,
        port=port,
        extra_args=["-c", str(rung), "--parallel", "1"],
        log_path=log_path,
    )
    try:
        if not healthy or not llama_server.wait_healthy(port, proc=proc):
            return False, {"error": "fwe server did not come up"}
        row = ruler_gate.run_fwe_depth(
            port, label, depth, 1, csv_path, seed0=seed, no_thinking=True
        )
    finally:
        llama_server.stop_server(proc, port)
    return row["acc"] == 1.0, row


def main() -> None:
    tee_output.install()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("models", nargs="+", help="GGUF paths")
    p.add_argument("--corpus", default=speed_gate.CORPUS_DEFAULT)
    p.add_argument("--port", type=int, default=8210)
    p.add_argument("--results-dir", default="ladder-results")
    p.add_argument("--seed", type=int, default=1024)
    p.add_argument("--max-rung", type=int, default=None, help="stop after this rung (debug)")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="preflight only: verify paths, print the plan, launch nothing",
    )
    args = p.parse_args()

    if args.dry_run:
        raise SystemExit(dry_run(args))

    os.makedirs(args.results_dir, exist_ok=True)
    table = []
    for model in args.models:
        label = os.path.splitext(os.path.basename(model))[0]
        print(f"\n=== ladder: {label} ===")
        if not os.path.exists(model):
            print(f"  SKIP: file not found ({model}) - fix the path and re-run")
            continue
        print(f"  rungs from {RUNG_BASE}, doubling until the speed gate fails")
        score = 0
        rung = RUNG_BASE
        model_t0 = time.monotonic()
        while True:
            t0 = time.monotonic()
            ok_s, sv = speed_pass(model, rung, args.corpus, args.port, args.results_dir)
            t_speed = time.monotonic() - t0
            print(
                f"  rung {rung}: speed {'PASS' if ok_s else 'FAIL'} [{t_speed:.0f}s]",
                flush=True,
            )
            if sv.get("mem_cost_gib") is not None:
                print(f"    cold machine cost @ rung: {sv['mem_cost_gib']:.2f} GiB")
            if not ok_s:
                print(f"    speed verdict: {json.dumps(sv)[:200]}")
                break
            t0 = time.monotonic()
            ok_f, fv = fwe_pass(model, rung, args.results_dir, args.seed, args.port)
            t_fwe = time.monotonic() - t0
            print(
                f"    fwe @ depth {fv['depth']}: "
                f"{fv['correct']}/{fv['n']} -> {'PASS' if ok_f else 'FAIL'} "
                f"[{t_fwe:.0f}s]",
                flush=True,
            )
            if not ok_f:
                break
            score = rung
            if args.max_rung and rung >= args.max_rung:
                break
            rung *= 2
        model_t = time.monotonic() - model_t0
        print(
            f"  {label}: SCORE = {score} tokens (last rung passing both) "
            f"[{model_t / 60:.1f} min wall, measured - the time command retired, session 34]"
        )
        table.append({"model": label, "score": score})
    print("\n=== ladder table ===")
    for row in sorted(table, key=lambda r: -r["score"]):
        print(f"  {row['model']}: {row['score']} tokens")


if __name__ == "__main__":
    main()
