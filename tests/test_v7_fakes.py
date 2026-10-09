"""Pins: R-31 (session 45, addendum 150) - the certify_v7 loop, covered
OFFLINE by fakes: the launch/preflight/score/teardown/census flow that
previously only a live GPU run exercised (addendum 108 flagged it as the
coverage hole; the addendum-112 discipline holds - fakes cover CONTROL
FLOW, never the measurement contract, so preflight keeps its live
/tokenize call in production and the fakes stub only the loop seams).

FakeServer: stands in for llama_server (start/stop/health/memory
breakdown); fake acquire; fake corpus; fake run_cell. The tests then
cover: the happy loop with census attached, server-not-coming-up,
template malfunction labelling, preflight overflow, run_cell failure,
acquire failure, config drift re-measure, and the answers-path
wiring - every branch of the loop, no GPU.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bench.v7 as v7m

FAKE_CENSUS = {
    "source": "fake (offline loop test)",
    "weights_gib": 1.0,
    "context_gib": 0.1,
    "compute_gib": 0.05,
    "total_gib": 1.15,
    "devices": {},
}


def _install(monkeypatch, tmp_path, *, run_cell=None, probe=None, acquire="/tmp/x.gguf"):
    """Wire the full fake seam set; returns the collected server calls."""
    calls: dict = {"stopped": 0, "answers": None}

    def cell(fam, ctx, est):
        return {
            "family": fam,
            "params_b": 0.3,
            "ctx": ctx,
            "wq": "F16",
            "kq": "f16",
            "vq": "f16",
            "est_gib": est,
        }

    monkeypatch.setattr(
        v7m,
        "climb_allocations",
        lambda b, limit=4, policy="greedy", report_unplaceable=False: [
            cell("famA", 4096, 1.0),
            cell("famA", 8192, 1.2),
        ],
    )
    monkeypatch.setattr(v7m, "_acquire_missing_model", lambda *a, **k: acquire)
    monkeypatch.setattr(
        v7m,
        "corpus_from_artifact",
        lambda port: {"questions": [], "cuts": {}, "sentences": []},
    )
    monkeypatch.setattr(
        v7m.llama_server,
        "start_server",
        lambda gguf, port, extra_args=None, log_path=None: (object(), True),
    )
    monkeypatch.setattr(
        v7m.llama_server,
        "wait_healthy",
        lambda port, proc=None: True,
    )
    monkeypatch.setattr(
        v7m.llama_server,
        "stop_server",
        lambda proc, port: calls.__setitem__("stopped", calls["stopped"] + 1),
    )
    monkeypatch.setattr(
        v7m.llama_server, "memory_breakdown_gib", lambda log_path: dict(FAKE_CENSUS)
    )
    monkeypatch.setattr(v7m, "preflight_reachable_grades", lambda port, c, w: {})
    monkeypatch.setattr(
        v7m,
        "preflight_template_sanity",
        lambda port: (_ for _ in ()).throw(probe) if probe else None,
    )
    monkeypatch.setattr(
        v7m,
        "run_cell",
        run_cell
        or (lambda port, corpus, window, answers_path=None: {"score": 0.5, "max_score": 3}),
    )
    monkeypatch.setattr(v7m, "save_state", lambda *a: None)
    return calls


def test_happy_loop_with_census(tmp_path, monkeypatch):
    """The full happy path offline: two cells measured, census attached
    to each record, state written per cell, both servers stopped."""
    calls = _install(monkeypatch, tmp_path)
    state = {"families": {}}
    res = v7m.certify_v7(str(tmp_path), state, str(tmp_path / "st.json"), 8210, 4, False)
    assert len(res) == 2
    assert all(e["score"] == 0.5 for e in res)
    assert all(e.get("mem_census") == FAKE_CENSUS for e in res)
    assert calls["stopped"] == 2
    assert state["families"]["famA"]["v7"]["4096"]["score"] == 0.5


def test_server_never_comes_up(tmp_path, monkeypatch):
    """The launch-failure branch: entry carries the error, no score,
    the loop moves on to the next cell."""

    def cell(fam, ctx, est):
        return {
            "family": fam,
            "params_b": 0.3,
            "ctx": ctx,
            "wq": "F16",
            "kq": "f16",
            "vq": "f16",
            "est_gib": est,
        }

    monkeypatch.setattr(
        v7m,
        "climb_allocations",
        lambda b, limit=4, policy="greedy", report_unplaceable=False: [cell("famA", 4096, 1.0)],
    )
    monkeypatch.setattr(v7m, "_acquire_missing_model", lambda *a, **k: "/tmp/x.gguf")
    monkeypatch.setattr(
        v7m, "corpus_from_artifact", lambda port: {"questions": [], "cuts": {}, "sentences": []}
    )
    monkeypatch.setattr(
        v7m.llama_server,
        "start_server",
        lambda gguf, port, extra_args=None, log_path=None: (object(), False),
    )
    monkeypatch.setattr(v7m.llama_server, "wait_healthy", lambda port, proc=None: False)
    monkeypatch.setattr(v7m.llama_server, "stop_server", lambda proc, port: None)
    monkeypatch.setattr(v7m, "save_state", lambda *a: None)
    state = {"families": {}}
    res = v7m.certify_v7(str(tmp_path), state, str(tmp_path / "st.json"), 8210, 4, False)
    assert res[0]["error"] == "server did not come up"
    assert res[0].get("score") is None


def test_template_malfunction_labels_cell(tmp_path, monkeypatch):
    """The addendum-140 branch: the PINEAPPLE probe throws, the cell
    is labelled and skipped, never scored 0."""
    _install(monkeypatch, tmp_path, probe=v7m.TemplateMalfunction("echo loop"))
    state = {"families": {}}
    res = v7m.certify_v7(str(tmp_path), state, str(tmp_path / "st.json"), 8210, 4, False)
    assert "template_malfunction" in res[0]["error"]
    assert res[0].get("score") is None


def test_preflight_overflow_labels_cell(tmp_path, monkeypatch):
    """The addendum-112 branch: a PreflightError labels the cell and
    the loop continues - reported per cell, never a crash."""
    _install(monkeypatch, tmp_path, probe=v7m.PreflightError("prompt exceeds window"))
    state = {"families": {}}
    res = v7m.certify_v7(str(tmp_path), state, str(tmp_path / "st.json"), 8210, 4, False)
    assert "preflight" in res[0]["error"]


def test_run_cell_failure_isolated(tmp_path, monkeypatch):
    """The addendum-111 branch: a run_cell crash is isolated into
    entry error; one bad cell never kills the run."""

    def boom(port, corpus, window, answers_path=None):
        raise RuntimeError("server exploded mid-cell")

    _install(monkeypatch, tmp_path, run_cell=boom)
    state = {"families": {}}
    res = v7m.certify_v7(str(tmp_path), state, str(tmp_path / "st.json"), 8210, 4, False)
    assert "run_cell failed" in res[0]["error"]


def test_acquire_failure_labels_cell(tmp_path, monkeypatch):
    """The acquire-failure branch: no gguf -> error entry, no launch."""

    def cell(fam, ctx, est):
        return {
            "family": fam,
            "params_b": 0.3,
            "ctx": ctx,
            "wq": "F16",
            "kq": "f16",
            "vq": "f16",
            "est_gib": est,
        }

    monkeypatch.setattr(
        v7m,
        "climb_allocations",
        lambda b, limit=4, policy="greedy", report_unplaceable=False: [cell("famA", 4096, 1.0)],
    )
    monkeypatch.setattr(v7m, "_acquire_missing_model", lambda *a, **k: None)
    monkeypatch.setattr(v7m, "save_state", lambda *a: None)
    state = {"families": {}}
    res = v7m.certify_v7(str(tmp_path), state, str(tmp_path / "st.json"), 8210, 4, False)
    assert res[0]["error"] == "could not acquire the quant"


def test_config_drift_remeasures(tmp_path, monkeypatch):
    """The addendum-134 branch: a stored cell whose quants drift from
    the plan is wiped and re-measured (the printed drift line)."""
    _install(monkeypatch, tmp_path)
    state = {
        "families": {
            "famA": {"v7": {"4096": {"score": 9.9, "wq": "Q2_K", "kq": "q4_0", "vq": "q4_0"}}}
        }
    }
    res = v7m.certify_v7(str(tmp_path), state, str(tmp_path / "st.json"), 8210, 4, False)
    assert res[0]["score"] == 0.5, "the drifted cell re-measured"
    assert state["families"]["famA"]["v7"]["4096"]["score"] == 0.5
