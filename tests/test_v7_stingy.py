"""Addendum 144 - the stingy climb: the second allocation policy.

R-18's greedy climb takes the LARGEST-fitting single-axis upgrade;
the stingy climb takes the SMALLEST. Both terminate at a maximal
config (no upgrade fits) - the paths diverge, the contract is
identical. This file pins the addendum-144 policy surface.

Pins: R-29 (addendum 144)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bench import v7


def _maximal(rows, budget=4.0):
    """Every row is maximal: no single-axis one-notch upgrade fits."""
    for r in rows:
        wi = v7.W_LADDER.index(r["wq"])
        ki = v7.KV_QUANT_LADDER.index(r["kq"])
        vi = v7.KV_QUANT_LADDER.index(r["vq"])
        for axis in ("wq", "kq", "vq"):
            if axis == "wq" and wi + 1 < len(v7.W_LADDER):
                cand = (v7.W_LADDER[wi + 1], r["kq"], r["vq"])
            elif axis == "kq" and ki + 1 < len(v7.KV_QUANT_LADDER):
                cand = (r["wq"], v7.KV_QUANT_LADDER[ki + 1], r["vq"])
            elif axis == "vq" and vi + 1 < len(v7.KV_QUANT_LADDER):
                cand = (r["wq"], r["kq"], v7.KV_QUANT_LADDER[vi + 1])
            else:
                continue
            t = v7._alloc_total(
                r["family"],
                r["params_b"],
                v7.family_geometry(r["family"]),
                cand[0],
                cand[1],
                cand[2],
                r["ctx"],
            )
            assert t is None or t > budget, (
                f"stingy row not maximal: {r['family']} ctx={r['ctx']} "
                f"upgrade to {cand} fits ({t:.2f} <= {budget})"
            )


def test_stingy_is_maximal():
    rows = v7.climb_allocations(4.0, roster_limit=12, policy="stingy")
    assert rows
    _maximal(rows)


def test_stingy_under_budget():
    for r in v7.climb_allocations(4.0, roster_limit=12, policy="stingy"):
        assert r["est_gib"] <= 4.0


def test_stingy_floor_is_feasible():
    """Same floor contract as greedy (test_greedy_floor_is_222): every
    emitted cell is under budget, and a starved budget emits nothing -
    the (Q2_K, q4_0, q4_0) floor is where every climb starts."""
    rows = v7.climb_allocations(0.45, roster_limit=12, policy="stingy")
    for r in rows:
        assert r["est_gib"] <= 0.45
    assert v7.climb_allocations(0.1, roster_limit=12, policy="stingy") == []


def test_stingy_diverges_from_greedy():
    g = {(r["family"], r["ctx"]): r for r in v7.climb_allocations(4.0, 12, "greedy")}
    s = {(r["family"], r["ctx"]): r for r in v7.climb_allocations(4.0, 12, "stingy")}
    shared = set(g) & set(s)
    assert shared, "rosters must overlap"
    assert any(
        (g[k]["wq"], g[k]["kq"], g[k]["vq"]) != (s[k]["wq"], s[k]["kq"], s[k]["vq"]) for k in shared
    ), "stingy must diverge from greedy somewhere at 4 GiB"


def test_unknown_policy_rejected():
    try:
        v7.climb_allocations(4.0, policy="bogus")
    except ValueError:
        return
    raise AssertionError("unknown policy must raise")


def test_greedy_policy_default_matches_r18():
    g = v7.climb_allocations(4.0, 12)
    assert g == v7.climb_allocations(4.0, 12, policy="greedy")
    for r in g:
        assert r["est_gib"] <= 4.0
