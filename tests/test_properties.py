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
from bench.state_store import _int_cells, arc_cells, speed_cells
from infra.hf_download import RUNG_BITS, estimate_rung_gib, find_rung_file, has_safetensors
from law_fit import kv_gib, law_worst

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


# ---- the addendum-23 targets: estimate, kv arithmetic, the law, cell loaders ----


cell_namespaces = st.dictionaries(
    keys=st.integers(1, 20).map(str),
    values=st.integers(0, 5),
    min_size=0,
    max_size=8,
)


@given(fst=st.fixed_dictionaries({"certify_arc": cell_namespaces}))
def test_arc_cells_roundtrip(fst):
    """Stored str-keys come back as the same int-keyed map."""
    assert arc_cells(fst) == {int(r): p for r, p in fst["certify_arc"].items()}


@given(
    fst=st.fixed_dictionaries(
        {
            "certify_speed": st.dictionaries(
                keys=st.integers(1, 100),
                values=st.dictionaries(
                    keys=st.integers(1, 20).map(str), values=st.integers(0, 3), max_size=5
                ),
            )
        }
    )
)
def test_speed_cells_picks_the_depth(fst):
    """Each depth sees only its own namespace."""
    for depth in (4096, 8192, 65536):
        stored = fst["certify_speed"].get(depth) or {}
        assert speed_cells(fst, depth) == {int(r): p for r, p in stored.items()}


@given(
    junk=st.one_of(
        st.none(), st.integers(), st.text(max_size=3), st.lists(st.integers(), max_size=3)
    )
)
def test_int_cells_guarded(junk):
    """A corrupt namespace (not a dict) yields an empty map, not a crash."""
    assert _int_cells(junk) == {}


@given(
    bad=st.dictionaries(
        keys=st.one_of(st.text(max_size=2), st.integers()),
        values=st.one_of(st.text(max_size=2), st.integers(), st.none()),
        max_size=6,
    )
)
def test_int_cells_skips_corrupt(bad):
    """Whatever int-coercible entries exist come back; the rest are skipped."""
    out = _int_cells(bad)
    for r, p in out.items():
        assert isinstance(r, int) and isinstance(p, int)


@st.composite
def arch(draw):
    return draw(st.integers(1, 128)), draw(st.integers(1, 64)), draw(st.integers(1, 256))


@given(arch=arch(), bpe=st.sampled_from([2.0, 1.0]))
def test_kv_gib_linear_in_depth(arch, bpe):
    layers, kv_heads, head_dim = arch
    half = kv_gib(layers, kv_heads, head_dim, 4096, bpe)
    full = kv_gib(layers, kv_heads, head_dim, 8192, bpe)
    assert math.isclose(full, 2 * half, rel_tol=1e-12)


@given(
    arch=arch(),
    d1=st.integers(1, 65536),
    d2=st.integers(1, 65536),
    bpe=st.sampled_from([1.0, 2.0]),
)
def test_kv_gib_monotone_in_depth(arch, d1, d2, bpe):
    layers, kv_heads, head_dim = arch
    lo, hi = sorted((d1, d2))
    assert kv_gib(layers, kv_heads, head_dim, lo, bpe) <= kv_gib(
        layers, kv_heads, head_dim, hi, bpe
    )


@given(a=st.floats(1e-6, 1.0), b=st.floats(1e-6, 10.0), s=st.floats(0.0, 100.0))
def test_law_worst_positive_and_decreasing(a, b, s):
    w1 = law_worst(s, a, b)
    w2 = law_worst(s + 10.0, a, b)
    assert w1 > 0.0 and w2 > 0.0 and w2 <= w1


@given(
    files=st.lists(st.text(min_size=1, max_size=10), max_size=5),
    sizes=st.dictionaries(
        keys=st.text(min_size=1, max_size=10), values=st.integers(1, 10**10), max_size=5
    ),
)
def test_estimate_none_or_positive(files, sizes):
    est = estimate_rung_gib("Q8_0", files, files, sizes)
    assert est is None or est > 0.0
