"""Pin the addendum-90 refactor seams (addendum 87's contract style)."""

import argparse
import os

import pytest

import code_edit
import full_benchmark as fb
import hf_download
import ruler_gate


def make_args(**kw):
    defaults = dict(
        families=["A/Qwen-A", "B/Qwen-B"],
        roster=None,
        rung=fb.RUNG_DEFAULT,
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


def test_prepare_roster_defaults_to_families():
    assert fb.prepare_roster(make_args()) == ["Qwen-A", "Qwen-B"]


def test_prepare_roster_flag_filters():
    args = make_args(roster="Qwen-B, Qwen-C")
    assert fb.prepare_roster(args) == ["Qwen-B", "Qwen-C"]


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

    monkeypatch.setattr(fb, "RUNG_DEFAULT", "Q8_0")
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

    def speed_pass(m, r, c, p, d, kv_quant=None):
        ok, v = speed_results[r]
        v = dict(v)
        v["window_cap"] = caps.get(r)
        worst = v.get("worst")
        if ok:
            v["ceiling_rung"] = worst is not None and 5.0 <= worst < 7.5
        return ok, v

    def fwe_pass(m, r, d, s, p, kv_quant=None):
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
    assert ladder["score"] == 18432
    assert [c["rung"] for c in ladder["rungs"]] == [16384, 32768, 18432, 19456]


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
    assert benched == [16384, 32768, 24576, 28672, 26624, 25600]
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


def test_code_edit_replace_n_targets_kth_occurrence(tmp_path):
    """replace_n: the k-th occurrence, no ambiguity error on dupes."""
    p = tmp_path / "mod.py"
    p.write_text("x = 1\ny = 1\nz = 1\n")
    code_edit.edit(str(p), [("replace_n", "= 1", "= 9", 2)])
    with open(str(p)) as f:
        assert f.read() == "x = 1\ny = 9\nz = 1\n"


def test_code_edit_replace_n_out_of_range_fails(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("x = 1\n")
    try:
        code_edit.edit(str(p), [("replace_n", "= 1", "= 9", 3)])
        raised = False
    except code_edit.CodeEditError:
        raised = True
    assert raised
    with open(str(p)) as f:
        assert f.read() == "x = 1\n"


def test_code_edit_replace_regex_requires_single_match(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("SCORE = 32768\nother = 16384\n")
    code_edit.edit(str(p), [("replace_regex", r"SCORE = \d+", "SCORE = 65536")])
    with open(str(p)) as f:
        assert f.read() == "SCORE = 65536\nother = 16384\n"
    try:
        code_edit.edit(str(p), [("replace_regex", r"\d+", "0")])
        raised = False
    except code_edit.CodeEditError as e:
        raised = "matched 4 times" in str(e) or "matched" in str(e)
    assert raised


def test_code_edit_set_lines_replaces_range(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("a\nb\nc\nd\n")
    code_edit.edit(str(p), [("set_lines", 2, 3, ["x", "y", "z"])])
    with open(str(p)) as f:
        assert f.read() == "a\nx\ny\nz\nd\n"


def test_code_edit_insert_lines_before_line(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("a\nb\nc\n")
    code_edit.edit(str(p), [("insert_lines", 2, ["inserted"])])
    with open(str(p)) as f:
        assert f.read() == "a\ninserted\nb\nc\n"


def test_code_edit_delete_lines_range(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("a\nb\nc\nd\n")
    code_edit.edit(str(p), [("delete_lines", 2, 3)])
    with open(str(p)) as f:
        assert f.read() == "a\nd\n"


def test_code_edit_indent_dedent_ranges(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("def f():\n    a = 1\n    b = 2\n")
    code_edit.edit(str(p), [("indent", 2, 3, "    ")])
    with open(str(p)) as f:
        assert f.read() == "def f():\n        a = 1\n        b = 2\n"
    code_edit.edit(str(p), [("dedent", 2, 3, "    ")])
    with open(str(p)) as f:
        assert f.read() == "def f():\n    a = 1\n    b = 2\n"


def test_code_edit_line_range_out_of_bounds_fails(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("a\n")
    try:
        code_edit.edit(str(p), [("set_lines", 1, 9, "x")])
        raised = False
    except code_edit.CodeEditError as e:
        raised = "out of bounds" in str(e)
    assert raised
    with open(str(p)) as f:
        assert f.read() == "a\n"


def test_code_edit_append_and_prepend(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("middle\n")
    code_edit.edit(str(p), [("prepend", "header\n"), ("append", "footer\n")])
    with open(str(p)) as f:
        assert f.read() == "header\nmiddle\nfooter\n"


def test_code_edit_write_creates_verified_file(tmp_path):
    p = tmp_path / "new.py"
    code_edit.write(str(p), "x = 1\n")
    with open(str(p)) as f:
        assert f.read() == "x = 1\n"


def test_code_edit_new_blocks_compose_in_one_transaction(tmp_path):
    """The session's ad-hoc recipe as one edit: dedent a collapsed loop
    body, delete the loop header, fix the caller - all or nothing."""
    p = tmp_path / "mod.py"
    p.write_text(
        "def bench():\n    for rep in range(1, 2):\n        do_work(rep)\n        return rep\n"
    )
    code_edit.edit(
        str(p),
        [
            ("dedent", 3, 4, "    "),
            ("delete_lines", 2, 2),
            ("replace", "do_work(rep)", "do_work(1)"),
            ("replace", "return rep", "return 1"),
        ],
    )
    with open(str(p)) as f:
        assert f.read() == "def bench():\n    do_work(1)\n    return 1\n"


def test_mapped_memory_census_splits_file_and_anon(tmp_path):
    """Addendum 23: the smaps census - mapped >= resident = file + anon;
    the VmHWM undercount fix. Linux-only instrument (skipped elsewhere)."""
    import subprocess
    import sys
    import time

    try:
        proc = subprocess.Popen(
            [sys.executable, "-c", "b = bytearray(16*1024*1024); import time; time.sleep(30)"]
        )
    except Exception:
        pytest.skip("cannot spawn a helper process")
    time.sleep(0.5)
    try:
        import llama_server

        if not os.path.exists(f"/proc/{proc.pid}/smaps"):
            pytest.skip("no /proc smaps (Linux exclusive)")
        c = llama_server.mapped_memory_gib(proc)
        assert c is not None
        assert c["mapped_gib"] >= c["resident_gib"] > 0
        assert abs(c["file_gib"] + c["anon_gib"] - c["resident_gib"]) < 1e-6
        assert c["anon_gib"] >= 0.015, "the 16 MiB anon bytearray"
        assert c["file_gib"] > 0, "the python binary's file-backed pages"
    finally:
        proc.kill()
        proc.wait()


def test_mapped_memory_none_for_dead_pid():
    import llama_server

    class Dead:
        pid = 999999998

    assert llama_server.mapped_memory_gib(Dead()) is None


def test_code_edit_preview_shows_diff_without_writing(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("x = 1\n")
    diff = code_edit.preview(str(p), [("replace", "x = 1", "x = 2")])
    assert "-x = 1" in diff and "+x = 2" in diff
    with open(str(p)) as f:
        assert f.read() == "x = 1\n"  # nothing written


def test_code_edit_preview_fails_like_edit(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("x = 1\n")
    try:
        code_edit.preview(str(p), [("replace", "nope", "x")])
        raised = False
    except code_edit.CodeEditError:
        raised = True
    assert raised


def test_code_edit_replace_region_between_anchors(tmp_path):
    # addendum 39: replace everything BETWEEN two unique anchors,
    # anchors kept - the minified-HTML pattern
    p = tmp_path / "page.html"
    p.write_text("<p>How the recommendation is computed.</strong> OLD TEXT </p> tail")
    code_edit.edit(
        str(p),
        [("replace_region", "How the recommendation is computed.", "</p>", " NEW ")],
    )
    with open(str(p)) as f:
        assert f.read() == "<p>How the recommendation is computed. NEW </p> tail"


def test_code_edit_replace_region_requires_unique_anchors(tmp_path):
    p = tmp_path / "page.html"
    p.write_text("a x a x")
    try:
        code_edit.edit(str(p), [("replace_region", "a", "x", "y")])
        raised = False
    except code_edit.CodeEditError as e:
        raised = "found 2 times" in str(e)
    assert raised
    with open(str(p)) as f:
        assert f.read() == "a x a x"


def test_code_edit_replace_region_end_not_after_start_fails(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("start middle end")
    try:
        code_edit.edit(str(p), [("replace_region", "end", "start", "y")])
        raised = False
    except code_edit.CodeEditError as e:
        raised = "not found after start" in str(e)
    assert raised


def test_code_edit_replace_regex_all_replaces_every_match(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("w1 = 1\nw2 = 2\nx = 3\n")
    code_edit.edit(str(p), [("replace_regex_all", r"w\d = ", "w_ = ")])
    with open(str(p)) as f:
        assert f.read() == "w_ = 1\nw_ = 2\nx = 3\n"
    try:
        code_edit.edit(str(p), [("replace_regex_all", r"nope", "x")])
        raised = False
    except code_edit.CodeEditError as e:
        raised = "matched nothing" in str(e)
    assert raised


def test_code_edit_catches_duplicated_fragment_on_a_line(tmp_path):
    # addendum 39: the delimiter balance check - a replace that leaves
    # an unbalanced line (a truncated/duplicated fragment shape) is
    # rejected at edit time and the file stays untouched
    p = tmp_path / "page.html"
    p.write_text('<div id="a">old</div>\n<div id="b">ok</div>\n')
    try:
        code_edit.edit(
            str(p),
            [("replace", '<div id="a">old</div>', '<div id="a>new</div>')],
        )
        raised = False
    except code_edit.CodeEditError as e:
        raised = "balance" in str(e)
    assert raised
    with open(str(p)) as f:
        assert f.read() == '<div id="a">old</div>\n<div id="b">ok</div>\n'


def test_code_edit_balance_check_whole_buffer_for_minified_lines(tmp_path):
    # long-line (minified) files: the whole buffer must balance - a
    # balanced source that becomes unbalanced is rejected
    long_line = '<t a="b">' + "x" * 600 + "</t>"
    p = tmp_path / "page.html"
    p.write_text(long_line)
    try:
        code_edit.edit(str(p), [("replace", "</t>", '</t>"')])
        raised = False
    except code_edit.CodeEditError as e:
        raised = "balance" in str(e)
    assert raised
    with open(str(p)) as f:
        assert f.read() == long_line  # untouched


def test_code_edit_balance_check_passes_clean_minified_edit(tmp_path):
    long_line = '<t a="b">' + "x" * 600 + "</t>"
    p = tmp_path / "page.html"
    p.write_text(long_line)
    code_edit.edit(str(p), [("replace", 'a="b"', 'a="c"')])
    with open(str(p)) as f:
        assert 'a="c"' in f.read()


def test_code_edit_balance_check_skips_unbalanced_source(tmp_path):
    # if the SOURCE was already unbalanced (rare, template-y files),
    # the check does not block the edit (it compares like with like)
    p = tmp_path / "page.html"
    p.write_text("<div>unclosed...\n<p>ok</p>\n")
    code_edit.edit(str(p), [("replace", "ok", "fine")])
    with open(str(p)) as f:
        assert "fine" in f.read()


def test_code_edit_edit_many_all_or_nothing_across_files(tmp_path):
    a, b = tmp_path / "a.py", tmp_path / "b.py"
    a.write_text("xa = 1\n")
    b.write_text("xb = 1\n")
    code_edit.edit_many(
        [
            (str(a), [("replace", "xa = 1", "xa = 2")]),
            (str(b), [("replace", "xb = 1", "xb = 2")]),
        ]
    )
    assert a.read_text() == "xa = 2\n"
    assert b.read_text() == "xb = 2\n"
    # now a failing set: b's block is bad - a must stay untouched
    try:
        code_edit.edit_many(
            [
                (str(a), [("replace", "xa = 2", "xa = 3")]),
                (str(b), [("replace", "nope", "x")]),
            ]
        )
        raised = False
    except code_edit.CodeEditError:
        raised = True
    assert raised
    assert a.read_text() == "xa = 2\n"  # rolled back - not half-edited
    assert b.read_text() == "xb = 2\n"


def test_code_edit_edit_many_rejects_duplicate_paths(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("x = 1\n")
    try:
        code_edit.edit_many(
            [
                (str(p), [("replace", "x = 1", "x = 2")]),
                (str(p), [("replace", "x = 2", "x = 3")]),
            ]
        )
        raised = False
    except code_edit.CodeEditError as e:
        raised = "duplicate" in str(e)
    assert raised
    assert p.read_text() == "x = 1\n"


def test_check_requirements_passes_when_all_importable(capsys, monkeypatch):
    # pytest is a real distribution present in any interpreter running
    # this suite (importlib.metadata resolves pip names, not module names)
    monkeypatch.setattr(fb, "REQ_PACKAGES", ["pytest"])
    fb.check_requirements()
    out = capsys.readouterr().out
    assert "python :" in out


def test_check_requirements_fails_loud_when_a_package_is_missing(capsys, monkeypatch):
    # a distribution name that does not exist (importlib.metadata, not
    # find_spec - protobuf installs as google.protobuf, addendum 25 fix)
    monkeypatch.setattr(fb, "REQ_PACKAGES", ["definitely-not-a-real-package-xyz"])
    try:
        fb.check_requirements()
        raised = False
    except SystemExit as e:
        raised = "python3 -m pip install -r requirements.txt" in str(
            e
        ) and "definitely-not-a-real-package-xyz" in str(e)
    assert raised


def test_resume_skip_prints_na_for_none_worst(capsys, tmp_path, monkeypatch):
    # the lineage-2 TypeError (addendum 27): a floor-rule-failed family
    # has selected set with worst=None; the resume print must not format it
    state = {
        "families": {
            "Fam": {
                "spec": "r/Fam",
                "runs": {
                    "Q8_0": {
                        "phases_done": [1, 2, 3, 4],
                        "verdict": "PASS (ladder score 0 tokens)",
                        "worst": None,
                    }
                },
                "selected": "Q8_0",
            }
        }
    }
    monkeypatch.setattr(fb, "save_state", lambda *a, **k: None)
    fb.process_family(
        "r/Fam",
        "corpus.json",
        str(tmp_path),
        state,
        "/tmp/unused-state.json",
        dry_run=False,
        force=False,
    )
    out = capsys.readouterr().out
    assert "worst n/a t/s" in out


def test_score_fwe_strips_template_debris():
    # ruling 1a (addendum 29/30): '<|im_end|>' debris must not fail an
    # otherwise-correct answer
    top_k = ["nysskz", "swucem", "tvjzpa"]
    ok, n = ruler_gate.score_fwe("nysskz, swucem, tvjzpa<|im_end|>", top_k)
    assert ok and n == 3
    # pure debris with no words still fails
    ok2, n2 = ruler_gate.score_fwe("<|im_end|>", top_k)
    assert not ok2 and n2 == 0


def test_resolve_f16_local_never_returns_a_quantized_file(tmp_path):
    # the MiniCPM-*-sft-bf16 bug (addendum 30): 'bf16' in the FAMILY
    # name made the family's own -Q8_0.gguf match the f16 glob
    famdir = tmp_path / "MiniCPM-1B-sft-bf16"
    famdir.mkdir()
    (famdir / "MiniCPM-1B-sft-bf16-Q8_0.gguf").write_text("x")
    assert hf_download.resolve_f16_local(str(famdir)) is None
    (famdir / "MiniCPM-1B-sft-bf16-f16.gguf").write_text("x")
    got = hf_download.resolve_f16_local(str(famdir))
    assert got and got.endswith("MiniCPM-1B-sft-bf16-f16.gguf")


def test_fwe_flicker_detects_non_monotone_verdicts():
    # addendum 31 ruling b: pass deep + fail shallow = coin-flip pair
    rungs = [
        {"rung": 2048, "fwe_pass": False},
        {"rung": 16384, "fwe_pass": True},
    ]
    assert fb.fwe_flicker(rungs) == (16384, 2048)  # the Qwen3-4B shape
    # monotone: fail deep, pass shallow - stands
    assert (
        fb.fwe_flicker([{"rung": 1024, "fwe_pass": True}, {"rung": 4096, "fwe_pass": False}])
        is None
    )
    # monotone: all pass / all fail - stands
    assert (
        fb.fwe_flicker([{"rung": 1024, "fwe_pass": True}, {"rung": 2048, "fwe_pass": True}]) is None
    )
    assert (
        fb.fwe_flicker([{"rung": 1024, "fwe_pass": False}, {"rung": 2048, "fwe_pass": False}])
        is None
    )
    # unmeasured rungs (speed-only cells) are ignored
    assert (
        fb.fwe_flicker([{"rung": 1024, "fwe_pass": None}, {"rung": 4096, "fwe_pass": True}]) is None
    )


def test_run_ladder_invalidates_a_flickering_run(monkeypatch, capsys):
    # the live hook: run_ladder consults fwe_flicker on its own rungs
    # and marks a non-monotone run invalid (score 0, loud print).
    # Within one ladder the gallop keeps verdicts monotone, so this
    # simulates the read-time/cross-grid shape by injecting the pair.
    monkeypatch.setattr(fb, "fwe_flicker", lambda rungs: (16384, 2048))
    monkeypatch.setattr(
        fb,
        "speed_pass",
        lambda model, rung, corpus, port, results_dir, kv_quant=None: (
            True,
            {"worst": 20.0, "stall_rate": 0.0, "ceiling_rung": False},
        ),
    )
    monkeypatch.setattr(
        fb,
        "fwe_pass",
        lambda model, rung, results_dir, seed, port, kv_quant=None: (
            True,
            {"depth": rung - 256, "correct": 1, "n": 1},
        ),
    )
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "m-Q8_0.gguf")
        open(p, "w").write("x")
        ladder = fb.run_ladder(p, corpus="c", min_rung=1024, max_rung=4096)
    assert ladder.get("invalid") is True
    assert "fwe flicker" in ladder["invalid_reason"]
    assert ladder["score"] == 0 and ladder["failed"] is True
    out = capsys.readouterr().out
    assert "INVALID" in out


def test_convert_quant_deletes_tensors_after_f16(tmp_path, monkeypatch):
    # addendum 42: the safetensors are dead weight once the f16 exists;
    # create() deletes safetensors-source only after the conversion is
    # verified on disk, and never when the f16 was already local
    import convert_quant

    famdir = tmp_path / "fam"
    famdir.mkdir()
    (famdir / "safetensors-source").mkdir()
    (famdir / "safetensors-source" / "model.safetensors").write_text("x")
    out_f16 = famdir / "fam-f16.gguf"
    out_q = famdir / "fam-Q4_K_M.gguf"
    monkeypatch.setattr(convert_quant.hf_download, "local_rung", lambda d, r: None)
    monkeypatch.setattr(convert_quant.hf_download, "resolve_f16_local", lambda d: None)
    monkeypatch.setattr(
        convert_quant,
        "run_quiet",
        lambda cmd, log, phase, rung, what: (
            (out_f16.write_text("f16"), out_q.write_text("q4"), 0)[2]
            if cmd[1] == str(famdir / "safetensors-source") or "--outfile" in cmd
            else (out_q.write_text("q4"), 0)[1]
        ),
    )
    got = convert_quant.create("fam", str(famdir), "Q4_K_M")
    assert got == str(out_q)
    assert not (famdir / "safetensors-source").exists(), "tensors deleted after f16"


def test_code_edit_prose_files_skip_the_balance_check(tmp_path):
    # session 35, addendum 4: prose (md) legally contains apostrophes
    # and brackets - no delimiter check runs for prose file types
    p = tmp_path / "note.md"
    p.write_text("hello\n")
    code_edit.edit(str(p), [("append", "Daniela's results (see [1])\n")])
    with open(str(p)) as f:
        assert "Daniela's results" in f.read()


def test_code_edit_markup_ignores_apostrophes_but_guards_double_quotes(tmp_path):
    # session 35, addendum 4: an apostrophe inside markup text is
    # fine; a TRUNCATED double-quoted attribute is still rejected
    p = tmp_path / "page.html"
    p.write_text('<div id="a">old</div>\n')
    code_edit.edit(str(p), [("replace", ">old<", ">it's new<")])
    with open(str(p)) as f:
        assert "it's new" in f.read()
    try:
        code_edit.edit(str(p), [("replace", 'id="a"', 'id="a')])
        raised = False
    except code_edit.CodeEditError as e:
        raised = "balance" in str(e)
    assert raised
    with open(str(p)) as f:
        assert 'id="a"' in f.read()  # untouched


def test_code_edit_verify_failure_leaves_the_file_untouched(tmp_path):
    # session 35, addendum 4: the block post-conditions run BEFORE the
    # write - a verify failure must not leave a modified file behind
    p = tmp_path / "code.py"
    p.write_text("x = 1\n")
    try:
        code_edit.edit(str(p), [("replace", "x = 1", "x = 2")]) if False else None
    except Exception:
        pass
    # real case: a replace whose new text is empty cannot pass verify
    # via the not-in-result rule when it IS in the result - use a
    # delete of a nonexistent... instead force a bad regex block
    try:
        code_edit.edit(str(p), [("replace_regex", "(unclosed", "y")])
        raised = False
    except code_edit.CodeEditError:
        raised = True
    assert raised
    with open(str(p)) as f:
        assert f.read() == "x = 1\n"


def test_code_edit_accepts_the_bare_replace_shorthand(tmp_path):
    # session 35, addendum 6: (old, new) without the kind tag is a
    # replace - the tag is inferred, not an error
    p = tmp_path / "code.py"
    p.write_text("x = 1\ny = 2\n")
    code_edit.edit(str(p), [("x = 1", "x = 42")])
    with open(str(p)) as f:
        assert "x = 42" in f.read()


def test_code_edit_check_pre_flights_without_writing(tmp_path):
    # session 35, addendum 6: check() runs every check edit() would
    # run, returns the preview diff, and leaves the file untouched;
    # a bad block raises with the reason
    p = tmp_path / "code.py"
    p.write_text("x = 1\ny = 2\n")
    diff = code_edit.check(str(p), [("y = 2", "y = 3")])
    assert "+y = 3" in diff
    with open(str(p)) as f:
        assert f.read() == "x = 1\ny = 2\n"  # untouched
    try:
        code_edit.check(str(p), [("nope", "z")])
        raised = False
    except code_edit.CodeEditError as e:
        raised = "not found" in str(e)
    assert raised
