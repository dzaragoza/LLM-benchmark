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
    """A grade is EXCLUDED when its whole request cannot fit the
    window (R-19 with the session-44 honesty fix): span + prompt
    overhead + generation headroom <= window. The 1024 grade needs
    1024+128+192 tokens, so a 1024 window sees NOTHING (the crash of
    the first live run: the span-2048 grade HTTP-400'd at ctx=2048);
    a 2048 window sees only the 1024 grades - no 2048 keys."""
    asked = []

    def fake_ask(port, prompt, max_tokens=64, no_thinking=True):
        asked.append(prompt)
        return ""

    monkeypatch.setattr(v7.ruler_gate, "ask", fake_ask)
    rec = v7.run_cell(0, small_corpus, window=1024)
    assert rec["per_grade"] == {} and rec["max_score"] == 0
    rec = v7.run_cell(0, small_corpus, window=2048)
    grades = {k for k in rec["per_grade"]}
    assert all(k.startswith("1024x") for k in grades)
    assert rec["max_score"] == 2  # the two 1024 grades (hops 2, 4)
    assert len(asked) == 2  # addendum 123: K=1 x 2 hop grades


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

    rec = v7.run_cell(0, c, window=4096)
    assert rec["max_score"] == 4  # both spans, both hop grades
    # addendum 123: K=1 flat - every asked grade is asked exactly once
    for g in rec["per_grade"].values():
        assert g["asked"] == 1
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
    rec = v7.run_cell(0, c, window=4096)
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
    grid = {
        "spans": v7.SPANS,
        "hops": v7.HOPS,
        "seed": v7.CORPUS_SEED,
        "s_max": v7.S_MAX,
    }
    art.write_text(json.dumps({"grid": grid, "corpus": corpus}), encoding="utf-8")
    assert v7.corpus_from_artifact(0) == corpus


def test_run_cell_reports_window(monkeypatch, small_corpus):
    """The record carries the window it was graded at - a score is
    only interpretable against its exclusion set."""
    monkeypatch.setattr(v7.ruler_gate, "ask", lambda *a, **k: "")
    rec = v7.run_cell(0, small_corpus, window=1024)
    assert rec["window"] == 1024


def test_grade_reachable_counts_the_whole_request():
    """The session-44 crash regression: reachability must account for
    the template + query tail (PROMPT_OVERHEAD_TOKENS) and the
    generation headroom the server reserves - span == window is NOT
    reachable (the first live run HTTP-400'd exactly there:
    2048 prefix + template = 2237 tokens vs a 2048 window)."""
    assert not v7.grade_reachable(2048, 2, 2048)
    assert not v7.grade_reachable(1024, 2, 1024)
    assert v7.grade_reachable(2048, 2, 4096)
    assert v7.grade_reachable(1024, 2, 2048)
    # the deepest generation demand still fits a window with margin
    assert v7.grade_reachable(1024, 32, 2048)


def test_argmax_excludes_empty_cells():
    """Pins: R-19 (session 44). A cell with no reachable grades
    (max_score 0, score 0.0 - every ctx=2048 cell after the honesty
    fix) is EXCLUDED from the ranking, not treated as a measured
    zero: the argmax filter requires asked grades."""
    assert v7.grade_reachable(2048, 2, 2048) is False
    # the summary-side guard lives in full_benchmark's _run; the
    # exclusion rule itself is what the argmax consults


# ---- layer 3: the boundary integration test - a fake server with the ----
# ---- real 400 semantics must agree with grade_reachable at EVERY pair ----


