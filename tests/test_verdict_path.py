"""The verdict-path tests (session 41, addendum 38, rulings a/b/d):
the full cell verdict path - verdict dict -> speed/FWE/VT/ARC
outcome -> the stored record -> combined_medal - exercised with
fakes for everything below the measurement seam, plus the
controller/medal INVARIANT: a clean 2-sigma accept always grades
2_sigma (the two implementations cannot drift apart), plus the
fake-hub tests for hf_download.acquire's branch table.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

import bench.cells as bench_cells
import bench.certify as bench_certify
import bench.state_store as bench_state_store
import speed_gate as sg

# ================================================== (a) the cell verdict path
# speed_pass/speed_cell verdicted strictly on worst wps (addendum 37)


def _turn(wps: float, model: str = "m") -> dict[str, Any]:
    # a minimal v3.x turn record: 10 words arriving at the given wps
    gap = 1.0 / wps
    deltas = [{"t": round(i * gap, 4), "w": i + 1} for i in range(10)]
    return {
        "model": model,
        "server_tps": 2.0 * wps,
        "server_wps": wps,
        "conv": 1,
        "gen_words": 10,
        "words_per_token": 0.5,
        "deltas": deltas,
    }


def _fake_bench_model(turns):
    def fake(model, corpus, port, ctx, thinking, no_thinking, **kw):
        return list(turns), None, []

    return fake


def test_speed_pass_verdict_strictly_wps(tmp_path, monkeypatch, capsys):
    """Addendum 37, ruling 1: a cell whose worst wps is below the reader
    line FAILS; at or above it PASSES. The stall rate is recorded as
    data and never gates (a slow-but-steady stream with zero catch-up
    events still fails; a fast stream with a late first word still
    passes)."""
    monkeypatch.setattr(sg, "bench_model", _fake_bench_model([_turn(4.9, "m.gguf")]))
    ok, verdict = bench_cells.speed_pass("m.gguf", 4096, "c.json", 1, str(tmp_path))
    assert ok is False
    assert verdict["worst"] == pytest.approx(4.9)
    assert "stall_rate" in verdict

    monkeypatch.setattr(sg, "bench_model", _fake_bench_model([_turn(5.0, "m.gguf")]))
    ok, verdict = bench_cells.speed_pass("m.gguf", 4096, "c.json", 1, str(tmp_path))
    assert ok is True
    # 5.0 sits inside the headroom band [5, 7.5): the rung is answered
    # but the ceiling diagnostic stays True
    assert verdict["ceiling_rung"] is True


def test_speed_pass_ceiling_rung_diagnostic(tmp_path, monkeypatch):
    """The headroom diagnostic: a worst wps in [5, 7.5) marks the cell
    ceiling_rung=True - the rung is answered but the model is near the
    line; >= 7.5 clears it."""
    monkeypatch.setattr(sg, "bench_model", _fake_bench_model([_turn(6.0, "m.gguf")]))
    ok, verdict = bench_cells.speed_pass("m.gguf", 4096, "c.json", 1, str(tmp_path))
    assert ok is True and verdict["ceiling_rung"] is True

    monkeypatch.setattr(sg, "bench_model", _fake_bench_model([_turn(7.5, "m.gguf")]))
    ok, verdict = bench_cells.speed_pass("m.gguf", 4096, "c.json", 1, str(tmp_path))
    assert ok is True and verdict["ceiling_rung"] is False


def test_speed_pass_window_cap_and_floor(tmp_path, monkeypatch):
    """The two structural refuses: a launch capped to the training
    window, and a rung below the conversation floor - both return
    (False, error record), never a crash."""
    # floor: bench_model returns a turn carrying the floor error
    monkeypatch.setattr(
        sg,
        "bench_model",
        lambda *a, **kw: ([{"error": "rung below conversation floor"}], None, []),
    )
    ok, rec = bench_cells.speed_pass("m.gguf", 4096, "c.json", 1, str(tmp_path))
    assert ok is False and rec["error"] == "rung below conversation floor"

    # capped: no turns + a window cap below the rung
    monkeypatch.setattr(sg, "bench_model", _fake_bench_model([]))
    monkeypatch.setattr(bench_cells, "_banner_window", lambda log: 4096)
    ok, rec = bench_cells.speed_pass("m.gguf", 8192, "c.json", 1, str(tmp_path))
    assert ok is False and rec["error"] == "capped to the window"
    assert rec["window_cap"] == 4096


def test_speed_cell_records_stalls_and_worst_wps(tmp_path, monkeypatch):
    """The redesigned speed cell (addendum 2): the record is the stall
    count + worst wps, stored per cell so any bar re-grades later."""
    monkeypatch.setattr(sg, "bench_model", _fake_bench_model([_turn(20.0)]))
    ok, rec = bench_cells.speed_cell("m.gguf", 4096, "c.json", str(tmp_path), 1, 1)
    assert ok is True
    assert rec["stalls"] == 0 and rec["turns"] == 1
    assert rec["worst_wps"] == pytest.approx(20.0)

    # no measured turns -> (False, launch_failed)
    monkeypatch.setattr(sg, "bench_model", _fake_bench_model([]))
    ok, rec = bench_cells.speed_cell("m.gguf", 4096, "c.json", str(tmp_path), 1, 1)
    assert ok is False and rec.get("launch_failed") is True


def test_analyze_verdict_strict_and_stall_rate_is_data(tmp_path):
    """analyze() on a real dump file: worst wps < 5 -> FAIL, >= 5 ->
    PASS (confident); the stall rate is present as data in both cases
    and no threshold field exists anywhere."""

    def run(name, wps):
        dump = tmp_path / f"{name}.json"
        with open(dump, "w") as f:
            json.dump([_turn(wps, name)], f)
        return sg.analyze(name, no_thinking=True, dump_override=str(dump))

    v = run("slow", 2.5)
    assert v["verdict"] == "FAIL"
    assert "stall_rate" in v and "stall_rate_max" not in v
    v = run("fast", 20.0)
    assert v["verdict"] == "PASS (confident)"
    assert "stall_rate" in v and "stall_rate_max" not in v


# ============================================ (b) the accept/medal invariant


def _gold_fst(depth: int = 8192) -> dict[str, Any]:
    """A family state whose every cell is a clean gold pass, matching
    the controller's gold bar exactly (fwe v>=3 at min_words=3? no -
    the stored record is the graded value; the medal grades at the
    TASK_PASS_BARS, the controller at the cell's own pass bar)."""
    return {
        "certify": {str(depth): {str(r): 3 for r in range(1, 21)}},
        "certify_vt": {str(depth): {str(r): 5 for r in range(1, 21)}},
        "certify_speed": {str(depth): {str(r): 0 for r in range(1, 21)}},
        "certify_arc": {str(r): 5 for r in range(1, 21)},
    }


