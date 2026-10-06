#!/usr/bin/env python3
"""convert_quant.py -- the llama.cpp conversion/quantization interface
(bottom layer).

Everything that shells out to llama.cpp conversion tooling lives here
and nothing else shells out to it: safetensors -> f16 conversion with
the pinned converter (./llama.cpp/convert_hf_to_gguf.py, checkout
b29c606e2) and f16 -> rung quantization with the pinned llama-quantize
binary (build b10964). Not a CLI - the orchestrator imports it.

Create stage of the pipeline (its phase 2).

Imported by full_benchmark.py; file helpers shared from hf_download.py.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import NoReturn

import infra.hf_download as hf_download

QUANTIZE_BIN = os.path.join(
    ".", "llama-b10964-gpu", "llama-quantize.exe" if os.name == "nt" else "llama-quantize"
)
CONVERTER = "./llama.cpp/convert_hf_to_gguf.py"

GUIDE = {
    2: [
        "converter deps: pip install -r requirements.txt "
        "(needs transformers, torch, gguf, sentencepiece, protobuf)",
        "pinned converter missing: ./llama.cpp must be the b10964 checkout",
        "quantizer missing: place the b10964 build at ./llama-b10964-gpu/",
        "RAM/disk: f16 conversion needs several GB of each",
    ],
}


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


def run_quiet(cmd: list[str], log_path: str, phase: int, rung: str, what: str) -> int:
    """Quiet tooling (author ruling, addendum 38): the converter's and
    quantizer's stdout/stderr is captured to log_path and printed
    only when the tool fails - success stays silent."""
    with open(log_path, "w", encoding="utf-8") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        print()
        print(f"--- output of the failed {what} (full log: {log_path}) ---")
        try:
            with open(log_path, encoding="utf-8") as f:
                tail = f.read()
            print(tail if tail.strip() else "(no output captured)")
        except OSError:
            print("(log unreadable)")
        print("--- end of tool output ---")
    return r.returncode


def create(fam: str, famdir: str, rung: str, plan: str = "", dry_run: bool = False) -> str | None:
    """Phase 2: ensure the rung file exists locally. Returns its path
    (None on dry run with nothing to do)."""
    p = hf_download.local_rung(famdir, rung)
    if p:
        return p
    if dry_run:
        return None
    f16 = hf_download.resolve_f16_local(famdir)
    if not f16:
        st_dir = os.path.join(famdir, "safetensors-source")
        out_f16 = os.path.join(famdir, fam + "-f16.gguf")
        print(
            "  [2] converting safetensors -> f16 (pinned converter; output hidden; shown on error)"
        )
        log = os.path.join(famdir, "convert-f16.log")
        rc = run_quiet(
            [sys.executable, CONVERTER, st_dir, "--outfile", out_f16, "--outtype", "f16"],
            log,
            2,
            rung,
            "safetensors -> f16 conversion",
        )
        if rc != 0 or not os.path.isfile(out_f16):
            fail(2, rung, f"f16 conversion failed (full log: {log})", GUIDE[2])
        f16 = out_f16
        # the tensors are dead weight once the f16 exists (addendum 42):
        # every further quant comes from the f16, never the safetensors.
        # Deleted only after the conversion is verified on disk.
        import shutil

        st_dir = os.path.join(famdir, "safetensors-source")
        if os.path.isdir(st_dir):
            shutil.rmtree(st_dir)
            print("  [2] safetensors-source deleted (the f16 is the quant source from here)")
    out = os.path.join(famdir, f"{fam}-{rung}.gguf")
    print(f"  [2] quantizing {os.path.basename(f16)} -> {rung} (output hidden; shown on error)")
    log = os.path.join(famdir, f"quantize-{rung}.log")
    rc = run_quiet([QUANTIZE_BIN, f16, out, rung], log, 2, rung, "llama-quantize run")
    if rc != 0 or not os.path.isfile(out):
        fail(2, rung, f"llama-quantize failed (full log: {log})", GUIDE[2])
    return out
