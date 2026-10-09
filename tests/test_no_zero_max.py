"""Pins: R-28 (session 44, addendum 130). No cell with max score 0.

The author: "A scoring system shall never create situations where
the maximum possible score is 0." A cell that structurally cannot
reach any grade (max_score 0) is a wasted measurement and a lying
row in the table - the addendum-128 lesson: after the 2k span was
dropped, every ctx=4096 cell scored a structural 0/0 with an empty
answers file.

The invariant: every ctx rung in the grid must host at least one
(span, hops) grade - smallest span + prompt overhead + generation
headroom <= the rung's window. Checked against the real allocation
plan, not just the constants.
"""

import bench.v7 as v7


def test_every_ctx_rung_reaches_at_least_one_grade():
    for ctx in v7.CTX_GRID:
        reachable = [(s, h) for s in v7.SPANS for h in v7.HOPS if v7.grade_reachable(s, h, ctx)]
        assert reachable, f"ctx {ctx}: max score would be 0 (R-28 violation)"


def test_allocation_plan_has_no_zero_max_cells():
    """Every cell in the real greedy plan can reach at least one
    grade at its ctx - no structural 0/0 rows in the table."""
    rows = v7.climb_allocations(4.0, roster_limit=38)
    assert rows, "the plan must have cells"
    for r in rows:
        reachable = [
            (s, h) for s in v7.SPANS for h in v7.HOPS if v7.grade_reachable(s, h, r["ctx"])
        ]
        assert reachable, f"{r['family']} ctx {r['ctx']}: max score would be 0 (R-28 violation)"


def test_r28_in_protocol():
    from pathlib import Path

    text = (Path(__file__).resolve().parent.parent / "md" / "protocol.md").read_text(
        encoding="utf-8"
    )
    assert "| R-28 |" in text
    assert "maximum possible score is 0" in text
