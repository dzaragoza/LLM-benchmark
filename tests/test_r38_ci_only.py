"""Pins: R-38 (session 45, addendum 159) - NOTHING verification-shaped
runs locally. Verification of every kind lives ONLY in GitHub CI. This
pin enforces the structural side: the repo carries no local gate
machinery (no pre-commit config, no local runner scripts the agent
could invoke), the CI workflow owns every check, and requirements.txt
documents the CI-only contract. The behavioral side (the agent never
hand-runs a tool) is governed by the requirement itself and graded on
the next pull - a CI verdict is the only execution signal.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_r38_no_local_gate_machinery():
    """No pre-commit config, no hook scripts, no local runner - the
    machinery that made local verification possible is gone."""
    assert not (ROOT / ".pre-commit-config.yaml").exists()
    assert not (ROOT / "testmon_hook.py").exists()
    assert not (ROOT / "format_hook.py").exists()


def test_r38_ci_owns_every_check():
    """The one workflow runs the complete verification set; nothing is
    scheduled, nothing local."""
    wf = (ROOT / ".github" / "workflows" / "push-regression.yml").read_text(encoding="utf-8")
    for check in (
        "ruff check",
        "ruff format --check",
        "ty_check.py",
        "md_check.py",
        "requirements_check.py",
        "pytest tests",
        "crosshair check",
        "coverage run",
        "vulture",
    ):
        assert check in wf, f"CI must own {check}"
    workflows = list((ROOT / ".github" / "workflows").glob("*.yml"))
    assert len(workflows) == 1, "exactly one workflow: push-regression"


def test_r38_the_requirement_is_registered():
    """The contract text is in the protocol table - the author's
    patience clause on record verbatim."""
    proto = (ROOT / "md" / "protocol.md").read_text(encoding="utf-8")
    assert "| R-38 |" in proto
    assert "NOTHING verification-shaped runs locally" in proto
