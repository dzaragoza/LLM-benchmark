"""size_predict.py (addendum 110): config-only Q8_0 file sizes.

The conversion policy validated on the measured v3.1 set: body tensors
at exactly 8.5 bpw, the OUTPUT tensor kept F16 (tied embedding, or
untied lm_head; untied embedding quantizes). Non-dense configs are
refused rather than mis-predicted.
"""

import json

import pytest

import size_predict as sp

# (config overrides, measured GiB, tolerance)
MEASURED = [
    (
        dict(
            hidden_size=896,
            num_hidden_layers=24,
            vocab_size=151936,
            intermediate_size=4864,
            num_attention_heads=14,
            num_key_value_heads=2,
            tie_word_embeddings=True,
        ),
        0.63,
        0.05,
    ),
    (
        dict(
            hidden_size=1536,
            num_hidden_layers=28,
            vocab_size=151936,
            intermediate_size=8960,
            num_attention_heads=12,
            num_key_value_heads=2,
            tie_word_embeddings=True,
        ),
        1.76,
        0.03,
    ),
    (
        dict(
            hidden_size=2048,
            num_hidden_layers=36,
            vocab_size=151936,
            intermediate_size=11008,
            num_attention_heads=16,
            num_key_value_heads=2,
            tie_word_embeddings=True,
        ),
        3.37,
        0.03,
    ),
    (
        dict(
            hidden_size=2560,
            num_hidden_layers=36,
            vocab_size=151936,
            intermediate_size=9728,
            num_attention_heads=32,
            num_key_value_heads=8,
            tie_word_embeddings=True,
        ),
        3.99,
        0.03,
    ),
    (
        dict(
            hidden_size=2560,
            num_hidden_layers=36,
            vocab_size=151936,
            intermediate_size=9728,
            num_attention_heads=32,
            num_key_value_heads=8,
            tie_word_embeddings=False,
        ),
        4.29,
        0.05,
    ),
]


@pytest.fixture(params=MEASURED, ids=["0.5B", "1.5B", "3B", "4B-tied", "4B-untied"])
def measured_case(request):
    return request.param


def write_cfg(tmp_path, cfg):
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return str(p)


def test_policy_hits_measured_files(measured_case, tmp_path):
    cfg, measured, tol = measured_case
    _, gib = sp.predict(write_cfg(tmp_path, cfg))
    assert gib == pytest.approx(measured, rel=tol)


def test_moe_refused(tmp_path):
    cfg = dict(
        hidden_size=896,
        num_hidden_layers=24,
        vocab_size=151936,
        intermediate_size=4864,
        num_attention_heads=14,
        num_key_value_heads=2,
        tie_word_embeddings=True,
        num_experts=8,
    )
    with pytest.raises(SystemExit):
        sp.predict(write_cfg(tmp_path, cfg))


def test_tied_vs_untied_split(tmp_path):
    """The 4.29-vs-3.99 measured split is tie_word_embeddings."""
    base = dict(
        hidden_size=2560,
        num_hidden_layers=36,
        vocab_size=151936,
        intermediate_size=9728,
        num_attention_heads=32,
        num_key_value_heads=8,
    )
    _, tied = sp.predict(write_cfg(tmp_path, {**base, "tie_word_embeddings": True}))
    _, untied = sp.predict(write_cfg(tmp_path, {**base, "tie_word_embeddings": False}))
    assert untied - tied == pytest.approx((151936 * 2560 * sp.Q8_BYTES) / sp.GIB, rel=0.01)
