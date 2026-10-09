"""bench.state_store -- the never-re-measure store (session 38,
addendum 15: the full_benchmark.py refactor). The task
namespaces (certify_vt, certify_speed) and their loaders; a cell is
stored once and only once. The retired certify/certify_arc namespaces
are historical state, never read - no backward compatibility
(session 43 retired the fwe/arc tasks; session 44 removed the
readers). Extracted verbatim -- addendum citations stay."""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# session 43: ARC and FWE are retired (R-05 RETIRED) - v7 owns the
# reach axis; stored certify/certify_arc cells remain readable history
# but no new arc/fwe cell is measured.
COMBINED_TASKS = ("speed", "vt")


def stamp(msg: str) -> None:
    import time

    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


class StateSchemaError(Exception):
    """The state file violates its schema (session 44, R-22). The
    message carries the exact offending path - `families.<name>.
    certify_vt.8192.3: expected int or object record, got str` - so
    the corruption is findable by hand, never silently swallowed."""


def validate_state(state: Any) -> dict[str, Any]:
    """The state-file schema (session 44, R-22): fail LOUDLY with the
    exact path on a corrupt file, instead of the two failure modes
    that predate it - json.load crashing on bad JSON (the
    orchestrator's loader had no guard at all) and the silent
    start-fresh that discards measured cells without a word. The
    schema is deliberately loose where state is open-ended
    (tournament metadata, verdict prose) and strict where machinery
    reads typed values (cell records, v7 scores).

    A corrupt state file is NEVER wiped - the caller aborts, the
    git rail keeps the file, and the author repairs by hand."""
    if not isinstance(state, dict):
        raise StateSchemaError("$: expected object, got " + type(state).__name__)
    fams = state.get("families")
    if not isinstance(fams, dict):
        raise StateSchemaError("families: expected object, got " + type(fams).__name__)
    for fam, fst in fams.items():
        if not isinstance(fst, dict):
            raise StateSchemaError(f"families.{fam}: expected object, got {type(fst).__name__}")
        for ns in ("certify_vt", "certify_speed"):
            depths = fst.get(ns)
            if depths is None:
                continue
            if not isinstance(depths, dict):
                raise StateSchemaError(
                    f"families.{fam}.{ns}: expected object, got {type(depths).__name__}"
                )
            for depth, cells in depths.items():
                if not isinstance(cells, dict):
                    raise StateSchemaError(
                        f"families.{fam}.{ns}.{depth}: expected object, got {type(cells).__name__}"
                    )
                for run, rec in cells.items():
                    if isinstance(rec, bool) or not isinstance(rec, (int, dict)):
                        raise StateSchemaError(
                            f"families.{fam}.{ns}.{depth}.{run}: expected int or object record, "
                            f"got {type(rec).__name__}"
                        )
                    if isinstance(rec, dict):
                        if "v" not in rec:
                            raise StateSchemaError(
                                f"families.{fam}.{ns}.{depth}.{run}: record object lacks 'v'"
                            )
        v7 = fst.get("v7")
        if v7 is None:
            continue
        if not isinstance(v7, dict):
            raise StateSchemaError(f"families.{fam}.v7: expected object, got {type(v7).__name__}")
        for ctx, cell in v7.items():
            if not isinstance(cell, dict):
                raise StateSchemaError(
                    f"families.{fam}.v7.{ctx}: expected object, got {type(cell).__name__}"
                )
            score = cell.get("score")
            if score is not None and (
                isinstance(score, bool) or not isinstance(score, (int, float))
            ):
                raise StateSchemaError(
                    f"families.{fam}.v7.{ctx}.score: expected number or null, "
                    f"got {type(score).__name__}"
                )
    return state


def load_state(path: str) -> dict[str, Any]:
    """The state file loader (moved here in the addendum-15 refactor:
    the bench modules save state mid-controller and must not import
    the orchestrator). Session 44, R-22: the loaded file is schema-
    validated - corruption raises StateSchemaError with the exact
    path (loud), never the silent start-fresh that silently
    discarded measured cells."""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return validate_state(json.load(f))
    return {"families": {}}


def save_state(path: str, state: dict[str, Any]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, path)
