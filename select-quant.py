#!/usr/bin/env python3
"""select-quant.py — automated quant selection by the live speed rule.

For each model family (an HF repo id), walks the quant ladder DOWNWARD from
Q8_0 and live-tests each rung with live-bench.py (the strict worst-turn
>= 20 rule). The first rung whose worst turn clears the floor is the
family's selection. No predictions, no skipping, no optimizations — the
plain downward search, automated so the process itself is the artifact.

Rung resolution, in order:
  1. local: a matching quant file already in ./models/<family>/
  2. download: the repo ships that quant -> download into ./models/<family>/
  3. quantize: download the repo's f16 (once per family) and quantize with
     the pinned llama-quantize (b10964)

No HF cache is used for model files: everything lands in ./models/<family>/
so the folder IS the provenance record (see selection-results.json for the
per-file provenance entries).

Family spec syntax: "model_repo" or "model_repo=f16_repo"
(the latter when the f16 GGUF lives in a different repo than the quants,
e.g. "google/gemma-3-4b-it-qat-q4_0-gguf=ggml-org/gemma-3-4b-it-GGUF").

Usage (from repo root):
  # plan only, no downloads:
  python3 select-quant.py --dry-run "Qwen/Qwen2.5-3B-Instruct-GGUF" ...

  # full run:
  python3 select-quant.py \
      "Qwen/Qwen2.5-3B-Instruct-GGUF" \
      "microsoft/Phi-3-mini-4k-instruct-gguf" \
      "meta-llama/Llama-3.2-3B-Instruct-GGUF" \
      "google/gemma-3-4b-it-qat-q4_0-gguf=ggml-org/gemma-3-4b-it-GGUF"
"""

import argparse
import json
import os
import re
import subprocess
import sys

try:
    from huggingface_hub import hf_hub_download, list_repo_files
except ImportError:
    sys.exit("huggingface_hub is required (pip install huggingface_hub)")

QUANTIZE_BIN = "./llama-b10964-gpu/llama-quantize"
LIVE_BENCH = "./live-bench.py"
CORPUS_DEFAULT = "./live-corpus.json"
MODELS_DIR_DEFAULT = "./models"
RESULTS_FILE_DEFAULT = "./selection-results.json"
LADDER_DEFAULT = ["Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M", "Q2_K"]
FLOOR_DEFAULT = 20.0


def find_rung_file(names, rung):
    """Return a filename that is this rung's quant (or None)."""
    tok = rung.lower()
    for f in names:
        low = f.lower()
        if not low.endswith(".gguf"):
            continue
        if "mmproj" in low:
            continue
        if "f16" in low or "fp16" in low or "bf16" in low:
            continue
        if tok in low:
            return f
    return None


def find_f16_file(names):
    """Return the f16 source filename (or None)."""
    fallback = None
    for f in names:
        low = f.lower()
        if not low.endswith(".gguf") or "mmproj" in low:
            continue
        if low.endswith("f16.gguf") or low.endswith("fp16.gguf"):
            return f
        if "f16" in low or "fp16" in low:
            fallback = fallback or f
    return fallback


def live_worst_turn(model_path, corpus):
    """Run live-bench.py on one model; return (worst turn t/s, dump path)."""
    dump = model_path + ".live-dump.json"
    cmd = [sys.executable, LIVE_BENCH,
           "--corpus", corpus, "--models", model_path, "--dump", dump]
    res = subprocess.run(cmd)
    if res.returncode != 0 or not os.path.isfile(dump):
        return None, dump
    with open(dump) as f:
        turns = json.load(f)
    label = os.path.basename(model_path)
    vals = [t["server_tps"] for t in turns
            if t.get("model") == label and t.get("server_tps")]
    return (min(vals) if vals else None), dump


