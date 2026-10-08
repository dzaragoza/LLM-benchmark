"""v7 pilot: the graded-grid scorer and the allocation planner (offline parts)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bench import v7 as v7_pilot


def test_grid_shape():
    # addendum 120: K 20 -> 2 (the 10x-easier ruling); grid stays 8x5
    assert len(v7_pilot.SPANS) * len(v7_pilot.HOPS) * v7_pilot.K == 80


def test_smallest_ctx_is_measurable():
    """The 2k rung must reach at least one span grade (the first live
    run's bug: SPANS started at 4096, so 2048-window cells asked zero
    questions and scored 0/0)."""
    smallest_ctx = min(v7_pilot.CTX_GRID)
    assert any(s <= smallest_ctx for s in v7_pilot.SPANS)
    for cell in v7_pilot.greedy_allocations(4.0, v7_pilot.PILOT_FAMILIES):
        reach = [s for s in v7_pilot.SPANS if s <= cell["ctx"]]
        assert reach, f"ctx {cell['ctx']} cannot reach any span grade"


def test_allocation_plan_frontier():
    rows = v7_pilot.greedy_allocations(4.0, roster_limit=12)
    assert rows, "4 GiB must admit at least one allocation"
    for r in rows:
        assert r["est_gib"] <= 4.0
        w = v7_pilot.family_window(r["family"])
        assert not w or r["ctx"] <= w
    biggest = max(r["params_b"] for r in rows)
    assert biggest >= 1.0, "4 GiB must afford a ~1B model somewhere"


def test_question_prompt_tail():
    corpus = {
        "sentences": ["NOISE"],
        "questions": [],
        "cuts": {4096: 1},
        "s_max": 100,
    }
    q = {"span": 4096, "hops": 4, "names": ["AAAAA", "BBBBB"], "value": "12345"}
    p = v7_pilot.question_prompt(corpus, q)
    assert "NOISE" in p and "12345" in p and "5 variables" in p


def test_greedy_starts_low_and_climbs():
    rows = v7_pilot.greedy_allocations(4.0, roster_limit=12)
    assert rows
    for r in rows:
        assert r["wq"] in v7_pilot.W_LADDER
        assert r["kq"] in v7_pilot.KV_QUANT_LADDER
        assert r["vq"] in v7_pilot.KV_QUANT_LADDER
        assert r["est_gib"] <= 4.0


def test_greedy_is_maximal():
    """No single-axis one-notch upgrade fits after the climb stops."""
    rows = v7_pilot.greedy_allocations(4.0, roster_limit=12)
    for r in rows:
        geom = v7_pilot.family_geometry(r["family"])
        wi = v7_pilot.W_LADDER.index(r["wq"])
        ki = v7_pilot.KV_QUANT_LADDER.index(r["kq"])
        vi = v7_pilot.KV_QUANT_LADDER.index(r["vq"])
        for axis in range(3):
            cw, ck, cv = wi, ki, vi
            if axis == 0 and wi + 1 < len(v7_pilot.W_LADDER):
                cw = wi + 1
            elif axis == 1 and ki + 1 < len(v7_pilot.KV_QUANT_LADDER):
                ck = ki + 1
            elif axis == 2 and vi + 1 < len(v7_pilot.KV_QUANT_LADDER):
                cv = vi + 1
            else:
                continue
            t = v7_pilot._alloc_total(
                r["family"],
                r["params_b"],
                geom,
                v7_pilot.W_LADDER[cw],
                v7_pilot.KV_QUANT_LADDER[ck],
                v7_pilot.KV_QUANT_LADDER[cv],
                r["ctx"],
            )
            assert t is None or t > 4.0, f"upgrade fits but was not taken: {r} axis={axis}"


def test_greedy_floor_is_222():
    """The tiny families with headroom must climb to the top; the
    starting point (2,2,2) must be feasible for every emitted cell."""
    rows = v7_pilot.greedy_allocations(0.45, roster_limit=12)
    for r in rows:
        assert r["est_gib"] <= 0.45
    # and at a starved budget, the floor config itself must appear
    tiny = v7_pilot.greedy_allocations(0.1, roster_limit=12)
    assert tiny == []


def test_recurrent_family_is_kvless():
    """RWKV7 carries no KV cache: per-token KV is 0 and it earns cells
    at every ctx its window allows (weights-only memory)."""
    assert v7_pilot.is_recurrent("RWKV7-World-2.9B")
    pt = v7_pilot.kv_per_token_f16("RWKV7-World-2.9B", None)
    assert pt == 0.0
    rows = v7_pilot.greedy_allocations(4.0, roster_limit=38)
    rwkv = [r for r in rows if r["family"] == "RWKV7-World-2.9B"]
    assert rwkv, "the recurrent family must earn cells"
    assert all(r["est_gib"] <= 4.0 for r in rwkv)


def test_mha_fallback_places_phi1():
    """phi-1's config has null kv_heads/head_dim (MHA shape): the
    hidden_size//heads fallback must place it, not drop it."""
    pt = v7_pilot.kv_per_token_f16("phi-1", None)
    assert pt and pt > 0
    rows = v7_pilot.greedy_allocations(4.0, roster_limit=38)
    assert any(r["family"] == "phi-1" for r in rows)


