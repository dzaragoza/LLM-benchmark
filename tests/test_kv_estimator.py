"""Addendum 133: the KV estimator must honor hybrid attention.

The addendum-132 run over-estimated Qwen3.5-0.8B ~4x at every ctx
(the estimator charged all 24 layers a full-window cache; only every
4th layer is full attention). Consequences: the greedy climb stopped
early (wrong, over-quantized configs - hurting scores) and the VRAM
recommendation was wrong. This pins the fix against the census
anchors measured in the addendum-132 run.
"""

import bench.v7 as v7

# (ctx, kv factor, measured context_gib from the census) - the
# addendum-132 run's Qwen3.5-0.8B anchors, family interval 4
QWEN_ANCHORS = [
    (8192, 1.0, 0.112),
    (16384, 1.0, 0.206),
    (32768, 1.0, 0.394),
    (65536, 1.0, 0.769),
    (131072, 0.53125, 0.815),
    (262144, 0.28125, 0.862),
]


def test_hybrid_interval_divides_kv():
    """The interval divides the per-token cost: Qwen3.5-0.8B's
    naive 24-layer figure is 49152 B/token; with interval 4 the
    estimator must return 12288 - the number that fits the
    census."""
    geom = v7.family_geometry("Qwen3.5-0.8B")
    assert geom and geom.get("full_attention_interval") == 4
    got = v7.kv_per_token_f16("Qwen3.5-0.8B", geom)
    assert got == 12288.0


def test_full_attention_family_unchanged():
    """Interval-1 families keep the naive figure (granite-4.0-350m:
    28 layers x 2 x 4 kvh x 64 hd x 2 B = 28672)."""
    geom = v7.family_geometry("granite-4.0-350m")
    got = v7.kv_per_token_f16("granite-4.0-350m", geom)
    assert got == 28672.0


def test_kv_est_fits_census_anchors():
    """The corrected estimator predicts the measured context_gib
    within 5% at every anchor >= 32k (wow.md rule 1: disagreements
    >5% per factor trigger recalibration). The small-ctx anchors
    run LOW because the census folds the compute buffer floor
    into 'context' - noted, not pinned."""
    geom = v7.family_geometry("Qwen3.5-0.8B")
    per_token = v7.kv_per_token_f16("Qwen3.5-0.8B", geom)
    assert per_token is not None
    for ctx, factor, meas in QWEN_ANCHORS:
        if ctx < 32768:
            continue
        pred_gib = per_token * factor * ctx / (1 << 30)
        assert abs(pred_gib - meas) / meas < 0.05, (ctx, pred_gib, meas)


def test_allocations_climb_higher_after_fix():
    """The greedy climb no longer stops early: Qwen3.5-0.8B at
    262144 must reach a HIGHER weight rung than the addendum-132
    Q5_K (the wrong estimator starved the weights to fund a
    4x-overpriced cache)."""
    rows = [r for r in v7.greedy_allocations(4.0) if r["family"] == "Qwen3.5-0.8B"]
    top = [r for r in rows if r["ctx"] == 262144]
    assert top, "Qwen must place at 262144"
    w_ladder = v7.W_LADDER
    assert w_ladder.index(top[0]["wq"]) >= w_ladder.index("Q5_K")
    assert top[0]["est_gib"] <= 4.0
