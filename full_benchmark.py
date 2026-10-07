#!/usr/bin/env python3
"""full_benchmark.py -- the certify orchestrator (session 41, addendum 35:
the simplification - ONE mode, the protocol; the legacy sweep, tournament,
rescore, diagnose and size-table modes are cut, their code in git history).

One command: acquire each family's rung file on demand (the registry's
param-ascending order, smallest model first - no hidden selection), then
run the certify controllers (the medal ladder: speed, fwe, vt, arc per
cell, never re-measuring a stored cell).

  families  the registry roster (param-ascending) or the specs given.
  rung      default Q8_0; --force-rung f16 is the full-capacity pass.
  verdicts  commit and push themselves (addendum 31); --no-git opts out.

Everything is IDEMPOTENT and RESUMABLE: the state file is rewritten after
every cell; rerun the same command to resume.
"""

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
from bench import cells as _cells
from bench import certify as _certify
from bench import state_store as _state_store
from bench.constants import (
    CORPUS_DEFAULT,
    RUNG_DEFAULT,
    TOURNAMENT_DEPTHS,
)

# re-exports: the tests patch these seams
fwe_pass = _cells.fwe_pass
vt_pass = _cells.vt_pass
speed_pass = _cells.speed_pass
speed_cell = _cells.speed_cell
kill_stale_server = _cells.kill_stale_server
COMBINED_TASKS = _state_store.COMBINED_TASKS
_task_load = _state_store._task_load
_task_store = _state_store._task_store
speed_cells = _state_store.speed_cells
vt_cells = _state_store.vt_cells
certify_cells = _state_store.certify_cells
wilson_interval = _certify.wilson_interval
certify_rung = _certify.certify_rung
certify_rung_combined = _certify.certify_rung_combined
TASK_PASS_BARS = _certify.TASK_PASS_BARS
combined_medal = _certify.combined_medal

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
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return {"families": {}}


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
            args.corpus,
            f"corpus not found at {args.corpus} - build it: python3 speed_gate.py --make-corpus",
        ),
        (
            QUANTIZE_BIN,
            f"llama-quantize not found at {QUANTIZE_BIN} - place the b10964 build in the repo root",
        ),
        (
            "./llama.cpp/convert_hf_to_gguf.py",
            "converter not found - the llama.cpp checkout must be in the repo root",
        ),
        (SERVER_BIN or "", "llama-server not found - place the b10964 build in the repo root"),
    ]:
        if not os.path.isfile(path):
            sys.exit(msg)


# =========================================================== roster


def _registry_params(spec: str) -> float | None:
    """The spec's registry parameter count. The spec may be a REPO
    ("Qwen/Qwen2.5-1.5B-Instruct") or a family NAME (the state file
    stores names - addendum 57: the name-only lookup silently sorted
    every state-carried family as uncounted, so restarts ran in
    alphabetical order instead of param-ascending)."""
    try:
        from etc import registry_data

        key = spec.partition("=")[0].rstrip("/")
        # addendum 62: the state carries acquisition-era names that may
        # differ from the roster key by a quant suffix (MiniCPM-1B-sft-bf16
        # vs roster MiniCPM-1B-sft) - strip the common suffixes so both
        # shapes resolve and the param sort never degenerates to
        # "unknowns last".
        aliases = {key}
        for suffix in ("-bf16", "-f16", "-f32", "-instruct"):
            if key.endswith(suffix):
                aliases.add(key[: -len(suffix)])
        for name, r in registry_data.ROSTER.items():
            if (
                key in (r, name, r.rpartition("/")[2]) or aliases & {name, r.rpartition("/")[2]}
            ) and (registry_data.params_b(name) is not None):
                return registry_data.params_b(name)
    except ImportError:
        return None
    return None


def param_ascending_specs(specs: list[str]) -> list[str]:
    """Family specs in PARAM-ASCENDING order (session 40, addendum 28):
    the model repo's registry parameter count, smallest first;
    unregistered repos sort after the counted ones, by repo name."""
    return sorted(
        specs,
        key=lambda s: (
            _registry_params(s.partition("=")[0].rstrip("/")) is None,
            _registry_params(s.partition("=")[0].rstrip("/")) or 0.0,
            s.partition("=")[0].rstrip("/"),
        ),
    )


def _resolve_spec_repo(spec: str) -> str | None:
    """A name-only spec (a state-carried family name, no stored spec)
    resolves to its roster REPO before it ever reaches the hub
    (addendum 63): 'MiniCPM-1B-sft-bf16' is a family name, not a repo -
    the hub 404s on it and the run crashes. Matches the repo string,
    its basename, or the roster name; suffix-quant aliases resolve too
    (the addendum-62 alias class).
    """
    try:
        from etc import registry_data

        key = spec.partition("=")[0].rstrip("/")
        aliases = {key}
        for suffix in ("-bf16", "-f16", "-f32", "-instruct"):
            if key.endswith(suffix):
                aliases.add(key[: -len(suffix)])
        for name, r in registry_data.ROSTER.items():
            base = r.rpartition("/")[2]
            if key in (r, name, base) or aliases & {name, base}:
                return r if "=" not in spec else spec
    except Exception:
        return None
    return None


