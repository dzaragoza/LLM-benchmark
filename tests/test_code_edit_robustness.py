"""Pins: R-26 (session 45, addendum 149) - code_edit robustness fixes
born from real session-45 struggles:

1. The docstring-apostrophe false block: the region balance check
   scanned edited regions as CODE even when the region sits inside a
   triple-quoted string, so prose apostrophes ("CI's job") read as
   unclosed quotes. A region inside a docstring now only needs its
   triple-quote pairing intact.

2. The quote-style rescue: the format hook (addendum 146) legally
   rewrites quote styles, so an old_str written against the
   pre-format style stops matching. The finder now tries the
   quote-swapped target (uniqueness required) - the file's own text
   is returned so the apply stays exact.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CE = ROOT / "AI_tools" / "code_edit.py"


def _edit(setup: str, blocks: list, tmp: Path) -> tuple[int, str]:
    target = tmp / "sample.py"
    target.write_text(setup, encoding="utf-8")
    spec = tmp / "spec.json"
    spec.write_text(__import__("json").dumps({"blocks": blocks}), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(CE), str(target), "--blocks-file", str(spec)],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def test_docstring_apostrophe_no_false_block(tmp_path):
    """An apostrophe in edited docstring prose is legal - the region
    sits inside a triple-quoted string and is not code."""
    rc, out = _edit(
        '''def f():
    """The note: CI's job.

    Done."""
    return 1
''',
        [["replace", "CI's job", "the CI's own job"]],
        tmp_path,
    )
    assert rc == 0, out


def test_docstring_multiline_apostrophes(tmp_path):
    """The session-45 shape: a multi-line docstring edit whose text
    carries apostrophes on several lines."""
    rc, out = _edit(
        '''def h():
    """Pins: R-37.

    The map is CI's job.
    """
    return 3
''',
        [["replace", "The map is CI's job.", "It's the CI's job now."]],
        tmp_path,
    )
    assert rc == 0, out


def test_broken_triple_quote_still_blocks(tmp_path):
    """The guard stays: breaking a docstring's triple-quote pairing
    in an edited region is still a blocked edit."""
    rc, _ = _edit(
        '''def f():
    """docs"""
    return 1
''',
        [["replace", '"""docs"""', '"""docs']],
        tmp_path,
    )
    assert rc != 0


def test_truncated_code_still_blocks(tmp_path):
    """The guard stays: a truncated call in code still blocks."""
    rc, _ = _edit(
        "def f():\n    g(1, 2)\n    return 1\n",
        [["replace", "g(1, 2)", "g(1,"]],
        tmp_path,
    )
    assert rc != 0


def test_quote_swap_rescue_doubles(tmp_path):
    """The file was formatted to double quotes; the spec carries the
    pre-format single-quote style - the rescue finds it uniquely."""
    rc, out = _edit(
        'x = "hello"\ny = 1\n',
        [["replace", "x = 'hello'", "x = 42"]],
        tmp_path,
    )
    assert rc == 0, out
    assert "x = 42" in (tmp_path / "sample.py").read_text(encoding="utf-8")


def test_quote_swap_rescue_singles(tmp_path):
    """The reverse direction: the file carries singles, the spec was
    written with doubles."""
    rc, out = _edit(
        "x = 'hello'\ny = 1\n",
        [["replace", 'x = "hello"', "x = 43"]],
        tmp_path,
    )
    assert rc == 0, out
    assert "x = 43" in (tmp_path / "sample.py").read_text(encoding="utf-8")


def test_exact_match_wins_over_swap(tmp_path):
    """The swap is a rescue only: an exact match applies normally."""
    rc, out = _edit(
        'a = "x"\nb = "x"\n',
        [["replace", 'a = "x"', "a = 1"]],
        tmp_path,
    )
    assert rc == 0, out
    assert "a = 1" in (tmp_path / "sample.py").read_text(encoding="utf-8")


def test_ambiguous_after_swap_blocks(tmp_path):
    """If the swapped target is ambiguous, the edit blocks - the
    rescue requires uniqueness like every other flexible pass."""
    rc, _ = _edit(
        'a = "x"\nb = "x"\nc = "x"\n',
        [["replace", "a = 'x', b = 'x'", "a = 2"]],
        tmp_path,
    )
    # the swapped two-var target does not exist at all -> not found
    assert rc != 0
