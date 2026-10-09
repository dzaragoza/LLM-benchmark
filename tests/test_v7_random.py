"""Pins: R-29 (session 45, addendum 150) - the random climb: the
assumption-free allocation policy. No ordering over the axes (the
author rejected the lexicographic fidelity ceiling for exactly that
flaw - an order assigns importance), no step preference; a SEEDED rng
picks each upgrade among the fitting ones; the stop is the same
maximality contract (no upgrade fits). Reproducibility is a wow.md
rule-1 obligation: ALLOC_RANDOM_SEED is registered, seeded per
(family, ctx) via params.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bench import v7


def _maximal(rows, budget=4.0):
    for r in rows:
        for axis, idx, ladder in (
            ("wq", v7.W_LADDER.index(r["wq"]), v7.W_LADDER),
            ("kq", v7.KV_QUANT_LADDER.index(r["kq"]), v7.KV_QUANT_LADDER),
            ("vq", v7.KV_QUANT_LADDER.index(r["vq"]), v7.KV_QUANT_LADDER),
        ):
            if idx + 1 >= len(ladder):
                continue
            cand = {**r, axis: ladder[idx + 1]}
            t = v7._alloc_total(
                r["family"],
                r["params_b"],
                v7.family_geometry(r["family"]),
                cand["wq"],
                cand["kq"],
                cand["vq"],
                r["ctx"],
            )
            assert t is None or t > budget, f"random row not maximal: {r} {axis}"


def test_random_is_maximal():
    rows = v7.climb_allocations(4.0, roster_limit=12, policy="random")
    assert rows
    _maximal(rows)


def test_random_under_budget():
    for r in v7.climb_allocations(4.0, roster_limit=12, policy="random"):
        assert r["est_gib"] <= 4.0


def test_random_is_reproducible():
    """Pins: R-32 - the seeded random climb reproduces its plan."""
    a = v7.climb_allocations(4.0, roster_limit=12, policy="random")
    b = v7.climb_allocations(4.0, roster_limit=12, policy="random")
    assert a == b, "the same seed must produce the same plan"


def test_random_diverges_from_greedy():
    g = {(r["family"], r["ctx"]): r for r in v7.climb_allocations(4.0, 12, "greedy")}
    s = {(r["family"], r["ctx"]): r for r in v7.climb_allocations(4.0, 12, "random")}
    shared = set(g) & set(s)
    assert shared
    assert any(
        (g[k]["wq"], g[k]["kq"], g[k]["vq"]) != (s[k]["wq"], s[k]["kq"], s[k]["vq"]) for k in shared
    ), "random must diverge from greedy somewhere at 4 GiB"


def test_random_policy_in_cli_choices():
    src = open(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "full_benchmark.py"
        ),
        encoding="utf-8",
    ).read()
    assert '"random"' in src, "--v7-alloc must offer the random policy"
