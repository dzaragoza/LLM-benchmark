"""run_status tests (session 41, addendum 41): the live-status block is
idempotent, extracts the per-family verdicts correctly, and never
breaks the picker page's script."""

from __future__ import annotations

import run_status


def test_verdict_extraction_from_results(tmp_path, monkeypatch):
    """The per-family row: verdict, rung, and the kill task taken from
    the DEAD block IMMEDIATELY BEFORE the family's own verdict line
    (a later family's DEAD must not leak into an earlier family's row)."""
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


def test_render_is_idempotent_and_wellformed():
    """Rendering twice produces the same block, and the block carries
    the runStatus marker the page updater keys on."""
    rows = [
        {
            "name": "fam",
            "verdict": "DEAD",
            "rung": "4,096",
            "kill": "arc",
            "tally": "0/6",
        }
    ]
    b1 = run_status.render(rows)
    b2 = run_status.render(rows)
    assert b1 == b2
    assert 'id="runStatus"' in b1
    assert "fam" in b1 and "arc" in b1
