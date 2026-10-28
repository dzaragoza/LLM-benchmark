"""bench.trek -- protocol trek: a deterministic random walker over
the (model, quant) grid, from the top-left corner.

THE GRID: 64 models (rows, params-ascending - the smallest at row
0) x 32 quants (columns, bpw-ascending - the smallest at column
0). Cell (r, c) = (models[r], LADDER-by-bpw[c]). One cell = one
(model, quant) pair = one pool index = one 49-combo kv sweep
(quantize once, measure everything - the amortization).

THE WALKER (the author's specification):

  - starts at (0, 0), the top-left corner: the smallest model at
    the smallest bit-width.
  - carries: a random seed (starts at 1), a high score (starts at
    -1), a direction (drawn from the seeded stream).
  - each iteration: EVALUATE the current cell (read the cache, or
    sweep if unmeasured), then:
      a) score > high score: update the high score, record this
         position as the best, step one cell in the current
         direction.
      b) score <= high score: draw a new direction, step one cell
         in it.
      c) blocked (the grid edge): keep drawing new directions
         until one is open (each draw consumes the stream), then
         step.
  - after 95 movements (plus evaluating the landing cell): TELEPORT
    to the best position, seed += 1, keep the high score, draw a
    new direction. 95 is the corner-to-corner distance - one epoch
    can cross the whole grid.
  - the walk ENDS when the walker teleports to the same location
    twice - the score rises monotonically, so the teleport target
    only changes on strict improvement; a repeated target means a
    full epoch found nothing better. A barren epoch converges.

DETERMINISM: everything is a pure function of (results cache, the
seed, the walk position). The walker's every draw, move and
evaluation is replayable from the walk log. No global randomness -
the only entropy is the seeded stream, advanced by every draw.

THE REPORTING: the tier crowns, the practitioner tables and the
suspicion post-condition (moved from the old bench/ei.py) survive
unchanged - they read records, not protocols.
"""

from __future__ import annotations

import json
import os
import random
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bench.roster import LADDER, roster_from_models_md

# ------------------------------------------------------------- constants

TREK_STATE_FILE = "state/trek-state.json"

# the epoch length: corner-to-corner (64 - 1) + (32 - 1) = 95
EPOCH_MOVEMENTS = 95

# the four directions: (row_step, col_step) - no diagonals
DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # up, down, left, right

# THE DYADIC TIME LADDER: the tier boundaries in seconds. A
# candidate's tier is the smallest cut its high-score level time
# fits. 256s is pre-declared but unreachable while the level clock
# is 128s.
TIME_LADDER_S = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0]

# THE DYADIC RAM LADDER: 1, 2, 4, 8, 16 GiB.
RAM_LADDER_GIB = [1.0, 2.0, 4.0, 8.0, 16.0]

# the device budget: the iGPU carve-out llama-server can use
DEVICE_LIMIT_GIB = 16.0

# ---------------------------------------------------------- the grid


def _models_sorted() -> list[str]:
    """the roster's models, params-ascending (the roster's own
    order is already smallest-first)."""
    return [fam for fam, _repo in roster_from_models_md()]


def _rungs_by_bpw() -> list[str]:
    """the LADDER's rungs, bpw-ascending (the walker's horizontal
    axis: the smallest bpw at column 0)."""
    return sorted(LADDER, key=_bpw)


def _bpw(rung: str) -> float:
    """bits per weight per rung."""
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


