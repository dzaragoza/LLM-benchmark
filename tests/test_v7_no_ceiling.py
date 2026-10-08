"""Pins: R-25 (session 44, addendum 124). No wall-clock ceiling.

The author: "Remove the ceiling. Adjusting the number of questions
is the correct fix." A budget stop would truncate a cell and hide
its true runtime; the question count (K, SPANS) is the only runtime
knob. run_cell asks every reachable question, and the record reports
wall_seconds - the honest price, never a silent truncation.
"""

import bench.v7 as v7


def test_no_budget_constant():
    assert not hasattr(v7, "CELL_BUDGET_SECONDS"), "addendum 124: the ceiling is removed"


def test_run_cell_records_wall_seconds(monkeypatch, tmp_path):
    """The record reports the wall time it took - the honest price."""
    corpus = {"sentences": ["x"], "questions": [], "cuts": {}, "s_max": 1}
    monkeypatch.setattr(v7.ruler_gate, "ask", lambda *a, **k: "")
    rec = v7.run_cell(0, corpus, window=1024)
    assert "wall_seconds" in rec and rec["wall_seconds"] >= 0.0
    assert "budget_hit" not in rec, "the truncation flag died with the ceiling"
