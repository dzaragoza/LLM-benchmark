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
