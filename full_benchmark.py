#!/usr/bin/env python3
"""full_benchmark.py -- the ei's envelope (the v9.5 exam
walk is retired; the ei is the benchmark).

One command: python full_benchmark.py --task trek. The grid is
v3: (model, model-quant) pairs - 64 models x 32 rungs = 2,048
pairs; every pick is 16 bits of real entropy, ONE chance per pair,
and the pick sweeps all 49 (k, v) cache-quant combinations in one
acquisition (a fresh 8-bit exam seed each, a 128s timer per
level), results only.

The envelope owns what the ei must never worry about: the
requirements check, the git pull/push rail, the crash commit, the
SIGINT clean shutdown, the artifact ledger, the log truncation.

Everything is IDEMPOTENT and RESUMABLE: the state file is rewritten
after every pick; rerun the same command to resume."""

from __future__ import annotations

import argparse
import glob
import json
import os
import signal
import subprocess
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bench.tee_output as tee_output
import infra.convert_quant as convert_quant
import infra.git_ops as git_ops
import infra.hf_download as hf_download
import infra.llama_server as llama_server
from bench import state_store as _state_store

kill_stale_server = llama_server.kill_stale_server

QUANTIZE_BIN = convert_quant.QUANTIZE_BIN
MODELS_DIR_DEFAULT = "./models"
STATE_FILE_DEFAULT = "./state/benchmark-state.json"
RESULTS_FILE_DEFAULT = "./benchmark-results.json"
SERVER_BIN = llama_server.find_server()

# =========================================================== state


def stamp(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}")


def load_state(path: str) -> dict[str, Any]:
    return _state_store.load_state(path)


def save_state(path: str, state: dict[str, Any]) -> None:
    with open(path, "w") as f:
        json.dump(state, f, indent=1)


def stamp_disk(state: dict[str, Any], path: str) -> None:
    """The RUN'S OWN disk reading (session 40, addendum 51): the run
    stamps its machine's free disk and hostname into the state file,
    so the live page always reports the benchmark machine's headroom
    no matter which machine regenerates the page (the addendum-50
    fix made the page name the host; this makes the page carry the
    run's number itself)."""
    import socket

    try:
        free = hf_download.free_disk_gib(os.path.dirname(os.path.abspath(path)) or ".")
    except Exception:
        return
    if free is not None:
        state["disk"] = {
            "free_gib": round(free, 1),
            "host": socket.gethostname(),
            "at": time.strftime("%Y-%m-%d %H:%M"),
        }


# =========================================================== preflight

REQ_PACKAGES = [
    "huggingface_hub",
    "transformers",
    "torch",
    "safetensors",
    "numpy",
    "gguf",
    "sentencepiece",
    "protobuf",
    "pandas",
    "pyarrow",
    "hf_transfer",
]


def check_requirements() -> None:
    """Every requirements.txt package importable in THIS interpreter.
    Silent on success; a missing package is a hard stop BEFORE any
    work begins."""
    from importlib.metadata import PackageNotFoundError, version

    missing = []
    for name in REQ_PACKAGES:
        try:
            version(name)
        except PackageNotFoundError:
            missing.append(name)
    if missing:
        sys.exit(
            "missing python packages in this interpreter: "
            + ", ".join(missing)
            + " - interpreter: "
            + sys.executable
            + " - activate the study venv and/or: python3 -m pip install -r requirements.txt"
        )


