#!/usr/bin/env python3
"""code_edit.py - deterministic single-file code edits for the agent
(session 34, addendum 20).

THE PROBLEM IT SOLVES: conversational editing (heredocs, hand-typed
diffs, string-paste tools) fails on whitespace, duplicate matches, and
silent partial writes. This tool makes an edit a TRANSACTION:

  verify -> apply -> write -> flush to disk -> re-read -> assert

Every edit is one of three kinds, each checked BEFORE anything is
written:
  replace   one exact occurrence of old text with new text
  insert    new text before/after an exact anchor line
  delete    one exact occurrence of text

USAGE
  import code_edit
  code_edit.edit("full_benchmark.py", [
      ("replace", old, new),             # one exact occurrence (must be unique)
      ("replace_all", old, new),         # every occurrence
      ("replace_n", old, new, 1),        # occurrence k of old (1-based), for dupes
      ("replace_regex", pattern, new),   # re.sub, count=1; pattern must match once
      ("insert_before", anchor, new),
      ("insert_after", anchor, new),
      ("delete", old),
      ("set_lines", first, last, new_lines),   # 1-based inclusive line range
      ("insert_lines", line, new_lines),       # insert BEFORE the 1-based line
      ("delete_lines", first, last),           # 1-based inclusive
      ("indent", first, last, "    "),          # prefix each line in range
      ("dedent", first, last, "    "),          # remove the prefix
      ("append", text),                  # end of file
      ("prepend", text),                 # start of file
  ])
  code_edit.write("new_file.py", content)  # create/overwrite - same atomic write
  # -> None on success; raises CodeEditError with file state on failure.

DESIGN RULES
  - edits apply in order; each block is verified against the CURRENT
    buffer (so a later block can rely on an earlier one)
  - write is atomic (temp file + os.replace), then fsync of the file
    AND its directory, so the change survives a hard crash
  - after writing, the file is RE-READ and every block re-verified -
    what the disk says is what the caller gets
  - no fuzzy matching: the caller states exactly what to change;
    ambiguity is a hard error. replace_regex is the one escape hatch
    (re.sub with count=1; the pattern must match exactly once)
  - line-range blocks are 1-BASED and inclusive, like an editor's
    selection; new_lines may be a string (one line, no newline
    needed) or a list of strings
"""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Sequence

__all__ = ["CodeEditError", "edit", "write", "apply_patch_blocks"]


class CodeEditError(Exception):
    """An edit block failed verification - the file was NOT modified."""


def _as_lines(text: str | Sequence[str]) -> list[str]:
    """new_lines may be a string (one line, newline optional) or a
    list/sequence of lines; returns bare lines (no newline)."""
    if isinstance(text, str):
        if not text:
            return []
        if not text.strip():
            return [text.rstrip("\n")]
        return text.rstrip("\n").split("\n")
    return [str(x).rstrip("\n") for x in text]


def _lines_of(buf: str) -> tuple[list[str], bool]:
    """Split into lines; trailing is True when the file ends with a
    newline (the join must restore it)."""
    trailing = buf.endswith("\n")
    lines = buf.split("\n")
    if trailing:
        lines = lines[:-1]
    return lines, trailing


def _join(lines: list[str], trailing: bool) -> str:
    return "\n".join(lines) + ("\n" if trailing else "")


def _check_range(first: object, last: object, n: int, i: int) -> tuple[int, int]:
    if not isinstance(first, int) or not isinstance(last, int):
        raise CodeEditError(f"block {i}: line range must be two ints - got {first!r}, {last!r}")
    if first < 1 or last < first or last > n:
        raise CodeEditError(
            f"block {i}: line range [{first}, {last}] out of bounds (file has {n} lines)"
        )
    return first, last


def _replace_nth(buf: str, old: str, new: str, k: int) -> str:
    """Replace the k-th (1-based) occurrence of old with new."""
    parts = buf.split(old)
    return old.join(parts[:k]) + new + old.join(parts[k:])


def _regex_once(buf: str, pattern: str, i: int, flags: int = 0) -> tuple[str, str]:
    matches = list(re.finditer(pattern, buf, flags))
    if len(matches) != 1:
        raise CodeEditError(
            f"block {i}: replace_regex pattern matched {len(matches)} "
            "times - must match exactly once"
        )
    return pattern, buf


