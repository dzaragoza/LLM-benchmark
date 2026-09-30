"""Pin the addendum-90 refactor seams (addendum 87's contract style)."""

import argparse
import copy
import os

import code_edit
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


def _ladder_stub(monkeypatch, speed_results, fwe_results, caps=None):
    """Stub the two gates for run_ladder tests: speed_results and
    fwe_results map rung -> (ok, verdict); caps maps rung -> window."""
    caps = caps or {}

    def speed_pass(m, r, c, p, d):
        ok, v = speed_results[r]
        v = dict(v)
        v["window_cap"] = caps.get(r)
        worst = v.get("worst")
        if ok:
            v["ceiling_rung"] = worst is not None and 5.0 <= worst < 7.5
        return ok, v

    def fwe_pass(m, r, d, s, p):
        ok, v = fwe_results[r]
        v = dict(v)
        v["window_cap"] = caps.get(r)
        return ok, v

    monkeypatch.setattr(fb, "speed_pass", speed_pass)
    monkeypatch.setattr(fb, "fwe_pass", fwe_pass)


def test_run_ladder_fails_when_the_ceiling_is_below_the_start(tmp_path, monkeypatch):
    """Session 34 (addendum 19, refinement 4): any ceiling below the
    16k start rung - here a speed <5 fail AT the start - marks the run
    FAILED and the author investigates (a base failure, not a score)."""
    model = tmp_path / "X.gguf"
    model.write_bytes(b"fake")
    _ladder_stub(
        monkeypatch,
        speed_results={16384: (False, {"worst": 3.0})},
        fwe_results={},
    )
    ladder = fb.run_ladder(
        str(model),
        corpus=str(tmp_path / "corpus.json"),
        results_dir=str(tmp_path / "res"),
        min_rung=16384,
    )
    assert ladder["failed"] is True
    assert ladder["score"] == 0
    assert [c["rung"] for c in ladder["rungs"]] == [16384]


def test_run_ladder_window_from_the_banner_is_the_ceiling(tmp_path, monkeypatch):
    """Session 34 (addendum 19, refinement 2): THE PROBE IS GONE. The
    gallop's own launch caps the -c down (the banner says so) - the
    window becomes the ceiling and the fwe-only search resolves the
    score below it. 16k passes; 32k's speed launch reads window 20480."""
    model = tmp_path / "X.gguf"
    model.write_bytes(b"fake")
    _ladder_stub(
        monkeypatch,
        speed_results={
            16384: (True, {"worst": 9.0, "mem_cost_gib": 2.0}),
            32768: (False, {"error": "capped to the window"}),
        },
        fwe_results={
            16384: (True, {"depth": 16128, "correct": 1, "n": 1}),
            18432: (True, {"depth": 18176, "correct": 1, "n": 1}),
            18944: (True, {"depth": 18688, "correct": 1, "n": 1}),
            19456: (False, {"depth": 19200, "correct": 0, "n": 1}),
        },
        caps={32768: 20480},
    )
    ladder = fb.run_ladder(
        str(model),
        corpus=str(tmp_path / "corpus.json"),
        results_dir=str(tmp_path / "res"),
        min_rung=16384,
    )
    assert ladder["failed"] is False
    assert ladder["score"] == 18944
    assert [c["rung"] for c in ladder["rungs"]] == [16384, 32768, 18432, 19456, 18944]


def test_run_ladder_speed_fail_keeps_speed_in_the_search(tmp_path, monkeypatch):
    """Session 34 (addendum 19, refinement 3.1): a <5 w/s fail sets the
    ceiling and the binary search measures SPEED at every midpoint too
    (a midpoint below 5 w/s must not be scored). 16k passes both; 32k
    fails speed; every midpoint fails speed -> the score stays 16384."""
    model = tmp_path / "X.gguf"
    model.write_bytes(b"fake")
    _ladder_stub(
        monkeypatch,
        speed_results={
            16384: (True, {"worst": 9.0, "mem_cost_gib": 2.0}),
            32768: (False, {"worst": 3.0}),
            24576: (False, {"worst": 4.2}),
            20480: (False, {"worst": 4.8}),
            18432: (False, {"worst": 3.5}),
            17408: (False, {"worst": 4.0}),
            16896: (False, {"worst": 4.5}),
        },
        fwe_results={
            r: (True, {"depth": r - 256, "correct": 1, "n": 1})
            for r in (16384, 24576, 20480, 18432, 17408, 16896)
        },
    )
    ladder = fb.run_ladder(
        str(model),
        corpus=str(tmp_path / "corpus.json"),
        results_dir=str(tmp_path / "res"),
        min_rung=16384,
    )
    assert ladder["score"] == 16384
    assert ladder["failed"] is False