class FakeWindowServer:
    """The simulated llama-server: tokenizes (1 token/4 chars, like the
    corpus fixtures) and 400s any request whose prompt + max_tokens
    exceed the window - the exact semantics that produced the
    session-44 crash."""

    def __init__(self, window):
        self.window = window
        self.rejected = []

    def tokenize(self, port, content, timeout=300):
        return [0] * (len(content) // 4)

    def ask(self, port, prompt, max_tokens=64, no_thinking=True):

        toks = len(self.tokenize(port, prompt))
        if toks + max_tokens > self.window:
            self.rejected.append((toks, max_tokens))
            raise ValueError(
                f"HTTP 400 from the server: request ({toks} tokens) exceeds "
                f"the available context size ({self.window} tokens)"
            )
        return ""


def test_run_cell_never_sends_an_overwide_request(monkeypatch, small_corpus):
    """THE session-44 lesson, end to end: for every (window, grade) pair
    on the fixture grid, run_cell must never emit a request the server
    would 400 - reachability and the server's accounting agree. The
    old span<=window rule fails this at span==window (the exact live
    crash); the honest rule passes at every pair."""
    from bench import v7 as v7m

    for window in (1024, 2048, 4096, 8192):
        server = FakeWindowServer(window)
        monkeypatch.setattr(v7m.ruler_gate, "ask", server.ask, raising=False)
        # keep the corpus fixture's tokenize active for any preflight
        rec = v7m.run_cell(0, small_corpus, window=window)
        assert server.rejected == [], (
            f"window {window}: server 400'd {server.rejected} - "
            f"reachability disagrees with the server"
        )
        # the asked grades are exactly the reachable ones
        reachable = {
            f"{q['span']}x{q['hops']}"
            for q in small_corpus["questions"]
            if v7m.grade_reachable(q["span"], q["hops"], window)
        }
        assert set(rec["per_grade"]) == reachable


def test_preflight_catches_estimate_drift(monkeypatch, small_corpus):
    """Layer 1's own regression: when the arithmetic says a grade fits
    but the measured prompt does not (the constants drifted from the
    tokenizer), preflight_reachable_grades raises PreflightError
    naming the grade - BEFORE any question is asked."""
    from bench import v7 as v7m

    window = 4096  # the arithmetic says span 2048 fits comfortably

    # a hostile tokenizer: 10 tokens per char - massive drift
    def hostile_tokenize(port, content, timeout=300):
        return [0] * (len(content) * 10)

    monkeypatch.setattr(v7m.llama_server, "tokenize", hostile_tokenize)
    with pytest.raises(v7m.PreflightError) as e:
        v7m.preflight_reachable_grades(0, small_corpus, window)
    assert "2048x" in str(e.value) or "1024x" in str(e.value)


def test_preflight_passes_when_honest(monkeypatch, small_corpus):
    from bench import v7 as v7m

    monkeypatch.setattr(v7m.llama_server, "tokenize", _fake_tokenize_factory(None))
    window = 8192
    got = v7m.preflight_reachable_grades(0, small_corpus, window)
    assert got and all(t > 0 for t in got.values())


def test_every_answer_is_logged(tmp_path, monkeypatch, small_corpus):
    """Pins: R-23. EVERY answer is logged, one JSON line per question -
    answers are always important for debugging. The file carries the
    grade, the expected names, the found count, and the RAW answer;
    the line count equals the asked questions; the ok flags agree
    with the scorer."""
    import json as _json

    from bench import v7 as v7m

    calls = {"n": 0}

    def fake_ask(port, prompt, max_tokens=64, no_thinking=True):
        calls["n"] += 1
        return "AAAAA BBBBB" if calls["n"] % 3 else ""

    monkeypatch.setattr(v7m.ruler_gate, "ask", fake_ask)
    path = tmp_path / "answers.jsonl"
    rec = v7m.run_cell(0, small_corpus, window=4096, answers_path=str(path))
    lines = path.read_text().splitlines()
    assert len(lines) == sum(g["asked"] for g in rec["per_grade"].values()) == calls["n"]
    for ln in lines:
        row = _json.loads(ln)
        assert {"window", "grade", "expected", "value", "found", "ok", "answer"} <= set(row)
    oks = [_json.loads(ln)["ok"] for ln in lines]
    passes = sum(1 for g in rec["per_grade"].values() for _ in range(g["pass"]))
    assert sum(oks) == passes


def test_answers_log_is_append_per_cell(tmp_path, monkeypatch, small_corpus):
    """Pins: R-23. A re-run of the same cell APPENDS - reruns never
    destroy the previous evidence (the resumable-store principle
    applied to answers)."""

    from bench import v7 as v7m

    monkeypatch.setattr(v7m.ruler_gate, "ask", lambda *a, **k: "")
    path = tmp_path / "answers.jsonl"
    v7m.run_cell(0, small_corpus, window=4096, answers_path=str(path))
    first = len(path.read_text().splitlines())
    v7m.run_cell(0, small_corpus, window=4096, answers_path=str(path))
    assert len(path.read_text().splitlines()) == 2 * first
