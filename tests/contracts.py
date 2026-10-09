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















def weights_gib_positive_ref(params_b: float, wi: int) -> bool:
    """A weight estimate is positive for any positive parameter count
    at any ladder rung (the planner's feasibility filter rests on it).
    pre: params_b > 0.0
    pre: 0 <= wi < 4  # the _0 ladder: Q4_0, Q5_0, Q8_0, F16 (addenda 172/173)
    post: __return__
    """
    from bench.v7 import W_LADDER, weights_gib

    return weights_gib(params_b, W_LADDER[wi]) > 0.0


def weights_gib_linear_ref(a: float, wi: int) -> bool:
    """Weights scale LINEARLY in parameters: doubling the model doubles
    the weight cost at any quant (the per-axis budget accounting).
    pre: a > 0.0
    pre: 0 <= wi < 4  # the _0 ladder: Q4_0, Q5_0, Q8_0, F16 (addenda 172/173)
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
    pre: 0 <= wi < 4 and 0 <= ki < 4 and 0 <= vi < 4  # the _0 ladders (addenda 172/173)
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
    pre: 0 <= ki < 4 and 0 <= vi < 4  # the _0 KV ladder (addenda 172/173)
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


def spans_ascending_ref() -> bool:
    """The span grid is strictly ascending - the dyadic ladder law.
    post: __return__
    """
    from bench.v7 import SPANS

    return all(a < b for a, b in zip(SPANS, SPANS[1:], strict=False))


def ctx_grid_ascending_ref() -> bool:
    """The ctx grid is strictly ascending.
    post: __return__
    """
    from bench.v7 import CTX_GRID

    return all(a < b for a, b in zip(CTX_GRID, CTX_GRID[1:], strict=False))


def format_theorem_q4_ref(params_b: float) -> bool:
    """The q4_0 format theorem: weights_gib is EXACTLY params x 18/32
    bytes - derivable from the block structure (16 payload + 2 scale
    per 32 weights), not a calibrated constant.
    pre: params_b > 0.0
    post: __return__
    """
    import math

    from bench.v7 import weights_gib

    expected = params_b * 1e9 * (18 / 32) / (1 << 30)
    return math.isclose(weights_gib(params_b, "Q4_0"), expected, rel_tol=1e-12)


def format_theorem_q8_ref(params_b: float) -> bool:
    """The q8_0 format theorem: 32 payload bytes + 2 scale bytes per
    32-weight block = 34/32 bytes/weight, census-confirmed.
    pre: params_b > 0.0
    post: __return__
    """
    import math

    from bench.v7 import weights_gib

    expected = params_b * 1e9 * (34 / 32) / (1 << 30)
    return math.isclose(weights_gib(params_b, "Q8_0"), expected, rel_tol=1e-12)
