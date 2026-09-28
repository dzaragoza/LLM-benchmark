#!/usr/bin/env python3
"""full_benchmark.py -- the end-to-end benchmark orchestrator.

One command, four stages, one final output: the RANKING of the selected
models by strict ARC-Challenge score, with exact McNemar separation
tests on every consecutive rank gap. This script owns the orchestration
only - state/resume, the fixed Q8_0 rung (addendum 86: the rung walk is
removed), and the final results file. Each stage lives in its own dedicated script (split from this
file 2026-09-24; same protocol, same state, byte-identical behavior):

  hf_download.py  STAGE A phase 1: every Hugging Face interaction -
                  premade rung file, f16 GGUF, or safetensors snapshot.
  convert_quant.py STAGE A phase 2: everything that touches llama.cpp
                  conversion tooling - safetensors -> f16, f16 -> rung.
  speed_gate.py   STAGE A phases 3-4: the speed gate - the
                  llama-server bench interface, mode-suffixed dumps,
                  verdict (protocol v3.1: the reader-wall stall
                  rate - the streaming gate simulates the reader on
                  each turn's per-word arrival stream; a turn
                  stalls iff the reader ever hits the wall; PASS
                  iff <= 5% of turns stall, addendum 73).
  arc_eval.py     STAGE B (phase 5): strict ARC-Challenge on every
                  benched model (raw protocol, logprob letter scoring).
  mcnemar.py      STAGE C (phase 6): pairwise exact McNemar; the final
                  ranking with separation verdicts.

  STAGE A (phases 1-4, per family, fixed Q8_0 rung - addendum 86):
    1. DOWNLOAD - premade rung file or the data to create it later.
    2. CREATE   - convert safetensors -> f16, quantize f16 -> rung.
    3. BENCH    - speed_gate.py, 1 rep, worst-turn metric.
    4. ANALYZE  - verdict (protocol v3.1, addendum 73): the
                  reader-wall stall rate - the gate streams every
                  turn and simulates the reader (reader_wps after
                  REACTION_S); PASS iff at most 5% of turns stall
                  the reader (a stall is counted, never aborted
                  for - the rate needs its denominator); PASS =
                  selected.
  STAGE B (phase 5): strict ARC-Challenge on EVERY BENCHED model -
    PASS or FAIL verdict, selected or not (addendum 86: ARC always,
    the only skip is an already-complete CSV). FULL test split, 1172
    questions; logprob letter scoring, temperature 0; per-question
    CSVs in --arc-results-dir; the RANKING uses the selected models.
  STAGE C (phase 6): pairwise exact McNemar; final output = ranking.

Everything is IDEMPOTENT and RESUMABLE: ./benchmark-state.json is
rewritten after every phase; rerun the same command to resume. Files
are never re-downloaded/re-quantized; complete ARC CSVs are never
re-run. Every failure stops the script with reader guidance.

Supersedes select-quant.py + strict-arc.py + paired-arc.py (removed
2026-09-23 by author ruling; their final commits remain in git history).
The ARC protocol is IDENTICAL to strict-arc.py: raw /v1/completions
prompt, max_tokens=1, temperature=0, top-20 logprobs, port 8081,
-ngl 99, -c 2048, -t 8.

Thinking-model category (author ruling 2026-09-24): benchmarked
separately with --thinking (the SAME worst-turn gate and ARC protocol;
reasoning tokens are measured descriptively - latency spent thinking
is the user's informed choice and is NOT gated). Keep the category in
its own --state-file/--results-file so rankings stay separate.

Usage (from the repo root):
    python3 full_benchmark.py --dry-run "Qwen/Qwen2.5-3B-Instruct-GGUF" ...
    python3 full_benchmark.py "Qwen/Qwen2.5-3B-Instruct-GGUF" \\
        "microsoft/Phi-3-mini-4k-instruct-gguf" \\
        "meta-llama/Llama-3.2-3B-Instruct" \\
        "google/gemma-3-4b-it-qat-q4_0-gguf=google/gemma-3-4b-it"

  Hybrid non-thinking mode (--no-thinking): for hybrid models in the
  non-thinking category - benchmarks with thinking disabled
  (chat_template_kwargs enable_thinking=false; first-turn dump check
  confirms no reasoning appears).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import arc_eval
import convert_quant
import hf_download
import llama_server
import mcnemar
import speed_gate

QUANTIZE_BIN = convert_quant.QUANTIZE_BIN
CORPUS_DEFAULT = speed_gate.CORPUS_DEFAULT
MODELS_DIR_DEFAULT = "./models"
STATE_FILE_DEFAULT = "./benchmark-state.json"
RESULTS_FILE_DEFAULT = "./benchmark-results.json"
# Q4_0 removed (author ruling, addendum 37): Q4_K_M is the single 4-bit
# rung - "there's a q4_0 that's unnecessary since we have q4_k_m".
# RUNG_BITS keeps the Q4_0 ratio for ad-hoc size estimates.
# Addendum 86: the rung walk is removed - the study is Q8_0 only
# (quant out of scope, MODEL-SELECTION.md note). One fixed rung.
RUNG = "Q8_0"
READER_WPS_DEFAULT = speed_gate.READER_WPS_DEFAULT
ARC_NUM_DEFAULT = arc_eval.ARC_NUM_DEFAULT
ARC_RESULTS_DIR_DEFAULT = arc_eval.ARC_RESULTS_DIR_DEFAULT
ARC_PORT = arc_eval.ARC_PORT
SERVER_BIN = llama_server.find_server()

local_rung = hf_download.local_rung
list_repo_files = hf_download.list_repo_files
safe_label = arc_eval.safe_label
arc_csv_path = arc_eval.arc_csv_path
arc_csv_valid = arc_eval.arc_csv_valid
load_questions = hf_download.load_questions
GUIDE = {}
GUIDE[1] = hf_download.GUIDE[1]
GUIDE[2] = convert_quant.GUIDE[2]
GUIDE[3] = speed_gate.GUIDE[3]
GUIDE[4] = speed_gate.GUIDE[4]
GUIDE[5] = arc_eval.GUIDE[5]
GUIDE[6] = mcnemar.GUIDE[6]
fail = hf_download.fail


# =========================================================== timestamps
# Addendum 78, item 4: every phase line carries a wall-clock stamp and
# the elapsed sweep time - run 1's log had no durations, so every time
# estimate had to be bracketed from commit times.
_SWEEP_T0 = time.time()


def stamp(msg: str) -> None:
    elapsed_min = (time.time() - _SWEEP_T0) / 60.0
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')} +{elapsed_min:.0f}m] {msg}")


# --dry-run read-only guard (addendum 79): set in main(); save_state
# checks it so a pre-flight never mutates the state file.
DRY_RUN_ACTIVE = False


# =========================================================== estimator
# Addendum 83: the dry-run run-time estimate. Pure: state in, counts
# and minutes out. Extracted from main() for the test suite
# (addendum 87) - the classification-order rule (f16 BEFORE download)
# is the bug class the tests pin.

PLAN_COST_MIN = {
    "local": 15,
    "download": 30,
    "f16_quantize": 45,
    "convert_quantize": 60,
    "unknown": 45,
}


def classify_plan(plan: str) -> str:
    """One acquisition plan string -> its cost class."""
    if plan.startswith("local file"):
        return "local"
    if "f16 from" in plan:
        return "f16_quantize"
    if plan.startswith("download "):
        return "download"
    if "safetensors from" in plan or "pytorch_model.bin from" in plan:
        return "convert_quantize"
    return "unknown"


def estimate_runtime(state: dict[str, Any]) -> tuple[dict[str, int], int]:
    """State -> (plan_counts, total_min). Infeasible cells excluded."""
    counts, total = {}, 0
    for fst in state.get("families", {}).values():
        for run in fst.get("runs", {}).values():
            plan = run.get("plan", "") or ""
            verdict = run.get("verdict", "") or ""
            if not plan or verdict.startswith("FAIL (infeasible"):
                continue
            cls = classify_plan(plan)
            counts[cls] = counts.get(cls, 0) + 1
            total += PLAN_COST_MIN[cls]
    return counts, total


# =========================================================== arc jobs
# Addendum 86: ARC runs on EVERY benched family (PASS or FAIL
# verdict) with a file; the only skip is an already-complete CSV
# (inside arc_eval.arc_run). Extracted from main() for the test suite
# (addendum 87). Pure: state -> [(family, rung, run), ...].


def collect_arc_jobs(
    state: dict[str, Any], roster: list[str] | None = None
) -> list[tuple[str, str, dict[str, Any]]]:
    jobs = []
    for fam, fst in state.get("families", {}).items():
        if roster is not None and fam not in roster:
            continue
        for rung, run in fst.get("runs", {}).items():
            if (
                run.get("file")
                and run.get("verdict")
                and not str(run["verdict"]).startswith("FAIL (infeasible")
            ):
                jobs.append((fam, rung, run))
    return jobs


# =========================================================== state


def load_state(path: str) -> dict[str, Any]:
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return {"families": {}}


def save_state(path: str, state: dict[str, Any]) -> None:
    # --dry-run is a READ-ONLY pre-flight (addendum 79): a dry run must
    # never write the state file, or the pre-flight-then-real-run way
    # of working would poison the real run (phases marked done with no
    # file on disk). Guarded here at the single choke point.
    if DRY_RUN_ACTIVE:
        return
    with open(path, "w") as f:
        json.dump(state, f, indent=1)


# =========================================================== selection


def process_family(
    spec: str,
    corpus: str,
    models_dir: str,
    state: dict[str, Any],
    state_path: str,
    dry_run: bool,
    force: bool,
    thinking: bool = False,
    no_thinking: bool = False,
    reader_wps: float = READER_WPS_DEFAULT,
) -> None:
    model_repo, _, source_repo = spec.partition("=")
    if not source_repo:
        source_repo = model_repo
    fam = os.path.basename(model_repo.rstrip("/"))
    famdir = os.path.join(models_dir, fam)
    fst = state["families"].setdefault(fam, {"spec": spec, "runs": {}, "selected": None})

    print()
    print("=" * 60)
    stamp(f"family: {fam}")
    print(f"  model repo : {model_repo}")
    print(f"  source repo: {source_repo}")
    print(f"  folder     : {famdir}")
    if fst["selected"] and not force:
        s = fst["runs"][fst["selected"]]
        print(
            f"  already selected: {fst['selected']} "
            f"({s['verdict']}, worst {s['worst']:.1f} t/s) - skipping "
            "(--force to redo)"
        )
        return
    if force:
        # --force re-benches: clear every rung's verdict and phases 3-4
        # (phases 1-2 stay done - the rung files exist and are reused;
        # the dumps are re-measured because speed_gate.bench gets force
        # too). Without this, the fixed-rung pass below would skip on the
        # STORED verdicts and --force would silently do nothing past
        # the family-level check (addendum 42).
        cleared = 0
        for run in fst["runs"].values():
            run["phases_done"] = [p for p in run.get("phases_done", []) if p in (1, 2)]
            if run.pop("verdict", None) is not None:
                cleared += 1
        fst["selected"] = None
        save_state(state_path, state)
        print(f"  --force: re-benching {RUNG} ({cleared} stored verdict(s) cleared; files reused)")

    # Stale-state guard (addendum 43): a stored rung file can vanish
    # from disk (folder deleted/moved) while benchmark-state.json still
    # marks phases 1-2 done. Trusting the state then crashes phase 3
    # with a bare FileNotFoundError. Invalidate those phases so the
    # walk re-acquires (re-download/re-quantize; both stages are
    # idempotent) instead of benching a path that is not there.
    for run in fst["runs"].values():
        f = run.get("file")
        if f and not os.path.isfile(f):
            run["phases_done"] = []
            run.pop("file", None)
            run.pop("plan", None)
            save_state(state_path, state)
            print(
                f"  stored rung file missing on disk ({f}) - "
                "phases 1-2 invalidated; will re-acquire"
            )

    hf_download.require_hub()
    assert list_repo_files is not None  # require_hub exits when the hub is missing
    try:
        model_files = list_repo_files(model_repo)
        source_files = model_files if source_repo == model_repo else list_repo_files(source_repo)
    except Exception as e:
        fail(1, "-", f"cannot list repo files for {model_repo}: {e}", GUIDE[1])

    for rung in [RUNG]:
        run = fst["runs"].get(rung, {"phases_done": []})
        fst["runs"][rung] = run
        if str(run.get("verdict", "")).startswith("PASS"):
            break
        if run.get("verdict") == "FAIL":
            continue
        print(f"\n  rung {rung}:")
        if 1 not in run["phases_done"]:
            path, plan = hf_download.acquire(
                fam, famdir, rung, model_repo, model_files, source_repo, source_files, dry_run
            )
            run["plan"] = plan
            run["phases_done"].append(1)
            save_state(state_path, state)
            if plan.startswith("infeasible"):
                run["verdict"] = "FAIL (infeasible: exceeds system RAM)"
                run["rung"] = rung
                save_state(state_path, state)
                continue
            print(f"  [1] downloads ok  (plan: {plan})")
            stamp("      phase 1 done (acquire)")
        if 2 not in run["phases_done"]:
            path = convert_quant.create(fam, famdir, rung, run.get("plan", ""), dry_run)
            if path:
                run["file"] = path
            run["phases_done"].append(2)
            save_state(state_path, state)
            print(f"  [2] rung file ready  ({run.get('file', 'dry run')})")
            stamp("      phase 2 done (create)")
        path = run.get("file") or local_rung(famdir, rung)
        assert path is not None  # phases 1-2 guarantee it on real runs
        if dry_run and not path:
            print(f"  [3] would live-bench the {rung} file")
            print(
                f"  [4] would analyze (the reader-wall test: a turn "
                f"fails iff the reader EVER hits the stream - reader "
                f"{reader_wps:g} w/s, reaction "
                f"{speed_gate.READER_REACTION_S}s, addendum 55)"
            )
            continue
        if 3 not in run["phases_done"]:
            dump = speed_gate.bench(
                path, corpus, dry_run, thinking, no_thinking, force=force, reader_wps=reader_wps
            )
            run["phases_done"].append(3)
            save_state(state_path, state)
            print(f"  [3] live bench ok  (dump: {os.path.basename(dump)})")
            stamp("      phase 3 done (bench)")
        if 4 not in run["phases_done"]:
            res = speed_gate.analyze(path, thinking, no_thinking, reader_wps=reader_wps)
            run.update(res)
            run["phases_done"].append(4)
            save_state(state_path, state)
            print(
                f"  [4] {res['verdict']} — reader-wall stall rate: "
                f"{res['wall_fail_turns']} of {res['n_turns']} turns "
                f"stalled ({res['stall_rate']:.1%}; PASS <= "
                f"{res['stall_rate_max']:.0%}), "
                f"{res['catchup_events']} catch-up event(s), "
                f"worst wait {res['worst_catchup_s']:.2f}s "
                f"(addendum 73; the span diagnostics: worst "
                f"{res['worst']:.2f} w/s, mean {res['mean']:.2f}, "
                f"sigma {res['sigma']:.2f})"
            )
            print(
                f"      token-side: worst {res['worst_tps']:.1f} t/s, "
                f"words/token {res['words_per_token']:.3f} (measured)"
            )
            mem_sidecar = dump + ".mem.json"
            if os.path.isfile(mem_sidecar):
                try:
                    with open(mem_sidecar) as f:
                        mem = json.load(f)
                    peaks = [m["peak_rss_gib"] for m in mem if m.get("peak_rss_gib")]
                    if peaks:
                        print(
                            f"      memory: peak RSS {max(peaks):.2f} "
                            "GiB (weights + KV + buffers + runtime; "
                            "VmHWM, addendum 36)"
                        )
                except Exception:
                    pass
            stamp("      phase 4 done (analyze)")
        if str(run["verdict"]).startswith("PASS"):
            fst["selected"] = rung
            run["rung"] = rung
            save_state(state_path, state)
            print(f"  SELECTED {rung} for {fam}")
            break


# =========================================================== main


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="end-to-end benchmark: quant selection, strict full "
        "ARC, exact-McNemar ranking - one final output"
    )
    ap.add_argument(
        "families", nargs="+", help='family specs: "model_repo" or "model_repo=source_repo"'
    )
    ap.add_argument("--corpus", default=CORPUS_DEFAULT)
    ap.add_argument(
        "--reader-wps",
        type=float,
        default=READER_WPS_DEFAULT,
        help="the k=1 guarantee line in WORDS per second: "
        "worst turn at the reference depth must never "
        "fall below this (default 5.0 w/s = 300 wpm, "
        "Brysbaert 2019 - match the fast reader)",
    )
    ap.add_argument("--models-dir", default=MODELS_DIR_DEFAULT)
    ap.add_argument("--state-file", default=STATE_FILE_DEFAULT)
    ap.add_argument("--results-file", default=RESULTS_FILE_DEFAULT)
    ap.add_argument(
        "--arc-num",
        type=int,
        default=ARC_NUM_DEFAULT,
        help="ARC-Challenge questions (default: full 1172)",
    )
    ap.add_argument("--arc-results-dir", default=ARC_RESULTS_DIR_DEFAULT)
    ap.add_argument("--arc-config", default="ARC-Challenge", choices=["ARC-Challenge", "ARC-Easy"])
    ap.add_argument(
        "--roster",
        default=None,
        help="restrict phases 5-6 and the ranking to these "
        "families (comma-separated, as named in the "
        "family specs); the state file accumulates "
        "across studies - without this flag the "
        "ranking defaults to the families named in "
        "this run's command line (addendum 41/56)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="READ-ONLY pre-flight (addendum 79): lists "
        "every repo, verifies tooling, runs the "
        "RAM/disk feasibility checks and reports each "
        "family's acquisition plan WITHOUT downloading, "
        "converting, benching or touching the state "
        "file. THE WAY OF WORKING: always run the "
        "command with --dry-run first, read the "
        "pre-flight report, then issue it without.",
    )
    ap.add_argument(
        "--force", action="store_true", help="redo families that already have a selection"
    )
    ap.add_argument(
        "--thinking",
        action="store_true",
        help="thinking-model category: benchmark with "
        "thinking enabled (same worst-turn gate; "
        "reasoning measured descriptively). Use separate "
        "--state-file/--results-file for this category.",
    )
    ap.add_argument(
        "--git-commit",
        action="store_true",
        help="commit and push the run's artifacts (state, "
        "results, per-turn dumps, mem sidecars, ARC "
        "CSVs) when the run completes - force-added "
        "past the ignores (addendum 78, item 5)",
    )
    ap.add_argument(
        "--no-thinking",
        action="store_true",
        help="hybrid models, non-thinking category: "
        "run with thinking disabled (chat-template "
        "kwargs enable_thinking=false; first-turn dump "
        "check confirms no reasoning appears)",
    )
    return ap


def main() -> None:
    ap = build_parser()
    args = ap.parse_args()
    global DRY_RUN_ACTIVE
    DRY_RUN_ACTIVE = args.dry_run

    if args.thinking and args.no_thinking:
        ap.error("--thinking and --no-thinking are mutually exclusive")

    if not args.dry_run:
        check_tooling(args)

    state = load_state(args.state_file)

    if not args.families:
        ap.error("no family specs given")

    failed_families = sweep_families(args, state)

    if args.dry_run:
        preflight_report(args, state, failed_families)
        return

    roster, selections, arc_jobs = prepare_phase56(args, state)
    report_roster_notes(args, state, roster, failed_families)
    run_arc_phase(args, state, arc_jobs)
    run_ranking(args, state, selections)
    write_results(args, state)
    print_wt_table(state)

    # ---- addendum 78, item 5: the git tail - commit and push every
    # artifact the study needs (state, results, per-turn dumps, mem
    # sidecars, ARC CSVs), force-added past the .gitignore.
    if args.git_commit and not args.dry_run:
        git_tail(args)
    stamp("run complete")


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


def sweep_families(args: argparse.Namespace, state: dict[str, Any]) -> list[tuple[str, str]]:
    """Phase A: bench every family (per-family isolation, addendum 78)."""
    # Addendum 78, item 4: per-family isolation IN THE TOOL - a family
    # that dies (conversion OOM, unsupported architecture, a bad repo)
    # is recorded and the sweep CONTINUES; the author's "continue even
    # in failure" made structural, no shell wrapper needed.
    failed_families = []
    for spec in args.families:
        try:
            process_family(
                spec,
                args.corpus,
                args.models_dir,
                state,
                args.state_file,
                args.dry_run,
                args.force,
                args.thinking,
                args.no_thinking,
                args.reader_wps,
            )
        except SystemExit as e:
            failed_families.append((spec, str(e) or "exit"))
            stamp(f"FAMILY FAILED: {spec} (recorded; the sweep continues - addendum 78)")
        except Exception as e:  # isolation is the point
            failed_families.append((spec, repr(e)))
            stamp(f"FAMILY FAILED: {spec} - {e!r} (recorded; the sweep continues - addendum 78)")
    return failed_families


def preflight_report(
    args: argparse.Namespace, state: dict[str, Any], failed_families: list[tuple[str, str]]
) -> None:
    """The --dry-run read-only report (addendum 79) + estimate (83)."""
    if args.dry_run:
        print()
        print("=" * 60)
        stamp("DRY RUN COMPLETE - READ-ONLY PRE-FLIGHT REPORT")
        print(f"  families checked : {len(args.families)}")
        print(f"  rung             : {RUNG} (fixed; the rung walk is removed - addendum 86)")
        # Addendum 83: the run-time estimate. Per-cell costs from the
        # run-1 measurement (the qwen overnight sweep, ~8.5 h for 7
        # cells, acquisition-dominated), split by acquisition-plan
        # class. Pre-registered brackets, converted to measurements as
        # sweep 2's stamps land.
        plan_counts, total_min = estimate_runtime(state)
        if plan_counts:
            print("  run-time estimate (run-1 brackets by acquisition class):")
            for cls in ("local", "download", "f16_quantize", "convert_quantize", "unknown"):
                if cls in plan_counts:
                    print(
                        f"    {cls:16s} x{plan_counts[cls]:2d} "
                        f"@ ~{PLAN_COST_MIN[cls]} min = "
                        f"{plan_counts[cls] * PLAN_COST_MIN[cls]:4d} min"
                    )
            lo = round(total_min / 60)
            hi = round(total_min * 1.3 / 60)
            print(
                f"    TOTAL: ~{lo}-{hi} h for {len(args.families)} "
                "families (bench 267 turns + ARC 1172 per cell; "
                "acquisition dominates)"
            )
        if failed_families:
            print(
                f"  FAILED families  : {len(failed_families)} of "
                f"{len(args.families)} - fix these BEFORE the real "
                f"run (the sweep would skip them):"
            )
            for spec, err in failed_families:
                print(f"    {spec}: {err}")
        else:
            print(
                "  failures         : none - every family's plan "
                "verified (repos exist, sizes estimated, "
                "RAM/disk feasible)"
            )
        print()
        print("  The state file was NOT modified and no files were downloaded (addendum 79).")
        print("  If the report is clean, issue the SAME command without")
        print("  --dry-run to start the real run.")
        return


def prepare_phase56(
    args: argparse.Namespace, state: dict[str, Any]
) -> tuple[list[str], dict[str, dict[str, Any]], list[tuple[str, str, dict[str, Any]]]]:
    """Roster, selections, and the ARC job list (addendum 86)."""
    # ---- phases 5-6: full ARC on selected models, then the ranking
    roster = (
        [f.strip() for f in args.roster.split(",")]
        if args.roster
        else [os.path.basename(s.partition("=")[0].rstrip("/")) for s in args.families]
    )
    selections = {}
    for fam, fst in state["families"].items():
        if roster is not None and fam not in roster:
            continue
        if fst.get("selected") and fst["runs"][fst["selected"]].get("file"):
            selections[fam] = fst["runs"][fst["selected"]]
    arc_jobs = collect_arc_jobs(state, roster)
    return roster, selections, arc_jobs


def report_roster_notes(
    args: argparse.Namespace,
    state: dict[str, Any],
    roster: list[str],
    failed_families: list[tuple[str, str]],
) -> None:
    """The roster missing-note and the failed-families note."""
    if roster is not None:
        missing = [
            f
            for f in roster
            if f not in state.get("families", {}) or not state["families"][f].get("selected")
        ]
        if missing:
            print(
                f"  note: roster families without a selection "
                f"(excluded from the ranking): {', '.join(missing)}"
            )
    if failed_families:
        print()
        stamp("families failed this run (isolated; state preserved):")
        for spec, err in failed_families:
            print(f"  {spec}: {err}")


def run_arc_phase(
    args: argparse.Namespace,
    state: dict[str, Any],
    arc_jobs: list[tuple[str, str, dict[str, Any]]],
) -> None:
    """Phase 5: full ARC on every benched model (addendum 86)."""
    if arc_jobs:
        print()
        print("=" * 60)
        stamp(
            f"PHASE 5: full {args.arc_config} on every benched model "
            f"({len(arc_jobs)} family rung(s), {args.arc_num} "
            "questions each - addendum 86: ARC always, the only skip "
            "is an already-complete CSV)"
        )
        questions = load_questions(args.arc_config, args.arc_num)
        for fam, rung, run in arc_jobs:
            label = f"{fam} {rung}"

            def on_scored(lbl, score, _state=state, _sp=args.state_file):
                _state.setdefault("arc", {})[lbl] = {
                    "csv": arc_csv_path(args.arc_results_dir, lbl),
                    "score": score,
                }
                save_state(_sp, _state)

            try:
                arc_eval.arc_run(
                    label,
                    run["file"],
                    questions,
                    args.arc_num,
                    args.arc_results_dir,
                    on_scored,
                    False,
                )
                stamp(f"ARC done: {label}")
            except SystemExit as e:
                stamp(f"ARC FAILED: {label} ({e}; recorded; the sweep continues - addendum 78)")
            except Exception as e:
                stamp(f"ARC FAILED: {label} - {e!r} (recorded; the sweep continues - addendum 78)")
    else:
        print("\nno benched family rungs yet - skipping ARC phase")


def run_ranking(
    args: argparse.Namespace,
    state: dict[str, Any],
    selections: dict[str, dict[str, Any]],
) -> None:
    """Phase 6: exact-McNemar ranking over the SELECTED models."""
    # ---- phase 6: the McNemar ranking over the SELECTED models
    rank_labels = [f"{fam} {state['families'][fam]['selected']}" for fam in selections]
    if rank_labels:
        print()
        stamp(f"PHASE 6: exact-McNemar ranking of the selected models ({len(rank_labels)})")
        try:
            ranking, scores, pairs = mcnemar.rank(rank_labels, args.arc_num, args.arc_results_dir)
            state["ranking"] = {
                "arc_num": args.arc_num,
                "scores": {m: scores[m] for m in ranking},
                "order": ranking,
                "pairs": pairs,
            }
            save_state(args.state_file, state)
        except SystemExit as e:
            stamp(f"RANKING FAILED ({e}; recorded; the sweep continues)")
        except Exception as e:
            stamp(f"RANKING FAILED - {e!r} (recorded; the sweep continues)")
    else:
        print("\nno family has a selection yet - skipping the ranking")


def write_results(args: argparse.Namespace, state: dict[str, Any]) -> None:
    """The results file: everything for later analysis."""
    # ---- results file: everything for later analysis
    results = []
    for fam, fst in state["families"].items():
        history = [dict(r, rung=rung) for rung, r in fst["runs"].items()]
        history.sort(key=lambda r: r["rung"])
        sel = fst["selected"]
        results.append(
            {
                "family": fam,
                "spec": fst["spec"],
                "history": history,
                "selected": (dict(fst["runs"][sel], rung=sel) if sel else None),
            }
        )
    doc = {"selection": results, "arc": state.get("arc", {}), "ranking": state.get("ranking")}
    with open(args.results_file, "w") as f:
        json.dump(doc, f, indent=1)
    print(f"\nresume state -> {args.state_file}")
    print(f"all data     -> {args.results_file}")


def print_wt_table(state: dict[str, Any]) -> None:
    """The per-model w/t calibration table (addendum 78, item 4)."""
    # ---- addendum 78, item 4: the per-model w/t calibration inline
    # (the addendum-74 lesson: grading waited on a manual extraction).
    # Single-sourced from speed_gate.analyze's own fields, already in
    # the state - no dump re-parsing, no second extraction pass.
    print()
    print("=" * 60)
    stamp("per-model w/t calibration (the gate's own p05 rule)")
    for fam, fst in state["families"].items():
        for rung, run in fst.get("runs", {}).items():
            if run.get("words_per_token_p05") is None:
                continue
            print(
                f"  {fam:36s} {rung:6s} "
                f"n={run.get('n_turns', 0):4d} "
                f"min={run.get('words_per_token_min') or 0:.3f} "
                f"p05={run['words_per_token_p05']:.3f} "
                f"mean={run.get('words_per_token') or 0:.3f}"
            )


# =========================================================== git tail


def git_tail(args: argparse.Namespace) -> None:
    stamp("committing artifacts to git (state, results, dumps, mem sidecars, ARC CSVs)")
    paths = [args.state_file, args.results_file]
    # per-turn dumps + mem sidecars: the grading instrument's raw data
    # (p05, Delta, stall attribution, gen_words, memory shape) - small
    # JSON, force-added past the models/ ignore (addendum 78).
    paths += (
        glob.glob("models/*/*.live-dump*.json")
        + glob.glob("models/*/*.sentinel*.json")
        + glob.glob("models/*/*.mem.json")
    )
    if os.path.isdir(args.arc_results_dir):
        paths.append(args.arc_results_dir)
    existing = [p for p in paths if os.path.exists(p)]
    if not existing:
        stamp("nothing to commit - no artifacts found")
        return
    r = subprocess.run(["git", "add", "-f", "--"] + existing, capture_output=True, text=True)
    if r.returncode != 0:
        stamp(f"git add failed: {r.stderr.strip()}")
        return
    r = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if r.returncode == 0:
        stamp("nothing new to commit")
        return
    msg = (
        f"benchmark artifacts {time.strftime('%Y-%m-%d %H:%M')} "
        "(addendum 78 auto-commit): state, results, per-turn dumps, "
        "mem sidecars, ARC CSVs"
    )
    r = subprocess.run(["git", "commit", "-m", msg], capture_output=True, text=True)
    if r.returncode != 0:
        stamp(f"commit failed: {r.stderr.strip()}")
        return
    stamp(f"committed: {r.stdout.strip().splitlines()[0]}")
    r = subprocess.run(["git", "push"], capture_output=True, text=True)
    if r.returncode != 0:
        stamp(f"push failed: {r.stderr.strip()} - run: git push")
    else:
        stamp("pushed")


if __name__ == "__main__":
    main()
