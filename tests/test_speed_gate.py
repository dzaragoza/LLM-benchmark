"""speed_gate.py dump-reuse rules: a dump measured at one ctx must never
satisfy reuse at a different ctx (the addendum-135 bug class: the reuse
check compared timestamps only, so a ctx-4096 dump was re-graded as a
--ctx 32768 cell in 88 ms with no server launch). Server-dependent
paths are avoided via the bench() reuse branch, the repo's established
monkeypatch style."""

import json
import os
import signal
import time
from typing import Any

import pytest

import speed_gate as sg
from bench import cells as bench_cells
from bench import state_store as bench_state_store


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


def test_tournament_rank_sigma_only():
    """Session 37, addendum 10: the mode is RETIRED - tournament_rank
    returns the sigma statistics only; no rank_depth, no
    rank_statistic, no central tendency of the fall depths."""
    import full_benchmark as fb

    depths = fb.TOURNAMENT_DEPTHS
    # champion: all five top out -> every rung 5/5, reliable = top
    r = fb.tournament_rank([None] * 5, depths)
    assert r["reliable_depth"] == 262144 and r["conservative_depth"] == 262144
    assert r["full_holds"] == 5 and r["ceiling"] == 262144
    assert "rank_depth" not in r and "rank_statistic" not in r and "rank_mode" not in r
    # a flicker: one climb falls at 131072, four top out
    r = fb.tournament_rank([131072, None, None, None, None], depths)
    assert r["passes"][262144] == 4 and r["passes"][65536] == 5
    assert r["reliable_depth"] == 262144 and r["ceiling"] == 262144  # lo(4,5)~0.58 >= 0.5
    # a fall-heavy shape: three climbs fall at 65536, two top out
    r = fb.tournament_rank([65536, 65536, 65536, None, None], depths)
    assert r["passes"][65536] == 2
    assert r["reliable_depth"] == 32768 and r["ceiling"] == 262144
    # unanimous early fall: nothing reliable, ceiling at the floor
    r = fb.tournament_rank([4096] * 5, depths)
    assert r["reliable_depth"] == 0 and r["ceiling"] == 4096
    # all five distinct: sigma stats computed from the pass vector alone
    r = fb.tournament_rank([4096, 8192, 32768, 65536, 131072], depths)
    assert r["passes"][4096] == 4 and r["passes"][65536] == 1
    assert r["reliable_depth"] == 4096 and r["ceiling"] == 131072  # lo(4,5)~0.58


def test_tournament_family_creates_climb_dirs(tmp_path, monkeypatch):
    """The addendum-14 bug: tournament_family passed per-climb subdirs
    to fwe_pass without creating them - fwe_pass (now hardened too)
    must never crash on a missing results_dir."""
    import full_benchmark as fb

    calls = []

    def fake_fwe_pass(
        model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None, min_words=1
    ):
        calls.append(results_dir)
        assert os.path.isdir(results_dir), f"fwe_pass got a missing dir: {results_dir}"
        hold = seed > 1
        return hold, {"correct": 1 if hold else 0, "depth": rung}

    monkeypatch.setattr(bench_cells, "fwe_pass", fake_fwe_pass)
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
    # climb 1 (seed 1) falls at 4096 -> early stop (1 call); climbs 2-20
    # hold every depth (7 calls each) -> 134 total
    assert len(calls) == 134
    assert tour["fall_depths"] == [4096] + [None] * 19
    assert tour["full_holds"] == 19
    assert tour["reliable_depth"] == 262144  # 19/20 at 1 sigma clears every rung


