"""ruler_gate.py (addendum 128): the quality-at-depth gate - RULER-style
needle-in-a-haystack through llama-server, the depth grid budgeted by
/tokenize. Task shape and scoring are pinned here; server-dependent
paths are monkeypatched, the repo's established test style."""

import random

import pytest

import ruler_gate as rg


def test_needle_shape_is_ruler_reference():
    assert rg.make_needle("alpha", "12345") == (
        "One of the special magic numbers for alpha is: 12345."
    )


def test_query_shape():
    assert "magic number for alpha" in rg.QUERY_TEMPLATE.format(key="alpha")


def test_score_answer_substring_tolerant():
    assert rg.score_answer("The number is 12 345.", "12345")
    assert not rg.score_answer("The number is 99999.", "12345")


def test_haystack_sentences_no_meltdown():
    paras = rg.haystack_paragraphs(random.Random(1024), 500)
    assert len(paras) == 500
    assert all(p.endswith(".") for p in paras)
    joined = " ".join(paras)
    assert "magic" not in joined


def test_needle_word_absent_from_haystack_word_bank():
    assert "magic" not in rg.WORD_BANK


def test_build_task_budget_enforced(monkeypatch):
    calls = {}

    def fake_tokenize(port, content, timeout=300):
        calls.setdefault("n", 0)
        calls["n"] += 1
        return [0] * max(1, len(content) // 4)

    monkeypatch.setattr(rg.llama_server, "tokenize", fake_tokenize)
    monkeypatch.setattr(
        rg.llama_server,
        "trim_to_tokens",
        lambda port, text, target, tolerance=8, max_iter=24: (text[: target * 4], target),
    )
    prompt, answers = rg.build_task(port=0, depth_tokens=1000, n_needles=4, seed=7)
    assert "magic number" in prompt
    assert prompt.index("magic number") < len(prompt) - 10
    assert len(answers) == 4
    for v in answers.values():
        assert v.isdigit()


def test_build_task_refuses_tiny_depth(monkeypatch):
    def fake_tokenize(port, content, timeout=300):
        return [0] * max(1, len(content) // 4)

    monkeypatch.setattr(rg.llama_server, "tokenize", fake_tokenize)
    monkeypatch.setattr(
        rg.llama_server,
        "trim_to_tokens",
        lambda port, text, target, tolerance=8, max_iter=24: (text, target),
    )
    with pytest.raises(ValueError, match="raise the depth"):
        rg.build_task(port=0, depth_tokens=100, n_needles=4, seed=7)


def test_run_depth_csv_roundtrip(tmp_path, monkeypatch):
    def fake_build_task(port, depth, n_needles, seed):
        return ("haystack ... needle", {"alpha": "12345"})

    monkeypatch.setattr(rg, "build_task", fake_build_task)
    monkeypatch.setattr(rg, "ask", lambda port, prompt, max_tokens=64, no_thinking=True: "12345")
    csv_path = str(tmp_path / "m-4096-niah.csv")
    row = rg.run_depth(0, "m", 4096, 3, 4, csv_path)
    assert row == {"label": "m", "depth": 4096, "n": 3, "correct": 3, "acc": 1.0}
    import csv

    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3
    assert all(r["correct"] == "1" for r in rows)
    cached = rg.run_depth(0, "m", 4096, 3, 4, csv_path)
    assert cached == row


def test_run_depth_mixed_answers(tmp_path, monkeypatch):
    def fake_build_task(port, depth, n_needles, seed):
        return ("haystack", {"alpha": "11111"})

    answers = iter(["11111", "wrong", "11111"])
    monkeypatch.setattr(rg, "build_task", fake_build_task)
    monkeypatch.setattr(
        rg, "ask", lambda port, prompt, max_tokens=64, no_thinking=True: next(answers)
    )
    row = rg.run_depth(0, "m", 4096, 3, 4, str(tmp_path / "m.csv"))
    assert row["correct"] == 2 and abs(row["acc"] - 2 / 3) < 1e-9


def test_fwe_vocab_and_counts_follow_upstream_constants(monkeypatch):
    """FWE (addendum 136b): vocab size = depth/50, rank-0 is the '...'
    noise word, counts follow the Zeta law, the answer is ranks 1-3."""

    monkeypatch.setattr(
        rg.llama_server,
        "tokenize",
        lambda port, content, timeout=300: [0] * max(1, len(content) // 4),
    )
    monkeypatch.setattr(
        rg.llama_server,
        "trim_to_tokens",
        lambda port, text, target, tolerance=8, max_iter=24: (text[: target * 4], target),
    )
    prompt, top_k = rg.build_fwe_task(port=0, depth_tokens=32768, seed=7)
    vocab_size = max(20, 32768 // 50)
    norm = sum(1.0 / (i**rg.FWE_ALPHA) for i in range(1, vocab_size + 1))
    counts = [int(5461 * (r + 1) ** -rg.FWE_ALPHA / norm) for r in range(vocab_size)]
    for rank, word in enumerate(top_k):
        assert word in prompt
        assert prompt.count(word) >= counts[rank + 1] - 20
    assert len(top_k) == rg.FWE_TOP_K
    # strictly decreasing counts => the top-3 are unambiguous even after trims
    assert counts[1] > counts[2] > counts[3] > counts[4]


def test_fwe_scoring_all_or_nothing_with_partial_diagnostic():
    ok, partial = rg.score_fwe("the top words are: alphaone", ["alphaone", "betatwo", "gammathree"])
    assert ok is False and partial == 1
    ok, partial = rg.score_fwe("alphaone betatwo gammathree", ["alphaone", "betatwo", "gammathree"])
    assert ok is True and partial == 3
    # parametric-word failure (the paper's signature): scores zero
    ok, partial = rg.score_fwe("the a and of", ["alphaone", "betatwo", "gammathree"])
    assert ok is False and partial == 0