def preflight_gc() -> None:
    """THE PREFLIGHT GC (the author's ruling): run the garbage
    collector BEFORE asserting anything - a run needs 16 GiB of
    headroom on /home for the f16 downloads and the quantization
    scratch, and the stranded quants / evictable f16s from an
    abruptly-stopped previous run are the first recovery source.
    This is the SAME cleanup the runtime watchdog runs (the
    stranded-quant sweep first, then the least-likely f16 eviction),
    executed synchronously here until the headroom is met or the
    sources are exhausted. It never touches the state or the
    results - only the model files the runtime rules would delete
    anyway."""
    import trek_run as R

    free = R._free_gib()
    if free > R.GC_THRESHOLD_GIB:
        return  # the headroom already there
    print(f"[preflight] free {free:.1f} GiB <= {R.GC_THRESHOLD_GIB:g} GiB - running the gc first")
    # the same exclusions the watchdog uses: nothing active yet
    R._GC_POOL.clear()
    R._GC_POOL.extend(R.the_pool())
    guard = 0
    while R._free_gib() <= R.GC_THRESHOLD_GIB and guard < 1000:
        guard += 1
        # 1. the stranded-quant sweep (crash leftovers), newest kept
        stranded = R._stranded_quants("models", set())
        if stranded:
            for p in stranded:
                os.remove(p)
                print(f"[preflight] gc: removed stranded {os.path.basename(p)}")
            continue
        # 2. the least-likely f16 eviction (the imatrix stays behind)
        victim = R._least_likely_f16("models", set(), R._GC_DONE_SET, R._GC_POOL)
        if not victim:
            break  # the sources exhausted: the assert will fire with the reason
        os.remove(victim)
        print(f"[preflight] gc: evicted the f16 of {os.path.basename(os.path.dirname(victim))}")
    free = R._free_gib()
    print(f"[preflight] the gc done: {free:.1f} GiB free")


