"""Pin the addendum-90 refactor seams (addendum 87's contract style)."""
import argparse
import os
import sys

# mutmut's staging dir does not run the repo-root conftest.py, so the bare
# root-module imports (code_edit, full_benchmark, infra.*) resolve only when
# the paths are set explicitly (addenda 175/178 - the mutation-stats run
# crashed on each import in turn; both dirs go on the path).
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "AI_tools"))
sys.path.insert(0, os.path.join(_HERE, ".."))

import code_edit  # noqa: E402, I001
import full_benchmark as fb  # noqa: E402
import infra.hf_download as hf_download  # noqa: E402
import ruler_gate  # noqa: E402


def make_args(**kw):
    defaults = dict(
        families=["A/Qwen-A", "B/Qwen-B"],
        roster=None,
        rung=fb.RUNG_DEFAULT,
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



def test_check_requirements_passes_when_all_importable(capsys, monkeypatch):
    # pytest is a real distribution present in any interpreter running
    # this suite (importlib.metadata resolves pip names, not module names)
    monkeypatch.setattr(fb, "REQ_PACKAGES", ["pytest"])
    fb.check_requirements()
    out = capsys.readouterr().out
    assert "python :" in out

def test_check_requirements_fails_loud_when_a_package_is_missing(capsys, monkeypatch):
    # a distribution name that does not exist (importlib.metadata, not
    # find_spec - protobuf installs as google.protobuf, addendum 25 fix)
    monkeypatch.setattr(fb, "REQ_PACKAGES", ["definitely-not-a-real-package-xyz"])
    try:
        fb.check_requirements()
        raised = False
    except SystemExit as e:
        raised = "python3 -m pip install -r requirements.txt" in str(
            e
        ) and "definitely-not-a-real-package-xyz" in str(e)
    assert raised

def test_score_fwe_strips_template_debris():
    # ruling 1a (addendum 29/30): '<|im_end|>' debris must not fail an
    # otherwise-correct answer
    top_k = ["nysskz", "swucem", "tvjzpa"]
    ok, n = ruler_gate.score_fwe("nysskz, swucem, tvjzpa<|im_end|>", top_k)
    assert ok and n == 3
    # pure debris with no words still fails
    ok2, n2 = ruler_gate.score_fwe("<|im_end|>", top_k)
    assert not ok2 and n2 == 0

def test_score_fwe_one_third_pass_rule():
    # session 37, addendum 2 ruling (a): 1/3 or higher passes
    top_k = ["nysskz", "swucem", "tvjzpa"]
    ok, n = ruler_gate.score_fwe("only nysskz found", top_k)
    assert ok and n == 1

def test_resolve_f16_local_never_returns_a_quantized_file(tmp_path):
    # the MiniCPM-*-sft-bf16 bug (addendum 30): 'bf16' in the FAMILY
    # name made the family's own -Q8_0.gguf match the f16 glob
    famdir = tmp_path / "MiniCPM-1B-sft-bf16"
    famdir.mkdir()
    (famdir / "MiniCPM-1B-sft-bf16-Q8_0.gguf").write_text("x")
    assert hf_download.resolve_f16_local(str(famdir)) is None
    (famdir / "MiniCPM-1B-sft-bf16-f16.gguf").write_text("x")
    got = hf_download.resolve_f16_local(str(famdir))
    assert got and got.endswith("MiniCPM-1B-sft-bf16-f16.gguf")