class Grid:
    """the 64 x 32 grid: (row, col) <-> (fam, rung) <-> pool index.
    The pool-index map is built ONCE per Grid - the walker consults
    it per step, and a rebuild per lookup was the replay's O(n^2)."""

    def __init__(self) -> None:
        self.models = _models_sorted()
        self.rungs = _rungs_by_bpw()
        self.n_rows = len(self.models)
        self.n_cols = len(self.rungs)
        # (fam, rung) -> pool index, built once
        self._pos: dict[tuple[str, str], int] = {}
        i = 0
        for f, _repo in roster_from_models_md():
            for r in LADDER:
                self._pos[(f, r)] = i
                i += 1
        # pool index -> (row, col), built once
        self._idx_to_cell: dict[int, tuple[int, int]] = {}
        for row in range(self.n_rows):
            for col in range(self.n_cols):
                self._idx_to_cell[self.pool_index(row, col)] = (row, col)

    def cell(self, row: int, col: int) -> tuple[str, str]:
        return (self.models[row], self.rungs[col])

    def inside(self, row: int, col: int) -> bool:
        return 0 <= row < self.n_rows and 0 <= col < self.n_cols

    def pool_index(self, row: int, col: int) -> int:
        return self._pos[self.cell(row, col)]

    def row_col_of(self, pool_index: int) -> tuple[int, int] | None:
        return self._idx_to_cell.get(pool_index)


_F16_GIB_CACHE: dict[str, float] = {}


def _f16_gib(fam: str) -> float:
    """the model's f16 size (GiB) from md/models.md - cached."""
    if fam in _F16_GIB_CACHE:
        return _F16_GIB_CACHE[fam]
    val = 0.0
    for ln in open("md/models.md", encoding="utf-8"):
        if ln.startswith(f"| {fam} |"):
            parts = [p.strip() for p in ln.strip().strip("|").split("|")]
            try:
                val = float(parts[2])
            except (ValueError, IndexError):
                val = 0.0
            break
    _F16_GIB_CACHE[fam] = val
    return val


def _est_size_gib_of(r: dict[str, Any]) -> float | None:
    """a record's weights size: the MEASURED size_gib where present,
    else the roster estimate (f16 x bpw/16)."""
    if r.get("size_gib") is not None:
        return r["size_gib"]
    f16 = _f16_gib(r.get("fam") or "")
    if not f16:
        return None
    return f16 * _bpw(r.get("rung") or "") / 16.0


# --------------------------------------------------- the results cache


def cache_scores(state_file: str = TREK_STATE_FILE) -> dict[tuple[int, int], int]:
    """(row, col) -> the cell's best kv-combo score, for every
    measured cell: a completed sweep contributes its best score;
    a sweep that ended with nothing runnable measures the cell at
    the floor (-1). Unmeasured cells are absent."""
    with open(state_file, encoding="utf-8") as fh:
        st = json.load(fh)
    grid = Grid()
    done_keys = {int(k) for k in st.get("done", []) if str(k).lstrip("-").isdigit()}
    best: dict[int, int] = {}
    for r in st.get("results", []):
        fam, rung = r.get("fam"), r.get("rung")
        if r.get("result") != "done" or (fam, rung) not in grid._pos:
            continue
        s = r.get("high_score")
        if s is None:
            continue
        idx = grid._pos[(fam, rung)]
        best[idx] = max(best.get(idx, -2), int(s))
    out: dict[tuple[int, int], int] = {}
    for idx, s in best.items():
        cell = grid.row_col_of(idx)
        if cell is not None:
            out[cell] = s
    for idx in done_keys:
        cell = grid.row_col_of(idx)
        if cell is not None and cell not in out:
            out[cell] = -1  # the sweep ended, nothing ran: the floor
    return out


# -------------------------------------------------------- the walker


# THE EXAM CLOCK: the walk's own patience ladder. The first trek
# runs at 1s per exam level; when it converges (the teleport rule),
# the clock doubles and the walk restarts from the best spot. The
# maximum clock is 128s - the protocol's patience ceiling.
CLOCK_MIN_S = 1.0
CLOCK_MAX_S = 128.0


def _clocks() -> list[float]:
    """the dyadic clock ladder: 1, 2, 4, ..., 128."""
    out = []
    c = CLOCK_MIN_S
    while c <= CLOCK_MAX_S:
        out.append(c)
        c *= 2
    return out


