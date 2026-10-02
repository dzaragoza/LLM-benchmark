"""speed_gate.py dump-reuse rules: a dump measured at one ctx must never
satisfy reuse at a different ctx (the addendum-135 bug class: the reuse
check compared timestamps only, so a ctx-4096 dump was re-graded as a
--ctx 32768 cell in 88 ms with no server launch). Server-dependent
paths are avoided via the bench() reuse branch, the repo's established
monkeypatch style."""

import json
import os
import time

import speed_gate as sg


def _fixture(tmp_path, turns):
    model = tmp_path / "m.gguf"
    model.write_text("x")
    dump = tmp_path / "m.live-dump.nothink.json"
    dump.write_text(json.dumps(turns))
    now = time.time()
    os.utime(model, (0, 0))
    os.utime(dump, (now, now))
    return str(model), str(dump)


TURNS_4096 = [{"model": "m.gguf", "server_tps": 5.0, "conv": 1}]
TURNS_32768 = [{"model": "m.gguf", "server_tps": 5.0, "conv": 1, "ctx": 32768}]


def test_old_dump_reuses_at_default_ctx(tmp_path):
    model, dump = _fixture(tmp_path, TURNS_4096)
    out = sg.bench(
        model,
        "c.json",
        dry_run=False,
        no_thinking=True,
        ctx=sg.CTX_DEFAULT,
        dump_override=dump,
        force=False,
        port=1,
    )
    assert out == dump


def test_unstamped_dump_refused_at_deeper_ctx(tmp_path):
    model, dump = _fixture(tmp_path, TURNS_4096)
    try:
        sg.bench(
            model,
            "c.json",
            dry_run=False,
            no_thinking=True,
            ctx=32768,
            dump_override=dump,
            force=False,
            port=1,
        )
    except FileNotFoundError:
        return
    except SystemExit:
        raise AssertionError("refused via fail() instead of benching") from None
    raise AssertionError("reused a dump whose ctx does not match the run")


def test_ctx_stamped_dump_reuses_at_same_ctx(tmp_path):
    model, dump = _fixture(tmp_path, TURNS_32768)
    out = sg.bench(
        model,
        "c.json",
        dry_run=False,
        no_thinking=True,
        ctx=32768,
        dump_override=dump,
        force=False,
        port=1,
    )
    assert out == dump


def test_tournament_rank_mode():
    import full_benchmark as fb

    depths = fb.TOURNAMENT_DEPTHS
    # champion: all five top out - mode is 'top' -> rank 262144
    r = fb.tournament_rank([None] * 5, depths)
    assert r["rank_depth"] == 262144 and r["full_holds"] == 5 and r["rank_mode"] is None
    # a flicker: one climb falls at 131072, four top out - mode is 'top'
    r = fb.tournament_rank([131072, None, None, None, None], depths)
    assert r["rank_depth"] == 262144  # mode of 4 x top beats 1 x 131072
    assert r["passes"][262144] == 4 and r["passes"][65536] == 5
    # a fall: three climbs fall at 65536, two top out - mode is 65536
    r = fb.tournament_rank([65536, 65536, 65536, None, None], depths)
    assert r["rank_depth"] == 65536  # mode of the climbs (3 x 65536)
    assert r["passes"][65536] == 2
    # majority-vs-mode split: 3 top, 2 fall at 131072 - mode is 'top'
    r = fb.tournament_rank([131072, 131072, None, None, None], depths)
    assert r["rank_depth"] == 262144  # mode agrees with the old majority rule
    # NO-MODE cases fall back to the MEDIAN (addendum 20), never the max:
    # mode tie two top / two at 65536 / one at 32768 -> median 65536
    r = fb.tournament_rank([None, None, 65536, 65536, 32768], depths)
    assert r["rank_depth"] == 65536 and r["rank_statistic"] == "median-fallback"
    # mode tie between two fall depths: two at 65536, two at 32768, one 131072
    # -> sorted [32768, 32768, 65536, 65536, 131072], median 65536
    r = fb.tournament_rank([65536, 65536, 32768, 32768, 131072], depths)
    assert r["rank_depth"] == 65536 and r["rank_statistic"] == "median-fallback"
    # all five distinct -> median (3rd of sorted), NOT the deepest climb
    r = fb.tournament_rank([4096, 8192, 32768, 65536, 131072], depths)
    assert r["rank_depth"] == 32768 and r["rank_statistic"] == "median-fallback"
    # two tops is already a mode (top x2) - no fallback needed
    r = fb.tournament_rank([4096, 65536, None, None, 131072], depths)
    assert r["rank_depth"] == 262144 and r["rank_statistic"] == "mode"
    # unanimous early fall: mode is the floor
    r = fb.tournament_rank([4096] * 5, depths)
    assert r["rank_depth"] == 4096 and r["rank_statistic"] == "mode"


