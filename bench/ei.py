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

from bench.contracts import contract_health, warn_contract
from bench.roster import LADDER, roster_from_models_md
from infra.hf_download import DEVICE_LIMIT_GIB

# THE SEED BANDS (the author's ruling): ONE global set of 3 FILE-SIZE
# BANDS, derived from the device budget - DEVICE/8, DEVICE/4,
# DEVICE/2 - no hand-picked numbers. Every lineage's largest model is
# measured at THE SAME THREE BANDS: the rung closest to each band
# (and feasible: est size <= DEVICE_LIMIT) fills the slot for that
# model - equal MEMORY COST for every model, the exam's RAM and time
# constraints held constant, so scores compare capability at matched
# device budgets (the author's fairness: same quants is NOT fair -
# the big models settle on the tiny quants that ruin the small
# models; same file size is).
SEED_BANDS_GIB = [DEVICE_LIMIT_GIB / 8, DEVICE_LIMIT_GIB / 4, DEVICE_LIMIT_GIB / 2]


def _est_size_gib(f16_gib: float | None, rung: str) -> float | None:
    """the estimated rung file size: f16 x bpw/16."""
    if f16_gib is None:
        return None
    return f16_gib * _bpw(rung) / 16.0


def band_rungs(f16_gib: float | None, exclude: set[str] = set()) -> list[str | None]:
    """THE BAND RESOLUTION (the author's ruling): for each band, the
    rung whose estimated size is CLOSEST to the band - the actual
    closest value, no tolerance percentage, repeats allowed across
    bands (a tiny model's closest pick for all three bands may be
    its own F16; the dedupe happens at pick time - a repeated rung
    is measured once). Feasible = est size <= DEVICE_LIMIT. Excluded
    rungs (the recovery's failed list) are skipped; None for a band
    no feasible rung can fill."""
    from bench.roster import LADDER

    # PRE: the bands are derived from the device budget, positive, sorted
    warn_contract(
        "pre", "band_rungs.bands",
        len(SEED_BANDS_GIB) == 3 and SEED_BANDS_GIB == sorted(SEED_BANDS_GIB)
        and all(b > 0 for b in SEED_BANDS_GIB),
        f"the bands are not 3 positive sorted values: {SEED_BANDS_GIB}",
    )
    out: list[str | None] = []
    for band in SEED_BANDS_GIB:
        cands = [
            (abs(size - band), r)
            for r in LADDER
            if r not in exclude
            and (size := _est_size_gib(f16_gib, r)) is not None
            and size <= DEVICE_LIMIT_GIB
        ]
        if not cands:
            out.append(None)
            continue
        cands.sort()
        out.append(cands[0][1])
    # POST: every resolved rung is feasible (est size <= the device budget)
    for band, q in zip(SEED_BANDS_GIB, out):
        if q is not None:
            size = _est_size_gib(f16_gib, q)
            warn_contract(
                "post", "band_rungs.feasible",
                size is not None and size <= DEVICE_LIMIT_GIB,
                f"{q} resolved for band {band:g} but est size {size} exceeds {DEVICE_LIMIT_GIB}",
            )
    return out


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
        # PRE on the RAW record: the score is an int >= -1. The
        # max() below CLAMPS anything below -1, masking corruption -
        # the negative test caught exactly this - so the contract
        # guards the input, not the output
        warn_contract(
            "pre", "load_results.record_score",
            isinstance(s, (int, float)) and int(s) >= -1,
            f"corrupt record: {r.get('fam')} {r.get('rung')} high_score={s}",
        )
        best[pi] = max(best.get(pi, -1), int(s))
    # POST: every pair score is an int >= -1, in pool-index space
    warn_contract(
        "post", "load_results.space",
        all(0 <= pi < 2048 for pi in best),
        f"pair index outside the pool: {min(best) if best else '-'}..{max(best) if best else '-'}",
    )
    warn_contract(
        "post", "load_results.range",
        all(s >= -1 for s in best.values()),
        f"score below -1 in the results: {min(best.values()) if best else '-'}",
    )
    return best


def _pool_index() -> dict[tuple[str, str], int]:
    idx: dict[tuple[str, str], int] = {}
    i = 0
    for fam, _repo in roster_from_models_md():
        for rung in LADDER:
            idx[(fam, rung)] = i
            i += 1
    return idx




# ------------------------------------------------- the three time tiers


