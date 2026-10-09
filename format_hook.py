#!/usr/bin/env python3
"""format_hook.py - the ruff-format wrapper that never aborts the
commit (session 45, addendum 146, the author's ruling: "Ruff format
should not abort the commit, since it is only formatting changes").

The stock ruff-format hook exits non-zero when it MODIFIES a file,
aborting the commit so the human re-stages. For this repo that is
pure friction: the change is exactly what the hook is for. This
wrapper applies the format, RE-STAGES the files it touched, and
exits 0 - the commit proceeds WITH the formatting applied (verified:
the committed tree is the formatted tree).

Contract:
- ruff format fails (a syntax error, not a style delta) -> non-zero,
  the commit blocks: a broken file must not slip in under a
  formatting flag.
- files touched by the format -> git add, exit 0, commit proceeds.
- nothing to do -> exit 0 silently.
"""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    files = sys.argv[1:]
    if not files:
        return 0
    proc = subprocess.run(
        [sys.executable, "-m", "ruff", "format", *files],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        print("format: ruff format FAILED - not a style delta, a broken file")
        return proc.returncode
    changed = [
        f
        for f in files
        if subprocess.run(
            ["git", "diff", "--name-only", "--", f],
            capture_output=True,
            text=True,
        ).stdout.strip()
    ]
    if changed:
        subprocess.run(["git", "add", *changed], check=True)
        print(f"format: applied + restaged {len(changed)} file(s); commit proceeds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
