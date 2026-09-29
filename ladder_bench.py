#!/usr/bin/env python3
"""ladder_bench.py -- the depth-ladder orchestrator (addendum 137).

The ranking instrument for the addendum-136 frontier: a model's score
is the DEEPEST dyadic rung at which it BOTH serves the reader (speed
gate, the guarantee) AND counts (FWE, quality-at-depth) -- reduced
rules: n=1 per gate per rung, the author's screening speed tier.

Per model, the ladder climbs 1024, 2048, ... up to
min(mechanical ceiling, model max context):
  1. speed gate at ctx = rung (n=1 conversation, the fastest honest
     shape: real blob prefill, real turns, real reader wall)
  2. if the speed gate passes: FWE at depth = rung - headroom (n=1)
  3. both pass -> the model's score advances to this rung; either
     fails -> the ladder STOPS (the author's rule: the score is the
     LAST rung both passed)

The speed gate and ruler gate are used AS LIBRARIES (their own
launch, banner guard, preflight, budgeting); nothing is re-implemented
here. Model max context comes from the GGUF metadata via a dry
server launch (the banner's n_ctx_train), the mechanical ceiling
from the KV budget at the reader line (law_fit.kv_gib, the
addendum-130 formula), capped by RAM (llama_server.system_memavailable_gib).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import llama_server
import ruler_gate
import speed_gate

RUNG_BASE = 1024


def gguf_max_context(model: str, port: int, arch: str) -> tuple[int, str]:
    """Model max context: launch the server once and read n_ctx_train
    from the banner (the metadata value; --override-kv lifted to a
    sentinel so the cap cannot silently clamp the probe)."""
    log_path = model + ".ladder-probe.log"
    proc, healthy = llama_server.start_server(
        model,
        port=port,
        extra_args=["-c", "4096", "--parallel", "1"],
        log_path=log_path,
    )
    n_train: int | None = None
    try:
        if not healthy or not llama_server.wait_healthy(port, proc=proc):
            sys.exit("ladder: probe server did not come up")
        import re

        with open(log_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.search(r"n_ctx_train\s*=?\s*(\d+)", line)
                if m:
                    n_train = int(m.group(1))
    finally:
        llama_server.stop_server(proc, port)
    if n_train is None:
        sys.exit(f"ladder: could not read n_ctx_train from {log_path}")
    return n_train, log_path


def mechanical_ceiling(model: str, n_train: int) -> int:
    """The KV-budget ceiling at the reader line (addendum-130 form):
    size_gib + kv_gib(depth) must fit usable RAM. Conservative: the
    KV per-token term is read from the file size doubling heuristic
    when config is unknown -- but the ladder NEVER exceeds n_train
    (the trained window is the hard wall, addendum 132), so the
    mechanical term only matters when it binds BELOW the trained
    window (tiny RAM, big model)."""
    file_gib = os.path.getsize(model) / (1024**3)
    ram = llama_server.system_memavailable_gib() or 4.0
    usable = ram - 0.4  # the standing OS reserve
    # KV at the worst-known rate for this study's families (12 KiB/tok,
    # the dense-0.5B and hybrid-0.8B coincide, addendum 133); a larger
    # model's denser KV only makes the ceiling SMALLER, which stops
    # the ladder EARLIER - the conservative direction for a screen.
    kv_per_tok_gib = 12 * 1024 / (1024**3)
    depth_kv_budget = max(0.0, usable - file_gib - 0.3)
    ceiling = int(depth_kv_budget / kv_per_tok_gib)
    return max(RUNG_BASE, min(n_train, ceiling))


def speed_pass(
    model: str, rung: int, corpus: str, port: int, results_dir: str
) -> tuple[bool, dict[str, Any]]:
    """One speed-gate cell at ctx=rung, n=1 conversation: real blob,
    real turns, the v3.1 verdict from those turns only (reduced rules:
    a screen, not a podium number). bench_model launches the server
    itself (banner guard included); the verdict is the REAL analyze()
    on a temp dump - the phase-4 code path, not a re-implementation."""
    turns, _, _ = speed_gate.bench_model(
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
    return verdict.get("stall_rate", 1.0) <= speed_gate.STALL_RATE_MAX, verdict


def fwe_pass(
    model: str, rung: int, results_dir: str, seed: int, port: int, arch: str
) -> tuple[bool, dict[str, Any]]:
    """One FWE cell at depth=rung-2x headroom, n=1, on its own server
    launch at exactly the rung's ctx (ruler_gate's launch shape: one
    slot, banner guard, no override - the ladder never exceeds the
    trained window, so the metadata cap is never fought)."""
    label = os.path.splitext(os.path.basename(model))[0]
    depth = rung - 2 * ruler_gate.ANSWER_HEADROOM
    csv_path = os.path.join(results_dir, f"{label}-{depth}-fwe.csv")
    if os.path.exists(csv_path):
        os.remove(csv_path)
    log_path = os.path.join(results_dir, f"{label}-rung{rung}-fwe-server.log")
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
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("models", nargs="+", help="GGUF paths")
    p.add_argument("--corpus", default=speed_gate.CORPUS_DEFAULT)
    p.add_argument("--port", type=int, default=8210)
    p.add_argument("--results-dir", default="ladder-results")
    p.add_argument("--seed", type=int, default=1024)
    p.add_argument("--max-rung", type=int, default=None, help="cap the ladder (debug)")
    args = p.parse_args()

    os.makedirs(args.results_dir, exist_ok=True)
    table = []
    for model in args.models:
        label = os.path.splitext(os.path.basename(model))[0]
        print(f"\n=== ladder: {label} ===")
        n_train, _ = gguf_max_context(model, args.port, "qwen2")
        ceiling = mechanical_ceiling(model, n_train)
        if args.max_rung:
            ceiling = min(ceiling, args.max_rung)
        rungs = []
        r = RUNG_BASE
        while r <= ceiling:
            rungs.append(r)
            r *= 2
        # keep the shave honest: a rung whose wanted ctx (rung + 2 x
        # ANSWER_HEADROOM) exceeds n_train is replaced by n_train - the
        # headroom (the 134b discipline)
        rungs = [min(rung, n_train - 2 * ruler_gate.ANSWER_HEADROOM) for rung in rungs]
        deduped: list[int] = []
        for rung in rungs:
            if rung not in deduped:
                deduped.append(rung)
        rungs = deduped
        print(f"  trained ctx {n_train}, mechanical ceiling {ceiling}, rungs {rungs}")
        score = 0
        for rung in rungs:
            ok_s, sv = speed_pass(model, rung, args.corpus, args.port, args.results_dir)
            print(f"  rung {rung}: speed {'PASS' if ok_s else 'FAIL'}", flush=True)
            if not ok_s:
                print(f"    speed verdict: {json.dumps(sv)[:200]}")
                break
            ok_f, fv = fwe_pass(model, rung, args.results_dir, args.seed, args.port, "qwen2")
            print(
                f"    fwe @ depth {fv['depth']}: "
                f"{fv['correct']}/{fv['n']} -> {'PASS' if ok_f else 'FAIL'}",
                flush=True,
            )
            if not ok_f:
                break
            score = rung
        print(f"  {label}: SCORE = {score} tokens (last rung passing both)")
        table.append({"model": label, "trained_ctx": n_train, "score": score})
    print("\n=== ladder table ===")
    for row in sorted(table, key=lambda r: -r["score"]):
        print(f"  {row['model']}: {row['score']} tokens")


if __name__ == "__main__":
    main()