def tier_of(t_s: float | None) -> str | None:
    """the candidate's tier by its own high-score level time: fast
    <= 32s, medium <= 64s, slow <= 128s (the exam's level clock).
    None: no level passed (score -1) - no tier (nothing was achieved
    to be fast at), or the time datum is absent."""
    warn_contract(
        "pre", "tier_of.positive",
        t_s is None or t_s > 0,
        f"non-positive level time: {t_s}",
    )
    if t_s is None:
        return None
    if t_s <= 32.0:
        return "fast"
    if t_s <= 64.0:
        return "medium"
    if t_s <= 128.0:
        return "slow"
    return "slow"  # over the clock never happens (the deadline caps at 128s)


def tier_incumbents(state_file: str) -> dict[str, dict[str, Any]]:
    """THE THREE INCUMBENTS (the author's ruling: the high score in
    each time tier, fast/medium/slow): the best score achieved by a
    candidate of that tier, per tier, with the holder's details. The
    same model may hold several tiers (quants change both speed and
    capability) or three different models may hold them."""
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
        if cur is None or s > cur["score"] or (s == cur["score"] and (r.get("high_score_time_s") or 1e9) < cur["time_s"]):
            inc[t] = {
                "score": s,
                "time_s": float(r.get("high_score_time_s") or 1e9),
                "fam": r.get("fam"),
                "rung": r.get("rung"),
                "k_quant": r.get("k_quant"),
                "v_quant": r.get("v_quant"),
            }
    # POST: every crown is a real achievement (score >= 0, time in its own tier)
    for t, v in inc.items():
        warn_contract("post", "tier_incumbents.score", v["score"] >= 0,
                      f"{t} crown has score {v['score']}")
        warn_contract("post", "tier_incumbents.time",
                      tier_of(v["time_s"]) == t,
                      f"{t} crown time {v['time_s']:.1f}s is not in its own tier")
    return inc


def weakest_tier(inc: dict[str, dict[str, Any]]) -> str | None:
    """THE ACQUISITION PRIORITY (the author's ruling: weakest first -
    results fast): the tier furthest behind the global best is the
    most valuable to improve. Ties broken toward the FASTER tier
    (a fast discovery is worth more at equal gap)."""
    if not inc:
        return None
    gbest = max(v["score"] for v in inc.values())
    order = ["fast", "medium", "slow"]
    # the gap BEHIND the global best; the weakest tier has the
    # LARGEST gap (ties: the faster tier wins - a fast discovery is
    # worth more at equal gap)
    gaps = {t: gbest - inc[t]["score"] for t in inc}
    return max(order, key=lambda t: (gaps.get(t, -1), -order.index(t)))