def test_tournament_family_resumes_saved_climbs(tmp_path, monkeypatch):
    """The addendum-37 resume rule: climbs already recorded in the
    family state (tournament_falls, seed = climb number) are NOT
    re-run - extending the tournament (5 -> 7) runs only the new
    seeds, and the rank covers all seven climbs."""
    import full_benchmark as fb

    calls = []

    def fake_fwe_pass(
        model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None, min_words=1
    ):
        calls.append(seed)
        assert os.path.isdir(results_dir), f"fwe_pass got a missing dir: {results_dir}"
        return seed > 6, {"correct": 1 if seed > 6 else 0, "depth": rung}

    monkeypatch.setattr(bench_cells, "fwe_pass", fake_fwe_pass)
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
    # only seeds 6-20 ran: seed 6 falls at 4096 (1 call), seeds 7-20
    # hold every depth (14 seeds x 7 calls) - climbs 1-5 were resumed
    # each of seeds 7-14 climbs all 7 depths with ITS OWN seed number
    assert calls == [6] + [s for s in range(7, 21) for _ in range(7)]
    assert tour["fall_depths"] == [4096, 4096, 4096, 8192, 32768, 4096] + [None] * 14
    saved = state["families"]["fam"]["tournament_falls"]
    assert len(saved) == 20 and saved["6"] == 4096 and saved["20"] is None
    # sigma rank: 14/20 top out -> reliable 262144 at 1 sigma (mode retired)
    assert "rank_statistic" not in tour and tour["reliable_depth"] == 262144


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

    def fake_fwe_pass(
        model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None, min_words=1
    ):
        calls.append((model, kv_quant_k, kv_quant_v))
        return (True, {"correct": 1})

    monkeypatch.setattr(bench_cells, "fwe_pass", fake_fwe_pass)
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
    assert out["reliable_depth"] == 262144 and out["full_holds"] == 20
    assert len(calls) == 20 * len(fb.TOURNAMENT_DEPTHS)
    assert all(c[1] == "q5_0" and c[2] == "q5_0" for c in calls)


def test_git_pull_head(monkeypatch):
    """Addendum 32: the forgotten pull, made structural - git_pull_head
    runs before the state loads; a failed pull is a hard stop."""
    import full_benchmark as fb
    import infra.git_ops as git_ops

    calls = []

    def fake_inside():
        calls.append("inside")
        return True

    def fake_pull(autostash=True, no_verify=False):
        calls.append(("pull", autostash, no_verify))
        return (1, "", "diverged")

    monkeypatch.setattr(git_ops, "inside_work_tree", fake_inside)
    monkeypatch.setattr(git_ops, "pull_rebase", fake_pull)
    try:
        fb.git_pull_head()
        raise AssertionError("failed pull did not stop the run")
    except SystemExit:
        pass
    assert calls == ["inside", ("pull", True, True)]

    def fake_pull_ok(autostash=True, no_verify=False):
        return (0, "Already up to date", "")

    monkeypatch.setattr(git_ops, "pull_rebase", fake_pull_ok)
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
    assert "pull_rebase(no_verify=True)" in src
    import infra.git_ops as git_ops

    assert "--autostash" in inspect.getsource(git_ops.pull_rebase)


def test_git_tail_pulls_before_push():
    """Addendum 47: the artifact tail pulls AFTER the commit and
    BEFORE the push - origin moves during long runs, and the
    artifact commit must replay on top before pushing."""
    import inspect

    import full_benchmark as fb

    src = inspect.getsource(fb.git_tail)
    i_commit = src.index("git_ops.commit(msg)")
    i_pull = src.index("git_ops.pull_rebase()")
    i_push = src.index("git_ops.push()")
    assert i_commit < i_pull < i_push, "order must be commit -> pull -> push"
    import inspect as _inspect

    import infra.git_ops as git_ops

    assert "--autostash" in _inspect.getsource(git_ops.pull_rebase)


def test_rescore_tournament(tmp_path, capsys):
    """Session 37, addendum 4: the saved 3/3 falls re-scored from the
    raw climb CSVs under 1/3 - a 1/3-or-2/3 partial cell becomes a
    HOLD (fall moves deeper or drops for re-run), a 0/3 cell still
    falls at the same rung."""
    import csv as csv_mod

    import full_benchmark as fb

    def cell(models_dir, fam, climb, depth, partial):
        d = os.path.join(models_dir, "tournament-results", fam, f"climb{climb}")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"fam-{depth}-fwe.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv_mod.writer(f)
            w.writerow(["task", "depth", "top_k", "partial", "answer", "correct"])
            w.writerow([0, depth, "a;b;c", partial, "ans", int(partial >= 1)])

    # climb 1: fell at 8192 under 3/3 (partial 2 at 8192) -> under 1/3
    # the fall moves deeper: 16384 is a 0/3 cell -> new fall 16384
    cell(str(tmp_path), "fam", 1, 4096, 3)
    cell(str(tmp_path), "fam", 1, 8192, 2)
    cell(str(tmp_path), "fam", 1, 16384, 0)
    # climb 2: fell at 8192 with 0/3 -> the fall is UNCHANGED
    cell(str(tmp_path), "fam", 2, 4096, 3)
    cell(str(tmp_path), "fam", 2, 8192, 0)
    # climb 3: fell at 4096 with a 2/3 partial -> a pass chain now; the
    # saved fall is DROPPED so the next tournament re-runs the climb
    cell(str(tmp_path), "fam", 3, 4096, 2)
    state = {"families": {"fam": {"tournament_falls": {"1": 8192, "2": 8192, "3": 4096}}}}
    state_path = str(tmp_path / "st.json")
    fb.rescore_tournament(str(tmp_path), state, state_path, False)
    saved = state["families"]["fam"]["tournament_falls"]
    assert saved["1"] == 16384
    assert saved["2"] == 8192
    assert "3" not in saved
    on_disk = json.load(open(state_path))
    assert on_disk["families"]["fam"]["tournament_falls"] == saved
    out = capsys.readouterr().out
    assert "PASS chain" in out and "16,384" in out

    # dry run: nothing written
    state2 = {"families": {"fam": {"tournament_falls": {"1": 8192}}}}
    fb.rescore_tournament(str(tmp_path), state2, state_path, True)
    assert state2["families"]["fam"]["tournament_falls"] == {"1": 8192}
    out = capsys.readouterr().out
    assert "state NOT written" in out