def preflight_selfcheck() -> None:
    """The behavioral self-check (the ruff --fix lesson): syntax and
    lint cannot see the failure class that costs hours - a shadowed
    name silently returning the wrong paper. Before any candidate is
    touched, THE GC RUNS (the author's ruling - the disk headroom is
    recovered from the previous run's leftovers first), then the
    exam machinery, the pool, the state and the disk are verified
    against the live code. SILENT on success (the quiet-preflight
    ruling); ANY failure refuses to start the run with a printed
    reason. ~2s."""
    import trek_run as R

    # --- THE PREFLIGHT GC (the author's ruling): the disk headroom is
    # --- recovered from the previous run's leftovers BEFORE asserting;
    # --- the run needs 16 GiB for the f16 downloads + quant scratch ---
    preflight_gc()
    free = R._free_gib()
    assert free > R.GC_THRESHOLD_GIB, (
        f"only {free:.1f} GiB free on /home - the run needs "
        f"{R.GC_THRESHOLD_GIB:g} GiB of headroom (the gc exhausted the "
        f"stranded quants and the evictable f16s; free some space by hand)"
    )
    print(f"[preflight] the disk headroom: {free:.1f} GiB free")

    import bench.exam as E
    import bench.trek as T
    from bench.roster import LADDER, dyadic_picks

    # --- the grader: the flexible subsequence ---
    inst = {"path": ["abc", "def", "ghi"]}
    assert E.score_exam("ANSWER: abc, def, ghi", inst, "stop")
    assert E.score_exam("ANSWER: x abc y def z ghi", inst, "stop")
    assert not E.score_exam("ANSWER: abc, ghi, def", inst, "stop")
    assert not E.score_exam("ANSWER: abc, def, ghi", inst, "length")
    # graded AT the bell - a complete answer still passes
    assert E.score_exam("ANSWER: abc, def, ghi", inst, "time_limit")
    assert not E.score_exam("ANSWER: abc, def, gh", inst, "time_limit")
    assert not E.score_exam("I cannot solve this", inst, "stop")

    # --- the exam builders: deterministic, level-shaped ---
    c0 = E.build_chain(1, 0)
    e0 = E.build_elevator(1, 0)
    assert c0["path"] and e0["path"], "the exam papers are empty"
    assert E.build_chain(1, 0) == c0, "the chain exam is not deterministic"
    assert len(E.build_chain(1, 3)["rows"]) == 4, "level d = d+1 pairs"
    assert len(E.build_elevator(1, 3)["rows"]) == 4, "level d = d+1 pairs"

    # --- the paper: the unknown-family branch ---
    assert E.bell_window({}, "no-such-family-xyz", "models") is None

    # --- THE WALK CANARY (the author's ruling: cheap): the seed-1
    # --- walk's first 20 picks on the canonical mock landscape -
    # --- regenerated and compared against the frozen sequence. Any
    # --- walk semantics change is a diff: the walk is the protocol's
    # --- determinism carrier, and its behavior is pinned here.
    canary_now = T.walk_canary_sequence()
    assert canary_now == T.WALK_CANARY, (
        f"the walk canary diverged - the walk semantics changed "
        f"(regenerate WALK_CANARY if the change is intended):\n"
        f"  was: {T.WALK_CANARY[:4]}...\n  now: {canary_now[:4]}..."
    )

    # --- the roster ladder the pool is drawn from (the safe ladder:
    # --- 15 classic K-quant rungs, F16 last - the imatrix rungs cut) ---
    assert LADDER[-1] == "F16" and len(LADDER) == 3, (
        "the small grid's ladder reshaped - update me when the truth changes"
    )

    # --- the roster: readable, granite first ---
    roster = dyadic_picks()
    assert roster and roster[0][0] == "Qwen2.5-0.5B-Instruct", (
        "the picks' param-ascending order broken"
    )

    # --- the pool: the full v2 candidate census (the dry-run check,
    # folded in): every family x every rung x every kv pair, the
    # drawn-set coherent with the state file ---
    import trek_run as R

    pool = R.the_pool()
    n_kv = len(R.KV_LADDER)
    total = len(pool) * n_kv * n_kv
    n_picks = len(dyadic_picks())
    assert len(pool) == n_picks * len(LADDER), (
        f"the pool must be {n_picks} x {len(LADDER)} = {n_picks * len(LADDER)} "
        f"pairs, got {len(pool)} (the grid reshaped - update me when the truth changes)"
    )
    assert n_kv == 3, f"the KV ladder must be 3 quants, got {n_kv}"
    assert R.PICK_BITS == 16, "the pick must be 16 bits in v3"
    fams = {f for f, _ in pool}
    assert len(fams) == len(dyadic_picks()), (
        f"the grid must carry {len(dyadic_picks())} models, got {len(fams)}"
    )
    assert len(LADDER) == 3 and LADDER[-1] == "F16", (
        "the LADDER must be 3 rungs (the small grid - update me when the truth changes)"
    )
    if os.path.isfile(R.TREK_STATE_FILE):
        with open(R.TREK_STATE_FILE, encoding="utf-8") as fh:
            st = json.load(fh)
        drawn = set(st.get("done", []))
        assert len(drawn) <= total, "the drawn-set exceeds the pool - corrupt state"
        rec_fams = {r.get("fam") for r in st.get("results", [])}
        assert rec_fams <= fams, "results name families outside the roster - corrupt state"

    # --- the disk: an f16 download needs headroom (the 8 GiB gate
    # plus working space); a nearly-full disk fails mid-run ---
    import infra.hf_download as hf_download

    free = hf_download.free_disk_gib(".")
    if free is not None and free < 16.0:
        sys.exit(
            f"only {free:.1f} GiB free - the run needs 16 GiB of "
            "headroom for f16 downloads and quantization scratch"
        )


def check_tooling(args: argparse.Namespace) -> None:
    """Verify the run's tooling (real runs only; addendum 79)."""
    for path, msg in [
        (
            QUANTIZE_BIN,
            f"llama-quantize not found at {QUANTIZE_BIN} - place the b11669 build in the repo root",
        ),
        (
            "./llama.cpp/convert_hf_to_gguf.py",
            "converter not found - the llama.cpp checkout must be in the repo root",
        ),
        (SERVER_BIN or "", "llama-server not found - place the b11669 build in the repo root"),
    ]:
        if not os.path.isfile(path):
            sys.exit(msg)


# =========================================================== git


