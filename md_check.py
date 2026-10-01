"""GitHub-rendering compliance check for the markdown files (pre-commit).

The addendum-106 failure class: markdown that GitHub will not render as
intended. Checks the markdownlint rule IDs that matter for our use case
(tables have been the only real issue so far) plus two structural rules:

  MD055  table-pipe-style    - every table row begins and ends with a pipe
  MD056  table-column-count - every row in a table has the same cell count
  MD058  blanks-around-tables - a blank line before the header (and after)
  MD047  single-trailing-newline
  fence-balance (markdownlint MD048 family) - an unclosed code fence turns
          everything after it into rendered code; the worst non-table
          failure mode on GitHub

Run with filenames as arguments; exit 1 with an MD-numbered report.
"""

from __future__ import annotations

import re
import sys

SEPARATOR = re.compile(r"^\|[-\s|]+\|$")


def check(path: str) -> list[str]:
    try:
        text = open(path, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError) as e:
        return [f"{path}: unreadable: {e}"]
    return check_text(path, text)


def check_text(path: str, text: str) -> list[str]:
    """The same rules, run on in-memory text (code_edit's pre-write gate)."""
    lines = text.split("\n")
    problems: list[str] = []
    problems.extend(check_md047(path, text))
    problems.extend(check_fences(path, lines))
    problems.extend(check_tables(path, lines))
    return problems


def check_md047(path: str, text: str) -> list[str]:
    if text != "" and not text.endswith("\n"):
        return [f"{path}:1: MD047 files should end with a single newline"]
    if text.endswith("\n\n"):
        return [f"{path}:1: MD047 files should end with a SINGLE newline"]
    return []


def check_fences(path: str, lines: list[str]) -> list[str]:
    fence = re.compile(r"^(`{3,}|~{3,})")
    problems: list[str] = []
    open_line = 0
    open_marker = ""
    for i, line in enumerate(lines, 1):
        m = fence.match(line)
        if not m:
            continue
        marker = m.group(1)
        if open_marker == "":
            open_line = i
            open_marker = marker
        elif marker[0] == open_marker[0] and len(marker) >= len(open_marker):
            open_marker = ""
    if open_marker != "":
        problems.append(
            f"{path}:{open_line}: unclosed code fence ({open_marker}) - "
            f"everything after this line renders as code on GitHub"
        )
    return problems


def check_tables(path: str, lines: list[str]) -> list[str]:
    problems: list[str] = []
    i = 0
    while i < len(lines):
        if SEPARATOR.match(lines[i]) and i > 0 and i + 1 < len(lines):
            header = lines[i - 1]
            prev = lines[i - 2] if i >= 2 else ""
            if not header.startswith("|"):
                problems.append(f"{path}:{i}: MD055 separator row not under a header row")
            elif prev.strip() != "" and not SEPARATOR.match(prev):
                problems.append(
                    f"{path}:{i}: MD058 no blank line before the table "
                    f"header - GitHub will not render the table"
                )
            block = [header, lines[i]]
            j = i + 1
            while j < len(lines) and lines[j].startswith("|"):
                block.append(lines[j])
                j += 1
            cols = [row.count("|") - 1 for row in block]
            if len(set(cols)) != 1:
                bad = sorted({c for c in cols if c != cols[0]})
                problems.append(
                    f"{path}:{i}: MD056 ragged table - rows with {bad} "
                    f"cells instead of {cols[0] + 1}"
                )
            for k, row in enumerate(block):
                if not re.match(r"^\|.*\|\s*$", row):
                    problems.append(
                        f"{path}:{i + k}: MD055 table row does not begin and end with a pipe"
                    )
            if j < len(lines) and lines[j].strip() != "":
                problems.append(f"{path}:{j}: MD058 no blank line after the table")
            i = j
        else:
            i += 1
    return problems


def main(argv: list[str]) -> int:
    problems: list[str] = []
    for path in argv:
        problems.extend(check(path))
    if problems:
        print("markdown check FAILED:")
        for p in problems:
            print(f"  {p}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
