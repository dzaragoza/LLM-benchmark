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
from bench.roster import LADDER, roster_from_models_md

# ------------------------------------------------------------- constants

TREK_STATE_FILE = "state/trek-state.json"

# the epoch length: corner-to-corner (64 - 1) + (32 - 1) = 95
EPOCH_MOVEMENTS = 95

# the four directions: (row_step, col_step) - no diagonals
DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

# the budget ladder: 1, 2, 4, ..., 128
CLOCK_LADDER = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0]

# THE CANDIDATE-DETERMINISTIC EXAM SEED: the same candidate always
# gets the same exam instance (the same levels, the same papers) -
# the histories are reproducible and shared across walkers/seeds
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


def _models_sorted() -> list[str]:
    return [fam for fam, _repo in roster_from_models_md()]


def _bpw(rung: str) -> float:
    BPW = {
        "F16": 16.0, "Q8_0": 8.5, "Q6_K": 6.56, "Q5_K_M": 5.69, "Q5_K_S": 5.54,
        "Q5_1": 5.63, "Q5_0": 5.54, "Q4_K_M": 4.85, "Q4_K_S": 4.58, "Q4_1": 5.0,
        "Q4_0": 4.55, "IQ4_NL": 4.5, "IQ4_XS": 4.25, "Q3_K_L": 3.91, "Q3_K_M": 3.91,
        "Q3_K_S": 3.5, "IQ3_M": 3.66, "IQ3_S": 3.44, "IQ3_XS": 3.3, "IQ3_XXS": 3.06,
        "Q2_K": 3.35, "Q2_K_S": 3.0, "IQ2_M": 2.7, "IQ2_S": 2.5, "IQ2_XS": 2.31,
        "IQ2_XXS": 2.06, "Q2_0": 3.35, "Q1_0": 1.68, "IQ1_M": 1.75, "IQ1_S": 1.56,
        "TQ1_0": 1.5, "TQ2_0": 2.0,
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
            "post", "grid.dimensions",
            self.n_rows == 64 and self.n_cols == 32,
            f"the grid is {self.n_rows}x{self.n_cols}, expected 64x32",
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


def load_state(state_file: str = TREK_STATE_FILE) -> dict[str, Any]:
    """the v2 state: {'candidates': {candidate_key: history}, ...}.
    The candidate key: 'fam|rung|k|v'. The history: {level: record}."""
    if not os.path.isfile(state_file):
        return {"candidates": {}}
    with open(state_file, encoding="utf-8") as fh:
        return json.load(fh)


def save_state(st: dict[str, Any], state_file: str = TREK_STATE_FILE) -> None:
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


def walk(
    st: dict[str, Any],
    walker_seed: int,
    budget_s: float | None = None,
    kv_ladder: list[str] | None = None,
    max_steps: int = 1_000_000,
) -> dict[str, Any] | None:
    """THE WALKER at a budget. Deterministic: (the exam histories,
    the walker seed, the budget) -> the next cell needing work.

    The walker state derives from the histories every call: the
    measured set (any candidate history exists = the cell is on the
    map), the scores under the budget, the needs-work flags. The
    walk re-derives from its epoch start each call (the v1 lesson:
    cached steps cost movements; the replay is exact).

    The walk's bookkeeping is MOVEMENTS ONLY: 95 per epoch, every
    step costs one, the epoch ends with a teleport to the best cell,
    a repeated teleport target doubles the budget (handled by the
    caller iterating the ladder) or ends at 128s.

    Returns {'row','col','fam','rung','budget_s','high','best',
    'epoch','movements','score','needs_work','reason'} where reason
    is 'evaluate' (the cell needs exam work under this budget) or
    'converged' (the walk finished: every reachable cell is settled
    under this budget)."""
    grid = Grid()
    if kv_ladder is None:
        kv_ladder = ["f16", "q8_0", "q5_1", "q5_0", "q4_1", "q4_0", "iq4_nl"]

    # the current budget: given, or derived from the state's last
    # walk record
    if budget_s is None:
        budget_s = st.get("last_budget", CLOCK_LADDER[0])

    # THE WALK'S START: (-1,-1) for a fresh walk - the first pick
    # draws both coordinates; otherwise the recorded walk position
    rng = random.Random(f"trek-walker-{walker_seed}-{CLOCK_LADDER.index(budget_s)}")

    # the cells' states under this budget
    cell_score: dict[tuple[int, int], int] = {}
    cell_work: dict[tuple[int, int], bool] = {}
    measured: set[tuple[int, int]] = set()
    for row in range(grid.n_rows):
        for col in range(grid.n_cols):
            fam, rung = grid.cell(row, col)
            s, work = pair_state_under(st, fam, rung, kv_ladder, budget_s)
            if s > -2:
                measured.add((row, col))
                cell_score[(row, col)] = s
                cell_work[(row, col)] = work

    # the walk bookkeeping: replay from the state's walk record
    walk_rec = st.setdefault("walks", {}).setdefault(f"{budget_s:g}", {})
    epoch = walk_rec.get("epoch", 1)
    position = tuple(walk_rec.get("position", [-1, -1]))
    moves = walk_rec.get("movements", 0)
    high = walk_rec.get("high", -1)
    best = tuple(walk_rec.get("best", position))
    targets = [tuple(t) for t in walk_rec.get("targets", [])]

    if position == (-1, -1):
        # THE FRESH START (the v2 ruling): ONLY the first walker (the
        # 1s budget) may start at (-1,-1) - it draws both coordinates
        # and starts at that random cell. Any other budget starting
        # at (-1,-1) is a contract violation (the walker state was
        # not carried across the budget doubling).
        warn_contract(
            "pre",
            "walk.start_budget",
            budget_s == CLOCK_LADDER[0],
            f"only the {CLOCK_LADDER[0]:g}s walker may start at (-1,-1); "
            f"the {budget_s:g}s walker must inherit a grid position",
        )
        position = (rng.randrange(grid.n_rows), rng.randrange(grid.n_cols))
        best = position

    def save() -> None:
        walk_rec["epoch"] = epoch
        walk_rec["position"] = list(position)
        walk_rec["movements"] = moves
        walk_rec["high"] = high
        walk_rec["best"] = list(best)
        walk_rec["targets"] = [list(t) for t in targets]

    def draw() -> tuple[int, int]:
        return DIRECTIONS[rng.randrange(4)]

    # POST: the position is inside the grid - and a non-first budget
    # NEVER sees (-1,-1) (its walk state carries over from the
    # previous budget's convergence)
    warn_contract(
        "post", "walk.start_inside",
        grid.inside(position[0], position[1]),
        f"the walk position {position} is outside the grid",
    )
    warn_contract(
        "inv",
        "walk.no_offgrid_restart",
        not (budget_s != CLOCK_LADDER[0] and tuple(position) == (-1, -1)),
        f"the {budget_s:g}s walker restarted at (-1,-1) - only the "
        f"{CLOCK_LADDER[0]:g}s walker may draw its start",
    )

    direction = draw()
    total = 0
    row, col = position
    while total < max_steps:
        if (row, col) not in measured:
            # an unmeasured cell: the walk's frontier under this budget
            fam, rung = grid.cell(row, col)
            save()
            return {
                "row": row, "col": col, "fam": fam, "rung": rung,
                "budget_s": budget_s, "high": high, "best": list(best),
                "epoch": epoch, "movements": moves,
                "score": -2, "needs_work": True, "reason": "evaluate",
            }
        score = cell_score[(row, col)]
        if cell_work[(row, col)]:
            # measured but needing re-runs under this budget
            fam, rung = grid.cell(row, col)
            save()
            return {
                "row": row, "col": col, "fam": fam, "rung": rung,
                "budget_s": budget_s, "high": high, "best": list(best),
                "epoch": epoch, "movements": moves,
                "score": score, "needs_work": True, "reason": "evaluate",
            }
        # a settled cell: the walk's rule applies
        if score > high:
            high = score
            best = (row, col)
        else:
            direction = draw()
        moves += 1
        total += 1
        if moves >= EPOCH_MOVEMENTS:
            # the epoch ends: teleport to the best
            if best in targets:
                # CONVERGED at this budget
                save()
                # THE BUDGET CARRY-OVER: the next budget's walker
                # restarts at this walk's best position - the walk
                # state carries across the doubling, never (-1,-1)
                # (the start_budget contract enforces exactly this)
                next_idx = CLOCK_LADDER.index(budget_s) + 1
                if next_idx < len(CLOCK_LADDER):
                    nb = CLOCK_LADDER[next_idx]
                    st.setdefault("walks", {})[f"{nb:g}"] = {
                        "epoch": 1,
                        "position": list(best),
                        "movements": 0,
                        "high": -1,
                        "best": list(best),
                        "targets": [],
                    }
                return {
                    "row": best[0], "col": best[1],
                    "fam": grid.cell(best[0], best[1])[0],
                    "rung": grid.cell(best[0], best[1])[1],
                    "budget_s": budget_s, "high": high, "best": list(best),
                    "epoch": epoch, "movements": moves,
                    "score": cell_score.get(best, -1), "needs_work": False,
                    "reason": "converged",
                }
            targets.append(best)
            row, col = best
            moves = 0
            continue
        # STEP (blocked: redraw until open)
        while True:
            nr, nc = row + direction[0], col + direction[1]
            if grid.inside(nr, nc):
                break
            direction = draw()
        row, col = nr, nc
    return None
