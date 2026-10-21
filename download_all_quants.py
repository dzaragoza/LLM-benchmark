#!/usr/bin/env python3
"""download_all_quants.py - phase 1 + 2 for EVERY rung of one family.

Uses the repo's own layers only: infra/hf_download.py (the HF interface)
and infra/convert_quant.py (convert + quantize). The rung set is the
registry's weight ladder, smallest first; each rung
is idempotent - an existing local file is reused, never re-downloaded.

Usage:
  python3 download_all_quants.py Qwen3.5-2B
  python3 download_all_quants.py Qwen3.5-2B --rungs Q4_0,Q8_0,F16
  python3 download_all_quants.py Qwen3.5-2B --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, cast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import infra.convert_quant as convert_quant
import infra.hf_download as hf_download
from etc.registry_data import ROSTER

# every llama-quantize weight type (b11669 --help output), smallest first;
# the K aliases (Q3_K, Q4_K, Q5_K) are expanded to their _M targets so each
# rung names exactly one output file. F32/COPY/MXFP4_MOE are excluded: F32
# and COPY do not quantize, MXFP4_MOE applies to MoE models only.
ALL_RUNGS = [
    "IQ1_S",
    "IQ1_M",
    "TQ1_0",
    "Q1_0",
    "IQ2_XXS",
    "TQ2_0",
    "IQ2_XS",
    "Q2_0",
    "IQ2_S",
    "Q2_K_S",
    "IQ2_M",
    "Q2_K",
    "IQ3_XXS",
    "IQ3_XS",
    "IQ3_S",
    "IQ3_M",
    "Q3_K_S",
    "Q3_K_M",
    "Q3_K_L",
    "IQ4_NL",
    "IQ4_XS",
    "Q4_0",
    "Q4_1",
    "Q4_K_S",
    "Q4_K_M",
    "Q5_0",
    "Q5_1",
    "Q5_K_S",
    "Q5_K_M",
    "Q6_K",
    "Q8_0",
    "BF16",
    "F16",
]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="download the tensors and build every rung of one family"
    )
    ap.add_argument(
        "family", help="family name as registered in etc/registry_data.py, e.g. Qwen3.5-2B"
    )
    ap.add_argument("--models-dir", default="./models")
    ap.add_argument(
        "--rungs", default=None, help="comma-separated subset of the ladder, e.g. Q4_0,Q8_0,F16"
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="report the plan only, download/build nothing"
    )
    args = ap.parse_args()

    fam = args.family
    if fam not in ROSTER:
        sys.exit(f"unknown family {fam!r}; registered: {', '.join(sorted(ROSTER))}")
    repo = ROSTER[fam]
    rungs = [
        r.strip().upper() for r in (args.rungs.split(",") if args.rungs else ALL_RUNGS) if r.strip()
    ]
    rungs = [{"Q3_K": "Q3_K_M", "Q4_K": "Q4_K_M", "Q5_K": "Q5_K_M"}.get(r, r) for r in rungs]
    bad = [r for r in rungs if r not in ALL_RUNGS]
    if bad:
        sys.exit(f"rungs {bad} are not supported; available: {','.join(ALL_RUNGS)}")

    famdir = os.path.join(args.models_dir, fam)
    os.makedirs(famdir, exist_ok=True)

    hf_download.require_hub()
    list_repo_files = cast("Any", hf_download.list_repo_files)
    print(f"listing {repo} ...")
    files = list_repo_files(repo)

    rc = 0
    for rung in rungs:
        print(f"== {fam} {rung} ==")
        try:
            path, plan = hf_download.acquire(
                fam, famdir, rung, repo, files, repo, files, args.dry_run
            )
            if not path:
                path = convert_quant.create(fam, famdir, rung, plan, args.dry_run)
        except SystemExit as e:
            if e.code == 130:
                raise
            rc = 1
            continue
        if path:
            print(f"  ready: {path}")
        elif args.dry_run:
            print(f"  would build: {plan}")
        else:
            print("  UNAVAILABLE (see output above)")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
