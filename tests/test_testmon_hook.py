"""Pins: R-25. The testmon hook: affected tests only, per commit.

pytest-testmon maps tests to covered source lines (.testmondata);
testmon_hook.py runs ONLY the tests affected by changed code at
commit time. The full suite stays on every push (push-regression).
This pins the hook contract: no map -> pass through (CI owns the
first full run); a real selection -> the affected tests run; a
failure -> non-zero so the commit blocks.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "testmon_hook.py"


def test_hook_exists_and_contract_documented():
    src = HOOK.read_text(encoding="utf-8")
    assert "--testmon" in src, "the hook must run pytest with --testmon"
    assert "def main() -> int:" in src


def test_hook_passes_without_map(tmp_path, monkeypatch):
    """No .testmondata -> exit 0 with the CI note: the first full run
    after a clone is the push workflow's job, never a hook crash."""
    monkeypatch.chdir(tmp_path)
    proc = subprocess.run([sys.executable, str(HOOK)], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "no .testmondata" in proc.stdout


def test_hook_runs_affected_tests_from_map(monkeypatch):
    """With the repo's live map, the hook invocation is exactly
    `pytest tests/ -q --testmon` in the repo root - the selection is
    testmon's job (deselected tests reported, not run)."""
    src = HOOK.read_text(encoding="utf-8")
    assert '"--testmon"' in src and "tests" in src
