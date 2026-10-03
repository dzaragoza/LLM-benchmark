"""ruler_gate tests (addendum 128): the quality-at-depth gate -
RULER FWE through llama-server, the depth grid budgeted by
/tokenize. Niah tests removed with the task (session 37, addendum 3).
"""




import ruler_gate as rg


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


def test_fwe_scoring_relaxed_one_third():
    # session 37, addendum 2 ruling (a): >= 1/3 words is a pass;
    # partial retrieval counts, the parametric-word 0/3 still fails
    ok, partial = rg.score_fwe("the top words are: alphaone", ["alphaone", "betatwo", "gammathree"])
    assert ok is True and partial == 1
    ok, partial = rg.score_fwe("alphaone betatwo", ["alphaone", "betatwo", "gammathree"])
    assert ok is True and partial == 2
    ok, partial = rg.score_fwe("alphaone betatwo gammathree", ["alphaone", "betatwo", "gammathree"])
    assert ok is True and partial == 3
    # parametric-word failure (the paper's signature): scores zero
    ok, partial = rg.score_fwe("the a and of", ["alphaone", "betatwo", "gammathree"])
    assert ok is False and partial == 0


def test_build_fwe_task_top_k_override():
    import ruler_gate

    assert ruler_gate.build_fwe_task.__defaults__ == (ruler_gate.FWE_TOP_K,)
    sig = ruler_gate.build_fwe_task.__code__
    assert "top_k" in sig.co_varnames
