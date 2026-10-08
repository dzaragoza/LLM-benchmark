import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CE = ROOT / "AI_tools" / "code_edit.py"


def _run(target: Path, spec: Path, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CE), str(target), "--blocks-file", str(spec), *flags],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**__import__("os").environ, "PYTHONPATH": str(ROOT)},
    )


def test_cli_blocks_file_surface():
    """Pins: R-26 (session 44, addendum 126). The CLI takes the JSON
    spec from --blocks-file, so the agent composes specs with its file
    tool - no heredoc, no shell quoting, no driver scripts."""
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "t.md"
        target.write_text("alpha\n", encoding="utf-8")
        spec = Path(td) / "spec.json"
        spec.write_text(json.dumps({"blocks": [["replace", "alpha", "beta"]]}), encoding="utf-8")
        proc = _run(target, spec)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert target.read_text(encoding="utf-8") == "beta\n"


def test_cli_write_surface():
    """Pins: R-26 (session 44, addendum 126). --write creates a file
    with spec[content] through the same atomic write() surface."""
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "new.py"
        spec = Path(td) / "spec.json"
        spec.write_text(json.dumps({"content": "x = 1\n"}), encoding="utf-8")
        proc = _run(target, spec, "--write")
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert target.read_text(encoding="utf-8") == "x = 1\n"


def test_cli_check_refuses_without_touching():
    """Pins: R-26 (session 44, addendum 126). --check verifies only;
    a non-matching block leaves the file untouched."""
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "t.md"
        target.write_text("alpha\n", encoding="utf-8")
        spec = Path(td) / "spec.json"
        spec.write_text(json.dumps({"blocks": [["replace", "nope", "beta"]]}), encoding="utf-8")
        proc = _run(target, spec, "--check")
        assert proc.returncode != 0
        assert target.read_text(encoding="utf-8") == "alpha\n"
