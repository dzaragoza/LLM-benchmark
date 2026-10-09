"""Pins: R-34 (addendum 176) - every committed answers JSONL is valid
evidence: every line parses as JSON and carries the required keys
(window, grade, expected, value, found, ok, answer). A truncated or
corrupt line - the mid-write crash class - is caught HERE, at push
time, instead of in a grading session. Run in CI as a named gate.
The validate logic lives in validate_jsonl.py (single-sourced); this
test imports it and walks every committed file.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import validate_jsonl  # noqa: E402


def test_all_answers_jsonl_valid():
    offenders = []
    files = list((ROOT / "models" / "tournament-results").rglob("*-answers.jsonl"))
    assert files, "no answers files found - the glob is wrong"
    for p in files:
        offenders.extend(validate_jsonl.validate(p))
    assert offenders == [], f"corrupt answers evidence: {offenders[:5]}"