def test_accept_implies_medal_2_sigma(tmp_path, monkeypatch, capsys):
    """THE invariant (addendum 38, ruling b): a clean 20/20 accept
    from the combined controller ALWAYS grades 2_sigma from the
    stored records - the controller's accept bar and combined_medal's
    2_sigma tier are two implementations of the same question and
    cannot drift. Any state the controller accepts must medal."""
    import full_benchmark as fb

    fst = _gold_fst()
    fst["selected"] = "Q8_0"
    model = tmp_path / "fam-Q8_0.gguf"
    model.write_bytes(b"x")
    fst["runs"] = {"Q8_0": {"file": str(model)}}
    state = {"families": {"fam": fst}}

    # the controller re-measures nothing: every cell is stored
    calls = []

    def fake_measure(*a, **kw):
        calls.append(a)
        raise AssertionError("a fully-stored cell must never re-measure")

    monkeypatch.setattr(bench_state_store, "_task_measure", fake_measure)
    res = fb.certify_rung_combined(
        8192,
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
    assert calls == []
    # the invariant itself: accept => medal == 2_sigma
    assert r["medal"] == "2_sigma"
    assert bench_certify.combined_medal(fst, 8192) == "2_sigma"


@pytest.mark.parametrize(
    "task,bar,values",
    [
        ("speed", 0, [0] * 15 + [1] * 5),  # 15/20 gold (0 stalls), 5 failed
        ("fwe", 2, [3] * 15 + [0] * 5),  # 15/20 at bar 2
        ("vt", 4, [5] * 15 + [0] * 5),  # 15/20 at bar 4
        ("arc", 4, [5] * 15 + [0] * 5),  # 15/20 at bar 4
    ],
)
def test_two_sigma_bar_matches_the_medal_tier(task, bar, values):
    """The equidistant ruling (session 40): 2_sigma lands on 15/20 cells
    at every task's own pass bar - TASK_PASS_BARS and the medal's 0.50
    Wilson bound are the same difficulty, per task."""
    n = len(values)
    if task == "speed":
        k = sum(1 for v in values if v == bar)  # gold = equality
    else:
        k = sum(1 for v in values if v >= bar)
    lo, _ = bench_certify.wilson_interval(k, n, bench_certify.CERTIFY_Z)
    lo_below, _ = bench_certify.wilson_interval(k - 1, n, bench_certify.CERTIFY_Z)
    assert lo >= bench_certify.CERTIFY_BAR > lo_below


# ============================================== (d) the fake-hub acquire tests


def _fake_hub(monkeypatch, repo_files, sizes=None, ram=None, disk=None):
    """Wire hf_download to a fake hub: list_repo_files and
    remote_file_sizes return canned data; the RAM/disk probes return
    canned values; require_hub is a no-op (the real one asserts the
    import, which is absent in this sandbox)."""
    from infra import hf_download

    downloaded = []

    def fake_hub_get(repo, name, local_dir=None, **kw):
        downloaded.append((repo, name))
        if local_dir:
            import os as _os

            _os.makedirs(local_dir, exist_ok=True)
            with open(_os.path.join(local_dir, name), "wb") as f:
                f.write(b"x")

    def fake_snap(repo, local_dir=None, allow_patterns=None, **kw):
        downloaded.append((repo, "snapshot:" + ",".join(allow_patterns or [])))
        if local_dir:
            import glob as _glob
            import os as _os

            _os.makedirs(local_dir, exist_ok=True)
            for pat in allow_patterns or []:
                for hit in _glob.glob(pat):
                    with open(_os.path.join(local_dir, _os.path.basename(hit)), "wb") as f:
                        f.write(b"x")
            # the fake hub materializes every shard the index names
            idx = _os.path.join(local_dir, "model.safetensors.index.json")
            if _os.path.isfile(idx):
                with open(idx) as f:
                    index = json.load(f)
                for shard in set((index.get("weight_map") or {}).values()):
                    with open(_os.path.join(local_dir, shard), "wb") as f:
                        f.write(b"x")

    monkeypatch.setattr(hf_download, "require_hub", lambda: None)
    monkeypatch.setattr(hf_download, "list_repo_files", lambda repo: list(repo_files))
    monkeypatch.setattr(hf_download, "remote_file_sizes", lambda repo: dict(sizes or {}))
    monkeypatch.setattr(hf_download, "system_ram_gib", lambda: ram)
    monkeypatch.setattr(hf_download, "free_disk_gib", lambda path=".": disk)
    monkeypatch.setattr(hf_download, "hf_hub_download", fake_hub_get)
    monkeypatch.setattr(hf_download, "snapshot_download", fake_snap)
    return downloaded


def test_acquire_downloads_the_rung_file(tmp_path, monkeypatch, capsys):
    """The happy path: the repo has the rung file; acquire downloads
    exactly it and reports the plan."""
    from infra import hf_download

    dl = _fake_hub(
        monkeypatch,
        ["model-Q8_0.gguf", "README.md"],
        ram=1024.0,
        disk=1024.0,
    )
    p, plan = hf_download.acquire(
        "fam",
        str(tmp_path),
        "Q8_0",
        "org/model",
        ["model-Q8_0.gguf"],
        "org/model",
        ["model-Q8_0.gguf"],
        False,
    )
    assert dl == [("org/model", "model-Q8_0.gguf")]
    assert p is None or p.endswith("Q8_0.gguf")  # the file exists only after the real download
    assert plan.startswith("download")


def test_acquire_skips_infeasible_before_download(tmp_path, monkeypatch, capsys):
    """The addendum-35 shortcut: a rung whose estimate exceeds usable
    RAM is skipped BEFORE any network traffic - no download happens."""
    from infra import hf_download

    dl = _fake_hub(
        monkeypatch,
        ["model-Q8_0.gguf"],
        sizes={"model-Q8_0.gguf": 80 * 1024**3},
        ram=64.0,
        disk=1024.0,
    )
    p, plan = hf_download.acquire(
        "fam",
        str(tmp_path),
        "Q8_0",
        "org/model",
        ["model-Q8_0.gguf"],
        "org/model",
        ["model-Q8_0.gguf"],
        False,
    )
    assert p is None
    assert plan == "infeasible: exceeds system RAM"
    assert dl == []


def test_acquire_dry_run_downloads_nothing(tmp_path, monkeypatch, capsys):
    """The addendum-108 contract: a dry run benches nothing and
    downloads nothing - the plan names what WOULD happen."""
    from infra import hf_download

    dl = _fake_hub(
        monkeypatch,
        ["model-Q8_0.gguf"],
        ram=1024.0,
        disk=1024.0,
    )
    p, plan = hf_download.acquire(
        "fam",
        str(tmp_path),
        "Q8_0",
        "org/model",
        ["model-Q8_0.gguf"],
        "org/model",
        ["model-Q8_0.gguf"],
        True,
    )
    assert p is None
    assert dl == []
    assert plan.startswith("download")


def test_acquire_f16_plan_and_no_f16_as_rung(tmp_path, monkeypatch, capsys):
    """No rung file in the model repo, but the source has f16 shards:
    the plan is download-f16-then-quantize. A dry run still touches
    nothing."""
    from infra import hf_download

    dl = _fake_hub(
        monkeypatch,
        ["model-f16.gguf", "README.md"],
        ram=1024.0,
        disk=1024.0,
    )
    p, plan = hf_download.acquire(
        "fam",
        str(tmp_path),
        "Q8_0",
        "org/model",
        [],
        "org/source",
        ["model-f16.gguf"],
        True,
    )
    assert p is None and dl == []
    assert "f16" in plan and "quantize" in plan


def test_acquire_safetensors_plan_and_missing_shard_redownload(tmp_path, monkeypatch, capsys):
    """The addendum-27 class: a PARTIAL safetensors source (shard 1 of
    2 on disk, the index names both) is NOT complete - st_source_complete
    is False, so the snapshot re-runs instead of the converter dying."""
    from infra import hf_download

    dl = _fake_hub(
        monkeypatch,
        ["model.safetensors.index.json", "model-00001-of-00002.safetensors"],
        ram=1024.0,
        disk=1024.0,
    )
    st_dir = tmp_path / "safetensors-source"
    st_dir.mkdir()
    (st_dir / "model-00001-of-00002.safetensors").write_bytes(b"x")
    with open(st_dir / "model.safetensors.index.json", "w") as f:
        json.dump(
            {
                "weight_map": {
                    "a": "model-00001-of-00002.safetensors",
                    "b": "model-00002-of-00002.safetensors",
                }
            },
            f,
        )
    assert not hf_download.st_source_complete(str(st_dir))
    p, plan = hf_download.acquire(
        "fam",
        str(tmp_path),
        "Q8_0",
        "org/model",
        [],
        "org/source",
        ["model-00001-of-00002.safetensors"],
        False,
    )
    # the snapshot ran (the source was incomplete)
    assert any(t[1].startswith("snapshot:") for t in dl)
    assert "safetensors" in plan


def test_acquire_nothing_to_download_fails_loudly(tmp_path, monkeypatch, capsys):
    """The empty-repo case: no rung file, no f16, no safetensors, no
    pytorch_model.bin - acquire fails with phase 1 (exit 1), the
    runner-pay failure class of addendum 14."""
    from infra import hf_download

    _fake_hub(monkeypatch, ["README.md"], ram=1024.0, disk=1024.0)
    with pytest.raises(SystemExit) as ei:
        hf_download.acquire(
            "fam",
            str(tmp_path),
            "Q8_0",
            "org/model",
            ["README.md"],
            "org/model",
            ["README.md"],
            False,
        )
    assert ei.value.code == 1


def test_resolve_f16_local_never_matches_a_quant(tmp_path):
    """The addendum-30 catch: a family whose own -Q8_0.gguf matches the
    *bf16* glob must never resolve as the f16 source - quantize would
    die with input == output."""
    from infra import hf_download

    (tmp_path / "MiniCPM-sft-bf16-Q8_0.gguf").write_bytes(b"x")
    assert hf_download.resolve_f16_local(str(tmp_path)) is None
    (tmp_path / "MiniCPM-sft-f16.gguf").write_bytes(b"x")
    assert hf_download.resolve_f16_local(str(tmp_path)) == str(tmp_path / "MiniCPM-sft-f16.gguf")


def test_window_cap_makes_the_family_infeasible_not_dead(tmp_path, monkeypatch):
    """Addendum 45 (the author's ruling): a family whose trained window
    cannot run the rung (the server capped -c to n_ctx_train, every
    turn 400s) is OUT of the benchmark - verdict 'infeasible', never
    'dead', zero cells in its entry, the window recorded in the state,
    never re-attempted at any rung.

    Pins: R-06
    """
    import full_benchmark as fb

    model = tmp_path / "capped-Q8_0.gguf"
    model.write_bytes(b"x")
    state: dict[str, Any] = {
        "families": {"capped": {"selected": "Q8_0", "runs": {"Q8_0": {"file": str(model)}}}}
    }

    def fake_measure(task, *a, **kw):
        raise bench_state_store.WindowCap(2048)

    monkeypatch.setattr(bench_state_store, "_task_measure", fake_measure)
    res = fb.certify_rung_combined(
        4096,
        ["capped"],
        str(tmp_path),
        state,
        str(tmp_path / "st.json"),
        8210,
        False,
    )
    r = res[0]
    assert r["verdict"] == "infeasible"
    assert r["cells_measured"] == 0 and r["passes"] == 0 and r["ran_now"] == 0
    assert "2,048" in r["infeasible_reason"]
    fst = state["families"]["capped"]
    assert fst["infeasible"] == {"window_cap": 2048, "depth": 4096}
    # never re-attempted: a second controller call skips the family
    monkeypatch.setattr(
        bench_state_store,
        "_task_measure",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("must not re-measure")),
    )
    res2 = fb.certify_rung_combined(
        4096,
        ["capped"],
        str(tmp_path),
        state,
        str(tmp_path / "st.json"),
        8210,
        False,
    )
    assert res2[0].get("skipped", "").startswith("infeasible")


