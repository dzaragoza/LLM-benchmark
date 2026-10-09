"""Pins: R-30, R-31 (session 45, addenda 145/147).

R-30 - the tool environment is explicit and complete: every hook/test/CI
dependency is declared in requirements.txt, and the working environment
imports them (the test_precommit_env pins carry the installed-side check).

R-31 - the verification split is LOCAL-FAST vs CI-COMPLETE (addendum
147): the commit hook runs what fits the 5s rule; GitHub CI owns
everything else on every push (the full suite, crosshair, coverage,
vulture, the drift report); no scheduled runs; the pull check (R-27)
is the safety net.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = Path(__file__).resolve().parent.parent


def test_r30_requirements_txt_declares_the_tool_environment():
    """Pins: R-30. Every tool a hook/test/CI resolves is declared in
    requirements.txt - the environment is explicit, not tribal."""
    declared = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    for tool in (
        "pytest",
        "ruff",
        "ty",
        "crosshair-tool",
        "hypothesis",
        "pytest-testmon",
        "huggingface_hub",
        "pyarrow",
        "transformers",
    ):
        assert tool in declared, f"{tool} missing from requirements.txt"


def test_r30_no_undeclared_ci_dependency():
    """Pins: R-30. The CI workflows install from requirements.txt (plus the
    run-local helpers coverage/vulture/pre-commit, installed in the workflow
    step) - no workflow resolves a tool the repo does not declare or install."""
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        text = wf.read_text(encoding="utf-8")
        assert "requirements.txt" in text, f"{wf.name} must install the declared environment"


def test_r31_layers_have_their_homes():
    """Pins: R-31. The verification homes: contracts in
    tests/contracts.py, properties in tests/test_properties.py, and
    EVERYTHING (lint, format, types, md, requirements, the full suite,
    crosshair, coverage, vulture) in the ONE push workflow - addendum
    158: no local gate at all."""
    assert (ROOT / "tests" / "contracts.py").exists()
    assert (ROOT / "tests" / "test_properties.py").exists()
    push = (ROOT / ".github" / "workflows" / "push-regression.yml").read_text(encoding="utf-8")
    for needle in (
        "pytest tests",
        "crosshair check",
        "coverage run",
        "vulture",
        "ruff check",
        "ruff format .",
    ):
        assert needle in push, f"push-regression must run it: {needle}"
    assert "schedule:" not in push, "no scheduled runs"


def test_r31_no_scheduled_workflows():
    """Pins: R-31. No daily/weekly scheduled CI survives (addendum 147):
    local-fast under the 5s rule, CI-complete on every push, the pull
    check (R-27) is the safety net."""
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        assert "schedule:" not in wf.read_text(encoding="utf-8"), f"{wf.name} is scheduled"
    assert not (ROOT / ".github" / "workflows" / "daily-quality.yml").exists()
    assert not (ROOT / ".github" / "workflows" / "weekly-quality.yml").exists()