def resolve_families(args: argparse.Namespace, state: dict[str, Any]) -> None:
    """With no positional specs: the state file's families (param-
    ascending), or a fresh state's full registered roster."""
    if args.families:
        return
    saved = [(fst or {}).get("spec") or fam for fam, fst in (state.get("families") or {}).items()]
    args.families = param_ascending_specs([_resolve_spec_repo(s) or s for s in saved if s])
    if args.families:
        return
    try:
        from etc import registry_data

        args.families = [
            registry_data.ROSTER[name] for name in registry_data.params_sorted_roster()
        ]
        stamp(
            f"fresh state: the full registered roster, param-ascending "
            f"({len(args.families)} models, smallest first)"
        )
    except Exception:
        sys.exit("no family specs given and the state file has none")


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
    rc, out, err = git_ops.pull_rebase(no_verify=True)
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
    the .gitignore."""
    stamp("committing artifacts to git (state, results, dumps, mem sidecars)")
    paths = [args.state_file, args.results_file, "results.txt"]
    paths += (
        glob.glob("models/*/*.live-dump*.json")
        + glob.glob("models/*/*.sentinel*.json")
        + glob.glob("models/*/*.mem.json")
        + glob.glob("models/*/*.arc-cell*.log")
        + glob.glob("models/*/*-server.log")
        + glob.glob("models/*/*window-probe.log")
    )
    # addendum 60: the cell/server logs moved into the results tree -
    # the tournament-results glob below picks them up; the model-dir
    # globs stay for the pre-addendum-60 logs already committed.
    paths += glob.glob("models/tournament-results/**/*", recursive=True)
    paths += (
        glob.glob("models/*/ladder-results/*")
        + glob.glob("ladder-results/*")
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


def verdict_commit(
    args: argparse.Namespace, fam: str, verdict: str, medal: Any, depth: int
) -> None:
    """Session 40, addendum 31: every VERDICT commits and pushes
    IMMEDIATELY, so the run is watchable while it goes. A git failure
    never stops the run."""
    if verdict == "accept":
        what = f"{fam} MEDAL {medal} at rung {depth:,}"
    elif verdict == "infeasible":
        what = f"{fam} INFEASIBLE at rung {depth:,} - out of the benchmark (addendum 45)"
    else:
        what = f"{fam} DEAD at rung {depth:,}"
    stamp(f"verdict: {what} - committing partial results")
    if verdict == "accept":
        try:
            import picker_medals

            picker_medals.main()
            stamp("picker gold-medal panels updated (addendum 72)")
        except Exception as e:
            stamp(f"picker medals update failed (ignored): {e}")
    tee_output.uninstall()
    try:
        git_tail(args)
    finally:
        tee_output.install()


def partial_commit_hook(args: argparse.Namespace) -> Any:
    return lambda fam, verdict, medal, depth: verdict_commit(args, fam, verdict, medal, depth)


# =========================================================== sigint


def sigint_shutdown(signum, frame, args=None):
    """Session 38, addendum 8: Ctrl-C stops cleanly - stop llama-server,
    stop results logging, git commit and pull. os._exit, not sys.exit:
    a SystemExit inside the handler unwinds through huggingface_hub's
    ThreadPoolExecutor shutdown(wait=True), which waits out every
    in-flight download - the Ctrl-C "did not stop"."""
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
    signal.signal(signal.SIGINT, lambda s, f: sigint_shutdown(s, f, args))


# =========================================================== main


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="the certify benchmark: acquire each family's rung file "
        "on demand (param-ascending) and run the medal ladder"
    )
    ap.add_argument(
        "families",
        nargs="*",
        help='family specs: "model_repo" or "model_repo=source_repo"; '
        "omitted = the state file's families or the full registered "
        "roster (param-ascending)",
    )
    ap.add_argument("--corpus", default=CORPUS_DEFAULT)
    ap.add_argument("--models-dir", default=MODELS_DIR_DEFAULT)
    ap.add_argument("--state-file", default=STATE_FILE_DEFAULT)
    ap.add_argument("--results-file", default=RESULTS_FILE_DEFAULT)
    ap.add_argument(
        "--rung",
        default=RUNG_DEFAULT,
        help="the quant to benchmark (default Q8_0)",
    )
    ap.add_argument(
        "--force-rung",
        dest="rung_forced",
        nargs="?",
        const=True,
        default=False,
        metavar="RUNG",
        help="certify EVERY family at --rung, ignoring stored selections "
        "(addendum 25). An optional value sets the rung too "
        "(--force-rung f16 == --rung f16 --force-rung, addendum 33).",
    )
    ap.add_argument(
        "--rungs",
        type=str,
        default=None,
        metavar="D1,D2,...",
        help="comma-separated rung(s) to certify (e.g. --rungs 32768,65536), "
        "cheapest-first; omitted = the full ladder 4096..262144",
    )
    ap.add_argument(
        "--task",
        default="fwe",
        choices=["fwe", "vt", "speed", "all"],
        help="the certify task; 'all' is the combined controller - each "
        "cell carries speed, fwe, vt and arc, measured only if missing",
    )
    ap.add_argument(
        "--fwe-min-words",
        type=int,
        default=1,
        metavar="N",
        help="the FWE pass bar: a cell passes when >= N of the 3 hidden "
        "words are found (default 1)",
    )
    _KV_CHOICES = ["q8_0", "q4_0", "q4_1", "q5_0", "q5_1", "iq4_nl"]
    ap.add_argument("--kv-quant-k", default=None, choices=_KV_CHOICES)
    ap.add_argument("--kv-quant-v", default=None, choices=_KV_CHOICES)
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
    ap = build_parser()
    args = ap.parse_args()
    if isinstance(args.rung_forced, str):
        if "/" in args.rung_forced or "=" in args.rung_forced:
            ap.error(
                f"--force-rung takes a RUNG (e.g. f16, Q8_0), not a family - "
                f"families are positional: {args.rung_forced!r}"
            )
        args.rung = args.rung_forced
        args.rung_forced = True
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
    if args.kv_quant_k:
        state["kv_quant_k"] = args.kv_quant_k
    if args.kv_quant_v:
        state["kv_quant_v"] = args.kv_quant_v
    resolve_families(args, state)
    if args.rungs:
        try:
            rung_list = [int(x) for x in args.rungs.split(",") if x.strip()]
        except ValueError:
            ap.error(f"--rungs must be comma-separated integers, got {args.rungs!r}")
        if not rung_list:
            ap.error("--rungs needs at least one depth")
    else:
        rung_list = list(TOURNAMENT_DEPTHS)
    for depth in sorted(rung_list):
        if args.task == "all":
            results = certify_rung_combined(
                depth,
                args.families,
                args.models_dir,
                state,
                args.state_file,
                state.get("ladder_port", 8210),
                args.dry_run,
                min_words=args.fwe_min_words,
                rung_override=args.rung if args.rung_forced else None,
                on_verdict=(None if args.no_git or args.dry_run else partial_commit_hook(args)),
            )
        else:
            results = certify_rung(
                depth,
                args.families,
                args.models_dir,
                state,
                args.state_file,
                state.get("ladder_port", 8210),
                args.dry_run,
                min_words=args.fwe_min_words,
                task=args.task,
                rung_override=args.rung if args.rung_forced else None,
                on_verdict=(None if args.no_git or args.dry_run else partial_commit_hook(args)),
            )
        state["certify"] = results
        save_state(args.state_file, state)
        print()
        print("=" * 60)
        stamp(f"CERTIFY 2_sigma {depth:,} SUMMARY")
        for r in results:
            v = r.get("verdict", r.get("error", r.get("skipped", "?")))
            extra = f" w/s median {r['wps_median']}" if r.get("wps_median") else ""
            print(
                f"  {r['family']}: {v} ({r.get('passes', 0)}/"
                f"{r.get('cells_measured', 0)} cells, ran {r.get('ran_now', 0)} now){extra}"
            )
        verdicts = [r.get("verdict") for r in results if "verdict" in r]
        if "accept" in verdicts:
            # session 40, addendum 56: a rung ANSWERED by an accept moves
            # the ladder UP to the next depth - the author's v4 ruling ("one
            # model is crowned or every model is dead -> go to next rung"),
            # and EVERYONE climbs: the only permanent outs are the two
            # ruled-out categories (infeasible - addendum 45; speed-dead -
            # addendum 13, the gate only hardens with depth). The old break
            # ENDED the whole run at the first medal (the 4k stop).
            stamp(
                f"rung {depth:,} ANSWERED - the ladder moves up "
                f"(everyone climbs; infeasible and speed-dead stay out)"
            )
            continue
        if verdicts and all(v in ("dead", "infeasible") for v in verdicts):
            stamp(f"rung {depth:,} ALL-DEAD - the ladder moves up")
            continue
    if not args.no_git and not args.dry_run:
        tee_output.uninstall()
        git_tail(args)
    stamp("run complete")


if __name__ == "__main__":
    main()
