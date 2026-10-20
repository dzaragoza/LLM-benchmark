#!/usr/bin/env python3
"""convert_quant.py -- the llama.cpp conversion/quantization interface
(bottom layer).

Everything that shells out to llama.cpp conversion tooling lives here
and nothing else shells out to it: safetensors -> f16 conversion with
the pinned converter (./llama.cpp/convert_hf_to_gguf.py, checkout
b29c606e2) and f16 -> rung quantization with the pinned llama-quantize
binary (build b11669). Not a CLI - the orchestrator imports it.

Create stage of the pipeline (its phase 2).

Imported by full_benchmark.py; file helpers shared from hf_download.py.
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys
from typing import NoReturn

import infra.hf_download as hf_download

QUANTIZE_BIN = os.path.join(
    ".", "llama-b11669", "llama-quantize.exe" if os.name == "nt" else "llama-quantize"
)
CONVERTER = "./llama.cpp/convert_hf_to_gguf.py"

IMATRIX_BIN = os.path.join(
    ".", "llama-b11669", "llama-imatrix.exe" if os.name == "nt" else "llama-imatrix")

# types the b11669 quantizer refuses without an importance matrix
# (llama-quantize: "this quantization requires an importance matrix")
IMATRIX_RUNGS = {
    "IQ1_S", "IQ1_M", "TQ1_0", "TQ2_0",
    "IQ2_XXS", "IQ2_XS", "IQ2_S", "IQ2_M", "Q2_K_S",
    "IQ3_XXS", "IQ3_XS", "IQ3_S", "IQ3_M",
    "IQ4_NL", "IQ4_XS",
    "Q1_0", "Q2_0",
}

# calibration text for the imatrix: the full arena English sample
# (arena/english_sample.json) flattened to plain text by
# build_imatrix_corpus.py (all 5000 conversations, every turn)
IMATRIX_CORPUS = "./data/imatrix-corpus.txt"


def ensure_imatrix(fam: str, famdir: str, f16: str) -> str | None:
    """Build the family's importance matrix once (from the f16, with the
    repo corpus as calibration text) and return its path. llama-imatrix
    writes <f16>.imatrix next to the model; reused on reruns."""
    out = f16 + ".imatrix"
    if os.path.isfile(out):
        return out
    txt = os.path.join(famdir, "imatrix-calib.txt")
    # every quantized tensor needs imatrix data or llama-quantize bails
    # out ("Missing importance matrix ... in a very low-bit
    # quantization"); the full arena corpus (10 MB, built once by
    # build_imatrix_corpus.py) exercises every tensor
    if not os.path.isfile(IMATRIX_CORPUS):
        import subprocess

        print("  [2] building the imatrix calibration corpus from the arena sample")
        r = subprocess.run([sys.executable, "build_imatrix_corpus.py"], cwd=".")
        if r.returncode != 0 or not os.path.isfile(IMATRIX_CORPUS):
            fail(2, "imatrix", "could not build the calibration corpus (build_imatrix_corpus.py failed)", GUIDE[2])
    try:
        os.link(IMATRIX_CORPUS, txt)
    except OSError:
        import shutil

        shutil.copyfile(IMATRIX_CORPUS, txt)
    log = os.path.join(famdir, "imatrix.log")
    print(f"  [2] computing importance matrix from {os.path.basename(f16)} (output hidden; shown on error)")
    rc = run_quiet(
        [IMATRIX_BIN, "-m", f16, "-f", txt, "-o", out],
        log, 2, "imatrix", "llama-imatrix run")
    if rc != 0 or not os.path.isfile(out):
        fail(2, "imatrix", f"llama-imatrix failed (full log: {log})", GUIDE[2])
    return out

GUIDE = {
    2: [
        "converter deps: pip install -r requirements.txt "
        "(needs transformers, torch, gguf, sentencepiece, protobuf)",
        "pinned converter missing: ./llama.cpp must be the matching checkout",
        "quantizer missing: place the b11669 build at ./llama-b11669/",
        "RAM/disk: f16 conversion needs several GB of each",
        "disk space: free some (the f16 gguf is written next to its "
        "source; both live together until the verified delete)",
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
    st_dir = os.path.join(famdir, "safetensors-source")
    has_st = os.path.isdir(st_dir) and (
        hf_download.st_source_complete(st_dir)
        or glob.glob(os.path.join(st_dir, "pytorch_model*.bin"))
    )
    if not f16 and not has_st:
        print(
            f"  [2] no local source to build {rung} from "
            "(no rung file, no f16, no safetensors-source)"
        )
        return None
    if not f16:
        out_f16 = os.path.join(famdir, fam + "-f16.gguf")
        # addendum 48: the disk check is a HARD GATE before the
        # conversion starts, not a warning - the f16 write is the
        # pipeline's transient peak (source + gguf live together until
        # the verified delete), and dying mid-write leaves a corrupt
        # partial gguf that the next run's local_rung could trust
        src_gib = (
            sum(
                os.path.getsize(os.path.join(st_dir, f))
                for f in os.listdir(st_dir)
                if os.path.isfile(os.path.join(st_dir, f))
            )
            / (1024**3)
            if os.path.isdir(st_dir)
            else 0.0
        )
        disk = hf_download.free_disk_gib(famdir)
        if disk is not None and disk < src_gib:
            print(
                f"  [2] f16 conversion needs ~{src_gib:.1f} GiB free "
                f"(the f16 is roughly the source's tensor payload) but only "
                f"{disk:.1f} GiB is free - free disk space and rerun; "
                "the script resumes from this phase"
            )
            fail(2, rung, "not enough disk for the f16 conversion", GUIDE[2])
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
    # session 40, addendum 30: the f16 rung IS the f16 - no quantize
    # step (the full-capacity pass measures (f16, f16, f16); quanting
    # f16 -> f16 through llama-quantize would be a wasteful copy)
    if rung.lower() == "f16":
        print(f"  [2] f16 rung - {os.path.basename(f16)} is the rung file (no quantize step)")
        return f16
    out = os.path.join(famdir, f"{fam}-{rung}.gguf")
    print(f"  [2] quantizing {os.path.basename(f16)} -> {rung} (output hidden; shown on error)")
    log = os.path.join(famdir, f"quantize-{rung}.log")
    cmd = [QUANTIZE_BIN]
    if rung.upper() in IMATRIX_RUNGS:
        imx = ensure_imatrix(fam, famdir, f16)
        if imx:
            cmd += ["--imatrix", imx]
            print(f"  [2] using importance matrix {os.path.basename(imx)}")
    cmd += [f16, out, rung]
    rc = run_quiet(cmd, log, 2, rung, "llama-quantize run")
    if rc != 0 or not os.path.isfile(out):
        fail(2, rung, f"llama-quantize failed (full log: {log})", GUIDE[2])
    return out