def test_certify_cells_inherit_from_falls():
    """Addendum 8: the cell model - climb s measured every rung up to
    and including its fall; a fall DEEPER than the rung means the
    cell passed, a fall AT the rung means it failed, a fall SHALLOWER
    means the cell was never reached (unmeasured)."""
    import full_benchmark as fb

    fst = {
        "tournament_falls": {
            "1": 8192,  # fell at 8192: cell(1, 8192)=False, cell(1,4096)=True
            "2": None,  # topped out: every cell True
            "3": 4096,  # cell(3, 8192) unmeasured, cell(3,4096)=False
        },
        "certify": {"8192": {"3": True}},
    }
    cells = fb.certify_cells(fst, 8192)
    assert cells == {1: False, 2: True, 3: True}
    cells4k = fb.certify_cells(fst, 4096)
    assert cells4k == {1: True, 2: True, 3: False}


def test_certify_rung_accepts_and_skips(tmp_path, capsys):
    """The sequential controller: the promising candidate certifies
    from historical cells + fresh ones (never re-measuring a used
    run), the rung is ANSWERED, the rest are skipped."""
    import full_benchmark as fb

    ran = []

    def fake_fwe_pass(
        model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None, min_words=1
    ):
        ran.append(seed)
        return True, {"correct": 1, "depth": rung}

    def fake_speed_pass(model, rung, corpus, port, results_dir, kv_quant_k=None, kv_quant_v=None):
        return True, {"worst": 30.0}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(bench_cells, "fwe_pass", fake_fwe_pass)
    monkeypatch.setattr(bench_cells, "speed_pass", fake_speed_pass)
    try:
        model = tmp_path / "good-Q8_0.gguf"
        model.write_bytes(b"x")
        # candidate A: 8 passing cells at 8192 historically; the
        # accept bar fires EARLY - at 11/11 measured cells
        # (lo(11,11)=0.917 >= 0.5, count 11 >= floor 11)
        state: dict[str, Any] = {
            "families": {
                "good": {
                    "selected": "Q8_0",
                    "runs": {"Q8_0": {"file": str(model)}},
                    "tournament_falls": {
                        "1": None,
                        "2": None,
                        "3": None,
                        "4": None,
                        "5": 16384,
                        "6": 16384,
                        "7": 16384,
                        "8": 16384,
                    },
                },
                "other": {
                    "selected": "Q8_0",
                    "runs": {"Q8_0": {"file": str(model)}},
                    "tournament_falls": {},
                },
            }
        }
        res = fb.certify_rung(
            8192,
            "1_sigma",
            ["good", "other"],
            str(tmp_path),
            state,
            str(tmp_path / "st.json"),
            8210,
            False,
        )
        first = [r for r in res if r["family"] == "good"][0]
        assert first["verdict"] == "accept"
        # historical cells at 8192: climbs 1-4 top + 5-8 fell deeper = 8 passes
        # runs 9-20 are fresh (12 seeds), never re-measured; accept at
        # 10 measured (10/10, lo(10,10,1)=0.909 >= 0.5, floor 10)
        assert sorted(ran) == [9, 10]
        assert first["cells_measured"] == 10 and first["passes"] == 10
        other = [r for r in res if r["family"] == "other"][0]
        assert other.get("skipped") == "rung already answered"
        # direct cells persisted
        good: dict[str, Any] = state["families"]["good"]
        direct = good["certify"]["8192"]
        assert direct == {str(r): True for r in (9, 10)}
    finally:
        monkeypatch.undo()


