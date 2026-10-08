"""Pins: R-25 (session 44, addendum 125). Partial credit scoring.

The author: "Partial credit it is." The strict all-names rule left
every pilot cell at 0 while models traced parts of the chain
(Qwen3.5-0.8B ctx=32768: 44/400 answers had >=1 name, 0/400 had
all). A question now earns found/(h+1); a grade's rate is the mean
credit; the cell score sums the grade rates. `pass` (all names)
stays in the record - the strict signal rides along.
"""

import bench.v7 as v7


def test_partial_credit_scores_partial_traces(monkeypatch):
    """A model that finds 1 of 3 names earns 1/3, not 0."""
    corpus = {
        "sentences": ["x"],
        "questions": [
            {"span": 1024, "hops": 2, "names": ["AAAAA", "BBBBB", "CCCCC"], "value": "1"}
        ],
        "cuts": {1024: 1},
        "s_max": 1,
    }
    monkeypatch.setattr(v7.ruler_gate, "ask", lambda *a, **k: "AAAAA only")
    monkeypatch.setattr(v7.ruler_gate, "score_vt", lambda a, e: (False, 1))
    rec = v7.run_cell(0, corpus, window=4096)
    assert rec["score"] == round(1 / 3, 3)
    g = rec["per_grade"]["1024x2"]
    assert g["pass"] == 0 and g["asked"] == 1
    assert g["credit"] == round(1 / 3, 3)


def test_full_pass_still_scores_one(monkeypatch):
    monkeypatch.setattr(v7.ruler_gate, "ask", lambda *a, **k: "AAAAA BBBBB CCCCC")
    monkeypatch.setattr(v7.ruler_gate, "score_vt", lambda a, e: (True, 3))
    corpus = {
        "sentences": ["x"],
        "questions": [
            {"span": 1024, "hops": 2, "names": ["AAAAA", "BBBBB", "CCCCC"], "value": "1"}
        ],
        "cuts": {1024: 1},
        "s_max": 1,
    }
    rec = v7.run_cell(0, corpus, window=4096)
    assert rec["score"] == 1.0


def test_clean_wipes_all_cells_and_logs_up_front(tmp_path, monkeypatch):
    """Pins: R-25 (session 44, addendum 129). --clean wipes EVERY
    family's v7 block and every answer log BEFORE any measuring -
    per-cell cleaning left mixed-era records for families not yet
    reached; the author's rule is never leave mixed results."""

    state = {
        "families": {
            "FamA": {"v7": {"8192": {"score": 0.5}}},
            "FamB": {"v7": {"16384": {"score": 0.1}}, "other": "keep"},
        }
    }
    for fam in ("FamA", "FamB"):
        d = tmp_path / "tournament-results" / fam
        d.mkdir(parents=True)
        (d / f"{fam}-ctx8192-v7-answers.jsonl").write_text("{}\n")
        (d / f"{fam}-other.csv").write_text("keep\n")
    spath = tmp_path / "state.json"

    def boom(*a, **k):
        raise AssertionError("clean must finish before any measuring")

    monkeypatch.setattr(v7, "greedy_allocations", boom)
    try:
        v7.certify_v7(
            str(tmp_path),
            state,
            str(spath),
            0,
            dry_run=True,
            budget_gib=4.0,
            roster_limit=1,
            on_cell_commit=None,
            clean=True,
        )
    except AssertionError as e:
        assert "before any measuring" in str(e), "the boom must be the measuring gate"
    else:
        raise AssertionError("greedy_allocations must still be called (post-clean)")
    assert "v7" not in state["families"]["FamA"]
    assert "v7" not in state["families"]["FamB"]
    assert state["families"]["FamB"]["other"] == "keep", "non-v7 state survives"
    for fam in ("FamA", "FamB"):
        d = tmp_path / "tournament-results" / fam
        assert not list(d.glob("*v7-answers.jsonl")), "answer logs wiped"
        assert (d / f"{fam}-other.csv").exists(), "non-v7 artifacts survive"
