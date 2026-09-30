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
      ("replace", old, new),
      ("insert_before", anchor_line, new_line),
      ("insert_after", anchor_line, new_line),
      ("delete", old),
  ])
  # -> None on success; raises CodeEditError with file state on failure.

DESIGN RULES
  - edits apply in order; each block is verified against the CURRENT
    buffer (so a later block can rely on an earlier one)
  - write is atomic (temp file + os.replace), then fsync of the file
    AND its directory, so the change survives a hard crash
  - after writing, the file is RE-READ and every block re-verified -
    what the disk says is what the caller gets
  - no regex, no fuzzy matching, no indentation magic: the caller
    states exactly what to change; ambiguity is a hard error
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Sequence

__all__ = ["CodeEditError", "edit", "apply_patch_blocks"]


class CodeEditError(Exception):
    """An edit block failed verification - the file was NOT modified."""


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
        if block[0] in ("replace", "replace_all") and block[2] and block[2] not in now:
            raise CodeEditError(
                f"{path}: block {i} verify-after-write failed (new text not on disk)"
            )
        if block[0] in ("insert_before", "insert_after") and block[2] and block[2] not in now:
            raise CodeEditError(
                f"{path}: block {i} verify-after-write failed (inserted text not on disk)"
            )
        if block[0] == "delete" and block[1] in now:
            raise CodeEditError(
                f"{path}: block {i} verify-after-write failed (deleted text still on disk)"
            )


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
