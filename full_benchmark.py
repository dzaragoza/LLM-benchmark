#!/usr/bin/env python3
"""full_benchmark.py -- the randomizer's envelope (the v9.5 exam
walk is retired; the randomizer is the benchmark).

One command: python full_benchmark.py --task randomize. The pool is
v3: (model, model-quant) pairs - 64 models x 32 rungs = 2,048
pairs; every pick is 16 bits of real entropy, ONE chance per pair,
and the pick sweeps all 49 (k, v) cache-quant combinations in one
acquisition (a fresh 8-bit exam seed each, a 128s timer per
level), results only.

The envelope owns what the randomizer must never worry about: the
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


def preflight_selfcheck() -> None:
    """The behavioral self-check (the ruff --fix lesson): syntax and
    lint cannot see the failure class that costs hours - a shadowed
    name silently returning the wrong paper. Before any candidate is
    touched, the exam machinery, the pool, the state and the disk
    are verified against the live code. SILENT on success (the
    quiet-preflight ruling); ANY failure refuses to start the run
    with a printed reason. ~2s."""
    import bench.exam as E
    from bench.roster import LADDER, roster_from_models_md

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

    # --- the roster ladder the pool is drawn from ---
    assert LADDER[-1] == "F16" and len(LADDER) == 32

    # --- the roster: readable, granite first ---
    roster = roster_from_models_md()
    assert roster and roster[0][0] == "granite-4.0-h-350m", "roster order broken"

    # --- the pool: the full v2 candidate census (the dry-run check,
    # folded in): every family x every rung x every kv pair, the
    # drawn-set coherent with the state file ---
    import randomize as R

    pool = R.the_pool()
    n_kv = len(R.KV_LADDER)
    total = len(pool) * n_kv * n_kv
    assert len(pool) == 2048, f"the model pool must be 2048 pairs, got {len(pool)}"
    assert n_kv == 7, f"the KV ladder must be 7 quants, got {n_kv}"
    assert R.PICK_BITS == 16, "the pick must be 16 bits in v3"
    fams = {f for f, _ in pool}
    assert len(fams) == 64, f"the roster must carry 64 families, got {len(fams)}"
    assert len(LADDER) == 32 and LADDER[-1] == "F16", "the LADDER must be 32 rungs"
    if os.path.isfile(R.RANDOMIZER_STATE_FILE):
        with open(R.RANDOMIZER_STATE_FILE, encoding="utf-8") as fh:
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


def git_pull_head() -> None:
    """The forgotten pull, made structural (session 36, addendum 32):
    every run starts from the freshest state. A failed pull is a HARD
    STOP - running
    on a diverged tree measures the wrong thing with confidence."""
    if os.environ.get("BENCH_NO_GIT_PULL"):
        return
    if not git_ops.inside_work_tree():
        stamp("git pull skipped - not a git work tree")
        return
    rc, out, err = git_ops.pull_rebase()
    if rc != 0:
        stamp(f"git pull failed - FIX BEFORE RUNNING: {err.strip()[:200]}")
        raise SystemExit(1)
    out = out.strip()
    if out and "Already up to date" not in out:
        stamp(f"git pull: {out.splitlines()[0]}")
    else:
        stamp("git pull: already up to date")


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
    if os.path.isfile("md/randomizer.md"):
        paths += ["md/randomizer.md"]
    if os.path.isfile(RANDOMIZER_STATE := "state/randomizer-state.json"):
        paths += [RANDOMIZER_STATE]
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
    # truncate any oversized randomizer log BEFORE the rail commits:
    # the os._exit below skips run_candidate's finally, so a multi-hour
    # log would otherwise ride the artifact push past github's limits
    # (the 119MB granite-3.1 lesson)
    import glob as _glob

    for p in _glob.glob("results/randomizer/**/exam-server-*.log", recursive=True):
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
            git_pull_head()
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
        description="the protocol randomizer: every candidate of the "
        "2048 pool (roster x LADDER) gets ONE chance - a fresh 8-bit "
        "exam seed per candidate, a 128s timer per level, results only"
    )
    ap.add_argument("--models-dir", default=MODELS_DIR_DEFAULT)
    ap.add_argument("--state-file", default=STATE_FILE_DEFAULT)
    ap.add_argument("--results-file", default=RESULTS_FILE_DEFAULT)
    ap.add_argument(
        "--task",
        default="randomize",
        choices=["randomize"],
        help="the benchmark: the protocol randomizer (the v9.5 exam walk is retired)",
    )
    ap.add_argument(
        "--clean",
        action="store_true",
        help="delete the randomizer state UP FRONT - a fresh pool, "
        "every chance restored; era changes only",
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
    git_pull_head()
    tee_output.install()
    kill_stale_server()
    check_tooling(args)
    preflight_selfcheck()
    state = load_state(args.state_file)
    stamp_disk(state, args.state_file)
    if args.task == "randomize":
        # protocol randomizer: the epitome of simplicity - every
        # candidate of the 2048 pool (roster x LADDER = 11 bits of
        # real entropy per pick, ONE chance each), a fresh 8-bit
        # exam per candidate, a 128s timer PER LEVEL, results only.
        # Runs INSIDE full_benchmark's envelope: the crash rail, the
        # SIGINT saves, the artifact commits, the log truncation.
        import randomize as R

        if args.clean and os.path.isfile(R.RANDOMIZER_STATE_FILE):
            # simple: delete the state file - main() treats a
            # missing file as a fresh pool, every chance restored
            os.remove(R.RANDOMIZER_STATE_FILE)
            stamp("randomizer: state deleted (--clean) - a fresh pool")

        def push_progress(n: int) -> None:
            # the watchability ruling, randomizer-shaped: after every
            # pair the ledger + state + all 49 (k, v) answers commit
            # and push - the full model-quant sweep lands as one
            # unit, a multi-hour run is readable remotely as it goes
            tee_output.uninstall()
            try:
                git_tail(args)
            finally:
                tee_output.install()

        try:
            R.main(on_progress=push_progress)
        finally:
            # the git tail ALWAYS runs (the envelope's ruling): the
            # ledger, the state, and the answers are committed and
            # pushed whether the run finished, crashed, or was
            # SIGINTerrupted - the randomizer's own handler saves
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
