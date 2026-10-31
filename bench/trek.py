"""bench.trek -- protocol trek v2: walkers over exam histories.

THE STATE (the author's v2 redesign): the single source of truth is
the EXAM HISTORY per candidate (model, model_quant, k, v):

    history = {
      0: {"status": "pass", "time_s": 0.3},
      1: {"status": "pass", "time_s": 0.5},
      2: {"status": "timeout", "timeout_s": 2.0},
    }

Levels are graded as always; a timeout records the budget it was
taken under. A candidate is fully described by its history - any
walker at any budget derives everything:

  - a 4s walker sees level 2's timeout_2s < 4s: RE-RUN from level 2
  - a 2s walker sees timeout_2s == its budget: SETTLED - score 2
  - a 1s walker reads the passes under 1s: score 2, no work needed

THE WALKERS are derivations: each walks the (model, quant) grid with
its own budget (the clock ladder 1, 2, ..., 128s); its score for a
cell is derived from the pair's 49 candidate histories (the best
score achievable under the budget - a level settled as timeout at a
smaller budget may pass at a bigger one). The walk's movements are
the only accounting: 95 per epoch, every step costs one, teleport to
the best on the epoch's end, a repeated teleport target doubles the
budget (or ends the trek at 128s).

THE GRID: 64 models (rows, params-ascending) x 32 quants (cols,
bpw-ascending); (0,0) is the top-left corner.

THE WALKER SEED: ONE seed for the whole run (the CLI --seed), for
all the walkers - never re-seeded (the v2 ruling). The first walker
starts at (-1,-1): both coordinates are drawn, and that random cell
is the initial position. Everything is deterministic: the same seed
produces the same walk and the same exams (the exam seeds are
candidate-deterministic - a fixed function of the candidate - so the
exam histories are reproducible and shared across seeds' walkers).

NOTE the two randomness layers never mix: the walker seed drives the
walk; the exam seeds are a fixed derivation per candidate.
"""

from __future__ import annotations

import json
import os
import random
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bench.contracts import warn_contract
from bench.roster import LADDER, dyadic_picks, roster_from_models_md

# ------------------------------------------------------------- constants

TREK_STATE_FILE = "state/trek-state.json"

# THE EPOCH DERIVES FROM THE GRID DIMENSIONS (the author's ruling):
# the max movements = n_rows + n_cols - 1 (64 + 15 - 1 = 78 on the
# safe grid); the max evaluations = n_rows + n_cols (the spawn cell +
# the steps - 64 + 15 = 79). Computed once from the grid below.
_EPOCH_MOVEMENTS: int | None = None


def epoch_movements(grid: Grid) -> int:
    """the walker's movement budget per epoch: n_rows + n_cols - 1,
    derived from the grid's dimensions (the author's encoding)."""
    return grid.n_rows + grid.n_cols - 1


def epoch_evaluations(grid: Grid) -> int:
    """the evaluations per epoch (the spawn cell + the steps):
    n_rows + n_cols - derived from the grid's dimensions."""
    return grid.n_rows + grid.n_cols


# the four directions: (row_step, col_step) - no diagonals
DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

# the budget ladder: 1, 2, 4, ..., 128
CLOCK_LADDER = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0]

# THE CANDIDATE-DETERMINISTIC EXAM SEED: the same candidate always
# gets the same exam instance (the same levels, the same papers) -
# the histories are reproducible and shared across walkers/seeds
# THE WALK CANARY (the author's ruling: cheap): the seed-1 walk's
# first 20 picks on the canonical mock landscape (every candidate of
# every picked cell times out at the picked budget - the pure-walk
# shape). The preflight regenerates this and compares: any walk
# semantics change (the spawn, the dispatch, the budget escalation,
# the one-action rule, the movement accounting) shows as a sequence
# diff - the pin bug, the spawn off-by-one, and the dispatch-default
# bug would ALL have been canary diffs. Stored as [row, col,
# movements, budget] tuples.
def grid_fingerprint(grid: "Grid") -> str:
    """THE GRID FINGERPRINT (the grid-expansion lesson): the walk
    record's coordinates (spawn, position, best, epoch_start) are
    meaningful only relative to the grid they were recorded on -
    the 5-model->10-model expansion shifted every row's meaning
    ([1,2] was gemma-3-1b F16, became MiniCPM4-0.5B F16) and the
    replay reset 'resumed' a life whose path was on another
    lattice. The fingerprint (the models + the rungs) detects the
    change; the runner's reset then starts a FRESH life."""
    return f"{grid.n_rows}x{grid.n_cols}:{','.join(grid.models)}"


