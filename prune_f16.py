#!/usr/bin/env python3
"""prune_f16 -- remove redundant f16 GGUFs (addendum 267).

A family's f16 is the quantization SOURCE; once both Q8_0 and Q4_0
exist on disk, the ladder never reads the f16 again (the quick ladder
rungs are Q8_0 and Q4_0 only). This script walks every models/ folder,
verifies the f16's two quant siblings exist AT DELETION TIME, and
removes the f16. Safety: --dry-run is the default posture; a missing
sibling skips the file, never fails the run.

Usage (fish):
  python3 prune_f16.py --dry-run   # list what would go (default)
  python3 prune_f16.py --remove    # actually delete
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(ROOT, "models")


def scan() -> tuple[list[str], list[str]]:
    """Returns (removable, skipped): the f16s whose q4+q8 siblings
    exist, and the f16s that must stay (a sibling is missing)."""
    removable, skipped = [], []
    if not os.path.isdir(MODELS):
        print(f"no models dir at {MODELS}")
        return removable, skipped
    for fam in sorted(os.listdir(MODELS)):
        famdir = os.path.join(MODELS, fam)
        if not os.path.isdir(famdir):
            continue
        ggufs = [f for f in os.listdir(famdir) if f.endswith(".gguf")]
        f16s = [f for f in ggufs if f.endswith("-f16.gguf")]
        for f16 in f16s:
            stem = f16[: -len("-f16.gguf")]
            q8 = os.path.join(famdir, f"{stem}-Q8_0.gguf")
            q4 = os.path.join(famdir, f"{stem}-Q4_0.gguf")
            path = os.path.join(famdir, f16)
            if os.path.isfile(q8) and os.path.isfile(q4):
                removable.append(path)
            else:
                missing = [s for s, p in (("Q8_0", q8), ("Q4_0", q4)) if not os.path.isfile(p)]
                skipped.append((path, missing))
    return removable, skipped


def main() -> None:
    ap = argparse.ArgumentParser(
        description="remove f16 GGUFs whose Q8_0 and Q4_0 siblings both exist"
    )
    ap.add_argument("--remove", action="store_true", help="actually delete (default: dry-run list)")
    args = ap.parse_args()
    removable, skipped = scan()
    if not removable and not skipped:
        print("no f16 GGUFs found under models/")
        return
    total = 0
    for path in removable:
        size = os.path.getsize(path)
        total += size
        print(f"{'REMOVE' if args.remove else 'would remove'}: {path} ({size / (1 << 30):.2f} GiB)")
    for path, missing in skipped:
        print(f"KEEP (missing {' and '.join(missing)}): {path}")
    unit = "GiB" if total >= (1 << 30) else "MiB"
    val = total / (1 << 30) if total >= (1 << 30) else total / (1 << 20)
    print(
        f"\n{len(removable)} f16 files, {val:.1f} {unit} {'freed' if args.remove else 'freed if --remove'}"
    )
    if args.remove:
        for path in removable:
            os.remove(path)
        print("done")


if __name__ == "__main__":
    main()
