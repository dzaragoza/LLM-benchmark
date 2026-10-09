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


def test_r31_hypothesis_never_in_the_hook():
    """Pins: R-31. The hypothesis layer lives OUTSIDE the 5s commit hook
    (R-25): BOTH pytest arms of the hook deselect the hypothesis_props
    marker - a substring check anywhere in the file is toothless (the
    teeth audit caught it: breaking only the testmon arm's deselect
    left the docstring mention and the pin passed)."""
    hook = (ROOT / "testmon_hook.py").read_text(encoding="utf-8")
    # every pytest invocation in the hook must deselect the marker:
    # each pytest call site ends with the marker arg before the
    # closing bracket - count must match the number of call sites
    import re

    call_sites = re.findall(r"subprocess\.run\(\s*\[", hook)
    deselects = hook.count('"not hypothesis_props"')
    assert deselects >= len(call_sites), (
        f"{deselects} deselects for {len(call_sites)} subprocess call sites - "
        "every hook pytest arm must deselect hypothesis_props"
    )
    assert '"--testmon"' in hook, "the testmon arm must stay a testmon run"
    props = (ROOT / "tests" / "test_properties.py").read_text(encoding="utf-8")
    assert "hypothesis_props" in props, "the properties must carry their layer marker"


def test_r31_layers_have_their_homes():
    """Pins: R-31. Each strategy layer has a registered home: contracts in
    tests/contracts.py, properties in tests/test_properties.py, the full
    suite in the push workflow, crosshair + coverage in the daily workflow."""
    assert (ROOT / "tests" / "contracts.py").exists()
    assert (ROOT / "tests" / "test_properties.py").exists()
    push = (ROOT / ".github" / "workflows" / "push-regression.yml").read_text(encoding="utf-8")
    for needle in (
        "pytest tests -q",
        "crosshair check",
        "coverage run",
        "vulture",
        "autoupdate",
    ):
        assert needle in push, f"push-regression must own the former daily step: {needle}"
    assert "schedule:" not in push, "no scheduled runs (addendum 147)"


def test_r31_no_scheduled_workflows():
    """Pins: R-31. No daily/weekly scheduled CI survives (addendum 147):
    local-fast under the 5s rule, CI-complete on every push, the pull
    check (R-27) is the safety net."""
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        assert "schedule:" not in wf.read_text(encoding="utf-8"), f"{wf.name} is scheduled"
    assert not (ROOT / ".github" / "workflows" / "daily-quality.yml").exists()
    assert not (ROOT / ".github" / "workflows" / "weekly-quality.yml").exists()