# THE 10-MODEL GRID'S CANARY (the 10x3 grid, 12-movement epochs):
# the seed-1 walk's first 20 picks on the canonical mock landscape
WALK_CANARY: list[list] = [
    [6, 0, 0, 1.0], [6, 1, 1, 1.0], [7, 1, 2, 1.0], [8, 1, 3, 1.0],
    [7, 1, 4, 2.0], [6, 1, 5, 2.0], [6, 2, 6, 1.0], [5, 2, 7, 1.0],
    [4, 2, 8, 1.0], [5, 2, 9, 2.0], [6, 2, 10, 2.0], [7, 2, 11, 1.0],
    [8, 1, 0, 2.0], [8, 0, 1, 1.0], [7, 0, 2, 1.0], [8, 0, 3, 2.0],
    [7, 0, 4, 2.0], [8, 0, 5, 4.0], [8, 1, 6, 4.0],
]


def walk_canary_sequence() -> list[list]:
    """Regenerate the canary: the seed-1 walk's first 20 picks on the
    canonical mock landscape (deterministic - the same code gives the
    same sequence). Compared against WALK_CANARY by the preflight."""
    grid = Grid()
    kv7 = ["f16", "q8_0", "q4_0"]  # the small grid's 3
    st: dict[str, Any] = {"candidates": {}, "walk": {}}
    seq: list[list] = []
    for _ in range(20):
        p = walk(st, 1)
        if p is None:
            break
        if p["reason"] == "ended":
            ws = st.setdefault("walk", {})
            ws["life"] = ws.get("life", 1) + 1
            ws["position"] = [-1, -1]
            ws["movements"] = 0
            ws["high"] = -1
            ws["dispatched"] = [-1, -1]
            continue
        f, r = grid.cell(p["row"], p["col"])
        for k in kv7:
            for v in kv7:
                st["candidates"].setdefault(cand_key(f, r, k, v), {})[0] = {
                    "status": "timeout",
                    "timeout_s": p["budget"],
                }
        seq.append([p["row"], p["col"], p["movements"], p["budget"]])
    return seq


# THE EXAM SEED (the author's correction): the exam seed counts
# exam REPETITIONS - we run each exam ONCE, so the seed is ALWAYS 1.
# The exam INSTANCE is still candidate-deterministic: the papers
# derive from the candidate's own key (below), so the same candidate
# always gets the same exam, and a re-run under a bigger budget
# continues the same exam faithfully.
EXAM_SEED = 1


def exam_instance_key(fam: str, rung: str, k_quant: str, v_quant: str) -> int:
    """the candidate's exam-instance key: a fixed 8-bit derivation
    of the candidate's identity - the papers (the chain and elevator
    instances per level) derive from this key, so every run of the
    same candidate presents the SAME exam regardless of the walker
    seed, the budget, or the run."""
    h = 0
    for s in (fam, rung, k_quant, v_quant):
        for ch in s:
            h = (h * 31 + ord(ch)) & 0xFF
    return h


# ---------------------------------------------------------- the grid


def _param_of(fam: str) -> float:
    """the family's parameter count from the roster's models.md table
    (the params column; the file is the author-maintained truth)."""
    # parse models.md: the table rows are name | params | f16 | window | repo
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models.md")
    try:
        with open(path, encoding="utf-8") as fh:
            for ln in fh:
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                if (
                    len(cells) >= 5
                    and cells[0] == fam
                    and cells[1] not in ("params", "", "unknown")
                ):
                    try:
                        return float(cells[1])
                    except ValueError:
                        break
    except OSError:
        pass
    return float("inf")


def _models_sorted() -> list[str]:
    """the model list: THE DYADIC PICKS (the author's small-grid
    ruling), sorted by param size ascending - the grid's row axis is
    the param ladder, one model per dyadic tier."""
    fams = [fam for fam, _repo in dyadic_picks()]
    return sorted(fams, key=_param_of)


def _bpw(rung: str) -> float:
    BPW = {
        "F16": 16.0,
        "Q8_0": 8.5,
        "Q6_K": 6.56,
        "Q5_K_M": 5.69,
        "Q5_K_S": 5.54,
        "Q5_1": 5.63,
        "Q5_0": 5.54,
        "Q4_K_M": 4.85,
        "Q4_K_S": 4.58,
        "Q4_1": 5.0,
        "Q4_0": 4.55,
        "IQ4_NL": 4.5,
        "IQ4_XS": 4.25,
        "Q3_K_L": 3.91,
        "Q3_K_M": 3.91,
        "Q3_K_S": 3.5,
        "IQ3_M": 3.66,
        "IQ3_S": 3.44,
        "IQ3_XS": 3.3,
        "IQ3_XXS": 3.06,
        "Q2_K": 3.35,
        "Q2_K_S": 3.0,
        "IQ2_M": 2.7,
        "IQ2_S": 2.5,
        "IQ2_XS": 2.31,
        "IQ2_XXS": 2.06,
        "Q2_0": 3.35,
        "Q1_0": 1.68,
        "IQ1_M": 1.75,
        "IQ1_S": 1.56,
        "TQ1_0": 1.5,
        "TQ2_0": 2.0,
    }
    return BPW.get(rung, 8.0)


def _rungs_by_bpw() -> list[str]:
    return sorted(LADDER, key=_bpw)


