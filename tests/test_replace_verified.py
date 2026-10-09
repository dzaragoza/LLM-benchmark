def test_replace_verified_unique_pairs(tmp_path):
    """Addendum 12: replace_verified is the scripted-replace pattern as
    a first-class transaction - the workaround for wrapped-line
    old_str failures that used to bypass the editor entirely (the
    addendum-6 incident class: the md auto-fixer and lint gate never
    saw the edit, and an MD058 reached git)."""
    import code_edit

    p = tmp_path / "doc.md"
    p.write_text("# title\n\nintro line\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")
    code_edit.replace_verified(
        str(p),
        [
            ("intro line", "replaced line"),
            ("| 1 | 2 |", "| 1 | 2 |\n| 3 | 4 |"),
        ],
    )
    text = p.read_text()
    assert "replaced line" in text and "intro line" not in text
    assert "| 3 | 4 |" in text
    import AI_tools.md_check as md_check

    assert md_check.check(str(p)) == []


def test_replace_verified_asserts_exact_count(tmp_path):
    """The assert IS the tool's now: an old text occurring the wrong
    number of times is refused with the file untouched - the
    hand-rolled `assert old in src` pattern, enforced centrally."""
    import code_edit

    p = tmp_path / "t.py"
    p.write_text("x = 1\nx = 1\n")
    try:
        code_edit.replace_verified(str(p), [("x = 1", "x = 2")])
        raise AssertionError("non-unique old accepted")
    except code_edit.CodeEditError as e:
        assert "occurs 2 time(s)" in str(e)
    assert p.read_text() == "x = 1\nx = 1\n"  # untouched
    # count=2 upgrades the same call to a replace_all
    code_edit.replace_verified(str(p), [("x = 1", "x = 2")], count=2)
    assert p.read_text() == "x = 2\nx = 2\n"


def test_replace_verified_missing_target_untouched(tmp_path):
    import code_edit

    p = tmp_path / "t.md"
    p.write_text("keep me\n")
    try:
        code_edit.replace_verified(str(p), [("absent", "new")])
        raise AssertionError("missing old accepted")
    except code_edit.CodeEditError:
        pass
    assert p.read_text() == "keep me\n"


def test_replace_verified_runs_the_md_pipeline(tmp_path):
    """The whole point: a scripted replace that inserts a table
    without its blank line gets AUTO-FIXED (MD058), and one that
    breaks a judgment rule (ragged MD056) is refused before the
    write."""
    import code_edit

    import AI_tools.md_check as md_check

    p = tmp_path / "n.md"
    p.write_text("# head\n\npara\n")
    code_edit.replace_verified(str(p), [("para", "para\n\n| a | b |\n|---|---|\n| 1 | 2 |")])
    assert md_check.check(str(p)) == []
    assert "\n\n| a | b |\n" in p.read_text()  # the fixer ran
    q = tmp_path / "r.md"
    q.write_text("| a | b |\n|---|---|\n| 1 | 2 |\n")
    try:
        code_edit.replace_verified(str(q), [("| 1 | 2 |", "| 1 | 2 | extra |")])
        raise AssertionError("ragged row accepted")
    except code_edit.CodeEditError as e:
        assert "MD056" in str(e)
    assert q.read_text() == "| a | b |\n|---|---|\n| 1 | 2 |\n"  # untouched


def test_replace_verified_per_pair_counts(tmp_path):
    """Addendum 82: a mixed transaction - one unique pair plus one
    all-occurrences pair - in a single call, each with its own expected
    count asserted against the file before anything is written."""
    p = tmp_path / "cfg.txt"
    p.write_text("a=1\nb=old\nc=old\n", encoding="utf-8")
    import code_edit

    code_edit.replace_verified(
        str(p),
        [("a=1", "a=2"), ("old", "new", 2)],
    )
    out = p.read_text(encoding="utf-8")
    assert out == "a=2\nb=new\nc=new\n"
    # the per-pair count is asserted: 1 occurrence claimed, 2 present
    p.write_text("a=1\nb=old\n", encoding="utf-8")
    try:
        code_edit.replace_verified(str(p), [("a=1", "a=2"), ("old", "new", 2)])
    except code_edit.CodeEditError as e:
        assert "expected exactly 2" in str(e)
        # transaction: the FIRST pair's change was not written either
        assert p.read_text(encoding="utf-8") == "a=1\nb=old\n"
    else:
        raise AssertionError("expected CodeEditError")
