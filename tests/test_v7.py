"""v7 pilot: the graded-grid scorer and the allocation planner (offline parts)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bench import v7 as v7_pilot


def test_grid_shape():
    assert len(v7_pilot.SPANS) * len(v7_pilot.HOPS) * v7_pilot.K == 800


def test_smallest_ctx_is_measurable():
    """The 2k rung must reach at least one span grade (the first live
    run's bug: SPANS started at 4096, so 2048-window cells asked zero
    questions and scored 0/0)."""
    smallest_ctx = min(v7_pilot.CTX_GRID)
    assert any(s <= smallest_ctx for s in v7_pilot.SPANS)
    for cell in v7_pilot.greedy_allocations(4.0, v7_pilot.PILOT_FAMILIES):
        reach = [s for s in v7_pilot.SPANS if s <= cell["ctx"]]
        assert reach, f"ctx {cell['ctx']} cannot reach any span grade"


def test_allocation_plan_frontier():
    rows = v7_pilot.greedy_allocations(4.0, roster_limit=12)
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
            t = v7_pilot._alloc_total(
                r["family"], r["params_b"], geom,
                v7_pilot.W_LADDER[cw], v7_pilot.KV_QUANT_LADDER[ck],
                v7_pilot.KV_QUANT_LADDER[cv], r["ctx"],
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


def test_recurrent_family_is_kvless():
    """RWKV7 carries no KV cache: per-token KV is 0 and it earns cells
    at every ctx its window allows (weights-only memory)."""
    assert v7_pilot.is_recurrent("RWKV7-World-2.9B")
    pt = v7_pilot.kv_per_token_f16("RWKV7-World-2.9B", None)
    assert pt == 0.0
    rows = v7_pilot.greedy_allocations(4.0, roster_limit=38)
    rwkv = [r for r in rows if r["family"] == "RWKV7-World-2.9B"]
    assert rwkv, "the recurrent family must earn cells"
    assert all(r["est_gib"] <= 4.0 for r in rwkv)


def test_mha_fallback_places_phi1():
    """phi-1's config has null kv_heads/head_dim (MHA shape): the
    hidden_size//heads fallback must place it, not drop it."""
    pt = v7_pilot.kv_per_token_f16("phi-1", None)
    assert pt and pt > 0
    rows = v7_pilot.greedy_allocations(4.0, roster_limit=38)
    assert any(r["family"] == "phi-1" for r in rows)