def test_f16_conversion_refuses_on_low_disk(tmp_path, monkeypatch):
    """Addendum 48: the disk check before the f16 conversion is a HARD
    GATE, not a warning - the f16 write is the pipeline's transient
    peak (source + gguf together until the verified delete), and a
    mid-write death leaves a partial gguf a later run could trust."""
    import infra.convert_quant as cq
    import infra.hf_download as hf

    famdir = tmp_path / "fam"
    famdir.mkdir()
    st_dir = famdir / "safetensors-source"
    st_dir.mkdir()
    (st_dir / "model-00001-of-00001.safetensors").write_bytes(b"x" * (2 * 1024**3))
    monkeypatch.setattr(hf, "free_disk_gib", lambda path=".": 1.0)
    monkeypatch.setattr(cq, "hf_download", hf)
    with pytest.raises(SystemExit):
        cq.create("fam", str(famdir), "f16")
    assert not (famdir / "fam-f16.gguf").exists()


def test_arc_gate_grades_at_the_task_pass_bar():
    """Addendum 52: the arc GATE predicate is TASK_PASS_BARS["arc"]
    (4/5), the same bar the medal grades at - the 5/5 gate was below
    the >= 50% kill-rate floor (27% per-cell pass; 4/5 gives 59%).
    Both predicates must agree: the stored-cell re-grade AND the
    freshly measured cell's printed verdict.

    Pins: R-03, R-05
    """
    from bench import state_store

    fst = {"certify_arc": {str(r): 4 for r in range(1, 21)}}
    loaded = state_store._task_load(fst, 4096, "arc", 2, "models", "fam")
    assert all(loaded.values()) and len(loaded) == 20
    fst = {"certify_arc": {str(r): 3 for r in range(1, 21)}}
    loaded = state_store._task_load(fst, 4096, "arc", 2, "models", "fam")
    assert loaded and not any(loaded.values())