def _verify_blocks(src: str, blocks: Sequence[tuple]) -> None:
    """Check every block against src, in order, simulating the apply."""
    buf = src
    for i, block in enumerate(blocks):
        if len(block) < 2:
            raise CodeEditError(f"block {i}: expected (kind, old, new) - got {block!r}")
        kind = block[0]
        if kind == "replace":
            if len(block) != 3:
                raise CodeEditError(f"block {i}: replace needs (replace, old, new)")
            n = buf.count(block[1])
            if n == 0:
                raise CodeEditError(
                    f"block {i}: replace target not found:\n"
                    f"--- target ---\n{block[1][:400]}\n--- end ---"
                )
            if n > 1:
                raise CodeEditError(
                    f"block {i}: replace target found {n} times - add context to make it unique"
                )
            buf = buf.replace(block[1], block[2], 1)
        elif kind == "delete":
            if len(block) != 2:
                raise CodeEditError(f"block {i}: delete needs (delete, old)")
            n = buf.count(block[1])
            if n == 0:
                raise CodeEditError(f"block {i}: delete target not found:\n{block[1][:400]}")
            if n > 1:
                raise CodeEditError(f"block {i}: delete target found {n} times - add context")
            buf = buf.replace(block[1], "", 1)
        elif kind in ("insert_before", "insert_after"):
            if len(block) != 3:
                raise CodeEditError(f"block {i}: insert needs (kind, anchor, new)")
            n = buf.count(block[1])
            if n == 0:
                raise CodeEditError(f"block {i}: anchor not found:\n{block[1][:200]}")
            if n > 1:
                raise CodeEditError(f"block {i}: anchor found {n} times - add context")
            new_text = block[2] + block[1] if kind == "insert_before" else block[1] + block[2]
            buf = buf.replace(block[1], new_text, 1)
        elif kind == "replace_all":
            if len(block) != 3:
                raise CodeEditError(f"block {i}: replace_all needs (replace_all, old, new)")
            if buf.count(block[1]) == 0:
                raise CodeEditError(f"block {i}: replace_all target not found:\n{block[1][:400]}")
            buf = buf.replace(block[1], block[2])
        elif kind == "replace_n":
            if len(block) != 4 or not isinstance(block[3], int) or block[3] < 1:
                raise CodeEditError(f"block {i}: replace_n needs (replace_n, old, new, k>=1)")
            n = buf.count(block[1])
            if n < block[3]:
                raise CodeEditError(
                    f"block {i}: replace_n wants occurrence {block[3]} of "
                    f"{n} found - target not present enough times"
                )
            buf = _replace_nth(buf, block[1], block[2], block[3])
        elif kind == "replace_regex":
            if len(block) != 3:
                raise CodeEditError(f"block {i}: replace_regex needs (replace_regex, pattern, new)")
            try:
                _regex_once(buf, block[1], i)
            except re.error as e:
                raise CodeEditError(f"block {i}: bad regex {block[1]!r}: {e}") from e
            buf = re.sub(block[1], block[2], buf, count=1)
        elif kind == "set_lines":
            if len(block) != 4:
                raise CodeEditError(f"block {i}: set_lines needs (set_lines, first, last, new)")
            lines, trailing = _lines_of(buf)
            first, last = _check_range(block[1], block[2], len(lines), i)
            buf = _join(lines[: first - 1] + _as_lines(block[3]) + lines[last:], trailing)
        elif kind == "insert_lines":
            if len(block) != 3:
                raise CodeEditError(f"block {i}: insert_lines needs (insert_lines, line, new)")
            lines, trailing = _lines_of(buf)
            _check_range(block[1], block[1], len(lines) + 1, i)
            buf = _join(
                lines[: block[1] - 1] + _as_lines(block[2]) + lines[block[1] - 1 :], trailing
            )
        elif kind == "delete_lines":
            if len(block) != 3:
                raise CodeEditError(f"block {i}: delete_lines needs (delete_lines, first, last)")
            lines, trailing = _lines_of(buf)
            first, last = _check_range(block[1], block[2], len(lines), i)
            buf = _join(lines[: first - 1] + lines[last:], trailing)
        elif kind == "indent":
            if len(block) != 4:
                raise CodeEditError(f"block {i}: indent needs (indent, first, last, prefix)")
            lines, trailing = _lines_of(buf)
            first, last = _check_range(block[1], block[2], len(lines), i)
            buf = _join(
                lines[: first - 1]
                + [block[3] + ln for ln in lines[first - 1 : last]]
                + lines[last:],
                trailing,
            )
        elif kind == "dedent":
            if len(block) != 4:
                raise CodeEditError(f"block {i}: dedent needs (dedent, first, last, prefix)")
            lines, trailing = _lines_of(buf)
            first, last = _check_range(block[1], block[2], len(lines), i)
            pre = block[3] if isinstance(block[3], str) else "    "
            buf = _join(
                lines[: first - 1]
                + [
                    ln[len(pre) :] if ln.startswith(pre) else ln.lstrip()
                    for ln in lines[first - 1 : last]
                ]
                + lines[last:],
                trailing,
            )
        elif kind == "append":
            if len(block) != 2:
                raise CodeEditError(f"block {i}: append needs (append, text)")
            buf = buf + block[1]
        elif kind == "prepend":
            if len(block) != 2:
                raise CodeEditError(f"block {i}: prepend needs (prepend, text)")
            buf = block[1] + buf
        else:
            raise CodeEditError(f"block {i}: unknown kind {kind!r}")


