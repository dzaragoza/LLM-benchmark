"""tee_output tests (session 34 WoW: stdout/stderr duplicated to results.txt)."""

import io

import tee_output


def test_install_tees_stdout(tmp_path, monkeypatch):
    path = str(tmp_path / "results.txt")
    real = io.StringIO()
    monkeypatch.setattr(tee_output.sys, "stdout", real)
    monkeypatch.setattr(tee_output.sys, "argv", ["prog", "--flag"])
    tee_output.install(path)
    print("hello tee")
    tee_output.sys.stdout.flush()
    content = open(path, encoding="utf-8").read()
    assert "hello tee" in content
    assert "prog --flag" in content  # timestamped command header
    assert "hello tee" in real.getvalue()  # terminal copy preserved


def test_install_appends(tmp_path, monkeypatch):
    path = str(tmp_path / "results.txt")
    monkeypatch.setattr(tee_output.sys, "argv", ["prog"])
    tee_output.install(path)
    tee_output.install(path)
    content = open(path, encoding="utf-8").read()
    assert content.count("===== ") == 2  # accumulate, not truncate


def test_install_bad_path_is_noop(monkeypatch):
    monkeypatch.setattr(tee_output.sys, "argv", ["prog"])
    before = tee_output.sys.stdout
    tee_output.install("/nonexistent-dir/results.txt")
    assert tee_output.sys.stdout is before
