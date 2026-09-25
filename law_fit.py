#!/usr/bin/env python3
"""law_fit.py -- the bandwidth->size law: harvest, fit, right-size.

Standalone analysis companion to the benchmark pipeline (Session 26
direction pivot). Reads the state files and model files the pipeline
already produced; writes nothing except optional JSON. Not part of the
pipeline layers - it is a post-hoc instrument for the report's
right-sizing table.

THE LAW (within one model, across its quant ladder, on one machine):

    1/t  =  size/BW_eff  +  1/t_inf        (t = worst turn, t/s)

Generation reads the whole file per token, so its cost scales with
file size; a fixed per-token overhead (KV reads, dispatch) is
amortized better by bigger files. Two parameters: BW_eff (effective
GiB/s the inference stack actually achieves) and t_inf (the
compute-bound ceiling as size -> 0). A pure "BW / size" rule is the
one-parameter special case t_inf = infinity - Session 18q proved that
special case wrong (family-specific "constants" that were really the
missing second parameter).

THE GATE, REINTERPRETED: the worst-turn floor plus the ladder walk is
an empirical binary search for the law's zero: the largest file that
still meets the floor,

    size*(floor) = BW_eff * (1/floor - 1/t_inf)

This script harvests every measured (size, worst) pair from the state
files, fits the law, and prints size* - so the gate's boundary, found
per model by ~8 min of search, becomes predictable before any download.

RIGHT-SIZING (the practitioner's question, answered in file size -
the quantity bandwidth actually reads):

    biggest model that fits size* at a plateau rung (>= Q4_K_M);
    params are derivable (params_B ~ size_GiB * 8.59 / bpw) but bpw
    varies per model, so file size is the primary currency.

Usage (from the repo root, on the machine that ran the benchmark):

    python3 law_fit.py                          # ./benchmark-state.json
    python3 law_fit.py --state-file a.json --state-file b.json
    python3 law_fit.py --floor 20 --bw-theoretical 102.4
    python3 law_fit.py --point "session18q Qwen Q8_0,3.36,21.5"
    python3 law_fit.py --predict-size 5.0        # t/s at 5 GiB from the fit

One machine's data per invocation: pooled fits mix machines. Manual
--point entries (e.g. notebook archive numbers) join the same pool -
pass only what belongs to the machine being fit.
"""

import argparse
import json
import os
import sys

BPW_APPROX = {          # llama.cpp average bits-per-weight; varies per model
    "Q4_K_M": 4.83,
    "Q5_K_M": 5.69,
    "Q6_K": 6.56,
    "Q8_0": 8.5,
}
GIB_BYTES = 1 << 30
GIB_TO_GB = 1.073741824


def harvest_state(state_files):
    """Every measured (size, worst, mean) pair from pipeline state."""
    pts = []
    for sf in state_files:
        if not os.path.isfile(sf):
            print(f"  warning: state file not found, skipped: {sf}",
                  file=sys.stderr)
            continue
        with open(sf) as f:
            st = json.load(f)
        tag = os.path.basename(sf)
        for fam, fst in st.get("families", {}).items():
            for rung, run in fst.get("runs", {}).items():
                if "worst" not in run or "file" not in run:
                    continue
                path = run["file"]
                if not os.path.isfile(path):
                    print(f"  warning: model file missing, skipped: "
                          f"{fam} {rung} ({path})", file=sys.stderr)
                    continue
                pts.append({
                    "label": f"{fam} {rung}",
                    "model": fam,
                    "size": os.path.getsize(path) / GIB_BYTES,
                    "worst": float(run["worst"]),
                    "mean": (float(run["mean"]) if run.get("mean") is not None
                             else None),
                    "verdict": run.get("verdict", "?"),
                    "source": tag,
                })
    return pts