def walk(
    state_file: str = TREK_STATE_FILE,
    max_steps: int = 100_000,
) -> dict[str, Any] | None:
    """THE WALKER, TIME-DOUBLING (the author's specification):

    - the walk starts at (0, 0) with the exam clock at 1s per level.
    - the walker's rules are the same as before: strict improvement
      keeps the direction (and records the position as the best);
      non-improvement draws a new direction; blocked at an edge,
      keep drawing; after 95 movements, evaluate the landing cell
      then TELEPORT to the best position, seed += 1, keep the high
      score and best, new direction.
    - CONVERGENCE: teleporting to a location it has already
      teleported to AT THIS CLOCK. Then the CLOCK DOUBLES, the seed
      += 1, and the walk RESTARTS from that spot - the previous
      best is re-evaluated with double the time (its score may
      rise: a 1s timeout may pass at 2s).
    - the maximum clock is 128s: converging at 128s ends the trek
      for good.

    The cache is PER CLOCK: a cell measured at 1s does not count at
    2s - the whole grid re-opens when the clock doubles. The walk
    log (state['walk']) stamps every evaluation with its clock, and
    the cache rebuild replays the log: the protocol's memory is the
    log, the records keep score and time (no clock tag needed).

    Deterministic given the cache: replays from (0,0) through
    cached cells (free) and hands back the first cell needing
    evaluation at the CURRENT clock. Returns {..., 'reason':
    'evaluate', 'clock_s': ...} or None when the trek has ended."""
    grid = Grid()
    st = json.load(open(state_file, encoding="utf-8"))
    log: list[dict[str, Any]] = st.get("walk", [])

    # THE CACHE REBUILD: replay the walk log per clock. Each log
    # entry's (cell, clock) marks the cell measured at that clock;
    # the CURRENT clock is the highest clock with any entry, or 1s.
    measured: dict[float, set[tuple[int, int]]] = {}
    scores: dict[float, dict[tuple[int, int], int]] = {}
    for e in log:
        c = float(e.get("clock_s", 1.0))
        cell = (int(e["row"]), int(e["col"]))
        measured.setdefault(c, set()).add(cell)
        scores.setdefault(c, {})[cell] = int(e.get("score", -1))
    current_clock = max(measured.keys()) if measured else CLOCK_MIN_S
    # per-clock walk state: the convergence bookkeeping
    # (teleport targets per clock) replays from the log's epochs
    # NOTE: the full replay of directions/teleports per past clock
    # is not needed - only the CURRENT clock's cache and the walk
    # position matter; the position derives from the current
    # clock's replay (below).

    # replay the current clock's walk from its start: the walk at
    # clock c starts at the BEST POSITION of clock c/2 (or (0,0)
    # for the first clock). The log's entries at the current clock,
    # in order, replay the draws deterministically.
    rng = random.Random(_clocks().index(current_clock) + 1)  # seed = 1 at 1s, 2 at 2s...
    # the starting position: the first entry of this clock's log
    # (the restart spot), or (0,0) if none yet
    this_clock_entries = [e for e in log if float(e.get("clock_s", 1.0)) == current_clock]
    if this_clock_entries:
        start = (int(this_clock_entries[0]["row"]), int(this_clock_entries[0]["col"]))
    else:
        start = (0, 0)

    cur_scores = scores.get(current_clock, {})
    row, col = start
    high = -1
    best = start
    moves = 0
    teleport_targets: list[tuple[int, int]] = []
    # the best/high replay: the high score at this clock starts from
    # the clock's own evaluations (the log), the best from the same
    for e in this_clock_entries:
        s = int(e.get("score", -1))
        if s > high:
            high = s
            best = (int(e["row"]), int(e["col"]))

    def draw() -> tuple[int, int]:
        return DIRECTIONS[rng.randrange(4)]

    def result(reason: str = "evaluate") -> dict[str, Any]:
        fam, rung = grid.cell(row, col)
        return {
            "row": row,
            "col": col,
            "fam": fam,
            "rung": rung,
            "pool_index": grid.pool_index(row, col),
            "clock_s": current_clock,
            "high_score": high,
            "best": list(best),
            "epoch": len(teleport_targets) + 1,
            "seed": _clocks().index(current_clock) + 1 + len(teleport_targets),
            "movements": moves,
            "reason": reason,
        }

    direction = draw()
    while moves < max_steps:
        if (row, col) not in cur_scores:
            return result()
        score = cur_scores[(row, col)]
        if score > high:
            high = score
            best = (row, col)
        else:
            direction = draw()
        moves += 1
        if moves >= EPOCH_MOVEMENTS:
            if best in teleport_targets:
                # CONVERGED at this clock: the clock doubles (or the
                # trek ends at the max clock)
                if current_clock >= CLOCK_MAX_S:
                    return None
                next_clock = current_clock * 2
                # the next trek restarts from the best spot, at the
                # doubled clock - the runner sweeps it fresh (the
                # cache has no entries at that clock yet)
                return {
                    "row": best[0],
                    "col": best[1],
                    "fam": grid.cell(best[0], best[1])[0],
                    "rung": grid.cell(best[0], best[1])[1],
                    "pool_index": grid.pool_index(best[0], best[1]),
                    "clock_s": next_clock,
                    "high_score": -1,
                    "best": list(best),
                    "epoch": 1,
                    "seed": _clocks().index(next_clock) + 1,
                    "movements": 0,
                    "reason": "evaluate",
                }
            teleport_targets.append(best)
            row, col = best
            rng = random.Random(_clocks().index(current_clock) + 1 + len(teleport_targets))
            direction = draw()
            moves = 0
            continue
        while True:
            nr, nc = row + direction[0], col + direction[1]
            if grid.inside(nr, nc):
                break
            direction = draw()
        row, col = nr, nc
    return None