def test_certify_rung_dead(tmp_path, capsys):
    """Early reject: a candidate whose remaining cells cannot reach
    the 1-sigma bar is declared DEAD without running a single cell."""
    import full_benchmark as fb

    ran = []

    def fake_fwe_pass(
        model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None, min_words=1
    ):
        ran.append(seed)
        return True, {"correct": 1, "depth": rung}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(bench_cells, "fwe_pass", fake_fwe_pass)
    try:
        model = tmp_path / "dead-Q8_0.gguf"
        model.write_bytes(b"x")
        # 9 climbs FELL AT 8192 (9 measured fails, 12 remaining):
        # best case 12/21 passes, lo(12,21)=0.463 < 0.5 -> dead
        falls = {str(i): 8192 for i in range(1, 10)}
        state = {
            "families": {
                "dead": {
                    "selected": "Q8_0",
                    "runs": {"Q8_0": {"file": str(model)}},
                    "tournament_falls": falls,
                }
            }
        }
        res = fb.certify_rung(
            8192, "1_sigma", ["dead"], str(tmp_path), state, str(tmp_path / "st.json"), 8210, False
        )
        assert res[0]["verdict"] == "dead"
        assert ran == []
        assert "DEAD" in capsys.readouterr().out
    finally:
        monkeypatch.undo()


def test_certify_rung_at_least_one(tmp_path, capsys):
    """Addendum 18: at_least_one accepts a candidate with a single
    historical pass - no fresh cells needed - and skips the rest."""
    import full_benchmark as fb

    ran = []

    def fake_fwe_pass(
        model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None, min_words=1
    ):
        ran.append(seed)
        return True, {"correct": 1, "depth": rung}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(bench_cells, "fwe_pass", fake_fwe_pass)
    try:
        model = tmp_path / "one-Q8_0.gguf"
        model.write_bytes(b"x")
        state = {
            "families": {
                "one": {
                    "selected": "Q8_0",
                    "runs": {"Q8_0": {"file": str(model)}},
                    "tournament_falls": {"1": None},
                },
                "none": {
                    "selected": "Q8_0",
                    "runs": {"Q8_0": {"file": str(model)}},
                    "tournament_falls": {},
                },
            }
        }
        res = fb.certify_rung(
            16384,
            "at_least_one",
            ["one", "none"],
            str(tmp_path),
            state,
            str(tmp_path / "st.json"),
            8210,
            False,
        )
        first = [r for r in res if r["family"] == "one"][0]
        # climb 1 topped out, so its 16384 cell passed historically -> no fresh cells
        assert first["verdict"] == "accept"
        assert first["passes"] == 1 and first["ran_now"] == 0
        assert ran == []
        other = [r for r in res if r["family"] == "none"][0]
        assert other.get("skipped") == "rung already answered"
        assert "at least one pass" in capsys.readouterr().out
    finally:
        monkeypatch.undo()


def test_certify_rung_at_least_one_dead(tmp_path, capsys):
    """Addendum 18: at_least_one with all 21 cells measured and zero
    passes is DEAD - every remaining candidate gets its turn."""
    import full_benchmark as fb

    ran = []

    def fake_fwe_pass(
        model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None, min_words=1
    ):
        ran.append(seed)
        return False, {"correct": 0, "depth": rung}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(bench_cells, "fwe_pass", fake_fwe_pass)
    try:
        model = tmp_path / "zero-Q8_0.gguf"
        model.write_bytes(b"x")
        falls = {str(i): 16384 for i in range(1, 21)}
        state = {
            "families": {
                "zero": {
                    "selected": "Q8_0",
                    "runs": {"Q8_0": {"file": str(model)}},
                    "tournament_falls": falls,
                }
            }
        }
        res = fb.certify_rung(
            16384,
            "at_least_one",
            ["zero"],
            str(tmp_path),
            state,
            str(tmp_path / "st.json"),
            8210,
            False,
        )
        assert res[0]["verdict"] == "dead"
        assert ran == []
        out = capsys.readouterr().out
        assert "no pass" in out and "DEAD" in out
    finally:
        monkeypatch.undo()