def git_sync_check() -> None:
    """THE SYNC CHECK (the author's ruling): the run REFUSES to start
    unless the local HEAD matches the latest remote commit - the
    missed-pull incident (the machine ran pre-two-phase code with
    full confidence, hours of prospect-only sweeps) is the evidence.
    The pull itself is the OPERATOR's job now: the tool never pulls;
    it only verifies. A fetch (harmless - it updates the remote
    refs without touching the tree) precedes the comparison, so the
    check is against the ACTUAL remote, not a stale tracking ref."""
    if os.environ.get("BENCH_NO_GIT_SYNC"):
        return
    if not git_ops.inside_work_tree():
        stamp("git sync skipped - not a git work tree")
        return
    import subprocess

    r = subprocess.run(["git", "fetch", "--quiet"], capture_output=True)
    if r.returncode != 0:
        stamp("git fetch failed - cannot verify the sync; fix the remote access")
        raise SystemExit(1)
    local = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    remote = subprocess.run(
        ["git", "rev-parse", "@{u}"], capture_output=True, text=True
    )
    if remote.returncode != 0:
        stamp(f"git sync check: no upstream configured - aborting ({remote.stderr.strip()[:100]})")
        raise SystemExit(1)
    remote = remote.stdout.strip()
    print(f"[preflight] the local commit: {local[:8]}")
    if local != remote:
        stamp(
            f"git OUT OF SYNC - the local HEAD {local[:8]} != the remote "
            f"{remote[:8]}; run: git pull --rebase; and restart "
            f"(the tool never pulls - the sync is the operator's)"
        )
        raise SystemExit(1)


