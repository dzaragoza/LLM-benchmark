#!/usr/bin/env python3
"""convert-quant.py -- the llama.cpp conversion + quantization stage.

Create stage of the pipeline (its phase 2): produce the requested rung
GGUF for a family - from a local f16 GGUF if one is present, else by
converting the downloaded safetensors snapshot to f16 first (pinned
converter), then quantizing f16 -> rung with the pinned llama-quantize
binary. Everything that shells out to llama.cpp conversion tooling
lives here.

Standalone use (from the repo root):
    python3 convert-quant.py ./models/Qwen3.5-4B Q5_K_M
    python3 convert-quant.py ./models/SmolLM2-1.7B-Instruct Q4_K_M --dry-run

Imported by full-benchmark.py (create).
"""

import argparse
import os
import subprocess
import sys

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


def _hf_download():
    """Sibling import: hf-download.py has a hyphenated filename, so a
    plain import cannot reach it. Canonical name = "hf_download" -
    full-benchmark.py registers the same name, so the pipeline and
    standalone runs share one module instance."""
    if "hf_download" in sys.modules:
        return sys.modules["hf_download"]
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        "hf_download", os.path.join(here, "hf-download.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hf_download"] = mod
    spec.loader.exec_module(mod)
    return mod


def create(fam, famdir, rung, plan="", dry_run=False):
    """Phase 2: ensure the rung file exists locally. Returns its path
    (None on dry run with nothing to do)."""
    hfd = _hf_download()
    p = hfd.local_rung(famdir, rung)
    if p:
        return p
    if dry_run:
        return None
    f16 = hfd.resolve_f16_local(famdir)
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


# =========================================================== main

def main():
    ap = argparse.ArgumentParser(
        description="create stage: convert safetensors -> f16 and quantize "
                    "f16 -> rung with the pinned llama.cpp toolchain")
    ap.add_argument("famdir",
                    help="family directory (e.g. ./models/Qwen3.5-4B)")
    ap.add_argument("rung", help="quantization rung to create (e.g. Q6_K)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would happen, create nothing")
    args = ap.parse_args()

    fam = os.path.basename(os.path.normpath(args.famdir))
    out = create(fam, args.famdir, args.rung, dry_run=args.dry_run)
    if out:
        print(f"[2] rung file ready: {out}")
    else:
        print(f"[2] dry run - would create {fam}-{args.rung}.gguf in "
              f"{args.famdir}")


if __name__ == "__main__":
    main()