class Grid:
    """the 64 x 32 grid: (row, col) <-> (fam, rung) <-> pool index."""

    def __init__(self) -> None:
        self.models = _models_sorted()
        self.rungs = _rungs_by_bpw()
        self.n_rows = len(self.models)
        self.n_cols = len(self.rungs)
        self._pos: dict[tuple[str, str], int] = {}
        i = 0
        for f, _repo in roster_from_models_md():
            for r in LADDER:
                self._pos[(f, r)] = i
                i += 1
        self._idx_to_cell: dict[int, tuple[int, int]] = {}
        for row in range(self.n_rows):
            for col in range(self.n_cols):
                self._idx_to_cell[self.pool_index(row, col)] = (row, col)
        warn_contract(
            "post",
            "grid.dimensions",
            self.n_rows == len(dyadic_picks()) and self.n_cols == len(LADDER),
            f"the grid is {self.n_rows}x{self.n_cols}, expected "
            f"{len(dyadic_picks())}x{len(LADDER)}",
        )
        # the author's contracts: the epoch derives from the grid's
        # dimensions; the models sort by param size ascending; an
        # epoch ends at exactly n_rows + n_cols - 1 movements with
        # n_rows + n_cols evaluations behind it
        warn_contract(
            "inv",
            "grid.epoch_derives",
            epoch_movements(self) == self.n_rows + self.n_cols - 1
            and epoch_evaluations(self) == self.n_rows + self.n_cols,
            f"the epoch budgets do not derive from the grid "
            f"({epoch_movements(self)} movements, {epoch_evaluations(self)} evaluations)",
        )
        warn_contract(
            "post",
            "grid.models_param_sorted",
            all(
                _param_of(self.models[i]) <= _param_of(self.models[i + 1])
                for i in range(len(self.models) - 1)
            ),
            "the model list is not sorted by param size ascending",
        )

    def cell(self, row: int, col: int) -> tuple[str, str]:
        return (self.models[row], self.rungs[col])

    def inside(self, row: int, col: int) -> bool:
        return 0 <= row < self.n_rows and 0 <= col < self.n_cols

    def pool_index(self, row: int, col: int) -> int:
        return self._pos[self.cell(row, col)]

    def row_col_of(self, pool_index: int) -> tuple[int, int] | None:
        return self._idx_to_cell.get(pool_index)


# ------------------------------------------------------- the exam history store


def _int_keys(history: dict[str, Any]) -> dict[int, Any]:
    """JSON turns int level keys into strings on the round-trip -
    normalize them back (the derivations look up int levels; a
    string-keyed history reads as empty and every candidate would
    re-run from level 0). The non-level keys (_launch) pass through
    as-is - the level-typed map is a convention for the level keys,
    and the passthrough keeps the marker visible."""
    out: dict[int, Any] = {}
    for k, v in history.items():
        if isinstance(k, str) and k.lstrip("-").isdigit():
            out[int(k)] = v
        elif isinstance(k, int):
            out[k] = v
        else:
            # the non-level key (_launch): passes through; the map's
            # declared int-key convention is for the LEVELS, and the
            # lookups go through .get(level) with int levels only
            marker: dict[Any, Any] = out
            marker[k] = v
    return out


def load_state(state_file: str = TREK_STATE_FILE) -> dict[str, Any]:
    """the v2 state: {'candidates': {candidate_key: history}, ...}.
    The candidate key: 'fam|rung|k|v'. The history: {level: record}
    - with the level keys normalized back to ints (JSON stringifies
    them on save; the derivations expect ints)."""
    if not os.path.isfile(state_file):
        return {"candidates": {}}
    with open(state_file, encoding="utf-8") as fh:
        st = json.load(fh)
    cands = st.get("candidates", {})
    st["candidates"] = {key: _int_keys(h) for key, h in cands.items()}
    _validate_state(st, "load")
    return st


