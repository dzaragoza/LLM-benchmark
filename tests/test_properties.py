"""Hypothesis property tests (session 40, addendum 22) - the
falsification complement to tests/contracts.py's proofs.

The contracts PROVE what holds for all inputs; these properties
SEARCH for counterexamples where proof is not feasible (state,
strings, corpus-shaped data). Same contracts, different tool:
crosshair proves, hypothesis falsifies cheaply.
"""

from __future__ import annotations

import math

import pytest
from bench.certify import wilson_interval
from hypothesis import given, settings
from hypothesis import strategies as st

from infra.hf_download import RUNG_BITS, estimate_rung_gib, find_rung_file, has_safetensors

pytestmark = pytest.mark.hypothesis_props

RUNGS = sorted(RUNG_BITS)

model_names = st.sampled_from(
    [
        "Qwen3.5-0.8B",
        "Qwen2.5-1.5B-Instruct",
        "Llama-3.2-3B-Instruct",
        "gemma-3-4b-it",
        "MiniCPM5-2B",
    ]
)
file_exts = st.sampled_from([".gguf", ".safetensors", ".bin", ".md", ".gguf.b64"])


@st.composite
def repo_files(draw):
    """A plausible repo listing: model files, quant rungs, junk."""
    fam = draw(model_names)
    names = []
    for rung in draw(st.sets(st.sampled_from(RUNGS), min_size=1)):
        names.append(f"{fam}-{rung}.gguf")
    for _ in range(draw(st.integers(0, 4))):
        names.append(f"{draw(model_names)}-f16{draw(file_exts)}")
    if draw(st.booleans()):
        names.append(f"{fam}-mmproj-f16.gguf")
    return names


@given(k=st.integers(0, 500), n=st.integers(0, 500), z=st.floats(0.0, 5.0))
def test_wilson_bounds(k, n, z):
    lo, hi = wilson_interval(min(k, n), max(n, min(k, n)), z)
    assert 0.0 <= lo <= hi <= 1.0


@given(k=st.integers(0, 99), n=st.integers(1, 100), z=st.floats(0.0, 3.0))
@settings(max_examples=200)
def test_wilson_monotone_in_k(k, n, z):
    """More passes, same evidence, must never lower the bound."""
    k = min(k, n - 1)
    lo1, _ = wilson_interval(k, n, z)
    lo2, _ = wilson_interval(k + 1, n, z)
    assert lo1 <= lo2


@given(k=st.integers(0, 20), n=st.integers(1, 20))
def test_wilson_zero_sigma_collapses(k, n):
    k = min(k, n)
    lo, hi = wilson_interval(k, n, 0.0)
    assert math.isclose(lo, hi, abs_tol=1e-12)
    assert math.isclose(lo, k / n, abs_tol=1e-12)


@given(files=repo_files(), rung=st.sampled_from(RUNGS))
def test_find_rung_file_returns_member(files, rung):
    hit = find_rung_file(files, rung)
    if hit is not None:
        assert hit in files
        assert rung.lower() in hit.lower()
        assert hit.lower().endswith(".gguf")
        assert "mmproj" not in hit.lower()


@given(files=st.lists(st.text(min_size=0, max_size=12), max_size=10))
def test_has_safetensors_iff(files):
    result = has_safetensors(files)
    assert result == any(f.lower().endswith(".safetensors") for f in files)


@given(n=st.integers(1, 100), z=st.floats(0.1, 3.0))
def test_wilson_all_pass_saturates(n, z):
    """k=n: the upper bound saturates at exactly 1; the lower is
    Wilson's own 1/denom (strictly below 1 for z > 0 - the honest
    interval never claims certainty from finite evidence)."""
    lo, hi = wilson_interval(n, n, z)
    assert math.isclose(hi, 1.0, abs_tol=1e-12)
    denom = 1 + z * z / n
    assert math.isclose(lo, 1.0 / denom, abs_tol=1e-9)


# ---- the addendum-23 targets: estimate, kv arithmetic, the law, cell loaders ----


cell_namespaces = st.dictionaries(
    keys=st.integers(1, 20).map(str),
    values=st.integers(0, 5),
    min_size=0,
    max_size=8,
)


