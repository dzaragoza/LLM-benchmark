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

from bench import cells as bench_cells
from bench.constants import CORPUS_DEFAULT, RUNG_DEFAULT, TASK_PASS_BARS

# session 43: ARC and FWE are retired (R-05 RETIRED) - v7 owns the
# reach axis; stored certify/certify_arc cells remain readable history
# but no new arc/fwe cell is measured.
COMBINED_TASKS = ("speed", "vt")


def _task_load(
    fst: dict[str, Any],
    depth: int,
    task: str,
    min_words: int,
    models_dir: str,
    fam: str,
    want: dict[str, Any] | None = None,
) -> dict[int, bool]:
    """The pass/fail cell map for one task at one rung, from whatever
    evidence already exists (combined mode: a cell's task measurement
    is loaded if present, measured later only if missing). `want` is
    the variant being certified (session 40, addendum 26): a stored
    cell measured under another variant does NOT load."""
    legacy = stored_variant(fst)
    if task == "vt":
        # addendum 54: the gate bar is TASK_PASS_BARS["vt"] (4/5), same
        # consistency ruling as arc (addenda 52-53) - the 5/5 gate was
        # the refactor's drift, not a difficulty choice
        return {r: p >= TASK_PASS_BARS["vt"] for r, p in vt_cells(fst, depth, want, legacy).items()}
    if task == "speed":
        return {r: p == 0 for r, p in speed_cells(fst, depth, want, legacy).items()}
    raise ValueError(f"task {task!r} is retired or unknown (session 43: speed and vt only)")


def variant_of(
    fst: dict[str, Any],
    rung: str | None,
    default_k: str | None = None,
    default_v: str | None = None,
) -> dict[str, Any] | None:
    """The variant actually configured for a family at a rung
    (session 40, addendum 26): rung + KV quants, resolved the same
    way the certify controllers resolve them - the run's stored
    quants, then the tournament entry's, then the state default."""
    if not rung:
        return None
    run = (fst.get("runs") or {}).get(rung, {})
    entry = fst.get("tournament_entry") or {}
    return {
        "rung": rung,
        "kv_k": run.get("kv_quant_k") or entry.get("kv_quant_k") or default_k,
        "kv_v": run.get("kv_quant_v") or entry.get("kv_quant_v") or default_v,
    }


def stored_variant(
    fst: dict[str, Any],
    default_k: str | None = None,
    default_v: str | None = None,
) -> dict[str, Any] | None:
    """The variant the family's STORED selection resolves to - the
    variant every pre-override (legacy int) cell was measured under,
    by construction: before --force-rung the controllers always ran
    the stored selection."""
    rung = fst.get("selected") or (fst.get("tournament_entry") or {}).get("rung") or RUNG_DEFAULT
    return variant_of(fst, rung, default_k, default_v)


def _rec_variant(p: Any) -> tuple[Any, Any, Any] | None:
    if not isinstance(p, dict):
        return None
    return (p.get("rung"), p.get("kv_k"), p.get("kv_v"))


def _variant_key(v: dict[str, Any] | None) -> tuple[Any, Any, Any]:
    return (v or {}).get("rung"), (v or {}).get("kv_k"), (v or {}).get("kv_v")


def _int_cells(
    direct: Any,
    want: dict[str, Any] | None = None,
    legacy: dict[str, Any] | None = None,
) -> dict[int, int]:
    """{run: value} from a stored namespace, guarded (session 40,
    addendum 23, found by crosshair): a state file is loaded JSON -
    a corrupt non-numeric key once crashed int() and took the whole
    certify run down with it. Corrupt entries are skipped, not
    fatal; the re-grade never sees them.
    Variant filtering (session 40, addendum 26): a cell record may
    carry the variant that measured it ({v, rung, kv_k, kv_v}). When
    `want` is given, only matching-variant records load - a cell
    measured under another variant is UNMEASURED for this run, not
    silently trusted. Plain legacy records predate variant tracking
    and match only the family's STORED selection (`legacy`) - by
    construction that is the variant they were measured under."""
    cells: dict[int, int] = {}
    if not isinstance(direct, dict):
        return cells
    for r, p in direct.items():
        try:
            if isinstance(p, dict):
                value = int(p.get("v"))
            else:
                value = int(p)
            if want is not None:
                rec = _rec_variant(p)
                if rec is not None:
                    if rec != _variant_key(want):
                        continue
                elif _variant_key(legacy) != _variant_key(want):
                    continue
            cells[int(r)] = value
        except (TypeError, ValueError):
            continue
    return cells


def cell_record(
    value: int,
    variant: dict[str, Any] | None = None,
    seconds: float | None = None,
) -> Any:
    """A stored cell record: the graded value plus, when a variant is
    known, the variant that measured it (session 40, addendum 26).
    Addendum 32: carries the wall seconds ({t}) - the per-test cost.
    Legacy plain-int records remain readable - they predate variant
    tracking and are attributed to the family's stored selection."""
    if variant is None:
        return value
    return {
        "v": value,
        "rung": variant.get("rung"),
        "kv_k": variant.get("kv_k"),
        "kv_v": variant.get("kv_v"),
        "t": round(seconds, 1) if seconds is not None else None,
    }


