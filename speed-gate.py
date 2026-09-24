#!/usr/bin/env python3
"""speed-gate.py -- the worst-turn speed gate (llama-server interface).

Bench + verdict stages of the pipeline (its phases 3-4): run
live-bench.py against a model file (1 rep, the committed corpus) and
compute the worst-turn verdict - PASS if worst turn >= floor - 2*sigma
(lenient 2-sigma ruling, 2026-09-23). Everything that launches or
talks to llama-server for the gate lives here, including the
mode-suffixed dump naming.

Mode rule (owner ruling 2026-09-24, rule 8): hybrid models are allowed
in BOTH categories and must run in the category's mode. Dumps are
name-separated per mode - a thinking-mode dump must NEVER be reused by
a non-thinking run (or vice versa) because the resume check compares
timestamps only (Session 25 bug: a --no-thinking run inherited
thinking-mode dumps and reported the thinking gate numbers as its own).

Standalone use (from the repo root):
    python3 speed-gate.py \
        --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q5_K_M.gguf \
        --thinking --floor 20
    python3 speed-gate.py --model <file> --no-thinking

Imported by full-benchmark.py (bench, analyze, live_dump_name).
"""

import argparse
import json
import math
import os
import subprocess
import sys

LIVE_BENCH = "./live-bench.py"
CORPUS_DEFAULT = "./live-corpus.json"
FLOOR_DEFAULT = 20.0

GUIDE = {
    3: [
        "llama-server missing: ./llama-b10964-gpu/llama-server must exist",
        "corpus missing: python3 live-bench.py --make-corpus",
        "port conflict: stop other llama-server instances (or pass --port)",
        "GPU stack: the server startup log names the GPU - it must "
        "be the real one via the vendor driver, never a software "
        "rasterizer (llvmpipe on Linux)",
    ],
    4: [
        "dump unreadable: the .live-dump.json is malformed or empty",
        "if the bench was interrupted, delete the dump and rerun "
        "(phase 3 will redo it)",
    ],
}


def fail(phase, rung, what, causes):
    """Abort loudly for one phase, with reader guidance."""
    print()
    print("=" * 60)
    print(f"PHASE {phase} FAILED at {rung}: {what}")
    print("Possible causes and fixes:")
    for c in causes:
        print(f"  - {c}")
    print("Fix the cause, then RERUN THE SAME COMMAND: the script is")
    print("idempotent and will resume from this phase.")
    print("=" * 60)
    sys.exit(1)


def live_dump_name(path, thinking=False, no_thinking=False):
    """Mode-suffixed dump name: a thinking-mode dump must NEVER be reused
    by a non-thinking run (or vice versa) - the resume check compares
    timestamps only, so the mode must live in the filename (Session 25
    bug: --no-thinking run inherited thinking-mode dumps and reported
    the thinking gate numbers as its own)."""
    if thinking:
        return path + ".live-dump.think.json"
    if no_thinking:
        return path + ".live-dump.nothink.json"
    return path + ".live-dump.json"


def bench(path, corpus, dry_run, thinking=False, no_thinking=False,
          dump=None):
    """Phase 3: live-bench the model file; returns the dump path."""
    dump = dump or live_dump_name(path, thinking, no_thinking)
    label = os.path.basename(path)

    def dump_valid():
        if not os.path.isfile(dump):
            return False
        try:
            with open(dump) as f:
                turns = json.load(f)
        except Exception:
            return False
        return any(t.get("model") == label and t.get("server_tps")
                   for t in turns)

    if dump_valid() and os.path.getmtime(dump) > os.path.getmtime(path):
        print("  [3] reusing existing dump (newer than model file)")
        return dump
    if dry_run:
        return dump
    cmd = [sys.executable, LIVE_BENCH, "--corpus", corpus,
           "--models", path, "--repeats", "1", "--dump", dump]
    if thinking:
        cmd.append("--thinking")
    if no_thinking:
        cmd.append("--no-thinking")
    r = subprocess.run(cmd)
    if r.returncode != 0 or not dump_valid():
        fail(3, label, "live-bench.py failed or produced no usable dump "
             "(see its output above)", GUIDE[3])
    return dump