# ------------------------------------------------------ the reporting


def tier_of(t_s: float | None) -> str | None:
    """the candidate's tier: the smallest dyadic cut its high-score
    level time fits. None: no level passed - no tier."""
    if t_s is None:
        return None
    for cut in TIME_LADDER_S:
        if t_s <= cut:
            return f"t{int(cut)}"
    return f"t{int(TIME_LADDER_S[-1])}"


def tier_incumbents(state_file: str = TREK_STATE_FILE) -> dict[str, dict[str, Any]]:
    """THE TIME-TIER CROWNS: the best score at each dyadic patience
    cut, with the holder's details."""
    with open(state_file, encoding="utf-8") as fh:
        st = json.load(fh)
    inc: dict[str, dict[str, Any]] = {}
    for r in st.get("results", []):
        if r.get("result") != "done":
            continue
        t = tier_of(r.get("high_score_time_s"))
        if t is None:
            continue
        s = int(r.get("high_score") or -1)
        if s < 0:
            continue
        cur = inc.get(t)
        if cur is None or s > cur["score"] or (
            s == cur["score"] and (r.get("high_score_time_s") or 1e9) < cur["time_s"]
        ):
            inc[t] = {
                "score": s,
                "time_s": float(r.get("high_score_time_s") or 1e9),
                "fam": r.get("fam"),
                "rung": r.get("rung"),
                "k_quant": r.get("k_quant"),
                "v_quant": r.get("v_quant"),
            }
    return inc


def suspicion_check(inc: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """THE POST-CONDITION (warning only, at completion): the tier
    bests should be non-decreasing up the ladder."""
    order = [f"t{int(c)}" for c in TIME_LADDER_S]
    have = [t for t in order if t in inc]
    violations = []
    for a, b in zip(have, have[1:]):
        if inc[a]["score"] > inc[b]["score"]:
            violations.append(
                f"{a} champion outscores the {b} champion - possible "
                "exam-instance luck, decide manually"
            )
    return {"violations": violations, "ok": not violations}


def weakest_tier(inc: dict[str, dict[str, Any]]) -> str | None:
    """the tier furthest behind the global best (ties: the faster
    tier) - the reporting target."""
    if not inc:
        return None
    gbest = max(v["score"] for v in inc.values())
    order = [f"t{int(c)}" for c in TIME_LADDER_S]
    gaps = {t: gbest - inc[t]["score"] for t in inc}
    return max(order, key=lambda t: (gaps.get(t, -1), -order.index(t)))
