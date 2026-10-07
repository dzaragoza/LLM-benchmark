"""requirements_check (pre-commit + manual): the R-xx traceability
gate (protocol v5.0, addendum 59). docs/protocol.md carries the
study's requirements table; tests pin them with a `Pins: R-xx`
docstring marker. This script fails the commit if:

1. a requirement in the table has NO pinning test (the table is
   a contract, not documentation - an unpinned requirement can
   regress invisibly, which is exactly how the addendum-52/54
   gate drift and the addendum-56 ladder break happened);
2. a test pins a requirement that does not exist (a stale or
   mistyped marker - the classic requirements-engineering
   failure mode, a table that rots while the pins point away).

Pass = every R-xx has >= 1 pin and every pin resolves.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQ_RE = re.compile(r"^\| (R-\d+) \|", re.MULTILINE)
PIN_RE = re.compile(r"Pins:\s*(R-\d+(?:\s*,\s*R-\d+)*)")


def main() -> int:
    root = Path(__file__).resolve().parent
    protocol = root / "md" / "protocol.md"
    table = protocol.read_text(encoding="utf-8")
    reqs = sorted(set(REQ_RE.findall(table)))
    if not reqs:
        print("requirements_check: no requirements found in docs/protocol.md")
        return 1
    pins: dict[str, list[str]] = {r: [] for r in reqs}
    bad: list[str] = []
    for py in sorted((root / "tests").glob("*.py")):
        text = py.read_text(encoding="utf-8")
        for m in PIN_RE.finditer(text):
            for r in re.findall(r"R-\d+", m.group(1)):
                if r in pins:
                    pins[r].append(py.name)
                else:
                    bad.append(f"{py.name}: pins {r}, not in docs/protocol.md")
    missing = [r for r in reqs if not pins[r]]
    for r in missing:
        print(f"requirements_check: {r} has no pinning test (add `Pins: {r}` to a test docstring)")
    for b in bad:
        print(f"requirements_check: {b}")
    if missing or bad:
        return 1
    print(f"requirements_check: {len(reqs)} requirements, all pinned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
