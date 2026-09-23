#!/usr/bin/env python3
"""
paired-arc.py — McNemar paired analysis for strict-ARC runs (Study #2 edition)

Reads the per-question CSVs written by strict-arc.py --csv, pairs configs
question-by-question, and runs exact McNemar (binomial) tests on every
pair. This is the correct test when all configs answered the SAME
questions; the unpaired z-test is needlessly conservative.

Inputs: strict-arc.py writes one CSV per model:
    <ModelFirstName>-arc-timing.csv   (columns: model,question,correct,seconds,prompt_chars)

Usage:
    python3 paired-arc.py                    # all pairs among all CSVs found
    python3 paired-arc.py --dir some/other   # point at another results dir
    python3 paired-arc.py --alpha 0.01       # stricter threshold
"""

import argparse
import csv
import math
import os
import sys
from itertools import combinations

# ============ EDIT ME ============
DEFAULT_DIR = os.path.expanduser("~/technical_reports/102.4/arc-results")
# =================================


def load_csvs(results_dir):
    """Return {model_name: {question_index: correct_bool}} for every
    *-arc-timing.csv in the directory. Questions with exceptions (missing
    rows) are simply absent for that model and are dropped from pairs."""
    models = {}
    for fname in sorted(os.listdir(results_dir)):
        if not fname.endswith("-arc-timing.csv"):
            continue
        path = os.path.join(results_dir, fname)
        per_q = {}
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                per_q[int(row["question"])] = bool(int(row["correct"]))
        # model name from the file's own rows; fall back to filename
        name = fname.replace("-arc-timing.csv", "")
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = row["model"]
                break
        models[name] = per_q
    return models


def binom_two_sided(k, n, p=0.5):
    """Exact two-sided binomial p-value for observing k successes of n."""
    def pmf(i):
        return math.comb(n, i) * p ** i * (1 - p) ** (n - i)
    pk = pmf(k)
    return min(1.0, sum(pmf(i) for i in range(n + 1) if pmf(i) <= pk + 1e-12))


def mcnemar_exact(b, c):
    """Exact McNemar test. b = discordant count model1 right/model2 wrong,
    c = model1 wrong/model2 right. Returns p-value."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return binom_two_sided(k, n)


def main():
    ap = argparse.ArgumentParser(description="Paired (McNemar exact) analysis of strict-ARC CSVs")
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--alpha", type=float, default=0.05)
    args = ap.parse_args()

    models = load_csvs(args.dir)
    if len(models) < 2:
        print(f"Need at least 2 model CSVs in {args.dir} (found {len(models)})", file=sys.stderr)
        sys.exit(1)

    names = sorted(models)
    print(f"Models found ({len(names)}):")
    for m in names:
        print(f"  {m}  ({len(models[m])} questions)")
    print()

    print(f"{'pair':55s} {'n_common':>8s} {'only1':>6s} {'only2':>6s} {'diff_pp':>8s} {'p_exact':>9s}  sig")
    print("-" * 100)

    rows = []
    for m1, m2 in combinations(names, 2):
        common = set(models[m1]) & set(models[m2])
        if not common:
            continue
        b = sum(1 for q in common if models[m1][q] and not models[m2][q])
        c = sum(1 for q in common if not models[m1][q] and models[m2][q])
        n = len(common)
        diff_pp = 100 * (b - c) / n  # exact paired difference on common set
        p = mcnemar_exact(b, c)
        sig = "YES" if p < args.alpha else ""
        rows.append((m1, m2, n, b, c, diff_pp, p, sig))

    # most significant first
    rows.sort(key=lambda r: (r[6], -abs(r[5])))
    for m1, m2, n, b, c, diff_pp, p, sig in rows:
        print(f"{m1[:24]} vs {m2[:24]:29s} {n:8d} {b:6d} {c:6d} {diff_pp:+8.2f} {p:9.4f}  {sig}")

    print("\nLegend: only1 = questions m1 got right and m2 wrong; diff_pp = paired")
    print(f"difference (b-c)/n; p_exact = exact two-sided McNemar. alpha = {args.alpha}.")
    print("Pairs where only1+only2 = 0 are perfectly concordant (p = 1).")
    print("Note: every pair of models is tested — for m models this is m*(m-1)/2 tests;")
    print("with 11 configs = 55 comparisons, expect ~2-3 'significant' results by chance.")
    print("Treat marginal p-values (0.01 < p < 0.05) with multiple-comparison caution")


if __name__ == "__main__":
    main()