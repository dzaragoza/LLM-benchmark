"""run_status tests (session 41, addenda 41-43): the live-status page
extracts the per-family verdicts correctly (the kill task from the
DEAD block immediately before each family's own verdict line), the
per-gate kill rates scoped to the current pass, and renders a
well-formed standalone page."""

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


def test_gate_kill_rates_scoped_to_the_pass(tmp_path, monkeypatch):
    """The kill rates count ONLY the current f16 pass (the pass's first
    --force-rung f16 header is the scope start; older runs must not
    leak in), and the cells are counted per-CELL (the k/n in the cell
    lines is a running tally - never summed)."""
    results = tmp_path / "results.txt"
    results.write_text(
        # an OLDER run's history - must not count
        "===== 2026-10-02T10:00:00 | full_benchmark.py --tournament =====\n"
        "  DEAD - fwe cannot reach the bar at 4,096 (0/9, best lower bound"
        " 0.4 < 0.5); next candidate\n"
        "  cell 9 (rung 4,096) speed: 0 stalls -> PASS -> speed 9/9\n"
        # THIS pass
        "===== 2026-10-06T17:40:10 | full_benchmark.py --task all --force-rung f16 =====\n"
        "  cell 1 (rung 4,096) fwe: 3/1 word(s) -> PASS [8s] -> fwe 1/1\n"
        "  cell 2 (rung 4,096) fwe: 0/1 word(s) -> FAIL [8s] -> fwe 1/2\n"
        "  cell 3 (rung 4,096) vt: 5/5 names -> PASS [6s] -> vt 1/1\n"
        "  DEAD - vt cannot reach the bar at 4,096 (0/6, best lower bound"
        " 0.477 < 0.5); next candidate\n"
    )
    monkeypatch.setattr(run_status, "RESULTS", str(results))
    kr = run_status.gate_kill_rates()
    assert kr["fwe"]["kills"] == 0  # the old fwe kill must not count
    assert kr["fwe"]["passes"] == 1 and kr["fwe"]["measured"] == 2
    assert kr["vt"]["kills"] == 1
    assert kr["vt"]["passes"] == 1 and kr["vt"]["measured"] == 1
    assert kr["speed"]["measured"] == 0  # the old speed cell must not count


def test_render_is_a_standalone_page_with_gates():
    """The page carries the four gates' difficulty panel, the kill-rate
    panel, one row per family, and idempotence: rendering twice is
    identical."""
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


def test_infeasible_families_are_out_of_the_statistics(tmp_path, monkeypatch):
    """Addendum 45: a family whose trained window cannot run the rung
    (the addendum-130e cap error) is OUT of the benchmark - its cells
    (all FAIL-by-400) and its kill never enter the kill-rate panel,
    and its row says so."""
    results = tmp_path / "results.txt"
    results.write_text(
        "===== 2026-10-06T19:00:00 | full_benchmark.py --task all --force-rung f16 =====\n"
        "  cell 1 (rung 4,096) speed: 0 stall(s) in 5 turns -> PASS [30s] -> speed 1/1\n"
        "  cell 1 (rung 4,096) fwe: 2/1 word(s) -> PASS [7s] -> fwe 1/1\n"
        "  ERROR: server accepted -c 4352 but runs n_ctx 2048 (slots/cap "
        "silently reduced it, addendum 130e/130f) - the depth budget "
        "would overflow and every deep turn would 400\n"
        "  cell 2 (rung 4,096) speed: 0 stall(s) in 0 turns -> FAIL [1s] -> speed 1/2\n"
        "  cell 2 (rung 4,096) fwe: 0/1 word(s) -> FAIL [1s] -> fwe 1/2\n"
        "  DEAD - speed cannot reach the bar at 4,096 (1/2, best lower bound"
        " 0.4 < 0.5); next candidate\n"
        "[2026-10-06T19:01:00] verdict: capped-family DEAD at rung 4,096"
        " - committing partial results\n"
        "  cell 1 (rung 4,096) speed: 0 stall(s) in 5 turns -> PASS [30s] -> speed 1/1\n"
        "  DEAD - fwe cannot reach the bar at 4,096 (0/9, best lower bound"
        " 0.4 < 0.5); next candidate\n"
        "[2026-10-06T19:02:00] verdict: honest-family DEAD at rung 4,096"
        " - committing partial results\n"
    )
    monkeypatch.setattr(run_status, "RESULTS", str(results))
    inf = run_status.infeasible_families(run_status._pass_segment())
    assert list(inf) == ["capped-family"]
    kr = run_status.gate_kill_rates()
    # the capped family's block (its PASS cell AND its FAIL-by-400
    # cells and kill) never entered the counts - only the honest
    # family's one speed cell remains
    assert kr["speed"]["measured"] == 1 and kr["speed"]["passes"] == 1
    assert kr["speed"]["kills"] == 0
    assert kr["fwe"]["kills"] == 1
