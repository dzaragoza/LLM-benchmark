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

Contract:
- no .testmondata            -> exit 0 with a note (first run after
                                clone; CI owns the first full gate)
- testmon selects 0 tests    -> exit 0 (nothing affected; the
                                trailing-newline case)
- affected tests fail        -> non-zero, the commit is blocked
- the map updates on success, so it stays current
- hypothesis stays OUT of the hook: -m "not hypothesis_props"
  (the addendum-117 compromise, restored after the addendum-119
  rewrite dropped it - caught by the R-31 pin); the properties run
  in the push workflow and the daily quality run
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = Path.cwd() / ".testmondata"


def main() -> int:
    if not DB.exists():
        print("testmon: no .testmondata map - first full run is CI's job (R-25)")
        return 0
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
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