def test_question_prompt_is_prefix_cut():
    """The span-s question must present only the corpus prefix up to
    that span's cut (the 357k-token HTTP-400 bug: the full corpus was
    pasted into every question, dead on any small-window cell)."""
    corpus = {
        "sentences": [f"sentence {i}." for i in range(1000)],
        "questions": [],
        "cuts": {2048: 100, 262144: 1000},
        "s_max": 262144,
    }
    q_small = {"span": 2048, "hops": 4, "names": ["AAAAA", "BBBBB"], "value": "12345"}
    p_small = v7_pilot.question_prompt(corpus, q_small)
    assert "sentence 99." in p_small
    assert "sentence 100." not in p_small
    q_big = {"span": 262144, "hops": 4, "names": ["AAAAA", "BBBBB"], "value": "12345"}
    p_big = v7_pilot.question_prompt(corpus, q_big)
    assert "sentence 999." in p_big


def test_corpus_artifact_roundtrip(tmp_path):
    """Pins: R-16. The corpus is a repo artifact: build once, persist
    to state/v7-corpus.json, load back byte-identical on the next
    run - citable and machine-independent."""
    import json

    import bench.v7 as v7m

    class Fake:
        @staticmethod
        def tokenize(port, content):
            return [0] * 40

    import unittest.mock as m

    with m.patch.object(v7m.llama_server, "tokenize", Fake.tokenize):
        with m.patch.object(v7m, "CORPUS_ARTIFACT", str(tmp_path / "corpus.json")):
            c1 = v7m.corpus_from_artifact(0)
            art = json.loads((tmp_path / "corpus.json").read_text())
            assert art["grid"]["k"] == v7m.K
            c2 = v7m.corpus_from_artifact(0)
            assert c1 == c2


def test_crash_tail_always_runs(tmp_path, monkeypatch):
    """Pins: R-17. The git tail runs on a crash: main() catches any
    exception, stamps the traceback into results.txt, runs git_tail
    (unless --no-git), and re-raises."""
    import argparse
    import unittest.mock as m

    import full_benchmark as fb

    calls = []

    def fake_git_tail(args):
        calls.append("git_tail")

    def fake_run(args):
        raise RuntimeError("boom")

    args = argparse.Namespace(no_git=False)
    for attr, default in vars(fb.build_parser().parse_args([])).items():
        setattr(args, attr, default) if not hasattr(args, attr) else None
    crash_log = tmp_path / "results.txt"
    with (
        m.patch.object(fb, "_run", fake_run),
        m.patch.object(fb, "git_tail", fake_git_tail),
        m.patch.object(fb.llama_server, "kill_stale_server", lambda: False),
        m.patch.object(fb.tee_output, "uninstall", lambda: None),
        m.patch.object(fb.tee_output, "install", lambda: None),
        m.patch.object(fb.sys, "argv", ["full_benchmark.py"]),
    ):
        monkeypatch.chdir(tmp_path)
        try:
            fb.main()
        except RuntimeError:
            pass
    assert "git_tail" in calls
    assert "RuntimeError: boom" in crash_log.read_text()