def test_certify_rung_2_sigma_dead(tmp_path, capsys):
    """Addendum 18: the 2-sigma bar is stricter - 8 passing cells at
    a rung are dead at 2 sigma (even 21/21 gives lo(21,21,2)=0.77 <
    0.5 is wrong - so use the real math: 9 fails, best 12/21,
    lo(12,21,2)=0.368 < 0.5) -> DEAD without running a cell."""
    import full_benchmark as fb

    ran = []

    def fake_fwe_pass(
        model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None, min_words=1
    ):
        ran.append(seed)
        return True, {"correct": 1, "depth": rung}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(bench_cells, "fwe_pass", fake_fwe_pass)
    try:
        model = tmp_path / "s2-Q8_0.gguf"
        model.write_bytes(b"x")
        falls = {str(i): 8192 for i in range(1, 10)}
        state = {
            "families": {
                "s2": {
                    "selected": "Q8_0",
                    "runs": {"Q8_0": {"file": str(model)}},
                    "tournament_falls": falls,
                }
            }
        }
        res = fb.certify_rung(
            8192, "2_sigma", ["s2"], str(tmp_path), state, str(tmp_path / "st.json"), 8210, False
        )
        assert res[0]["verdict"] == "dead"
        assert ran == []
        out = capsys.readouterr().out
        assert "2s lower bound" in out
    finally:
        monkeypatch.undo()


def test_diagnose_fwe(tmp_path, capsys):
    """Addendum 9: the per-rank diagnostic reads the climb CSVs -
    which of the 3 expected words the found-words actually are, and
    the pass rate at every threshold (>=1, >=2, 3 of 3)."""
    import csv as csv_mod

    import full_benchmark as fb

    d = tmp_path / "tournament-results" / "fam" / "climb1"
    d.mkdir(parents=True)
    # cell 1: finds rank-1 only; cell 2: perfect; cell 3: nothing
    rows = [
        ["task", "depth", "top_k", "partial", "answer", "correct"],
        [0, 4096, "aaa;bbb;ccc", 1, "the word is aaa", 1],
        [0, 4096, "aaa;bbb;ccc", 3, "aaa bbb ccc", 1],
        [0, 4096, "aaa;bbb;ccc", 0, "the a and of", 0],
    ]
    with open(d / "fam-4096-fwe.csv", "w", newline="", encoding="utf-8") as f:
        csv_mod.writer(f).writerows(rows)
    fb.diagnose_fwe(str(tmp_path), {"families": {"fam": {}}})
    out = capsys.readouterr().out
    assert "3 cells" in out
    assert "rank-1 word found in 2/3" in out
    assert "3/3: 1/3" in out
    assert ">=2/3: 1/3" in out
    assert ">=1/3: 2/3" in out


def test_certify_cells_regrades_inherited_from_csv(tmp_path):
    """The 2/3 tightening: inherited tournament-fall cells are re-graded
    from their committed climb CSV `partial` word counts instead of
    being dropped - the fall only says pass/fail at 3/3, but the CSV
    holds the actual words found."""
    import csv as _csv

    import full_benchmark as fb

    fam = "fam"
    cdir = tmp_path / "tournament-results" / fam / "climb7"
    cdir.mkdir(parents=True)
    with open(cdir / "fam-Q8_0-8192-fwe.csv", "w", newline="") as fh:
        w = _csv.writer(fh)
        w.writerow(["task", "depth", "top_k", "partial", "answer", "correct"])
        w.writerow([0, 8192, "aaa;bbb;ccc", 1, "x", False])

    fst = {"tournament_falls": {"7": None}}
    cells = fb.certify_cells(fst, 8192, 2, str(tmp_path), fam)
    assert cells == {7: False}

    with open(cdir / "fam-Q8_0-8192-fwe.csv", "w", newline="") as fh:
        w = _csv.writer(fh)
        w.writerow(["task", "depth", "top_k", "partial", "answer", "correct"])
        w.writerow([0, 8192, "aaa;bbb;ccc", 2, "x", True])
    cells = fb.certify_cells(fst, 8192, 2, str(tmp_path), fam)
    assert cells == {7: True}

    # no models_dir: the inherited cell stays dropped (re-run, never guessed)
    cells = fb.certify_cells(fst, 8192, 2)
    assert cells == {}