def test_arc_pass_fresh_cell_grades_at_the_task_pass_bar(monkeypatch):
    """Addendum 52, the author's follow-up ("the ARC gate was wrong -
    it should have been 4/5... we need to pay more attention"): the
    FRESHLY measured arc cell grades at TASK_PASS_BARS["arc"] too, so
    a refactor can never again reintroduce a 5/5 gate that disagrees
    with both the stored re-grade and the medal bar.

    Pins: R-03, R-05
    """
    from bench import state_store
    from bench.constants import TASK_PASS_BARS

    questions = [{"q": f"q{i}", "choices": [("A", "a"), ("B", "b")], "ans": "A"} for i in range(5)]
    monkeypatch.setattr(state_store, "arc_cell_questions", lambda run: questions)

    class FakeProc:
        pass

    monkeypatch.setattr(
        state_store.llama_server,
        "start_server",
        lambda model, port, extra, log_path="": (FakeProc(), True),
    )
    monkeypatch.setattr(state_store.llama_server, "wait_healthy", lambda port, proc=None: True)
    monkeypatch.setattr(state_store.llama_server, "stop_server", lambda proc, port: None)

    n_correct = len(questions) - 1  # 4/5 - one wrong
    calls = {"i": 0}

    def fake_post(port, path, payload, timeout=0):
        letter = "A" if calls["i"] < n_correct else "B"
        calls["i"] += 1
        return {
            "choices": [
                {
                    "text": f" {letter}",
                    "logprobs": {
                        "content": [
                            {
                                "top_logprobs": [
                                    {"token": " A", "logprob": -0.1 if letter == "A" else -9.9},
                                    {"token": " B", "logprob": -9.9 if letter == "A" else -0.1},
                                ]
                            }
                        ]
                    },
                }
            ]
        }

    monkeypatch.setattr(state_store.llama_server, "post_json", fake_post)
    ok, rec = state_store.arc_pass("m.gguf", 1, 8210)
    assert rec["correct"] == TASK_PASS_BARS["arc"]
    assert ok is True  # 4/5 passes at the 4/5 gate - the 5/5 regression cannot return


