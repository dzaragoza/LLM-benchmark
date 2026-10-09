"""Pins: R-37 (session 44, addendum 128). The 4k ctx rung dropped.

The author: "Drop 4k." After the 2k span was dropped (addendum
123), the smallest span 4096 + overhead 128 + headroom 192 = 4416
tokens no longer fit a 4096 window - every ctx=4096 cell asked zero
questions and scored a structural 0/0 (granite-4.0-h-350m live:
empty answers file, wall 0.0s). The rung is dropped; the smallest
ctx now hosts the smallest span (8192 hosts 4096).

The honest consequence, pinned: the four 4096-window families
(Phi-3-mini-4k-instruct, granite-3.0-2b-instruct, MiniCPM-1B-sft,
MiniCPM-2B-sft) earn no cell - their window is below the smallest
ctx rung, exactly like the 2048-window families at addendum 123.
"""

import bench.v7 as v7


def test_smallest_ctx_hosts_smallest_span():
    """No structural 0/0 rungs: span + overhead + headroom must fit
    the smallest ctx window."""
    s = min(v7.SPANS)
    assert s + v7.PROMPT_OVERHEAD_TOKENS + v7.GEN_HEADROOM_TOKENS <= min(v7.CTX_GRID)


def test_ctx_grid_has_no_4k():
    assert 4096 not in v7.CTX_GRID
    assert min(v7.CTX_GRID) == 8192


def test_4096_window_families_earn_no_cell():
    for fam in (
        "Phi-3-mini-4k-instruct",
        "granite-3.0-2b-instruct",
        "MiniCPM-1B-sft",
        "MiniCPM-2B-sft",
    ):
        assert v7.family_window(fam) == 4096
    rows = v7.climb_allocations(4.0, roster_limit=38)
    for fam in (
        "Phi-3-mini-4k-instruct",
        "granite-3.0-2b-instruct",
        "MiniCPM-1B-sft",
        "MiniCPM-2B-sft",
    ):
        assert not any(r["family"] == fam for r in rows), f"{fam}: window 4096 earns no cell"
