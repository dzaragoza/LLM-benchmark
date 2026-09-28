"""Pin the addendum-90 refactor seams (addendum 87's contract style)."""

import argparse
import copy

import full_benchmark as fb


def make_args(**kw):
    defaults = dict(
        families=["A/Qwen-A", "B/Qwen-B"],
        roster=None,
        arc_config="ARC-Challenge",
        arc_num=1172,
        arc_results_dir="arc-results-test",
        state_file="/tmp/unused-state.json",
        results_file="/tmp/unused-results.json",
    )
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def make_state():
    run_a = {
        "verdict": "PASS",
        "file": "./models/Qwen-A/A-Q8_0.gguf",
        "words_per_token_p05": 0.41,
    }
    run_b = {
        "verdict": "FAIL",
        "file": "./models/Qwen-B/B-Q8_0.gguf",
        "words_per_token_p05": 0.41,
    }
    return {
        "families": {
            "Qwen-A": {"spec": "A/Qwen-A", "selected": "Q8_0", "runs": {"Q8_0": run_a}},
            "Qwen-B": {"spec": "B/Qwen-B", "selected": None, "runs": {"Q8_0": run_b}},
            "Qwen-C": {
                "spec": "C/Qwen-C",
                "selected": None,
                "runs": {"Q8_0": {"verdict": "FAIL (infeasible: RAM)", "file": None}},
            },
        }
    }


def test_prepare_phase56_roster_defaults_to_families():
    roster, _, _ = fb.prepare_phase56(make_args(), make_state())
    assert roster == ["Qwen-A", "Qwen-B"]


def test_prepare_phase56_selections_only_selected_with_file():
    _, selections, _ = fb.prepare_phase56(make_args(), make_state())
    assert list(selections) == ["Qwen-A"]


def test_prepare_phase56_arc_jobs_skip_infeasible():
    _, _, arc_jobs = fb.prepare_phase56(make_args(), make_state())
    assert [(f, r) for f, r, _ in arc_jobs] == [
        ("Qwen-A", "Q8_0"),
        ("Qwen-B", "Q8_0"),
    ]


def test_prepare_phase56_roster_flag_filters():
    args = make_args(roster="Qwen-B, Qwen-C")
    roster, selections, arc_jobs = fb.prepare_phase56(args, make_state())
    assert roster == ["Qwen-B", "Qwen-C"]
    assert selections == {}
    assert [(f, r) for f, r, _ in arc_jobs] == [("Qwen-B", "Q8_0")]


def test_prepare_phase56_does_not_mutate_state():
    state = make_state()
    snapshot = copy.deepcopy(state)
    fb.prepare_phase56(make_args(), state)
    assert state == snapshot


def test_run_ranking_uses_selected_only_and_records(tmp_path):
    calls = []

    class FakeMcnemar:
        @staticmethod
        def rank(labels, arc_num, results_dir):
            calls.append(list(labels))
            return list(labels), {m: 0.5 for m in labels}, {}

    fb_mcnemar = fb.mcnemar
    fb.mcnemar = FakeMcnemar()
    try:
        state = make_state()
        _, selections, _ = fb.prepare_phase56(make_args(), state)
        args = make_args(state_file=str(tmp_path / "s.json"))
        fb.run_ranking(args, state, selections)
    finally:
        fb.mcnemar = fb_mcnemar
    assert calls == [["Qwen-A Q8_0"]]
    assert state["ranking"]["order"] == ["Qwen-A Q8_0"]
    assert state["ranking"]["scores"]["Qwen-A Q8_0"] == 0.5