def parse_points(specs):
    """Manual archive points: 'label,size_gib,worst[,mean]'."""
    pts = []
    for s in specs:
        parts = [p.strip() for p in s.split(",")]
        if len(parts) < 3:
            sys.exit(f"bad --point (need label,size_gib,worst): {s}")
        pts.append({
            "label": parts[0],
            "model": parts[0],
            "size": float(parts[1]),
            "worst": float(parts[2]),
            "mean": float(parts[3]) if len(parts) > 3 else None,
            "verdict": "archive",
            "source": "--point",
        })
    return pts


def ols(points, tkey="worst"):
    """Fit 1/t = a*size + b. Returns (a, b, r2, n)."""
    xs = [p["size"] for p in points]
    ys = [1.0 / p[tkey] for p in points]
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    a = sxy / sxx
    b = my - a * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (a * x + b)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return a, b, r2, n


def law_worst(size_gib, a, b):
    if b <= 0:
        return a * 0 + 1 / (a * size_gib) if a > 0 else float("inf")
    return 1.0 / (a * size_gib + b)


def print_fit(name, a, b, r2, n):
    bw = 1.0 / a if a > 0 else float("inf")
    tinf = 1.0 / b if b > 0 else float("inf")
    print(f"  {name}: n={n}  BW_eff={bw:.1f} GiB/s "
          f"({bw * GIB_TO_GB:.1f} GB/s)  "
          f"t_inf={'inf' if tinf == float('inf') else f'{tinf:.0f}'} t/s  "
          f"R2={r2:.4f}")
    return bw, tinf


