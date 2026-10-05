#!/usr/bin/env python3
"""full_benchmark.py -- the end-to-end benchmark orchestrator.

One command: acquire each family's GGUF at the rung (default Q8_0, --rung
overrides; addendum 86 removed the WALK, not the choice of rung),
then run the PROTOCOL v4 ladder (speed gate + FWE per rung, addendum 4)
and print the depth-scored ladder table - the study's ranking. This
script owns the orchestration only - state/resume and the final results
file. Each stage lives in its own dedicated script:

  hf_download.py  every Hugging Face interaction - premade rung file,
                  f16 GGUF, or safetensors snapshot.
  convert_quant.py  everything that touches llama.cpp conversion tooling
                  - safetensors -> f16, f16 -> rung.
  speed_gate.py   the speed gate - the llama-server bench interface,
                  dumps, and the protocol v3.1 stall-rate verdict.
  ruler_gate.py   the FWE (frequent-words-extraction) cell.

  STAGE A (phases 1-4, per family, fixed Q8_0 rung):
    1. DOWNLOAD - premade rung file or the data to create it later.
    2. CREATE   - convert safetensors -> f16, quantize f16 -> rung.
    3. LADDER   - protocol v4: gallop 2x from the min rung, then binary
                  search to 1024-token resolution (speed gate + FWE at
                  every rung, the ceiling matrix 3.1/3.2/3.3, window
                  from the launch banners).
    4. SCORE    - the scored-rung row (worst-turn w/s + cold cost).

Everything is IDEMPOTENT and RESUMABLE: the state file is rewritten
after every phase; rerun the same command to resume. Files are never
re-downloaded/re-quantized. Every failure stops the script with reader
guidance.

ARC is RETIRED (session 34, addendum 22: the FWE ladder "demolishes arc
as a measurement" - the depth score is the ranking; arc_eval.py and
mcnemar.py are removed with it).

Hybrid non-thinking mode (--no-thinking): for hybrid models in the
non-thinking category - benchmarks with thinking disabled
(chat_template_kwargs enable_thinking=false).
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import signal
import subprocess
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import convert_quant
import hf_download
import llama_server
import speed_gate
import tee_output

# session 34 (addendum 32): the ladder floor is 4096 - the corpus's
# structural floor (the worst conversation's side is ~2,670 tokens +
# depth headroom + the noise reserve: 2048 cannot host it even
# blob-less, so below 4096 the speed gate measures nothing, it just
# fences - the 1k-grid HTTP 400s were exactly this)
RUNG_BASE = 4096
MIN_RUNG_FAIL = 16384  # session 34 (addendum 19): a floor below the start
# rung means a base failure - the model is out, pending investigation


# session 39, addendum 15: the bench/ package holds the extracted
# concerns; this file remains the CLI + orchestration only.
from bench import cells as _cells  # noqa: E402
from bench import certify as _certify  # noqa: E402
from bench import ladder as _ladder  # noqa: E402
from bench import size_table as _size_table  # noqa: E402
from bench import state_store as _state_store  # noqa: E402
from bench import tournament as _tournament  # noqa: E402

# re-exports: the tests and the notebook-era scripts patch these seams
fwe_pass = _cells.fwe_pass
vt_pass = _cells.vt_pass
speed_pass = _cells.speed_pass
speed_cell = _cells.speed_cell
kill_stale_server = _cells.kill_stale_server
_banner_window = _cells._banner_window
RUNG_BASE = _cells.RUNG_BASE
MIN_RUNG_FAIL = _cells.MIN_RUNG_FAIL
RUNG_MIDPOINT = _cells.RUNG_MIDPOINT
COMBINED_TASKS = _state_store.COMBINED_TASKS
ARC_CELL_K = _state_store.ARC_CELL_K
ARC_RUN_CTX = _state_store.ARC_RUN_CTX
_task_load = _state_store._task_load
_task_store = _state_store._task_store
arc_pass = _state_store.arc_pass
arc_cells = _state_store.arc_cells
arc_cell_questions = _state_store.arc_cell_questions
speed_cells = _state_store.speed_cells
vt_cells = _state_store.vt_cells
certify_cells = _state_store.certify_cells
wilson_interval = _certify.wilson_interval
CERTIFY_LEVELS = _certify.CERTIFY_LEVELS
certify_rung = _certify.certify_rung
certify_rung_combined = _certify.certify_rung_combined
TASK_PASS_BARS = _certify.TASK_PASS_BARS
combined_medal = _certify.combined_medal
fwe_flicker = _tournament.fwe_flicker
tournament_rank = _tournament.tournament_rank
tournament_family = _tournament.tournament_family
rescore_tournament = _tournament.rescore_tournament
print_tournament_table = _tournament.print_tournament_table
run_ladder = _ladder.run_ladder
scored_row = _ladder.scored_row
build_size_table = _size_table.build_size_table
print_size_table = _size_table.print_size_table


def diagnose_fwe(models_dir: str, state: dict[str, Any]) -> None:
    """Session 37, addendum 9: the per-rank diagnostic - which of the
    three expected words does a partial pass actually find? Reads the
    climb cell CSVs (task rows carry the answer text and the rank-
    ordered top_k list; the zeta law makes rank 1 the ~4x/9x more
    frequent word, so a 1/3 pass that only ever finds rank 1 is a
    WEAKER claim than the threshold suggests). Also reports the pass
    rate at every threshold (>=1, >=2, 3 of 3) per family per rung:
    measure once, grade later."""
    import re as _re

    print("=" * 60)
    stamp("FWE DIAGNOSTIC (per-rank found; pass rates by threshold)")
    for fam, _fst in sorted((state.get("families") or {}).items()):
        results_dir = os.path.join(models_dir, "tournament-results", fam)
        if not os.path.isdir(results_dir):
            continue
        rank_found = [0, 0, 0]
        partials = [0, 0, 0, 0]
        cells = 0
        for climb_dir in sorted(os.listdir(results_dir)):
            cpath = os.path.join(results_dir, climb_dir)
            if not os.path.isdir(cpath) or not climb_dir.startswith("climb"):
                continue
            for name in os.listdir(cpath):
                if not name.endswith("-fwe.csv"):
                    continue
                with open(os.path.join(cpath, name), encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        ans = r.get("answer") or ""
                        top_k = (r.get("top_k") or "").split(";")
                        if not ans or not top_k or ans.startswith("ERROR"):
                            continue
                        clean = _re.sub(r"\s+", "", ans)
                        found = [i for i, w in enumerate(top_k) if w and w in clean]
                        cells += 1
                        partials[min(len(found), 3)] += 1
                        for i in found:
                            rank_found[i] += 1
        if not cells:
            continue
        print(f"  {fam}: {cells} cells (climb CSVs)")
        for i, c in enumerate(rank_found):
            print(f"    rank-{i + 1} word found in {c}/{cells} cells ({c / cells:.0%})")
        p1 = partials[1] + partials[2] + partials[3]
        p2 = partials[2] + partials[3]
        p3 = partials[3]
        print(
            f"    pass >=1/3: {p1}/{cells} ({p1 / cells:.0%}) | "
            f">=2/3: {p2}/{cells} ({p2 / cells:.0%}) | "
            f"3/3: {p3}/{cells} ({p3 / cells:.0%})"
        )
        if p1 and rank_found[0] / max(1, rank_found[0] + rank_found[1] + rank_found[2]) > 0.7:
            print(
                "    NOTE: found-words are overwhelmingly rank-1 - "
                "the >=1/3 claim is mostly 'finds the most frequent word'"
            )


QUANTIZE_BIN = convert_quant.QUANTIZE_BIN
CORPUS_DEFAULT = speed_gate.CORPUS_DEFAULT
MODELS_DIR_DEFAULT = "./models"
STATE_FILE_DEFAULT = "./state/benchmark-state.json"
RESULTS_FILE_DEFAULT = "./benchmark-results.json"
# Q4_0 removed (author ruling, addendum 37): Q4_K_M is the single 4-bit
# rung - "there's a q4_0 that's unnecessary since we have q4_k_m".
# Addendum 86: the rung WALK is removed - one rung per run.
# The study's default rung stays Q8_0; --rung overrides it (session
# 34: the Q4 quants - context dominates this bw class, so the smaller
# file with the deeper ladder is the hypothesis to test).
RUNG_DEFAULT = "Q8_0"

# The tournament grid and climb count (session 36, addenda 10/11): a
# dyadic ladder from 4,096 to the 262,144 ceiling, five climbs per
# family, SEED = CLIMB NUMBER (1..5) so every competitor faces the
# same five task ladders. Upstream RULER FWE parameters exactly
# (k=3, alpha 2.0 - addendum 7/8 verification).
TOURNAMENT_DEPTHS = [4096, 8192, 16384, 32768, 65536, 131072, 262144]
TOURNAMENT_CLIMBS = 21
TOURNAMENT_MODEL_QUANTS = ["Q2_K", "Q3_K", "Q4_K", "Q5_K", "Q6_K", "Q8_0"]
TOURNAMENT_KV_QUANTS = ["q4_0", "q5_0", "q6_K", "q8_0", "f16"]
READER_WPS_DEFAULT = speed_gate.READER_WPS_DEFAULT
SERVER_BIN = llama_server.find_server()

local_rung = hf_download.local_rung
list_repo_files = hf_download.list_repo_files
GUIDE = {}
GUIDE[1] = hf_download.GUIDE[1]
GUIDE[2] = convert_quant.GUIDE[2]
GUIDE[3] = speed_gate.GUIDE[3]
GUIDE[4] = speed_gate.GUIDE[4]
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
    rung: str = RUNG_DEFAULT,
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
        # worst is None for a floor-rule-failed family (score 0 has no
        # scored rung) - the resume print must not format it (the
        # lineage-2 run's TypeError, addendum 27)
        worst_txt = "n/a" if s.get("worst") is None else f"{s['worst']:.1f}"
        print(
            f"  already selected: {fst['selected']} "
            f"({s['verdict']}, worst {worst_txt} t/s) - skipping "
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
        print(f"  --force: re-benching {rung} ({cleared} stored verdict(s) cleared; files reused)")

    # Stale-state guard (addendum 43): a stored rung file can vanish
    # from disk (folder deleted/moved) while state/benchmark-state.json still
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

    # Session 34 (addendum 4): the LOCAL SHORTCUT. If the rung file is
    # already on disk, acquisition is DONE - no hub listing needed (the
    # author's models/ tree is the common case; the v4 WoW runs local
    # files). The hub is only a real dependency when the file must be
    # downloaded or converted.
    local_path = local_rung(famdir, rung)
    if local_path and 1 not in (fst["runs"].get(rung, {}).get("phases_done", [])):
        run = fst["runs"].setdefault(rung, {"phases_done": []})
        run["plan"] = "local file"
        run["file"] = local_path
        if 1 not in run["phases_done"]:
            run["phases_done"].append(1)
        if 2 not in run["phases_done"]:
            run["phases_done"].append(2)
        save_state(state_path, state)
        print(f"  [1] local rung file found - no download needed  ({local_path})")
        print(f"  [2] rung file ready  ({local_path})")
    model_files: list[str] = []
    source_files: list[str] = []
    if not local_path:
        hf_download.require_hub()
        assert list_repo_files is not None  # require_hub exits when the hub is missing
        try:
            model_files = list_repo_files(model_repo)
            source_files = (
                model_files if source_repo == model_repo else list_repo_files(source_repo)
            )
        except Exception as e:
            fail(1, "-", f"cannot list repo files for {model_repo}: {e}", GUIDE[1])

    run = fst["runs"].get(rung, {"phases_done": []})
    fst["runs"][rung] = run
    if str(run.get("verdict", "")).startswith("PASS") or run.get("verdict") == "FAIL":
        return
    print(f"\n  rung {rung}:")
    if 1 not in run["phases_done"]:
        path, plan = hf_download.acquire(
            fam, famdir, rung, model_repo, model_files, source_repo, source_files, dry_run
        )
        run["plan"] = plan
        run["phases_done"].append(1)
        save_state(state_path, state)
        print(f"  [1] downloads ok  (plan: {plan})")
        stamp("      phase 1 done (acquire)")
        if plan.startswith("infeasible"):
            run["verdict"] = "FAIL (infeasible: exceeds system RAM)"
            run["rung"] = rung
            save_state(state_path, state)
            return
    if 2 not in run["phases_done"]:
        path = convert_quant.create(fam, famdir, rung, run.get("plan", ""), dry_run)
        if path:
            run["file"] = path
        run["phases_done"].append(2)
        save_state(state_path, state)
        print(f"  [2] rung file ready  ({run.get('file', 'dry run')})")
        stamp("      phase 2 done (create)")
    path = run.get("file") or local_rung(famdir, rung)
    if dry_run:
        print(f"  [3] would run the PROTOCOL v4 ladder on {path or 'the rung file'}")
        print(
            "  [4] would record the ladder score (the deepest rung passing both; "
            "scored-rung w/s + cold cost per addendum 137n/137m)"
        )
        return
    assert path is not None  # real runs: phases 1-2 guarantee it
    # Session 34 (addendum 4): the 50-conv corpus wall is REPLACED
    # by the PROTOCOL v4 ladder as the family's bench. Per rung:
    # speed gate (n=1) then FWE (n=1); both pass -> score advances;
    # either fails -> the ladder stops. The verdict is the ladder
    # SCORE (0 = the counting floor / speed cliff at the base
    # rung). The corpus-wall phases 3-4 are retired (the author:
    # "we don't do 50 conv turns. We do run fwe as in ladder-bench").
    if 3 not in run["phases_done"] or force:
        ladder = run_ladder(
            path,
            corpus,
            port=state.get("ladder_port", 8210),
            results_dir=os.path.join(models_dir, "ladder-results"),
            seed=state.get("ladder_seed", 1024),
            min_rung=state.get("ladder_min_rung", RUNG_BASE),
            max_rung=state.get("ladder_max_rung"),
            kv_quant_k=state.get("kv_quant_k"),
            kv_quant_v=state.get("kv_quant_v"),
        )
        run["ladder"] = ladder
        run["phases_done"].append(3)
        save_state(state_path, state)
        print(f"  [3] ladder ok  (score: {ladder['score']} tokens)")
        stamp("      phase 3 done (ladder)")
    if 4 not in run["phases_done"]:
        # phase 4: the scored-rung row (the 137n/137m anchors)
        ladder = run.get("ladder")
        if ladder and ladder.get("invalid"):
            # the flicker rule (addendum 31): a non-monotone FWE run
            # scores NOTHING - the verdict is invalid, not a depth
            run["verdict"] = f"INVALID ({ladder.get('invalid_reason', 'fwe flicker')})"
            run["rung"] = rung
            run["score"] = 0
            run["invalid"] = True
            run["invalid_reason"] = ladder.get("invalid_reason")
            run["phases_done"].append(4)
            save_state(state_path, state)
            stamp("      phase 4 done (invalid - flicker)")
            return
        if ladder and ladder.get("launch_failed"):
            # session 35, addendum 7: a launch failure is not a score -
            # the family stays UNSELECTED (the false-zero bug: the
            # crashed witness runs recorded "PASS (ladder score 0)" and
            # the resume skipped the family)
            run["verdict"] = (
                "FAIL (server launch failed - bad flags/build or load-time "
                "crash; fix the launch and re-run with --force)"
            )
            run["rung"] = rung
            run["score"] = 0
            run["launch_failed"] = True
            run["phases_done"].append(4)
            save_state(state_path, state)
            stamp("      phase 4 done (launch failed - not selectable)")
            return
        if ladder:
            row = scored_row(ladder)
            run["verdict"] = f"PASS (ladder score {ladder['score']} tokens)"
            run["rung"] = rung
            run["score"] = ladder["score"]
            run["worst"] = row["worst_wps"]
            run["mem_cost_gib"] = row["cold_cost_gib"]
            run["phases_done"].append(4)
            save_state(state_path, state)
            worst_txt = "n/a" if row["worst_wps"] is None else f"{row['worst_wps']:.1f}"
            cost_txt = "n/a" if row["cold_cost_gib"] is None else f"{row['cold_cost_gib']:.2f}"
            print(
                f"  [4] scored-rung row: depth {row['depth']} tokens, "
                f"worst {worst_txt} w/s, cold cost {cost_txt} GiB"
            )
            stamp("      phase 4 done (scored row)")
    if str(run.get("verdict", "")).startswith("PASS"):
        fst["selected"] = rung
        run["rung"] = rung
        save_state(state_path, state)
        print(f"  SELECTED {rung} for {fam} (ladder score {run.get('score')} tokens)")


# =========================================================== main


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="end-to-end benchmark: acquire each family's Q8_0 "
        "rung and run the protocol v4 ladder - the depth-scored "
        "ladder table is the ranking"
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
        "--rung",
        default=RUNG_DEFAULT,
        help="the quant to benchmark (default Q8_0; e.g. Q4_K_M - session 34's "
        "context-over-parameters test)",
    )
    ap.add_argument(
        "--roster",
        default=None,
        help="restrict the run's notes to these families "
        "(comma-separated, as named in the family specs); "
        "the state file accumulates across studies "
        "(addendum 41/56)",
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
        "--tournament",
        action="store_true",
        help="session 36, addenda 10/11: run the TOURNAMENT instead of the "
        "ladder sweep - every family at its SELECTED rung (the PASS "
        "config, its stored KV quants), five climbs of the dyadic FWE "
        "ladder 4096..262144, SEED = CLIMB NUMBER, early stop at the "
        "first non-perfect cell; the sigma rank (reliable/conservative depths) is the ranking",
    )
    ap.add_argument(
        "--rescore",
        action="store_true",
        help="session 37, addendum 4: re-derive every saved climb's fall "
        "from the raw per-cell CSVs under the relaxed 1/3 criterion "
        "(addendum 2) instead of running the tournament. Read-only by "
        "default; --rescore-apply rewrites tournament_falls (a climb "
        "whose recorded fall is now a pass chain is DROPPED so the next "
        "--tournament re-runs it under 1/3)",
    )
    ap.add_argument(
        "--rescore-apply",
        action="store_true",
        help="with --rescore: write the re-scored falls to the state file",
    )
    ap.add_argument(
        "--size-table",
        action="store_true",
        help="session 39, addendum 16: print the per-context recommendation "
        "table (family x rung) from the committed -lv 5 memory censuses "
        "and speed dumps - the flat 5 GiB ceiling becomes a curve; the "
        "speed gate is the size authority. Read-only",
    )
    ap.add_argument(
        "--diagnose",
        action="store_true",
        help="session 37, addendum 9: read the climb cell CSVs and report "
        "the per-rank diagnostic (which of the 3 expected words a "
        "partial pass found) and the pass rate at >=1/3, >=2/3, 3/3 "
        "per family - measure once, grade at any threshold later",
    )
    ap.add_argument(
        "--certify",
        choices=CERTIFY_LEVELS,
        default=None,
        metavar="LEVEL",
        help="session 37, addendum 18: certify the rungs given by "
        "--rungs sequentially - the most promising candidate is tested "
        "cell by cell (a cell is model x run x step, NEVER re-measured; "
        "historical climb cells are inherited) until it certifies or is "
        "mathematically dead; the first accepted model answers the rung; "
        "the rest are skipped. LEVEL is the certification type: "
        "at_least_one (any model with a pass at the step), 1_sigma "
        "(reliable: 1-sigma Wilson lower bound >= 0.5, n=21), 2_sigma "
        "(conservative: the same bar at 2 sigma)",
    )
    ap.add_argument(
        "--rungs",
        type=str,
        default=None,
        metavar="D1,D2,...",
        help="session 37, addendum 18: comma-separated rung(s) to "
        "certify (e.g. --rungs 32768,65536), processed "
        "cheapest-first (sorted ascending); required with --certify. "
        "State is saved after each rung, so each rung's answers feed "
        "the next rung's predictions - a range is just multiple "
        "commands concatenated, no JSON needed. Comma form keeps the "
        "positional families list parseable (addendum 19: argparse's "
        "nargs='+' swallowed the families as depths)",
    )
    ap.add_argument(
        "--fwe-min-words",
        type=int,
        default=1,
        metavar="N",
        help="session 37 (the 2/3 tightening): the FWE pass bar - a cell "
        "passes when >= N of the 3 hidden words are found (default 1, "
        "the addendum-2 relaxation). N=2 tightens gold certification to "
        "2-of-3. Cells that stored an integer word count are re-graded "
        "exactly at the new bar; cells stored as booleans or inherited "
        "from tournament falls were graded under the old 1/3 rule and are "
        "re-run, never silently trusted",
    )
    ap.add_argument(
        "--task",
        default="fwe",
        choices=["fwe", "vt", "speed", "all"],
        help="session 37 (the VT certification): with --certify, run the "
        "variable-tracking task instead of FWE - same stack, n=21, "
        "seeds and sequential controller, but a separate cell namespace "
        "(certify_vt - the FWE evidence is never touched), pass = ALL "
        "5 chain names, the 0..5 partial stored per cell as the graded "
        "diagnostic (the VT analogue of the FWE x/3 word count). "
        "session 38 (addendum 3): 'all' is the combined controller - "
        "each cell carries speed, fwe and vt, measured only if missing, "
        "three independent tallies, accept when all three clear, dead "
        "when any one dies",
    )
    _KV_CHOICES = ["q8_0", "q4_0", "q4_1", "q5_0", "q5_1", "iq4_nl"]
    ap.add_argument(
        "--kv-quant-k",
        default=None,
        choices=_KV_CHOICES,
        help="session 35, addendum 7: quantize ONLY the K cache to this type "
        "(V keeps its own setting; both None = default f16).",
    )
    ap.add_argument(
        "--kv-quant-v",
        default=None,
        choices=_KV_CHOICES,
        help="session 35, addendum 7: quantize ONLY the V cache to this type "
        "(K keeps its own setting; both None = default f16).",
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
        "--no-git",
        action="store_true",
        help="skip the git tail (session 34 addendum 15: the "
        "commit-and-push of the run's artifacts is now DEFAULT - "
        "the git interface is layer 3, like the hub and llama.cpp; "
        "the old --git-commit opt-in is superseded)",
    )
    ap.add_argument(
        "--min-rung",
        type=int,
        default=None,
        help="session 34 (addendum 9/10): the ladder's first rung "
        "(default: the protocol v4 base 8192); stored in the state "
        "as ladder_min_rung so every subsequent run of the family "
        "climbs the same grid",
    )
    ap.add_argument(
        "--max-rung",
        type=int,
        default=None,
        help="session 35 (addendum 9): the gallop's hard stop - the ladder "
        "never climbs past this rung. With --min-rung N --max-rung N the run "
        "is a single-rung probe: speed + fwe at exactly N, pass or fail, no "
        "search; stored in the state as ladder_max_rung",
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
    install_sigint_handler(args)

    if args.thinking and args.no_thinking:
        ap.error("--thinking and --no-thinking are mutually exclusive")

    if args.size_table:
        print_size_table(
            build_size_table(
                [
                    os.path.join(args.models_dir, "ladder-results"),
                    os.path.join(args.models_dir, "tournament-results"),
                ]
            )
        )
        return

    check_requirements()
    git_pull_head()
    tee_output.install()
    if not args.dry_run:
        kill_stale_server()
        check_tooling(args)

    state = load_state(args.state_file)
    if args.min_rung:
        state["ladder_min_rung"] = args.min_rung
    if args.max_rung:
        state["ladder_max_rung"] = args.max_rung
    if args.kv_quant_k:
        state["kv_quant_k"] = args.kv_quant_k
    if args.kv_quant_v:
        state["kv_quant_v"] = args.kv_quant_v

    if not args.families:
        ap.error("no family specs given")
    if args.rescore:
        rescore_tournament(args.models_dir, state, args.state_file, not args.rescore_apply)
        return
    if args.diagnose:
        diagnose_fwe(args.models_dir, state)
        return
    if args.certify:
        if not args.rungs:
            ap.error("--certify needs --rungs D1,D2,...")
        try:
            rung_list = [int(x) for x in args.rungs.split(",") if x.strip()]
        except ValueError:
            ap.error(f"--rungs must be comma-separated integers, got {args.rungs!r}")
        if not rung_list:
            ap.error("--rungs needs at least one depth")
        all_results: list[dict[str, Any]] = []
        for depth in sorted(rung_list):
            if args.task == "all":
                results = certify_rung_combined(
                    depth,
                    args.certify,
                    args.families,
                    args.models_dir,
                    state,
                    args.state_file,
                    state.get("ladder_port", 8210),
                    args.dry_run,
                    min_words=args.fwe_min_words,
                )
            else:
                results = certify_rung(
                    depth,
                    args.certify,
                    args.families,
                    args.models_dir,
                    state,
                    args.state_file,
                    state.get("ladder_port", 8210),
                    args.dry_run,
                    min_words=args.fwe_min_words,
                    task=args.task,
                )
            state["certify"] = results
            save_state(args.state_file, state)
            print()
            print("=" * 60)
            stamp(f"CERTIFY {args.certify} {depth:,} SUMMARY")
            for r in results:
                v = r.get("verdict", r.get("error", r.get("skipped", "?")))
                extra = f" w/s median {r['wps_median']}" if r.get("wps_median") else ""
                print(
                    f"  {r['family']}: {v} ({r.get('passes', 0)}/"
                    f"{r.get('cells_measured', 0)} cells, ran {r.get('ran_now', 0)} now){extra}"
                )
            all_results.extend(results)
        # the gold-run lesson (2026-10-03): the certify branch returned
        # bare and skipped the git tail - the artifacts (results.txt,
        # state) never committed and had to be pushed by hand
        if not args.no_git:
            tee_output.uninstall()
            git_tail(args)
        return
    if args.tournament:
        tours = []
        for spec in args.families:
            try:
                tours.append(
                    tournament_family(
                        spec,
                        args.models_dir,
                        state,
                        args.state_file,
                        state.get("ladder_port", 8210),
                        args.dry_run,
                    )
                )
            except Exception as e:
                tours.append({"family": spec, "error": repr(e)})
                stamp(f"TOURNAMENT FAMILY FAILED: {spec} - {e!r} (isolated; recorded)")
        state["tournament"] = tours
        save_state(args.state_file, state)
        print_tournament_table(tours)
        # session 37, addendum 15: the reliable-depth w/s measurement
        # (addendum 42) is RETIRED - the RAM-ceiling assumption
        # replaces it (a config selected under the ceiling has the
        # bandwidth to clear the reader line); w/s is not measured in
        # the benchmark. The historical wps medians in state stay as
        # records of what was measured under the old protocol.
        if not args.no_git:
            tee_output.uninstall()
            git_tail(args)
        stamp("tournament complete")
        sys.exit(0)

    failed_families = sweep_families(args, state)

    # Session 34 (addendum 4): the ladder is the bench; the scored
    # table prints from the ladder results in state (ARC and the
    # McNemar ranking are retired - addendum 22).
    if args.dry_run:
        # session 34 (addendum 36): a dry run WRITES results.txt (the tee
        # is installed from the first line) - it must be committed and
        # pushed like a real run's, so the git tail runs before the exit
        if not args.no_git:
            tee_output.uninstall()  # stop writing before committing
            git_tail(args)
        sys.exit(preflight_report(args, state, failed_families))
    roster = prepare_roster(args)
    report_roster_notes(args, state, roster, failed_families)
    print_ladder_table(state)
    write_results(args, state)
    write_results(args, state)

    # ---- addendum 78, item 5 / session 34 addendum 15: the git tail -
    # commit and push every artifact the study needs, force-added past
    # the .gitignore. Now DEFAULT (the author: "do the git work in full
    # benchmark. layer 3 is the right place to have a git interface,
    # same as the hugging face interface and the llama-cpp interface");
    # --no-git opts out.
    if not args.no_git:
        tee_output.uninstall()  # results.txt is complete - stop writing before it is committed
        git_tail(args)
    stamp("run complete")


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
    """Verify every requirements.txt package the run needs is importable
    in THIS interpreter - the dry run included (the author: "I had to
    restart our latest run because I forgot to enable the venv"). The
    interpreter's own path is printed first so the wrong-venv (or
    system-python) case is visible at a glance; a missing package is a
    hard stop BEFORE any download or bench work begins."""
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
                args.rung,
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
) -> int:
    """The --dry-run read-only report (addendum 79) + estimate (83).
    Returns the process exit code: 1 iff any family failed (author
    ruling, addendum 108 - the pre-flight is a scriptable gate)."""
    if args.dry_run:
        print()
        print("=" * 60)
        stamp("DRY RUN COMPLETE - READ-ONLY PRE-FLIGHT REPORT")
        print(f"  families checked : {len(args.families)}")
        print(
            f"  rung             : {args.rung} (one rung per run - addendum 86; --rung overrides)"
        )
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
                "families (acquisition dominates; the v4 ladder "
                "cost scales with how deep each model climbs)"
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
        return 1 if failed_families else 0
    return 0


def prepare_roster(args: argparse.Namespace) -> list[str]:
    """The run's roster: the families named in this command (addendum 41/56)."""
    if args.roster:
        return [f.strip() for f in args.roster.split(",")]
    return [os.path.basename(s.partition("=")[0].rstrip("/")) for s in args.families]


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