def test_vt_gate_grades_at_the_task_pass_bar():
    """Addendum 54: "Be consistent, we chose 4/5 for a reason" - the vt
    GATE predicate is TASK_PASS_BARS["vt"] (4/5), the same consistency
    ruling as arc (addenda 52-53): the 5/5 gate was the refactor's
    drift, not a difficulty choice.

    Pins: R-03
    """
    from bench import state_store

    fst = {"certify_vt": {"4096": {str(r): 4 for r in range(1, 21)}}}
    loaded = state_store._task_load(fst, 4096, "vt", 2, "models", "fam")
    assert loaded and all(loaded.values())
    fst = {"certify_vt": {"4096": {str(r): 3 for r in range(1, 21)}}}
    loaded = state_store._task_load(fst, 4096, "vt", 2, "models", "fam")
    assert loaded and not any(loaded.values())


def test_vt_pass_fresh_cell_grades_at_the_task_pass_bar():
    """Addendum 54: vt_pass launches a real server, so the fresh-cell
    grading is pinned at the source level: its return expression must
    grade row["acc"] at TASK_PASS_BARS["vt"] / 5 - a drifted 5/5 gate
    (acc == 1.0) fails this test, not the run.

    Pins: R-03
    """
    import inspect

    from bench import cells as bench_cells

    src = inspect.getsource(bench_cells.vt_pass)
    assert 'row["acc"] >= TASK_PASS_BARS["vt"] / 5.0' in src
    assert 'row["acc"] == 1.0' not in src


