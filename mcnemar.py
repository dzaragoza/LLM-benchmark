#!/usr/bin/env python3
"""mcnemar.py -- exact McNemar ranking on ARC result CSVs.

Ranking stage of the pipeline (its phase 6): read the per-question ARC
CSVs, score every model, run pairwise exact (binomial) McNemar on all
pairs, and print the final RANKING with consecutive-rank separation
verdicts at p < 0.05. The statistic is exact - no asymptotic shortcut.

Standalone use (from the repo root):
    python3 mcnemar.py --labels "Phi-3-mini Q6_K,Qwen3.5-4B Q5_K_M"
    python3 mcnemar.py --arc-models-dir ./arc-results --arc-num 1172

Imported by full-benchmark.py (rank, pairs_from_csvs, csv_per_question).
"""

import argparse
import csv as _csv
import math
import os
import sys
from itertools import combinations

ARC_NUM_DEFAULT = 1172   # full ARC-Challenge test split (author ruling 2026-09-23)
ARC_RESULTS_DIR_DEFAULT = "./arc-results"

GUIDE = {
    6: [
        "CSVs disagree on question count: rerun with the same --arc-num",
        "a CSV is missing: rerun (phase 5 is idempotent per model)",
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


def safe_label(label):
    return "".join(ch if ch.isalnum() or ch in "-_." else "_"
                   for ch in label)


def arc_csv_path(arc_dir, label):
    return os.path.join(arc_dir, safe_label(label) + "-arc-timing.csv")


def csv_per_question(path, label, arc_num, arc_dir):
    """Load one model's CSV as {question_id: correct_bool}; fail if
    missing or short. path may be None to resolve from label+arc_dir."""
    p = path if path else arc_csv_path(arc_dir, label)
    if not os.path.isfile(p):
        fail(6, label, f"ARC CSV missing (expected {arc_num} questions)",
             GUIDE[6])
    per_q = {}
    try:
        with open(p, newline="", encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                per_q[int(row["question"])] = bool(int(row["correct"]))
    except Exception as e:
        fail(6, label, f"cannot read ARC CSV {p}: {e}", GUIDE[6])
    if len(per_q) != arc_num:
        fail(6, label, f"ARC CSV short ({len(per_q)}/{arc_num} questions) - "
             "rerun the ARC stage for this model", GUIDE[6])
    return per_q


# =========================================================== statistic

def binom_two_sided(k, n, p=0.5):
    def pmf(i):
        return math.comb(n, i) * p ** i * (1 - p) ** (n - i)
    pk = pmf(k)
    return min(1.0, sum(pmf(i) for i in range(n + 1)
                        if pmf(i) <= pk + 1e-12))


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return binom_two_sided(min(b, c), n)


def pairs_from_csvs(models, arc_num, arc_dir):
    """models: {label: per_question_dict}. Returns the pairs dict."""
    scores = {m: sum(v.values()) for m, v in models.items()}
    ranking = sorted(models, key=lambda m: (-scores[m], m))

    pairs = {}
    for m1, m2 in combinations(sorted(models), 2):
        common = set(models[m1]) & set(models[m2])
        b = sum(1 for q in common if models[m1][q] and not models[m2][q])
        c = sum(1 for q in common if not models[m1][q] and models[m2][q])
        diff = 100 * (b - c) / len(common) if common else 0.0
        pairs[f"{m1}|{m2}"] = {"n_common": len(common), "only1": b,
                              "only2": c, "diff_pp": diff,
                              "p_exact": mcnemar_exact(b, c)}
    return ranking, scores, pairs


def print_ranking(ranking, scores, pairs, arc_num):
    print()
    print("=" * 60)
    print(f"FINAL RANKING (ARC-Challenge, n={arc_num}, exact McNemar)")
    for i, m in enumerate(ranking, 1):
        print(f"  {i}. {m}: {scores[m]}/{arc_num} = "
              f"{100 * scores[m] / arc_num:.1f}%")
    print("-" * 60)
    print("consecutive-pair McNemar (does the rank order separate?)")
    for i in range(len(ranking) - 1):
        m1, m2 = ranking[i], ranking[i + 1]
        key = f"{m1}|{m2}" if f"{m1}|{m2}" in pairs else f"{m2}|{m1}"
        p = pairs[key]
        print(f"  #{i + 1} vs #{i + 2}: {p['diff_pp']:+.2f} pp  "
              f"(b={p['only1']}, c={p['only2']}, n={p['n_common']}), "
              f"p = {p['p_exact']:.4f}"
              f"{'  SEPARATED' if p['p_exact'] < 0.05 else '  (not separated)'}")
    print("=" * 60)


def rank(labels, arc_num, arc_dir):
    """Pairwise exact McNemar; the pipeline's FINAL OUTPUT is this
    ranking. Returns (ranking, scores, pairs)."""
    models = {}
    for label in labels:
        models[label] = csv_per_question(None, label, arc_num, arc_dir)
    ranking, scores, pairs = pairs_from_csvs(models, arc_num, arc_dir)
    print_ranking(ranking, scores, pairs, arc_num)
    return ranking, scores, pairs


# =========================================================== main

def main():
    ap = argparse.ArgumentParser(
        description="exact McNemar ranking from per-question ARC CSVs")
    ap.add_argument("--labels", required=True,
                    help="comma-separated model labels (CSV filenames "
                         "are <safe_label>-arc-timing.csv)")
    ap.add_argument("--arc-num", type=int, default=ARC_NUM_DEFAULT,
                    help="ARC-Challenge questions (default: full 1172)")
    ap.add_argument("--arc-models-dir", default=ARC_RESULTS_DIR_DEFAULT,
                    help="directory holding the ARC timing CSVs")
    args = ap.parse_args()

    labels = [x.strip() for x in args.labels.split(",") if x.strip()]
    if not labels:
        sys.exit("no labels given")
    rank(labels, args.arc_num, args.arc_models_dir)


if __name__ == "__main__":
    main()
