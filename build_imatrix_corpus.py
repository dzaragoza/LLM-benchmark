#!/usr/bin/env python3
"""build_imatrix_corpus.py - flatten the arena English sample into plain
calibration text for llama-imatrix.

Reads arena/english_sample.json (the LMSYS-Chat-1M English extract,
conversation-role format) and writes data/imatrix-corpus.txt: turns
capped at a total of 256 KB (~55k tokens). The imatrix needs far less
data than people assume - activations stabilize within tens of
thousands of tokens; 100k+ is the comfortable community standard, and
256 KB of arena text sits safely above it while keeping the
llama-imatrix pass minutes, not hours. Assistant and user turns alike
(the imatrix wants representative activations over natural text, not a
dialogue structure). Deterministic - same input, same output; safe to
rerun.

Usage:
  python3 build_imatrix_corpus.py [--input arena/english_sample.json]
                                  [--output data/imatrix-corpus.txt]
                                  [--max-bytes 262144]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="flatten the arena English sample to imatrix calibration text"
    )
    ap.add_argument("--input", default=os.path.join(ROOT, "arena", "english_sample.json"))
    ap.add_argument("--output", default=os.path.join(ROOT, "data", "imatrix-corpus.txt"))
    ap.add_argument("--max-bytes", type=int, default=256 * 1024)
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        convs = json.load(f)
    if not isinstance(convs, list) or not convs:
        sys.exit(f"unexpected input shape: {args.input}")

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    n_turns = 0
    n_convs = 0
    with open(args.output, "w", encoding="utf-8") as out:
        for c in convs:
            if out.tell() >= args.max_bytes:
                break
            wrote = False
            for turn in c.get("conversation", []):
                text = (turn.get("content") or "").strip()
                if text:
                    out.write(text + "\n\n")
                    n_turns += 1
                    wrote = True
            if wrote:
                n_convs += 1
    size = os.path.getsize(args.output)
    print(
        f"{args.output}: {n_convs}/{len(convs)} conversations, {n_turns} turns, {size / 1024:.0f} KB"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
