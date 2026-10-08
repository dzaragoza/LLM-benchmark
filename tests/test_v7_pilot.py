"""v7 pilot: the graded-grid scorer and the allocation planner (offline parts)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import v7_pilot


def test_grid_shape():
    assert len(v7_pilot.SPANS) * len(v7_pilot.HOPS) * v7_pilot.K == 700


def test_allocation_plan_frontier():
    rows = v7_pilot.plan_allocations(4.0, roster_limit=12)
    assert rows, "4 GiB must admit at least one allocation"
    for r in rows:
        assert r["est_gib"] <= 4.0
        w = v7_pilot.family_window(r["family"])
        assert not w or r["ctx"] <= w
    biggest = max(r["params_b"] for r in rows)
    assert biggest >= 1.0, "4 GiB must afford a ~1B model somewhere"


def test_question_prompt_tail():
    corpus = {"context": "NOISE", "questions": [], "s_max": 100}
    q = {"span": 4096, "hops": 4, "names": ["AAAAA", "BBBBB"], "value": "12345"}
    p = v7_pilot.question_prompt(corpus, q)
    assert "NOISE" in p and "12345" in p and "5 variables" in p


def test_greedy_starts_low_and_climbs():
    rows = v7_pilot.greedy_allocations(4.0, roster_limit=12)
    assert rows
    for r in rows:
        assert r["wq"] in v7_pilot.W_LADDER
        assert r["kq"] in v7_pilot.KV_QUANT_LADDER
        assert r["vq"] in v7_pilot.KV_QUANT_LADDER
        assert r["est_gib"] <= 4.0


def test_greedy_is_maximal():
    """No single-axis one-notch upgrade fits after the climb stops."""
    rows = v7_pilot.greedy_allocations(4.0, roster_limit=12)
    for r in rows:
        geom = v7_pilot.family_geometry(r["family"])
        wi = v7_pilot.W_LADDER.index(r["wq"])
        ki = v7_pilot.KV_QUANT_LADDER.index(r["kq"])
        vi = v7_pilot.KV_QUANT_LADDER.index(r["vq"])
        for axis in range(3):
            cw, ck, cv = wi, ki, vi
            if axis == 0 and wi + 1 < len(v7_pilot.W_LADDER):
                cw = wi + 1
            elif axis == 1 and ki + 1 < len(v7_pilot.KV_QUANT_LADDER):
                ck = ki + 1
            elif axis == 2 and vi + 1 < len(v7_pilot.KV_QUANT_LADDER):
                cv = vi + 1
            else:
                continue
            t = v7_pilot.weights_gib(r["params_b"], v7_pilot.W_LADDER[cw]) + (
                v7_pilot.kv_split_gib(
                    geom, v7_pilot.KV_QUANT_LADDER[ck], v7_pilot.KV_QUANT_LADDER[cv], r["ctx"]
                )
            )
            assert t > 4.0, f"upgrade fits but was not taken: {r} axis={axis}"


def test_greedy_floor_is_222():
    """The tiny families with headroom must climb to the top; the
    starting point (2,2,2) must be feasible for every emitted cell."""
    rows = v7_pilot.greedy_allocations(0.45, roster_limit=12)
    for r in rows:
        assert r["est_gib"] <= 0.45
    # and at a starved budget, the floor config itself must appear
    tiny = v7_pilot.greedy_allocations(0.1, roster_limit=12)
    assert tiny == []
