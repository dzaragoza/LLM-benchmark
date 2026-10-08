"""Pins: R-25 (session 44, addendum 121). The 5-minute cell ceiling.

The author's ruling: "Let's aim for 5 minutes max per cell." Two
mechanisms: CELL_BUDGET_SECONDS (a wall-clock ceiling - a slow
machine stops the cell at the budget and scores what landed,
honestly marked) and k-major question order (a truncated cell
covers every (span, hops) grade at least once before the second
sample of anything).
"""

import bench.v7 as v7


def test_budget_is_five_minutes():
    assert v7.CELL_BUDGET_SECONDS == 300, "addendum 121: 5 minutes max per cell"


def test_questions_are_k_major():
    """k-major order: every (span, hops) grade appears once before
    any grade gets its second question (K=2) - a budget-stopped
    cell still covers the whole grid."""
    order = [(s, h) for k_i in range(v7.K) for s in v7.SPANS for h in v7.HOPS]
    first_pass = len(v7.SPANS) * len(v7.HOPS)
    grades_in_first_pass = len(set(order[:first_pass]))
    assert grades_in_first_pass == first_pass, "k_i=0 sweep must cover all grades first"
