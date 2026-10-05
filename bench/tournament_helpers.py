"""bench.tournament_helpers -- the shared CSV readers between the
store and the tournament (session 38, addendum 15 refactor).
Extracted verbatim; addendum citations stay."""

from __future__ import annotations

import csv
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _climb_csv_partial(
    models_dir: str | None, fam: str | None, climb: int, depth: int
) -> int | None:
    """The climb's committed FWE CSV holds the actual `partial` word
    count for cell (climb, depth); None means no CSV (the cell is
    unmeasured at this depth and stays dropped at a stricter bar)."""
    if not models_dir or not fam:
        return None
    cdir = os.path.join(models_dir, "tournament-results", fam, f"climb{climb}")
    if not os.path.isdir(cdir):
        return None
    matches = glob.glob(os.path.join(cdir, f"*-{depth}-fwe.csv"))
    if len(matches) != 1:
        return None
    try:
        with open(matches[0], newline="") as fh:
            rows = list(csv.DictReader(fh))
    except OSError:
        return None
    if len(rows) != 1:
        return None
    try:
        return int(rows[0]["partial"])
    except (KeyError, TypeError, ValueError):
        return None
