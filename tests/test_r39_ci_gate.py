"""Pins: R-39 (session 45, addendum 160) - the CI verdict gates every
git command: before ANY git operation the agent checks the latest
COMPLETED push-regression verdict and fixes red issues first. The
structural pin: the requirement is registered, and the workflow that
produces the verdict is pinned to exist and run on every push. The
behavioral discipline (check before every git command) is the
author-facing contract, graded in conversation.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_r39_the_requirement_is_registered():
    proto = (ROOT / "md" / "protocol.md").read_text(encoding="utf-8")
    assert "| R-39 |" in proto
    assert "Before ANY git command" in proto


def test_r39_the_verdict_source_exists():
    """The push-regression workflow runs on every push - the verdict
    the rule checks is always being produced."""
    wf = (ROOT / ".github" / "workflows" / "push-regression.yml").read_text(encoding="utf-8")
    assert "on:" in wf and "push:" in wf and "branches: [main]" in wf
    assert "requirements_check" in wf, "the verdict includes the traceability gate"
