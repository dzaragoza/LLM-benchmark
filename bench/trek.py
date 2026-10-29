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
    max_steps: int = 1_000_000,
) -> dict[str, Any] | None:
    """THE WALKER, TIME-DOUBLING (the author's specification), with
    EVERY MOVEMENT COSTING THE SAME - cached or measured (the
    author's ruling): an epoch's 95 movements count every step the
    walker takes, so the walk is a pure function of the log - the
    replay re-derives the ENTIRE current epoch from its start, and
    a restart anywhere leaves the walk identical.

    THE REPLAY'S EXACTNESS rests on one property: a cached cell can
    never improve the high score - its score was already absorbed
    when the cell was swept (high is monotone), so re-crossing it
    applies the same non-improvement rule and consumes the same
    draw. The path from an epoch's start is therefore identical
    given the measured set, regardless of when the runner swept
    which cell or restarted the process.

    THE LOG is the protocol's memory: every swept cell at this
    clock (its score), the epoch numbers, and each epoch's start
    position (best_before of its first entry - the teleport
    target). No restore fields are needed; draws/direction in the
    entries are informational.

    Returns the first unmeasured cell at the current clock (the
    runner sweeps it), or the doubled-clock restart cell on
    convergence, or None when the trek ends (converged at 128s)."""
    grid = Grid()
    if not os.path.isfile(state_file):
        os.makedirs(os.path.dirname(state_file) or ".", exist_ok=True)
        st: dict[str, Any] = {"done": [], "results": [], "walk": []}
        with open(state_file, "w", encoding="utf-8") as fh:
            json.dump(st, fh, indent=1)
    else:
        with open(state_file, encoding="utf-8") as fh:
            st = json.load(fh)
    log: list[dict[str, Any]] = st.get("walk", [])

    # THE FRESH START: no log - the trek begins at (0,0) at the 1s clock
    if not log:
        fam, rung = grid.cell(0, 0)
        return {
            "row": 0,
            "col": 0,
            "fam": fam,
            "rung": rung,
            "pool_index": grid.pool_index(0, 0),
            "clock_s": CLOCK_MIN_S,
            "high_score": -1,
            "best": [0, 0],
            "epoch": 1,
            "seed": 1,
            "movements": 0,
            "draws": 0,
            "direction": [1, 0],
            "reason": "evaluate",
        }

    # THE CURRENT CLOCK and its entries (chronological)
    current_clock = max(float(e.get("clock_s", 1.0)) for e in log)
    entries = [e for e in log if float(e.get("clock_s", 1.0)) == current_clock]
    clock_idx = _clocks().index(current_clock)  # 0-based; seed = clock_idx + epoch

    # THE MEASURED SET at this clock: (row, col) -> score
    measured: dict[tuple[int, int], int] = {}
    for e in entries:
        measured[(int(e["row"]), int(e["col"]))] = int(e.get("score", -1))

    # THE HIGH/BEST: replay the entries chronologically - a swept
    # cell's score applies the strict-improvement rule exactly as
    # the original walk did (cached cells never improve high, so
    # the entries are the complete record)
    high = -1
    best = (0, 0)
    for e in entries:
        s = int(e.get("score", -1))
        if s > high:
            high = s
            best = (int(e["row"]), int(e["col"]))

    # THE EPOCH STARTS: epoch 1 starts at the clock's restart spot
    # (entries[0].best_before); epoch k > 1 starts where epoch k-1
    # teleported TO (also its first entry's best_before)
    epoch_starts: dict[int, tuple[int, int]] = {}
    for e in entries:
        ep = int(e.get("epoch", 1))
        if ep not in epoch_starts:
            t = e.get("best_before")
            epoch_starts[ep] = (int(t[0]), int(t[1])) if t else (0, 0)
    max_epoch = max(epoch_starts)

    # THE TELEPORT TARGETS: epoch k's start (k >= 2) IS the target
    # of the k-1 -> k teleport. A repeated target = converged.
    targets = [epoch_starts[k] for k in sorted(epoch_starts) if k >= 2]
    if len(set(targets)) < len(targets):
        # converged already (a repeated teleport target in the log)
        return _advance_clock(grid, state_file, current_clock, best, measured, log)

    # THE CLOCK REPLAY: walk the current epoch from its start - and
    # through subsequent epochs if the replay crosses boundaries -
    # until an unmeasured cell (return it) or convergence (advance
    # the clock) or the trek's end (None)
    epoch = max_epoch
    total = 0
    while total < max_steps:
        start = epoch_starts.get(epoch, best)
        rng = random.Random(clock_idx + 1 + epoch)
        row, col = start
        moves = 0
        draws = 0

        def draw(rng: random.Random = rng) -> tuple[int, int]:
            nonlocal draws
            draws += 1
            return DIRECTIONS[rng.randrange(4)]

        direction = draw()
        while moves < EPOCH_MOVEMENTS:
            if (row, col) not in measured:
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
                    "epoch": epoch,
                    "seed": clock_idx + 1 + epoch,
                    "movements": moves,
                    "draws": draws,
                    "direction": list(direction),
                    "reason": "evaluate",
                }
            score = measured[(row, col)]
            # THE RULE: strict improvement keeps the direction and
            # records the position; non-improvement draws a new one.
            # A cached cell never improves high (proven), so the
            # replay's draws match the original's exactly.
            if score > high:
                high = score
                best = (row, col)
            else:
                direction = draw()
            moves += 1
            total += 1
            if moves >= EPOCH_MOVEMENTS:
                # THE EPOCH ENDS: teleport to the best position
                if best in targets:
                    # converged at this clock
                    return _advance_clock(grid, state_file, current_clock, best, measured, log)
                targets.append(best)
                epoch += 1
                epoch_starts[epoch] = best
                break  # the next epoch starts at the target
            # STEP (blocked at an edge: keep drawing until open)
            while True:
                nr, nc = row + direction[0], col + direction[1]
                if grid.inside(nr, nc):
                    break
                direction = draw()
            row, col = nr, nc
    return None


def _advance_clock(
    grid: Grid,
    state_file: str,
    current_clock: float,
    best: tuple[int, int],
    measured: dict[tuple[int, int], int],
    log: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """CONVERGENCE: the clock doubles and the walk restarts from the
    best spot (re-evaluated at the doubled time); at the max clock
    the trek ENDS."""
    if current_clock >= CLOCK_MAX_S:
        return None
    next_clock = current_clock * 2
    fam, rung = grid.cell(best[0], best[1])
    return {
        "row": best[0],
        "col": best[1],
        "fam": fam,
        "rung": rung,
        "pool_index": grid.pool_index(best[0], best[1]),
        "clock_s": next_clock,
        "high_score": -1,
        "best": list(best),
        "epoch": 1,
        "seed": _clocks().index(next_clock) + 1,
        "movements": 0,
        "draws": 0,
        "direction": [1, 0],
        "reason": "evaluate",
    }


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
        if (
            cur is None
            or s > cur["score"]
            or (s == cur["score"] and (r.get("high_score_time_s") or 1e9) < cur["time_s"])
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
    for a, b in zip(have, have[1:], strict=False):
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