def suspicion_check(inc: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """THE POST-CONDITION (the author's ruling, warning only): when
    the experiment is FINISHED, the tier bests should be
    non-decreasing in tier time - the slow champion outscoring the
    medium, the medium the fast (deep scores need time; a total
    champion faster than the next score would smell of exam-instance
    luck). NOT an invariant DURING execution: a transient tier
    inversion mid-run is expected (a crown may simply not have a
    serious contender yet); the suspicion only arises at completion.
    A violation is reported, we decide what to do - never blocks."""
    order = ["fast", "medium", "slow"]
    have = [t for t in order if t in inc]
    violations = []
    for a, b in zip(have, have[1:]):
        if inc[a]["score"] > inc[b]["score"]:
            violations.append(
                f"{a} champion ({inc[a]['fam']} {inc[a]['rung']}, "
                f"score {inc[a]['score']} at {inc[a]['time_s']:.0f}s) outscores the "
                f"{b} champion (score {inc[b]['score']}) - possible "
                "exam-instance luck, decide manually"
            )
    return {"violations": violations, "ok": not violations}

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
    out = eq / s
    # POST: the level probabilities sum to 1 per combo
    warn_contract(
        "post", "level_probs.normalized",
        bool(np.allclose(out.sum(axis=-1), 1.0)),
        f"level probabilities do not sum to 1: min {out.sum(axis=-1).min():.6f} max {out.sum(axis=-1).max():.6f}",
    )
    return out


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
    """THE DETERMINISTIC SEED: every lineage's LARGEST model, measured
    at THE SAME THREE FILE-SIZE BANDS (2 / 4 / 8 GiB - the device
    budget /8, /4, /2, no hand-picked numbers). Each model's bands
    resolve to the rung closest to the band it can carry: equal
    MEMORY COST for every model, the exam's RAM/time constraints
    held constant (the author's fairness ruling). The seeding
    SUCCEEDS when every lineage's largest model has all three bands
    measured (done).

    THE FAILURE DISTINCTION (the author's ruling): a kv failure is
    NOT a quant failure. As long as ANY of the 49 (k, v) combinations
    ran, the pair is SUCCESSFUL; only a zero-done sweep means the
    rung is unusable for the model and the recovery fires. The
    replaced slot's data is never wasted - every swept pair's 49
    records stay in the results, pre-computed for later.

    THE RECOVERY: when a band's rung fails for a model (zero done
    records), the slot RE-RESOLVES for that model - the failed rungs
    are excluded, and the next-closest feasible rung to the band
    fills the slot. The bands themselves are FIXED for everyone (the
    fairness invariant is the memory cost, not the rung); the
    per-model resolution adapts. The failed pair is re-armed and
    re-swept at the replacement; a second failure moves the slot
    again; all-rungs-failed leaves the lineage short (its largest
    model is unusable quantized - the seed proceeds around it).

    Returns the next (largest-model, band-rung) pair to sweep, or
    None when every lineage's block is complete."""
    models, _quants = catalog()
    states = pair_state(state_file)
    # the largest model per lineage
    by_fam: dict[str, list] = {}
    for m in models:
        by_fam.setdefault(m["family"], []).append(m)
    largest = {f: max(ms, key=lambda m: m["params_b"]) for f, ms in by_fam.items()}
    pool_index = _pool_index()
    # THE SEED ORDER: DESCENDING PARAMS across all lineages - the
    # biggest models first, the worst cases first: an early repair
    # invalidates almost nothing
    for m in sorted(largest.values(), key=lambda m: -m["params_b"]):
        # this model's failed rungs (the recovery's exclusion list)
        failed_rungs = {
            rung for (fam, rung), s in states.items()
            if fam == m["id"] and s == "failed"
        }
        # THE CLOSEST-VALUE RESOLUTION, repeats allowed: the same
        # rung may serve several bands - a repeated rung is
        # measured ONCE (the dedupe), so a tiny model whose closest
        # pick for every band is its own F16 seeds with one sweep
        clean = band_rungs(m["f16_gib"])
        rungs = band_rungs(m["f16_gib"], exclude=failed_rungs)
        seen: set[str] = set()
        for band, q_clean, q in zip(SEED_BANDS_GIB, clean, rungs):
            if q is None or q in seen:
                continue  # repeated rung: measured once, this band rides along
            state = states.get((m["id"], q))
            if state == "done":
                seen.add(q)  # measured - and it covers its bands
                continue
            pi = pool_index.get((m["id"], q))
            if pi is None:
                continue
            if state == "failed":
                continue  # excluded rung, the resolution already moved past it
            phase = "seed" if q == q_clean else "seed-recovery"
            seen.add(q)
            return {
                "index": pi,
                "fam": m["id"],
                "rung": q,
                "band_gib": band,
                "p": None,
                "probs": None,
                "phase": phase,
                "cost_gib": _f16_gib_from_models_md(m["id"]),
            }
    return None  # every lineage's block is complete


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


    # THE TIER TARGET (the author's ruling: weakest tier first -
    # results fast): the PoI target level is the weakest tier's
    # incumbent + 1 (a full-point improvement where it is worth the
    # most). The surrogate stays score-only; the tier names the goal.
    inc = tier_incumbents(state_file)
    wt = weakest_tier(inc)
    y_best = max(best.values())
    if wt is not None:
        y_target_inc = inc[wt]["score"]
    else:
        y_target_inc = y_best
    X = feature_matrix()
    probs = surrogate_predict(X, X, best, tested)
    t_target = y_target_inc + 1  # PoI: beat the weakest tier's incumbent by a full point
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
            "target_tier": wt,
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
        "target_tier": wt,
        "target_score": y_target_inc,
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
        # THE THREE TIERS (the author's ruling): the incumbent per
        # time tier, the weakest tier, and the suspicion invariant -
        # warning only, we decide what to do if it fires
        "tiers": tier_incumbents(state_file),
        "weakest_tier": None,
        "suspicion": None,  # the post-condition's live status; FINAL only when the pool is drained
    }
    inc = out["tiers"]
    if inc:
        out["weakest_tier"] = weakest_tier(inc)
        out["suspicion"] = suspicion_check(inc)
        out["suspicion"]["final"] = len(tested) >= n_pairs
    out["contract_violations"] = contract_health()
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
