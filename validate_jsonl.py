#!/usr/bin/env python3
"""validate_jsonl.py - the CI gate form of the R-34 evidence check
(addendum 176): every committed answers JSONL parses and carries
the required keys. Exit 1 names the first offenders. The validate
logic is inlined (not imported from the test file) - ty resolves
statically, and the test imports THIS module so the logic is
single-sourced (the test's pin covers this file too).
"""
import json
import sys
from pathlib import Path

REQUIRED = ("window", "grade", "expected", "value", "found", "ok", "answer")


def validate(path: Path) -> list:
    bad = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                bad.append(f"{path.name}:{i} unparseable: {e}")
                continue
            missing = [k for k in REQUIRED if k not in rec]
            if missing:
                bad.append(f"{path.name}:{i} missing keys: {missing}")
    return bad


def main() -> int:
    root = Path(__file__).resolve().parent
    files = list((root / "models" / "tournament-results").rglob("*-answers.jsonl"))
    offenders = []
    for p in files:
        offenders.extend(validate(p))
    if offenders:
        for o in offenders[:20]:
            print(f"CORRUPT: {o}")
        return 1
    print(f"validate_jsonl: {len(files)} answers files, all lines valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
