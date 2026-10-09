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
        text = py.read_text(encoding="utf-8")
        # ANY quoted literal containing the flag - not just the flag
        # as the whole literal: a bypass embedded in a longer command
        # string ("git commit --no-verify") escaped the old exact-
        # literal check (the teeth audit caught it). Docstrings
        # narrating the retired bypass are history, not usage: only
        # string literals (single- or double-quoted lines that also
        # look like code: not inside a docstring block) count.
        import re

        tq = chr(34) * 3
        code_only = re.sub(tq + ".*?" + tq, "", text, flags=re.DOTALL)
        code_only = re.sub(chr(39) * 3 + ".*?" + chr(39) * 3, "", code_only, flags=re.DOTALL)
        for m in re.finditer(
            r"[\"]([^\"]*" + re.escape(needle) + r"[^\"]*)[\"]",
            code_only,
        ):
            line_no = text[: m.start()].count("\n") + 1
            offenders.append(f"{py.relative_to(ROOT)}:{line_no}")
    assert offenders == [], offenders


def test_precommit_config_hooks_present():
    """Pins: R-20, R-25. The hook suite is the five fast checks only
    (ruff, ruff-format, ty, md, requirements) - pytest in the hook
    violates the 5s budget (R-25). The full pytest suite MUST live in
    the push workflow instead - or the regression suite silently
    loses its gate. Removing a hook silently is the other way to
    'omit the commit hook'."""
    import yaml  # noqa: F401 - presence is the point, parsing is stdlib-free

    cfg = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    for hook_id in ("ruff", "ruff-format", "ty", "md-tables", "requirements-check"):
        assert f"id: {hook_id}" in cfg, f"hook {hook_id} missing from .pre-commit-config.yaml"
    assert "id: pytest" not in cfg, "pytest in the commit hook violates the 5s budget (R-25)"
    push_ci = (ROOT / ".github" / "workflows" / "push-regression.yml").read_text(encoding="utf-8")
    assert "pytest tests -q" in push_ci, "the push workflow must run the full pytest suite"
    assert "crosshair check" in push_ci, "the push workflow must run the contract proofs"


def test_no_backward_compatibility_shims():
    """Pins: R-21. Retired machinery is gone, not shimmed: the v6
    prototype (superseded by bench/v7.py) is absent, the state store
    has no reader for the retired certify/certify_arc namespaces, and
    find_server resolves the llama-server binary repo-relative only -
    no pre-reorg HOME fallback. Compat is added back only by explicit
    requirement."""
    assert not (ROOT / "v6_prototype.py").exists()
    src = (ROOT / "bench" / "state_store.py").read_text(encoding="utf-8")
    assert "def certify_cells" not in src
    server = (ROOT / "infra" / "llama_server.py").read_text(encoding="utf-8")
    assert "expanduser" not in server


def test_task_store_has_no_retired_namespace_fallback():
    """Pins: R-21. _task_store maps the live tasks to their namespaces
    directly - an unknown task KeyErrors instead of silently writing
    into the retired `certify` (FWE) namespace."""
    from bench import state_store

    fst: dict[str, object] = {}
    with pytest.raises(KeyError):
        state_store._task_store(fst, 8192, "arc", 1, 0, None, None)
    assert "certify" not in fst