def main():
    ap = argparse.ArgumentParser(
        description="harvest the ladder data, fit the bandwidth->size law, "
                    "print the right-sizing boundary size*(floor)")
    ap.add_argument("--state-file", action="append", default=[],
                    help="pipeline state file (repeatable); "
                         "default ./benchmark-state.json")
    ap.add_argument("--point", action="append", default=[],
                    metavar="'label,size_gib,worst[,mean]'",
                    help="manual archive point (repeatable)")
    ap.add_argument("--floor", type=float, default=20.0,
                    help="comfort floor in t/s (default 20; or pass "
                         "--latency-budget for the time-based form)")
    ap.add_argument("--latency-budget", type=float, default=None,
                    metavar="MS",
                    help="comfort budget in ms per generated token; "
                         "replaces --floor (floor = 1000/budget); the "
                         "floor-free form of the boundary")
    ap.add_argument("--bw-theoretical", type=float, default=None,
                    help="theoretical bandwidth in GB/s, to report the "
                         "efficiency fraction")
    ap.add_argument("--predict-size", type=float, default=None,
                    help="also print the law's worst t/s at this size (GiB)")
    ap.add_argument("--json", default=None,
                    help="write the fit to this JSON file")
    args = ap.parse_args()

    state_files = args.state_file or ["./benchmark-state.json"]
    pts = harvest_state(state_files) + parse_points(args.point)
    if len(pts) < 2:
        sys.exit("need at least 2 measured points to fit "
                 "(pass state files and/or --point entries)")

    print("=" * 72)
    print("HARVESTED POINTS (size = actual file on disk)")
    print("=" * 72)
    print(f"  {'label':40} {'size GiB':>8} {'worst':>6} {'mean':>6}"
          f" {'verdict':<20} source")
    for p in sorted(pts, key=lambda q: (q["model"], q["size"])):
        mean = f"{p['mean']:.1f}" if p["mean"] is not None else "-"
        print(f"  {p['label']:40} {p['size']:8.2f} {p['worst']:6.1f} "
              f"{mean:>6} {p['verdict']:<20} {p['source']}")

    pooled = ols(pts)
    if pooled is None or pooled[0] <= 0:
        sys.exit("cannot fit: points do not span sizes "
                 "(need >= 2 distinct file sizes)")

    print()
    print("=" * 72)
    print("FIT  (1/worst = size/BW_eff + 1/t_inf)")
    print("=" * 72)
    a, b, r2, n = pooled
    bw, tinf = print_fit("pooled (all points)", a, b, r2, n)
    if args.bw_theoretical:
        eff = bw * GIB_TO_GB / args.bw_theoretical
        print(f"  efficiency vs theoretical {args.bw_theoretical} GB/s: "
              f"{100 * eff:.0f}%")

    print()
    print("  per-point residuals (family efficiency = measured/predicted;")
    print("  the Session-18q family factors, now against a principled law)")
    print(f"  {'label':40} {'size':>5} {'meas':>5} {'pred':>5} {'ratio':>6}")
    for p in sorted(pts, key=lambda q: (q["model"], q["size"])):
        pred = law_worst(p["size"], a, b)
        print(f"  {p['label']:40} {p['size']:5.2f} {p['worst']:5.1f} "
              f"{pred:5.1f} {p['worst'] / pred:6.2f}")

    models = {}
    for p in pts:
        models.setdefault(p["model"], []).append(p)
    multi = {m: q for m, q in models.items() if len(q) >= 2}
    if len(multi) >= 1 and len(pts) > 2:
        print()
        print("  per-model fits (>= 2 rungs of the same ladder)")
        for m in sorted(multi):
            f = ols(multi[m])
            if f is None or f[0] <= 0:
                print(f"  {m}: degenerate (no size spread), skipped")
                continue
            print_fit(m, f[0], f[1], f[2], f[3])

    if args.latency_budget is not None:
        floor = 1000.0 / args.latency_budget
    else:
        floor = args.floor

    print()
    print("=" * 72)
    print(f"RIGHT-SIZING  (comfort boundary: floor {floor:g} t/s worst "
          f"turn = {1000 / floor:.0f} ms per generated token)")
    print("=" * 72)
    print("  the boundary in time language (no floor needed): a token "
          "costs")
    overhead_ms = 1000.0 / tinf if tinf != float("inf") else 0.0
    print(f"    T_token = size/GW_eff + T_overhead = size x "
          f"{1000.0 / bw:.2f} ms/GiB + {overhead_ms:.1f} ms")
    print("    (GW_eff = effective GiB read per second; the whole model "
          "is")
    print("     read once per token - that is the cost of autoregressive "
          "decode)")
    if b <= 0:
        size_star = bw / floor
        print(f"  overhead term vanished with this data; "
              f"pure-BW approximation:")
    else:
        size_star = bw * (1000.0 / floor - overhead_ms) / 1000.0
        print(f"    comfort budget {1000 / floor:.0f} ms/token = read "
              f"budget {1000 / floor - overhead_ms:.1f} ms -> "
              f"size* = GW_eff x read budget")
    print(f"  size* = {size_star:.2f} GiB  (band {size_star * 0.9:.2f}"
          f"-{size_star * 1.1:.2f}, family factors +-10%)")
    print("  biggest model class that fits size* at plateau rungs "
          "(approx bpw):")
    for rung, bpw in BPW_APPROX.items():
        print(f"    {rung:6} ({bpw:4.2f} bpw): "
              f"~{size_star * 8.59 / bpw:4.1f}B params")
    print("  rule: maximize parameters inside size*, never below Q4_K_M "
          "(the quality cliff); the rung is a free variable on the plateau")
    if args.predict_size is not None:
        t = law_worst(args.predict_size, a, b)
        print(f"  law prediction at {args.predict_size:.2f} GiB: "
              f"worst {t:.1f} t/s = {1000.0 / t:.0f} ms/token "
              f"({'meets' if t >= floor else 'exceeds'} the "
              f"{1000.0 / floor:.0f} ms comfort budget)")

    if args.json:
        out = {
            "points": pts,
            "fit": {"bw_eff_gib_s": 1.0 / a, "t_inf": (None if b <= 0
                    else 1.0 / b), "r2": r2, "n": n},
            "size_star": {"floor": floor,
                          "latency_budget_ms": 1000.0 / floor,
                          "gib": size_star,
                          "band": [size_star * 0.9, size_star * 1.1]},
        }
        with open(args.json, "w") as f:
            json.dump(out, f, indent=1)
        print(f"\nfit written to {args.json}")


if __name__ == "__main__":
    main()
