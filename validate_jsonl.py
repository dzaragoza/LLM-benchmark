#!/usr/bin/env python3
"""validate_jsonl.py - the CI gate form of the R-34 evidence check
(addendum 176): every committed answers JSONL parses and carries
the required keys. Exit 1 names the first offenders.
"""
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE / "tests"))
sys.path.insert(0, str(_HERE))

import test_answers_jsonl  # noqa: E402

validate = test_answers_jsonl.validate

ROOT = Path(__file__).resolve().parent
files = list((ROOT / "models" / "tournament-results").rglob("*-answers.jsonl"))
offenders = []
for p in files:
    offenders.extend(validate(p))
if offenders:
    for o in offenders[:20]:
        print(f"CORRUPT: {o}")
    sys.exit(1)
print(f"validate_jsonl: {len(files)} answers files, all lines valid")