def _task_store(
    fst: dict[str, Any],
    depth: int,
    task: str,
    run: int,
    value: int,
    variant: dict[str, Any] | None = None,
    seconds: float | None = None,
) -> None:
    """Persist one cell's graded record in its own namespace (the
    combined controller never re-measures a stored cell-task).
    Session 40, addendum 26: the record carries the VARIANT that
    measured it ({v, rung, kv_k, kv_v}) - the author will try
    several variants per model, so a score without its variant is
    unattributable. Addendum 32: the record carries the WALL SECONDS
    the test took ({t}) - the per-test cost, so the expensive tests
    are visible and the cheap ones are too."""
    ns = {
        "vt": "certify_vt",
        "speed": "certify_speed",
    }[task]
    record: Any = value
    if variant is not None:
        record = {
            "v": value,
            "rung": variant.get("rung"),
            "kv_k": variant.get("kv_k"),
            "kv_v": variant.get("kv_v"),
            "t": round(seconds, 1) if seconds is not None else None,
        }
    fst.setdefault(ns, {}).setdefault(str(depth), {})[str(run)] = record


class WindowCap(Exception):
    """The model's trained window cannot run the rung at all (session
    41, addendum 45): the server capped the requested -c down to
    n_ctx_train, so the depth budget overflows and every deep turn
    400s - the cell was never measurable. The family is OUT of the
    benchmark (the author's ruling), never re-attempted, and its
    cells never enter any statistic."""

    def __init__(self, window_cap: int | None) -> None:
        self.window_cap = window_cap
        super().__init__(f"trained window {window_cap} caps the rung")


def _task_measure(
    task: str,
    model: str,
    depth: int,
    results_dir: str,
    run: int,
    port: int,
    kv_k: str | None,
    kv_v: str | None,
    min_words: int,
) -> tuple[bool, int, str, float]:
    """Measure one cell's one task. Returns (passed_at_gold, graded
    record, human line, wall seconds - session 40, addendum 32: the
    per-test cost, so the expensive tests are visible). The graded
    record is the speed stall count, the VT 5-name
    count - all re-gradable at any bar later without re-measuring.
    Raises WindowCap when the launch's banner shows the trained
    window below the rung's ctx (addendum 45) - that is not a FAIL,
    the cell was never measurable."""
    t0 = time.time()
    if task == "speed":
        ok, fv = bench_cells.speed_cell(
            model,
            depth,
            CORPUS_DEFAULT,
            results_dir,
            run,
            port,
            kv_quant_k=kv_k,
            kv_quant_v=kv_v,
        )
        if fv.get("error") == "capped to the window":
            raise WindowCap(fv.get("window_cap"))
        stalls = int(fv.get("stalls") or 0)
        n_turns = int(fv.get("turns") or 0)
        return (
            ok,
            stalls,
            (f"speed: {stalls} stall(s) in {n_turns} turns -> {'PASS' if ok else 'FAIL'}"),
            time.time() - t0,
        )
    if task == "vt":
        ok, fv = bench_cells.vt_pass(
            model,
            depth,
            results_dir,
            seed=run,
            port=port,
            kv_quant_k=kv_k,
            kv_quant_v=kv_v,
        )
        if fv.get("error") == "capped to the window":
            raise WindowCap(fv.get("window_cap"))
        partial = int((fv.get("words_found") or [0])[0] or 0)
        return (
            ok,
            partial,
            f"vt: {partial}/5 names -> {'PASS' if ok else 'FAIL'}",
            time.time() - t0,
        )
    raise ValueError(f"task {task!r} is retired or unknown (session 43: speed and vt only)")


def speed_cells(
    fst: dict[str, Any],
    depth: int,
    want: dict[str, Any] | None = None,
    legacy: dict[str, Any] | None = None,
) -> dict[int, int]:
    """The redesigned speed gate's cell model (session 38, addendum 2):
    cell = (model, rung, conversation r), stored in certify_speed as
    {run: stall count}. Gold bar = 0 stalls; the counts re-grade at
    any 'at most x stalls' bar later without re-measuring."""
    return _int_cells((fst.get("certify_speed") or {}).get(str(depth)), want, legacy)


def vt_cells(
    fst: dict[str, Any],
    depth: int,
    want: dict[str, Any] | None = None,
    legacy: dict[str, Any] | None = None,
) -> dict[int, int]:
    """The VT cell model: a cell is (model, run, task) and is NEVER
    measured twice. VT inherits NOTHING from the tournament (the
    climbs were FWE) - every cell is fresh, stored in the separate
    certify_vt namespace as {run: partial 0..5} (the graded score,
    like the FWE x/3 word count; pass = 5, re-gradable at any bar
    later without re-measuring)."""
    return _int_cells((fst.get("certify_vt") or {}).get(str(depth)), want, legacy)


def stamp(msg: str) -> None:
    import time

    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_state(path: str) -> dict[str, Any]:
    """The state file loader (moved here in the addendum-15 refactor:
    the bench modules save state mid-controller and must not import
    the orchestrator)."""
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"state file corrupt ({e}); starting fresh")
    return {"families": {}}


def save_state(path: str, state: dict[str, Any]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, path)