# THE STATE SCHEMA (the author's ruling, option 1: JSON stays, the
# schema is the fix - the int-key bug was a schema failure, not a
# format failure): the executable declaration of what the state IS.
# save_state validates against it and REFUSES to write a violation
# (the crash-rail philosophy: corrupt data never lands on disk);
# load_state validates after the int-key normalization and refuses
# to serve corrupt state. The schema doubles as the report's data
# dictionary: this is what a candidate's exam history is.
STATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["candidates"],
    "properties": {
        "candidates": {
            "type": "object",
            # the key: 'fam|rung|k|v'
            "additionalProperties": {
                "type": "object",
                # the history: level -> record. The level keys are
                # ints in memory; JSON stringifies on disk (the
                # loader normalizes back - the schema accepts both)
                "additionalProperties": {
                    "oneOf": [
                        {  # a passed level: the time is required
                            "type": "object",
                            "required": ["status", "time_s"],
                            "properties": {
                                "status": {"const": "pass"},
                                "time_s": {"type": "number", "minimum": 0},
                            },
                            "additionalProperties": False,
                        },
                        {  # a timeout: the budget is required
                            "type": "object",
                            "required": ["status", "timeout_s"],
                            "properties": {
                                "status": {"const": "timeout"},
                                "timeout_s": {"type": "number", "exclusiveMinimum": 0},
                            },
                            "additionalProperties": False,
                        },
                        {  # a settled failure (the closing budget rides
                            # the record - the radio's attempted-bracket
                            # evidence needs it)
                            "type": "object",
                            "required": ["status"],
                            "properties": {
                                "status": {"enum": ["wrong answer", "out of paper", "error"]},
                                "detail": {"type": "string"},
                                "budget_s": {"type": "number", "exclusiveMinimum": 0},
                            },
                            "additionalProperties": False,
                        },
                        {  # the launch-failure marker (not a level)
                            "type": "object",
                            "required": ["status"],
                            "properties": {
                                "status": {"const": "failed"},
                                "detail": {"type": "string"},
                            },
                            "additionalProperties": False,
                        },
                    ]
                },
            },
        },
        "last_budget": {"type": "number"},
        "walks": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "epoch": {"type": "integer", "minimum": 1},
                    "position": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                    "movements": {"type": "integer", "minimum": 0},
                    "high": {"type": "integer"},
                    "best": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                    "targets": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 2,
                            "maxItems": 2,
                        },
                    },
                },
            },
        },
    },
}


