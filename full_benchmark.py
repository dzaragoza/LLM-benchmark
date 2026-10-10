#!/usr/bin/env python3
"""full_benchmark.py -- the certify orchestrator (session 41, addendum 35:
the simplification - ONE mode, the protocol; the legacy sweep, tournament,
rescore, diagnose and size-table modes are cut, their code in git history).

One command: acquire each family's rung file on demand (the registry's
param-ascending order, smallest model first - no hidden selection), then
run the certify controllers (speed + vt per cell, never re-measuring
a stored cell; arc/fwe retired session 43, or --task v7: the
fixed-budget reach benchmark).

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
from functools import partial
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bench.tee_output as tee_output
import infra.convert_quant as convert_quant
import infra.git_ops as git_ops
import infra.hf_download as hf_download
import infra.llama_server as llama_server
from bench import state_store as _state_store
from bench.v7 import certify_v7

# addendum 132: the llama-server-supported --cache-type-k/v values
# (the KV_QUANT_LADDER rungs must come from this set)
_KV_CHOICES = ["q8_0", "q4_0", "q4_1", "q5_0", "q5_1", "iq4_nl"]

# addendum 183: the v5 cell/controller surface is retired; only the v7
# machinery and the state-store loader remain
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
    the .gitignore."""
    stamp("committing artifacts to git (state, results, dumps, mem sidecars)")
    paths = [args.state_file, args.results_file, "results.txt"]
    paths += (
        glob.glob("models/*/*.live-dump*.json")
        + glob.glob("models/*/*.sentinel*.json")
        + glob.glob("models/*/*.mem.json")
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


def v7_model_commit(args: argparse.Namespace, entries: list[dict[str, Any]]) -> None:
    """Session 44, addendum 132: the commit fires once per MODEL,
    after all its ctx cells are scored (was per cell, addendum 115 -
    too frequent). Addendum 147: it fires only when at least one
    cell RAN - a fully-skipped family (resume) commits nothing.
    A git failure never stops the run; the commit is skipped under
    --no-git/dry-run."""
    fam = entries[0].get("family")
    scored = sum(1 for e in entries if e.get("score") is not None)
    stamp(f"v7 model done: {fam} ({scored}/{len(entries)} cells scored) - committing artifacts")
    tee_output.uninstall()
    try:
        git_tail(args)
    finally:
        tee_output.install()


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
    tee_output.uninstall()
    try:
        git_tail(args)
    finally:
        tee_output.install()


def partial_commit_hook(args: argparse.Namespace) -> Any:
    return lambda fam, verdict, medal, depth: verdict_commit(args, fam, verdict, medal, depth)


# =========================================================== sigint


def sigint_shutdown(_signum, _frame, args=None):
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
    ap.add_argument("--models-dir", default=MODELS_DIR_DEFAULT)
    ap.add_argument("--state-file", default=STATE_FILE_DEFAULT)
    ap.add_argument("--results-file", default=RESULTS_FILE_DEFAULT)
    ap.add_argument(
        "--task",
        default="v7",
        choices=["v7"],
        help="the certify task; 'all' is the combined controller "
        "(speed + vt per cell, measured only if missing); 'v7' is the "
        "fixed-budget reach benchmark (session 42/43: greedy (q,k,v) "
        "cells, one fixed 256k corpus, graded (span, hops)). ARC and "
        "FWE are retired (session 43: v7 sharpened the focus to reach "
        "vs reasoning; the corpus carries both axes)",
    )
    ap.add_argument(
        "--v7-budget-gib",
        type=float,
        default=None,
        help="v7: the memory budget in GiB (default 4.0)",
    )
    ap.add_argument(
        "--v7-families",
        type=int,
        required=True,
        help="v7: MANDATORY (addendum 156) - the first N candidates param-ascending; "
        "unplaceable candidates are reported as findings, the measured count is "
        "honest by construction (addendum 154)",
    )
    ap.add_argument(
        "--v7-cells",
        default=None,
        help="v7: measure ONLY these cells, comma-separated family:ctx "
        "pairs (addendum 162) - everything else reports as skipped, never "
        "measured. E.g. --v7-cells Qwen3.5-2B:262144,granite-4.0-1b:16384",
    )
    ap.add_argument(
        "--v7-multi-arm",
        action="store_true",
        help="v7: measure all three allocation policies per cell (addendum 166) - "
        "greedy first, then stingy/random only where their config differs; every "
        "arm's config and score stored in the same cell record",
    )
    ap.add_argument(
        "--v7-probe-axes",
        default=None,
        help="v7: the axis probe (addendum 196) - measure the config neighborhood "
        "(base + each axis one rung down + the pairwise downs) with n=3 repeat "
        "corpora on these cells, comma-separated family:ctx pairs. Results land "
        "under families/<fam>/probe/<ctx>/, apart from the v7 table. "
        "E.g. --v7-probe-axes Qwen3.5-2B:131072",
    )
    ap.add_argument(
        "--clean",
        action="store_true",
        help="v7: wipe ALL stored v7 cells and answer logs UP FRONT, then "
        "measure - never leave mixed-era results in the table (addendum 129)",
    )
    ap.add_argument(
        "--v7-alloc",
        default="greedy",
        choices=["greedy", "stingy", "random"],
        help="v7: the allocation climb policy (addendum 144/150) - greedy takes "
        "the largest-fitting single-axis upgrade (R-18), stingy the smallest, "
        "random a seeded random one (reproducible)",
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
    resolve_families(args, state)
    # addendum 183: the v5 rung ladder args are retired with the v5 tasks
    if args.task == "v7":
        from bench.v7 import BUDGET_GIB

        def parse_v7_cells(spec: str | None) -> list[tuple[str, int]] | None:
            if not spec:
                return None
            out = []
            for pair in spec.split(","):
                fam, ctx = pair.rsplit(":", 1)
                out.append((fam.strip(), int(ctx)))
            return out

        if args.v7_probe_axes:
            from bench.v7 import probe_axes

            probe_spec = []
            for pair in args.v7_probe_axes.split(","):
                fam, ctx = pair.rsplit(":", 1)
                probe_spec.append((fam.strip(), int(ctx)))
            probe_results = probe_axes(
                args.models_dir,
                state,
                args.state_file,
                state.get("ladder_port", 8210),
                probe_spec,
                dry_run=args.dry_run,
                budget_gib=args.v7_budget_gib or BUDGET_GIB,
                on_model_commit=None
                if (args.no_git or args.dry_run)
                else partial(v7_model_commit, args),
            )
            state["probe"] = probe_results
            save_state(args.state_file, state)
            print()
            print("=" * 60)
            stamp("V7 AXIS PROBE SUMMARY")
            for fam, ctx in probe_spec:
                pdir = ((state["families"].get(fam) or {}).get("probe") or {}).get(str(ctx)) or {}
                if not pdir:
                    continue
                print(f"  {fam} ctx={ctx}:")
                for key, rec in sorted(pdir.items(), key=lambda kv: -(kv[1].get("mean_score") or 0)):
                    if "mean_score" in rec:
                        print(
                            f"    {key}: mean {rec['mean_score']} "
                            f"(per-seed {rec.get('scores')}) est {rec.get('est_gib')} GiB"
                        )
            if not args.no_git:
                tee_output.uninstall()
                git_tail(args)
            stamp("probe complete")
            return

        results = certify_v7(
            args.models_dir,
            state,
            args.state_file,
            state.get("ladder_port", 8210),
            args.v7_families,
            dry_run=args.dry_run,
            budget_gib=args.v7_budget_gib or BUDGET_GIB,
            on_model_commit=None
            if (args.no_git or args.dry_run)
            else partial(v7_model_commit, args),
            clean=args.clean,
            alloc_policy=args.v7_alloc,
            only_cells=parse_v7_cells(args.v7_cells),
            multi_arm=args.v7_multi_arm,
        )
        state["v7"] = results
        save_state(args.state_file, state)
        print()
        print("=" * 60)
        stamp("V7 REACH BENCHMARK SUMMARY")
        best = None
        for r in results:
            if r.get("score") is None:
                print(f"  {r['family']} ctx={r['ctx']}: {r.get('skipped', r.get('error', '?'))}")
                continue
            print(f"  {r['family']} ctx={r['ctx']}: score {r['score']}/{r['max_score']}")
            if not r["max_score"]:
                continue  # no reachable grades: excluded, not a zero (R-19)
            if best is None or r["score"] > best["score"]:
                best = r
        if best:
            stamp(
                f"V7 ARGMAX at 4 GiB: {best['family']} ctx={best['ctx']} "
                f"({best['wq']}, k={best['kq']}, v={best['vq']}) "
                f"score {best['score']}/{best['max_score']}"
            )
        if not args.no_git:
            tee_output.uninstall()
            git_tail(args)
        stamp("run complete")
        return

    # addendum 183: the v5 task controllers (vt/speed/all) are retired with
    # the v5 cell machinery - only the v7 task remains (the author's ruling:
    # "We only need V7.1 machinery. Rest is dead code.")
    if args.task != "v7":
        raise SystemExit(f"task {args.task!r} is retired (addendum 183) - only --task v7 exists")
    if not args.no_git:
        tee_output.uninstall()
        git_tail(args)
    stamp("run complete")

if __name__ == "__main__":
    main()
