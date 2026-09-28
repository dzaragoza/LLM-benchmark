#!/usr/bin/env python3
"""lag_analyze.py -- Andes-style streaming-lag analysis of live dumps.

Post-hoc companion to the benchmark pipeline (Session 26, addendum 7).
Reads the .live-dump.*.json files the speed gate already wrote; never
launches a server; writes nothing except optional JSON. Same layer as
law_fit.py - an analysis instrument, not a pipeline phase.

WHY: the comfort analysis is a WORST-TURN story, and the QoE argument
(Andes, arXiv 2404.16283) is that user experience degrades with the
lateness of individual tokens - average TPOT hides mid-stream stalls.
The dumps hold one server_tps value per TURN (not per token), so this
tool prices lag at turn granularity: a turn slower than the reader's
consumption speed is a stall the reader feels in full.

THE TWO LINES (Session 26 ruling):
  guarantee     k=1: never slower than the anchor reader (worst turn)
  (addendum 50: the recommended k=3 floor-20 line is deleted - an
  observation for the report, not a protocol constant)

METRICS per rung (dump):
  turns             number of turns with a server_tps reading
  mean/min          turn t/s mean and minimum
  p50/p95           turn t/s percentiles (nearest-rank)
  worst/mean        the pure delivery-variance ratio (addendum-6
                    pre-registration: predicted 0.75-0.90)
  stall fraction    fraction of turns slower than each threshold:
                    the reader line (5.0 w/s, each turn's measured
                    words/s; addendum 44) and the default line (20 t/s)
  S_delay           Andes-style lateness area, in reader-seconds per
                    conversation: sum over turns of
                    (turn_wall_seconds - turn_words/reader_wps)
                    clipped at 0 - how many seconds the reader spent
                    waiting on text that had not arrived yet (only
                    turns slower than the reader generate lateness)
  kv-slope          t/s of turn n vs turn n-1 within conversations:
                    mean of t_n/t_(n-1) over sequential turn pairs -
                    < 1.0 means turns slow down as context grows
                    (the KV-growth signature, addendum-7 prediction 4)

Usage (from the repo root, on the machine that ran the benchmark):

    python3 lag_analyze.py                                    # *.live-dump*.json
    python3 lag_analyze.py --dump q5.live-dump.json --dump q8.live-dump.think.json
    python3 lag_analyze.py --reader-wps 5.0 --default-tp 20.0
    python3 lag_analyze.py --json lag-report.json

One machine's dumps per invocation (same rule as law_fit.py).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from speed_gate import READER_WPS_DEFAULT

# addendum 44: the 6.5 t/s reader line (300 wpm at 0.75 w/t) is
# DELETED - second-order magic inheriting the unanchored 0.75. The
# stall metrics are re-anchored to the study's single anchor, 5.0
# w/s, computed from each turn's MEASURED server_wps (v2.1 dumps).
# Addendum 50: the k=3 floor-20 default line is deleted with the
# floor itself - stlD is retired, stlR is the only stall metric.
READER_WPS = READER_WPS_DEFAULT


def load_dumps(paths: list[str]) -> list[dict[str, Any]]:
    """Read dumps; return a list of {path, label, turns}."""
    dumps = []
    for p in paths:
        if not os.path.isfile(p):
            print(f"  warning: dump not found, skipped: {p}", file=sys.stderr)
            continue
        with open(p) as f:
            data = json.load(f)
        turns = data if isinstance(data, list) else data.get("turns", [])
        turns = [t for t in turns if t.get("server_tps")]
        if not turns:
            print(f"  warning: no turn timings in {p}, skipped", file=sys.stderr)
            continue
        label = (data.get("label") if isinstance(data, dict) else None) or os.path.basename(p)
        dumps.append({"path": p, "label": label, "turns": turns})
    return dumps


def percentile(sorted_vals: list[float], q: float) -> float | None:
    """Nearest-rank percentile of a sorted list."""
    if not sorted_vals:
        return None
    idx = max(0, min(len(sorted_vals) - 1, round(q / 100.0 * len(sorted_vals)) - 1))
    return sorted_vals[idx]


def analyze_dump(dump: dict[str, Any], reader_wps: float) -> dict[str, Any]:
    """All lag metrics for one dump. Reader-line metrics are in WORDS
    per second (addendum 44): each turn's measured server_wps vs the
    5.0 w/s anchor. (The k=3 default-line stall fraction stlD is
    deleted with the floor, addendum 50.) Turns without measured
    w/s (protocol-v1 dumps) are excluded from the reader metrics
    and counted in `legacy_turns`."""
    turns = dump["turns"]
    tps = sorted(t["server_tps"] for t in turns)
    mean = sum(tps) / len(tps)
    worst = tps[0]
    ratio = worst / mean if mean else None

    wps = [t["server_wps"] for t in turns if t.get("server_wps")]
    legacy = len(turns) - len(wps)
    stall_reader = (sum(1 for w in wps if w < reader_wps) / len(wps)) if wps else None

    s_delay = 0.0
    convs = {}
    for t in turns:
        convs.setdefault(t["conv"], []).append(t)
    for ci in sorted(convs):
        seq = convs[ci]
        for t in seq:
            words = t.get("gen_words") or 0
            w = t.get("server_wps")
            if not words or not w:
                continue
            wall = words / w
            ideal = words / reader_wps
            s_delay += max(0.0, wall - ideal)
    # normalize: reader-seconds of lateness per conversation-second
    n_convs = len(convs) or 1

    kv_pairs = []
    for ci in sorted(convs):
        seq = sorted(convs[ci], key=lambda t: t.get("turn", 0))
        for a, b in zip(seq, seq[1:], strict=False):
            if a.get("server_tps") and b.get("server_tps"):
                kv_pairs.append(b["server_tps"] / a["server_tps"])
    kv_slope = (sum(kv_pairs) / len(kv_pairs)) if kv_pairs else None

    return {
        "label": dump["label"],
        "turns": len(tps),
        "mean": mean,
        "min": worst,
        "p50": percentile(tps, 50),
        "p95": percentile(tps, 95),
        "worst_over_mean": ratio,
        "stall_frac_reader": stall_reader,
        "legacy_turns": legacy,
        "s_delay_reader_sec": s_delay,
        "s_delay_per_conv": s_delay / n_convs,
        "kv_slope": kv_slope,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Andes-style streaming-lag analysis of live dumps "
        "(turn-granularity stall metrics vs the reader line)"
    )
    ap.add_argument(
        "--dump",
        action="append",
        default=[],
        help="live dump file (repeatable); default: all *.live-dump*.json in cwd",
    )
    ap.add_argument(
        "--reader-wps",
        type=float,
        default=READER_WPS,
        help=f"reader consumption speed in w/s (default "
        f"{READER_WPS:g} = 300 wpm, Brysbaert 2019 - the "
        f"study's single anchor; stall metrics use each "
        f"turn's MEASURED words/s, addendum 44)",
    )
    ap.add_argument("--json", default=None, help="write the per-dump metrics to this JSON file")
    args = ap.parse_args()

    paths = args.dump or sorted(glob.glob("*.live-dump*.json"))
    if not paths:
        sys.exit(
            "no dumps found: pass --dump paths or run from a directory holding *.live-dump*.json"
        )
    dumps = load_dumps(paths)
    if not dumps:
        sys.exit("no usable dumps (files missing or no turn timings)")

    print("=" * 72)
    print(f"LAG ANALYSIS  (reader line {args.reader_wps:g} w/s = k=1 guarantee, measured words/s)")
    print("=" * 72)

    results = []
    for d in dumps:
        results.append(analyze_dump(d, args.reader_wps))

    hdr = (
        f"  {'rung (dump)':28} {'turns':>5} {'mean':>5} {'min':>5} "
        f"{'p50':>5} {'p95':>5} {'w/m':>5} {'stlR':>5} "
        f"{'Sdel':>6} {'kv':>5}"
    )
    print(hdr)
    for r in results:
        kv = f"{r['kv_slope']:.2f}" if r["kv_slope"] is not None else "-"
        print(
            f"  {r['label'][:28]:28} {r['turns']:5d} {r['mean']:5.1f} "
            f"{r['min']:5.1f} {r['p50']:5.1f} {r['p95']:5.1f} "
            f"{r['worst_over_mean']:5.2f} "
            f"{r['stall_frac_reader']:5.1%} "
            f"{r['s_delay_per_conv']:6.2f} {kv:>5}"
        )

    print()
    print("  reading the table:")
    print("    w/m   = worst/mean turn t/s (addendum-6 pre-registration:")
    print("            predicted 0.75-0.90; < 0.75 needs a story)")
    print(
        "    stlR  = fraction of turns below the READER line in "
        "measured words/s (k=1 guarantee: target ~0; addendum 44)"
    )
    print("    Sdel  = Andes-style lateness per conversation, in reader-seconds")
    print(
        "    kv    = mean t_(n)/t_(n-1) within conversations (< 1.0 = turns slow as context grows)"
    )

    if args.json:
        with open(args.json, "w") as f:
            json.dump(
                {
                    "reader_wps": args.reader_wps,
                    "dumps": results,
                },
                f,
                indent=1,
            )
        print(f"\nmetrics written to {args.json}")


if __name__ == "__main__":
    main()
