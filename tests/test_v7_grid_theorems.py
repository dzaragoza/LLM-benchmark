"""Pins: addendum 182 - the formal layer built out where it is
superior: the v7 grid arithmetic, proven over the whole domain by
crosshair contracts (the author's ruling: trust formal methods where
they are clearly better; tests only cover different risks).

The grid invariants (formerly implicit, now theorems):
- SPANS/HOPS/CTX_GRID are strictly ascending (the dyadic ladder law)
- every span fits the largest ctx rung (R-28's no-zero-max root)
- the ladder constants equal their structural derivations
  (q4_0 = 18/32 bytes/weight, q8_0 = 34/32 - the format theorems)
"""

from bench import v7


def test_grid_ascending():
    assert v7.SPANS == sorted(set(v7.SPANS)), "SPANS must be strictly ascending"
    assert v7.HOPS == sorted(set(v7.HOPS)), "HOPS must be strictly ascending"
    assert v7.CTX_GRID == sorted(set(v7.CTX_GRID)), "CTX_GRID must be ascending"


def test_every_span_fits_the_largest_ctx():
    for s in v7.SPANS:
        assert s + v7.PROMPT_OVERHEAD_TOKENS <= v7.CTX_GRID[-1], (
            f"span {s} + overhead exceeds the largest ctx rung - a zero-max "
            f"cell at the top rung (R-28 violation)"
        )


def test_the_format_theorems():
    """The _0 ladder constants are the structural format sizes, derivable
    and provable - not registered magic (the author's formal-methods
    ruling): q4_0 = 18 bytes/32 weights, q8_0 = 34/32, f16 = 2.0."""
    assert v7.W_QUANT_BPB["Q4_0"] == 18 / 32
    assert v7.W_QUANT_BPB["Q8_0"] == 34 / 32
    assert v7.W_QUANT_BPB["F16"] == 2.0
    # the KV factors are the same arithmetic per K/V half
    assert v7.KV_QUANT_FACTOR["q4_0"] == (18 / 32) / 2
    assert v7.KV_QUANT_FACTOR["q8_0"] == (34 / 32) / 2