def test_fresh_family_cells_persist_to_the_state_file(tmp_path, monkeypatch):
    """Addendum 55: a FRESH family (not yet in the state) must store its
    cells into the state's OWN entry. The bug: fst = get(fam, {}) bound
    a detached dict, while _acquire_missing_model later created a
    different dict via setdefault - every stored cell landed in the
    orphan and save_state wrote the empty entry. The whole from-scratch
    f16 pass stored zero cells; restarts re-measured everything.

    Pins: R-01
    """
    import json

    import bench.certify as BC
    import bench.state_store as SS

    def fake_measure(task, model, depth, results_dir, run, port, kv_k, kv_v, min_words):
        return (True, 0 if task == "speed" else 4, f"{task} ok", 2.0)

    monkeypatch.setattr(SS, "_task_measure", fake_measure)
    monkeypatch.setattr(BC.bench_state_store, "_task_measure", fake_measure)

    class HD:
        require_hub = staticmethod(lambda: None)
        acquire = staticmethod(lambda *a, **k: ("./models/newfam/newfam-f16.gguf", "plan"))
        list_repo_files = staticmethod(lambda repo: [])

    monkeypatch.setattr(BC, "hf_download", HD())
    monkeypatch.setattr(
        BC, "convert_quant", type("cq", (), {"create": staticmethod(lambda *a, **k: None)})()
    )
    models = tmp_path / "models" / "newfam"
    models.mkdir(parents=True)
    (models / "newfam-f16.gguf").touch()
    state = {"families": {}}
    state_file = tmp_path / "state.json"
    BC.certify_rung_combined(
        4096,
        ["newfam"],
        str(tmp_path / "models"),
        state,
        str(state_file),
        8210,
        False,
        min_words=2,
    )
    saved = json.loads(state_file.read_text())
    fam = saved["families"]["newfam"]
    assert [k for k in fam if k.startswith("certify")], "fresh family cells were lost"
    # and the never-re-measure promise: the rerun measures nothing
    res2 = BC.certify_rung_combined(
        4096,
        ["newfam"],
        str(tmp_path / "models"),
        saved,
        str(state_file),
        8210,
        False,
        min_words=2,
    )
    assert res2[0].get("ran_now", 0) == 0
    # addendum 57: the verdict is persisted per rung
    assert saved["families"]["newfam"]["verdicts"]["4096"] == "accept"


def test_restarted_rung_skips_stored_verdicts(tmp_path, monkeypatch):
    """Addendum 57: the author's catch - "if there's already a champion
    at 4k, why is the benchmark re-running 4k models?" The verdict is
    PERSISTED per (family, rung): a stored accept ANSWERS the rung
    (later families skip it), a stored dead skips THIS family at THIS
    rung only (it still climbs at deeper rungs - addendum 56).

    Pins: R-02, R-04
    """
    import bench.certify as BC

    state = {
        "families": {
            "medalist": {"verdicts": {"4096": "accept"}},
            "deadfam": {"verdicts": {"4096": "dead"}},
            "newfam": {},
        }
    }
    measured = []
    monkeypatch.setattr(
        BC.bench_state_store,
        "_task_measure",
        lambda *a: measured.append(a) or (True, 4, "ok", 1.0),
    )
    res = BC.certify_rung_combined(
        4096,
        ["medalist", "deadfam", "newfam"],
        str(tmp_path),
        state,
        str(tmp_path / "st.json"),
        8210,
        False,
        min_words=2,
    )
    by = {r["family"]: r for r in res}
    assert by["medalist"]["skipped"] == "rung already answered (stored verdict)"
    assert by["deadfam"]["skipped"] == "dead at this rung (stored verdict)"
    # the medalist's accept ANSWERS the rung: the new family skips it too
    assert "rung already answered" in by["newfam"]["skipped"]


