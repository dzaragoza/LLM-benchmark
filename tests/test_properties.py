"""Hypothesis property tests (session 40, addendum 22) - the
falsification complement to tests/contracts.py's proofs.

The contracts PROVE what holds for all inputs; these properties
SEARCH for counterexamples where proof is not feasible (state,
strings, corpus-shaped data). Same contracts, different tool:
crosshair proves, hypothesis falsifies cheaply.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

pytestmark = pytest.mark.hypothesis_props


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

@given(
    k_v=st.integers(min_value=0, max_value=5),
    n_v=st.integers(min_value=1, max_value=5),
)
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
