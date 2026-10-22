#!/usr/bin/env python3
"""full_benchmark.py -- the v9 benchmark: the exam is the only phase.

One command: every (model, quant) candidate in the roster takes the
exam - the full training window as the paper, the 1024-second time
bell per attempt, PASS/FAIL chain-following sweeps of escalating
difficulty. The roster is self-cleaning: a scored candidate strictly
below the running best loses its artifacts from disk (the data
always stays in git). No pre-measurement, no model-count limits.

Everything is IDEMPOTENT and RESUMABLE: the state file is rewritten
after every attempt; rerun the same command to resume."""

from __future__ import annotations

import argparse
import glob
import json
import os
import signal
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


def preflight_selfcheck() -> None:
    """The behavioral self-check (the ruff --fix lesson): syntax and
    lint cannot see the failure class that cost hours - the gc
    deleting a family mid-sweep, a shadowed name silently returning
    the wrong paper. Before any model is touched, the exact
    simulations run against the live code on temp dirs with fake
    state; ANY assertion failure refuses to start the run. ~2s."""
    import tempfile

    import bench.exam as E

    with tempfile.TemporaryDirectory() as tmp:
        # --- the paper: all three bell_window branches ---
        # (the roster lookup needs a REAL roster family; use the
        # first one, with a local config.json in the temp dir)
        from bench.roster import roster_from_models_md as _roster

        fam = _roster()[0][0]
        famdir = os.path.join(tmp, fam)
        os.makedirs(famdir, exist_ok=True)
        with open(os.path.join(famdir, "config.json"), "w", encoding="utf-8") as f:
            json.dump({"max_position_embeddings": 32768}, f)
        w = E.bell_window({"sweet": {}}, fam, tmp)
        assert w == 32768, f"bell_window config branch: {w}"
        w = E.bell_window({"sweet": {fam: {"window": 8192}}}, fam, tmp)
        assert w == 8192, f"bell_window cached branch: {w}"
        assert E.bell_window({"sweet": {}}, "no-such-family-xyz", tmp) is None

        # --- v9.1: candidates are (model, F16) only ---
        c = E.candidates({}, [fam])
        assert c == [(fam, 'F16')], f'candidates must be F16-only, got {c}'

        # --- v9.1 gc: model granularity, F16-keyed ---
        d = os.path.join(tmp, 'gcA')
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'gcA-F16.gguf'), 'w', encoding='utf-8').close()
        state = {'exam': {'gcA': {'F16': {'score': -1}}, 'top': {'F16': {'score': 4}}}}
        E._gc(tmp, state, exclude_fam=None)
        assert not os.path.isdir(d), 'gc kept a beaten model'
        assert state['exam']['gcA']['_eliminated'] is True
        d2 = os.path.join(tmp, 'gcB')
        os.makedirs(d2, exist_ok=True)
        open(os.path.join(d2, 'gcB-F16.gguf'), 'w', encoding='utf-8').close()
        state2 = {'exam': {'gcB': {'F16': {'score': 4}}, 'top': {'F16': {'score': 4}}}}
        E._gc(tmp, state2, exclude_fam=None)
        assert os.path.isdir(d2), 'gc deleted a survivor model'
        d3 = os.path.join(tmp, 'gcC')
        os.makedirs(d3, exist_ok=True)
        open(os.path.join(d3, 'gcC-F16.gguf'), 'w', encoding='utf-8').close()
        state3 = {'exam': {'gcC': {'F16': {}}, 'top': {'F16': {'score': 4}}}}
        E._gc(tmp, state3, exclude_fam=None)
        assert os.path.isdir(d3), 'gc deleted a pending model'
        open(os.path.join(d3, 'gcC-F16.gguf'), 'w', encoding='utf-8').close()
        state4 = {'exam': {'gcC': {'F16': {'score': -1}}, 'top': {'F16': {'score': 4}}}}
        E._gc(tmp, state4, exclude_fam='gcC')
        assert os.path.isdir(d3), 'gc deleted the running model'

        # --- the grader: the flexible subsequence ---
        inst = {"path": ["abc", "def", "ghi"]}
        assert E.score_exam("ANSWER: abc, def, ghi", inst, "stop")
        assert E.score_exam("ANSWER: x abc y def z ghi", inst, "stop")
        assert not E.score_exam("ANSWER: abc, ghi, def", inst, "stop")
        assert not E.score_exam("ANSWER: abc, def, ghi", inst, "length")
        assert not E.score_exam("ANSWER: abc, def, ghi", inst, "time_limit")
        assert not E.score_exam("I cannot solve this", inst, "stop")

        # --- v9.1: the candidate is F16, always ---
        from bench.roster import LADDER

        assert LADDER[-1] == "F16" and len(LADDER) == 32

        # --- the roster: readable, granite first ---
        from bench.roster import roster_from_models_md

        roster = roster_from_models_md()
        assert roster and roster[0][0] == "granite-4.0-h-350m", "roster order broken"

    print("  self-check: the gc, the paper, the grader, the ladder, the roster - OK")


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
    paths += glob.glob("ladder-results/*") + glob.glob("ruler-results/*")
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
        description="the v9 benchmark: every (model, quant) candidate "
        "takes the exam - the full training window as the paper, the "
        "1024s time bell, self-cleaning elimination"
    )
    ap.add_argument(
        "families",
        nargs="*",
        help="family names, limiting the exam to these models "
        "(param-ascending from md/models.md); omitted = the full roster",
    )
    ap.add_argument("--models-dir", default=MODELS_DIR_DEFAULT)
    ap.add_argument("--state-file", default=STATE_FILE_DEFAULT)
    ap.add_argument("--results-file", default=RESULTS_FILE_DEFAULT)
    ap.add_argument(
        "--task",
        default="exam",
        choices=["exam"],
        help="the benchmark: every (model, quant) candidate takes the "
        "exam - the full training window as the paper, the 1024s time "
        "bell, PASS/FAIL sweeps, self-cleaning elimination",
    )
    ap.add_argument(
        "--exam-seeds",
        type=int,
        default=1,
        help="the repetition count - the seed set is 1..n (the "
        "benchmark runs n=1, so every instance is built from seed 1 "
        "and every model takes the SAME exam)",
    )
    ap.add_argument(
        "--exam-max-level",
        type=int,
        default=32,
        help="the sweep's hard ceiling on difficulty (hops)",
    )
    ap.add_argument(
        "--eliminate",
        default=None,
        help="mark these models ELIMINATED in the ledger and delete "
        "their models/ artifacts (the collected data always stays in "
        "git) - comma-separated family names; mostly superseded by "
        "the run's self-cleaning gc",
    )
    ap.add_argument(
        "--clean",
        action="store_true",
        help="wipe the stored exam records UP FRONT, then measure - "
        "never leave mixed-era results; era changes only",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="READ-ONLY pre-flight: the plan, nothing downloaded, converted, examined or written",
    )
    ap.add_argument(
        "--no-git",
        action="store_true",
        help="skip the git tail and the artifact commits",
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
    except BaseException as exc:
        import traceback

        tb = traceback.format_exc()
        try:
            print(tb)
            from bench.exam import TimeBellHit

            if isinstance(exc, TimeBellHit):
                stamp(f"TIME BELL HIT - {exc} - the benchmark is STOPPED for review")
            else:
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


def write_v9_md(state: dict[str, Any], roster_pos: dict[str, int]) -> None:
    """md/v9.md - the tournament ledger, rewritten from state after
    every run: every candidate ever measured, its score, why it
    failed its highest exam, and whether it is eliminated (its
    artifacts deleted from the benchmark machine - the data always
    stays in git)."""
    from bench.exam import fail_reason

    exam = state.get("exam") or {}
    lines = [
        "# v9.md - the tournament ledger",
        "",
        "One row per (model, quant) candidate, param-ascending; regenerated",
        "from state after every run. Eliminated = the candidate's artifacts",
        "were deleted from the benchmark machine (the collected data",
        "always stays). The exam's failure reasons:",
        "`out of context` (the bell rang before an answer), `wrong chain`",
        "(an answer arrived, the chain was incorrect), `error` (tool",
        "failure), `no record` (never measured).",
        "",
        "| # | model | quant | score | ctx (bell) | failed at | why | eliminated? |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for fam, pos in sorted(roster_pos.items(), key=lambda kv: kv[1]):
        fam_exam = exam.get(fam) or {}
        if not fam_exam:
            continue
        rungs = sorted(fam_exam.items(), key=lambda kv: -(kv[1].get("score") or -1))
        for rung, rec in rungs:
            score = rec.get("score")
            failed_at = ""
            if score is not None:
                failed_at = f"level {score + 1}" if fail_reason(rec) not in ("no record",) else ""
            why = fail_reason(rec)
            ctx = rec.get("bell_ctx")
            lines.append(
                f"| {pos} | {fam} | {rung} | {score if score is not None else '-'} "
                f"| {ctx if ctx is not None else '-'} | {failed_at or '-'} "
                f"| {why if failed_at or why != 'no record' else '-'} "
                f"| {'yes' if fam_exam.get('_eliminated') else 'no'} |"
            )
    lines.append("")
    lines.append(
        f"_Eliminated models: {sum(1 for f in exam if (exam[f] or {}).get('_eliminated'))} "
        f"of {len(exam)} ever measured. The roster refill continues at "
        f"--models-from {max(roster_pos.values(), default=0) + 1}._"
    )
    with open(os.path.join("md", "v9.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    stamp("v9.md ledger rewritten")


def _exam_to_state(state: dict[str, Any], results: dict[tuple[str, str], Any]) -> None:
    """Store the exam results under state.exam with JSON-safe keys:
    exam.<family>.<rung> - a tuple key cannot survive json.dump (it
    would coerce to a string and break the resume path)."""
    tree = state.setdefault("exam", {})
    for (fam, rung), rec in results.items():
        tree.setdefault(fam, {})[rung] = rec


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
    if not args.dry_run:
        preflight_selfcheck()
    state = load_state(args.state_file)
    stamp_disk(state, args.state_file)
    if args.task in ("v8", "exam"):
        # v9: the exam is the only phase. No sweet walk, no in-window
        # rule, no model-count logic: every (model, quant) candidate
        # takes the exam under the full-window paper and the 1024s
        # time bell; the roster is self-cleaning (strictly-lower
        # scorers are deleted from disk as soon as scores exist).
        from bench.exam import run as exam_run
        from bench.roster import roster_from_models_md

        if args.clean and state.get("exam"):
            state["exam"] = {}
            save_state(args.state_file, state)
            stamp("exam: all records wiped (--clean) - a full re-measure under the v9 protocol")

        if args.eliminate:
            # the manual tournament cut (mostly superseded by the
            # self-clean; kept for the ledger bookkeeping)
            import shutil

            for fam in args.eliminate.split(","):
                fam = fam.strip()
                if not fam:
                    continue
                tree = state.setdefault("exam", {}).setdefault(fam, {})
                tree["_eliminated"] = True
                famdir = os.path.join(args.models_dir, fam)
                if os.path.isdir(famdir):
                    shutil.rmtree(famdir)
                    stamp(f"eliminated {fam}: artifacts deleted (data kept)")
                else:
                    stamp(f"eliminated {fam}: marked (no artifacts on disk)")
            save_state(args.state_file, state)
            write_v9_md(
                state,
                {name: i + 1 for i, name in enumerate([n for n, _ in roster_from_models_md()])},
            )
            if not args.no_git:
                tee_output.uninstall()
                git_tail(args)
            stamp("elimination complete")
            return

        def family_done(fam: str) -> None:
            """A push every time a model completes all its candidates
            (the author's watchability ruling): state + answers + the
            refreshed ledger are committed and pushed, so the run is
            readable model by model, hours apart instead of at the
            end."""
            _exam_to_state_keep(state)
            save_state(args.state_file, state)
            write_v9_md(
                state,
                {name: i + 1 for i, name in enumerate([n for n, _ in roster_from_models_md()])},
            )
            stamp(f"family complete: {fam} - committing artifacts")
            if args.no_git or args.dry_run:
                return
            tee_output.uninstall()
            try:
                git_tail(args)
            except Exception as e:
                stamp(f"family push failed (ignored): {e}")
            finally:
                tee_output.install()

        def _exam_to_state_keep(state: dict[str, Any]) -> None:
            pass  # the exam writes state directly; nothing to merge

        results = exam_run(
            args.models_dir,
            state,
            args.state_file,
            state.get("ladder_port", 8210),
            args.families or None,
            n_seeds=args.exam_seeds,
            max_level=args.exam_max_level,
            dry_run=args.dry_run,
            on_family_done=None if args.dry_run else family_done,
        )
        _exam_to_state(state, results)
        save_state(args.state_file, state)
        write_v9_md(
            state, {name: i + 1 for i, name in enumerate([n for n, _ in roster_from_models_md()])}
        )
        print()
        print("=" * 60)
        stamp("V9 EXAM SUMMARY (highest difficulty achieved per candidate)")
        for (fam, rung), rec in sorted(results.items(), key=lambda kv: -(kv[1].get("score") or -1)):
            verdict = rec.get("error") or f"score {rec.get('score')}"
            print(f"  {fam} {rung}: {verdict}")
        if not args.no_git:
            tee_output.uninstall()
            git_tail(args)
        stamp("v9 run complete")
        return
    if not args.no_git:
        tee_output.uninstall()
        git_tail(args)
    stamp("run complete")


if __name__ == "__main__":
    main()
