#!/usr/bin/env python3
"""hf_download.py -- the Hugging Face interface (bottom layer).

Every interaction with Hugging Face services in the study goes through
this module and nothing else: model downloads (premade rung GGUF, f16
GGUF, safetensors snapshots), repo/file listings, and the ARC question
fetch from the HF datasets-server. Not a CLI - the phase scripts and
the orchestrator import it.

Download stage of the pipeline (its phase 1): given a family spec
("model_repo" or "model_repo=source_repo") and a rung, acquire
whatever is needed to end up with that rung file. Also owns the
repo/file-inventory helpers (rung matching, f16 matching,
local-file checks).

Imported by full_benchmark.py, speed_gate.py, arc_eval.py,
convert_quant.py.
"""

import glob
import json
import os
import sys
import time
import urllib.parse
import urllib.request

try:
    from huggingface_hub import (hf_hub_download, list_repo_files,
                                 snapshot_download)
except ImportError:
    hf_hub_download = list_repo_files = snapshot_download = None


def require_hub():
    """Only callers that actually talk to the Hub need the dependency -
    importing this module for its file helpers must not exit."""
    if list_repo_files is None:
        sys.exit("huggingface_hub is required: pip install -r "
                 "requirements.txt (then activate the repo venv: "
                 ".venv/bin/activate on Linux/macOS, "
                 ".venv\\Scripts\\Activate.ps1 on Windows)")


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


GUIDE = {
    1: [
        "gated repo: accept the license on hf.co and log in (hf auth login)",
        "wrong repo id: verify it exists at https://huggingface.co/<repo>",
        "network / disk space: check the download progress and df -h",
        "python deps: pip install -r requirements.txt (huggingface_hub)",
    ],
}


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


# =========================================================== ARC questions

def _http_get_json(url, params=None, timeout=60, retries=4):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last_err = e
            wait = 5 * (attempt + 1)
            print(f"    http get failed (attempt {attempt + 1}/{retries}): "
                  f"{e} - retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise last_err


def load_questions(config, n):
    """ARC questions from the HF datasets-server; cached in the repo root
    (same questions across runs and models - McNemar pairing depends
    on it)."""
    cache_file = f"arc-{config}-test-{n}.json"
    if os.path.exists(cache_file):
        print(f"    using cached questions: {cache_file}", file=sys.stderr)
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)
    require_hub()
    qs = []
    for offset in range(0, n, 100):
        batch = min(100, n - offset)
        rows = _http_get_json(
            "https://datasets-server.huggingface.co/rows",
            params={"dataset": "allenai/ai2_arc", "config": config,
                    "split": "test", "offset": offset, "length": batch})
        for row in rows["rows"]:
            item = row["row"]
            qs.append({"q": item["question"],
                       "choices": list(zip(item["choices"]["label"],
                                           item["choices"]["text"])),
                       "ans": item["answerKey"]})
    with open(cache_file, "w") as f:
        json.dump(qs, f)
    return qs
