# LLM-benchmark — local LLM selection & benchmarking

Companion repository for **"Small Models, Big Claims"** — an independent
measurement study of small instruct LLMs running from system RAM on
integrated GPUs, with the llama.cpp Vulkan backend.

**📄 Report (study #1):** [DOI: 10.5281/zenodo.22855666](https://doi.org/10.5281/zenodo.22855666)
**🆔 ORCID:** [0009-0003-8529-2638](https://orcid.org/0009-0003-8529-2638)

---

## The one command (after setup)

```
python full-benchmark.py ^
    "Qwen/Qwen2.5-3B-Instruct-GGUF" ^
    "microsoft/Phi-3-mini-4k-instruct-gguf" ^
    "meta-llama/Llama-3.2-3B-Instruct" ^
    "google/gemma-3-4b-it-qat-q4_0-gguf=google/gemma-3-4b-it"
```

(Linux: replace `^` with `\` line continuations, or put it on one line.)

That single command runs the **entire study** for the four families:

- **Stage A — selection** (per family, quant ladder Q8_0 -> Q6_K ->
  Q5_K_M -> Q4_K_M -> Q3_K_M -> Q2_K, stopping at the first rung that
  passes):
  1. **Download** the rung file (or the f16 / safetensors to create it).
  2. **Create** missing quants (safetensors -> f16 -> quantize, pinned
     toolchain).
  3. **Bench** it with `live-bench.py` (5 real multi-turn conversations,
     worst-turn metric).
  4. **Analyze**: PASS if worst turn >= floor - 2*sigma. First PASS wins.
- **Stage B — accuracy**: full strict **ARC-Challenge** (1,172 questions,
  logprob letter scoring, temperature 0) on each selected model.
- **Stage C — ranking**: exact **McNemar** pairwise tests; the final
  output is the ranking with separation verdicts.

The script is **idempotent and resumable**: `benchmark-state.json` is
saved after every phase. If anything fails, it stops with guidance;
fix the cause and **rerun the exact same command** — completed phases
are never repeated. Use `--dry-run` to preview the plan without
downloading anything.

---

## Reproduction guide (Windows 10/11 and Linux)

You need about **50 GB of free disk** and a **Vulkan-capable GPU**
(any modern AMD/Intel/NVIDIA iGPU or dGPU with an up-to-date driver).
Everything below is run from the repository root.

### Step 1 — clone this repo

```powershell
git clone https://github.com/dzaragoza/LLM-benchmark.git
cd LLM-benchmark
```

### Step 2 — llama.cpp binaries (pinned build b10964)

Download the **Vulkan prebuilt** for your OS from the pinned release
(all asset names verified against the release manifest):

- Release: https://github.com/ggml-org/llama.cpp/releases/tag/b10964
- Windows: `llama-b10964-bin-win-vulkan-x64.zip`
- Linux:   `llama-b10964-bin-ubuntu-vulkan-x64.tar.gz`

Extract it **into the repo root** so that these paths exist:

- Windows: `llama-b10964-gpu\llama-server.exe` and
  `llama-b10964-gpu\llama-quantize.exe`
- Linux: `llama-b10964-gpu/llama-server` and
  `llama-b10964-gpu/llama-quantize`

If the archive extracts into its own folder, just rename that folder
to `llama-b10964-gpu`. (If the archive has an inner folder, move the
binaries up one level.) The scripts find the binaries automatically,
including the `llama-server.exe` name on Windows — no configuration
needed.

**CPU-only fallback:** `llama-b10964-bin-win-cpu-x64.zip` /
`llama-b10964-bin-ubuntu-x64.tar.gz` work too (slower; the script
passes `-ngl 99` which is ignored gracefully by CPU builds).

### Step 3 — llama.cpp converter checkout (pinned commit b29c606e2)

The safetensors -> f16 conversion uses the pinned converter from the
same llama.cpp version:

```powershell
git clone https://github.com/ggml-org/llama.cpp llama.cpp-tmp
cd llama.cpp-tmp
git checkout b29c606e2
cd ..
Move-Item llama.cpp-tmp llama.cpp
```

Linux is the same with `git clone ... llama.cpp-tmp && cd llama.cpp-tmp
&& git checkout b29c606e2 && cd .. && mv llama.cpp-tmp llama.cpp`.

Verify: `llama.cpp\convert_hf_to_gguf.py` (Windows) /
`llama.cpp/convert_hf_to_gguf.py` (Linux) must exist.

### Step 4 — Python environment

Python 3.10+ required (the scripts are pure stdlib + the pinned deps).

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks the activation script, run once per session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Linux (bash):

```bash
python3 -m venv .venv
source .venv/bin/activate            # fish: source .venv/bin/activate.fish
python3 -m pip install -r requirements.txt
```

On openSUSE use the repo venv as shown (`pip` is "externally managed"
system-wide).

### Step 5 — Hugging Face access (needed for gated models)

1. Create/log in to a Hugging Face account.
2. Accept the license on the gated model pages (visit while logged in):
   - https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct
   - https://huggingface.co/google/gemma-3-4b-it
3. Create a read token at https://huggingface.co/settings/tokens and:

```powershell
hf auth login
```

(If `hf` is not found: `python -m pip install "huggingface_hub[cli]"`.)

### Step 6 — run the benchmark

```powershell
python full-benchmark.py ^
    "Qwen/Qwen2.5-3B-Instruct-GGUF" ^
    "microsoft/Phi-3-mini-4k-instruct-gguf" ^
    "meta-llama/Llama-3.2-3B-Instruct" ^
    "google/gemma-3-4b-it-qat-q4_0-gguf=google/gemma-3-4b-it"
```

Expect several hours total (dominated by downloads and the 4 x 1,172
ARC questions). Every phase prints its progress; on failure it stops
with **possible causes and fixes** — address the cause and rerun the
same command to resume.

**The speed floor is tier-specific.** The default `--floor 20` (worst
turn, tokens/s) is the comfort line calibrated on a **102.4 GB/s**
system-RAM machine (LPDDR5X dual channel). Generation speed scales
roughly linearly with memory bandwidth, so on a 51.2 GB/s machine pass
`--floor 10`, on 25.6 GB/s pass `--floor 5`, etc. — or keep the default
and expect the ladder to descend to smaller quants (a family may find
no passing rung, which the script reports cleanly). Pick the floor
**before** the run and keep it fixed: it is part of the protocol.

### Step 7 — outputs

| File | What it is |
|---|---|
| `benchmark-state.json` | resume state (safe to delete to start over) |
| `benchmark-results.json` | full results: selection history, ARC scores, McNemar ranking |
| `arc-results/*.csv` | per-question ARC results (pairwise analysis, timings) |
| `models/<family>/*.live-dump.json` | per-turn live-bench data for every rung tested |

Rerunning is always safe: complete results are detected and reused.

---

## Provenance

Every selected model file traces to **first-party model-owner weights**
plus the **pinned toolchain**: llama.cpp build b10964 (commit b29c606e2)
for binaries and converter, with quantization done locally by
`llama-quantize`. No third-party quantizations are used for selection.
Pre-made rungs are downloaded only from the model owner's official
repos. The QAT Q4_0 file for Gemma is the first-party
google/gemma-3-4b-it-qat-q4_0-gguf release; other Gemma rungs are
self-quantized from google/gemma-3-4b-it safetensors (the `=` in the
family spec separates "download repo" from "source repo").

## Protocol notes (pre-registered, fixed)

- **Speed metric:** worst turn across 5 fixed Arena conversations
  (corpus committed at `live-corpus.json`, seed 1024, reply-length
  p75 answer cap). Verdict: worst >= floor - 2*sigma (sigma = standard
  error of per-conversation worsts).
- **Accuracy metric:** strict ARC-Challenge letter-answer protocol —
  raw completion prompt, max_tokens=1, temperature 0, logprob scoring;
  no chain-of-thought. Full test split, 1,172 questions, cached in
  `arc-ARC-Challenge-test-1172.json` after first download.
- **Statistics:** exact (binomial) McNemar on paired per-question
  results; consecutive-rank gaps are reported as separated /
  not separated at p < 0.05.
- Both servers run on fixed ports (8077 live, 8081 ARC); leftover
  servers are killed and their ports verified free between runs
  (Windows uses `taskkill /T /F` automatically).

## License

- **Report and notebook:** CC BY 4.0
- **Code:** MIT

## Citation

```bibtex
@misc{zaragoza2026smallmodels,
  author       = {Daniela Zaragoza Rodriguez},
  title        = {Small Models, Big Claims: Choosing and Quantizing Local LLMs on an Integrated GPU},
  year         = {2026},
  doi          = {10.5281/zenodo.22855666},
  url          = {https://doi.org/10.5281/zenodo.22855666}
}
```
