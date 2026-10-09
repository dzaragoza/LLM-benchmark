"""Pins: R-34 (addendum 176) - every committed answers JSONL is valid
evidence: every line parses as JSON and carries the required keys
(window, grade, expected, value, found, ok, answer). A truncated or
corrupt line - the mid-write crash class - is caught HERE, at push
time, instead of in a grading session. Run in CI as a named gate.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

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


def test_all_answers_jsonl_valid():
    offenders = []
    files = list((ROOT / "models" / "tournament-results").rglob("*-answers.jsonl"))
    assert files, "no answers files found - the glob is wrong"
    for p in files:
        offenders.extend(validate(p))
    assert offenders == [], f"corrupt answers evidence: {offenders[:5]}"