def print_ladder_table(state: dict[str, Any]) -> None:
    """The v4 ladder table (session 34, addendum 4): every benched
    family's ladder score with its scored-rung row (the 137n/137m
    anchors), sorted by depth - the ranking output of the merged
    full benchmark."""
    rows = []
    for fam, fst in state["families"].items():
        for rung, run in fst.get("runs", {}).items():
            lad = run.get("ladder")
            if lad is None:
                continue
            row = scored_row(lad)
            rows.append(
                (
                    lad["score"] or 0,
                    fam,
                    rung,
                    row["worst_wps"],
                    row["cold_cost_gib"],
                    lad["wall_min"],
                    bool(lad.get("failed")),
                )
            )
    if not rows:
        print("\nno ladder results in state - nothing benched yet")
        return
    print()
    print("=" * 60)
    stamp("PROTOCOL v4 ladder table (depth score; n=1 screen - addendum 137h)")
    for score, fam, _rung, wps, cost, wall, failed in sorted(rows, key=lambda r: (-r[0], r[1])):
        wps_txt = "n/a" if wps is None else f"{wps:.1f}"
        cost_txt = "n/a" if cost is None else f"{cost:.2f}"
        flag = "  FAILED (below the start rung - investigate)" if failed else ""
        print(
            f"  {fam:36s} score {score:>7,} tokens | "
            f"scored-rung worst {wps_txt:>5s} w/s | cold {cost_txt:>5s} GiB | "
            f"{wall:.1f} min{flag}"
        )


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
    doc = {"selection": results}
    with open(args.results_file, "w") as f:
        json.dump(doc, f, indent=1)
    print(f"\nresume state -> {args.state_file}")
    print(f"all data     -> {args.results_file}")