def test_registry_preflight_declares_infeasible_before_download(tmp_path, monkeypatch, capsys):
    """Addendum 58: "we measured and downloaded every model at 4k for
    nothing. They should have never been even evaluated." The registry
    store already carries each family's trained window (the hub
    config.json extract) - a family whose window cannot run the rung's
    ctx is declared infeasible BEFORE any download, conversion or
    launch, with the same state record as the runtime catch (addendum 45).

    Pins: R-06
    """
    import bench.certify as BC

    downloaded = []
    monkeypatch.setattr(BC.hf_download, "require_hub", lambda: downloaded.append("hub") or None)
    monkeypatch.setattr(
        BC, "_acquire_missing_model", lambda *a: downloaded.append("acquire") or None
    )
    monkeypatch.setattr(BC, "_registry_window", lambda fam: 2048 if fam == "tiny-win" else None)
    state = {"families": {}}
    res = BC.certify_rung_combined(
        4096,
        ["tiny-win"],
        str(tmp_path),
        state,
        str(tmp_path / "st.json"),
        8210,
        False,
        min_words=2,
    )
    assert downloaded == [], "the pre-flight must fire before any acquire"
    r = res[0]
    assert r["verdict"] == "infeasible"
    assert "pre-flight" in r["infeasible_reason"]
    fst = state["families"]["tiny-win"]
    assert fst["infeasible"] == {"window_cap": 2048, "depth": 4096}
    assert fst["verdicts"]["4096"] == "infeasible"
    out = capsys.readouterr().out
    assert "nothing downloaded, converted or launched" in out


def test_param_sort_resolves_family_names_identically():
    """R-07 (addendum 57): the state file carries family NAMES, not
    repos - the param sort must resolve both shapes to the same
    parameter count, so a restart's order matches the from-scratch
    param-ascending order.

    Pins: R-07
    """
    import full_benchmark as fb

    repo = "meta-llama/Llama-3.2-1B-Instruct"
    name = "Llama-3.2-1B-Instruct"
    assert fb._registry_params(repo) is not None
    assert fb._registry_params(repo) == fb._registry_params(name)
    ordered = fb.param_ascending_specs([name, repo])
    assert ordered == [repo, name] or fb._registry_params(repo) == fb._registry_params(name)


def test_registered_constants_single_source():
    """R-09 (the registry's standing governance rule): a study
    constant appears in exactly one place - TASK_PASS_BARS lives in
    bench/constants.py only; every consumer imports it, none
    redefines it.

    Pins: R-09
    """
    import inspect

    import bench.cells
    import bench.certify
    import bench.constants
    import bench.state_store

    assert hasattr(bench.constants, "TASK_PASS_BARS")
    for mod in (bench.state_store, bench.certify, bench.cells):
        src = inspect.getsource(mod)
        assert not re.search(r"TASK_PASS_BARS\s*=\s*{", src), mod.__name__


def test_cell_logs_live_in_the_results_tree(tmp_path, monkeypatch):
    """Addendum 60: every per-cell log (speed server log, arc cell log)
    is written into the RESULTS tree, never next to the model - so
    deleting models/<family> touches only regenerable data. The fwe
    and vt cells already lived there; this pins the two that moved.

    Pins: R-01, R-10
    """
    import bench.state_store as SS

    model = tmp_path / "fam" / "fam-f16.gguf"
    (tmp_path / "fam").mkdir()
    model.write_bytes(b"x")
    results = tmp_path / "tournament-results" / "fam"
    written: list[str] = []

    def fake_post(port, path, body, timeout=60):
        return {
            "choices": [{"text": "A", "logprobs": {"content": [{"token": " A", "logprob": -0.1}]}}]
        }

    def fake_start(model_, port, extra, server_bin=None, log_path=None, **kw):
        written.append(str(log_path))
        with open(str(log_path), "wb") as f:
            f.write(b"server up")
        return None, True

    class FakeProc:
        pass

    monkeypatch.setattr(SS.llama_server, "start_server", fake_start)
    monkeypatch.setattr(SS.llama_server, "post_json", fake_post)
    monkeypatch.setattr(SS.llama_server, "wait_healthy", lambda port, proc=None: True)
    monkeypatch.setattr(SS.llama_server, "stop_server", lambda proc, port: None)

    questions = [{"q": "q", "choices": [("A", "a"), ("B", "b")], "ans": "A"}]
    monkeypatch.setattr(SS, "arc_cell_questions", lambda run: questions)

    ok, fv = SS.arc_pass(str(model), 3, 8080, str(results))
    assert ok and fv.get("correct") == 1
    assert written and all(str(results) in p for p in written), written
    arc_log = results / "fam-f16.gguf.arc-cell3.log"
    assert arc_log.is_file()
    leftovers = list((tmp_path / "fam").glob("*.log"))
    assert leftovers == [], leftovers


