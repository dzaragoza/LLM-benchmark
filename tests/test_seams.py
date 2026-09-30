"""Pin the addendum-90 refactor seams (addendum 87's contract style)."""

import argparse
import copy

import full_benchmark as fb


def make_args(**kw):
    defaults = dict(
        families=["A/Qwen-A", "B/Qwen-B"],
        roster=None,
        arc_config="ARC-Challenge",
        arc_num=1172,
        arc_results_dir="arc-results-test",
        state_file="/tmp/unused-state.json",
        results_file="/tmp/unused-results.json",
    )
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def make_state():
    run_a = {
        "verdict": "PASS",
        "file": "./models/Qwen-A/A-Q8_0.gguf",
        "words_per_token_p05": 0.41,
    }
    run_b = {
        "verdict": "FAIL",
        "file": "./models/Qwen-B/B-Q8_0.gguf",
        "words_per_token_p05": 0.41,
    }
    return {
        "families": {
            "Qwen-A": {"spec": "A/Qwen-A", "selected": "Q8_0", "runs": {"Q8_0": run_a}},
            "Qwen-B": {"spec": "B/Qwen-B", "selected": None, "runs": {"Q8_0": run_b}},
            "Qwen-C": {
                "spec": "C/Qwen-C",
                "selected": None,
                "runs": {"Q8_0": {"verdict": "FAIL (infeasible: RAM)", "file": None}},
            },
        }
    }


def test_prepare_phase56_roster_defaults_to_families():
    roster, _, _ = fb.prepare_phase56(make_args(), make_state())
    assert roster == ["Qwen-A", "Qwen-B"]


def test_prepare_phase56_selections_only_selected_with_file():
    _, selections, _ = fb.prepare_phase56(make_args(), make_state())
    assert list(selections) == ["Qwen-A"]


def test_prepare_phase56_arc_jobs_skip_infeasible():
    _, _, arc_jobs = fb.prepare_phase56(make_args(), make_state())
    assert [(f, r) for f, r, _ in arc_jobs] == [
        ("Qwen-A", "Q8_0"),
        ("Qwen-B", "Q8_0"),
    ]


def test_prepare_phase56_roster_flag_filters():
    args = make_args(roster="Qwen-B, Qwen-C")
    roster, selections, arc_jobs = fb.prepare_phase56(args, make_state())
    assert roster == ["Qwen-B", "Qwen-C"]
    assert selections == {}
    assert [(f, r) for f, r, _ in arc_jobs] == [("Qwen-B", "Q8_0")]


def test_prepare_phase56_does_not_mutate_state():
    state = make_state()
    snapshot = copy.deepcopy(state)
    fb.prepare_phase56(make_args(), state)
    assert state == snapshot


def test_run_ranking_uses_selected_only_and_records(tmp_path):
    calls = []

    class FakeMcnemar:
        @staticmethod
        def rank(labels, arc_num, results_dir):
            calls.append(list(labels))
            return list(labels), {m: 0.5 for m in labels}, {}

    fb_mcnemar = fb.mcnemar
    fb.mcnemar = FakeMcnemar()  # ty: ignore[invalid-assignment]
    try:
        state = make_state()
        _, selections, _ = fb.prepare_phase56(make_args(), state)
        args = make_args(state_file=str(tmp_path / "s.json"))
        fb.run_ranking(args, state, selections)
    finally:
        fb.mcnemar = fb_mcnemar
    assert calls == [["Qwen-A Q8_0"]]
    assert state["ranking"]["order"] == ["Qwen-A Q8_0"]
    assert state["ranking"]["scores"]["Qwen-A Q8_0"] == 0.5


def test_preflight_report_exit_code():
    """The dry run exits non-zero iff families failed (author ruling,
    addendum 108): the report is a gate, its status must be scriptable."""
    state = {"families": {}}
    ok = fb.preflight_report(make_args(dry_run=True), state, failed_families=[])
    bad = fb.preflight_report(
        make_args(dry_run=True),
        state,
        failed_families=[("X/Qwen-X", "AssertionError()")],
    )
    assert ok == 0
    assert bad == 1


def test_dry_run_no_local_file_does_not_assert(tmp_path, monkeypatch, capsys):
    """The addendum-108 bug class: on a dry run, a family with no local
    rung file (the network-acquisition case) must reach the would-bench
    prints - the path-is-None assert is a REAL-run invariant and must
    not fire before the dry-run guard."""
    import hf_download

    monkeypatch.setattr(fb, "RUNG", "Q8_0")
    monkeypatch.setattr(hf_download, "require_hub", lambda: None)
    monkeypatch.setattr("full_benchmark.list_repo_files", lambda repo: ["model.safetensors"])
    monkeypatch.setattr("full_benchmark.local_rung", lambda famdir, rung: None)
    monkeypatch.setattr(
        "full_benchmark.convert_quant.create",
        lambda fam, famdir, rung, plan="", dry_run=False: None,
    )
    state = {"families": {}}
    famdir = tmp_path / "Qwen-X"
    famdir.mkdir()
    fb.process_family(
        "X/Qwen-X",
        corpus=str(tmp_path / "corpus.json"),
        models_dir=str(tmp_path),
        state=state,
        state_path=str(tmp_path / "state.json"),
        dry_run=True,
        force=False,
    )
    out = capsys.readouterr().out
    assert "[3] would run the PROTOCOL v4 ladder" in out


def test_local_rung_shortcut_skips_the_hub(tmp_path, capsys, monkeypatch):
    """Session 34 (addendum 4): a rung file already on disk means
    acquisition is DONE - phases 1-2 marked from the local file, no
    require_hub call, no repo listing. The hub is only a dependency
    when the file must be acquired remotely."""

    famdir = tmp_path / "Qwen-X"
    famdir.mkdir()
    (famdir / "Qwen-X-Q8_0.gguf").write_bytes(b"fake")
    (tmp_path / "corpus.json").write_text("{}")
    state = {"families": {}}

    def _hub_must_not_run() -> None:
        raise AssertionError("hub required")

    monkeypatch.setattr(fb.hf_download, "require_hub", _hub_must_not_run)
    fb.process_family(
        "X/Qwen-X",
        corpus=str(tmp_path / "corpus.json"),
        models_dir=str(tmp_path),
        state=state,
        state_path=str(tmp_path / "state.json"),
        dry_run=True,
        force=False,
    )
    run = state["families"]["Qwen-X"]["runs"]["Q8_0"]
    assert 1 in run["phases_done"] and 2 in run["phases_done"]
    assert run["plan"] == "local file"
    out = capsys.readouterr().out
    assert "no download needed" in out
