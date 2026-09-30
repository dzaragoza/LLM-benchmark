"""Tee stdout/stderr to the terminal and to ./results.txt (session 34 WoW).

The author no longer pastes terminal output (session 34, addendum 139): every
command the agent hands over writes its full stdout/stderr to results.txt in
addition to the terminal, and the run ends with a commit+push so the agent can
read the output from the repo. Append mode - the file accumulates runs, each
prefixed with a timestamped command header.
"""

from __future__ import annotations

import datetime
import sys
from typing import TextIO


class _Tee:
    def __init__(self, *streams: TextIO) -> None:
        self._streams = streams

    def write(self, data: str) -> int:
        written = 0
        for s in self._streams:
            written = s.write(data)
        return written

    def flush(self) -> None:
        for s in self._streams:
            s.flush()

    def isatty(self) -> bool:
        return False


_ORIG_STDOUT = sys.stdout
_ORIG_STDERR = sys.stderr


def uninstall() -> None:
    """Stop writing to results.txt (restore the original stdout/stderr)."""
    sys.stdout = _ORIG_STDOUT
    sys.stderr = _ORIG_STDERR


def install(path: str = "./results.txt") -> None:
    """Duplicate stdout and stderr into `path` (append); no-op if not writable."""
    try:
        fh = open(path, "a", encoding="utf-8", buffering=1)
    except OSError:
        return
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    cmd = " ".join(sys.argv)
    fh.write(f"\n===== {stamp} | {cmd} =====\n")
    fh.flush()
    sys.stdout = _Tee(sys.stdout, fh)  # type: ignore[assignment]
    sys.stderr = _Tee(sys.stderr, fh)  # type: ignore[assignment]