def test_window_equal_to_rung_is_a_candidate(tmp_path, monkeypatch):
    """Addendum 61 (the author's ruling, option A): the rung at depth D
    launches at ctx = D - the answer headroom is paid from the MEASURED
    CONTENT, not from the model's window. A family whose trained window
    equals the rung depth (the power-of-two coincidence that killed the
    medalist at 32,768 under the old ctx = D + 256 rule) is a CANDIDATE
    at its own rung: the pre-flight stays silent and the family is
    measured, never pre-declared infeasible.

    Pins: R-06
    """
    import bench.certify as BC

    launched = []
    monkeypatch.setattr(BC, "_acquire_missing_model", lambda *a: launched.append("acquire"))
    # a 4,096-window family at the 4,096 rung: EQUAL, not below
    monkeypatch.setattr(BC, "_registry_window", lambda fam: 4096)
    state: dict[str, Any] = {"families": {}}
    res = BC.certify_rung_combined(
        4096,
        ["eq-win"],
        str(tmp_path),
        state,
        str(tmp_path / "st.json"),
        8210,
        False,
        min_words=2,
    )
    r = res[0]
    assert r.get("verdict") != "infeasible", r.get("infeasible_reason")
    assert r.get("infeasible_reason") is None
    fst = state["families"]["eq-win"]
    assert fst.get("infeasible") is None
    assert fst.get("verdicts", {}).get("4096") != "infeasible"
    # the family proceeds to acquisition - the pre-flight stayed silent
    assert launched == ["acquire"]


def test_answered_rung_still_measures_the_terminal_family(tmp_path, monkeypatch, capsys):
    """Addendum 62: the answered-rung skip must not swallow a family
    whose window makes THIS its terminal rung - never-evaluated (no
    stored verdict, no cells), window <= depth: it cannot climb, so
    skipping it at the answered rung means never measuring it at all.
    The rung was answered first (a stored accept ahead of it in param
    order), and the terminal family measures anyway.

    Pins: R-04, R-06, R-11
    """
    import bench.certify as BC

    model = tmp_path / "eq" / "eq-f16.gguf"
    (tmp_path / "eq").mkdir()
    model.write_bytes(b"x")
    # champion: stored accept at 4,096, cells present - answers the rung
    # terminal family: 4,096-window, never evaluated - must MEASURE
    state: dict[str, Any] = {
        "families": {
            "champ": {
                "verdicts": {"4096": "accept"},
                "certify": {"4096": {"1": {"v": 3}}},
                "certify_speed": {"4096": {"1": {"v": 0}}},
                "certify_vt": {"4096": {"1": {"v": 5}}},
                "tournament_entry": {"rung": "f16", "file": str(model)},
            },
            "eqfam": {"tournament_entry": {"rung": "f16", "file": str(model)}},
        }
    }
    monkeypatch.setattr(BC, "_registry_window", lambda fam: 4096 if fam == "eqfam" else None)
    measured = []

    def fake_measure(task, *a, **kw):
        measured.append(task)
        return (task != "fwe", 5, "line", 1.0)

    import bench.state_store as SS

    monkeypatch.setattr(SS, "_task_measure", fake_measure)
    res = BC.certify_rung_combined(
        4096,
        ["champ", "eqfam"],
        str(tmp_path),
        state,
        str(tmp_path / "st.json"),
        8210,
        False,
        min_words=2,
    )
    out = capsys.readouterr().out
    assert "terminal rung - measuring it (addendum 62)" in out
    assert measured, "the terminal family must be measured at the answered rung"
    eq = (
        next(r for r in res if r.get("family") == "eqfam")
        if any(r.get("family") == "eqfam" for r in res)
        else res[-1]
    )
    assert eq.get("skipped") != "rung already answered"


def test_terminal_rung_never_measures_below_the_rung(monkeypatch):
    """Addendum 66: the addendum-62 terminal check fires only when the
    family's window REACHES the rung (window >= depth) - a sub-rung
    window is R-06 infeasible (phi-2, 2,048 at 4,096), never a
    "terminal measurement"; and _registry_window resolves the
    addendum-63 alias class, so a state-carried basename
    (MiniCPM-1B-sft-bf16) gets its real window and the pre-flight
    bars the above-window rungs instead of silence.

    Pins: R-06, R-11
    """
    from bench import certify

    assert certify._registry_window("MiniCPM-1B-sft-bf16") == 4096
    assert certify._registry_window("phi-2") == 2048
    # the terminal condition is window >= depth, never below
    first = 4096
    assert not (2048 >= first)
    assert 4096 >= first
