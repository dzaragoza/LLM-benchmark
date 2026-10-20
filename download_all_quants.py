#!/usr/bin/env python3
"""download_all_quants.py - phase 1 + 2 for EVERY rung of one family.

Uses the repo's own layers only: infra/hf_download.py (the HF interface)
and infra/convert_quant.py (convert + quantize). The rung set is the
registry's weight ladder (bench.v7.W_LADDER), smallest first; each rung
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
from bench.v7 import W_LADDER
from etc.registry_data import ROSTER


def main() -> int:
    ap = argparse.ArgumentParser(description="download the tensors and build every rung of one family")
    ap.add_argument("family", help="family name as registered in etc/registry_data.py, e.g. Qwen3.5-2B")
    ap.add_argument("--models-dir", default="./models")
    ap.add_argument("--rungs", default=None, help="comma-separated subset of the ladder, e.g. Q4_0,Q8_0,F16")
    ap.add_argument("--dry-run", action="store_true", help="report the plan only, download/build nothing")
    args = ap.parse_args()

    fam = args.family
    if fam not in ROSTER:
        sys.exit(f"unknown family {fam!r}; registered: {', '.join(sorted(ROSTER))}")
    repo = ROSTER[fam]
    rungs = [r.strip().upper() for r in (args.rungs.split(",") if args.rungs else W_LADDER) if r.strip()]
    bad = [r for r in rungs if r not in W_LADDER]
    if bad:
        sys.exit(f"rungs {bad} are not on the ladder {W_LADDER}")

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
            path, plan = hf_download.acquire(fam, famdir, rung, repo, files, repo, files, args.dry_run)
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
            print(f"  UNAVAILABLE (see output above)")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
