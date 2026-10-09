"""Pins: R-40 (session 45, addendum 172) - _0 encodings only below f16:
the weights ladder is exactly [Q4_0, Q8_0, F16] - the legacy block
formats with exact structural sizes (0.5625 and 1.0625 bpB), no K-quant
super-block bookkeeping (the Q4_K size hazard was the addendum-170/171
lesson: measured 0.625-0.646 vs the naive 0.56 - the k-scales are a
size-limit risk at the budget line).
"""

from pathlib import Path

import bench.v7 as v7

ROOT = Path(__file__).resolve().parent.parent


def test_r40_the_ladder_is_0_encodings_only():
    assert v7.W_LADDER == ["Q4_0", "Q4_1", "Q5_0", "Q5_1", "Q8_0", "F16"], (
        "the weights ladder is the _0 family + f16 only (addenda 172/173)"
    )


def test_r40_no_k_quant_anywhere_in_the_v7_plan():
    """No K-quant encoding exists on the weights ladder or the KV
    ladder - the plan cannot produce one."""
    for wq in v7.W_LADDER:
        assert not wq.endswith("_K"), f"K-encoding on the weights ladder: {wq}"
    for kvq in v7.KV_QUANT_LADDER:
        assert not kvq.endswith("_K"), f"K-encoding on the KV ladder: {kvq}"


def test_r40_the_sizes_are_structural():
    """The _0 formats' bpB are the exact structural constants - no
    census calibration needed, no under-estimate risk from
    bookkeeping."""
    assert v7.W_QUANT_BPB["Q4_0"] == 0.5625  # 18 bytes / 32 weights
    assert v7.W_QUANT_BPB["Q8_0"] == 1.0625  # 34 bytes / 32 weights


def test_r40_the_ladders_are_equal():
    """Addendum 173: the weights and KV ladders carry the same _0 family."""
    assert [q.lower() for q in v7.W_LADDER] == v7.KV_QUANT_LADDER
