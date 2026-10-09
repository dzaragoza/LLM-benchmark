"""Pin the addendum-90 refactor seams (addendum 87's contract style)."""
import argparse
import os
import sys

# mutmut's staging dir does not run the repo-root conftest.py, so the bare
# root-module imports (code_edit, full_benchmark, infra.*) resolve only when
# the paths are set explicitly (addenda 175/178 - the mutation-stats run
# crashed on each import in turn; both dirs go on the path).
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "AI_tools"))
sys.path.insert(0, os.path.join(_HERE, ".."))

import code_edit  # noqa: E402  (path setup above must precede it)
import full_benchmark as fb  # noqa: E402
import infra.hf_download as hf_download  # noqa: E402
import ruler_gate  # noqa: E402


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


def test_code_edit_insert_forces_newline_at_join(tmp_path):
    """Session 35, addendum 9 (register entry 6): insert_after with a
    multi-line anchor whose last line has no trailing newline fused the
    inserted text onto the anchor's last line, corrupting the file.
    The separator is forced; an explicit \n in the new text is kept."""
    p = tmp_path / "mod.py"
    p.write_text("def f():\n    x = 1\n")
    code_edit.edit(
        str(p),
        [
            (
                "insert_after",
                "def f():\n    x = 1",
                "\ndef g():\n    pass",
            )
        ],
    )
    with open(str(p)) as f:
        assert f.read() == "def f():\n    x = 1\ndef g():\n    pass\n"