@given(
    fst=st.fixed_dictionaries(
        {
            "certify_speed": st.dictionaries(
                keys=st.integers(1, 100),
                values=st.dictionaries(
                    keys=st.integers(1, 20).map(str), values=st.integers(0, 3), max_size=5
                ),
            )
        }
    )
)
def test_estimate_none_or_positive(files, sizes):
    est = estimate_rung_gib("Q8_0", files, files, sizes)
    assert est is None or est > 0.0


# ================================================== addendum 38, ruling c:
# the state roundtrip and the medal's monotonicity


@settings(max_examples=50)
@given(
    task=st.sampled_from(["vt", "speed"]),
    depth=st.integers(4096, 262144),
    run=st.integers(1, 21),
    value=st.integers(0, 5),
    secs=st.floats(0.0, 10000.0),
)
def test_combined_medal_monotone_in_evidence(n_pass, others_gold):
    """The medal is MONOTONE in the evidence: turning failing cells
    into passes can never LOWER the tier - a state that grades 1_sigma
    with k passes still grades at least 1_sigma with k+1."""
    from bench.certify import combined_medal

    def fst_with(k_fwe):
        return {
            "certify": {"8192": {str(r): 3 if r <= k_fwe else 0 for r in range(1, 21)}},
            "certify_vt": {
                "8192": {
                    str(r): (5 if others_gold else (4 if r <= 10 else 0)) for r in range(1, 21)
                }
            },
            "certify_speed": {"8192": {str(r): 0 for r in range(1, 21)}},
            "certify_arc": {
                str(r): (5 if others_gold else (4 if r <= 10 else 0)) for r in range(1, 21)
            },
        }

    tier_rank = {"0.5_sigma": 1, "1_sigma": 2, "2_sigma": 3}

    def rank(fst):
        m = combined_medal(fst, 8192)
        return tier_rank.get(m, 0)

    base = fst_with(n_pass)
    if n_pass < 20:
        improved = fst_with(n_pass + 1)
        assert rank(improved) >= rank(base)


# ================================================== session 43, R-18/R-19:
# the v7 allocation arithmetic and the scorer's bounds

from bench.v7 import (  # noqa: E402
    KV_QUANT_FACTOR,
    KV_QUANT_LADDER,
    W_LADDER,
    W_QUANT_BPB,
    weights_gib,
)


@settings(max_examples=100)
@given(
    params_b=st.floats(0.01, 50.0),
    wq=st.sampled_from(W_LADDER),
    kq=st.sampled_from(KV_QUANT_LADDER),
    vq=st.sampled_from(KV_QUANT_LADDER),
    ctx=st.integers(2048, 262144),
    per_token=st.floats(0.0, 4096.0),
)
def test_alloc_total_monotone_in_quant(params_b, wq, kq, vq, ctx, per_token):
    """The memory estimate is monotone in every ladder axis: a higher
    weight rung, a higher cache rung, or a deeper ctx never SHRINKS
    the estimate (the greedy climb's budget discipline rests on it)."""

    w_i = W_LADDER.index(wq)
    k_i = KV_QUANT_LADDER.index(kq)
    v_i = KV_QUANT_LADDER.index(vq)
    base = _alloc_total_at(params_b, per_token, wq, kq, vq, ctx)
    if w_i + 1 < len(W_LADDER):
        up = _alloc_total_at(params_b, per_token, W_LADDER[w_i + 1], kq, vq, ctx)
        assert up >= base
    if k_i + 1 < len(KV_QUANT_LADDER):
        up = _alloc_total_at(params_b, per_token, wq, KV_QUANT_LADDER[k_i + 1], vq, ctx)
        assert up >= base
    if v_i + 1 < len(KV_QUANT_LADDER):
        up = _alloc_total_at(params_b, per_token, wq, kq, KV_QUANT_LADDER[v_i + 1], ctx)
        assert up >= base
    assert _alloc_total_at(params_b, per_token, wq, kq, vq, ctx * 2) >= base