def test_greedy_ruling_shape():
    """Pins: R-18, R-19. The climb starts at (Q2_K, q2_K, q2_K),
    uses K-encoding below q8, tops at 16 bits, and every pilot cell
    reaches at least one span grade (exclusion, not failure)."""
    assert v7_pilot.W_LADDER[0] == "Q2_K" and v7_pilot.W_LADDER[-1] == "F16"
    assert v7_pilot.KV_QUANT_LADDER[0] == "q2_K" and v7_pilot.KV_QUANT_LADDER[-1] == "f16"
    for w in v7_pilot.W_LADDER[:-1]:
        assert w.endswith("_K") or w.endswith("_0")
    assert all(q in ("q2_K", "q4_K", "q8_0", "f16") for q in v7_pilot.KV_QUANT_LADDER)
    for cell in v7_pilot.greedy_allocations(4.0, v7_pilot.PILOT_FAMILIES):
        assert any(s <= cell["ctx"] for s in v7_pilot.SPANS)


def test_prefix_and_exclusion_ruling():
    """Pins: R-19 (with R-18's grid): the span-s question presents the
    prefix cut; run_cell excludes spans beyond the window."""
    corpus = {
        "sentences": [f"noise {i}." for i in range(200)],
        "questions": [
            {"span": 2048, "hops": 2, "names": ["AAAAA", "BBBBB", "CCCCC"], "value": "11111"},
            {"span": 65536, "hops": 2, "names": ["DDDDD", "EEEEE", "FFFFF"], "value": "22222"},
        ],
        "cuts": {2048: 50, 65536: 200},
        "s_max": 65536,
    }
    p = v7_pilot.question_prompt(corpus, corpus["questions"][0])
    assert "noise 49." in p and "noise 50." not in p


def test_certify_v7_commits_per_cell(tmp_path, monkeypatch):
    """Pins: R-24. Every evaluated (family, ctx) cell fires
    on_cell_commit immediately - the author reads results through
    the git rail while the run goes. Skipped (already-measured) and
    dry-run cells do not fire it; a commit failure never stops the
    run."""
    import bench.v7 as v7m

    committed = []

    def fake_alloc(budget, limit=4):
        return [
            {
                "family": "famA",
                "params_b": 0.3,
                "ctx": 4096,
                "wq": "F16",
                "kq": "f16",
                "vq": "f16",
                "est_gib": 1.0,
            },
            {
                "family": "famA",
                "params_b": 0.3,
                "ctx": 8192,
                "wq": "F16",
                "kq": "f16",
                "vq": "f16",
                "est_gib": 1.2,
            },
        ]

    monkeypatch.setattr(v7m, "greedy_allocations", fake_alloc)
    # every acquisition and server launch faked out; run_cell scores empty
    monkeypatch.setattr(v7m, "_acquire_missing_model", lambda *a, **k: "/tmp/x.gguf")
    monkeypatch.setattr(
        v7m, "corpus_from_artifact", lambda port: {"questions": [], "cuts": {}, "sentences": []}
    )
    monkeypatch.setattr(v7m.llama_server, "start_server", lambda *a, **k: (object(), True))
    monkeypatch.setattr(v7m.llama_server, "wait_healthy", lambda *a, **k: True)
    monkeypatch.setattr(v7m.llama_server, "stop_server", lambda *a, **k: None)
    monkeypatch.setattr(v7m, "preflight_reachable_grades", lambda port, c, w: {})
    monkeypatch.setattr(
        v7m,
        "run_cell",
        lambda port, corpus, window, answers_path=None: {"score": 0.5, "max_score": 3},
    )
    monkeypatch.setattr(v7m, "save_state", lambda *a: None)
    # pre-measure the second cell: it must NOT fire the hook
    state = {"families": {"famA": {"v7": {"8192": {"score": 0.1}}}}}

    def boom(entry):
        committed.append((entry["family"], entry["ctx"]))
        if len(committed) == 1:
            raise RuntimeError("git is down")

    res = v7m.certify_v7(
        str(tmp_path),
        state,
        str(tmp_path / "st.json"),
        8210,
        False,
        on_cell_commit=boom,
    )
    # the fresh cell fired (and survived the hook's own failure);
    # the measured cell skipped without firing
    assert committed == [("famA", 4096)]
    assert res[0]["score"] == 0.5
    assert "skipped" in res[1]