def git_tail(args: argparse.Namespace) -> None:
    """Commit and push every artifact the study needs (addendum 78
    item 5): state, results, dumps, sidecars, logs - force-added past
    the .gitignore.

    The rule (the author's v8 ruling): models/ holds ONLY re-
    downloadable or re-creatable data (quants, safetensors sources,
    the imatrix); every benchmark OUTPUT - exam answers, server and
    quantize logs, dumps, sidecars - lives in the results/ tree and
    is uploaded wholesale, so all debug data is always available
    remotely."""
    stamp("committing artifacts to git (state, results, dumps, mem sidecars)")
    paths = [args.state_file, args.results_file, "results.txt"]
    # the ledger is a first-class artifact: every commit carries
    # the latest regeneration (the progress pushes depend on it)
    if os.path.isfile("md/trek.md"):
        paths += ["md/trek.md"]
    if os.path.isfile(EI_STATE := "state/trek-state.json"):
        paths += [EI_STATE]
    # the results tree wholesale: exam answers + logs, the historical
    # dumps and sidecars that predate the split
    paths += glob.glob("results/**/*", recursive=True)
    # tool failure logs from models/ (quantize/convert/imatrix) are
    # BENCHMARK DEBUG DATA: they explain why a rung could not be
    # created - uploaded, never left stranded on the machine.
    # The gc's eliminations DELETE these logs from models/ - the
    # deletions must be staged too, else they stay unstaged and
    # block the next run's pull --rebase (the v9.1 lesson: git add
    # on an existing-file list never stages a deletion)
    paths += glob.glob("models/*/quantize-*.log")
    paths += glob.glob("models/*/convert-f16.log")
    paths += glob.glob("models/*/imatrix.log")
    deleted = [
        p
        for p in subprocess.run(
            ["git", "ls-files", "-d", "--", "models/"],
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        if p
    ]
    if deleted:
        rc, err = git_ops.add(deleted)
        if rc != 0:
            stamp(f"staging log deletions failed: {err.strip()[:120]}")
    # the historical output globs (pre-split locations, already
    # committed trees stay reachable; new artifacts land in results/)
    paths += (
        glob.glob("models/*/*.live-dump*.json")
        + glob.glob("models/*/*.sentinel*.json")
        + glob.glob("models/*/*.mem.json")
        + glob.glob("models/tournament-results/**/*", recursive=True)
        + glob.glob("models/*/ladder-results/*")
    )
    existing = []
    for p in paths:
        if not os.path.exists(p):
            continue
        try:
            if os.path.getsize(p) > 48 * 1024 * 1024:
                size_mib = os.path.getsize(p) / 2**20
                stamp(f"skipping {p}: {size_mib:.0f} MiB exceeds github's 50 MiB limit")
                continue
        except OSError:
            continue
        existing.append(p)
    if not existing:
        stamp("nothing to commit - no artifacts found")
        return
    if git_ops.in_rebase():
        stamp(
            "NOT committing: a rebase is in progress (unresolved "
            "conflicts) - resolve it by hand (git status, fix, git add, "
            "git rebase --continue) and restart; committing onto the "
            "detached HEAD makes recovery harder"
        )
        return
    rc, err = git_ops.add(existing)
    if rc != 0:
        stamp(f"git add failed: {err.strip()}")
        return
    if not git_ops.staged_changes_exist():
        stamp("nothing new to commit")
        return
    msg = (
        f"benchmark artifacts {time.strftime('%Y-%m-%d %H:%M')} "
        "(addendum 78 auto-commit): state, results, per-turn dumps, "
        "mem sidecars, ladder dumps"
    )
    rc, out = git_ops.commit(msg)
    if rc != 0:
        stamp(f"commit failed: {out.strip()}")
        return
    stamp(f"committed: {out.strip().splitlines()[0]}")
    rc, out, err = git_ops.pull_rebase()
    hint = "run: git pull --rebase --autostash; and git push"
    if rc != 0:
        stamp(f"pull before push failed: {err.strip()} - {hint}")
    rc, err = git_ops.push()
    if rc != 0:
        stamp(f"push failed: {err.strip()} - {hint}")
    else:
        stamp("pushed")


# =========================================================== sigint


_SHUTTING_DOWN = False


def sigint_shutdown(_signum: int, _frame: Any, args: argparse.Namespace | None = None) -> None:
    """Session 38, addendum 8: Ctrl-C stops cleanly - stop llama-server,
    stop results logging, git commit and pull. os._exit, not sys.exit:
    a SystemExit inside the handler unwinds through huggingface_hub's
    ThreadPoolExecutor shutdown(wait=True), which waits out every
    in-flight download - the Ctrl-C "did not stop".

    Re-entry hard-exits: the first press runs the clean shutdown (the
    git tail can take seconds), a SECOND press means the user wants
    out NOW - falling into the handler a second time mid-commit (two
    racing git processes, a torn tee) is the failure this guard
    closes. SIGTERM rides the same path: a bare `kill` must leave the
    machine as clean as Ctrl-C does, not strand a llama-server."""
    global _SHUTTING_DOWN
    if _SHUTTING_DOWN:
        stamp("shutdown already in progress - exiting immediately")
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(130)
    _SHUTTING_DOWN = True
    stamp("SIGINT - shutting down cleanly (addendum 8)")
    # truncate any oversized ei log BEFORE the rail commits:
    # the os._exit below skips run_candidate's finally, so a multi-hour
    # log would otherwise ride the artifact push past github's limits
    # (the 119MB granite-3.1 lesson)
    import glob as _glob

    for p in _glob.glob("results/trek/**/exam-server-*.log", recursive=True):
        try:
            if os.path.getsize(p) > 20 * 2**20:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    lines = fh.readlines()
                with open(p, "w", encoding="utf-8") as fh:
                    fh.writelines(lines[:100])
                    fh.write(f"... [SIGINT truncation: {len(lines)} lines]\n")
                    fh.writelines(lines[-300:])
                stamp(f"truncated oversized log {p} before commit")
        except OSError:
            pass
    stopped = llama_server.kill_stale_server()
    stamp("llama-server stopped" if stopped else "no llama-server to stop")
    try:
        tee_output.uninstall()
        stamp("results logging stopped")
    except Exception as e:
        stamp(f"results logging stop failed (ignored): {e}")
    if args is not None:
        try:
            git_tail(args)
        except Exception as e:
            stamp(f"git tail failed (ignored): {e}")
    stamp("shutdown complete - goodbye")
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(130)


def install_sigint_handler(args: argparse.Namespace) -> None:
    handler = lambda s, f: sigint_shutdown(s, f, args)  # noqa: E731
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


# =========================================================== main


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="the protocol ei: every candidate of the "
        "2048 pool (roster x LADDER) gets ONE chance - a fresh 8-bit "
        "exam seed per candidate, a 128s timer per level, results only"
    )
    ap.add_argument("--models-dir", default=MODELS_DIR_DEFAULT)
    ap.add_argument("--state-file", default=STATE_FILE_DEFAULT)
    ap.add_argument("--results-file", default=RESULTS_FILE_DEFAULT)
    ap.add_argument(
        "--task",
        default="trek",
        choices=["trek"],
        help="the benchmark: the protocol ei (the v9.5 exam walk is retired)",
    )
    ap.add_argument(
        "--clean",
        action="store_true",
        help="delete the trek state UP FRONT - a fresh pool, "
        "every chance restored; era changes only",
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=1,
        help="the walker seed: ONE seed for the whole run, all the "
        "walkers (the v2 ruling). The same seed reproduces the same "
        "walk exactly; different seeds explore the same landscape "
        "by different paths (the exam histories are shared - the "
        "exams are candidate-deterministic)",
    )
    return ap


