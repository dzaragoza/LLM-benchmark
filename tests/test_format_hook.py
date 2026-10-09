"""Pins: R-25 (session 45, addendum 146) - the ruff-format hook never
aborts the commit: it applies the format, re-stages what it touched,
and exits 0 (the author's ruling: formatting-only changes are exactly
what the hook is for; re-running the commit by hand is pure friction).
A real ruff failure (a broken file) still blocks - the exit-0 is for
style deltas only.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _init_repo(tmp_path):
    repo = tmp_path
    repo.mkdir(exist_ok=True)

    def git(*a):
        return subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True)

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    return repo, git


def _run_hook(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "format_hook.py"), "sample.py"],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def test_format_applied_restage_exit0(tmp_path):
    """A style delta: the hook formats, re-stages, exits 0 - the commit
    is never aborted by a formatting change."""
    repo, git = _init_repo(tmp_path)
    (repo / "sample.py").write_text('x = {  "a":1,   "b":2 }\n', encoding="utf-8")
    git("add", "sample.py")
    git("commit", "-q", "-m", "init")

    proc = _run_hook(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "restaged" in proc.stdout, proc.stdout
    assert (repo / "sample.py").read_text(encoding="utf-8") == 'x = {"a": 1, "b": 2}\n'
    staged = git("diff", "--name-only", "--cached", "HEAD").stdout
    assert "sample.py" in staged, "the formatted file must be re-staged"


def test_format_clean_file_is_silent(tmp_path):
    """An already-formatted file: exit 0, nothing restaged."""
    repo, git = _init_repo(tmp_path)
    (repo / "sample.py").write_text('x = {"a": 1, "b": 2}\n', encoding="utf-8")
    git("add", "sample.py")
    git("commit", "-q", "-m", "init")
    proc = _run_hook(repo)
    assert proc.returncode == 0
    assert "restaged" not in proc.stdout


def test_broken_file_still_blocks(tmp_path):
    """A syntax error is NOT a style delta: the hook exits non-zero and
    the commit is blocked - the exit-0 ruling covers formatting only."""
    repo, _ = _init_repo(tmp_path)
    (repo / "sample.py").write_text("def f(:\n", encoding="utf-8")
    proc = _run_hook(repo)
    assert proc.returncode != 0


def test_hook_entry_registered():
    """The commit hook suite carries the wrapper (never-abort form), and
    the stock aborting ruff-format entry is gone."""
    cfg = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "entry: python3 format_hook.py" in cfg
    assert cfg.count("id: ruff-format") == 1, "one ruff-format entry: the wrapper"
    assert "https://github.com/astral-sh/ruff-pre-commit" in cfg, "ruff lint stays pinned"