def _validate_state(st: dict[str, Any], where: str) -> None:
    """the schema gate: refuse corrupt state - on SAVE (never write
    it) and on LOAD (never serve it). The int-key normalization
    runs FIRST (load_state), so the in-memory form always has int
    levels and the schema's oneOf branches check the records.

    THE SCHEMA IS MANDATORY (the author's ruling): no skip path.
    jsonschema is a hard requirement - a missing library is a
    crash, not a degraded mode (the same ruling as the converter
    dependencies: a wrong result silently produced is worse than
    a loud failure)."""
    import jsonschema

    try:
        jsonschema.validate(st, STATE_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValueError(
            f"the trek state fails its schema ({where}): {e.message} at {list(e.absolute_path)}"
        ) from e


def save_state(st: dict[str, Any], state_file: str = TREK_STATE_FILE) -> None:
    """Save the state, SCHEMA-VALIDATED: a violation refuses to
    write (corrupt data never lands on disk - the crash-rail
    philosophy applied to the state itself)."""
    _validate_state(st, "save")
    os.makedirs(os.path.dirname(state_file) or ".", exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=1)


def cand_key(fam: str, rung: str, k: str, v: str) -> str:
    return f"{fam}|{rung}|{k}|{v}"


def history_of(st: dict[str, Any], fam: str, rung: str, k: str, v: str) -> dict[int, Any]:
    return st.get("candidates", {}).get(cand_key(fam, rung, k, v), {})


def score_under(history: dict[int, Any], budget_s: float) -> int:
    """THE DERIVATION: the candidate's score under a walker's budget.
    - levels passed with time <= budget: count (all of them, they pass)
    - the first level not settled under this budget:
        timeout at a SMALLER budget: UNKNOWN at this budget (needs a
        re-run - the timeout happened under a tighter clock)
        timeout at THIS budget: SETTLED - the exam ends here
        wrong answer / out of paper / error: SETTLED - ends here
    The score is the highest level fully passed under the budget.
    Returns -1 when nothing passes; None is never returned."""
    score = -1
    level = 0
    while True:
        rec = history.get(level)
        if rec is None:
            # unmeasured: the exam continues at this level (a re-run
            # would need to measure it); for the SCORE this is where
            # the known history ends
            break
        if rec.get("status") == "pass":
            if rec.get("time_s", 1e9) <= budget_s:
                score = level
                level += 1
                continue
            # passed, but slower than this budget allows: the level
            # does not count under this budget (a stricter walker
            # would have timed out here)
            break
        if rec.get("status") == "timeout":
            t = rec.get("timeout_s", 1e9)
            if t <= budget_s:
                # settled: the exam timed out under this (or a
                # smaller-or-equal) budget - this walker's exam ends
                break
            # timed out under a SMALLER budget: unknown at this one -
            # the derivation stops (a re-run would continue the exam)
            break
        # wrong answer / out of paper / error: settled
        break
    return score


def needs_rerun(history: dict[int, Any], budget_s: float) -> bool:
    """does this candidate need exam work under this budget? True
    when the history's frontier is unsettled: the next unmeasured
    level exists and all prior levels pass under the budget, or a
    prior level timed out under a SMALLER budget (unknown here)."""
    level = 0
    while True:
        rec = history.get(level)
        if rec is None:
            return True  # the exam is unfinished: more to measure
        if rec.get("status") == "pass":
            if rec.get("time_s", 1e9) <= budget_s:
                level += 1
                continue
            # passed slower than the budget: the exam, under this
            # budget, would have timed out here - settled
            return False
        if rec.get("status") == "timeout":
            return rec.get("timeout_s", 1e9) < budget_s  # smaller-budget timeout: re-run
        return False  # wrong answer etc: settled


def pair_state_under(
    st: dict[str, Any],
    fam: str,
    rung: str,
    kv_ladder: list[str],
    budget_s: float,
) -> tuple[int, bool]:
    """the PAIR's (cell's) state under a walker's budget: (best score
    over its 49 candidates, needs_work). The cell is SETTLED when no
    candidate needs a re-run; its score is the best settled score.
    A cell with NO histories at all is unmeasured (-2, needs work)."""
    best = -2
    any_hist = False
    work = False
    for k in kv_ladder:
        for v in kv_ladder:
            h = history_of(st, fam, rung, k, v)
            if not h:
                continue
            any_hist = True
            s = score_under(h, budget_s)
            best = max(best, s)
            if needs_rerun(h, budget_s):
                work = True
    if not any_hist:
        return (-2, True)  # unmeasured
    return (best, work)


# ------------------------------------------------------------- the walker


def cell_action(
    st: dict[str, Any],
    fam: str,
    rung: str,
    kv_ladder: list[str],
) -> tuple[str, float]:
    """THE CELL'S ACTION under the two-phase v3 (the author's
    prospect/dig ruling). Returns (action, budget):
    - ('dig', 128.0): THE DIG - the cell has ANY score > -1 (some
      candidate answered) and still has work at t=128: the walker
      switches immediately to the maximum time and works ALL the
      kv combos at 128, closing the cell in one visit. As soon as
      a candidate shows it can answer, the cell gets the maximum
      chance to show its ceiling.
    - ('exam', 1.0): THE PROSPECT on a NEW cell (no histories) -
      the first exam at t=1
    - ('exam', t*2): THE PROSPECT's escalation - the cell's top
      result is a timeout at t (no score yet) - re-run at the
      doubled budget, exactly as before
    - ('none', 0): no score ever found and the cell is settled
      (every candidate closed, or the top timeout at 128, or a
      fail) - do nothing; the dig never started
    The 'top result' is the best candidate's frontier: the highest
    score any candidate reaches, and what stops it."""
    # THE DIG TRIGGER (the author's phase 2): any score > -1 anywhere
    # in the cell + any work left at the max budget -> dig at 128,
    # closing the cell in one visit
    best = _cell_best_score(st, fam, rung, kv_ladder, 0)
    if best > -1:
        any_work_at_128 = any(
            needs_rerun(history_of(st, fam, rung, k, v), 128.0)
            for k in kv_ladder
            for v in kv_ladder
        )
        if any_work_at_128:
            return ("dig", 128.0)
        return ("none", 0)  # scored and fully settled at 128: done
    # THE SCORE CONVENTION (the off-by-one fix): score = the highest
    # level PASSED = the pass count - 1. A wrong answer AT level k
    # books score k-1, never k. (Found in audit: the old code booked
    # the failing level as the score in the timeout branch.)
    open_caps: list[float] = []
    any_hist = False
    for k in kv_ladder:
        for v in kv_ladder:
            h = history_of(st, fam, rung, k, v)
            if not h:
                continue
            any_hist = True
            # the frontier: the first non-pass level
            level = 0
            rec = h.get(level)
            while rec is not None and rec.get("status") == "pass":
                level += 1
                rec = h.get(level)
            if rec is None:
                # unfinished (an interrupted exam): continue it at its
                # last recorded budget
                return ("exam", max(1.0, _last_budget_of(h)))
            if rec.get("status") == "timeout":
                open_caps.append(float(rec.get("timeout_s", 1.0)))
            # wrong answer / out of paper / error: closed - nothing here
    if not any_hist:
        return ("exam", 1.0)  # a new cell: the first exam at t=1
    if open_caps:
        # THE ONE TIMEOUT SETTING (the author's rule): the cell's live
        # candidates re-run at cap x 2 (max 128; at max, do nothing).
        # The most-due (smallest) cap drives - a desynced cell catches
        # up over visits, one doubling per action.
        cap = min(open_caps)
        if cap >= 128.0:
            return ("none", 0)  # the max budget already evaluated
        return ("exam", min(cap * 2, 128.0))
    return ("none", 0)  # every probed candidate closed: the top result a fail


def cell_sweep_unfinished(
    st: dict[str, Any],
    fam: str,
    rung: str,
    kv_ladder: list[str],
) -> bool:
    """True when the cell's sweep never completed: any candidate
    missing entirely (the sweep interrupted before reaching it) or
    any candidate's exam unfinished (levels recorded but no frontier
    verdict - the sweep died mid-exam). A COMPLETED sweep leaves all
    49 candidates with terminal records (a fail verdict counts -
    terminal is terminal). The walk re-offers such a cell on the
    restart regardless of the dispatch marker - the leftover
    candidates resume (the skip-the-missing bug)."""
    cands = st.get("candidates", {})
    any_hist = False
    for k in kv_ladder:
        for v in kv_ladder:
            h = cands.get(cand_key(fam, rung, k, v))
            if h is None:
                if any_hist:
                    return True  # some measured, this one missing: interrupted
                continue
            any_hist = True
            # an unfinished exam: passes recorded but no frontier verdict
            level = 0
            rec = h.get(level)
            while rec is not None and rec.get("status") == "pass":
                level += 1
                rec = h.get(level)
            if rec is None and level > 0:
                return True  # the exam died mid-run
            if rec is None and not any(
                isinstance(kk, int) or (isinstance(kk, str) and kk.lstrip("-").isdigit())
                for kk in h
            ):
                return True  # only a _launch marker: never really measured
    return False


def _last_budget_of(h: dict[int, Any]) -> float:
    """the newest timeout budget in a history (for the unfinished-
    exam case): the re-run continues at that budget."""
    budgets = [
        rec.get("timeout_s", 1.0)
        for rec in h.values()
        if isinstance(rec, dict) and rec.get("status") == "timeout"
    ]
    return max(budgets) if budgets else 1.0


def walk(
    st: dict[str, Any],
    walker_seed: int = 1,
    kv_ladder: list[str] | None = None,
    max_steps: int = 1_000_000,
) -> dict[str, Any] | None:
    """THE V3 PHASE-A WALKER (the author's spec): the walker acts on
    EVERY cell it stands on - never passes through.

    THE WALK: the walker spawns at a random grid position (drawn
    from the fixed seed-1 stream), sets its high score to -1, and
    evaluates each cell it stands on:
    - a new cell: the exam at t=1
    - the cell's top result a timeout: the exam at timeout x 2
      (max 128s; at max, do nothing)
    - the cell's top result a fail: do nothing
    After the action, the walker draws a random direction and steps
    (95 movements per life; a blocked edge redraws). If the action's
    result improved the high score, the high-score location updates
    to the current cell.

    When the 95 movements are exhausted, the walker teleports to the
    high-score cell and explores again. If it teleports to a cell
    ALREADY marked with the high score (no improvement found in the
    life), the walk ENDS: a new walker spawns at a random position
    and starts a new life. The trek ends when a spawned walker's
    high-score-teleport target repeats - no improvement anywhere.

    THE REPLAY is exact from the persisted walk state: the spawn,
    the position, the movements used, the high score and its cell,
    and the teleports-so-far determine everything (the draws are a
    pure function of the seed and the draw count - actions never
    influence the path, so the replay never diverges).

    Returns {'row','col','fam','rung','action','budget','high',
    'best','life','movements','draws','spawn','reason'} - reason
    'evaluate' (the cell needs the action), 'teleport' (the walker
    returns to its best), 'ended' (the walk finished: the spawn's
    high-score target repeated - the trek is done)."""
    grid = Grid()
    if kv_ladder is None:
        kv_ladder = ["f16", "q8_0", "q4_0"]  # the small grid's 3

    ws = st.setdefault("walk", {})
    rng = random.Random(f"trek-v3-{walker_seed}-{ws.get('draws', 0)}")

    # THE WALK STATE (persisted; the replay's complete truth)
    life = ws.get("life", 1)
    position = tuple(ws.get("position", [-1, -1]))
    movements = ws.get("movements", 0)
    high = ws.get("high", -1)
    best = tuple(ws.get("best", position))
    draws_used = ws.get("draws", 0)
    # THE EPOCH START (the death rule's baseline): the cell where
    # the current epoch began - the spawn cell or the last teleport
    # target. Persisted (a resume mid-epoch must know it); replaces
    # the retired spawn_targets list.
    epoch_start: tuple[int, int] | None = (
        tuple(ws["epoch_start"]) if "epoch_start" in ws else None
    )
    # PRE (phase a): the spawn at (-1,-1) is LEGAL for every life -
    # each new walker spawns at a random position (the v3 ruling) -
    # but the HIGH SCORE must reset with it: a spawned life never
    # inherits the previous life's high
    warn_contract(
        "pre",
        "walk.spawn_resets_high",
        not (position == (-1, -1) and high != -1 and movements > 0),
        f"the spawn at (-1,-1) must reset the high score (found high {high})",
    )

    def draw() -> tuple[int, int]:
        nonlocal draws_used
        draws_used += 1
        ws["draws"] = draws_used
        return DIRECTIONS[rng.randrange(4)]

    epoch_budget = epoch_movements(grid)

    # THE TRANSITION CONTRACTS' BASELINE: the record as of this
    # walk() call's ENTRY - the advance is measured ACROSS calls
    # (per pick), never between the in-call saves (the spawn's save
    # and the dispatch's save legitimately repeat values within one
    # call - the first-call false positive, caught in verification).
    # THE REPLAY FLAG (the author's replay principle): a startup
    # reset rewinds the record to the life's origin - the first pick
    # after it is the LEGITIMATE fresh standing; honored once.
    replay_reset = bool(ws.pop("replay_reset", False))
    entry_record = {
        "life": ws.get("life"),
        "movements": ws.get("movements"),
        "position": list(ws["position"]) if "position" in ws else None,
        "high": ws.get("high"),
        "best": list(ws["best"]) if "best" in ws else None,
    }

    def save() -> None:
        # INV: movements within the epoch budget, never negative
        warn_contract(
            "inv", "walk.movements_in_budget",
            0 <= movements <= epoch_budget,
            f"movements {movements} outside [0, {epoch_budget}]",
        )
        # INV: the high score never decreases within a life
        if life == entry_record.get("life") and entry_record.get("high") is not None:
            warn_contract(
                "inv", "walk.high_monotone",
                high >= entry_record["high"],
                f"the high score decreased within a life "
                f"({entry_record['high']} -> {high})",
            )
        ws["life"] = life
        ws["position"] = list(position)
        ws["movements"] = movements
        ws["high"] = high
        ws["best"] = list(best)
        ws["draws"] = draws_used
        if epoch_start is not None:
            ws["epoch_start"] = list(epoch_start)

    if position == (-1, -1):
        # THE SPAWN IS A TELEPORT, NOT A MOVEMENT (the author's
        # correction): the walker materializes at a random grid
        # position with the high score -1; the spawn costs nothing -
        # the first MOVEMENT is after evaluating the first cell, so a
        # life evaluates 96 cells (the spawn cell + 95 step-cells).
        position = (rng.randrange(grid.n_rows), rng.randrange(grid.n_cols))
        high = -1
        best = position
        movements = 0  # the teleport: free
        epoch_start = position
        # THE LIFE'S ORIGIN RECORD (the replay principle): the spawn
        # coordinates and the draws base at the life's start - the
        # startup replay reset re-walks from HERE, deterministically
        ws["spawn"] = list(position)
        ws["life_draws"] = draws_used
        ws["grid_fp"] = grid_fingerprint(grid)
        save()

    row, col = position
    # THE DISPATCH DEFAULT: nothing dispatched - (-1,-1), never the
    # current position (the fresh-state bug: the default equaled the
    # spawn cell, so the spawn's first action was silently skipped -
    # the walker stepped away without examining its birthplace)
    dispatched = tuple(ws.get("dispatched", [-1, -1]))
    total = 0
    while total < max_steps:
        fam, rung = grid.cell(row, col)
        action, budget = cell_action(st, fam, rung, kv_ladder)
        # THE UNFINISHED-SWEEP OVERRIDE (the skip-the-missing bug): a
        # cell whose sweep never completed (an interrupt mid-sweep
        # leaves the dispatch marker set with candidates unmeasured)
        # re-dispatches on the restart regardless of the marker - the
        # leftover candidates resume. A COMPLETED sweep honors the
        # marker: one action per visit, no escalation loop.
        # THE RE-OFFER RULE, PRECISE (the author's ruling): the walk
        # records the dispatched (action, budget) alongside the
        # marker. On the next call, standing on the same cell:
        # - the cell's action UNCHANGED (the same kind, the same
        #   budget): the dispatched sweep was INTERRUPTED (an
        #   interrupt mid-sweep leaves the histories still showing
        #   the same pending work - the movement-48 incident: the
        #   dig's 43 combos, 42 run, the 43rd's older timeout@32
        #   verdict masked it from the retired detector) -> RE-OFFER,
        #   the leftovers resume.
        # - the cell's action CHANGED (the prospect completed and
        #   escalated; the dig completed and closed): the dispatch
        #   COMPLETED -> honor the marker, step away (the pin guard:
        #   the escalation is work, but it belongs to a LATER visit -
        #   the author's land-exam-move-out ruling).
        dispatched_action = ws.get("dispatched_action")
        # THE LEGACY CASE (the movement-48 lesson's second act): a
        # dispatch made by the PRE-field code carries the marker but
        # no dispatched_action - the comparison would fail and the
        # interrupted dig steps past again. Absent = UNKNOWN, and
        # unknown re-offers: re-offering a COMPLETED action is a
        # no-op (its work list is empty - the completed prospect's
        # timeouts are recorded at its budget, the completed dig's
        # candidates are settled at 128), so the worst case is one
        # wasted acquisition; the best case is the resume.
        interrupted = (
            (row, col) == dispatched
            and (dispatched_action is None or dispatched_action == [action, budget])
        )
        if action in ("exam", "dig") and ((row, col) != dispatched or interrupted):
            # INV: THE RECORD ADVANCES - this pick moves, or the
            # dispatch is a legitimate RESUME of interrupted work;
            # a completed action never re-fires (its cell_action
            # changed, so interrupted is False)
            entry_pos = entry_record.get("position")
            same_cell_as_entry = entry_pos == [row, col]
            nothing_advanced = (
                movements == entry_record.get("movements")
                and life == entry_record.get("life")
            )
            warn_contract(
                "inv", "walk.record_advances",
                not (
                    same_cell_as_entry
                    and nothing_advanced
                    and not interrupted
                    and not replay_reset
                ),
                "the walk record did not advance - a frozen walk "
                "(the same cell re-dispatched at the same movement "
                "with no interrupted work: the pin bug's signature)",
            )
            ws["dispatched_action"] = [action, budget]
            # THE ONE-ACTION-PER-VISIT RULE (the author's #4): the cell
            # needs exam work and was not yet dispatched THIS visit -
            # hand it to the runner; the phase-B radio then fires (the
            # author's #5), and the NEXT walk() steps away from here
            ws["dispatched"] = [row, col]
            save()
            return {
                "row": row,
                "col": col,
                "fam": fam,
                "rung": rung,
                "action": action,
                "budget": budget,
                "high": high,
                "best": list(best),
                "life": life,
                "movements": movements,
                "draws": draws_used,
                "reason": "evaluate",
            }
        # NO ACTION NEEDED (the marker honored: the dispatched
        # action completed): apply the cell's best settled score to
        # the high score and move on
        # INV: THE STEP-PAST GUARD (the author's catch, made
        # permanent): the walk is a deterministic function of (state,
        # seed) - a restart is a REPLAY of the same standing, and a
        # cell with live work underfoot is never walked past. If this
        # line executes with the dispatched action still pending (a
        # step-past: the movement-48 incident walked off an
        # interrupted dig and the walk never came back), the contract
        # fires - the marker may only be honored when the dispatch's
        # work is genuinely done (the action changed).
        warn_contract(
            "inv", "walk.no_step_past_live_work",
            not (
                (row, col) == dispatched
                and action in ("exam", "dig")
                and (
                    dispatched_action is None
                    or dispatched_action == [action, budget]
                )
            ),
            "stepping past a cell whose dispatched work is still "
            "pending - the completion must show as a CHANGED action "
            "(the escalation moved on, or the dig closed the cell), "
            "never assumed (the movement-48 incident)",
        )
        ws["dispatched"] = [-1, -1]
        ws["dispatched_action"] = None
        cell_score = _cell_best_score(st, fam, rung, kv_ladder, budget)
        if cell_score > high:
            high = cell_score
            best = (row, col)
        # THE MOVEMENT IS THE STEP AWAY (after the evaluation), not
        # the visit - the spawn cell costs no movement
        movements += 1
        total += 1
        if movements >= epoch_budget:
            # INV (the author's contract): the epoch ends at EXACTLY
            # the derived budget of movements (n_rows + n_cols - 1);
            # over-shooting means the boundary check was skipped
            warn_contract(
                "inv",
                "walk.exact_movements",
                movements == epoch_budget,
                f"the epoch ended at {movements} movements, expected exactly {epoch_budget}",
            )            # THE DEATH RULE (the author's corrected spec): the
            # walker dies when the teleport returns to the cell the
            # EPOCH STARTED FROM - the epoch found nothing better
            # than its own start. The epoch's start is the entry
            # record's best (the walk record's best at call entry =
            # where this epoch began); the strict-improvement update
            # makes the target chain monotone, so the accumulated
            # spawn-targets list of the old rule was redundant
            # machinery (a repeated target anywhere implies this
            # local condition fires at the same epoch or earlier).
            if best == epoch_start:
                # the teleport goes home to the epoch's start: the
                # life ENDS - a new walker spawns at random
                save()
                return {
                    "row": best[0], "col": best[1],
                    "fam": grid.cell(best[0], best[1])[0],
                    "rung": grid.cell(best[0], best[1])[1],
                    "action": "none",
                    "budget": 0,
                    "high": high,
                    "best": list(best),
                    "life": life,
                    "movements": movements,
                    "draws": draws_used,
                    "reason": "ended",
                }
            row, col = best
            position = (row, col)
            movements = 0
            epoch_start = (row, col)
            save()
            continue
        # DRAW A DIRECTION AND STEP (blocked: redraw)
        direction = draw()
        while True:
            nr, nc = row + direction[0], col + direction[1]
            if grid.inside(nr, nc):
                break
            direction = draw()
        row, col = nr, nc
        position = (row, col)
        save()
    return None


def _cell_pass_count(h: dict[str, Any]) -> int:
    """the count of PASS levels in one candidate's history (0 if
    none): the prospect's early-exit check - any pass means the
    candidate reached a score > -1."""
    n = 0
    while h.get(n, {}).get("status") == "pass":
        n += 1
    return n


def _cell_best_score(
    st: dict[str, Any],
    fam: str,
    rung: str,
    kv_ladder: list[str],
    budget: float,
) -> int:
    """the cell's best settled score: the highest level any candidate
    passes, reading the histories at whatever budget they were
    taken (the walker's high score tracks the best-known result)."""
    best = -1
    for k in kv_ladder:
        for v in kv_ladder:
            h = history_of(st, fam, rung, k, v)
            if not h:
                continue
            score = 0
            while True:
                rec = h.get(score)
                if rec is None:
                    break
                if rec.get("status") == "pass":
                    score += 1
                    continue
                break
            if score - 1 > best:
                best = score - 1
    return best
