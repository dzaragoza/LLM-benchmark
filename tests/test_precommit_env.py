"""The pre-commit environment contract (session 43, R-20).

The author's ruling: all the dependencies for the commit hook shall
be installed, and the commit hook shall not be omitted. This pins
the environment side of that contract - every hook entry and every
third-party module the suite resolves must be importable/ runnable
in the active environment, so the full hook suite runs for real and
no --no-verify bypass is ever needed.
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

HOOK_TOOL_BINARIES = ("ruff", "pre-commit")
HOOK_PYTHON_MODULES = (
    "ty",  # the type check (ty_check.py wrapper shells out to it)
    "pytest",
    "hypothesis",  # tests/test_properties.py
    "huggingface_hub",  # infra/hf_download.py
    "pyarrow.parquet",  # etc/registry_data.py
    "transformers",  # tokenizer_probe.py
)


def test_hook_binaries_on_path():
    """Pins: R-20. ruff and pre-commit are installed as executables."""
    for tool in HOOK_TOOL_BINARIES:
        assert shutil.which(tool), f"{tool} is not installed (the hooks cannot run)"


@pytest.mark.parametrize("module", HOOK_PYTHON_MODULES)
def test_hook_python_modules_importable(module):
    """Pins: R-20. Every third-party module a hook resolves imports."""
    importlib.import_module(module)


def test_ty_check_wrapper_passes():
    """Pins: R-20. The type-check hook entry itself is green in this
    environment - the addendum-21 ruling (no --no-verify exceptions)
    is enforceable only where the check can actually run."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "ty_check.py")],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_no_verify_is_not_used_in_history():
    """Pins: R-20. The working scripts never bake the bypass in: no
    repo file instructs anyone to commit with --no-verify."""
    needle = "--no-ver" + "ify"
    offenders = []
    for py in ROOT.rglob("*.py"):
        if "__pycache__" in py.parts or py.name == "test_precommit_env.py":
            continue
        # quoted string literals only - a docstring NARRATING the
        # retired bypass (ty_check.py) is history, not a usage
        text = py.read_text(encoding="utf-8")
        if f'"{needle}"' in text or f"'{needle}'" in text:
            offenders.append(str(py.relative_to(ROOT)))
    assert offenders == [], offenders


def test_precommit_config_hooks_present():
    """Pins: R-20. The hook suite stays complete: ruff, ruff-format, ty,
    pytest, the markdown check and the requirements check - removing a
    hook silently is the other way to 'omit the commit hook'."""
    import yaml  # noqa: F401 - presence is the point, parsing is stdlib-free

    cfg = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    for hook_id in ("ruff", "ruff-format", "ty", "pytest", "md-tables", "requirements-check"):
        assert f"id: {hook_id}" in cfg, f"hook {hook_id} missing from .pre-commit-config.yaml"
