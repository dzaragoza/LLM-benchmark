#!/usr/bin/env python3
"""testmon_hook.py - the changed-files test selector for the commit
hook (session 44, R-25's use-the-remaining-4-seconds ruling).

pytest-testmon maps every test to the source lines it covers
(.testmondata). At commit time we run ONLY the tests whose covered
code changed - a state_store.py edit runs its 41 tests in ~3s, a
v7.py edit runs its own set, everything else is deselected. The full
suite (all 258 incl. hypothesis) runs on every push in GitHub
Actions (push-regression.yml) - the hook is the fast affected-only
gate, CI is the complete gate.

Contract (addendum 148 adds the changed-test-files arm):
- changed NEW/EDITED test files run EXPLICITLY, always: the map only
  knows tests that already ran, so testmon alone never selects a new
  test file (the manual run-it-by-hand gap this closes). Detected via
  git status (staged + unstaged + untracked, tests/*.py), run as file
  args directly.
- no .testmondata            -> exit 0 with a note (first run after
                                clone; CI owns the first full gate) -
                                but changed test files still run above
- testmon selects 0 tests     -> exit 0 (nothing affected; the
                                trailing-newline case)
- affected tests fail        -> non-zero, the commit is blocked
- the map updates on success, so it stays current
- hypothesis stays OUT of the hook: -m "not hypothesis_props"
  (the addendum-117 compromise, restored after the addendum-119
  rewrite dropped it - caught by the R-31 pin); the properties run
  in the push workflow
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = Path.cwd() / ".testmondata"


def _changed_test_files() -> list[str]:
    """tests/*.py that are staged, modified, or untracked - the files
    testmon cannot know about (a new test is not in the map until it
    has run once; the addendum-148 gap)."""
    proc = subprocess.run(
        ["git", "status", "--porcelain", "-uall", "--", "tests"],
        capture_output=True,
        text=True,
    )
    files = []
    for line in proc.stdout.splitlines():
        path = line[3:].strip().strip('"')
        if path.endswith(".py") and Path(path).exists():
            files.append(path)
    return sorted(set(files))


def main() -> int:
    rc = 0
    changed = _changed_test_files()
    if changed:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                *changed,
                "-q",
                "--no-header",
                "-m",
                "not hypothesis_props",
            ],
        )
        print(f"testmon: ran {len(changed)} changed test file(s) explicitly (R-25)")
        rc = proc.returncode
    if not DB.exists():
        if changed:
            return rc
        print("testmon: no .testmondata map - first full run is CI's job (R-25)")
        return 0
    if rc != 0:
        return rc
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "tests"),
            "-q",
            "--testmon",
            "--no-header",
            "-m",
            "not hypothesis_props",
        ],
        cwd=ROOT,
    )
    return proc.returncode if rc == 0 else rc


if __name__ == "__main__":
    sys.exit(main())
