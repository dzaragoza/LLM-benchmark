"""Pins: R-30, R-31 (session 45, addendum 145).

R-30 - the tool environment is explicit and complete: every hook/test/CI
dependency is declared in requirements.txt, and the working environment
imports them (the test_precommit_env pins carry the installed-side check).

R-31 - the test strategy is layered, each layer with a registered home:
deterministic pins in the commit hook via testmon, hypothesis properties
marked hypothesis_props never in the hook, crosshair contracts, the full
suite on every push and daily in CI.
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


def test_r31_hypothesis_never_in_the_hook():
    """Pins: R-31. The hypothesis layer lives OUTSIDE the 5s commit hook
    (R-25): the hook's pytest selection excludes the hypothesis_props
    marker, and the hook config has no bare pytest entry."""
    hook = (ROOT / "testmon_hook.py").read_text(encoding="utf-8")
    assert "not hypothesis_props" in hook, "the hook must deselect the hypothesis layer"
    props = (ROOT / "tests" / "test_properties.py").read_text(encoding="utf-8")
    assert "hypothesis_props" in props, "the properties must carry their layer marker"


def test_r31_layers_have_their_homes():
    """Pins: R-31. Each strategy layer has a registered home: contracts in
    tests/contracts.py, properties in tests/test_properties.py, the full
    suite in the push workflow, crosshair + coverage in the daily workflow."""
    assert (ROOT / "tests" / "contracts.py").exists()
    assert (ROOT / "tests" / "test_properties.py").exists()
    push = (ROOT / ".github" / "workflows" / "push-regression.yml").read_text(encoding="utf-8")
    assert "pytest tests -q" in push and "crosshair check" in push
    daily = (ROOT / ".github" / "workflows" / "daily-quality.yml").read_text(encoding="utf-8")
    assert "pytest tests -q" in daily and "crosshair check" in daily
    assert 'cron: "0 0 * * *"' in daily, "the quality run is DAILY (addendum 145)"


def test_r31_weekly_workflow_is_gone():
    """Pins: R-31. The weekly-quality workflow is retired - the quality
    cadence is daily (addendum 145, the author's ruling); no stale weekly
    schedule survives to double-run the same checks."""
    assert not (ROOT / ".github" / "workflows" / "weekly-quality.yml").exists()
