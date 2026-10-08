"""Pins: R-25 (session 44, addendum 122). Questions match prefill time.

The author: "OK prefill rate is a good indicator. Make the questions
match prefill time." Prefill cost grows ~linearly with the span, so
k(s) = max(1, round(K * SPANS[0] / s)): the smallest span earns K
questions, larger spans proportionally fewer, floored at one.
"""

import bench.v7 as v7


def test_questions_inverse_in_span():
    for s in v7.SPANS:
        assert v7.questions_for_span(s) == max(1, round(v7.K * v7.SPANS[0] / s))


def test_every_span_still_measured():
    assert all(v7.questions_for_span(s) >= 1 for s in v7.SPANS)


def test_prefill_time_matched_across_spans():
    """k(s) * s is constant above the floor: equal prefill per span."""
    products = {v7.questions_for_span(s) * s for s in v7.SPANS if v7.questions_for_span(s) > 1}
    assert products == {v7.K * v7.SPANS[0]}, "equal prefill time per span, unfloored spans only"
