def test_safe_append_md_pipeline(tmp_path):
    """Addendum 13: safe_append to a .md target runs the same pipeline
    as edit() - a table appended without its blank line is AUTO-FIXED,
    and a ragged row (MD056, judgement class) is refused with the
    file untouched. The notebook-append pattern can no longer smuggle
    a lint break into git."""
    import code_edit

    import AI_tools.md_check as md_check

    m = tmp_path / "notes.md"
    m.write_text("# notes\n")
    code_edit.safe_append(str(m), "\n## addendum\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
    text = m.read_text()
    assert "\n\n| a | b |\n" in text  # the auto-fixer blank-lined it
    assert md_check.check(str(m)) == []
    # ragged: 3 cells in a 2-column table -> refused, untouched
    before = m.read_text()
    try:
        code_edit.safe_append(str(m), "\n## bad\n\n| a | b |\n|---|---|\n| 1 | 2 | x |\n")
        raise AssertionError("ragged append accepted")
    except code_edit.CodeEditError as e:
        assert "MD056" in str(e)
    assert m.read_text() == before


def test_safe_append_python_still_compiles_first(tmp_path):
    """The addendum-21 guarantee is unchanged: a syntactically broken
    python addition is still refused before the write."""
    import code_edit

    t = tmp_path / "t.py"
    t.write_text("x = 1\n")
    try:
        code_edit.safe_append(str(t), "def broken(:\n")
        raise AssertionError("broken python accepted")
    except SyntaxError:
        pass
    assert t.read_text() == "x = 1\n"
