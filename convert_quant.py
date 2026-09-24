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

import os
import subprocess
import sys

import hf_download

QUANTIZE_BIN = os.path.join(".", "llama-b10964-gpu",
                            "llama-quantize.exe" if os.name == "nt"
                            else "llama-quantize")
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


def create(fam, famdir, rung, plan="", dry_run=False):
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
        print("  [2] converting safetensors -> f16 (pinned converter)")
        r = subprocess.run([sys.executable, CONVERTER,
                            st_dir, "--outfile", out_f16, "--outtype", "f16"])
        if r.returncode != 0 or not os.path.isfile(out_f16):
            fail(2, rung, "f16 conversion failed "
                 "(see the converter output above)", GUIDE[2])
        f16 = out_f16
    out = os.path.join(famdir, f"{fam}-{rung}.gguf")
    print(f"  [2] quantizing {os.path.basename(f16)} -> {rung}")
    r = subprocess.run([QUANTIZE_BIN, f16, out, rung])
    if r.returncode != 0 or not os.path.isfile(out):
        fail(2, rung, "llama-quantize failed "
             "(see the quantizer output above)", GUIDE[2])
    return out