def analyze(path, floor, thinking=False, no_thinking=False):
    """Phase 4: worst-turn verdict from the dump."""
    dump = live_dump_name(path, thinking, no_thinking)
    label = os.path.basename(path)
    try:
        with open(dump) as f:
            turns = json.load(f)
    except Exception as e:
        fail(4, label, f"cannot read dump: {e}", GUIDE[4])
    mine = [t for t in turns
            if t.get("model") == label and t.get("server_tps")]
    if not mine:
        fail(4, label, "dump has no turns for this model", GUIDE[4])
    convs = {}
    for t in mine:
        convs.setdefault(t["conv"], []).append(t["server_tps"])
    conv_worsts = [min(v) for v in convs.values()]
    worst = min(conv_worsts)
    mean = sum(t["server_tps"] for t in mine) / len(mine)
    if len(conv_worsts) > 1:
        mu = sum(conv_worsts) / len(conv_worsts)
        sd = math.sqrt(sum((w - mu) ** 2 for w in conv_worsts)
                       / (len(conv_worsts) - 1))
        sigma = sd / math.sqrt(len(conv_worsts))
    else:
        sigma = 0.0
    threshold = floor - 2 * sigma
    if worst >= floor:
        verdict = "PASS (confident)"
    elif worst >= threshold:
        verdict = "PASS (within 2-sigma)"
    else:
        verdict = "FAIL"
    return {"worst": worst, "mean": mean, "sigma": sigma,
            "threshold": threshold, "verdict": verdict,
            "n_turns": len(mine), "n_convs": len(conv_worsts),
            "dump": dump}


# =========================================================== main

def main():
    ap = argparse.ArgumentParser(
        description="speed gate: live-bench a model file and grade the "
                    "worst turn against the floor (llama-server interface)")
    ap.add_argument("--model", required=True, help=".gguf file to bench")
    ap.add_argument("--corpus", default=CORPUS_DEFAULT)
    ap.add_argument("--floor", type=float, default=FLOOR_DEFAULT)
    ap.add_argument("--dump", default=None,
                    help="live-dump path override (default: next to the "
                         "model file, mode-suffixed)")
    ap.add_argument("--thinking", action="store_true",
                    help="thinking mode (category protocol, rule 8)")
    ap.add_argument("--no-thinking", action="store_true",
                    help="hybrid model, non-thinking category (rule 8)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.thinking and args.no_thinking:
        ap.error("--thinking and --no-thinking are mutually exclusive")

    path = args.model
    if not args.dry_run and not os.path.isfile(path):
        sys.exit(f"model file not found: {path}")
    if not args.dry_run and not os.path.isfile(LIVE_BENCH):
        sys.exit(f"live-bench.py not found at {LIVE_BENCH} - run from "
                 "the repo root")
    if not args.dry_run and not os.path.isfile(args.corpus):
        sys.exit(f"corpus not found at {args.corpus} - build it: "
                 "python3 live-bench.py --make-corpus")

    dump = bench(path, args.corpus, args.dry_run, args.thinking,
                 args.no_thinking, args.dump)
    if args.dry_run:
        print(f"[3] would live-bench {path} (dump: {dump})")
        print(f"[4] would analyze (floor {args.floor:g} - 2*sigma)")
        return
    res = analyze(path, args.floor, args.thinking, args.no_thinking)
    res["dump"] = dump
    print(f"[4] worst {res['worst']:.1f} t/s "
          f"(mean {res['mean']:.1f}, sigma {res['sigma']:.2f}, "
          f"threshold {res['threshold']:.1f}) -> {res['verdict']}")


if __name__ == "__main__":
    main()