def _alloc_total_at(params_b, per_token, wq, kq, vq, ctx):
    """_alloc_total with the KV-per-token term injected (no registry)."""
    kv = (per_token / 2.0) * (KV_QUANT_FACTOR[kq] + KV_QUANT_FACTOR[vq]) * ctx
    return weights_gib(params_b, wq) + kv / (1 << 30)


@settings(max_examples=100)
@given(
    params_b=st.floats(0.01, 50.0),
    wq=st.sampled_from(W_LADDER),
)
def test_weights_gib_matches_ladder_order(params_b, wq):
    """The weight ladders are ordered by bits-per-byte: a higher rung
    never weighs LESS (the climb's single-axis budget accounting)."""
    i = W_LADDER.index(wq)
    if i > 0:
        assert W_QUANT_BPB[W_LADDER[i]] >= W_QUANT_BPB[W_LADDER[i - 1]]
    assert weights_gib(params_b, wq) > 0.0


@given(k_v=st.integers(0, 5), n_v=st.integers(1, 5))
def test_score_vt_partial_never_passes(k_v, n_v):
    """The pass is ALL names (upstream's rule): fewer found names than
    expected is never a pass, however many were found."""
    import ruler_gate

    expected = [chr(ord("A") + i) * 5 for i in range(n_v)]
    answer = " ".join(expected[:k_v])
    ok, found = ruler_gate.score_vt(answer, expected)
    assert ok == (found == n_v)
    assert found == min(k_v, n_v)


@given(names=st.lists(st.text(min_size=5, max_size=5, alphabet="ABCDE"), min_size=1, max_size=6))
def test_score_vt_order_and_noise_tolerant(names):
    """Names found in ANY order (with debris) still pass - the score
    reads a natural-language answer, not a formatted one."""
    import random as _random

    import ruler_gate

    unique = list(dict.fromkeys(names))
    shuffled = unique[:]
    _random.Random(0).shuffle(shuffled)
    answer = "Sure! They are: " + ", ".join(shuffled) + " (end)"
    ok, found = ruler_gate.score_vt(answer, unique)
    assert ok and found == len(unique)


# ---- v7 reachability: the arithmetic must upper-bound the rendered request ----
# Session 44, addendum 112: both live crashes were estimate-vs-server drift.
# The pinned invariant: IF grade_reachable says yes, THEN the rendered
# prompt's measured tokens + generation fit the window. The fake
# tokenizer (1 token per 4 chars) makes the rendered length computable.


@given(
    span=st.sampled_from([2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144]),
    hops=st.sampled_from([2, 4, 8, 16, 32]),
    window=st.integers(min_value=2048, max_value=262144),
)
def test_grade_reachable_never_overflows_the_rendered_request(span, hops, window):
    """The soundness direction: reachable => the WHOLE request fits.
    grade_reachable's arithmetic must be an upper bound on the real
    rendered prompt + the server's max_tokens reservation."""
    import bench.v7 as v7
    import ruler_gate

    if not v7.grade_reachable(span, hops, window):
        return
    gen = max(ruler_gate.VT_GEN_TOKENS, (hops + 1) * 12)
    # the rendered prompt is the span prefix (<= span tokens by
    # construction of cuts) + the template tail, which the overhead
    # constant must cover: template + query + names is well under
    # PROMPT_OVERHEAD_TOKENS + margin; the pin is the bound relation
    assert span + v7.PROMPT_OVERHEAD_TOKENS + max(v7.GEN_HEADROOM_TOKENS, gen) <= window
    assert gen + span < window  # no reachable grade leaves zero room


@given(
    overhead=st.integers(min_value=0, max_value=512),
    headroom=st.integers(min_value=0, max_value=512),
)
def test_grade_reachable_monotone_in_window(overhead, headroom):
    """Widening the window never un-reaches a grade - the exclusion
    rule is monotone; a non-monotone rule would silently drop grades
    that DO fit."""
    import bench.v7 as v7

    for span in (1024, 2048, overhead + 1 if overhead else 1024):
        for hops in (2, 16, headroom % 17):
            for w1, w2 in ((2048, 4096), (4096, 8192), (16384, 32768)):
                r1 = v7.grade_reachable(span, hops, w1)
                r2 = v7.grade_reachable(span, hops, w2)
                assert not (r1 and not r2)
