#!/usr/bin/env python3
"""full_benchmark.py -- the v9 benchmark: the exam is the only phase.

One command: every (model, quant) candidate in the roster takes the
exam - the full training window as the paper, the 32-second time
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
        w = E.bell_window({}, fam, tmp)
        assert w == 32768, f"bell_window config branch: {w}"
        assert E.bell_window({}, "no-such-family-xyz", tmp) is None

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

        # --- v9.4: the exhaustive quant walk helpers ---
        groups = E.rung_groups()
        assert groups[0] == ('F16', ('F16',)), 'the walk starts at F16, alone'
        assert groups[1][0] == 'Q8' and groups[1][1] == ('Q8_0',)
        assert groups[2][0] == 'Q6' and groups[2][1] == ('Q6_K',)
        assert [g[0] for g in groups] == ['F16', 'Q8', 'Q6', 'Q5', 'Q4', 'Q3', 'Q2', 'Q1']
        assert 'IQ2_M' in groups[6][1] and 'TQ2_0' in groups[6][1], 'IQ/TQ variants walk under their number'
        # rung_verdict: pass / fail / time / unmeasured
        vp = {'score': 3, 'levels': {'3': {'pass': True}}}
        assert E.rung_verdict(vp) == 'pass'
        vf = {'score': 1, 'levels': {'2': {'pass': False, 'attempts': [
            {'finish_reason': 'stop', 'ok': False}]}}}
        assert E.rung_verdict(vf) == 'fail'
        vt = {'score': 1, 'levels': {'2': {'pass': False, 'attempts': [
            {'finish_reason': 'time_limit'}]}}}
        assert E.rung_verdict(vt) == 'time'
        assert E.rung_verdict({'score': None}) is None
        # model_verdict: the walk's terminal states
        assert E.model_verdict({'F16': vp}) == 'pass'
        assert E.model_verdict({'F16': vf}) == 'fail'
        assert E.model_verdict({'F16': vt, 'Q8_0': {'unbuildable': True}}) is None, 'quants remain - pending'
        assert E.model_verdict({'F16': vt, '_out_of_time': True}) == 'time'
        # only bells everywhere = out of time (a fail reason)
        allbell = {r: dict(vt) for r, _num in
                   [(rg, 0) for g in groups for rg in g[1]]}
        assert E.model_verdict(allbell) == 'time', 'all-bell exhaustion is out of time'
        # a mixed group (fail + bell) moves on; exhausted = _out_of_time wins
        mixed = {'F16': vt, 'Q8_0': vf, '_out_of_time': True}
        assert E.model_verdict(mixed) == 'time'
        # best_rung: the highest-scoring rung, earlier rung on ties.
        # Records must carry LEVELS (as the walk writes them): a
        # score with no failing level reads as a clean sweep (pass)
        # and ends the walk at its own level - the score-only fixture
        # of the pre-correction era is not a shape the walk produces.
        mk_t = lambda s: {'score': s, 'levels': {
            '0': {'pass': True}, '1': {'pass': False,
            'attempts': [{'finish_reason': 'time_limit'}]}}}
        bx = {'F16': mk_t(3), 'Q8_0': mk_t(5)}
        assert E.best_rung(bx)[0] == 'Q8_0' and E.best_rung(bx)[1]['score'] == 5
        bx2 = {'F16': mk_t(4), 'Q8_0': mk_t(4)}
        assert E.best_rung(bx2)[0] == 'F16', 'ties go to the earlier rung'
        assert E.best_rung({}) is None
        # the author's worked example: f16 passes 0..3 bells at 4; q8
        # same; q6 fails at 4 - the walk ends there (q5.. never run),
        # the verdict is fail, and the HIGH SCORE is f16's 3
        vt = {'score': 3, 'levels': {
            **{str(i): {'pass': True} for i in range(4)},
            '4': {'pass': False, 'attempts': [{'finish_reason': 'time_limit'}]}}}
        vfl = {'score': 3, 'levels': {
            **{str(i): {'pass': True} for i in range(4)},
            '4': {'pass': False, 'attempts': [{'finish_reason': 'stop', 'ok': False}]}}}
        ex = {'F16': vt, 'Q8_0': dict(vt), 'Q6_K': vfl}
        assert E.model_verdict(ex) == 'fail', 'a wrong answer ends the walk'
        assert E.best_rung(ex)[0] == 'F16' and E.best_rung(ex)[1]['score'] == 3
        assert E.hit_time_bell(vt), 'the bell record reads as time'
        assert not E.hit_time_bell(vfl), 'the wrong-chain record reads as fail'

        # --- v9.4 gc: terminal verdicts collect, pending walks never ---
        # fixtures carry LEVELS (the walk's real record shape): a
        # score-only record reads as a clean sweep (pass) under the
        # level-granular verdict and the gc would read it differently
        mkbell = lambda s: {'score': s, 'levels': {
            '0': {'pass': True}, '1': {'pass': False,
            'attempts': [{'finish_reason': 'time_limit'}]}}}
        mkwrong = lambda s: {'score': s, 'levels': {
            '0': {'pass': True}, '1': {'pass': False,
            'attempts': [{'finish_reason': 'stop', 'ok': False}]}}}
        d5 = os.path.join(tmp, 'gcR')
        os.makedirs(d5, exist_ok=True)
        open(os.path.join(d5, 'gcR-F16.gguf'), 'w', encoding='utf-8').close()
        # f16 belled; q8_0 PASSED clean to 4 - the walk ended at q8_0,
        # the model SURVIVES (4 == the global best)
        state5 = {'exam': {'gcR': {'F16': mkbell(-1), 'Q8_0': {
            'score': 4, 'levels': {str(i): {'pass': True} for i in range(5)}}},
        'top': {'F16': {'score': 4}}}}
        E._gc(tmp, state5, exclude_fam=None)
        assert os.path.isdir(d5), 'gc deleted a model its Q8_0 recovery SAVED'
        assert not state5['exam']['gcR'].get('_eliminated')
        d6 = os.path.join(tmp, 'gcS')
        os.makedirs(d6, exist_ok=True)
        open(os.path.join(d6, 'gcS-F16.gguf'), 'w', encoding='utf-8').close()
        # f16 answered wrong at level 0 - the walk ended there, fail, collected
        state6 = {'exam': {'gcS': {'F16': {'score': -1, 'levels': {
            '0': {'pass': False, 'attempts': [
                {'finish_reason': 'stop', 'ok': False},
                {'finish_reason': 'stop', 'ok': False}]}}}},
        'top': {'F16': {'score': 4}}}}
        E._gc(tmp, state6, exclude_fam=None)
        assert not os.path.isdir(d6), 'gc kept a model every rung of failed'
        # v9.4: a PENDING walk (bells, quants untried) is never touched
        d7 = os.path.join(tmp, 'gcT')
        os.makedirs(d7, exist_ok=True)
        open(os.path.join(d7, 'gcT-F16.gguf'), 'w', encoding='utf-8').close()
        state7 = {'exam': {'gcT': {'F16': mkbell(1)},
        'top': {'F16': {'score': 4}}}}
        E._gc(tmp, state7, exclude_fam=None)
        assert os.path.isdir(d7), 'gc deleted a PENDING (mid-walk) model'
        assert not state7['exam']['gcT'].get('_eliminated')
        # v9.4: quants EXHAUSTED at the bell = out of time = an exam
        # fail - the gc collects it like any fail
        state7['exam']['gcT']['_out_of_time'] = True
        E._gc(tmp, state7, exclude_fam=None)
        assert not os.path.isdir(d7), 'gc kept an out-of-time model (an exam fail)'

        # --- the grader: the flexible subsequence ---
        inst = {"path": ["abc", "def", "ghi"]}
        assert E.score_exam("ANSWER: abc, def, ghi", inst, "stop")
        assert E.score_exam("ANSWER: x abc y def z ghi", inst, "stop")
        assert not E.score_exam("ANSWER: abc, ghi, def", inst, "stop")
        assert not E.score_exam("ANSWER: abc, def, ghi", inst, "length")
        # v9.2: graded AT the bell - a complete answer still passes
        assert E.score_exam("ANSWER: abc, def, ghi", inst, "time_limit")
        assert not E.score_exam("ANSWER: abc, def, gh", inst, "time_limit")
        assert not E.score_exam("I cannot solve this", inst, "stop")

        # --- v9.4: the roster ladder the walk draws its variations from ---
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
    # the ledger is a first-class artifact: every commit carries the
    # latest regeneration (the per-model pushes depend on it)
    paths += ["md/v9.4.md"]
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
    # truncate any oversized exam log BEFORE the rail commits: the
    # os._exit below skips run_family's finally, so a multi-hour
    # -lv 5 log would otherwise ride the artifact push past github's
    # limits (the 119MB granite-3.1 lesson)
    import glob as _glob

    for p in _glob.glob("results/exam/**/exam-server.log", recursive=True):
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
        "32s time bell, self-cleaning elimination"
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
        "exam - the full training window as the paper, the 32s time "
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
        "--regrade",
        action="store_true",
        help="re-score every RECORDED attempt with the CURRENT grader "
        "(no re-measurement): each attempt's stored answer text is "
        "graded again, the level pass flags and rung scores are "
        "recomputed, and every walk is marked PENDING - a restart "
        "then resumes the walks that the new grades re-opened. For "
        "grader changes; far cheaper than --clean",
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


def regrade_records(state: dict[str, Any]) -> int:
    """Re-score every recorded attempt with the CURRENT grader (the
    --regrade path, for grader changes - far cheaper than --clean):
    the attempts' stored answer text is graded again, the level pass
    flags and rung scores recomputed from the new ok flags, and every
    walk's derived verdict cleared (_out_of_time dropped) so the run
    resumes exactly the walks the new grades re-opened. Returns the
    number of attempts whose grade flipped."""
    from bench.exam import TIME_BELL_SECONDS, score_exam

    flipped = 0
    for fam, tree in (state.get("exam") or {}).items():
        if not isinstance(tree, dict):
            continue
        tree.pop("_out_of_time", None)
        for rung, rec in tree.items():
            if not isinstance(rec, dict) or rung.startswith("_"):
                continue
            if rec.get("too_large") or rec.get("unbuildable"):
                continue
            levels = rec.get("levels") or {}
            for lv, lrec in levels.items():
                attempts = lrec.get("attempts") or []
                for a in attempts:
                    if a.get("answer") is None or not a.get("expected"):
                        continue
                    new_ok = score_exam(
                        a.get("answer") or "",
                        {"path": a["expected"]},
                        a.get("finish_reason") or "stop",
                    )
                    if new_ok != a.get("ok"):
                        a["ok"] = new_ok
                        flipped += 1
                lrec["pass"] = all(a.get("ok") for a in attempts) and bool(attempts)
            # recompute the rung's score: the highest level with all-below passed
            score = None
            for lv in sorted(levels, key=int):
                if not levels[lv].get("pass"):
                    break
                score = int(lv)
            rec["score"] = score
    return flipped



def write_v94_md(state: dict[str, Any], roster_pos: dict[str, int]) -> None:
    """md/v9.4.md - the tournament ledger, v9.4: ONE line per model
    (its quant walk), in md/models.md order. The deciding rung's
    score IS the model's score; the quant column shows WHICH
    variant carried the exam (the walk's best scorer). Eliminated =
    the model's artifacts were deleted from the benchmark machine
    (the collected data always stays in git). Tied top-tier models
    are never eliminated; their ranking column shows the time order
    at the highest exam level (the tiebreaker indication - the
    human breaks ties)."""
    from bench.exam import best_rung

    exam = state.get("exam") or {}
    # gather the measured models first (needed for the tier ranking)
    rows = []
    for fam, pos in sorted(roster_pos.items(), key=lambda kv: kv[1]):
        fam_exam = exam.get(fam) or {}
        if not isinstance(fam_exam, dict):
            continue
        br = best_rung(fam_exam)
        if br is None:
            continue
        rung, rec = br
        score = rec.get("score")
        # the time + generation rate at the model's HIGHEST PASSED
        # level (both parts), and the MAX CONTEXT USED across all
        # its attempts - how much of the paper the model ever needed
        top_time = None
        top_tps = None
        max_ctx = 0
        for lv in (rec.get("levels") or {}).values():
            for a in lv.get("attempts") or []:
                max_ctx = max(max_ctx, a.get("answer_tokens") or 0)
        if score is not None and score >= 0:
            lv = (rec.get("levels") or {}).get(str(score)) or {}
            atts = lv.get("attempts") or []
            tot = sum(a.get("elapsed_s") or 0 for a in atts)
            toks = sum(a.get("answer_tokens") or 0 for a in atts)
            if atts and tot > 0:
                top_time = tot
                top_tps = toks / tot
        rows.append((fam, pos, rung, score, top_time, top_tps, max_ctx))
    # the top tier: the global best score; rank by time at the top
    # level, fastest first (the tiebreaker indication)
    # rows are (fam, pos, rung, score, top_time, top_tps, max_ctx):
    # the score is r[3] (r[2] is the RUNG - reading it here made the
    # tier 'the models with the lexicographically-largest quant name')
    best = max((r[3] for r in rows if r[3] is not None), default=None)
    tier = [r for r in rows if r[3] is not None and r[3] == best]
    tier.sort(key=lambda r: (r[4] if r[4] is not None else float("inf")))
    rank = {r[0]: i + 1 for i, r in enumerate(tier)}
    lines = [
        "# v9.4.md - the tournament ledger (v9.4: the exhaustive quant walk, the 32s bell)",
        "",
        "One line per model, md/models.md order (param-ascending). The",
        "deciding rung's score IS the model's score; the quant column is",
        "the variant that carried the exam (the walk's best scorer). The",
        "context is the model's full training window; no model gets more",
        "than 32s to solve any exam. Max context used = the largest",
        "answer the model ever produced (its real need vs its window).",
        "Time = the wall time at the model's highest passed level (both",
        "parts). The ranking column is valid ONLY for the top tier (tied",
        "at the global best): fastest first, the tiebreaker indication -",
        "the human breaks ties.",
        "",
        "| # | model | quant | score | max context used | time @ top | tok/s @ top | rank |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for fam, pos, rung, score, top_time, top_tps, max_ctx in rows:
        rk = rank.get(fam, "-")
        lines.append(
            f"| {pos} | {fam} | {rung} "
            f"| {score if score is not None else '-'} "
            f"| {max_ctx} "
            f"| {f'{top_time:.1f}s' if top_time is not None else '-'} "
            f"| {f'{top_tps:.1f}' if top_tps is not None else '-'} "
            f"| {rk} |"
        )
    lines.append("")
    n_measured = sum(1 for r in rows if r[3] is not None)
    lines.append(
        f"_{n_measured} models measured; the deciding rung's record decides "
        "everything. Max context used = the largest answer the model ever "
        "produced (its real need vs its window)._"
    )
    with open(os.path.join("md", "v9.4.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    stamp("v9.4.md ledger rewritten")


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
        # takes the exam under the full-window paper and the 32s
        # time bell; the roster is self-cleaning (strictly-lower
        # scorers are deleted from disk as soon as scores exist).
        from bench.exam import run as exam_run
        from bench.roster import roster_from_models_md

        if args.clean and state.get("exam"):
            state["exam"] = {}
            save_state(args.state_file, state)
            stamp("exam: all records wiped (--clean) - a full re-measure under the v9 protocol")

        if args.regrade:
            flipped = regrade_records(state)
            save_state(args.state_file, state)
            stamp(
                f"exam: {flipped} attempt grade(s) re-scored with the current "
                "grader (--regrade) - every walk is PENDING; the run resumes "
                "exactly the walks the new grades re-opened"
            )

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
            write_v94_md(
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
            write_v94_md(
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
        write_v94_md(
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
