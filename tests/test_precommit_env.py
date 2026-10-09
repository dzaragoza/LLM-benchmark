"""Pins: R-20 (session 43, reworked addendum 158 - the hook era is
over). The verification environment is complete: every dependency
the CI workflow resolves is declared in requirements.txt, and the
CI workflow runs every check - nothing is skipped because a tool
is missing. The commit hook and its install are ABOLISHED (the
machinery is gone from the repo - pinned here so it cannot creep
back unregistered).
"""

from __future__ import annotations

import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CI_MODULES = (
    "pytest",
    "hypothesis",
    "huggingface_hub",
    "pyarrow.parquet",
    "transformers",
)


def test_r20_requirements_declare_the_ci_environment():
    """Pins: R-20. requirements.txt declares every tool CI resolves."""
    declared = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    for tool in ("pytest", "ruff", "ty", "crosshair-tool", "hypothesis", "coverage", "vulture"):
        assert tool in declared, f"{tool} missing from requirements.txt"


def test_r20_ci_installs_from_requirements():
    """Pins: R-20. The workflow installs the declared environment - no
    undeclared dependency, no skipped check."""
    wf = (ROOT / ".github" / "workflows" / "push-regression.yml").read_text(encoding="utf-8")
    assert "requirements.txt" in wf
    for step in (
        "ruff check",
        "ruff format --check",
        "ty_check.py",
        "md_check.py",
        "requirements_check.py",
        "pytest tests",
    ):
        assert step in wf, f"CI must run {step} (nothing is skipped)"


def test_r20_the_hook_machinery_is_gone():
    """Pins: R-20/R-25 (addendum 158): the abolished hook cannot creep
    back unregistered - a restored .pre-commit-config.yaml or hook
    script is a protocol change requiring an addendum."""
    assert not (ROOT / ".pre-commit-config.yaml").exists()
    assert not (ROOT / "testmon_hook.py").exists()
    assert not (ROOT / "format_hook.py").exists()


def test_r20_modules_importable():
    """Pins: R-20. The suite's imports resolve in this environment."""
    for module in CI_MODULES:
        importlib.import_module(module)


def test_r21_no_backward_compatibility_shims():
    """Pins: R-21. Retired machinery is gone, not shimmed: the v6
    prototype is absent, the state store has no reader for the retired
    certify/certify_arc namespaces, and find_server resolves the
    llama-server binary repo-relative only - no pre-reorg HOME
    fallback. Compat returns only by explicit requirement."""
    assert not (ROOT / "v6_prototype.py").exists()
    src = (ROOT / "bench" / "state_store.py").read_text(encoding="utf-8")
    assert "def certify_cells" not in src
    server = (ROOT / "infra" / "llama_server.py").read_text(encoding="utf-8")
    assert "expanduser" not in server