def test_code_edit_insert_no_double_newline_when_new_starts_with_one(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("x = 1\n")
    code_edit.edit(str(p), [("insert_after", "x = 1", "\ny = 2")])
    with open(str(p)) as f:
        assert f.read() == "x = 1\ny = 2\n"


def test_code_edit_insert_before_forces_newline_at_join(tmp_path):
    p = tmp_path / "mod.py"
    p.write_text("x = 1\n")
    code_edit.edit(str(p), [("insert_before", "x = 1", "y = 0")])
    with open(str(p)) as f:
        assert f.read() == "y = 0\nx = 1\n"


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


def test_score_fwe_strips_template_debris():
    # ruling 1a (addendum 29/30): '<|im_end|>' debris must not fail an
    # otherwise-correct answer
    top_k = ["nysskz", "swucem", "tvjzpa"]
    ok, n = ruler_gate.score_fwe("nysskz, swucem, tvjzpa<|im_end|>", top_k)
    assert ok and n == 3
    # pure debris with no words still fails
    ok2, n2 = ruler_gate.score_fwe("<|im_end|>", top_k)
    assert not ok2 and n2 == 0


def test_score_fwe_one_third_pass_rule():
    # session 37, addendum 2 ruling (a): 1/3 or higher passes
    top_k = ["nysskz", "swucem", "tvjzpa"]
    ok, n = ruler_gate.score_fwe("only nysskz found", top_k)
    assert ok and n == 1


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


def test_convert_quant_deletes_tensors_after_f16(tmp_path, monkeypatch):
    # addendum 42: the safetensors are dead weight once the f16 exists;
    # create() deletes safetensors-source only after the conversion is
    # verified on disk, and never when the f16 was already local
    import infra.convert_quant as convert_quant

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


def test_code_edit_md_autofix_inserts_blank_line_before_table(tmp_path):
    """Session 35, addendum 17: the mechanical rules are FIXED by the
    editor, not linted - a table inserted with no blank line before it
    gets the blank line inserted automatically (MD058)."""
    p = tmp_path / "doc.md"
    p.write_text("# Title\n\nSome prose.\n")
    code_edit.edit(
        str(p),
        [
            (
                "replace",
                "Some prose.",
                "Some prose.\n| a | b |\n|---|---|\n| 1 | 2 |",
            )
        ],
    )
    with open(str(p)) as f:
        assert f.read() == ("# Title\n\nSome prose.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")


def test_code_edit_md_gate_allows_clean_table(tmp_path):
    """The gate must not over-block: a properly blank-lined table
    passes and the file is written."""
    p = tmp_path / "doc.md"
    p.write_text("# Title\n\nSome prose.\n")
    code_edit.edit(
        str(p),
        [
            (
                "replace",
                "Some prose.",
                "Some prose.\n\n| a | b |\n|---|---|\n| 1 | 2 |",
            )
        ],
    )
    with open(str(p)) as f:
        assert "| 1 | 2 |" in f.read()


def test_code_edit_md_gate_ignores_preexisting_violations(tmp_path):
    """Only NEW violations fail the edit; a pre-existing ragged table
    elsewhere in the file does not block an unrelated clean edit."""
    p = tmp_path / "doc.md"
    p.write_text("# T\n\nprose\n\n| a | b |\n|---|---|\n| 1 | 2 | 3 |\n")
    code_edit.edit(str(p), [("replace", "prose", "more prose")])
    with open(str(p)) as f:
        assert "more prose" in f.read()


def test_code_edit_md_gate_ragged_table_blocked(tmp_path):
    """MD056: an edit introducing a ragged (uneven cell count) table
    fails before the write."""
    p = tmp_path / "doc.md"
    p.write_text("# T\n\nprose\n")
    try:
        code_edit.edit(
            str(p),
            [("replace", "prose", "prose\n\n| a | b |\n|---|---|\n| 1 |\n")],
        )
        raised = False
    except code_edit.CodeEditError as e:
        raised = "MD056" in str(e)
    assert raised
    with open(str(p)) as f:
        assert f.read() == "# T\n\nprose\n"


def test_code_edit_md_gate_unclosed_fence_blocked(tmp_path):
    """Fence balance: an edit that leaves an unclosed code fence fails
    before the write."""
    p = tmp_path / "doc.md"
    p.write_text("# T\n\nprose\n")
    try:
        code_edit.edit(
            str(p),
            [("replace", "prose", "prose\n\n```python\nx = 1\n")],
        )
        raised = False
    except code_edit.CodeEditError as e:
        raised = "unclosed code fence" in str(e)
    assert raised
    with open(str(p)) as f:
        assert f.read() == "# T\n\nprose\n"


def test_code_edit_md_autofix_single_trailing_newline(tmp_path):
    """Session 35, addendum 17: MD047 is auto-fixed - an edit leaving
    extra trailing newlines (or none) lands with exactly one."""
    p = tmp_path / "doc.md"
    p.write_text("# T\n\nprose\n")
    code_edit.edit(str(p), [("replace", "prose\n", "prose\n\n\n")])
    with open(str(p)) as f:
        assert f.read() == "# T\n\nprose\n"


def test_code_edit_md_autofix_blank_line_after_table(tmp_path):
    """Session 35, addendum 17: a non-table line directly after a
    table body gets the blank line inserted automatically."""
    p = tmp_path / "doc.md"
    p.write_text("# T\n\ntable below\n")
    code_edit.edit(
        str(p),
        [("replace", "table below", "table below\n\n| a | b |\n|---|---|\nfooter")],
    )
    with open(str(p)) as f:
        assert f.read() == ("# T\n\ntable below\n\n| a | b |\n|---|---|\n\nfooter\n")


def test_code_edit_md_gate_not_applied_to_python(tmp_path):
    """The gate is md-only: a python file with pipe characters is
    untouched by it."""
    p = tmp_path / "mod.py"
    p.write_text("x = 1\n")
    code_edit.edit(str(p), [("replace", "x = 1", "y = 'a|b'")])
    with open(str(p)) as f:
        assert f.read() == "y = 'a|b'\n"


def test_memory_breakdown_gib(tmp_path):
    import infra.llama_server as ls

    """Addendum 11: llama's own memory-breakdown table replaces the smaps
    census. Both row shapes (paren'd GPU line, flat Host line), the
    hybrid placeholder quirk (0.00 first, summed over all occurrences),
    and per-device model/context/compute extraction."""

    log = tmp_path / "lv5.log"
    log.write_text(
        "0.00.474.193 I load_tensors:      Vulkan0 model buffer size =     0.00 MiB\n"
        "0.00.474.193 I load_tensors:  Vulkan_Host model buffer size =     0.00 MiB\n"
        "0.00.960.078 I load_tensors:      Vulkan0 model buffer size =   763.78 MiB\n"
        "0.00.960.079 I load_tensors:  Vulkan_Host model buffer size =   257.66 MiB\n"
        "0.00.501.944 I common_memory_breakdown_print: | memory breakdown [MiB]"
        "                     | total    free    self   model   context   compute"
        "    unaccounted |\n"
        "0.00.501.945 I common_memory_breakdown_print: |   - Vulkan0 (780M Graphics"
        " (RADV PHOENIX)) | 16383 = 14998 + ( 935 =   763 +     125 +      46)"
        " +         450 |\n"
        "0.00.501.945 I common_memory_breakdown_print: |   - Host"
        "                                   |"
        "                   265 =   257 +       0 +       8                |\n",
        encoding="utf-8",
    )
    out = ls.memory_breakdown_gib(str(log))
    assert out is not None
    assert out["source"] == "llama-server (memory breakdown)"
    assert abs(out["weights_gib"] - 1021.44 / 1024) < 0.001
    assert abs(out["model_gib"] - (763 + 257) / 1024) < 0.001
    assert abs(out["context_gib"] - 125 / 1024) < 0.001
    assert abs(out["compute_gib"] - (46 + 8) / 1024) < 0.001
    assert set(out["devices"]) == {"Vulkan0", "Host"}
    assert abs(out["devices"]["Host"]["model_gib"] - 257 / 1024) < 0.001

    empty = tmp_path / "empty.log"
    empty.write_text("nothing here\n", encoding="utf-8")
    assert ls.memory_breakdown_gib(str(empty)) is None


def test_code_edit_edit_many_region_check_not_stale(tmp_path):
    """Session 40, addendum 3, fix 1: edit_many used the PREVIOUS
    edit()'s _last_edit_regions (module-global) for its delimiter
    check - regions from ANOTHER file. The failure mode is a false
    PASS: the stale regions point at benign spans of the new file,
    so the file's own region - which carries a real violation - is
    never checked. The global is gone; _apply now returns the
    regions and every caller threads them."""
    import code_edit

    pA = tmp_path / "a.c"
    pA.write_text("alpha\n")
    # seed the (now deleted) global with a region whose old/new text
    # also occur in b.txt at benign positions
    code_edit.edit(str(pA), [("replace", "alpha", "alpha")])
    pB = tmp_path / "b.c"
    pB.write_text("alpha\nplain txt\n")
    # b's own region inserts an unterminated double quote; with the
    # stale a-regions it slipped through, with its own regions it is
    # caught
    try:
        code_edit.edit_many([(str(pB), [("replace", "plain txt", 'plain "txt')])])
        raised = False
    except code_edit.CodeEditError:
        raised = True
    assert raised, "the stale-region edit_many must fail the quote check"
    assert pB.read_text() == "alpha\nplain txt\n"  # file untouched


def test_code_edit_edit_many_runs_md_gates(tmp_path):
    """Session 40, addendum 3, fix 2: edit_many skipped _fix_markdown
    and _check_markdown entirely - an md file edited via edit_many got
    no MD047/MD058 auto-fix and no introduced-violation gate."""
    import code_edit
    import pytest

    p = tmp_path / "t.md"
    p.write_text("# t\n\nhello")  # no trailing newline
    code_edit.edit_many([(str(p), [("append", "world\n")])])
    assert p.read_text().endswith("\n")  # MD047 auto-fixed now

    p2 = tmp_path / "t2.md"
    p2.write_text("# t\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
    with pytest.raises(code_edit.CodeEditError):
        code_edit.edit_many(
            [(str(p2), [("append", "| ragged |\n")])]  # MD056 ragged row
        )


def test_code_edit_verify_old_text_gone(tmp_path):
    """Session 40, addendum 3, fix 3: _verify_result checked only that
    the new text IS in the result - never that the old text is GONE.
    A replace whose old text survives (the apply silently missed)
    now fails; the legal exceptions (new == old; new contains old)
    still pass."""
    import code_edit

    p = tmp_path / "t.py"
    p.write_text("a = 1\nb = 1\n")
    code_edit.edit(str(p), [("replace", "a = 1", "a = 2")])  # old gone: fine
    code_edit.edit(str(p), [("replace", "a = 2", "a = 2")])  # new == old: fine
    code_edit.edit(str(p), [("replace", "b = 1", "b = 10")])  # new contains old: fine
    assert p.read_text() == "a = 2\nb = 10\n"


def test_code_edit_check_single_read(tmp_path):
    """Session 40, addendum 3, fix 4: check() used to verify against one
    read of the file and then call preview() - a SECOND read - so the
    verdict and the returned diff could disagree (TOCTOU). check() now
    computes everything from a single read; the returned diff IS the
    verified result."""
    import code_edit

    p = tmp_path / "t.py"
    p.write_text("x = 1\n")
    diff = code_edit.check(str(p), [("replace", "x = 1", "x = 2")])
    assert "-x = 1" in diff and "+x = 2" in diff
    assert p.read_text() == "x = 1\n"  # nothing written


def test_code_edit_balance_interior_paths(tmp_path):
    """Session 40, addendum 4, coverage-driven: the character-level
    loop inside balance() had rare paths no test exercised -
    triple-quoted strings, comments carrying brackets, backslash
    escapes, a mismatched closer, and closer underflow. These are
    exactly the paths that catch a duplicated or truncated edit
    fragment."""
    import code_edit

    def try_edit(p, blocks):
        try:
            code_edit.edit(str(p), blocks)
            return None
        except code_edit.CodeEditError as e:
            return str(e)

    # a comment's bracket must NOT mask a real imbalance elsewhere
    p = tmp_path / "c1.c"
    p.write_text("int a;\n")
    err = try_edit(p, [("replace", "int a;", "int a;  /* ( */\nint b;\n")])
    assert err is None  # the ( is inside a comment - legal
    # a MISMATCHED closer species in the region IS caught; a stray
    # closer with an empty stack is underflow - legal by design (the
    # opener may sit before the region)
    p2 = tmp_path / "c2.c"
    p2.write_text("if (a) { b(); }\n")
    # both the opener and the wrong-species closer INSIDE the region -
    # a true mismatch, which must be caught
    err = try_edit(p2, [("replace", "b();", "b(};")])
    assert err and "unbalanced" in err
    # a closer with an EMPTY stack is underflow - legal (the opener
    # may sit before the region)
    err = try_edit(p2, [("replace", "b();", "b(); extra )")])
    assert err is None
    # backslash escape inside a string does not eat the closing quote
    p3 = tmp_path / "c3.c"
    p3.write_text('char *s = "x";\n')
    err = try_edit(p3, [("replace", '"x"', '"\\"")')])
    assert err is None
    # closer underflow in a region is legal (the opener sits before it)
    p4 = tmp_path / "c4.c"
    p4.write_text("call(1);\n")
    err = try_edit(p4, [("replace", "1", "1, 2")])
    assert err is None


def test_code_edit_unclosed_triple_quote_refused(tmp_path):
    """Session 40, addendum 4: an unclosed triple quote at end of
    buffer returned None from balance() - the whole-buffer check
    (markup/json) passed corrupted edits. balance() now reports it;
    region mode still tolerates a triple quote that closes after
    the region (a legal docstring opener)."""
    import code_edit

    p = tmp_path / "u.c"
    p.write_text("int a;\n")
    try:
        code_edit.edit(str(p), [("replace", "int a;", 'int a; /* """ open')])
        raised = False
    except code_edit.CodeEditError:
        raised = True
    assert raised, "an unclosed triple quote must be refused"
    assert p.read_text() == "int a;\n"

    p2 = tmp_path / "ok.py"
    p2.write_text("def f():\n    return 1\n")
    code_edit.edit(str(p2), [("replace", "return 1", '"""doc\n    return 1\n    """')])
    assert '"""doc' in p2.read_text()  # legal region-local docstring


def test_code_edit_replace_regex_verify_literal(tmp_path):
    """Session 40, addendum 4: _verify_result demanded the PATTERN
    still match the result after a replace_regex - a false failure
    for every ordinary replacement (old_word -> new_word no longer
    matches old_word). The verify now checks the replacement text is
    in the result for literal replacements; backreference
    replacements are exempt (their text is not literal)."""
    import code_edit

    p = tmp_path / "t.c"
    p.write_text("int old_word;\n")
    code_edit.edit(str(p), [("replace_regex", r"old_word", "new_word")])
    assert "new_word" in p.read_text()

    p2 = tmp_path / "t2.c"
    p2.write_text("int old_word;\n")
    code_edit.edit(str(p2), [("replace_regex", r"old_\w+", "/* \\g<0> */")])
    assert "/* old_word */" in p2.read_text()


def test_code_edit_replace_whitespace_flexible(tmp_path):
    """Session 40, addendum 6: a replace target that misses on exact
    whitespace but matches exactly one place whitespace-flexibly is
    rescued (the session's raw-tool incident: an edit written against
    differently-indented text was a blind not-found); ambiguity is
    still a refusal, and a total miss reports the file's own near
    lines so the caller can re-aim."""
    import code_edit

    p = tmp_path / "t.py"
    p.write_text("def f():\n    x = 1   # comment\n    return x\n")
    code_edit.edit(
        str(p), [("replace", "x = 1 # comment\n    return x", "x = 2  # changed\n    return x")]
    )
    assert "x = 2" in p.read_text()

    p2 = tmp_path / "t2.py"
    p2.write_text("a = 1\nb = 1\n")
    code_edit.edit(str(p2), [("replace", "a = 1", "a = 2")])
    assert p2.read_text() == "a = 2\nb = 1\n"

    p3 = tmp_path / "t3.py"
    p3.write_text("if a:\n    b()\nif c:\n    b()\n")
    try:
        code_edit.edit(str(p3), [("replace", "def missing():", "z")])
        raised = False
    except code_edit.CodeEditError as e:
        raised = True
        assert "wanted" in str(e) and "file's near lines" in str(e)
    assert raised, "a total miss must be refused with the file's own text"
    assert p3.read_text() == "if a:\n    b()\nif c:\n    b()\n"  # untouched
