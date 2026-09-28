"""The dry-run plan classifier and runtime estimator (addendum 87).

The addendum-83 bug class: "download f16 from ..." must classify as
f16_quantize BEFORE the plain-download match, or every f16 cell is
underestimated at 30 instead of 45 min.
"""

import pytest

import full_benchmark as fb


@pytest.mark.parametrize("plan,expected", [
    ("local file ./models/A/A-Q8_0.gguf", "local"),
    # the order bug the tests pin: f16 BEFORE download
    ("download f16 from org/repo, quantize", "f16_quantize"),
    ("download org/repo/file-Q8_0.gguf", "download"),
    ("safetensors from org/repo, convert + quantize",
     "convert_quantize"),
    ("pytorch_model.bin from org/repo, convert + quantize",
     "convert_quantize"),
    ("something never seen before", "unknown"),
])
def test_classify_plan(plan, expected):
    assert fb.classify_plan(plan) == expected


def mock_state():
    return {"families": {
        "A": {"runs": {"Q8_0": {
            "plan": "local file ./models/A/A-Q8_0.gguf",
            "verdict": "PASS (confident)"}}},
        "B": {"runs": {"Q8_0": {
            "plan": "download f16 from org/b, quantize",
            "verdict": "FAIL — reader-wall"}}},
        "C": {"runs": {"Q8_0": {
            "plan": "safetensors from org/c, convert + quantize",
            "verdict": "PASS (confident)"}}},
        "D": {"runs": {"Q8_0": {
            "plan": "infeasible: Q8_0 exceeds system RAM",
            "verdict": "FAIL (infeasible: exceeds system RAM)"}}},
        "E": {"runs": {"Q8_0": {"phases_done": []}}},
    }}


def test_estimate_runtime_classes_and_total():
    counts, total = fb.estimate_runtime(mock_state())
    assert counts == {"local": 1, "f16_quantize": 1, "convert_quantize": 1}
    assert total == fb.PLAN_COST_MIN["local"] \
        + fb.PLAN_COST_MIN["f16_quantize"] \
        + fb.PLAN_COST_MIN["convert_quantize"]


def test_estimate_excludes_infeasible_and_unplanned():
    """Infeasible cells cost nothing (the addendum-35 guard skips them
    pre-download); families with no plan yet are not counted."""
    counts, _ = fb.estimate_runtime(mock_state())
    assert sum(counts.values()) == 3


def test_estimate_empty_state():
    assert fb.estimate_runtime({"families": {}}) == ({}, 0)


def test_plan_costs_are_registered_brackets():
    """The run-1 measured brackets (addendum 83) - the report's
    arithmetic depends on these exact values."""
    assert fb.PLAN_COST_MIN == {
        "local": 15, "download": 30, "f16_quantize": 45,
        "convert_quantize": 60, "unknown": 45,
    }
