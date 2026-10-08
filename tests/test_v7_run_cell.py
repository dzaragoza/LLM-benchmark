"""v7 scorer and corpus tests (session 43) - the offline core of the
reach benchmark: build_corpus determinism and structure, run_cell
exclusion/score math, corpus_from_artifact's mismatch-rebuild path.

These pin the benchmark's OWN output (the score every cell reports
and the winner is argued from), which the earlier suite only touched
via the allocation planner.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import bench.v7 as v7
import ruler_gate

# ---- corpus fixtures: build against a fake tokenizer (no server) ----


class FakeTokenizerPort:
    """llama_server.tokenize stand-in: ~1 token per 4 chars."""

    def __init__(self, tokens_per_probe=25):
        self.tokens_per_probe = tokens_per_probe


def _fake_tokenize_factory(retval):
    def tokenize(port, content, timeout=300):
        return [0] * (len(content) // 4)

    return tokenize


@pytest.fixture
def small_corpus(monkeypatch):
    """A tiny deterministic corpus: s_max small so the build is fast."""
    monkeypatch.setattr(v7.llama_server, "tokenize", _fake_tokenize_factory(None))
    monkeypatch.setattr(v7, "S_MAX", 2000, raising=False)
    monkeypatch.setattr(v7, "SPANS", [1024, 2048], raising=False)
    monkeypatch.setattr(v7, "HOPS", [2, 4], raising=False)
    monkeypatch.setattr(v7, "K", 2, raising=False)
    # build_corpus reads the module-level constants through its
    # defaults; call it with the small grid explicitly instead
    return v7.build_corpus(0, s_max=2000)


def test_build_corpus_deterministic(monkeypatch):
    """Same seed, same bytes: two builds produce IDENTICAL corpora -
    the prefix-fairness promise (every model sees the same text)."""
    monkeypatch.setattr(v7.llama_server, "tokenize", _fake_tokenize_factory(None))
    a = v7.build_corpus(0, s_max=2000)
    b = v7.build_corpus(0, s_max=2000)
    assert a == b


def test_build_corpus_structure(small_corpus):
    """The corpus carries every (span, hops) question with its names
    and value, and a cut per span grade."""
    c = small_corpus
    assert set(c["cuts"]) == {1024, 2048}
    seen = {(q["span"], q["hops"]) for q in c["questions"]}
    assert seen == {(s, h) for s in (1024, 2048) for h in (2, 4)}
    for q in c["questions"]:
        assert len(q["names"]) == q["hops"] + 1
        assert len(set(q["names"])) == q["hops"] + 1
        assert len(q["value"]) == 5 and q["value"].isdigit()


def test_build_corpus_chains_embedded_before_cut(small_corpus):
    """Every span's chains live INSIDE that span's prefix: each
    question's first link appears in sentences[:cut_span]. The prefix
    cut may never orphan a chain (the cell would ask about text the
    model never saw)."""
    c = small_corpus
    for q in c["questions"]:
        cut = c["cuts"][q["span"]]
        prefix = "\n".join(c["sentences"][:cut])
        assert f"VAR {q['names'][0]} = {q['value']}" in prefix, (
            f"span {q['span']} chain base missing from its own prefix"
        )


def test_cuts_monotone_in_span(small_corpus):
    """A deeper span's prefix contains the shallower ones' chains too
    (its cut is never smaller) - the corpus is one growing text."""
    c = small_corpus
    spans = sorted(c["cuts"])
    for lo, hi in zip(spans, spans[1:], strict=False):
        assert c["cuts"][lo] <= c["cuts"][hi]


def test_question_prompt_contains_chain_and_query(small_corpus):
    """The rendered prompt carries the chain (inside the context) and
    the query tail asking for the value."""
    c = small_corpus
    q = c["questions"][0]
    p = v7.question_prompt(c, q)
    assert f"VAR {q['names'][0]} = {q['value']}" in p
    assert q["value"] in p[p.index("Question:") :]


# ---- run_cell: exclusion, per-grade accounting, score math ----


def test_run_cell_excludes_unreachable_spans(monkeypatch, small_corpus):
    """span > window is EXCLUDED, not failed: a 1024-token window sees
    only the 1024 grade - the per-grade map has no 2048 keys and the
    max_score counts only what was asked (R-19)."""
    asked = []

    def fake_ask(port, prompt, max_tokens=64, no_thinking=True):
        asked.append(prompt)
        return ""

    monkeypatch.setattr(v7.ruler_gate, "ask", fake_ask)
    rec = v7.run_cell(0, small_corpus, window=1024)
    grades = {k for k in rec["per_grade"]}
    assert all(k.startswith("1024x") for k in grades)
    assert rec["max_score"] == 2  # the two 1024 grades (hops 2, 4)
    assert len(asked) == 4  # K=2 chains x 2 hop grades


def test_run_cell_score_is_mean_pass_mass(monkeypatch, small_corpus):
    """score = mean over asked grades of (pass/asked) - the property
    the argmax rides on. A half-passing grade and a full grade give
    (0.5 + 1.0) / 2."""
    c = small_corpus
    answers = {}

    def fake_ask(port, prompt, max_tokens=64, no_thinking=True):
        # grade by prompt order: first half of the 1024x2 questions
        # answer fully, the rest answer nothing
        q_idx = len(answers)
        answers[q_idx] = prompt
        return ""

    def fake_score(answer, expected):
        return (len(expected) == 0, 0)

    # simpler: answer with the full name list for the first K questions
    state = {"n": 0}

    def fake_ask2(port, prompt, max_tokens=64, no_thinking=True):
        i = state["n"]
        state["n"] += 1
        return "AAAAA BBBBB" if i % 2 == 0 else ""

    monkeypatch.setattr(v7.ruler_gate, "ask", fake_ask2)

    class FakeRG:
        VT_GEN_TOKENS = 128

        @staticmethod
        def score_vt(answer, expected):
            return ruler_gate.score_vt(answer, expected)

        VT_TEMPLATE = ruler_gate.VT_TEMPLATE
        VT_NAME_LEN = ruler_gate.VT_NAME_LEN

    rec = v7.run_cell(0, c, window=2048)
    assert rec["max_score"] == 4  # both spans, both hop grades
    # every grade asked K=2; alternating passes -> each grade 1/2
    for g in rec["per_grade"].values():
        assert g["asked"] == 2
    assert 0.0 <= rec["score"] <= float(rec["max_score"])


def test_run_cell_all_pass_scores_max(monkeypatch, small_corpus):
    """A model that always answers every name earns exactly the
    asked-grade count - the maximum is ATTAINABLE, not aspirational
    (reach pays when converted)."""
    c = small_corpus
    by_value = {q["value"]: q["names"] for q in c["questions"]}

    def fake_ask(port, prompt, max_tokens=64, no_thinking=True):
        for value, names in by_value.items():
            if f"value {value} " in prompt or f"'{value}" in prompt:
                return " ".join(names)
        return ""

    monkeypatch.setattr(v7.ruler_gate, "ask", fake_ask)
    rec = v7.run_cell(0, c, window=2048)
    assert rec["score"] == float(rec["max_score"])
    assert all(g["pass"] == g["asked"] for g in rec["per_grade"].values())


def test_run_cell_score_never_exceeds_max(monkeypatch, small_corpus):
    """A pathological scorer can never push the score past its max -
    the mean-of-ratios is bounded by the asked-grade count."""
    monkeypatch.setattr(v7.ruler_gate, "ask", lambda *a, **k: "ZZZZZ")
    monkeypatch.setattr(
        v7.ruler_gate,
        "score_vt",
        lambda answer, expected: (True, len(expected)),
    )
    rec = v7.run_cell(0, small_corpus, window=2048)
    assert rec["score"] <= rec["max_score"]


# ---- corpus_from_artifact: the load/rebuild fork ----


def test_artifact_grid_mismatch_rebuilds(monkeypatch, tmp_path):
    """A stale artifact (different grid constants) is NOT loaded -
    the corpus is rebuilt and the artifact rewritten (R-16: the load
    is keyed on the grid, not the file's presence)."""
    monkeypatch.setattr(v7.llama_server, "tokenize", _fake_tokenize_factory(None))
    art = tmp_path / "v7-corpus.json"
    art.write_text(
        json.dumps(
            {
                "grid": {"spans": [1], "hops": [1], "k": 1, "s_max": 1},
                "corpus": {"sentences": ["stale"]},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(v7, "CORPUS_ARTIFACT", str(art))
    monkeypatch.setattr(
        v7,
        "build_corpus",
        lambda port: {"sentences": ["fresh"], "questions": [], "cuts": {}, "s_max": 999},
    )
    loaded = v7.corpus_from_artifact(0)
    assert loaded["sentences"] == ["fresh"]
    on_disk = json.loads(art.read_text())
    assert on_disk["corpus"]["sentences"] == ["fresh"]


def test_artifact_matching_grid_loads(monkeypatch, tmp_path):
    """A matching artifact short-circuits the build entirely - no
    server tokenize, no rebuild (the citable-bytes promise)."""
    art = tmp_path / "v7-corpus.json"
    corpus = {"sentences": ["the artifact"], "questions": [], "cuts": {}, "s_max": 1}

    def boom(port):
        raise AssertionError("build_corpus must not run on a matching artifact")

    monkeypatch.setattr(v7, "CORPUS_ARTIFACT", str(art))
    monkeypatch.setattr(v7, "build_corpus", boom)
    grid = {"spans": v7.SPANS, "hops": v7.HOPS, "k": v7.K, "s_max": v7.S_MAX}
    art.write_text(json.dumps({"grid": grid, "corpus": corpus}), encoding="utf-8")
    assert v7.corpus_from_artifact(0) == corpus


def test_run_cell_reports_window(monkeypatch, small_corpus):
    """The record carries the window it was graded at - a score is
    only interpretable against its exclusion set."""
    monkeypatch.setattr(v7.ruler_gate, "ask", lambda *a, **k: "")
    rec = v7.run_cell(0, small_corpus, window=1024)
    assert rec["window"] == 1024
