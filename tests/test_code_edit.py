

def test_fix_markdown_collapses_blank_line_inside_table():
    import code_edit

    broken = "| A | B |\n|---|---|\n\n| 1 | 2 |\n"
    fixed = code_edit._fix_markdown(broken, "t.md")
    assert fixed == "| A | B |\n|---|---|\n| 1 | 2 |\n"
