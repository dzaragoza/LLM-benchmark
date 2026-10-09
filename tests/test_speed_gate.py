"""speed_gate.py dump-reuse rules: a dump measured at one ctx must never
satisfy reuse at a different ctx (the addendum-135 bug class: the reuse
check compared timestamps only, so a ctx-4096 dump was re-graded as a
--ctx 32768 cell in 88 ms with no server launch). Server-dependent
paths are avoided via the bench() reuse branch, the repo's established
monkeypatch style."""

import json
import os
import time


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


def test_git_pull_head(monkeypatch):
    """Addendum 32: the forgotten pull, made structural - git_pull_head
    runs before the state loads; a failed pull is a hard stop."""
    import full_benchmark as fb
    import infra.git_ops as git_ops

    calls = []

    def fake_inside():
        calls.append("inside")
        return True

    def fake_pull(autostash=True):
        calls.append(("pull", autostash))
        return (1, "", "diverged")

    monkeypatch.setattr(git_ops, "inside_work_tree", fake_inside)
    monkeypatch.setattr(git_ops, "pull_rebase", fake_pull)
    try:
        fb.git_pull_head()
        raise AssertionError("failed pull did not stop the run")
    except SystemExit:
        pass
    assert calls == ["inside", ("pull", True)]

    def fake_pull_ok(autostash=True):
        return (0, "Already up to date", "")

    monkeypatch.setattr(git_ops, "pull_rebase", fake_pull_ok)
    fb.git_pull_head()  # pull succeeds -> no exit


def test_git_pull_before_tee():
    """Addendum 34: the pull runs BEFORE tee_output.install appends to
    results.txt - the tool must not dirty its own tree then refuse to
    pull (the author's dry-run finding), and the pull autostashes."""
    import inspect

    import full_benchmark as fb

    # session 43: main() is the crash-safe wrapper; the run body lives
    # in _run(args) - the pull-before-tee ordering is pinned there
    body = inspect.getsource(fb._run)
    assert body.index("git_pull_head()") < body.index("tee_output.install()")
    src = inspect.getsource(fb.git_pull_head)
    # session 43, R-20: the pull runs WITH hooks - the no_verify
    # bypass is removed from pull_rebase and never used here
    assert "pull_rebase()" in src
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


def test_param_ascending_selection():
    """Addendum 28 regression: with no specs and no state families the
    roster comes from the registry, param-ascending; state-carried
    specs are re-sorted param-ascending too, unregistered last.

    Pins: R-07
    """
    import full_benchmark as fb

    ordered = fb.param_ascending_specs(
        [
            "meta-llama/Llama-3.1-8B-Instruct",
            "Qwen/Qwen3.5-0.8B",
            "microsoft/phi-1",
            "not/a-registered-model",
            "openbmb/MiniCPM4-0.5B",
        ]
    )
    assert ordered == [
        "openbmb/MiniCPM4-0.5B",
        "Qwen/Qwen3.5-0.8B",
        "microsoft/phi-1",
        "meta-llama/Llama-3.1-8B-Instruct",
        "not/a-registered-model",
    ]
    from etc import registry_data

    roster = registry_data.params_sorted_roster()
    assert len(roster) == len(registry_data.ROSTER)
    # addendum 29: every count is RETRIEVED FROM HF and recorded with
    # its source - never guessed, never missing
    store = registry_data.json.loads(registry_data.STORE.read_text())
    assert all(registry_data.params_b(n) is not None for n in roster)
    assert all(store[n].get("params_source") for n in roster)
    sizes = [registry_data.params_b(n) or 0.0 for n in roster]
    assert sizes == sorted(sizes)
    # the orchestrator order is the roster order - the smallest models
    # first (the granite 350ms and MiniCPM4-0.5B at the head)
    assert [registry_data.ROSTER[n] for n in roster][:3] == [
        "ibm-granite/granite-4.0-h-350m",
        "ibm-granite/granite-4.0-350m",
        "openbmb/MiniCPM4-0.5B",
    ]


def test_st_source_complete_guard(tmp_path):
    """Addendum 27 regression: a safetensors-source counts as present
    only when every shard named in its index exists - the partial
    download that killed the full-capacity run at phase 2."""
    import infra.hf_download as hf

    d = tmp_path / "st"
    d.mkdir()
    assert not hf.st_source_complete(str(d))
    # one shard on disk, no index: complete (unsharded repo)
    (d / "model.safetensors").write_bytes(b"x")
    assert hf.st_source_complete(str(d))
    # sharded repo with a two-shard index and one shard missing
    (d / "model.safetensors").unlink()
    (d / "model-00001-of-00002.safetensors").write_bytes(b"x")
    (d / "model.safetensors.index.json").write_text(
        json.dumps(
            {
                "weight_map": {
                    "a": "model-00001-of-00002.safetensors",
                    "b": "model-00002-of-00002.safetensors",
                }
            }
        )
    )
    assert not hf.st_source_complete(str(d))
    (d / "model-00002-of-00002.safetensors").write_bytes(b"x")
    assert hf.st_source_complete(str(d))
    # a corrupt index is incomplete, never silently trusted
    (d / "model.safetensors.index.json").write_text("{not json")
    assert not hf.st_source_complete(str(d))


def test_f16_is_a_rung(tmp_path):
    """Addendum 30 regression: f16 is a first-class rung - a shipped f16
    GGUF resolves as the rung file (never skipped as 'the quantize
    source'), the estimate is the full 16 bits, and create() returns
    the f16 itself with no quantize step."""
    import infra.convert_quant as cq
    import infra.hf_download as hf

    files = ["model-Q8_0.gguf", "model-f16.gguf", "model-bf16.gguf"]
    assert hf.find_rung_file(files, "f16") == "model-f16.gguf"
    assert hf.find_rung_file(files, "Q8_0") == "model-Q8_0.gguf"
    assert hf.RUNG_BITS["f16"] == 16.0
    # estimate: a shipped f16 file sizes exactly
    est = hf.estimate_rung_gib("f16", ["model-f16.gguf"], [], {"model-f16.gguf": 2 * 1024**3})
    assert est is not None and abs(est - 2.0) < 1e-9
    # create(): the f16 rung returns the existing f16, no quantize call
    famdir = tmp_path / "fam"
    famdir.mkdir()
    f16 = famdir / "fam-f16.gguf"
    f16.write_bytes(b"x")
    assert cq.create("fam", str(famdir), "f16") == str(f16)


def test_state_names_resolve_to_repos_before_the_hub():
    """Addendum 63: a state-carried family name is not a hub repo -
    'MiniCPM-1B-sft-bf16' 404s and crashed the run. Every name-only
    spec resolves to its roster repo before the acquire ever touches
    the hub (the addendum-62 alias class, applied to specs).

    Pins: R-07, R-12
    """
    import full_benchmark as fb

    assert fb._resolve_spec_repo("MiniCPM-1B-sft-bf16") == "openbmb/MiniCPM-1B-sft-bf16"
    assert fb._resolve_spec_repo("MiniCPM-2B-sft-bf16") == "openbmb/MiniCPM-2B-sft-bf16"
    assert fb._resolve_spec_repo("RWKV7-World-2.9B") == "RWKV/RWKV7-Goose-World3-2.9B-HF"
    # repos pass through unchanged; unknown names stay None (no guess)
    assert fb._resolve_spec_repo("openbmb/MiniCPM5-2B") == "openbmb/MiniCPM5-2B"
    assert fb._resolve_spec_repo("not-a-real-family") is None

