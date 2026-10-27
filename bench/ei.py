"""bench.ei -- the expected-improvement steering for the ei.

The search space is the 2,048 (model, model-quant) pairs - the
ei's own pool (roster x LADDER, the stable index the state's
done-set already keys on). The kv cache quants are NOT searched: a
picked pair sweeps all 49 (k, v) combinations in one acquisition
(quantize once, measure everything, the pair is never needed again).
The pair's scalar outcome is the BEST score of its sweep.

The surrogate is PER-THRESHOLD MONOTONE LOGISTIC REGRESSION (the
author's ruling: monotone logistic only; the Bayesian ordinal model
waits until the data justifies it):

  P(score >= t | x) = sigmoid(w_t . phi(x))       one binary model
                                                  per threshold t

fit with L2-regularized Newton (IRLS) in pure numpy; monotonicity
enforced by isotonic projection per combo (P(>=t+1) <= P(>=t));
uncertainty by bootstrap resampling of the training pairs. No new
dependencies - numpy only.

The acquisition is PROBABILITY OF IMPROVEMENT by a full point:

  p(x) = P(score(x) >= y_best + 1)

Each model is treated EQUAL (the author's ruling: no cost weighting -
PoI-per-cost would over-rank the small models we already know are
weak); the expected acquisition cost is REPORTED next to the pick but
never enters the ranking.

The SEED phase is DETERMINISTIC, not random (the author's ruling):
for each lineage, the LARGEST model is probed first (the worst case
- if the biggest model runs at a quant level, every smaller model
in the lineage can too), at a FIXED quant grid, and the grid is
DERIVED from what works: the probe quant launches and measures; if
the launch fails, the next-coarser quant replaces it. The seed ends
when every lineage has SEED_PER_LINEAGE swept pairs at the largest
model - a balanced block design (lineage x quant grid).

The EXPLORATION RATE is ADAPTIVE (the author's ruling: values are
derived, not picked): epsilon = the trailing rate at which PoI
picks scored at or below the population median - when the
surrogate's picks stop outperforming, exploration rises; when PoI
is winning, it fades toward zero. No hand-picked constant.

Everything derives from state/ei-state.json - the single source of
truth, restart-safe, crash-railed. The import is the warm start:
every fully-swept pair becomes a training point.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bench.roster import LADDER, roster_from_models_md

# THE SEED GRID (the author's ruling): ONE global set of 3 quants.
# Every lineage's largest model is measured with THE SAME three
# quants - a balanced block design (lineage x quant). The grid starts
# pre-selected and SELF-REPAIRS: when a model fails a grid quant
# (quantize or launch failure), the replacement search tries
# candidates coarser-first until the failed model runs with one, and
# the winner replaces the slot GLOBALLY - every model is then
# measured with the same three quants again.
SEED_GRID_INITIAL = ["Q8_0", "Q5_K_M", "IQ3_XS"]
# the replacement candidates, coarser-first (bpw descending)
SEED_GRID_CANDIDATES = [
    "Q6_K", "Q4_K_M", "Q4_K_S", "Q3_K_M", "IQ4_NL", "Q3_K_S",
    "IQ3_M", "Q2_K", "IQ2_M", "Q2_K_S", "IQ2_S", "Q1_0", "IQ1_M",
]

# the thresholds: P(score >= t), t = 0..MAX_T. The top threshold is
# always one full point ABOVE the best observed (the PoI target) and
# two phantom levels ride above it (mass on "a better score exists").
# If a phantom is observed it simply joins the ladder.
PHANTOM_LEVELS = 2

# bootstrap draws for the uncertainty (the spread across refits is
# the uncertainty; deterministic given SEED)
BOOTSTRAP_N = 200
BOOT_SEED = 7

# L2 strength for the logistic fits (n is small, d ~ 71)
L2_LAMBDA = 1.0


# ---------------------------------------------------------- catalog


def catalog() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """models (64: id, family, params_b, f16_gib, window) and quants
    (32: id, bpw, method), deterministic order - the pool layout."""
    models = []
    for fam, _repo in roster_from_models_md():
        meta = _f16_gib_from_models_md(fam)
        params = _params_from_models_md(fam)
        models.append(
            {
                "id": fam,
                "family": _family_of(fam),
                "params_b": params,
                "f16_gib": meta,
                "window": _window_from_models_md(fam),
                "arch": _arch_of(fam),
            }
        )
    quants = []
    for rung in LADDER:
        quants.append(
            {
                "id": rung,
                "bpw": _bpw(rung),
                "method": _method_of(rung),
            }
        )
    return models, quants


def _md_row(fam: str) -> list[str] | None:
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "md", "models.md"
    )
    for ln in open(path, encoding="utf-8"):
        if ln.startswith(f"| {fam} |"):
            return [p.strip() for p in ln.strip().strip("|").split("|")]
    return None


def _f16_gib_from_models_md(fam: str) -> float | None:
    row = _md_row(fam)
    if row is None:
        return None
    try:
        return float(row[2])
    except (ValueError, IndexError):
        return None


def _params_from_models_md(fam: str) -> float:
    row = _md_row(fam)
    if row is None:
        return 0.0
    try:
        return float(row[1])
    except (ValueError, IndexError):
        return 0.0


def _window_from_models_md(fam: str) -> int | None:
    row = _md_row(fam)
    if row is None:
        return None
    try:
        return int(row[3].replace(",", ""))
    except (ValueError, IndexError):
        return None


def _arch_of(fam: str) -> str:
    """the architecture class: hybrid (jamba), rwkv, or attention -
    cuts ACROSS lineages (the feature the lineage one-hots cannot
    express)."""
    low = fam.lower()
    if "rwkv" in low:
        return "rwkv"
    if "jamba" in low:
        return "hybrid"
    return "attention"


def _family_of(fam: str) -> str:
    # the lineage prefix: qwen / granite / gemma / phi / minicpm /
    # smollm / llama / ai21 / rwkv / mistral / falcon / olmo / yi ...
    low = fam.lower()
    for pre in (
        "qwen", "granite", "gemma", "phi", "minicpm", "smollm", "llama",
        "ai21", "rwkv", "ministral", "mistral", "falcon", "olmo", "yi",
    ):
        if low.startswith(pre):
            return pre
    return low.split("-", 1)[0]


def _bpw(rung: str) -> float:
    # bits per weight per rung (the estimated file size axis)
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


def _method_of(rung: str) -> str:
    if rung == "F16":
        return "f16"
    if rung.startswith("IQ"):
        return "iq"
    if rung.startswith("TQ"):
        return "tq"
    if rung.endswith("_K") or "_K_" in rung:
        return "k"
    return "legacy"


# ---------------------------------------------------------- features


def feature_matrix() -> np.ndarray:
    """X of shape (2048, d): one-hot family, standardized log(params),
    standardized log(window), one-hot architecture, standardized bpw,
    one-hot quant method, log(params) x bpw. Row i is the pool index i
    (models.md order x LADDER order)."""
    models, quants = catalog()
    fams = sorted({m["family"] for m in models})
    archs = ["attention", "hybrid", "rwkv"]
    methods = ["f16", "k", "iq", "tq", "legacy"]
    log_p = np.log([m["params_b"] if m["params_b"] > 0 else 1e-3 for m in models])
    lp = (log_p - log_p.mean()) / (log_p.std() or 1.0)
    log_w = np.log([m["window"] if m["window"] else 8192 for m in models])
    lw = (log_w - log_w.mean()) / (log_w.std() or 1.0)
    bpws = np.array([q["bpw"] for q in quants])
    b = (bpws - bpws.mean()) / (bpws.std() or 1.0)
    rows = []
    for mi, m in enumerate(models):
        fam_oh = [1.0 if m["family"] == f else 0.0 for f in fams]
        arch_oh = [1.0 if m["arch"] == a else 0.0 for a in archs]
        for qi, q in enumerate(quants):
            m_oh = [1.0 if q["method"] == meth else 0.0 for meth in methods]
            rows.append(fam_oh + arch_oh + [lp[mi], lw[mi], b[qi], lp[mi] * b[qi]] + m_oh)
    X = np.array(rows, dtype=np.float64)
    return X


# ---------------------------------------------------------- store


def load_results(state_file: str) -> dict[int, int]:
    """pair index -> best score, from the ei state: every
    fully-swept pair (49 records) contributes its max; partial sweeps
    (crash leftovers) contribute their max too - a data point is a
    data point."""
    with open(state_file, encoding="utf-8") as fh:
        st = json.load(fh)
    best: dict[int, int] = {}
    pool_index = _pool_index()
    for r in st.get("results", []):
        if r.get("result") != "done":
            continue
        pi = pool_index.get((r["fam"], r["rung"]))
        if pi is None:
            continue
        s = r.get("high_score")
        if s is None:
            continue
        best[pi] = max(best.get(pi, -1), int(s))
    return best


def _pool_index() -> dict[tuple[str, str], int]:
    idx: dict[tuple[str, str], int] = {}
    i = 0
    for fam, _repo in roster_from_models_md():
        for rung in LADDER:
            idx[(fam, rung)] = i
            i += 1
    return idx


# ---------------------------------------------------------- surrogate


def _fit_logistic(Xtr: np.ndarray, y: np.ndarray, lam: float = L2_LAMBDA) -> np.ndarray:
    """L2-regularized logistic regression by Newton (IRLS). y in {0,1}."""
    n, d = Xtr.shape
    w = np.zeros(d)
    I = np.eye(d) * lam
    for _ in range(50):
        z = Xtr @ w
        p = 1.0 / (1.0 + np.exp(-z))
        grad = Xtr.T @ (y - p) - lam * w
        s = p * (1.0 - p) + 1e-9
        H = (Xtr * s[:, None]).T @ Xtr + I
        try:
            step = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            break
        w_new = w + step
        if np.abs(w_new - w).max() < 1e-8:
            w = w_new
            break
        w = w_new
    return w


def _isotonic_down(p: np.ndarray) -> np.ndarray:
    """enforce the threshold ladder's monotonicity per combo:
    P(>=t+1) <= P(>=t) for every t - the probabilities are
    non-increasing up the ladder. Applied from the LOW threshold
    upward: each threshold is clipped by the one below it (the
    projection direction that never destroys the low-t signal)."""
    out = p.copy()
    for t in range(len(p) - 1):
        if out[t + 1] > out[t]:
            out[t + 1] = out[t]
    return out


def level_probs(thresh_probs: np.ndarray) -> np.ndarray:
    """per-combo P(score = k) from the threshold ladder: P(=t) =
    P(>=t) - P(>=t+1), with P(>= T_top+1) = 0."""
    T = thresh_probs.shape[-1]
    ge = np.concatenate([thresh_probs, np.zeros(thresh_probs.shape[:-1] + (1,))], axis=-1)
    eq = ge[..., :-1] - ge[..., 1:]
    eq = np.clip(eq, 0.0, None)
    s = eq.sum(axis=-1, keepdims=True)
    s[s == 0] = 1.0
    return eq / s


def surrogate_predict(
    X: np.ndarray, Xtr: np.ndarray, ys: dict[int, int], tested: set[int]
) -> np.ndarray:
    """fit the threshold ladder on the tested pairs and predict the
    per-combo THRESHOLD probabilities for ALL pairs. Returns
    (2048, T) - bootstrap-averaged, monotone. ys: pair -> score."""
    y_best = max(ys.values()) if ys else -1
    # thresholds 0..(y_best + PHANTOM_LEVELS): P(>=t) models
    thresholds = list(range(0, y_best + 1 + PHANTOM_LEVELS))
    tested_idx = np.array(sorted(tested))
    ytr = np.array([ys[i] for i in tested_idx])
    rng = np.random.default_rng(BOOT_SEED)
    probs = np.zeros((X.shape[0], len(thresholds)))
    n_tr = len(tested_idx)
    for _ in range(BOOTSTRAP_N):
        take = rng.integers(0, n_tr, size=n_tr)
        bidx, by = tested_idx[take], ytr[take]
        for ti, t in enumerate(thresholds):
            yb = (by >= t).astype(np.float64)
            if yb.sum() == 0 or yb.sum() == n_tr:
                # no signal in this bootstrap draw: rate = the base rate
                probs[:, ti] += float(yb.sum()) / n_tr
                continue
            w = _fit_logistic(X[bidx], yb)
            probs[:, ti] += 1.0 / (1.0 + np.exp(-(X @ w)))
    probs /= BOOTSTRAP_N
    probs = np.clip(probs, 0.0, 1.0)
    probs = np.apply_along_axis(_isotonic_down, 1, probs)
    return probs


# ---------------------------------------------------------- acquisition


def load_seed_grid(state_file: str) -> list[str]:
    """the global 3-quant seed grid, from the state (persisted across
    restarts); the initial grid on first sight."""
    with open(state_file, encoding="utf-8") as fh:
        st = json.load(fh)
    grid = st.get("seed_grid")
    if grid and len(grid) == len(SEED_GRID_INITIAL):
        return list(grid)
    return list(SEED_GRID_INITIAL)


def save_seed_grid(state_file: str, grid: list[str]) -> None:
    with open(state_file, encoding="utf-8") as fh:
        st = json.load(fh)
    st["seed_grid"] = list(grid)
    with open(state_file, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=1)


def pair_state(state_file: str) -> dict[tuple[str, str], str]:
    """(fam, rung) -> 'done' | 'failed' | None, from the records: a
    pair is done when ANY of its kv combos ran, failed when its sweep
    ended without a single done record (quantize_failed,
    server_failed, ...)."""
    out: dict[tuple[str, str], str] = {}
    with open(state_file, encoding="utf-8") as fh:
        st = json.load(fh)
    for r in st.get("results", []):
        fam, rung = r.get("fam"), r.get("rung")
        if not fam or not rung:
            continue
        key = (fam, rung)
        if r.get("result") == "done":
            out[key] = "done"
        elif key not in out or out[key] is None:
            out[key] = "failed"
    return out


def seed_pair(state_file: str, n_pairs: int = 2048) -> dict[str, Any] | None:
    """THE DETERMINISTIC SEED: every lineage's LARGEST model,
    measured with THE SAME three global quants (seed_grid in the
    state). The seeding SUCCEEDS when every lineage's largest model
    has all grid quants measured (done) at the current grid.

    THE FAILURE DISTINCTION (the author's ruling): a kv failure is
    NOT a quant failure. As long as ANY of the 49 (k, v) combinations
    ran, the (model, model_quant) pair is SUCCESSFUL - per-combo
    failures (an architecture that cannot hold a quantized cache,
    one device-fit miss) are outcomes, not verdicts; only a sweep
    with ZERO done records means the quant is unusable for the model
    and the recovery fires. The replaced slot's data is never wasted:
    every swept pair's 49 records stay in the results - pre-computed
    for whatever needs them later (the risk of the repair is
    mitigated by the data it already collected).

    THE RECOVERY: when a grid quant is unusable for a model (zero
    done records in its sweep), the slot is not skipped but
    REPLACED: the next candidate quant (coarser-first, from
    SEED_GRID_CANDIDATES, not already in the grid) that the failed
    model CAN run replaces it GLOBALLY - the failed pair is re-picked
    with it, and every other model measures with the new grid too,
    keeping the same-three-quants invariant.

    Returns the next (largest-model, grid-quant) pair to sweep, or
    None when every lineage's block is complete at the current grid."""
    models, _quants = catalog()
    states = pair_state(state_file)
    grid = load_seed_grid(state_file)
    # the largest model per lineage
    by_fam: dict[str, list] = {}
    for m in models:
        by_fam.setdefault(m["family"], []).append(m)
    largest = {f: max(ms, key=lambda m: m["params_b"]) for f, ms in by_fam.items()}
    pool_index = _pool_index()
    # THE SEED ORDER: DESCENDING PARAMS across all lineages (the
    # author's ruling) - the biggest models first, the worst cases
    # first: an early grid repair invalidates almost nothing
    for m in sorted(largest.values(), key=lambda m: -m["params_b"]):
        for slot, q in enumerate(grid):
            pi = pool_index.get((m["id"], q))
            if pi is None:
                continue  # the model does not carry this rung (never for LADDER)
            state = states.get((m["id"], q))
            if state == "done":
                continue  # measured at this grid quant
            if state == "failed":
                # THE RECOVERY: replace the slot globally with a
                # candidate the failed model can run. Candidates are
                # tried in order; 'can run' is decided by the records:
                # the first candidate with NO failed record for this
                # model wins the slot (it will be picked next and its
                # sweep decides - a second failure moves the slot
                # again).
                replacement = None
                for cand in SEED_GRID_CANDIDATES:
                    if cand in grid:
                        continue
                    if states.get((m["id"], cand)) == "failed":
                        continue  # already known unusable for this model
                    replacement = cand
                    break
                if replacement is None:
                    # every candidate failed for this model - the
                    # model cannot run quantized at all; leave the
                    # slot, the lineage stays short (its largest
                    # model is simply unusable - the seed proceeds
                    # around it)
                    continue
                grid[slot] = replacement
                save_seed_grid(state_file, grid)
                pi2 = pool_index.get((m["id"], replacement))
                if pi2 is None or states.get((m["id"], replacement)) == "done":
                    continue  # already measured at the replacement
                return {
                    "index": pi2,
                    "fam": m["id"],
                    "rung": replacement,
                    "p": None,
                    "probs": None,
                    "phase": "seed-recovery",
                    "cost_gib": _f16_gib_from_models_md(m["id"]),
                }
            # state is None: not measured - pick it
            return {
                "index": pi,
                "fam": m["id"],
                "rung": q,
                "p": None,
                "probs": None,
                "phase": "seed",
                "cost_gib": _f16_gib_from_models_md(m["id"]),
            }
    return None  # every lineage's block is complete at the current grid


def adaptive_epsilon(state_file: str) -> float:
    """EPSILON, DERIVED NOT PICKED: the trailing rate at which PoI
    picks scored at or below the population median. Each PoI pick's
    outcome is compared with the median score of the pairs measured
    so far (the surrogate's own training data at pick time is
    approximated by the full tested set - conservative): the rate of
    PoI picks that did NOT beat the median is the exploration rate.
    No PoI history yet -> 0.0 (pure PoI). Clamped to [0, 0.5]."""
    with open(state_file, encoding="utf-8") as fh:
        st = json.load(fh)
    picks = st.get("picks", [])
    poi = [p for p in picks if p.get("phase", "").startswith("poi")]
    if not poi:
        return 0.0
    scores = [p.get("score") for p in poi if p.get("score") is not None]
    if not scores:
        return 0.0
    all_scores = [r.get("high_score") for r in st.get("results", [])
                  if r.get("result") == "done" and r.get("high_score") is not None]
    if not all_scores:
        return 0.5
    med = float(np.median(all_scores))
    below = sum(1 for s in scores if s <= med)
    return float(min(0.5, max(0.0, below / len(scores))))


def next_pair(
    state_file: str,
    seed_get: Any = None,
    n_pairs: int = 2048,
) -> dict[str, Any] | None:
    """THE PICK. Seed phase (every lineage short of its block): the
    deterministic largest-model grid. Above: PoI with the ADAPTIVE
    epsilon - with probability eps the pick is the max-predictive-
    entropy pair instead (eps derived from the trailing PoI failure
    rate, not picked). Returns {'index', 'fam', 'rung', 'p',
    'probs', 'phase', 'cost_gib'} or None when the pool is drained."""
    seed = seed_pair(state_file, n_pairs)
    if seed is not None:
        return seed
    best = load_results(state_file)
    tested = set(best)
    untested = [i for i in range(n_pairs) if i not in tested]
    if not untested:
        return None


    # the surrogate: fit on all tested, predict all
    X = feature_matrix()
    probs = surrogate_predict(X, X, best, tested)
    y_best = max(best.values())
    t_target = y_best + 1  # PoI: beat the incumbent by a full point
    if t_target >= probs.shape[1]:
        # the target rides a phantom level: take the top threshold
        t_target = probs.shape[1] - 1
    p = probs[:, t_target]
    cand = np.array(untested)
    pc = p[cand]

    def _entropy_pick() -> dict[str, Any]:
        # the max-predictive-entropy untested pair: the most
        # informative next measurement
        lvl = level_probs(probs[cand])
        ent = -(lvl * np.log(np.clip(lvl, 1e-15, None))).sum(axis=1)
        idx = int(cand[np.argmax(ent)])
        fam, rung = _pair_of(idx)
        levels = level_probs(probs[idx])
        return {
            "index": idx,
            "fam": fam,
            "rung": rung,
            "p": float(p[idx]),
            "probs": [float(x) for x in levels],
            "phase": "poi-entropy",
            "cost_gib": _f16_gib_from_models_md(fam),
        }

    if pc.max() < 1e-6:
        # THE DRAFT'S FALLBACK: every untested p(x) ~ 0 - the target
        # level has no training signal anywhere (the phantom band).
        # Entropy instead - the most informative next measurement.
        return _entropy_pick()

    # THE ADAPTIVE EPSILON (derived, never picked): the trailing rate
    # at which PoI picks failed to beat the population median. With
    # probability eps, inject an entropy pick - exploration rises
    # exactly as fast as the surrogate's picks stop outperforming.
    eps = adaptive_epsilon(state_file)
    if eps > 0.0 and np.random.default_rng(BOOT_SEED ^ len(best)).random() < eps:
        pick = _entropy_pick()
        pick["phase"] = "poi-explore"
        pick["epsilon"] = eps
        return pick

    # random tie-break among the top (deterministic given the data)
    top = cand[pc >= pc.max() - 1e-12]
    rng = np.random.default_rng(BOOT_SEED)
    idx = int(top[rng.integers(0, len(top))])
    fam, rung = _pair_of(idx)
    levels = level_probs(probs[idx])
    return {
        "index": idx,
        "fam": fam,
        "rung": rung,
        "p": float(p[idx]),
        "probs": [float(x) for x in levels],
        "phase": "poi",
        "epsilon": eps,
        "cost_gib": _f16_gib_from_models_md(fam),
    }


def _pair_of(idx: int) -> tuple[str, str]:
    models, _quants = catalog()
    m = models[idx // len(LADDER)]
    return m["id"], LADDER[idx % len(LADDER)]


def status(state_file: str, n_pairs: int = 2048) -> dict[str, Any]:
    """best pair, tested count, the P-better-remains estimate (log-
    space product over untested p(x) - independence approximation, a
    heuristic, not a guarantee), and the calibration report."""
    best = load_results(state_file)
    tested = set(best)
    out: dict[str, Any] = {
        "tested": len(tested),
        "best_score": max(best.values()) if best else None,
        "best_pairs": [
            _pair_of(i) for i, s in sorted(best.items(), key=lambda kv: -kv[1]) if s == max(best.values())
        ][:5],
    }
    if seed_pair(state_file, n_pairs) is not None:
        out["phase"] = "seed"
        out["p_better_remains"] = None
        return out
    X = feature_matrix()
    probs = surrogate_predict(X, X, best, tested)
    y_best = max(best.values())
    t = min(y_best + 1, probs.shape[1] - 1)
    p = probs[:, t]
    untested = [i for i in range(n_pairs) if i not in tested]
    if not untested:
        out["p_better_remains"] = 0.0
        return out
    # 1 - prod(1 - p) in log space
    log_no = float(np.sum(np.log1p(-np.clip(p[untested], 0.0, 1 - 1e-15))))
    out["p_better_remains"] = float(1.0 - np.exp(log_no))
    out["phase"] = "poi"
    out["calibration"] = _calibration(X, best, tested)
    return out


def _calibration(X: np.ndarray, ys: dict[int, int], tested: set[int]) -> dict[str, Any]:
    """k-fold CV reliability per threshold: predicted P(>=t) vs the
    observed rate, on held-out folds. Warns when overconfident
    (reliability slope < 0.9 - predictions claim more skill than they
    have)."""
    idx = np.array(sorted(tested))
    y = np.array([ys[i] for i in idx])
    y_best = max(ys.values())
    thresholds = list(range(0, y_best + 1))
    folds = 5
    n = len(idx)
    report: dict[str, Any] = {"folds": folds, "thresholds": {}}
    for t in thresholds:
        yb = (y >= t).astype(np.float64)
        if yb.sum() == 0 or yb.sum() == n:
            continue
        pred = np.zeros(n)
        for k in range(folds):
            v = np.arange(k, n, folds)
            tr = np.array([i for i in range(n) if i not in set(v)])
            w = _fit_logistic(X[idx[tr]], yb[tr])
            pred[v] = 1.0 / (1.0 + np.exp(-(X[idx[v]] @ w)))
        # reliability: bin the predictions, observed vs predicted
        bins = np.clip((pred * 5).astype(int), 0, 4)
        rel = []
        for b in range(5):
            m = bins == b
            if m.sum() < 2:
                continue
            rel.append((float(pred[m].mean()), float(yb[m].mean()), int(m.sum())))
        if len(rel) >= 2:
            px = np.array([r[0] for r in rel])
            py = np.array([r[1] for r in rel])
            slope = float(np.polyfit(px, py, 1)[0]) if px.std() > 0 else 1.0
            report["thresholds"][t] = {
                "bins": rel,
                "slope": slope,
                "overconfident": slope < 0.9,
            }
    return report


# ---------------------------------------------------------- self check


if __name__ == "__main__":
    state = os.environ.get("EI_STATE", "state/ei-state.json")
    t0 = time.time()
    models, quants = catalog()
    X = feature_matrix()
    assert X.shape[0] == len(models) * len(quants) == 2048, X.shape
    print(f"catalog: {len(models)} models x {len(quants)} quants, X {X.shape}, {time.time()-t0:.1f}s")
    st = status(state)
    print("status:", json.dumps({k: v for k, v in st.items() if k != "calibration"}, indent=1))
    if st.get("calibration", {}).get("thresholds"):
        for t, r in st["calibration"]["thresholds"].items():
            warn = " OVERCONFIDENT" if r["overconfident"] else ""
            print(f"  threshold {t}: slope {r['slope']:.2f}{warn}")
    nxt = next_pair(state)
    if nxt:
        print(
            f"next: [{nxt['phase']}] {nxt['fam']} {nxt['rung']} "
            f"(idx {nxt['index']}, p={nxt['p']}, cost ~{nxt['cost_gib']} GiB)"
        )
        if nxt["probs"]:
            print("  level probs:", [round(p, 3) for p in nxt["probs"]])
