"""The ARC-jobs filter (addendum 87).

Addendum 86: ARC runs on EVERY benched family - PASS or FAIL verdict
alike; the only skip is an already-complete CSV (checked inside
arc_eval.arc_run, not here). Infeasible cells (no file) and
not-yet-benched cells are excluded.
"""

import pytest

import full_benchmark as fb


@pytest.fixture
def state():
    return {
        "families": {
            # PASS with a file -> ARC
            "A": {
                "runs": {"Q8_0": {"file": "a.gguf", "verdict": "PASS (confident)"}},
                "selected": "Q8_0",
            },
            # FAIL with a file -> ARC (the standing ruling, made structural)
            "B": {"runs": {"Q8_0": {"file": "b.gguf", "verdict": "FAIL — reader-wall"}}},
            # infeasible -> no file, no bench happened -> skip
            "C": {"runs": {"Q8_0": {"verdict": "FAIL (infeasible: exceeds system RAM)"}}},
            # benched? no verdict yet -> skip
            "D": {"runs": {"Q8_0": {"file": None, "verdict": None}}},
            # file but no verdict (phase 4 not reached) -> skip
            "E": {"runs": {"Q8_0": {"file": "e.gguf"}}},
        }
    }


def test_pass_and_fail_both_arc(state):
    jobs = fb.collect_arc_jobs(state)
    assert [(f, r) for f, r, _ in jobs] == [("A", "Q8_0"), ("B", "Q8_0")]


def test_infeasible_and_unbenched_skipped(state):
    fams = {f for f, _, _ in fb.collect_arc_jobs(state)}
    assert "C" not in fams and "D" not in fams and "E" not in fams


def test_roster_filters(state):
    jobs = fb.collect_arc_jobs(state, roster=["B"])
    assert [(f, r) for f, r, _ in jobs] == [("B", "Q8_0")]
    assert fb.collect_arc_jobs(state, roster=["C"]) == []


def test_empty_state():
    assert fb.collect_arc_jobs({"families": {}}) == []


def test_jobs_carry_the_run_records(state):
    """The job tuples carry the run dict itself - arc_run needs
    run['file']."""
    for _, _, run in fb.collect_arc_jobs(state):
        assert run.get("file")
