#!/usr/bin/env python3
"""hf-download.py -- every Hugging Face interaction for the study.

Download stage of the pipeline (its phase 1): given a family spec
("model_repo" or "model_repo=source_repo") and a rung, acquire whatever
is needed to end up with that rung file - the premade rung GGUF from
the model repo, an f16 GGUF to quantize from (downloaded from the
source repo or already local), or the safetensors snapshot to convert
+ quantize from. Also owns the repo/file-inventory helpers (rung
matching, f16 matching, local-file checks) - no other pipeline script
talks to the Hub.

Standalone use (from the repo root):
    python3 hf-download.py "Qwen/Qwen3.5-4B" --rung Q5_K_M
    python3 hf-download.py \
        "google/gemma-3-4b-it-qat-q4_0-gguf=google/gemma-3-4b-it" \
        --rung Q6_K --dry-run

Imported by full-benchmark.py (acquire, list_repo_files, local_rung,
resolve_f16_local - the last two also imported by convert-quant.py).
"""

import argparse
import glob
import os
import sys

try:
    from huggingface_hub import (hf_hub_download, list_repo_files,
                                 snapshot_download)
except ImportError:
    hf_hub_download = list_repo_files = snapshot_download = None


def require_hub():
    """Only scripts that actually talk to the Hub need the dependency -
    importing this module for its file helpers must not exit."""
    if list_repo_files is None:
        sys.exit("huggingface_hub is required: pip install -r "
                 "requirements.txt (then activate the repo venv: "
                 ".venv/bin/activate on Linux/macOS, "
                 ".venv\\Scripts\\Activate.ps1 on Windows)")

MODELS_DIR_DEFAULT = "./models"

GUIDE = {
    1: [
        "gated repo: accept the license on hf.co and log in (hf auth login)",
        "wrong repo id: verify it exists at https://huggingface.co/<repo>",
        "network / disk space: check the download progress and df -h",
        "python deps: pip install -r requirements.txt (huggingface_hub)",
    ],
}


def fail(phase, rung, what, causes):
    """Abort loudly for one phase, with reader guidance."""
    print()
    print("=" * 60)
    print(f"PHASE {phase} FAILED at {rung}: {what}")
    print("Possible causes and fixes:")
    for c in causes:
        print(f"  - {c}")
    print("Fix the cause, then RERUN THE SAME COMMAND: the script is")
    print("idempotent and will resume from this phase.")
    print("=" * 60)
    sys.exit(1)


# =========================================================== rung helpers

def find_rung_file(names, rung):
    tok = rung.lower()
    for f in names:
        low = f.lower()
        if not low.endswith(".gguf") or "mmproj" in low:
            continue
        if "f16" in low or "fp16" in low or "bf16" in low:
            continue
        if tok in low:
            return f
    return None


def find_f16_files(names):
    singles, shards = [], []
    for f in names:
        low = f.lower()
        if not low.endswith(".gguf") or "mmproj" in low:
            continue
        if "00001-of-" in low and ("f16" in low or "fp16" in low):
            prefix = low.split("00001-of-")[0]
            shards.append([n for n in names
                           if n.lower().startswith(prefix)
                           and n.lower().endswith(".gguf")])
        elif "f16" in low or "fp16" in low:
            singles.append(f)
    if shards:
        return sorted(shards[0], key=lambda s: s.lower())
    for f in singles:
        if f.lower().endswith(("-f16.gguf", "-fp16.gguf")):
            return [f]
    return ([singles[0]] if singles else [])


def has_safetensors(names):
    return any(f.lower().endswith(".safetensors") for f in names)


def resolve_f16_local(famdir):
    """Local f16/fp16/bf16 GGUF (fp16 does NOT match a *f16* glob)."""
    if not os.path.isdir(famdir):
        return None
    hits = []
    for pat in ("*f16*.gguf", "*fp16*.gguf", "*bf16*.gguf"):
        hits += glob.glob(os.path.join(famdir, pat))
    hits = [h for h in hits if "mmproj" not in os.path.basename(h).lower()]
    return sorted(hits)[0] if hits else None


