"""run_status tests (session 41, addenda 41/42): the live-status page
extracts the per-family verdicts correctly (the kill task from the
DEAD block immediately before each family's own verdict line - a
later family's DEAD must not leak into an earlier family's row), and
renders a well-formed standalone page."""

from __future__ import annotations

import run_status


def test_verdict_extraction_from_results(tmp_path, monkeypatch):
    results = tmp_path / "results.txt"
    results.write_text(
        "  some log\n"
        "  DEAD - fwe cannot reach the bar at 4,096 (0/6, best lower bound"
        " 0.477 < 0.5); next candidate\n"
        "[2026-10-06T17:43:54] verdict: granite-4.0-h-350m DEAD at rung 4,096"
        " - committing partial results\n"
        "  DEAD - arc cannot reach the bar at 4,096 (2/8, best lower bound"
        " 0.477 < 0.5); next candidate\n"
        "[2026-10-06T17:47:02] verdict: Qwen3.5-0.8B DEAD at rung 4,096 -"
        " committing partial results\n"
    )
    state = tmp_path / "state"
    state.mkdir()
    (state / "benchmark-state.json").write_text(
        '{"families": {"granite-4.0-h-350m": {}, "Qwen3.5-0.8B": {}}}'
    )
    monkeypatch.setattr(run_status, "STATE", str(state / "benchmark-state.json"))
    monkeypatch.setattr(run_status, "RESULTS", str(results))
    rows = run_status.family_rows()
    by_name = {r["name"]: r for r in rows}
    # granite's kill is the fwe block BEFORE its own verdict - not the
    # arc block of the LATER family
    assert by_name["granite-4.0-h-350m"]["kill"] == "fwe"
    assert by_name["granite-4.0-h-350m"]["tally"] == "0/6"
    assert by_name["granite-4.0-h-350m"]["verdict"] == "DEAD"
    assert by_name["Qwen3.5-0.8B"]["kill"] == "arc"
    assert by_name["Qwen3.5-0.8B"]["tally"] == "2/8"


def test_render_is_a_standalone_page_with_gates():
    """The page carries the four gates' difficulty panel, one row per
    family, and the idempotence: rendering twice is identical."""
    rows = [
        {
            "name": "fam",
            "verdict": "DEAD",
            "rung": "4,096",
            "kill": "arc",
            "tally": "0/6",
        },
        {"name": "climber", "verdict": "climbing", "rung": "", "kill": "", "tally": ""},
    ]
    b1 = run_status.render(rows)
    b2 = run_status.render(rows)
    assert b1 == b2
    assert b1.startswith("<!doctype html>")
    assert "difficulty" in b1 and "2 sigma" in b1
    for gate in ("speed", "fwe", "vt", "arc"):
        assert gate in b1
    assert "fam" in b1 and "climber" in b1