def main() -> None:
    """The crash-safe entry: the git tail ALWAYS runs - on a clean
    finish, on any exception (the traceback is stamped into
    results.txt and committed as a CRASH artifact), and on SIGINT
    (the existing handler). A crashed run must still upload its
    state and results - the author's session-43 ruling: the git
    rail runs always, and the crash is REPORTED, not dropped on
    the console of a machine you are not sitting at."""
    ap = build_parser()
    args = ap.parse_args()
    try:
        _run(args)
    except SystemExit:
        raise
    except BaseException:
        import traceback

        tb = traceback.format_exc()
        try:
            print(tb)
            stamp("CRASH DETECTED - committing artifacts before exit")
            try:
                llama_server.kill_stale_server()
            except Exception as e:
                stamp(f"stale-server kill failed (ignored): {e}")
            try:
                tee_output.uninstall()
            except Exception as e:
                stamp(f"results logging stop failed (ignored): {e}")
            with open("results.txt", "a", encoding="utf-8") as f:
                f.write(f"\n===== CRASH {time.strftime('%Y-%m-%dT%H:%M:%S')} =====\n{tb}\n")
            try:
                git_tail(args)
            except Exception as e:
                stamp(f"git tail after crash failed (ignored): {e}")
        finally:
            sys.stdout.flush()
        raise


def _run(args: argparse.Namespace) -> None:
    install_sigint_handler(args)
    check_requirements()
    git_sync_check()
    tee_output.install()
    kill_stale_server()
    check_tooling(args)
    preflight_selfcheck()
    state = load_state(args.state_file)
    stamp_disk(state, args.state_file)
    if args.task == "trek":
        # protocol ei: the epitome of simplicity - every
        # candidate of the 2048 pool (roster x LADDER = 11 bits of
        # real entropy per pick, ONE chance each), a fresh 8-bit
        # exam per candidate, a 128s timer PER LEVEL, results only.
        # Runs INSIDE full_benchmark's envelope: the crash rail, the
        # SIGINT saves, the artifact commits, the log truncation.
        import trek_run as R

        if args.clean and os.path.isfile(R.TREK_STATE_FILE):
            # simple: delete the state file - main() treats a
            # missing file as a fresh pool, every chance restored
            os.remove(R.TREK_STATE_FILE)
            stamp("ei: state deleted (--clean) - a fresh pool")

        def push_progress(n: int) -> None:
            # the watchability ruling, ei-shaped: after every
            # pair the ledger + state + all 49 (k, v) answers commit
            # and push - the full model-quant sweep lands as one
            # unit, a multi-hour run is readable remotely as it goes
            tee_output.uninstall()
            try:
                git_tail(args)
            finally:
                tee_output.install()

        try:
            R.main(on_progress=push_progress, walker_seed=args.seed)
        finally:
            # the git tail ALWAYS runs (the envelope's ruling): the
            # ledger, the state, and the answers are committed and
            # pushed whether the run finished, crashed, or was
            # SIGINTerrupted - the ei's own handler saves
            # its state and defers to this tail
            tee_output.uninstall()
            try:
                git_tail(args)
            except Exception as e:
                stamp(f"git tail failed (ignored): {e}")
            finally:
                tee_output.install()
        return

    tee_output.uninstall()
    git_tail(args)
    stamp("run complete")


if __name__ == "__main__":
    main()