def test_run_ladder_fwe_fail_drops_speed_in_the_search(tmp_path, monkeypatch):
    """Session 34 (addendum 19, refinement 3.3): speed >= 7.5 passed at
    the ceiling rung, fwe failed - the midpoints' speed passes too, so
    the search is fwe-only. 16k passes both; 32k speed-passes, fwe
    fails; the search resolves 24576 (the rungs above it fail fwe)."""
    model = tmp_path / "X.gguf"
    model.write_bytes(b"fake")
    _ladder_stub(
        monkeypatch,
        speed_results={
            16384: (True, {"worst": 9.0, "mem_cost_gib": 2.0}),
            32768: (True, {"worst": 8.0, "mem_cost_gib": 2.4}),
        },
        fwe_results={
            16384: (True, {"depth": 16128, "correct": 1, "n": 1}),
            32768: (False, {"depth": 32512, "correct": 0, "n": 1}),
            24576: (True, {"depth": 24320, "correct": 1, "n": 1}),
            28672: (False, {"depth": 28416, "correct": 0, "n": 1}),
            26624: (False, {"depth": 26368, "correct": 0, "n": 1}),
            25600: (False, {"depth": 25344, "correct": 0, "n": 1}),
            25088: (False, {"depth": 24832, "correct": 0, "n": 1}),
        },
    )
    ladder = fb.run_ladder(
        str(model),
        corpus=str(tmp_path / "corpus.json"),
        results_dir=str(tmp_path / "res"),
        min_rung=16384,
    )
    assert ladder["score"] == 24576
    benched = [c["rung"] for c in ladder["rungs"]]
    assert benched == [16384, 32768, 24576, 28672, 26624, 25600, 25088]
    assert ladder["failed"] is False


def test_run_ladder_ceiling_rung_57_is_the_score_no_search(tmp_path, monkeypatch):
    """Session 34 (addendum 19, refinement 3.2): a 5<=w<7.5 pass at the
    gallop rung is the CEILING - speed is not measured anymore; the
    rung still needs fwe to pass to become the floor; deeper is slower
    still so NOTHING above is searched."""
    model = tmp_path / "X.gguf"
    model.write_bytes(b"fake")
    _ladder_stub(
        monkeypatch,
        speed_results={
            16384: (True, {"worst": 9.0, "mem_cost_gib": 2.0}),
            32768: (True, {"worst": 6.0, "mem_cost_gib": 2.4}),
        },
        fwe_results={
            16384: (True, {"depth": 16128, "correct": 1, "n": 1}),
            32768: (True, {"depth": 32512, "correct": 1, "n": 1}),
        },
    )
    ladder = fb.run_ladder(
        str(model),
        corpus=str(tmp_path / "corpus.json"),
        results_dir=str(tmp_path / "res"),
        min_rung=16384,
    )
    assert ladder["score"] == 32768
    assert [c["rung"] for c in ladder["rungs"]] == [16384, 32768]
    assert ladder["failed"] is False


def test_code_edit_replaces_and_syncs_to_disk(tmp_path):
    """Addendum 20: the editing tool writes the edit, fsyncs the file
    AND its directory, then re-reads to verify what is on disk."""
    p = tmp_path / "mod.py"
    p.write_text("def f():\n    return 1\n")
    code_edit.edit(str(p), [("replace", "return 1", "return 2")])
    with open(str(p)) as f:
        assert f.read() == "def f():\n    return 2\n"


def test_code_edit_fails_loud_on_missing_target(tmp_path):
    """Addendum 20: a bad block leaves the file UNTOUCHED."""
    p = tmp_path / "mod.py"
    p.write_text("def f():\n    return 1\n")
    try:
        code_edit.edit(str(p), [("replace", "return 99", "return 2")])
        raised = False
    except code_edit.CodeEditError:
        raised = True
    assert raised
    with open(str(p)) as f:
        assert f.read() == "def f():\n    return 1\n"


def test_code_edit_rejects_ambiguous_targets(tmp_path):
    """Addendum 20: two matches is an error, not a coin flip."""
    p = tmp_path / "mod.py"
    p.write_text("a = 1\nb = 1\n")
    try:
        code_edit.edit(str(p), [("replace", "= 1", "= 2")])
        raised = False
    except code_edit.CodeEditError as e:
        raised = "found 2 times" in str(e)
    assert raised
    with open(str(p)) as f:
        assert f.read() == "a = 1\nb = 1\n"


def test_code_edit_blocks_apply_in_order(tmp_path):
    """Addendum 20: a later block can rely on an earlier one; nothing
    is written unless EVERY block verifies first."""
    p = tmp_path / "mod.py"
    p.write_text("x = 1\n")
    code_edit.edit(
        str(p),
        [
            ("replace", "x = 1", "x = 2"),
            ("insert_after", "x = 2", "\ny = x + 1"),
        ],
    )
    with open(str(p)) as f:
        assert f.read() == "x = 2\ny = x + 1\n"


def test_code_edit_transaction_all_or_nothing(tmp_path):
    """Addendum 20: when the SECOND block fails verification, the FIRST
    block must not leak into the file either."""
    p = tmp_path / "mod.py"
    p.write_text("x = 1\nz = 3\n")
    try:
        code_edit.edit(
            str(p),
            [
                ("replace", "x = 1", "x = 2"),
                ("replace", "not there", "anything"),
            ],
        )
        raised = False
    except code_edit.CodeEditError:
        raised = True
    assert raised
    with open(str(p)) as f:
        assert f.read() == "x = 1\nz = 3\n"  # the first block did NOT apply


def test_code_edit_replace_all(tmp_path):
    """Addendum 20: replace_all changes EVERY occurrence (a deliberate
    multi-edit, not an ambiguous coin-flip)."""
    p = tmp_path / "mod.py"
    p.write_text("a = old\nb = old\nc = other\n")
    code_edit.edit(str(p), [("replace_all", "old", "new")])
    with open(str(p)) as f:
        assert f.read() == "a = new\nb = new\nc = other\n"


def test_code_edit_atomic_write_leaves_no_tempfiles(tmp_path):
    """Addendum 20: the atomic-write path cleans its temp file; the
    directory holds only the edited module."""
    p = tmp_path / "mod.py"
    p.write_text("a\n")
    code_edit.edit(str(p), [("replace", "a", "b")])
    assert sorted(os.listdir(str(tmp_path))) == ["mod.py"]
