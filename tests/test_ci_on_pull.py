"""Pins: R-27 (session 44, addendum 127). Check CI on pull.

The author: "Add the requirement to check the latest completed CI
results from github when you pull." Every pull checks the latest
COMPLETED push-regression verdict; a red run blocks the next
delivery. In-flight runs are never waited for - the previous
completed verdict is the governing signal.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTOCOL = ROOT / "md" / "protocol.md"


def test_r27_in_protocol():
    text = PROTOCOL.read_text(encoding="utf-8")
    assert "| R-27 |" in text
    assert "COMPLETED push-regression verdict" in text
    assert "In-flight runs are NOT waited for" in text


def test_r27_row_pinned_by_this_file():
    """requirements_check.py needs the pin named - the docstring
    carries the R-27 tag."""
    assert "Pins: R-27" in Path(__file__).read_text(encoding="utf-8")
