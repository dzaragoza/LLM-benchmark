#!/usr/bin/env python3
"""full_benchmark.py -- the end-to-end benchmark orchestrator.

One command, four stages, one final output: the RANKING of the selected
models by strict ARC-Challenge score, with exact McNemar separation
tests on every consecutive rank gap. This script owns the orchestration
only - state/resume, the per-family ladder walk, and the final results
file. Each stage lives in its own dedicated script (split from this
file 2026-09-24; same protocol, same state, byte-identical behavior):

  hf_download.py  STAGE A phase 1: every Hugging Face interaction -
                  premade rung file, f16 GGUF, or safetensors snapshot.
  convert_quant.py STAGE A phase 2: everything that touches llama.cpp
                  conversion tooling - safetensors -> f16, f16 -> rung.
  speed_gate.py   STAGE A phases 3-4: the worst-turn speed gate - the
                  llama-server bench interface, mode-suffixed dumps,
                  verdict.
  arc_eval.py     STAGE B (phase 5): strict ARC-Challenge on every
                  selected model (raw protocol, logprob letter scoring).
  mcnemar.py      STAGE C (phase 6): pairwise exact McNemar; the final
                  ranking with separation verdicts.

  STAGE A (phases 1-4, per family, downward quant ladder):
    1. DOWNLOAD - premade rung file or the data to create it later.
    2. CREATE   - convert safetensors -> f16, quantize f16 -> rung.
    3. BENCH    - speed_gate.py, 1 rep, worst-turn metric.
    4. ANALYZE  - verdict: PASS if worst >= floor - 2*sigma (lenient
                  2-sigma ruling, 2026-09-23); first PASS = selected.
  STAGE B (phase 5): strict ARC-Challenge on every selected model
    (FULL test split, 1172 questions; logprob letter scoring,
    temperature 0; per-question CSVs in --arc-results-dir).
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

Ad-hoc use (no selection stage): rank arbitrary model files directly:
    python3 full_benchmark.py --arc-only \\
        --arc-models "./models/A/q8.gguf,./models/B/q6.gguf"

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

import argparse
import json
import os
import sys

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
LADDER_DEFAULT = ["Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M", "Q2_K"]
FLOOR_DEFAULT = speed_gate.FLOOR_DEFAULT
READER_TP_DEFAULT = speed_gate.READER_TPS_DEFAULT
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


# =========================================================== state

def load_state(path):
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return {"families": {}}


def save_state(path, state):
    with open(path, "w") as f:
        json.dump(state, f, indent=1)


# =========================================================== selection

def process_family(spec, ladder, corpus, floor, models_dir, state,
                   state_path, dry_run, force, thinking=False,
                   no_thinking=False, reader_tp=READER_TP_DEFAULT):
    model_repo, _, source_repo = spec.partition("=")
    if not source_repo:
        source_repo = model_repo
    fam = os.path.basename(model_repo.rstrip("/"))
    famdir = os.path.join(models_dir, fam)
    fst = state["families"].setdefault(
        fam, {"spec": spec, "runs": {}, "selected": None})

    print()
    print("=" * 60)
    print(f"family: {fam}")
    print(f"  model repo : {model_repo}")
    print(f"  source repo: {source_repo}")
    print(f"  folder     : {famdir}")
    if fst["selected"] and not force:
        s = fst["runs"][fst["selected"]]
        print(f"  already selected: {fst['selected']} "
              f"({s['verdict']}, worst {s['worst']:.1f} t/s) - skipping "
              "(--force to redo)")
        return

    hf_download.require_hub()
    try:
        model_files = list_repo_files(model_repo)
        source_files = (model_files if source_repo == model_repo
                        else list_repo_files(source_repo))
    except Exception as e:
        fail(1, "-", f"cannot list repo files for {model_repo}: {e}", GUIDE[1])

    for rung in ladder:
        run = fst["runs"].get(rung, {"phases_done": []})
        fst["runs"][rung] = run
        if str(run.get("verdict", "")).startswith("PASS"):
            break
        if run.get("verdict") == "FAIL":
            continue
        print(f"\n  rung {rung}:")
        if 1 not in run["phases_done"]:
            path, plan = hf_download.acquire(fam, famdir, rung, model_repo,
                                             model_files, source_repo,
                                             source_files, dry_run)
            run["plan"] = plan
            run["phases_done"].append(1)
            save_state(state_path, state)
            print(f"  [1] downloads ok  (plan: {plan})")
        if 2 not in run["phases_done"]:
            path = convert_quant.create(fam, famdir, rung,
                                        run.get("plan", ""), dry_run)
            if path:
                run["file"] = path
            run["phases_done"].append(2)
            save_state(state_path, state)
            print(f"  [2] rung file ready  ({run.get('file', 'dry run')})")
        path = run.get("file") or local_rung(famdir, rung)
        if dry_run and not path:
            print(f"  [3] would live-bench the {rung} file")
            print(f"  [4] would analyze (reader line {reader_tp:g} "
                  f"- 2*sigma; floor {floor:g} as headroom)")
            continue
        if 3 not in run["phases_done"]:
            dump = speed_gate.bench(path, corpus, dry_run, thinking,
                                    no_thinking)
            run["phases_done"].append(3)
            save_state(state_path, state)
            print(f"  [3] live bench ok  (dump: {os.path.basename(dump)})")
        if 4 not in run["phases_done"]:
            res = speed_gate.analyze(path, floor, thinking, no_thinking,
                                     reader_tp=reader_tp)
            run.update(res)
            run["phases_done"].append(4)
            save_state(state_path, state)
            print(f"  [4] worst {res['worst']:.1f} t/s "
                  f"(mean {res['mean']:.1f}, sigma {res['sigma']:.2f}, "
                  f"guarantee threshold {res['threshold']:.1f}) "
                  f"-> {res['verdict']}")
            print(f"      headroom vs floor {floor:g}: {res['headroom']}")
        if str(run["verdict"]).startswith("PASS"):
            fst["selected"] = rung
            run["rung"] = rung
            save_state(state_path, state)
            print(f"  SELECTED {rung} for {fam}")
            break


# =========================================================== main

def main():
    ap = argparse.ArgumentParser(
        description="end-to-end benchmark: quant selection, strict full "
                    "ARC, exact-McNemar ranking - one final output")
    ap.add_argument("families", nargs="*",
                    help='family specs: "model_repo" or '
                         '"model_repo=source_repo" (skip for --arc-only)')
    ap.add_argument("--corpus", default=CORPUS_DEFAULT)
    ap.add_argument("--floor", type=float, default=FLOOR_DEFAULT,
                    help="the k=3 headroom line (t/s), reported not "
                         "gated (protocol v2)")
    ap.add_argument("--reader-tp", type=float, default=READER_TP_DEFAULT,
                    help="the k=1 guarantee line: worst turn at the "
                         "reference depth must never fall below this "
                         "(default 6.5 = 300 wpm at 0.75 words/token)")
    ap.add_argument("--ladder", default=",".join(LADDER_DEFAULT))
    ap.add_argument("--models-dir", default=MODELS_DIR_DEFAULT)
    ap.add_argument("--state-file", default=STATE_FILE_DEFAULT)
    ap.add_argument("--results-file", default=RESULTS_FILE_DEFAULT)
    ap.add_argument("--arc-num", type=int, default=ARC_NUM_DEFAULT,
                    help="ARC-Challenge questions (default: full 1172)")
    ap.add_argument("--arc-results-dir", default=ARC_RESULTS_DIR_DEFAULT)
    ap.add_argument("--arc-config", default="ARC-Challenge",
                    choices=["ARC-Challenge", "ARC-Easy"])
    ap.add_argument("--arc-only", action="store_true",
                    help="skip selection; ARC + rank only")
    ap.add_argument("--arc-models", default=None,
                    help="comma-separated .gguf files to ARC and rank "
                         "(with --arc-only); labels from filenames")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="redo families that already have a selection")
    ap.add_argument("--thinking", action="store_true",
                    help="thinking-model category: benchmark with "
                         "thinking enabled (same worst-turn gate; "
                         "reasoning measured descriptively). Use separate "
                         "--state-file/--results-file for this category.")
    ap.add_argument("--no-thinking", action="store_true",
                    help="hybrid models, non-thinking category: "
                         "run with thinking disabled (chat-template "
                         "kwargs enable_thinking=false; first-turn dump "
                         "check confirms no reasoning appears)")
    args = ap.parse_args()

    if args.thinking and args.no_thinking:
        ap.error("--thinking and --no-thinking are mutually exclusive")

    ladder = [x.strip() for x in args.ladder.split(",") if x.strip()]

    if not args.dry_run:
        for path, msg in [
            (args.corpus, f"corpus not found at {args.corpus} - build it: "
                          "python3 speed_gate.py --make-corpus"),
            (QUANTIZE_BIN, f"llama-quantize not found at {QUANTIZE_BIN} - "
                           "place the b10964 build in the repo root"),
            ("./llama.cpp/convert_hf_to_gguf.py",
             "converter not found - the llama.cpp checkout must be in "
             "the repo root"),
            (SERVER_BIN, "llama-server not found - place the b10964 "
                         "build in the repo root"),
        ]:
            if not os.path.isfile(path):
                sys.exit(msg)

    state = load_state(args.state_file)

    if args.arc_only:
        if args.arc_models:
            jobs = []
            for p in args.arc_models.split(","):
                p = p.strip()
                if not os.path.isfile(p):
                    sys.exit(f"model file not found: {p}")
                jobs.append((safe_label(os.path.basename(p)), p))
        else:
            jobs = []
            for fam, fst in state["families"].items():
                if fst.get("selected"):
                    run = fst["runs"][fst["selected"]]
                    jobs.append((f"{fam} {fst['selected']}", run["file"]))
            if not jobs:
                sys.exit("no selections in state - run the full pipeline "
                         "first, or pass --arc-models")
        questions = load_questions(args.arc_config, args.arc_num)
        for label, path in jobs:
            def on_scored(lbl, score, _state=state, _sp=args.state_file):
                _state.setdefault("arc", {})[lbl] = {
                    "csv": arc_csv_path(args.arc_results_dir, lbl),
                    "score": score}
                save_state(_sp, _state)
            arc_eval.arc_run(label, path, questions, args.arc_num,
                             args.arc_results_dir, on_scored,
                             args.dry_run)
        if not args.dry_run:
            ranking, scores, pairs = mcnemar.rank(
                [l for l, _ in jobs], args.arc_num, args.arc_results_dir)
            state["ranking"] = {"arc_num": args.arc_num,
                                "scores": {m: scores[m] for m in ranking},
                                "order": ranking, "pairs": pairs}
            save_state(args.state_file, state)
        return

    if not args.families:
        ap.error("no family specs given (or use --arc-only)")

    for spec in args.families:
        process_family(spec, ladder, args.corpus, args.floor,
                       args.models_dir, state, args.state_file,
                       args.dry_run, args.force, args.thinking,
                       args.no_thinking, args.reader_tp)

    if args.dry_run:
        print("\ndry run complete - no files were downloaded or tested")
        return

    # ---- phases 5-6: full ARC on selected models, then the ranking
    selections = {}
    for fam, fst in state["families"].items():
        if fst.get("selected") and fst["runs"][fst["selected"]].get("file"):
            selections[fam] = fst["runs"][fst["selected"]]
    if selections:
        print()
        print("=" * 60)
        print(f"PHASES 5-6: full {args.arc_config} on selected models "
              f"({args.arc_num} questions each)")
        questions = load_questions(args.arc_config, args.arc_num)
        labels = []
        for fam, sel in selections.items():
            label = f"{fam} {state['families'][fam]['selected']}"
            labels.append(label)

            def on_scored(lbl, score, _state=state, _sp=args.state_file):
                _state.setdefault("arc", {})[lbl] = {
                    "csv": arc_csv_path(args.arc_results_dir, lbl),
                    "score": score}
                save_state(_sp, _state)
            arc_eval.arc_run(label, sel["file"], questions, args.arc_num,
                             args.arc_results_dir, on_scored, False)
        ranking, scores, pairs = mcnemar.rank(
            labels, args.arc_num, args.arc_results_dir)
        state["ranking"] = {"arc_num": args.arc_num,
                            "scores": {m: scores[m] for m in ranking},
                            "order": ranking, "pairs": pairs}
        save_state(args.state_file, state)
    else:
        print("\nno family has a selection yet - skipping ARC phases")

    # ---- results file: everything for later analysis
    results = []
    for fam, fst in state["families"].items():
        history = [dict(r, rung=rung) for rung, r in fst["runs"].items()]
        history.sort(key=lambda r: ladder.index(r["rung"])
                     if r["rung"] in ladder else 99)
        sel = fst["selected"]
        results.append({"family": fam, "spec": fst["spec"],
                        "history": history,
                        "selected": (dict(fst["runs"][sel], rung=sel)
                                    if sel else None)})
    doc = {"selection": results, "arc": state.get("arc", {}),
           "ranking": state.get("ranking")}
    with open(args.results_file, "w") as f:
        json.dump(doc, f, indent=1)
    print(f"\nresume state -> {args.state_file}")
    print(f"all data     -> {args.results_file}")


if __name__ == "__main__":
    main()