def _apply(src: str, blocks: Sequence[tuple]) -> str:
    buf = src
    for block in blocks:
        kind = block[0]
        if kind == "replace":
            buf = buf.replace(block[1], block[2], 1)
        elif kind == "delete":
            buf = buf.replace(block[1], "", 1)
        elif kind == "replace_all":
            buf = buf.replace(block[1], block[2])
        elif kind == "insert_before":
            buf = buf.replace(block[1], block[2] + block[1], 1)
        elif kind == "insert_after":
            buf = buf.replace(block[1], block[1] + block[2], 1)
        elif kind == "replace_n":
            buf = _replace_nth(buf, block[1], block[2], block[3])
        elif kind == "replace_regex":
            buf = re.sub(block[1], block[2], buf, count=1)
        elif kind == "set_lines":
            lines, trailing = _lines_of(buf)
            buf = _join(lines[: block[1] - 1] + _as_lines(block[3]) + lines[block[2] :], trailing)
        elif kind == "insert_lines":
            lines, trailing = _lines_of(buf)
            buf = _join(
                lines[: block[1] - 1] + _as_lines(block[2]) + lines[block[1] - 1 :], trailing
            )
        elif kind == "delete_lines":
            lines, trailing = _lines_of(buf)
            buf = _join(lines[: block[1] - 1] + lines[block[2] :], trailing)
        elif kind == "indent":
            lines, trailing = _lines_of(buf)
            buf = _join(
                lines[: block[1] - 1]
                + [block[3] + ln for ln in lines[block[1] - 1 : block[2]]]
                + lines[block[2] :],
                trailing,
            )
        elif kind == "dedent":
            lines, trailing = _lines_of(buf)
            pre = block[3] if isinstance(block[3], str) else "    "
            buf = _join(
                lines[: block[1] - 1]
                + [
                    ln[len(pre) :] if ln.startswith(pre) else ln.lstrip()
                    for ln in lines[block[1] - 1 : block[2]]
                ]
                + lines[block[2] :],
                trailing,
            )
        elif kind == "append":
            buf = buf + block[1]
        elif kind == "prepend":
            buf = block[1] + buf
    return buf


def _atomic_write_sync(path: str, content: str) -> None:
    """Write to a temp file in the same directory, fsync it, os.replace
    over the target, then fsync the DIRECTORY entry - the rename is
    what makes it crash-atomic; the dir fsync is what makes the rename
    itself durable."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".code_edit_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        dir_fd = os.open(d, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def edit(path: str, blocks: Sequence[tuple]) -> None:
    """Apply edit blocks to a file as one verified transaction.

    Raises CodeEditError (file untouched) when any block cannot be
    verified against the current content.
    """
    with open(path, encoding="utf-8") as f:
        src = f.read()
    _verify_blocks(src, blocks)
    out = _apply(src, blocks)
    _atomic_write_sync(path, out)
    # re-read from disk and re-verify the post-conditions
    with open(path, encoding="utf-8") as f:
        now = f.read()
    if now != out:
        raise CodeEditError(
            f"{path}: disk content diverged after write - the file may be corrupt; re-check"
        )
    for i, block in enumerate(blocks):
        if block[0] in ("replace", "replace_all", "replace_n") and block[2] and block[2] not in now:
            raise CodeEditError(
                f"{path}: block {i} verify-after-write failed (new text not on disk)"
            )
        if (
            block[0]
            in (
                "insert_before",
                "insert_after",
                "set_lines",
                "insert_lines",
                "append",
                "prepend",
            )
            and block[-1]
            and _as_lines(block[-1])
            and all(ln in now for ln in _as_lines(block[-1])) is False
            and block[-1] not in now
        ):
            raise CodeEditError(
                f"{path}: block {i} verify-after-write failed (inserted text not on disk)"
            )
        if block[0] == "delete" and block[1] in now:
            raise CodeEditError(
                f"{path}: block {i} verify-after-write failed (deleted text still on disk)"
            )
        if block[0] == "replace_regex":
            try:
                if not re.search(block[1], now):
                    raise CodeEditError(
                        f"{path}: block {i} verify-after-write failed (pattern result not on disk)"
                    )
            except re.error as e:
                raise CodeEditError(f"{path}: block {i}: bad regex: {e}") from e


def write(path: str, content: str) -> None:
    """Create or overwrite a file with the same atomic, synced write
    as edit(); the ONLY path for new files (an edit on a missing file
    is still an error - write is deliberate)."""
    _atomic_write_sync(path, content)
    with open(path, encoding="utf-8") as f:
        if f.read() != content:
            raise CodeEditError(f"{path}: disk content diverged after write - re-check")


def apply_patch_blocks(path: str, blocks: Sequence[tuple]) -> None:
    """Alias kept for callers that think in patch blocks."""
    edit(path, blocks)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", help="file to edit")
    ap.add_argument(
        "--check",
        action="store_true",
        help="verify blocks only (JSON on stdin) - no write",
    )
    args = ap.parse_args()
    import json
    import sys

    spec = json.load(sys.stdin)
    if args.check:
        with open(args.path, encoding="utf-8") as f:
            _verify_blocks(f.read(), [tuple(b) for b in spec["blocks"]])
        print("OK - all blocks verify")
    else:
        edit(args.path, [tuple(b) for b in spec["blocks"]])
        print(f"OK - {len(spec['blocks'])} block(s) applied and synced to {args.path}")
