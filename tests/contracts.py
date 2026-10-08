"""CrossHair contracts (session 40, addendum 22) - formal verification of
the study's pure functions.

Run:  crosshair check tests/contracts.py

The contracts live here, not in the source modules: the source keeps
its measurement docstrings, and this module is the verification layer.
Each *_ref function mirrors a study function and states what MUST hold
for ALL inputs; crosshair proves it or returns a counterexample.
"""

from __future__ import annotations

import math

from bench.certify import wilson_interval
from infra.hf_download import find_rung_file, has_safetensors

# ---- wilson_interval: the accept/dead math of every certify run ----


def wilson_ref(k: int, n: int, z: float) -> tuple[float, float]:
    """The Wilson score interval bounds.

    pre: 0 <= k <= n
    pre: 0.0 <= z <= 10.0
    post: 0.0 <= __return__[0]
    post: __return__[0] <= __return__[1]
    post: __return__[1] <= 1.0
    """
    return wilson_interval(k, n, z)


def wilson_domain_ref(k: int, n: int, z: float) -> bool:
    """Outside the domain (0 <= k <= n, z >= 0) there is no interval.

    post: (0 <= k <= n and z >= 0) or (__return__)
    """
    return wilson_interval(k, n, z) == (0.0, 0.0)


def wilson_degenerate_ref(k: int, n: int) -> bool:
    """At z=0 the interval must collapse onto the point estimate.

    pre: 0 <= k <= n
    pre: n > 0
    post: __return__
    """
    lo, hi = wilson_interval(k, n, 0.0)
    return math.isclose(lo, k / n, abs_tol=1e-12) and math.isclose(hi, k / n, abs_tol=1e-12)


# ---- find_rung_file: the acquire path's repo-file matcher ----


def find_rung_file_ref(names: list[str], rung: str) -> str | None:
    """A returned file is one of the names and carries the rung token.

    post: (__return__ is None) or (__return__ in names)
    post: (__return__ is None) or (rung.lower() in __return__.lower())
    """
    return find_rung_file(names, rung)


def find_rung_file_none_ref(names: list[str], rung: str) -> bool:
    """No GGUF names means no match at all.

    post: any(f.lower().endswith('.gguf') for f in names) or __return__
    """
    return find_rung_file(names, rung) is None


def has_safetensors_ref(names: list[str]) -> bool:
    """True implies some name ends in .safetensors.

    post: (not __return__) or any(n.lower().endswith('.safetensors') for n in names)
    """
    return has_safetensors(names)


# ---- estimate_rung_gib: the memory shortcut (addendum 35) ----


def estimate_ref(rung: str, files: list[str], sizes: dict[str, int]) -> object:
    """An estimate, when produced, is positive; unknown rungs and
    empty sources estimate nothing (never a false skip).

    post: (__return__ is None) or (__return__ > 0.0)
    """
    from infra.hf_download import estimate_rung_gib

    return estimate_rung_gib(rung, files, files, sizes)


def estimate_none_ref(rung: str, files: list[str], sizes: dict[str, int]) -> bool:
    """No sizes at all means no estimate (the caller does not skip)."""
    from infra.hf_download import estimate_rung_gib

    return estimate_rung_gib(rung, files, files, sizes) is None


# ---- kv_gib: the KV cache arithmetic (the ceiling predictor's term) ----


def kv_gib_ref(layers: int, kv_heads: int, head_dim: int, depth: int, bpe: float) -> float:
    """KV cost is non-negative and linear in depth (double the depth,
    double the cache).

    pre: layers >= 0 and kv_heads >= 0 and head_dim >= 0 and depth >= 0 and bpe >= 0
    post: __return__ >= 0.0
    """
    from law_fit import kv_gib

    return kv_gib(layers, kv_heads, head_dim, depth, bpe)


def kv_gib_linear_ref(layers: int, kv_heads: int, head_dim: int, bpe: float) -> bool:
    """Linearity in depth: kv(d) + kv(d) == kv(2d) exactly (integer-ish
    arithmetic, no rounding drift at small scales).

    pre: layers >= 0 and kv_heads >= 0 and head_dim >= 0 and bpe >= 0
    post: __return__
    """
    from law_fit import kv_gib

    d = 4096
    return math.isclose(
        kv_gib(layers, kv_heads, head_dim, d, bpe) * 2,
        kv_gib(layers, kv_heads, head_dim, 2 * d, bpe),
        rel_tol=1e-12,
    )


# ---- law_worst: the fitted law evaluated at a size ----


def law_worst_ref(size: float, a: float, b: float) -> float:
    """A positive fit (a>0, b>0) predicts a positive worst-speed,
    decreasing in size (bandwidth: bigger file, slower worst turn).

    pre: 0.0 < a < 1e6 and 0.0 < b < 1e6 and 0.0 <= size < 1e6
    post: __return__ > 0.0
    """
    from law_fit import law_worst

    return law_worst(size, a, b)


# ---- the cell loaders: stored state -> cell maps ----


def speed_cells_ref(fst: dict[str, dict[str, int]], depth: int) -> dict:
    """The loader returns exactly the stored runs as int keys (the
    state's str keys never leak out).

    post: set(__return__) == set((fst.get('certify_speed') or {}).get(str(depth)) or {})
    """
    from bench.state_store import speed_cells

    return speed_cells(fst, depth)


def vt_cells_ref(fst: dict[str, dict[str, int]], depth: int) -> dict:
    """The VT loader mirrors the speed loader's contract.

    post: set(__return__) == set((fst.get('certify_vt') or {}).get(str(depth)) or {})
    """
    from bench.state_store import vt_cells

    return vt_cells(fst, depth)


