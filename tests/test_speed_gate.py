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


def test_tournament_rank_majority():
    import full_benchmark as fb

    depths = fb.TOURNAMENT_DEPTHS
    # champion: all five top out
    r = fb.tournament_rank([None] * 5, depths)
    assert r["rank_depth"] == 262144 and r["full_holds"] == 5
    # a flicker: one climb falls at 131072, four top out -> 131072 holds 4/5
    r = fb.tournament_rank([131072, None, None, None, None], depths)
    assert r["rank_depth"] == 262144  # 4/5 majority at the top rung
    assert r["passes"][262144] == 4 and r["passes"][65536] == 5
    # a fall: three climbs fall at 65536, two top out -> 65536 has 2/5
    r = fb.tournament_rank([65536, 65536, 65536, None, None], depths)
    assert r["rank_depth"] == 32768  # 5/5 at 32768; 2/5 at 65536 fails majority
    assert r["passes"][65536] == 2
    # majority boundary: 3/5 passes
    r = fb.tournament_rank([65536, 65536, None, None, None], depths)
    assert r["rank_depth"] == 262144
    assert r["passes"][262144] == 3


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
    # climb 1 (seed 1) falls at 4096 -> early stop (1 call); climbs 2-5
    # hold every depth (7 calls each) -> 29 total
    assert len(calls) == 29
    assert tour["fall_depths"] == [4096, None, None, None, None]
    assert tour["full_holds"] == 4
    assert tour["rank_depth"] == 262144  # 4/5 majority at the top rung