def test_certify_rung_vt_separate_namespace_and_partial(tmp_path, capsys):
    """The VT certification: same sequential controller, but cells live in
    certify_vt (the FWE evidence is untouched), NOTHING is inherited from the
    FWE tournament, pass = 5/5 names, and the 0..5 partial is stored per cell
    (re-gradable at any bar later without re-measuring)."""
    import full_benchmark as fb

    ran = []

    def fake_vt_pass(model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None):
        ran.append(seed)
        # the pilot shape: 4/5 names - a near-miss that still FAILs the 5/5 bar
        return False, {"correct": 0, "words_found": [4], "depth": rung}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(bench_cells, "vt_pass", fake_vt_pass)
    try:
        model = tmp_path / "good-Q8_0.gguf"
        model.write_bytes(b"x")
        state: dict[str, Any] = {
            "families": {
                "good": {
                    "selected": "Q8_0",
                    "runs": {"Q8_0": {"file": str(model)}},
                    # an FWE certification exists at this rung - VT must not
                    # read it, write it, or inherit its cells
                    "certify": {"8192": {"1": True, "2": True, "3": True}},
                    "tournament_falls": {"1": None, "2": None},
                }
            }
        }
        res = fb.certify_rung(
            8192,
            "1_sigma",
            ["good"],
            str(tmp_path),
            state,
            str(tmp_path / "st.json"),
            8210,
            False,
            task="vt",
        )
        first = res[0]
        # 0 passes, dead by EARLY REJECT at 8 consecutive fails
        # (best 12/20, lo 0.488 < 0.5 - the remaining 12 cells are not run)
        assert first["verdict"] == "dead"
        assert len(ran) == 8
        # the partials landed in certify_vt - 4/5 per cell, FAIL at the 5/5 bar
        good_ns: dict[str, Any] = state["families"]["good"]
        vt = good_ns["certify_vt"]["8192"]
        assert all(p == 4 for p in vt.values()) and len(vt) == 8
        # the FWE namespace is untouched
        assert good_ns["certify"] == {"8192": {"1": True, "2": True, "3": True}}
        # re-grade the SAME cells at the 4/5 bar from the stored partials
        cells = fb.vt_cells(good_ns, 8192)
        assert all(p == 4 for p in cells.values())
    finally:
        monkeypatch.undo()


def test_certify_rung_vt_accepts_on_5_of_5(tmp_path, capsys):
    """A model that traces all 5 names every cell: VT gold certifies with the
    same early-accept math as FWE (11/11 at 1 sigma)."""
    import full_benchmark as fb

    ran = []

    def fake_vt_pass(model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None):
        ran.append(seed)
        return True, {"correct": 1, "words_found": [5], "depth": rung}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(bench_cells, "vt_pass", fake_vt_pass)
    try:
        model = tmp_path / "vt-Q8_0.gguf"
        model.write_bytes(b"x")
        state: dict[str, Any] = {
            "families": {
                "vt": {
                    "selected": "Q8_0",
                    "runs": {"Q8_0": {"file": str(model)}},
                }
            }
        }
        res = fb.certify_rung(
            8192,
            "1_sigma",
            ["vt"],
            str(tmp_path),
            state,
            str(tmp_path / "st.json"),
            8210,
            False,
            task="vt",
        )
        assert res[0]["verdict"] == "accept"
        assert sorted(ran) == list(range(1, 11))
        assert res[0]["cells_measured"] == 10
        vt_ns: dict[str, Any] = state["families"]["vt"]
        vt = vt_ns["certify_vt"]["8192"]
        assert all(p == 5 for p in vt.values())
    finally:
        monkeypatch.undo()


def test_combined_rung_accept_and_medal(tmp_path, capsys):
    """The combined controller (addendum 3): one cell run shared by the
    three tasks, measured only if missing; accept needs ALL THREE at
    the bar; the medal is re-graded from the stored records."""
    import full_benchmark as fb

    calls = []

    def fake_measure(task, model, depth, results_dir, run, port, kv_k, kv_v, min_words):
        calls.append((task, run))
        return True, {"speed": 0, "fwe": 3, "vt": 5, "arc": 5}[task], f"{task} ok"

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(bench_state_store, "_task_measure", fake_measure)
    try:
        model = tmp_path / "fam-Q8_0.gguf"
        model.write_bytes(b"x")
        state: dict[str, Any] = {
            "families": {"fam": {"selected": "Q8_0", "runs": {"Q8_0": {"file": str(model)}}}}
        }
        res = fb.certify_rung_combined(
            8192,
            "1_sigma",
            ["fam"],
            str(tmp_path),
            state,
            str(tmp_path / "st.json"),
            8210,
            False,
            min_words=3,
        )
        r = res[0]
        assert r["verdict"] == "accept"
        assert all(r[f"{t}_verdict"] == "accept" for t in fb.COMBINED_TASKS)
        # ruling B: the 1_sigma level ANSWERS at the 1_sigma tier - the
        # controller bar and the medal bar are the same thing now
        assert r["medal"] == "1_sigma"
        ns: dict[str, Any] = state["families"]["fam"]
        assert ns["certify"]["8192"] and ns["certify_vt"]["8192"] and ns["certify_speed"]["8192"]
        assert ns["certify_arc"]  # rung-independent, stored once
        # resume: every cell-task stored, nothing re-measured
        calls.clear()
        res = fb.certify_rung_combined(
            8192,
            "1_sigma",
            ["fam"],
            str(tmp_path),
            state,
            str(tmp_path / "st.json"),
            8210,
            False,
            min_words=3,
        )
        assert calls == []
        assert res[0]["verdict"] == "accept"
    finally:
        monkeypatch.undo()


