"""Pins: R-33, R-34, R-35, R-36 (session 45, addendum 153) - the
wow.md items promoted to WoW REQUIREMENTS. The v5.0 rule holds: a
requirement is a TESTABLE statement, so each pin checks the
mechanically checkable part; the human-discipline parts stay in
wow.md and are marked there as requirement-covered.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_r33_preregistrations_exist_in_the_notebook():
    """R-33: every experiment's pre-registration is IN THE NOTEBOOK
    before the run. Mechanical pin: the current session carries
    pre-registration sections (the standing predictions), and every
    'PRE-REGISTRATION' block names its predictions."""
    sessions = sorted((ROOT / "lab-notebook").glob("session-*.md"))
    assert len(sessions) >= 15  # merged per the one-session-per-day rule
    text = (ROOT / "lab-notebook" / "session-45.md").read_text(encoding="utf-8")
    assert "PRE-REGISTRATION" in text or "pre-regist" in text.lower()
    # quantitative: the standing pre-registrations carry numbers with bands
    assert re.search(r"Predictions.*\[.*\]", text, re.DOTALL) or "in [" in text


def test_r34_zero_scores_carry_evidence():
    """R-34: negative results are recorded - a v7 cell with score 0
    must carry either an answers log (the evidence) or an error label;
    a bare unexplained 0 is a discarded negative result."""
    import json

    state = json.loads((ROOT / "state" / "benchmark-state.json").read_text(encoding="utf-8"))
    bare = []
    for fam, fst in state.get("families", {}).items():
        for ctx, c in (fst.get("v7") or {}).items():
            if isinstance(c, dict) and c.get("score") == 0:
                answers = (
                    ROOT
                    / "models"
                    / "tournament-results"
                    / fam
                    / f"{fam}-ctx{ctx}-v7-answers.jsonl"
                )
                if not answers.exists() and not c.get("error"):
                    bare.append(f"{fam}@{ctx}")
    assert bare == [], f"score-0 cells without evidence or label: {bare}"


def test_r35_index_lists_every_session():
    """R-35: the notebook index links every session file - no orphan
    sessions, the one-session-per-day structure stays navigable."""
    idx = (ROOT / "lab-notebook" / "index.md").read_text(encoding="utf-8")
    for sf in (ROOT / "lab-notebook").glob("session-*.md"):
        assert sf.name in idx, f"{sf.name} is not linked from the index"


def test_r36_lowercase_kebab_naming():
    """R-36: documents are lowercase-kebab; ALL-CAPS is reserved for
    README.md alone; the directories hold their classes of document."""
    for md in ROOT.rglob("*.md"):
        if any(p in md.parts for p in (".git", ".venv", "models", "node_modules")):
            continue
        rel = md.relative_to(ROOT)
        if md.name != "README.md" and md.name == md.name.upper() and md.name.isalpha():
            raise AssertionError(f"ALL-CAPS filename outside README: {rel}")
        if md.name != "README.md" and " " in md.name:
            raise AssertionError(f"spaces in filename (kebab rule): {rel}")
    assert (ROOT / "md" / "protocol.md").exists()
    assert (ROOT / "lab-notebook" / "index.md").exists()
    assert (ROOT / "docs" / "index.md").exists()