def local_rung(famdir, rung):
    if not os.path.isdir(famdir):
        return None
    f = find_rung_file(os.listdir(famdir), rung)
    return os.path.join(famdir, f) if f else None


# =========================================================== phase 1

def acquire(fam, famdir, rung, model_repo, model_files, source_repo,
            source_files, dry_run):
    """Phase 1: make sure the rung file, or the data to create it,
    is on disk. Returns (path_or_None, plan)."""
    require_hub()
    os.makedirs(famdir, exist_ok=True)
    if local_rung(famdir, rung):
        return local_rung(famdir, rung), "local file"
    repo_file = find_rung_file(model_files, rung)
    if repo_file:
        if dry_run:
            return None, f"download {model_repo}/{repo_file}"
        try:
            hf_hub_download(model_repo, repo_file, local_dir=famdir)
        except Exception as e:
            fail(1, rung, f"download of {model_repo}/{repo_file} failed: {e}",
                 GUIDE[1])
        p = local_rung(famdir, rung)
        if not p:
            fail(1, rung, "downloaded file not found afterwards", GUIDE[1])
        return p, f"downloaded {model_repo}/{repo_file}"

    if resolve_f16_local(famdir):
        return None, "quantize from local f16"
    f16_names = find_f16_files(source_files)
    if f16_names:
        if dry_run:
            return None, (f"download f16 from {source_repo} "
                          f"({'+'.join(f16_names)}), quantize")
        try:
            for name in f16_names:
                hf_hub_download(source_repo, name, local_dir=famdir)
        except Exception as e:
            fail(1, rung, f"f16 download from {source_repo} failed: {e}",
                 GUIDE[1])
        if not resolve_f16_local(famdir):
            fail(1, rung, "f16 download finished but file is missing",
                 GUIDE[1])
        return None, f"downloaded f16 from {source_repo}, quantize"
    if has_safetensors(source_files):
        st_dir = os.path.join(famdir, "safetensors-source")
        if dry_run or (os.path.isdir(st_dir)
                       and glob.glob(os.path.join(st_dir, "*.safetensors"))):
            return None, f"safetensors from {source_repo}, convert + quantize"
        try:
            print(f"  [1] downloading safetensors from {source_repo} "
                  "(several GB, once per family)")
            snapshot_download(source_repo, local_dir=st_dir)
        except Exception as e:
            fail(1, rung, f"safetensors download from {source_repo} "
                 f"failed: {e}", GUIDE[1])
        if not glob.glob(os.path.join(st_dir, "*.safetensors")):
            fail(1, rung, "snapshot download finished, no safetensors found",
                 GUIDE[1])
        return None, f"safetensors from {source_repo}, convert + quantize"
    fail(1, rung, f"no {rung} file, no f16 GGUF, no safetensors in "
         f"{source_repo} - nothing to download or quantize from", GUIDE[1])


# =========================================================== main

def main():
    ap = argparse.ArgumentParser(
        description="download stage: acquire a rung file (or the data to "
                    "create it) from Hugging Face - all Hub interaction "
                    "lives here")
    ap.add_argument("spec",
                    help='family spec: "model_repo" or '
                         '"model_repo=source_repo"')
    ap.add_argument("--rung", required=True,
                    help="quantization rung to acquire (e.g. Q6_K)")
    ap.add_argument("--models-dir", default=MODELS_DIR_DEFAULT)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan only, download nothing")
    args = ap.parse_args()

    require_hub()
    model_repo, _, source_repo = args.spec.partition("=")
    if not source_repo:
        source_repo = model_repo
    fam = os.path.basename(model_repo.rstrip("/"))
    famdir = os.path.join(args.models_dir, fam)
    try:
        model_files = list_repo_files(model_repo)
        source_files = (model_files if source_repo == model_repo
                        else list_repo_files(source_repo))
    except Exception as e:
        fail(1, "-", f"cannot list repo files for {model_repo}: {e}",
             GUIDE[1])
    path, plan = acquire(fam, famdir, args.rung, model_repo, model_files,
                         source_repo, source_files, args.dry_run)
    if path:
        print(f"[1] rung file ready: {path}  (plan: {plan})")
    else:
        print(f"[1] {plan}")


if __name__ == "__main__":
    main()