def test_combined_rung_dead_when_one_task_dies(tmp_path, capsys):
    """Any single task dead kills the candidate - the others' perfect
    runs do not rescue it; the next candidate is picked up."""
    import full_benchmark as fb

    calls = []

    def fake_measure(task, model, depth, results_dir, run, port, kv_k, kv_v, min_words):
        calls.append((task, run))
        if task == "vt":
            return False, 0, "vt 0/5"
        return True, {"speed": 0, "fwe": 3, "arc": 5}[task], f"{task} ok"

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(bench_state_store, "_task_measure", fake_measure)
    try:
        model = tmp_path / "a-Q8_0.gguf"
        model.write_bytes(b"x")
        state = {
            "families": {
                "a": {"selected": "Q8_0", "runs": {"Q8_0": {"file": str(model)}}},
            }
        }
        res = fb.certify_rung_combined(
            4096,
            "2_sigma",
            ["a"],
            str(tmp_path),
            state,
            str(tmp_path / "st.json"),
            8210,
            False,
        )
        r = res[0]
        assert r["verdict"] == "dead"
        assert r["vt_verdict"] == "dead"
        assert r["vt_passes"] == 0
        # gold bars: fwe (>=3) and speed (0 stalls) held everywhere measured
        assert r["fwe_verdict"] is None or r["fwe_verdict"] == "accept"
        assert r["medal"] is None
    finally:
        monkeypatch.undo()


def test_combined_medal_grading_from_records():
    """Addendum 7 (the author's refinement): the medals are PURE
    confidence tiers over each task pass bar - 2_sigma = 2 sigma in
    every test, 1_sigma = at least 1 sigma in every test,
    0.5_sigma = 0.5 sigma in every test (session 40: the tier names
    are the sigma names, the consistency ruling).
    Re-graded from stored records alone."""
    import full_benchmark as fb

    def recs(n):
        return {str(r): 3 for r in range(1, n + 1)}

    gold = {
        "certify": {"8192": recs(20)},
        "certify_vt": {"8192": {str(r): 5 for r in range(1, 21)}},
        "certify_speed": {"8192": {str(r): 0 for r in range(1, 21)}},
        "certify_arc": {str(r): 5 for r in range(1, 21)},
    }
    assert fb.combined_medal(gold, 8192, "2_sigma") == "2_sigma"

    silver = {
        "certify": {"8192": {str(r): 3 if r <= 10 else 0 for r in range(1, 21)}},
        "certify_vt": {"8192": {str(r): 5 for r in range(1, 21)}},
        "certify_speed": {"8192": {str(r): 0 for r in range(1, 21)}},
        "certify_arc": {str(r): 5 for r in range(1, 21)},
    }
    assert fb.combined_medal(silver, 8192, "2_sigma") == "1_sigma"

    bronze = {
        "certify": {"8192": {str(r): 3 if r <= 5 else 0 for r in range(1, 21)}},
        "certify_vt": {"8192": {str(r): 5 for r in range(1, 21)}},
        "certify_speed": {"8192": {str(r): 0 for r in range(1, 21)}},
        "certify_arc": {str(r): 5 for r in range(1, 21)},
    }
    assert fb.combined_medal(bronze, 8192, "2_sigma") == "0.5_sigma"

    weak_bronze = {
        "certify": {"8192": {str(r): 3 if r <= 4 else 0 for r in range(1, 21)}},
        "certify_vt": {"8192": {str(r): 5 for r in range(1, 21)}},
        "certify_speed": {"8192": {str(r): 0 for r in range(1, 21)}},
        "certify_arc": {str(r): 5 for r in range(1, 21)},
    }
    assert fb.combined_medal(weak_bronze, 8192, "2_sigma") is None

    no_pass = {
        "certify": {"8192": {str(r): 0 for r in range(1, 21)}},
        "certify_vt": {"8192": {str(r): 5 for r in range(1, 21)}},
        "certify_speed": {"8192": {str(r): 0 for r in range(1, 21)}},
        "certify_arc": {str(r): 5 for r in range(1, 21)},
    }
    assert fb.combined_medal(no_pass, 8192, "2_sigma") is None
    empty = {}
    assert fb.combined_medal(empty, 8192, "2_sigma") is None


