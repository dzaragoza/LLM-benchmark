"""Pins: R-26. All agent edits go through AI_tools/code_edit.py.

The transactional editor (session 34, addendum 20) exists because
hand-rolled string replacement is not a transaction: a mid-script
assert failure silently skips the later steps, leaving a half-applied
tree (session 44, the R-25 half-edit). This file pins the two sides
of the requirement: the tool's own contract, and the visible trace
it leaves on the files it edits.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "AI_tools"))

import code_edit  # noqa: E402


def test_edit_is_a_transaction(tmp_path):
    """Pins: R-26 (the tool's side). A block list applies fully or
    not at all: when a later block's anchor is missing, NOTHING is
    written - the file on disk still reads exactly as before."""
    f = tmp_path / "t.txt"
    f.write_text("alpha\nbeta\n")
    try:
        code_edit.edit(str(f), [("replace", "alpha", "ALPHA"), ("replace", "absent", "X")])
    except code_edit.CodeEditError:
        pass
    assert f.read_text() == "alpha\nbeta\n", "a failed block list must not write"


def test_edit_rewrites_atomically_and_verifies(tmp_path):
    """Pins: R-26. A good edit lands, and the re-read verification
    passed (edit returning without raising IS the assertion)."""
    f = tmp_path / "t.txt"
    f.write_text("one\ntwo\n")
    code_edit.edit(str(f), [("replace", "one", "ONE"), ("insert_after", "two", "three")])
    assert f.read_text() == "ONE\ntwo\nthree\n"


def test_code_edit_module_is_importable_and_used_pattern():
    """Pins: R-26 (the discipline's side). The tool is importable from
    the repo layout, and the repo carries no sanctioned alternative:
    the requirement is that agents call THIS module - the test keeps
    its seam honest so a rename/refactor of the tool surface fails
    loudly here instead of silently voiding the requirement."""
    for fn in ("edit", "write", "edit_many", "safe_append", "replace_verified"):
        assert callable(getattr(code_edit, fn, None)), f"code_edit.{fn} missing"