def test_tournament_family_creates_climb_dirs(tmp_path, monkeypatch):
    """The addendum-14 bug: tournament_family passed per-climb subdirs
    to fwe_pass without creating them - fwe_pass (now hardened too)
    must never crash on a missing results_dir."""
    import full_benchmark as fb

    calls = []

    def fake_fwe_pass(model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None):
        calls.append(results_dir)
        assert os.path.isdir(results_dir), f"fwe_pass got a missing dir: {results_dir}"
        hold = seed > 1
        return hold, {"correct": 1 if hold else 0, "depth": rung}

    monkeypatch.setattr(fb, "fwe_pass", fake_fwe_pass)
    model = tmp_path / "fam-Q8_0.gguf"
    model.write_bytes(b"x")
    state = {
        "families": {
            "fam": {
                "selected": "Q8_0",
                "runs": {"Q8_0": {"file": str(model)}},
            }
        }
    }
    models_dir = str(tmp_path)
    tour = fb.tournament_family("fam", models_dir, state, str(tmp_path / "st.json"), 8210, False)
    # climb 1 (seed 1) falls at 4096 -> early stop (1 call); climbs 2-21
    # hold every depth (7 calls each) -> 141 total
    assert len(calls) == 141
    assert tour["fall_depths"] == [4096] + [None] * 20
    assert tour["full_holds"] == 20
    assert tour["rank_depth"] == 262144  # mode of 14 x top (addendum 40)


def test_tournament_family_resumes_saved_climbs(tmp_path, monkeypatch):
    """The addendum-37 resume rule: climbs already recorded in the
    family state (tournament_falls, seed = climb number) are NOT
    re-run - extending the tournament (5 -> 7) runs only the new
    seeds, and the rank covers all seven climbs."""
    import full_benchmark as fb

    calls = []

    def fake_fwe_pass(model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None):
        calls.append(seed)
        assert os.path.isdir(results_dir), f"fwe_pass got a missing dir: {results_dir}"
        return seed > 6, {"correct": 1 if seed > 6 else 0, "depth": rung}

    monkeypatch.setattr(fb, "fwe_pass", fake_fwe_pass)
    model = tmp_path / "fam-Q8_0.gguf"
    model.write_bytes(b"x")
    state = {
        "families": {
            "fam": {
                "selected": "Q8_0",
                "runs": {"Q8_0": {"file": str(model)}},
                "tournament_falls": {"1": 4096, "2": 4096, "3": 4096, "4": 8192, "5": 32768},
            }
        }
    }
    models_dir = str(tmp_path)
    state_path = str(tmp_path / "st.json")
    tour = fb.tournament_family("fam", models_dir, state, state_path, 8210, False)
    # only seeds 6-21 ran: seed 6 falls at 4096 (1 call), seeds 7-21
    # hold every depth (15 seeds x 7 calls) - climbs 1-5 were resumed
    # each of seeds 7-15 climbs all 7 depths with ITS OWN seed number
    assert calls == [6] + [s for s in range(7, 22) for _ in range(7)]
    assert tour["fall_depths"] == [4096, 4096, 4096, 8192, 32768, 4096] + [None] * 15
    saved = state["families"]["fam"]["tournament_falls"]
    assert len(saved) == 21 and saved["6"] == 4096 and saved["21"] is None
    # mode of the twenty-one climbs: 16 x top beats 4 x 4096
    assert tour["rank_statistic"] == "mode" and tour["rank_mode"] is None


def test_wilson_and_reliable_depth():
    """The addendum-42 recommendation statistics: 1-sigma Wilson
    bounds on the per-rung hold fraction, reliable depth (deepest
    rung with lower bound >= 0.5 and count >= n/2), ceiling."""
    import full_benchmark as fb

    # wilson at the extremes and a known middle
    assert fb.wilson_interval(0, 15) == (0.0, 0.0625)  # verified: standard score interval
    lo, hi = fb.wilson_interval(15, 15)
    assert lo > 0.8 and hi == 1.0
    lo, hi = fb.wilson_interval(8, 15)
    assert abs(lo - 0.4065) < 0.001 and abs(hi - 0.6560) < 0.001  # 8/15 at 1 sigma, verified

    # a mostly-holding family: 5/7 hold 4096 (wilson lower ~0.53 >
    # 0.5), 4/7 hold 8192 (lower ~0.36 < 0.5) -> reliable 4096
    r = fb.tournament_rank([8192, 8192, 4096, 8192, 32768, 4096, 8192], fb.TOURNAMENT_DEPTHS)
    assert r["reliable_depth"] == 4096
    assert r["ceiling"] == 32768

    # the 0.8B's actual rounds-6-7 pattern: only 4/7 hold 4096 ->
    # nothing is reliable, but the ceiling is 262,144 (the near-top
    # climb). Mode/ceiling disagree: exactly the recommendation case.
    r = fb.tournament_rank([4096, 4096, 4096, 8192, 32768, 262144, 32768], fb.TOURNAMENT_DEPTHS)
    assert r["reliable_depth"] == 0
    assert r["ceiling"] == 262144

    # a floor-faller: all-4096 falls -> reliable 0, ceiling 4096
    r = fb.tournament_rank([4096] * 7, fb.TOURNAMENT_DEPTHS)
    assert r["reliable_depth"] == 0 and r["ceiling"] == 4096

    # the addendum-43 conservative depth at n=21: the 1-sigma bar is
    # 13/21 at a rung, the 2-sigma bar is 16/21 (verified against
    # wilson_interval). 12/21 -> neither; 13/21 -> reliable only;
    # 16/21 -> both. Conservative is always <= reliable.
    # a climb HOLDS 4096 iff it fell deeper (>= 8192) or topped - so
    # k/21 holds at 4096 means k climbs fall at 8192-or-deeper
    falls = [8192] * 12 + [4096] * 9  # 12/21 hold 4096 -> neither
    r = fb.tournament_rank(falls, fb.TOURNAMENT_DEPTHS)
    assert r["reliable_depth"] == 0 and r["conservative_depth"] == 0
    falls = [8192] * 13 + [4096] * 8  # 13/21 hold 4096 -> reliable only
    r = fb.tournament_rank(falls, fb.TOURNAMENT_DEPTHS)
    assert r["reliable_depth"] == 4096 and r["conservative_depth"] == 0
    falls = [8192] * 16 + [4096] * 5  # 16/21 hold 4096 -> both
    r = fb.tournament_rank(falls, fb.TOURNAMENT_DEPTHS)
    assert r["reliable_depth"] == 4096 and r["conservative_depth"] == 4096


