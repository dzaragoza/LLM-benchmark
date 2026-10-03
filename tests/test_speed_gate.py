"""speed_gate.py dump-reuse rules: a dump measured at one ctx must never
satisfy reuse at a different ctx (the addendum-135 bug class: the reuse
check compared timestamps only, so a ctx-4096 dump was re-graded as a
--ctx 32768 cell in 88 ms with no server launch). Server-dependent
paths are avoided via the bench() reuse branch, the repo's established
monkeypatch style."""

import json
import os
import time

import pytest

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
    assert tour["reliable_depth"] == 262144  # 20/21 at 1 sigma clears every rung


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
    # sigma rank: 15/21 top out -> reliable 262144 at 1 sigma (mode retired)
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
    assert out["reliable_depth"] == 262144 and out["full_holds"] == 21
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


def test_rescore_tournament(tmp_path, capsys):
    """Session 37, addendum 4: the saved 3/3 falls re-scored from the
    raw climb CSVs under 1/3 - a 1/3-or-2/3 partial cell becomes a
    HOLD (fall moves deeper or drops for re-run), a 0/3 cell still
    falls at the same rung."""
    import csv as csv_mod
    import full_benchmark as fb
    import ruler_gate as rg

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
    state = {
        "families": {
            "fam": {"tournament_falls": {"1": 8192, "2": 8192, "3": 4096}}
        }
    }
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
            "1": 8192,   # fell at 8192: cell(1, 8192)=False, cell(1,4096)=True
            "2": None,   # topped out: every cell True
            "3": 4096,   # cell(3, 8192) unmeasured, cell(3,4096)=False
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

    def fake_fwe_pass(model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None):
        ran.append(seed)
        return True, {"correct": 1, "depth": rung}

    def fake_speed_pass(model, rung, corpus, port, results_dir, kv_quant_k=None, kv_quant_v=None):
        return True, {"worst": 30.0}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(fb, "fwe_pass", fake_fwe_pass)
    monkeypatch.setattr(fb, "speed_pass", fake_speed_pass)
    try:
        model = tmp_path / "good-Q8_0.gguf"
        model.write_bytes(b"x")
        # candidate A: 8 passing cells at 8192 historically; the
        # accept bar fires EARLY - at 11/11 measured cells
        # (lo(11,11)=0.917 >= 0.5, count 11 >= floor 11)
        state = {
            "families": {
                "good": {
                    "selected": "Q8_0",
                    "runs": {"Q8_0": {"file": str(model)}},
                    "tournament_falls": {
                        "1": None, "2": None, "3": None, "4": None,
                        "5": 16384, "6": 16384, "7": 16384, "8": 16384,
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
            8192, "1_sigma", ["good", "other"], str(tmp_path), state, str(tmp_path / "st.json"), 8210, False
        )
        first = [r for r in res if r["family"] == "good"][0]
        assert first["verdict"] == "accept"
        # historical cells at 8192: climbs 1-4 top + 5-8 fell deeper = 8 passes
        # runs 9-21 are fresh (13 seeds), never re-measured
        assert sorted(ran) == [9, 10, 11]
        assert first["cells_measured"] == 11 and first["passes"] == 11
        other = [r for r in res if r["family"] == "other"][0]
        assert other.get("skipped") == "rung already answered"
        # direct cells persisted
        direct = state["families"]["good"]["certify"]["8192"]
        assert direct == {str(r): True for r in (9, 10, 11)}
    finally:
        monkeypatch.undo()


def test_certify_rung_dead(tmp_path, capsys):
    """Early reject: a candidate whose remaining cells cannot reach
    the 1-sigma bar is declared DEAD without running a single cell."""
    import full_benchmark as fb

    ran = []

    def fake_fwe_pass(model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None):
        ran.append(seed)
        return True, {"correct": 1, "depth": rung}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(fb, "fwe_pass", fake_fwe_pass)
    try:
        model = tmp_path / "dead-Q8_0.gguf"
        model.write_bytes(b"x")
        # 9 climbs FELL AT 8192 (9 measured fails, 12 remaining):
        # best case 12/21 passes, lo(12,21)=0.463 < 0.5 -> dead
        falls = {str(i): 8192 for i in range(1, 10)}
        state = {"families": {"dead": {
            "selected": "Q8_0",
            "runs": {"Q8_0": {"file": str(model)}},
            "tournament_falls": falls,
        }}}
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
    def fake_fwe_pass(model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None):
        ran.append(seed)
        return True, {"correct": 1, "depth": rung}
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(fb, "fwe_pass", fake_fwe_pass)
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
            16384, "at_least_one", ["one", "none"], str(tmp_path), state, str(tmp_path / "st.json"), 8210, False
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
    def fake_fwe_pass(model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None):
        ran.append(seed)
        return False, {"correct": 0, "depth": rung}
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(fb, "fwe_pass", fake_fwe_pass)
    try:
        model = tmp_path / "zero-Q8_0.gguf"
        model.write_bytes(b"x")
        falls = {str(i): 16384 for i in range(1, 22)}
        state = {"families": {"zero": {
            "selected": "Q8_0",
            "runs": {"Q8_0": {"file": str(model)}},
            "tournament_falls": falls,
        }}}
        res = fb.certify_rung(
            16384, "at_least_one", ["zero"], str(tmp_path), state, str(tmp_path / "st.json"), 8210, False
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
    def fake_fwe_pass(model, rung, results_dir, seed, port, kv_quant_k=None, kv_quant_v=None):
        ran.append(seed)
        return True, {"correct": 1, "depth": rung}
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(fb, "fwe_pass", fake_fwe_pass)
    try:
        model = tmp_path / "s2-Q8_0.gguf"
        model.write_bytes(b"x")
        falls = {str(i): 8192 for i in range(1, 10)}
        state = {"families": {"s2": {
            "selected": "Q8_0",
            "runs": {"Q8_0": {"file": str(model)}},
            "tournament_falls": falls,
        }}}
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