# =========================================================== git tail


def git_pull_head() -> None:
    """The forgotten pull, made structural (session 36, addendum 32;
    wow.md section 6 - many errors come from missing steps like git
    pull). Runs BEFORE the state loads, so every run - real or dry -
    starts from the freshest state file and notebook the repo has:
    the author's artifact commits land on main between exchanges, and
    a stale checkout silently grades against old data. --no-git is
    the escape hatch (same as the tail); a failed pull is a HARD
    STOP, not a warning - running on a diverged tree measures the
    wrong thing with confidence."""
    if os.environ.get("BENCH_NO_GIT_PULL"):
        return
    r = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True
    )
    if r.returncode != 0 or r.stdout.strip() != "true":
        stamp("git pull skipped - not a git work tree")
        return
    r = subprocess.run(
        ["git", "pull", "--rebase", "--autostash", "--no-verify"], capture_output=True, text=True
    )
    if r.returncode != 0:
        stamp(f"git pull failed - FIX BEFORE RUNNING: {r.stderr.strip()[:200]}")
        raise SystemExit(1)
    out = r.stdout.strip()
    if out and "Already up to date" not in out:
        stamp(f"git pull: {out.splitlines()[0]}")
    else:
        stamp("git pull: already up to date")


def git_tail(args: argparse.Namespace) -> None:
    stamp("committing artifacts to git (state, results, dumps, mem sidecars)")
    paths = [args.state_file, args.results_file, "results.txt"]
    # per-turn dumps + mem sidecars: the grading instrument's raw data
    # (p05, Delta, stall attribution, gen_words, memory shape) - small
    # JSON, force-added past the models/ ignore (addendum 78).
    paths += (
        glob.glob("models/*/*.live-dump*.json")
        + glob.glob("models/*/*.sentinel*.json")
        + glob.glob("models/*/*.mem.json")
        # session 39, addendum 9: the per-model server logs (the -lv 5
        # accounting - arc cells, window probes, model-dir launches) -
        # the interrupted-run lesson: both Ctrl-Cs landed before the
        # tail, so the ONLY copies of llama's own memory accounting
        # sat uncommitted on the author's disk (prediction B needs
        # them; the SIGINT handler now runs the tail, but the glob
        # has to reach the logs first)
        + glob.glob("models/*/*.arc-cell*.log")
        + glob.glob("models/*/*-server.log")
        + glob.glob("models/*/*window-probe.log")
    )
    # wow.md section 9 lesson (2026-10-03): the tournament/certify cells
    # write their per-cell CSVs (with the `partial` word counts) to
    # models/tournament-results/ (one shared dir, per-family subdirs) -
    # a path this glob missed, so the certify runs' raw evidence never
    # committed and re-grading had to mine results.txt instead of the
    # state
    paths += glob.glob("models/tournament-results/**/*", recursive=True)
    # session 34 addendum 15: the ladder's raw data rides too - the
    # speed/fwe dumps and the window-probe logs (the addendum-6 cap's
    # evidence), plus the ruler CSVs.
    paths += (
        glob.glob("models/*/ladder-results/*")
        + glob.glob("ladder-results/*")
        + glob.glob("ruler-results/*")
    )
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
        "mem sidecars, ladder dumps"
    )
    r = subprocess.run(["git", "commit", "-m", msg], capture_output=True, text=True)
    if r.returncode != 0:
        stamp(f"commit failed: {r.stderr.strip()}")
        return
    stamp(f"committed: {r.stdout.strip().splitlines()[0]}")
    # addendum 47: the artifact push can race origin (rules land on
    # main DURING a long run - the addendum-46 lesson: stale data on
    # my side for hours). Pull-rebase-autostash AFTER the commit and
    # BEFORE the push, so the artifact commit replays on top of
    # whatever landed meanwhile; the autostash covers tree dirt.
    r = subprocess.run(["git", "pull", "--rebase", "--autostash"], capture_output=True, text=True)
    if r.returncode != 0:
        hint = "run: git pull --rebase --autostash; and git push"
        stamp(f"pull before push failed: {r.stderr.strip()} - {hint}")
    r = subprocess.run(["git", "push"], capture_output=True, text=True)
    if r.returncode != 0:
        stamp(f"push failed: {r.stderr.strip()} - run: git pull --rebase --autostash; and git push")
    else:
        stamp("pushed")


def sigint_shutdown(signum, frame, args=None):
    """Session 38, addendum 8: the author's Ctrl-C ruling - "when I
    interrupt a run with control-c it stops cleanly: stop llama-server,
    stop results logging, git commit and pull". The handler is
    installed AFTER arg parsing, so it always has args (state file,
    results file, --no-git). Dry runs skip the tail (nothing to
    commit that pre-flight didn't already plan to)."""
    stamp("SIGINT - shutting down cleanly (addendum 8)")
    r = subprocess.run(
        ["pkill", "-f", "llama-server"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    stamp("llama-server stopped" if r.returncode == 0 else "no llama-server to stop")
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
    sys.exit(130)


def install_sigint_handler(args: argparse.Namespace) -> None:
    signal.signal(signal.SIGINT, lambda s, f: sigint_shutdown(s, f, args))


if __name__ == "__main__":
    main()