def test_tournament_entry_config(tmp_path, monkeypatch):
    """The addendum-16 entry path: a participant WITHOUT a PASS
    selection enters on its predicted ceiling-matching config
    (tournament_entry: rung + kv quants + file) instead of being
    skipped."""
    import full_benchmark as fb

    calls = []

    def fake_fwe_pass(model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None):
        calls.append((model, kv_quant_k, kv_quant_v))
        return (True, {"correct": 1})

    monkeypatch.setattr(fb, "fwe_pass", fake_fwe_pass)
    m = tmp_path / "Llama-3.2-1B-Instruct"
    m.mkdir()
    f = m / "Llama-3.2-1B-Instruct-F16.gguf"
    f.write_text("x")
    state = {
        "families": {
            "Llama-3.2-1B-Instruct": {
                "tournament_entry": {
                    "rung": "F16",
                    "kv_quant_k": "q5_0",
                    "kv_quant_v": "q5_0",
                    "predicted_ram_gib": 4.96,
                    "file": str(f),
                }
            }
        }
    }
    out = fb.tournament_family(
        "meta-llama/Llama-3.2-1B-Instruct",
        str(tmp_path),
        state,
        str(tmp_path / "s.json"),
        8210,
        False,
    )
    assert out["rank_depth"] == 262144 and out["full_holds"] == 21
    assert len(calls) == 21 * len(fb.TOURNAMENT_DEPTHS)
    assert all(c[1] == "q5_0" and c[2] == "q5_0" for c in calls)


def test_git_pull_head(monkeypatch):
    """Addendum 32: the forgotten pull, made structural - git_pull_head
    runs before the state loads; a failed pull is a hard stop."""
    import full_benchmark as fb

    calls = []

    class R:
        def __init__(self, rc, out):
            self.returncode = rc
            self.stdout = out
            self.stderr = ""

    def fake_run(cmd, capture_output=True, text=True):
        calls.append(cmd)
        if cmd[0] == "git" and cmd[1] == "rev-parse":
            return R(0, "true\n")
        return R(1, "")

    monkeypatch.setattr(fb.subprocess, "run", fake_run)
    try:
        fb.git_pull_head()
        raise AssertionError("failed pull did not stop the run")
    except SystemExit:
        pass
    assert any(c[:2] == ["git", "pull"] for c in calls)

    monkeypatch.setattr(
        fb.subprocess, "run", lambda cmd, capture_output=True, text=True: R(0, "true\n")
    )
    fb.git_pull_head()  # pull succeeds -> no exit


def test_git_pull_before_tee():
    """Addendum 34: the pull runs BEFORE tee_output.install appends to
    results.txt - the tool must not dirty its own tree then refuse to
    pull (the author's dry-run finding), and the pull autostashes."""
    import inspect

    import full_benchmark as fb

    body = inspect.getsource(fb.main)
    assert body.index("git_pull_head()") < body.index("tee_output.install()")
    src = inspect.getsource(fb.git_pull_head)
    assert "--autostash" in src


def test_git_tail_pulls_before_push():
    """Addendum 47: the artifact tail pulls AFTER the commit and
    BEFORE the push - origin moves during long runs, and the
    artifact commit must replay on top before pushing."""
    import inspect

    import full_benchmark as fb

    src = inspect.getsource(fb.git_tail)
    i_commit = src.index('["git", "commit", "-m", msg]')
    i_pull = src.index('["git", "pull", "--rebase", "--autostash"]')
    i_push = src.index('subprocess.run(["git", "push"]')
    assert i_commit < i_pull < i_push, "order must be commit -> pull -> push"
    assert "--autostash" in src
