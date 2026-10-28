"""bench.trek -- protocol trek: a deterministic walk over the
(model, quant) grid, from the smallest corner, steered by measured
neighbors.

THE PROTOCOL (one sentence for the report): start at the smallest
parameter model at the smallest feasible bit-width; always measure
the frontier's best-estimated unmeasured cell (the mean of its
measured neighbors); ties break by a declared, logged strategy;
the walk re-derives from the cache at every checkpoint (every N=16
pairs), where the strategy may be re-ruled from the walk's own
diagnostics; each pair's 49 (k, v) cache combos are swept in one
acquisition (quantize once, measure everything).

THE GRID: 64 models x 32 quants = 2,048 cells. The axes are the
roster's models (params-ascending) and the quant LADDER. Each cell
is one pool index; the kv sweep amortizes the quantization.

THE WALK'S DETERMINISM: the next pick is a pure function of
(measured results, the strategy list). The strategy is logged at
every checkpoint (and at the start), so any stretch of the walk
replays exactly. No randomness anywhere: the tie-break ladder is
a total order ending at the pool index.

THE FRONTIER: an unmeasured cell is ON THE FRONTIER when it is
grid-adjacent (same model, adjacent rung; same rung, adjacent
model in the roster's params order) to at least one measured cell.
The walk can never teleport; it expands the measured region's
boundary. A cell's ESTIMATE is the mean of its measured neighbors'
scores; its SUPPORT is how many neighbors back that estimate.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bench.roster import LADDER, roster_from_models_md

# THE DYADIC TIME LADDER: the tier boundaries in seconds. A
# candidate's tier is the smallest cut its high-score level time
# fits. 256s is pre-declared but unreachable while the level clock
# is 128s - it activates only if the clock is ever extended.
TIME_LADDER_S = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0]

# THE DYADIC RAM LADDER: 1, 2, 4, 8, 16 GiB - the patience ladder's
# mirror for memory. A candidate's ram tier is the smallest cut its
# measured vulkan0 memory fits.
RAM_LADDER_GIB = [1.0, 2.0, 4.0, 8.0, 16.0]

# the device budget: the iGPU carve-out llama-server can use
DEVICE_LIMIT_GIB = 16.0

# ------------------------------------------------------------- state

TREK_STATE_FILE = "state/trek-state.json"

# the checkpoint cadence: every N measured pairs, the walk
# re-derives from the cache and the strategy is reviewed
CHECKPOINT_N = 16

# ------------------------------------------------------- the grid


def the_grid() -> list[dict[str, Any]]:
    """the 2,048 cells, roster order: models params-ascending (the
    roster's own order) x the LADDER. Index i = the pool index."""
    models = roster_from_models_md()
    grid: list[dict[str, Any]] = []
    for m_pos, (fam, _repo) in enumerate(models):
        for rung_pos, rung in enumerate(LADDER):
            grid.append(
                {
                    "index": m_pos * len(LADDER) + rung_pos,
                    "fam": fam,
                    "rung": rung,
                    "m_pos": m_pos,      # the model's roster position (params-ascending)
                    "rung_pos": rung_pos,  # the rung's LADDER position
                }
            )
    return grid


def _model_params(fam: str) -> float:
    """params (B) from md/models.md - the walk's size axis."""
    for ln in open("md/models.md", encoding="utf-8"):
        if ln.startswith(f"| {fam} |"):
            parts = [p.strip() for p in ln.strip().strip("|").split("|")]
            try:
                return float(parts[1])
            except (ValueError, IndexError):
                return 0.0
    return 0.0


def _model_window(fam: str) -> int:
    """training window from md/models.md - the tie-break's window axis."""
    for ln in open("md/models.md", encoding="utf-8"):
        if ln.startswith(f"| {fam} |"):
            parts = [p.strip() for p in ln.strip().strip("|").split("|")]
            try:
                return int(parts[3].replace(",", ""))
            except (ValueError, IndexError):
                return 0
    return 0


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
    """THE POST-CONDITION (warning only, evaluated at completion):
    the tier bests should be non-decreasing up the ladder. A
    transient inversion mid-run is expected; the verdict only
    attaches when the walk has measured everything reachable."""
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
    """a record's weights size: the MEASURED size_gib where present
    (the post-quantization truth), else the roster estimate
    (f16 x bpw/16) - for the ledger's ram-budget table."""
    if r.get("size_gib") is not None:
        return r["size_gib"]
    f16 = _f16_gib(r.get("fam") or "")
    if not f16:
        return None
    return f16 * _bpw(r.get("rung") or "") / 16.0


def _bpw(rung: str) -> float:
    """bits per weight per rung - the walk's quant axis."""
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


# -------------------------------------------------- measured results


def measured(state_file: str = TREK_STATE_FILE) -> dict[int, dict[str, Any]]:
    """cell index -> {'score': int, 'n_kv': int}: every measured pair
    (a completed sweep - the driver's done-mark) contributes its best
    kv-combo score. Failed pairs (the sweep ended, nothing ran)
    measure the cell too: their score is -1 (the landscape's floor -
    a dead cell the walk must see as bad, not as unmeasured)."""
    with open(state_file, encoding="utf-8") as fh:
        st = json.load(fh)
    # the pool layout: (fam, rung) -> index
    models = roster_from_models_md()
    pos = {}
    i = 0
    for fam, _repo in models:
        for rung in LADDER:
            pos[(fam, rung)] = i
            i += 1
    done_keys = {int(k) for k in st.get("done", []) if str(k).lstrip("-").isdigit()}
    best: dict[int, int] = {}
    for r in st.get("results", []):
        fam, rung = r.get("fam"), r.get("rung")
        if not fam or not rung or (fam, rung) not in pos:
            continue
        idx = pos[(fam, rung)]
        if r.get("result") == "done":
            s = r.get("high_score")
            if s is None:
                continue
            best[idx] = max(best.get(idx, -2), int(s))
    out: dict[int, dict[str, Any]] = {}
    for idx, s in best.items():
        out[idx] = {"score": s}
    # pairs whose sweep ENDED but scored nothing: measured at the floor
    for idx in done_keys:
        if idx not in out:
            out[idx] = {"score": -1}
    return out


# -------------------------------------------------- the frontier


def frontier(
    grid: list[dict[str, Any]],
    meas: dict[int, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """every unmeasured cell grid-adjacent to a measured one, with
    its ESTIMATE (mean of measured neighbors' scores) and SUPPORT
    (how many neighbors back it). The walk's boundary."""
    n_rungs = len(LADDER)
    out: dict[int, dict[str, Any]] = {}
    for cell in grid:
        idx = cell["index"]
        if idx in meas:
            continue
        # grid neighbors: same model, rung +-1; same rung, model +-1
        neighbors = []
        m, r = cell["m_pos"], cell["rung_pos"]
        if r > 0:
            neighbors.append(m * n_rungs + r - 1)
        if r < n_rungs - 1:
            neighbors.append(m * n_rungs + r + 1)
        if m > 0:
            neighbors.append((m - 1) * n_rungs + r)
        if m < len(grid) // n_rungs - 1:
            neighbors.append((m + 1) * n_rungs + r)
        measured_nbrs = [meas[n]["score"] for n in neighbors if n in meas]
        if not measured_nbrs:
            continue  # not on the boundary - unreachable this step
        out[idx] = {
            "estimate": sum(measured_nbrs) / len(measured_nbrs),
            "support": len(measured_nbrs),
        }
    return out


# ------------------------------------------------- the strategy


# the tie-break conditions, BY NAME - the strategy is a declared,
# logged object. Each condition: (key-name, direction) - the walk
# prefers higher (+) or lower (-) values of the feature.
STRATEGY_V1 = [
    ("score", "+"),      # the frontier estimate - walk toward what looks good
    ("support", "+"),    # better-backed estimates win ties (fill confident regions first)
    ("model-step", "+"), # prefer cells that open a NEW MODEL ROW (the params axis is
                         # the landscape's dominant gradient; this is the desert-
                         # crossing rule - a flat/bad row never traps the walk)
    ("params", "-"),     # smaller model on ties (the corner-ward bias; cheap sweeps)
    ("bpw", "-"),        # smaller bit-width on ties (deeper quantization; cheaper files)
    ("window", "+"),     # larger training window on ties (correlates with exam skill)
    ("novelty", "+"),    # fewer measured lineages adjacent on ties (spread the walk)
    ("index", "+"),      # the pool index - the total-order last resort
]


def _lineage(fam: str) -> str:
    low = fam.lower()
    for pre in (
        "qwen", "granite", "gemma", "phi", "minicpm", "smollm", "llama",
        "ai21", "rwkv", "ministral", "mistral", "falcon", "olmo", "yi",
    ):
        if low.startswith(pre):
            return pre
    return low.split("-", 1)[0]


def pick(
    state_file: str = TREK_STATE_FILE,
    strategy: list[tuple[str, str]] = STRATEGY_V1,
) -> dict[str, Any] | None:
    """THE NEXT STEP: the frontier's best cell under the strategy.
    The pick is a pure function of (measured results, strategy) -
    fully deterministic, replayable from the log.

    Returns {'index', 'fam', 'rung', 'estimate', 'support',
    'strategy'} or None when the grid is fully measured."""
    grid = the_grid()
    meas = measured(state_file)
    if not meas:
        # THE BLIND START: the smallest params model at the smallest
        # feasible bpw - the grid's corner, fixed by the roster order
        corner = min(
            grid,
            key=lambda c: (_model_params(c["fam"]), _bpw(c["rung"])),
        )
        return {
            "index": corner["index"],
            "fam": corner["fam"],
            "rung": corner["rung"],
            "estimate": None,
            "support": 0,
            "strategy": [list(s) for s in strategy],
        }
    fr = frontier(grid, meas)
    if not fr:
        return None  # the walk has measured everything reachable

    n_rungs = len(LADDER)
    n_models = len(grid) // n_rungs
    cell_by_idx = {c["index"]: c for c in grid}
    # the measured lineages, for the novelty tie-break
    meas_lineages = {_lineage(cell_by_idx[i]["fam"]) for i in meas}

    def feature(cell: dict[str, Any], fr_info: dict[str, Any], name: str) -> float:
        if name == "score":
            return fr_info["estimate"]
        if name == "support":
            return float(fr_info["support"])
        if name == "model-step":
            # 1 when a MEASURED neighbor on the params axis (the cell
            # extends the walk into a new model row); 0 when only
            # rung-axis neighbors are measured (same-row filling)
            m, r = cell["m_pos"], cell["rung_pos"]
            up = (m + 1) * n_rungs + r if m < n_models - 1 else None
            down = (m - 1) * n_rungs + r if m > 0 else None
            if (up is not None and up in meas) or (down is not None and down in meas):
                return 1.0
            return 0.0
        if name == "params":
            return _model_params(cell["fam"])
        if name == "bpw":
            return _bpw(cell["rung"])
        if name == "window":
            return float(_model_window(cell["fam"]))
        if name == "novelty":
            # the count of DISTINCT measured lineages adjacent to
            # this cell - fewer = more novel territory
            m, r = cell["m_pos"], cell["rung_pos"]
            nbrs = []
            if m > 0:
                nbrs.append((m - 1) * n_rungs + r)
            if m < n_models - 1:
                nbrs.append((m + 1) * n_rungs + r)
            if r > 0:
                nbrs.append(m * n_rungs + r - 1)
            if r < n_rungs - 1:
                nbrs.append(m * n_rungs + r + 1)
            lin = {_lineage(cell_by_idx[n]["fam"]) for n in nbrs if n in meas}
            return -float(len(lin))  # fewer adjacent measured lineages = higher novelty
        if name == "index":
            return float(cell["index"])
        return 0.0

    best_key = None
    best_cell = None
    for idx, info in fr.items():
        cell = cell_by_idx[idx]
        key = []
        for name, direction in strategy:
            v = feature(cell, info, name)
            key.append(v if direction == "+" else -v)
        if best_key is None or key > best_key:
            best_key = key
            best_cell = (idx, cell, info)
    idx, cell, info = best_cell
    return {
        "index": idx,
        "fam": cell["fam"],
        "rung": cell["rung"],
        "estimate": info["estimate"],
        "support": info["support"],
        "strategy": [list(s) for s in strategy],
    }


# ------------------------------------------------------ the checkpoint


def checkpoint_report(state_file: str = TREK_STATE_FILE) -> dict[str, Any]:
    """the diagnostics the checkpoint reviews: crown progression,
    estimate bias (realized vs estimated at measurement time), and
    lineage coverage - the evidence for re-ruling the strategy."""
    import json as _json

    with open(state_file, encoding="utf-8") as fh:
        st = _json.load(fh)
    picks = st.get("walk", [])
    out: dict[str, Any] = {"n_measured": len(picks)}
    # crown progression: the best score per dyadic tier, live
    from bench.trek import measured as _meas

    meas = _meas(state_file)
    out["n_cells_measured"] = len(meas)
    out["best_score"] = max((m["score"] for m in meas.values()), default=None)
    # estimate bias: the picks' estimates vs realized scores
    ests, reals = [], []
    for p in picks:
        if p.get("estimate") is not None and p.get("score") is not None:
            ests.append(p["estimate"])
            reals.append(p["score"])
    if ests:
        out["estimate_bias"] = round(
            sum(r - e for e, r in zip(ests, reals)) / len(ests), 2
        )
    # lineage coverage
    grid = the_grid()
    cell_by_idx = {c["index"]: c for c in grid}
    lin_counts: dict[str, int] = {}
    for idx in meas:
        lin = _lineage(cell_by_idx[idx]["fam"])
        lin_counts[lin] = lin_counts.get(lin, 0) + 1
    out["lineage_coverage"] = dict(
        sorted(lin_counts.items(), key=lambda kv: -kv[1])
    )
    return out