def process_family(spec, ladder, corpus, floor, models_dir, dry_run):
    if "=" in spec:
        model_repo, f16_repo = spec.split("=", 1)
    else:
        model_repo, f16_repo = spec, spec
    fam = os.path.basename(model_repo.rstrip("/"))
    famdir = os.path.join(models_dir, fam)

    print()
    print("=" * 60)
    print(f"family: {fam}")
    print(f"  model repo : {model_repo}")
    print(f"  f16 repo   : {f16_repo}")
    print(f"  folder     : {famdir}")

    model_files = list_repo_files(model_repo)
    f16_files = (model_files if f16_repo == model_repo
                 else list_repo_files(f16_repo))
    f16_name = find_f16_file(f16_files)
    if not f16_name:
        print(f"  ERROR: no f16 GGUF found in {f16_repo} — cannot quantize")
        return {"family": fam, "spec": spec, "error": "no f16 source",
                "history": [], "selected": None}

    print(f"  f16 source : {f16_repo}/{f16_name}")

    history = []
    selected = None
    for rung in ladder:
        local = None
        if os.path.isdir(famdir):
            local = find_rung_file(os.listdir(famdir), rung)
        if local:
            path = os.path.join(famdir, local)
            prov = f"local: {local}"
        else:
            repo_file = find_rung_file(model_files, rung)
            os.makedirs(famdir, exist_ok=True)
            if repo_file:
                prov = f"downloaded: {model_repo}/{repo_file}"
                if dry_run:
                    print(f"  [{rung}] would download {repo_file}")
                    history.append({"rung": rung, "plan": prov})
                    continue
                print(f"  [{rung}] downloading {repo_file} from {model_repo}")
                path = hf_hub_download(model_repo, repo_file,
                                       local_dir=famdir)
            else:
                prov = f"quantized from {f16_repo}/{f16_name}"
                if dry_run:
                    print(f"  [{rung}] would quantize (repo has no "
                          f"{rung} file)")
                    history.append({"rung": rung, "plan": prov})
                    continue
                print(f"  [{rung}] not in repo — quantizing from f16")
                f16_local = hf_hub_download(f16_repo, f16_name,
                                            local_dir=famdir)
                out = os.path.join(famdir, fam + "-" + rung + ".gguf")
                r = subprocess.run([QUANTIZE_BIN, f16_local, out, rung])
                if r.returncode != 0 or not os.path.isfile(out):
                    print(f"  [{rung}] ERROR: quantize failed — "
                          "aborting this family")
                    history.append({"rung": rung, "error": "quantize failed"})
                    break
                path = out

        print(f"  [{rung}] live test: {os.path.basename(path)}")
        worst, dump = live_worst_turn(path, corpus)
        if worst is None:
            print(f"  [{rung}] ERROR: live test failed (dump: {dump})")
            history.append({"rung": rung, "error": "live test failed"})
            break
        verdict = "PASS" if worst >= floor else "FAIL"
        print(f"  [{rung}] worst turn {worst:.1f} t/s -> {verdict} "
              f"(floor {floor})")
        history.append({"rung": rung, "worst": worst, "verdict": verdict,
                        "file": path, "provenance": prov})
        if worst >= floor:
            selected = history[-1]
            break

    return {"family": fam, "spec": spec,
            "f16": f"{f16_repo}/{f16_name}", "history": history,
            "selected": selected}


def main():
    ap = argparse.ArgumentParser(
        description="automated downward quant selection by the live "
                    "worst-turn >= floor rule")
    ap.add_argument("families", nargs="+",
                    help='family specs: "model_repo" or "model_repo=f16_repo"')
    ap.add_argument("--corpus", default=CORPUS_DEFAULT)
    ap.add_argument("--floor", type=float, default=FLOOR_DEFAULT)
    ap.add_argument("--ladder", default=",".join(LADDER_DEFAULT),
                    help="comma-separated rungs, top to bottom")
    ap.add_argument("--models-dir", default=MODELS_DIR_DEFAULT)
    ap.add_argument("--results-file", default=RESULTS_FILE_DEFAULT)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the resolution plan only")
    args = ap.parse_args()

    ladder = [x.strip() for x in args.ladder.split(",") if x.strip()]

    if not os.path.isfile(LIVE_BENCH) and not args.dry_run:
        sys.exit(f"live-bench.py not found at {LIVE_BENCH} — run from the "
                 "repo root")
    if not os.path.isfile(args.corpus) and not args.dry_run:
        sys.exit(f"corpus not found at {args.corpus} — build it first: "
                 "python3 live-bench.py --make-corpus")
    if not os.path.isfile(QUANTIZE_BIN) and not args.dry_run:
        sys.exit(f"llama-quantize not found at {QUANTIZE_BIN} — place the "
                 "b10964 build in the repo root")

    results = []
    for spec in args.families:
        try:
            results.append(process_family(spec, ladder, args.corpus,
                                          args.floor, args.models_dir,
                                          args.dry_run))
        except Exception as e:
            print(f"  ERROR: family {spec} aborted: {e}")
            results.append({"family": spec, "error": str(e),
                            "history": [], "selected": None})

    if args.dry_run:
        print()
        print("dry run complete — no files were downloaded or tested")
        return

    with open(args.results_file, "w") as f:
        json.dump(results, f, indent=1)

    print()
    print("=" * 60)
    print("SELECTION (highest rung with worst turn >= "
          f"{args.floor:g} t/s)")
    for r in results:
        fam = r["family"]
        if r.get("selected"):
            s = r["selected"]
            print(f"  {fam}: {s['rung']}  (worst {s['worst']:.1f} t/s, "
                  f"{s['provenance']})")
        else:
            print(f"  {fam}: NO PASSING RUNG in ladder "
                  "(see history in " + args.results_file + ")")
    print("=" * 60)
    print(f"details -> {args.results_file}")


if __name__ == "__main__":
    main()
