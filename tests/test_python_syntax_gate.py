def test_edit_refuses_python_syntax_break(tmp_path):
    """Addendum 16: the ast gate - a .py edit whose result does not
    parse (when the source did) is refused with the SyntaxError's
    line, file untouched. Reproduces the addendum-15 incident class:
    a replace inserting a literal newline inside a string literal."""
    import code_edit

    p = tmp_path / "m.py"
    p.write_text('help = "session 37, addendum 8"\n')
    try:
        code_edit.edit(
            str(p),
            [
                (
                    'help = "session 37, addendum 8"',
                    'help = "line one\nline two"',  # real newline in a string = SyntaxError
                )
            ],
        )
        raise AssertionError("syntax-breaking edit accepted")
    except code_edit.CodeEditError as e:
        assert "breaks the python syntax" in str(e)
        assert "line 1" in str(e)
    assert p.read_text() == 'help = "session 37, addendum 8"\n'  # untouched


def test_edit_allows_repair_of_broken_python(tmp_path):
    """Only NEW problems fail (same philosophy as the md gate): if the
    source was already broken, an edit is a legal repair."""
    import code_edit

    p = tmp_path / "m.py"
    p.write_text("def broken(:\n    pass\n")  # already a SyntaxError
    code_edit.edit(str(p), [("def broken(:", "def fixed():")])
    compile(p.read_text(), str(p), "exec")


def test_edit_clean_python_still_passes(tmp_path):
    import code_edit

    p = tmp_path / "m.py"
    p.write_text("x = 1\n")
    code_edit.edit(str(p), [("x = 1", "x = 2\ny = x + 1")])
    assert p.read_text() == "x = 2\ny = x + 1\n"


def test_check_preflight_catches_syntax_break(tmp_path):
    """The pre-flight (check) runs the same gate - a syntax-breaking
    block set fails before any caller commits to it."""
    import code_edit

    p = tmp_path / "m.py"
    p.write_text("a = [1, 2]\n")
    try:
        code_edit.check(str(p), [("a = [1, 2]", "a = [1, 2")])
        raise AssertionError("preflight accepted a syntax break")
    except code_edit.CodeEditError as e:
        assert "breaks the python syntax" in str(e)
    assert p.read_text() == "a = [1, 2]\n"
