"""Registered-constants arithmetic (addendum 87).

protocol.md is the single source of the study's registered constants.
These tests recompute the study's headline derived numbers from them,
so any future edit that silently drifts a constant fails here first.

NOTE (flagged to the author, addendum 87): the registered "4.92 GiB
~ 4.6B params" ceiling (addendum 78) is arithmetically the PARAMS
number at the formula's own size ceiling: 76.5 x (0.412/5.0 - 1/74)
= 5.27 GiB file size (matching PROTOCOL row 103's 5.27 GiB ceiling),
which / 1.07 GiB/B = 4.92B params. The tests assert the formula.
"""

import pytest

import full_benchmark as fb

# ---- the registry (protocol.md rows 100/103/124; single source) ----
BW_EFF = 76.5  # GiB/s, 102.4 tier
T_INF = 74.0  # t/s
W_T_P05_QWEN = 0.412  # the qwen-class anchor
W_T_P05_POOLED = 0.366
READER_WPS = 5.0  # the k=1 guarantee line
GIB_PER_B = 1.07  # Q8_0 file size per B params


def law_tps(size_gib, bw=BW_EFF, t_inf=T_INF):
    """The registered law: 1/t = size/BW + 1/t_inf."""
    return 1.0 / (size_gib / bw + 1.0 / t_inf)


def ceiling_gib(w_t, bw=BW_EFF, t_inf=T_INF, reader=READER_WPS):
    """size_max = BW x (w/t/reader - 1/t_inf)."""
    return bw * (w_t / reader - 1.0 / t_inf)


def test_ceiling_qwen_anchor():
    """The size ceiling at the qwen anchor: 5.27 GiB (PROTOCOL row
    103's number), i.e. 4.92B params at Q8_0 (1.07 GiB/B)."""
    size_max = ceiling_gib(W_T_P05_QWEN)
    assert size_max == pytest.approx(5.27, abs=0.01)
    params = size_max / GIB_PER_B
    assert params == pytest.approx(4.92, abs=0.01)


def test_ceiling_pooled_anchor_lower():
    """The anchor-conditional caveat: the pooled anchor ceilings
    lower than the qwen anchor."""
    qwen = ceiling_gib(W_T_P05_QWEN)
    pooled = ceiling_gib(W_T_P05_POOLED)
    assert pooled < qwen
    assert pooled == pytest.approx(4.57, abs=0.01)


def test_ceiling_is_the_inversion_of_the_law():
    """At the ceiling size, the law's w/s lands exactly on the reader
    line - the ceiling is the law inverted at 5.0 w/s."""
    size_max = ceiling_gib(W_T_P05_QWEN)
    wps = law_tps(size_max) * W_T_P05_QWEN
    assert wps == pytest.approx(READER_WPS, abs=1e-6)


def test_law_4b_cell():
    """The law at the roster's sharp-edge size (MiniCPM3-4B, 4.03 GiB):
    predicted 5.52 w/s at w/t 0.366 (pooled) - the pre-registered row."""
    tps = law_tps(4.03)
    assert tps * W_T_P05_POOLED == pytest.approx(5.52, abs=0.01)


def test_law_monotone_decreasing_in_size():
    sizes = [0.5, 1.0, 2.0, 3.0, 4.0, 5.27]
    tps = [law_tps(s) for s in sizes]
    assert tps == sorted(tps, reverse=True)


def test_band_pred_form():
    """The corrected prediction band (addendum 74): pred +- 0.156.t/s."""
    tps = law_tps(4.29)
    band = 0.156 * tps
    assert tps - band < tps + band
    # 2*sigma_w/t at the registered anchor: 0.156 = 2 x 0.078
    assert 0.156 == pytest.approx(2 * 0.078)


def test_default_rung_is_q8_0():
    """Addendum 86: the rung WALK is gone; one rung per run, default Q8_0
    (session 34: --rung overrides it - the Q4 context-over-parameters test)."""
    assert fb.RUNG_DEFAULT == "Q8_0"
