def test_fix_markdown_collapses_blank_line_inside_table():
    import code_edit

    broken = "| A | B |\n|---|---|\n\n| 1 | 2 |\n"
    fixed = code_edit._fix_markdown(broken, "t.md")
    assert fixed == "| A | B |\n|---|---|\n| 1 | 2 |\n"


def test_safe_append(tmp_path):
    """Addendum 21: safe_append is the transactional, idempotent,
    syntax-checked append born from the session's heredoc-escaping
    incidents (the escaped-newline corruption of a test file and the
    triple-repair chain it took)."""
    import code_edit

    m = tmp_path / "notes.md"
    m.write_text("# notes\n")
    r1 = code_edit.safe_append(str(m), "\n## addendum\n\nbody text\n")
    assert r1.startswith("appended")
    r2 = code_edit.safe_append(str(m), "\n## addendum\n\nbody text\n")
    assert r2.startswith("idempotent skip")
    assert m.read_text().count("## addendum") == 1

    t = tmp_path / "t.py"
    t.write_text("x = 1\n")
    try:
        code_edit.safe_append(str(t), "def broken(:\n")
        raise AssertionError("broken python accepted")
    except SyntaxError:
        pass
    assert t.read_text() == "x = 1\n"
    code_edit.safe_append(str(t), "def ok():\n    return 2\n")
    compile(t.read_text(), str(t), "exec")