def test_arc_rung_independence_and_namespace():
    """ARC (addendum 6): one measurement per family, rung-independent -
    the same certify_arc records answer every rung, and the medal is
    identical at any depth (nothing to re-measure)."""
    import full_benchmark as fb

    assert fb._task_load(
        {"certify_arc": {str(r): 5 for r in range(1, 12)}}, 8192, "arc", 3, "", "f"
    ) == {r: True for r in range(1, 12)}
    assert fb._task_load({"certify_arc": {"1": 5}}, 262144, "arc", 3, "", "f") == {1: True}

    fst = {}
    fb._task_store(fst, 8192, "arc", 3, 5)
    fb._task_store(fst, 262144, "fwe", 3, 3)
    assert fst["certify_arc"] == {"3": 5}
    assert fst["certify"] == {"262144": {"3": 3}}

    arc_gold = {
        "certify": {"8192": {str(r): 3 for r in range(1, 12)}},
        "certify_vt": {"8192": {str(r): 5 for r in range(1, 12)}},
        "certify_speed": {"8192": {str(r): 0 for r in range(1, 12)}},
        "certify_arc": {str(r): 5 for r in range(1, 12)},
    }
    assert fb.combined_medal(arc_gold, 8192, "1_sigma") == "2_sigma"
    no_arc = {k: v for k, v in arc_gold.items() if k != "certify_arc"}
    assert fb.combined_medal(no_arc, 8192, "1_sigma") is None


def test_sigint_shutdown_sequence(tmp_path, capsys):
    """Addendum 8: Ctrl-C stops cleanly - llama-server pkilled, the tee
    uninstalled, the git tail only when --no-git is absent."""
    import argparse

    import full_benchmark as fb

    assert fb.TASK_PASS_BARS["arc"] == 4  # addendum 8: the 4/5 calibration
    assert fb.TASK_PASS_BARS["vt"] == 4  # addendum 12: the 4/5 calibration
    assert fb.TASK_PASS_BARS["fwe"] == 2  # addendum 13: the 2/3 calibration
    args = argparse.Namespace(no_git=True, dry_run=False)
    import contextlib
    import io

    buf = io.StringIO()
    with pytest.raises(SystemExit) as exc:
        with contextlib.redirect_stdout(buf):
            fb.sigint_shutdown(signal.SIGINT, None, args)
    assert exc.value.code == 130
    out = buf.getvalue()
    assert "SIGINT" in out
    assert "llama-server" in out


def test_speed_dead_stops_the_climb(tmp_path, capsys):
    """Addendum 13: a speed-gate death at rung k persists
    speed_dead_at on the family - the climb stops there, every deeper
    rung skips the family without measuring a single cell (the gate
    measures at depth + 2 * ANSWER_HEADROOM, so a stall at k stalls
    at every deeper rung too)."""
    import full_benchmark as fb

    calls = []

    def fake_measure(task, model, depth, results_dir, run, port, kv_k, kv_v, min_words):
        calls.append((task, run))
        if task == "speed":
            return False, 3, "speed: 3 stall(s)"
        return True, {"fwe": 3, "vt": 5, "arc": 5}[task], f"{task} ok"

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(bench_state_store, "_task_measure", fake_measure)
    try:
        model = tmp_path / "slow-Q8_0.gguf"
        model.write_bytes(b"x")
        state: dict[str, Any] = {
            "families": {"slow": {"selected": "Q8_0", "runs": {"Q8_0": {"file": str(model)}}}}
        }
        res = fb.certify_rung_combined(
            4096,
            "1_sigma",
            ["slow"],
            str(tmp_path),
            state,
            str(tmp_path / "st.json"),
            8210,
            False,
        )
        r = res[0]
        assert r["verdict"] == "dead"
        assert r["speed_verdict"] == "dead"
        assert state["families"]["slow"]["speed_dead_at"] == 4096
        calls.clear()
        res = fb.certify_rung_combined(
            8192,
            "1_sigma",
            ["slow"],
            str(tmp_path),
            state,
            str(tmp_path / "st.json"),
            8210,
            False,
        )
        assert calls == []
        assert res[0].get("skipped") == "speed gate died at 4,096"
        assert "not climbed" in capsys.readouterr().out
    finally:
        monkeypatch.undo()
