#!/usr/bin/env python3
"""probe_gen_len.py -- the dyadic -n probe: where does llama-bench's
measured tg/s converge (or keep decaying) as the generation length
grows? One model file, one rung, a dyadic ladder of -n values.

The v8 use: the exam showed the -n 128 burst rate overestimates the
sustained fill rate (granite-4.0-350m: bench 98.3, exam avg 51.9 over
a 32k fill = 0.53). This probe walks -n dyadically up to the exam's
own fill scale and prints the decay curve - the sweet spot of n is
where the curve flattens (measuring shorter inflates the rate;
measuring longer buys nothing).

Not part of the benchmark: a one-shot diagnostic, its output is
meant to be pasted into the lab notebook / a commit message.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import infra.hf_download as hf_download

BENCH_BIN = os.path.join(
    ".", "llama-b11669", "llama-bench.exe" if os.name == "nt" else "llama-bench"
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("family", help="family name, e.g. granite-4.0-350m")
    ap.add_argument("rung", nargs="?", default="F16", help="the rung (default F16)")
    ap.add_argument("--models-dir", default="./models")
    ap.add_argument(
        "--max-n",
        type=int,
        default=32768,
        help="the ladder's top -n (default 32768 - the exam fill scale "
        "of the worst-discrepancy case)",
    )
    ap.add_argument("--min-n", type=int, default=128)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument(
        "--reference",
        type=float,
        default=None,
        help="an observed sustained rate (e.g. the exam's "
        "answer_tokens/elapsed_s) to print the ratio against",
    )
    ap.add_argument(
        "--kv",
        default=None,
        help="quantize the KV cache both axes (e.g. q4_0) - the A/B "
        "experiment: a 4x smaller cache should flatten the token/"
        "KV-driven part of the decay while leaving thermal decay "
        "alone. Uses -fa on (required for cache quant)",
    )
    args = ap.parse_args()

    famdir = os.path.join(args.models_dir, args.family)
    path = hf_download.local_rung(famdir, args.rung)
    if not path:
        sys.exit(f"no local rung {args.rung} for {args.family} in {famdir}")

    ns = []
    n = args.min_n
    while n <= args.max_n:
        ns.append(n)
        n *= 2
    if ns[-1] != args.max_n:
        ns.append(args.max_n)

    print(f"# dyadic -n probe: {args.family} {args.rung} ({os.path.basename(path)})")
    if args.kv:
        print(f"# KV cache quantized: k={args.kv} v={args.kv} (-fa on)")
    print(f"# {'n':>7} {'tg/s':>8} {'seconds':>8} {'vs first':>9}")
    first = None
    for n in ns:
        cmd = [BENCH_BIN, "-m", path, "-p", "0", "-n", str(n), "-r", str(args.repeat), "-o", "csv"]
        if args.kv:
            cmd += ["-fa", "on", "--cache-type-k", args.kv, "--cache-type-v", args.kv]
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=7200,
        )
        tg = None
        for row in csv.DictReader(io.StringIO(r.stdout)):
            if row.get("avg_ts"):
                try:
                    tg = float(row["avg_ts"])
                except ValueError:
                    pass
        if tg is None:
            print(f"# n={n}: llama-bench failed: {r.stderr.strip()[:120]}")
            continue
        if first is None:
            first = tg
        secs = n / tg
        ratio = tg / first
        print(f"# {n:>7} {tg:>8.2f} {secs:>8.1f} {ratio:>9.2f}")
    if args.reference is not None and first is not None:
        print(f"# reference sustained rate: {args.reference} "
              f"({args.reference / first:.2f} of the n={ns[0]} burst)")
    print("# the sweet n: the first row where the curve flattens; "
          "still decaying at the top means the decay is thermal/time-driven, "
          "not token-driven")


if __name__ == "__main__":
    main()
