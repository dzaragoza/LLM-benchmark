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

from __future__ import annotations

import glob
import json
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, NoReturn

# Quiet downloads (author ruling, addendum 38): hub progress bars are
# hidden; failures still surface through fail() with the full error.
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

try:
    from huggingface_hub import hf_hub_download, list_repo_files, snapshot_download
except ImportError:
    hf_hub_download = list_repo_files = snapshot_download = None


def require_hub() -> None:
    """Only callers that actually talk to the Hub need the dependency -
    importing this module for its file helpers must not exit."""
    if list_repo_files is None:
        sys.exit(
            "huggingface_hub is required: pip install -r "
            "requirements.txt (then activate the repo venv: "
            ".venv/bin/activate on Linux/macOS, "
            ".venv\\Scripts\\Activate.ps1 on Windows)"
        )


def fail(phase: int, rung: str, what: str, causes: list[str]) -> NoReturn:
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


def system_ram_gib() -> float | None:
    """Total system RAM in GiB (best effort, cross-platform).
    Linux: /proc/meminfo; macOS: sysctl; Windows: ctypes GlobalMemoryStatusEx.
    Returns None when undetectable - the feasibility check then trusts
    the caller instead of guessing."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) / (1024 * 1024)
    except Exception:
        pass
    try:
        import subprocess

        out = subprocess.run(
            ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=10
        )
        if out.returncode == 0:
            return int(out.stdout.strip()) / (1024**3)
    except Exception:
        pass
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        if not hasattr(ctypes, "windll"):
            return None
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return stat.ullTotalPhys / (1024**3)
    except Exception:
        return None


def free_disk_gib(path: str = ".") -> float | None:
    """Free disk space at `path` in GiB (None if undetectable)."""
    try:
        return shutil.disk_usage(path).free / (1024**3)
    except Exception:
        return None


def remote_file_sizes(repo: str) -> dict[str, int]:
    """{filename: size_in_bytes} for a repo, from the HF metadata API -
    NO file content is downloaded. Returns {} when the hub client is
    too old to expose tree listings (the caller then estimates from
    quant ratios or skips the feasibility check)."""
    try:
        from huggingface_hub import HfApi

        sizes = {}
        for entry in HfApi().list_repo_tree(repo, recursive=True):
            size = getattr(entry, "size", None)
            if size:
                sizes[entry.path] = size
        return sizes
    except Exception:
        return {}


# bits-per-weight of each ladder rung (llama.cpp quant formats) - the
# conversion path scales linearly: rung_gib ~= fp16_gib * bits / 16
RUNG_BITS = {
    "Q8_0": 8.5,
    "Q6_K": 6.6,
    "Q5_K_M": 5.7,
    "Q4_K_M": 4.8,
    "Q4_0": 4.5,
    "Q3_K_M": 3.9,
    "Q2_K": 3.4,
}


def estimate_rung_gib(
    rung: str, model_files: list[str], source_files: list[str], sizes: dict[str, int]
) -> float | None:
    """Estimated size in GiB of the rung file, WITHOUT downloading it
    (addendum 35 - the memory shortcut). Exact when the repo ships the
    rung GGUF (remote metadata); ratio-scaled from the fp16/safetensors
    size when the rung is self-quantized. Returns None when no estimate
    is possible (the caller then does not skip - never a false skip)."""
    repo_file = find_rung_file(model_files, rung)
    if repo_file and repo_file in sizes:
        return sizes[repo_file] / (1024**3)
    bits = RUNG_BITS.get(rung)
    if bits is None:
        return None
    f16s = [sizes[f] for f in find_f16_files(source_files) if f in sizes]
    if f16s:
        return sum(f16s) / (1024**3) * bits / 16
    sts = [
        s
        for f, s in sizes.items()
        if f.lower().endswith(".safetensors") and not f.lower().startswith("original/")
    ]
    if sts:
        return sum(sts) / (1024**3) * bits / 16
    bins = [
        s
        for f, s in sizes.items()
        if (
            f.lower().endswith("pytorch_model.bin")
            or (f.lower().startswith("pytorch_model-") and f.lower().endswith(".bin"))
        )
    ]
    if bins:
        return sum(bins) / (1024**3) * bits / 16
    return None


# system-RAM reserve for the OS + the KV cache at the 4096 reference
# depth (addendum 35): a rung is feasible only if its file fits in
# total RAM minus this reserve (the T14s: 32 - 4 = 28 GiB usable).
RAM_RESERVE_GIB = 4.0


def find_rung_file(names: list[str] | tuple[str, ...], rung: str) -> str | None:
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


def find_f16_files(names: list[str]) -> list[str]:
    singles, shards = [], []
    for f in names:
        low = f.lower()
        if not low.endswith(".gguf") or "mmproj" in low:
            continue
        if "00001-of-" in low and ("f16" in low or "fp16" in low):
            prefix = low.split("00001-of-")[0]
            shards.append(
                [n for n in names if n.lower().startswith(prefix) and n.lower().endswith(".gguf")]
            )
        elif "f16" in low or "fp16" in low:
            singles.append(f)
    if shards:
        return sorted(shards[0], key=lambda s: s.lower())
    for f in singles:
        if f.lower().endswith(("-f16.gguf", "-fp16.gguf")):
            return [f]
    return [singles[0]] if singles else []


def has_safetensors(names: list[str]) -> bool:
    return any(f.lower().endswith(".safetensors") for f in names)


def has_pytorch_bin(names: list[str]) -> bool:
    """pytorch_model.bin (+ sharded index) - the legacy pickle format the
    pinned b10964 converter loads natively (conversion/base.py falls
    back to pytorch_model*.bin when no safetensors parts exist; addendum 81
    - the MiniCPM-2B/1B-sft-bf16 repos ship bin-only)."""
    return any(
        f.lower().endswith("pytorch_model.bin") or f.lower().startswith("pytorch_model-00001-of-")
        for f in names
    )


def resolve_f16_local(famdir: str) -> str | None:
    """Local f16/fp16/bf16 GGUF (fp16 does NOT match a *f16* glob)."""
    if not os.path.isdir(famdir):
        return None
    hits = []
    for pat in ("*f16*.gguf", "*fp16*.gguf", "*bf16*.gguf"):
        hits += glob.glob(os.path.join(famdir, pat))
    hits = [h for h in hits if "mmproj" not in os.path.basename(h).lower()]
    return sorted(hits)[0] if hits else None


def local_rung(famdir: str, rung: str) -> str | None:
    if not os.path.isdir(famdir):
        return None
    f = find_rung_file(os.listdir(famdir), rung)
    return os.path.join(famdir, f) if f else None


# =========================================================== phase 1


def acquire(
    fam: str,
    famdir: str,
    rung: str,
    model_repo: str,
    model_files: list[str],
    source_repo: str,
    source_files: list[str],
    dry_run: bool,
) -> tuple[str | None, str]:
    """Phase 1: make sure the rung file, or the data to create it,
    is on disk. Returns (path_or_None, plan).
    Memory shortcut (addendum 35): rungs whose estimated size cannot
    fit in system RAM (minus the OS/KV reserve) are skipped BEFORE any
    download - no time spent on rungs the machine cannot run at all.
    Disk is checked the same way (source files can be 2x the rung)."""
    require_hub()
    assert (
        hf_hub_download is not None and snapshot_download is not None
    )  # require_hub exits when the hub is missing
    os.makedirs(famdir, exist_ok=True)
    if local_rung(famdir, rung):
        return local_rung(famdir, rung), "local file"

    # feasibility shortcut, before any network traffic
    sizes = remote_file_sizes(source_repo) or remote_file_sizes(model_repo)
    rung_est = estimate_rung_gib(rung, model_files, source_files, sizes)
    ram = system_ram_gib()
    if rung_est is not None and ram is not None:
        usable = ram - RAM_RESERVE_GIB
        if rung_est > usable:
            print(
                f"  [1] {rung}: estimated {rung_est:.1f} GiB exceeds "
                f"usable RAM {usable:.1f} GiB (total {ram:.1f} GiB - "
                f"{RAM_RESERVE_GIB:g} reserve) - CANNOT RUN on this "
                "machine, skipping before download (addendum 35)"
            )
            return None, "infeasible: exceeds system RAM"
    disk = free_disk_gib(famdir)
    if rung_est is not None and disk is not None:
        need = rung_est * 2 if rung_est else 0
        if disk < need:
            print(
                f"  [1] {rung}: estimated {rung_est:.1f} GiB rung (worst "
                f"case {need:.1f} GiB with source) but only {disk:.1f} "
                "GiB free on disk - fix disk space; attempting anyway "
                "(local files may already exist)"
            )
    repo_file = find_rung_file(model_files, rung)
    if repo_file:
        if dry_run:
            return None, f"download {model_repo}/{repo_file}"
        try:
            print(f"  [1] downloading {model_repo}/{repo_file} (output hidden; shown on error)")
            hf_hub_download(model_repo, repo_file, local_dir=famdir)
        except Exception as e:
            fail(1, rung, f"download of {model_repo}/{repo_file} failed: {e}", GUIDE[1])
        p = local_rung(famdir, rung)
        if not p:
            fail(1, rung, "downloaded file not found afterwards", GUIDE[1])
        return p, f"downloaded {model_repo}/{repo_file}"

    if resolve_f16_local(famdir):
        return None, "quantize from local f16"
    f16_names = find_f16_files(source_files)
    if f16_names:
        if dry_run:
            return None, (f"download f16 from {source_repo} ({'+'.join(f16_names)}), quantize")
        try:
            for name in f16_names:
                print(f"  [1] downloading {source_repo}/{name} (output hidden; shown on error)")
                hf_hub_download(source_repo, name, local_dir=famdir)
        except Exception as e:
            fail(1, rung, f"f16 download from {source_repo} failed: {e}", GUIDE[1])
        if not resolve_f16_local(famdir):
            fail(1, rung, "f16 download finished but file is missing", GUIDE[1])
        return None, f"downloaded f16 from {source_repo}, quantize"
    if has_safetensors(source_files):
        st_dir = os.path.join(famdir, "safetensors-source")
        if dry_run or (os.path.isdir(st_dir) and glob.glob(os.path.join(st_dir, "*.safetensors"))):
            return None, f"safetensors from {source_repo}, convert + quantize"
        try:
            print(
                f"  [1] downloading safetensors from {source_repo} "
                "(safetensors + configs only; once per family; "
                "output hidden; shown on error)"
            )
            snapshot_download(
                source_repo,
                local_dir=st_dir,
                allow_patterns=[
                    "*.safetensors",
                    "*.json",
                    "*.txt",
                    "tokenizer.model",
                    "tokenizer.model.v3",
                ],
            )
        except Exception as e:
            fail(1, rung, f"safetensors download from {source_repo} failed: {e}", GUIDE[1])
        if not glob.glob(os.path.join(st_dir, "*.safetensors")):
            fail(1, rung, "snapshot download finished, no safetensors found", GUIDE[1])
        return None, f"safetensors from {source_repo}, convert + quantize"
    if has_pytorch_bin(source_files):
        st_dir = os.path.join(famdir, "safetensors-source")
        if dry_run or (
            os.path.isdir(st_dir) and glob.glob(os.path.join(st_dir, "pytorch_model*.bin"))
        ):
            return None, (f"pytorch_model.bin from {source_repo}, convert + quantize")
        try:
            print(
                f"  [1] downloading pytorch_model.bin from {source_repo} "
                "(weights + configs; output hidden; shown on error)"
            )
            snapshot_download(
                source_repo,
                local_dir=st_dir,
                allow_patterns=[
                    "pytorch_model*.bin",
                    "*.json",
                    "*.txt",
                    "tokenizer.model",
                    "tokenizer.model.v3",
                ],
            )
        except Exception as e:
            fail(1, rung, f"pytorch_model.bin download from {source_repo} failed: {e}", GUIDE[1])
        if not glob.glob(os.path.join(st_dir, "pytorch_model*.bin")):
            fail(1, rung, "bin download finished, no pytorch_model*.bin found", GUIDE[1])
        return None, f"pytorch_model.bin from {source_repo}, convert + quantize"
    fail(
        1,
        rung,
        f"no {rung} file, no f16 GGUF, no safetensors, no "
        f"pytorch_model.bin in {source_repo} - nothing to download or "
        "quantize from",
        GUIDE[1],
    )


# =========================================================== ARC questions


def _http_get_json(
    url: str,
    params: dict[str, str | int] | None = None,
    timeout: int = 60,
    retries: int = 4,
) -> Any:
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
            print(
                f"    http get failed (attempt {attempt + 1}/{retries}): {e} - retrying in {wait}s",
                file=sys.stderr,
            )
            time.sleep(wait)
    raise RuntimeError(f"http get failed after {retries} attempts: {url}") from last_err


def load_questions(config: str, n: int) -> list[dict[str, Any]]:
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
            params={
                "dataset": "allenai/ai2_arc",
                "config": config,
                "split": "test",
                "offset": offset,
                "length": batch,
            },
        )
        for row in rows["rows"]:
            item = row["row"]
            qs.append(
                {
                    "q": item["question"],
                    "choices": list(
                        zip(item["choices"]["label"], item["choices"]["text"], strict=True)
                    ),
                    "ans": item["answerKey"],
                }
            )
    with open(cache_file, "w") as f:
        json.dump(qs, f)
    return qs
