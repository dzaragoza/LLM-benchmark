#!/usr/bin/env python3
"""full_benchmark.py -- the v8 orchestrator (sweet spot + exam).

One command, two phases:
  phase 1  the sweet walk - for the roster's first --models models,
           walk the quant ladder, measure tg/s, find the boundary
           rung: the last quant that can fill the training window
           within the time parameter (tg/s x 1024 > window).
  phase 2  the exam - each sweet spot takes the chain-follow +
           elevator exam (one shared context per level, PASS/FAIL,
           difficulty = hops); the final score is the highest
           difficulty achieved.

  families  the roster's first --models models (param-ascending) or
             the families given.
  verdicts   commit and push themselves (addendum 31); --no-git opts out.

Everything is IDEMPOTENT and RESUMABLE: the state file is rewritten after
every cell; rerun the same command to resume. The v5/v7 tasks are cut,
their code in git history (bench/v7.py remains importable).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import signal
import sys
import time
from functools import partial
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

DRY_RUN_ACTIVE = False


def stamp(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}")


def load_state(path: str) -> dict[str, Any]:
    return _state_store.load_state(path)


def save_state(path: str, state: dict[str, Any]) -> None:
    # --dry-run is READ-ONLY (addendum 79): never write the state file.
    if DRY_RUN_ACTIVE:
        return
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
    """Every requirements.txt package importable in THIS interpreter -
    the dry run included. The interpreter path prints first so the
    wrong-venv case is visible at a glance; a missing package is a
    hard stop BEFORE any work begins."""
    from importlib.metadata import PackageNotFoundError, version

    print(f"  python : {sys.executable}")
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
    every run starts from the freshest state. --no-git and dry runs
    are handled by the callers; a failed pull is a HARD STOP - running
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
    # the results tree wholesale: exam answers + logs, the historical
    # dumps and sidecars that predate the split
    paths += glob.glob("results/**/*", recursive=True)
    # tool failure logs from models/ (quantize/convert/imatrix) are
    # BENCHMARK DEBUG DATA: they explain why a rung could not be
    # created - uploaded, never left stranded on the machine
    paths += glob.glob("models/*/quantize-*.log")
    paths += glob.glob("models/*/convert-f16.log")
    paths += glob.glob("models/*/imatrix.log")
    # the historical output globs (pre-split locations, already
    # committed trees stay reachable; new artifacts land in results/)
    paths += (
        glob.glob("models/*/*.live-dump*.json")
        + glob.glob("models/*/*.sentinel*.json")
        + glob.glob("models/*/*.mem.json")
        + glob.glob("models/tournament-results/**/*", recursive=True)
        + glob.glob("models/*/ladder-results/*")
    )
    paths += (
        glob.glob("ladder-results/*")
        + glob.glob("ruler-results/*")
    )
    existing = [p for p in paths if os.path.exists(p)]
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


def sigint_shutdown(_signum, _frame, args=None):
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
    stopped = llama_server.kill_stale_server()
    stamp("llama-server stopped" if stopped else "no llama-server to stop")
    try:
        tee_output.uninstall()
        stamp("results logging stopped")
    except Exception as e:
        stamp(f"results logging stop failed (ignored): {e}")
    if (
        args is not None
        and not getattr(args, "no_git", True)
        and not getattr(args, "dry_run", True)
    ):
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
        description="the v8 benchmark: find each model's sweet spot "
        "(phase 1, the quant that fills the context in time) and grade "
        "the sweet spots with the exam (phase 2, chain-following "
        "difficulty under a context bell)"
    )
    ap.add_argument(
        "families",
        nargs="*",
        help="family names, limiting the run to these models "
        "(param-ascending from md/models.md); omitted = the roster's "
        "first --models (v8) or the sweet-spot holders (exam)",
    )
    ap.add_argument("--models-dir", default=MODELS_DIR_DEFAULT)
    ap.add_argument("--state-file", default=STATE_FILE_DEFAULT)
    ap.add_argument("--results-file", default=RESULTS_FILE_DEFAULT)
    ap.add_argument(
        "--task",
        default="v8",
        choices=["v8", "sweet", "exam"],
        help="the task; 'v8' (default) is the integrated run: sweet "
        "walk over the first --models models, then the exam over "
        "their sweet spots; 'sweet' and 'exam' run the phases standalone",
    )
    ap.add_argument(
        "--models",
        type=int,
        default=16,
        help="v8: the number of models to test - the roster's first N, "
        "param-ascending (default 16)",
    )
    ap.add_argument(
        "--sweet-repeat",
        type=int,
        default=3,
        help="sweet: llama-bench repetitions per rung (default 3)",
    )
    ap.add_argument(
        "--sweet-concurrency",
        type=int,
        default=1024,
        help="sweet: the concurrency factor - a rung is in-window while "
        "tg/s * this > the training window (default 1024)",
    )
    ap.add_argument(
        "--sweet-limit",
        type=int,
        default=4,
        help="sweet: cap the walked roster to the first N models of "
        "md/models.md (param-ascending; default 4 - the disk ruling). "
        "The table keeps every model; only the walk is capped",
    )
    ap.add_argument(
        "--sweet-retry-skipped",
        action="store_true",
        help="sweet: clear every stored skip (unavailable/bench-failed "
        "records) before the walk, so transient causes (disk-full, a "
        "truncated f16) get a fresh attempt; permanent shape "
        "incompatibilities will re-skip",
    )
    ap.add_argument(
        "--exam-seeds",
        type=int,
        default=1,
        help="exam: the repetition count - the seed set is 1..n (the "
        "benchmark runs n=1, so every instance is built from seed 1 "
        "and every model takes the SAME exam)",
    )
    ap.add_argument(
        "--exam-max-level",
        type=int,
        default=32,
        help="exam: the sweep's hard ceiling on difficulty (hops)",
    )
    ap.add_argument(
        "--clean",
        action="store_true",
        help="wipe the stored exam records UP FRONT, then measure - "
        "never leave mixed-era results in the table (addendum 129); "
        "the sweet measurements always stand",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="READ-ONLY pre-flight: the plan, the feasibility checks, "
        "nothing downloaded, converted, benched or written",
    )
    ap.add_argument(
        "--no-git",
        action="store_true",
        help="skip the git tail and the verdict commits",
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
            if not args.no_git:
                try:
                    git_tail(args)
                except Exception as e:
                    stamp(f"git tail after crash failed (ignored): {e}")
        finally:
            sys.stdout.flush()
        raise


def _run(args: argparse.Namespace) -> None:
    global DRY_RUN_ACTIVE
    DRY_RUN_ACTIVE = args.dry_run
    install_sigint_handler(args)
    check_requirements()
    git_pull_head()
    tee_output.install()
    if not args.dry_run:
        kill_stale_server()
        check_tooling(args)
    state = load_state(args.state_file)
    stamp_disk(state, args.state_file)
    if args.task == "v8":
        # the integrated run: the roster's first --models models, the
        # same time parameter driving both phases
        from bench.exam import run as exam_run
        from bench.sweet import find_bench, roster_from_models_md
        from bench.sweet import run as sweet_run

        if args.clean and state.get("exam"):
            state["exam"] = {}
            save_state(args.state_file, state)
            stamp("exam: all records wiped (--clean) - a full re-measure")
        roster = [name for name, _ in roster_from_models_md()]
        families = roster[: args.models]
        if len(families) < len(roster):
            stamp(
                f"v8: the roster's first {len(families)} models "
                f"(before {roster[len(families)]} - --models)"
            )
        sweet = sweet_run(
            args.models_dir,
            state,
            args.state_file,
            families,
            repeat=args.sweet_repeat,
            concurrency=args.sweet_concurrency,
            dry_run=args.dry_run,
            bench_bin=find_bench(),
        )
        state["sweet"] = sweet
        save_state(args.state_file, state)
        print()
        print("=" * 60)
        stamp("PHASE 1 COMPLETE - SWEET-SPOT SUMMARY")
        for fam, rec in (sweet or {}).items():
            spot = rec.get("sweet_spot")
            beyond = sum(1 for m in rec.get("rungs", {}).values() if m.get("in_window") is False)
            if spot and rec.get("over_window"):
                verdict = f"fastest rung {spot} (OVER the window - the fill-rate bell binds)"
            elif spot:
                verdict = f"boundary {spot}"
            else:
                verdict = "no measured rung"
            print(f"  {fam}: {verdict}, {beyond} beyond-the-window curve points")
        print()
        print("=" * 60)
        stamp("PHASE 2 - THE EXAM")
        results = exam_run(
            args.models_dir,
            state,
            args.state_file,
            state.get("ladder_port", 8210),
            families,
            n_seeds=args.exam_seeds,
            max_level=args.exam_max_level,
            dry_run=args.dry_run,
            time_factor=args.sweet_concurrency,
        )
        state["exam"] = results
        save_state(args.state_file, state)
        print()
        print("=" * 60)
        stamp("V8 EXAM SUMMARY (highest difficulty achieved per sweet spot)")
        for fam, rec in sorted(results.items(), key=lambda kv: -(kv[1].get("score") or -1)):
            spot = ((state.get("sweet") or {}).get(fam) or {}).get("sweet_spot")
            verdict = rec.get("error") or f"score {rec.get('score')}"
            print(f"  {fam} ({spot}): {verdict}")
        if not args.no_git:
            tee_output.uninstall()
            git_tail(args)
        stamp("v8 run complete")
        return
    if args.task == "exam":
        from bench.exam import run as exam_run

        if args.clean and state.get("exam"):
            state["exam"] = {}
            save_state(args.state_file, state)
            stamp("exam: all records wiped (--clean) - a full re-measure")
        results = exam_run(
            args.models_dir,
            state,
            args.state_file,
            state.get("ladder_port", 8210),
            args.families or None,
            n_seeds=args.exam_seeds,
            max_level=args.exam_max_level,
            dry_run=args.dry_run,
        )
        state["exam"] = results
        save_state(args.state_file, state)
        print()
        print("=" * 60)
        stamp("EXAM SUMMARY (highest difficulty achieved per sweet spot)")
        for fam, rec in sorted(results.items(), key=lambda kv: -(kv[1].get("score") or -1)):
            spot = ((state.get("sweet") or {}).get(fam) or {}).get("sweet_spot")
            verdict = rec.get("error") or f"score {rec.get('score')}"
            print(f"  {fam} ({spot}): {verdict}")
        if not args.no_git:
            tee_output.uninstall()
            git_tail(args)
        stamp("exam complete")
        return
    if args.task == "sweet":
        from bench.sweet import find_bench, roster_from_models_md
        from bench.sweet import run as sweet_run

        if args.sweet_retry_skipped:
            cleared = 0
            kept = 0
            for rec in state.get("sweet", {}).values():
                for rung, m in list(rec.get("rungs", {}).items()):
                    if m.get("tg") is None:
                        if m.get("permanent"):
                            kept += 1
                            continue
                        del rec["rungs"][rung]
                        cleared += 1
            if kept:
                stamp(
                    f"sweet: {kept} permanently-unquantizable records kept "
                    "(the architecture can never express this rung)"
                )
            if cleared:
                save_state(args.state_file, state)
                stamp(f"sweet: cleared {cleared} skipped records for a fresh attempt")
        families = [f.split("=")[0] for f in args.families]
        if not families:
            families = [n for n, _ in roster_from_models_md()]
            if args.sweet_limit and len(families) > args.sweet_limit:
                cut = families[args.sweet_limit]
                families = families[: args.sweet_limit]
                stamp(
                    f"sweet run capped at {len(families)} models (before {cut} - "
                    f"--sweet-limit; md/models.md still carries the full roster)"
                )
            else:
                stamp(
                    f"fresh sweet run: the md/models.md roster, "
                    f"param-ascending ({len(families)} models)"
                )
        sweet = sweet_run(
            args.models_dir,
            state,
            args.state_file,
            families,
            repeat=args.sweet_repeat,
            concurrency=args.sweet_concurrency,
            dry_run=args.dry_run,
            bench_bin=find_bench(),
        )
        state["sweet"] = sweet
        save_state(args.state_file, state)
        print()
        print("=" * 60)
        stamp("SWEET-SPOT SUMMARY")
        for fam, rec in (sweet or {}).items():
            spot = rec.get("sweet_spot")
            beyond = sum(1 for m in rec.get("rungs", {}).values() if m.get("in_window") is False)
            if spot and rec.get("over_window"):
                verdict = f"fastest rung {spot} (OVER the window - the fill-rate bell binds)"
            elif spot:
                verdict = f"boundary {spot}"
            else:
                verdict = "no measured rung"
            print(f"  {fam}: {verdict}, {beyond} beyond-the-window curve points")
        if not args.no_git:
            tee_output.uninstall()
            git_tail(args)
        stamp("run complete")
        return
    if not args.no_git:
        tee_output.uninstall()
        git_tail(args)
    stamp("run complete")


if __name__ == "__main__":
    main()