# ================================================== session 43: the v7 layer
# The fixed-budget benchmark's pure functions: the weight/KV
# arithmetic, the ladder ordering, and the VT pass predicate.


def weights_gib_positive_ref(params_b: float, wi: int) -> bool:
    """A weight estimate is positive for any positive parameter count
    at any ladder rung (the planner's feasibility filter rests on it).
    pre: params_b > 0.0
    pre: 0 <= wi < 7
    post: __return__
    """
    from bench.v7 import W_LADDER, weights_gib

    return weights_gib(params_b, W_LADDER[wi]) > 0.0


def weights_gib_linear_ref(a: float, wi: int) -> bool:
    """Weights scale LINEARLY in parameters: doubling the model doubles
    the weight cost at any quant (the per-axis budget accounting).
    pre: a > 0.0
    pre: 0 <= wi < 7
    post: __return__
    """
    from bench.v7 import W_LADDER, weights_gib

    return math.isclose(
        weights_gib(2 * a, W_LADDER[wi]), 2 * weights_gib(a, W_LADDER[wi]), rel_tol=1e-12
    )


def kv_quant_factor_order_ref() -> bool:
    """The KV ladder is ordered by factor: a later rung never costs
    LESS per token - the climb's closest-without-exceeding rule needs
    monotone rungs or it can oscillate."""
    from bench.v7 import KV_QUANT_FACTOR, KV_QUANT_LADDER

    return all(
        KV_QUANT_FACTOR[KV_QUANT_LADDER[i]] < KV_QUANT_FACTOR[KV_QUANT_LADDER[i + 1]]
        for i in range(len(KV_QUANT_LADDER) - 1)
    )


def w_quant_bpb_order_ref() -> bool:
    """The weight ladder is ordered by bits-per-byte (same reason)."""
    from bench.v7 import W_LADDER, W_QUANT_BPB

    return all(
        W_QUANT_BPB[W_LADDER[i]] < W_QUANT_BPB[W_LADDER[i + 1]] for i in range(len(W_LADDER) - 1)
    )


def alloc_total_positive_ref(
    per_token: float, params_b: float, ctx: int, wi: int, ki: int, vi: int
) -> bool:
    """An allocation total is positive: weights + KV, both
    non-negative terms, so the estimate never lands at or below zero
    for a placeable family (the greedy floor (2,2,2) is feasible).
    pre: per_token >= 0.0 and params_b > 0.0 and ctx > 0
    pre: 0 <= wi < 7 and 0 <= ki < 4 and 0 <= vi < 4
    post: __return__
    """
    import bench.v7 as v7m

    kv = (
        (per_token / 2.0)
        * (
            v7m.KV_QUANT_FACTOR[v7m.KV_QUANT_LADDER[ki]]
            + v7m.KV_QUANT_FACTOR[v7m.KV_QUANT_LADDER[vi]]
        )
        * ctx
    )
    return v7m.weights_gib(params_b, v7m.W_LADDER[wi]) + kv / (1 << 30) > 0.0


def alloc_kv_monotone_in_ctx_ref(per_token: float, ctx1: int, ctx2: int, ki: int, vi: int) -> bool:
    """The KV term is monotone in ctx: a deeper context never costs
    LESS cache - the reach-vs-smarts tradeoff the argmax balances.
    pre: per_token >= 0.0 and 0 < ctx1 <= ctx2
    pre: 0 <= ki < 4 and 0 <= vi < 4
    post: __return__
    """
    import bench.v7 as v7m

    f = v7m.KV_QUANT_FACTOR[v7m.KV_QUANT_LADDER[ki]] + v7m.KV_QUANT_FACTOR[v7m.KV_QUANT_LADDER[vi]]
    return (per_token / 2.0) * f * ctx1 <= (per_token / 2.0) * f * ctx2


def alloc_kv_monotone_in_rung_ref(per_token: float, ctx: int, ki: int) -> bool:
    """The KV term is monotone in the cache ladder: a higher rung
    never costs LESS at the same depth.
    pre: per_token >= 0.0 and ctx > 0
    pre: 0 <= ki < 3
    post: __return__
    """
    import bench.v7 as v7m

    f_lo = v7m.KV_QUANT_FACTOR[v7m.KV_QUANT_LADDER[ki]]
    f_hi = v7m.KV_QUANT_FACTOR[v7m.KV_QUANT_LADDER[ki + 1]]
    return (per_token / 2.0) * f_lo * ctx <= (per_token / 2.0) * f_hi * ctx


def grade_reachable_monotone_in_window_ref(span: int, hops: int, w1: int, w2: int) -> bool:
    """Monotonicity: widening the window never un-reaches a grade.

    pre: span > 0 and hops >= 0 and w1 > 0 and w2 >= w1
    post: __return__
    """
    import bench.v7 as v7m

    return not (v7m.grade_reachable(span, hops, w1) and not v7m.grade_reachable(span, hops, w2))


def grade_reachable_boundary_tight_ref(span: int, hops: int) -> bool:
    """Boundary tightness (session 44, addendum 112): the minimal
    window the rule accepts is exactly span + overhead + gen - one
    token less is unreachable, one more is reachable. The old buggy
    rule (span <= window) failed exactly here.

    pre: span > 0 and hops >= 0
    post: __return__
    """
    import bench.v7 as v7m

    gen = max(v7m.GEN_HEADROOM_TOKENS, (hops + 1) * 12)
    minimal = span + v7m.PROMPT_OVERHEAD_TOKENS + gen
    return v7m.grade_reachable(span, hops, minimal) and not v7m.grade_reachable(
        span, hops, minimal - 1
    )
