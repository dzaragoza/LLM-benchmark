"""Hypothesis property tests (session 40, addendum 22) - the
falsification complement to tests/contracts.py's proofs.

The contracts PROVE what holds for all inputs; these properties
SEARCH for counterexamples where proof is not feasible (state,
strings, corpus-shaped data). Same contracts, different tool:
crosshair proves, hypothesis falsifies cheaply.
"""

from __future__ import annotations

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from bench.certify import wilson_interval
from infra.hf_download import RUNG_BITS, find_rung_file, has_safetensors

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
