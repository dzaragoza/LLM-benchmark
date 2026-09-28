"""GFM table-structure check for the markdown files (pre-commit hook).

Checks exactly the failure class the registry hit (addendum 106): a GFM
table renders on GitHub only if the header row is preceded by a blank
line (or file start) and every row in the block has the same pipe count.
Run with filenames as arguments; exit 1 with a report if any table is
malformed. repo-root scoped: paths are used as given.
"""

from __future__ import annotations

import re
import sys

SEPARATOR = re.compile(r"^\|[-\s|]+\|$")


def check(path: str) -> list[str]:
    problems: list[str] = []
    try:
        lines = open(path, encoding="utf-8").read().split("\n")
    except (OSError, UnicodeDecodeError) as e:
        return [f"{path}: unreadable: {e}"]
    i = 0
    while i < len(lines):
        if SEPARATOR.match(lines[i]) and i > 0 and i + 1 < len(lines):
            header = lines[i - 1]
            prev = lines[i - 2] if i >= 2 else ""
            if not header.startswith("|"):
                problems.append(f"{path}:{i}: separator row not under a header row")
            elif prev.strip() != "" and not SEPARATOR.match(prev):
                problems.append(
                    f"{path}:{i}: no blank line before the table header (GitHub will not render it)"
                )
            block = [header, lines[i]]
            j = i + 1
            while j < len(lines) and lines[j].startswith("|"):
                block.append(lines[j])
                j += 1
            cols = [row.count("|") - 1 for row in block]
            if len(set(cols)) != 1:
                bad = {c for c in cols if c != cols[0]}
                problems.append(
                    f"{path}:{i}: ragged table - rows with {sorted(bad)} "
                    f"pipes instead of {cols[0] + 1}"
                )
            i = j
        else:
            i += 1
    return problems


def main(argv: list[str]) -> int:
    problems: list[str] = []
    for path in argv:
        problems.extend(check(path))
    if problems:
        print("markdown table check FAILED:")
        for p in problems:
            print(f"  {p}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
