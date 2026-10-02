"""The markdown compliance checker (addendum 107): every rule ID it
reports maps to the markdownlint rule of the same name, restricted to
the GitHub-rendering failure class (tables, fences, trailing newline).
"""

import md_check


def run(tmp_path, text):
    f = tmp_path / "t.md"
    f.write_text(text, encoding="utf-8")
    return md_check.check(str(f))


def test_md058_no_blank_line_before_header(tmp_path):
    problems = run(
        tmp_path,
        "Some paragraph.\n| A | B |\n|---|---|\n| 1 | 2 |\n",
    )
    assert any("MD058" in p and "before" in p for p in problems)


def test_md058_no_blank_line_after_table(tmp_path):
    problems = run(
        tmp_path,
        "| A | B |\n|---|---|\n| 1 | 2 |\ntrailing text\n",
    )
    assert any("MD058" in p and "after" in p for p in problems)


def test_md056_ragged_table(tmp_path):
    problems = run(tmp_path, "| A | B |\n|---|---|\n| 1 |\n")
    assert any("MD056" in p for p in problems)


def test_md055_row_not_piped(tmp_path):
    problems = run(tmp_path, "| A | B |\n|---|---|\n| 1 | 2\n")
    assert any("MD055" in p for p in problems)


def test_md047_no_trailing_newline(tmp_path):
    problems = run(tmp_path, "| A | B |\n|---|---|\n\nno newline at eof")
    assert any("MD047" in p for p in problems)


def test_md047_double_trailing_newline(tmp_path):
    problems = run(tmp_path, "text\n\n")
    assert any("MD047" in p for p in problems)


def test_unclosed_fence(tmp_path):
    problems = run(tmp_path, "```python\nx = 1\n")
    assert any("unclosed code fence" in p for p in problems)


def test_closed_fence_passes(tmp_path):
    assert run(tmp_path, "```python\nx = 1\n```\n") == []


def test_well_formed_table_passes(tmp_path):
    assert run(tmp_path, "| A | B |\n|---|---|\n| 1 | 2 |\n") == []


def test_tilde_fence_closed_by_backticks_is_flagged(tmp_path):
    problems = run(tmp_path, "~~~\ncode\n```\n")
    assert any("unclosed code fence" in p for p in problems)


def test_deep_indented_line_is_not_a_closing_fence(tmp_path):
    problems = run(tmp_path, "```\ncode\n    ```\n")
    assert any("unclosed code fence" in p for p in problems)


def test_md058_blank_line_inside_table(tmp_path):
    problems = run(
        tmp_path,
        "| A | B |\n|---|---|\n\n| 1 | 2 |\n",
    )
    assert any("MD058" in p and "inside" in p for p in problems)
