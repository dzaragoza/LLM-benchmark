# LLM-benchmark — local LLM selection & benchmarking

Companion repository for **"Small Models, Big Claims"** — an independent
measurement study of small instruct LLMs running from system RAM on
integrated GPUs, with the llama.cpp Vulkan backend.

**📄 Report (study #1):** [DOI: 10.5281/zenodo.22855666](https://doi.org/10.5281/zenodo.22855666)
**🆔 ORCID:** [0009-0003-8529-2638](https://orcid.org/0009-0003-8529-2638)

---

## The one command (after setup)

```
python full_benchmark.py ^
    "meta-llama/Llama-3.2-1B-Instruct-GGUF" ^
    "Qwen/Qwen2.5-1.5B-Instruct-GGUF" ^
    "google/gemma-3-1b-it-qat-q4_0-gguf=google/gemma-3-1b-it" ^
    "HuggingFaceTB/SmolLM2-1.7B-Instruct"
```

(Linux: replace `^` with `\` line continuations, or put it on one line.)

That single command runs the **entire study** for the four families:

- **Stage A — selection** (per family, quant ladder Q8_0 -> Q6_K ->
  Q5_K_M -> Q4_K_M -> Q3_K_M -> Q2_K, stopping at the first rung that
  passes):
  1. **Download** the rung file (or the f16 / safetensors to create it).
  2. **Create** missing quants (safetensors -> f16 -> quantize, pinned
     toolchain).
  3. **Bench** it with `speed_gate.py` (5 real multi-turn conversations,
     each running ON TOP of a depth prefill — a corpus-text blob sized
     per conversation via `/tokenize` so the deepest turn lands just
     under the 4096 reference depth; worst-turn metric at depth).
  4. **Analyze**: PASS if worst turn >= reader line − 2*sigma
     (protocol v2: the k=1 reader guarantee — 6.5 t/s = 300 wpm at
     0.75 words/token, Brysbaert 2019 — so even a fast reader is never
     made to wait; floor 20 is reported as headroom, not gated).
     First PASS wins.
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

## Repository layout (three layers)

The pipeline is split across scripts in three layers. Users normally
touch only the orchestrator's CLI:

| Layer | Script | Role | Callable as |
|---|---|---|---|
| Top | `full_benchmark.py` | the orchestrator: state/resume, the per-family ladder walk, results assembly | CLI (the main entry point) |
| Middle | `speed_gate.py` | phases 3–4: the worst-turn speed gate (live conversations, mode-suffixed dumps, verdict) | CLI + import |
| Middle | `arc_eval.py` | phase 5: strict ARC-Challenge evaluation | CLI + import |
| Middle | `mcnemar.py` | phase 6: pairwise exact McNemar, the final ranking | CLI + import |
| Bottom | `hf_download.py` | every Hugging Face interaction: downloads, repo listings, ARC question fetch | import only |
| Bottom | `convert_quant.py` | llama.cpp conversion tooling: safetensors -> f16, f16 -> rung | import only |
| Bottom | `llama_server.py` | llama-server lifecycle (launch, health, teardown) and HTTP | import only |

The middle layer never talks to an outside tool directly — all
Hugging Face, llama.cpp-converter and llama-server contact happens in
the bottom-layer interfaces. The former `live-bench.py` was split
along the same seam: its measurement half lives in `speed_gate.py`,
its server-management half in `llama_server.py`.

The corpus build (`--make-sample` / `--make-corpus`) also lives in
`speed_gate.py`:

```
python3 speed_gate.py --make-sample
python3 speed_gate.py --make-corpus
```

---

## Roster selection (pre-registered, transparent)

The four model families were chosen **before any measurement**, by a
fixed procedure with recorded numbers — anyone can audit or repeat it.

**Rules (fixed in advance):**
1. Start from the [Ollama library](https://ollama.com/library?sort=popular)
   ranked by pull count (snapshot: 2026-09-23).
2. **Distinct families only** — no two models from the same model
   family/owner.
3. **Non-thinking category: models must run in non-thinking mode.**
   Pure-reasoning models (no off switch) are excluded here - the
   strict letter-answer ARC protocol requires plain answers. Hybrid
   models (reasoning can be toggled) ARE allowed, run with thinking
   disabled (rule 8).
4. The family must have a size class **predicted to pass the speed
   floor** on the target machine class (51.2 GB/s system RAM; live
   t/s ≈ 26 ÷ model size in GiB, so floor 20 t/s requires ≲ 1.3 GiB
   files, i.e. roughly 1–2B parameters at 4–6 bit).
5. Weights are always **first-party** (the model owner's official
   Hugging Face repos) — popularity picks the family, never the
   weight file.
6. At least one model in the family has a **published research
   paper** (technical report or peer-reviewed).
7. **Prefer the latest generation** within a family: the newest
   model generation supersedes older ones of the same family
   (e.g. qwen3.5 supersedes qwen3).
8. **Hybrid models (toggleable reasoning) are allowed in BOTH
   categories** and are always run in the mode that matches the
   category: thinking enabled in the thinking category, disabled in
   the non-thinking category. Mode control is part of the protocol
   and is logged per run.

**Popularity snapshot and the walk down the list** (Ollama pull counts):

| # | Ollama family | Pulls | Small variant | Verdict |
|---|---|---|---|---|
| 1 | llama3.1 | 119.8M | 8b | excluded — no variant under ~4 GB |
| 2 | deepseek-r1 | 93.1M | 1.5b | excluded — thinking model; 1.5b is a Qwen distill |
| 3 | nomic-embed-text | 86.9M | — | excluded — embedding model |
| 4 | **llama3.2** | **84.2M** | **1b** | **SELECTED** |
| 5 | **qwen2.5** | **40.8M** | **1.5b** | **SELECTED** |
| 6 | **gemma3** | **40.7M** | **1b** | **SELECTED** |
| 7 | qwen3 | 37.8M | 1.7b | excluded — thinking model; same family as qwen2.5 |
| 8 | mistral | 33.7M | 7b | excluded — no small variant |
| 9 | gemma2 | 33.2M | 2b | excluded — same family as gemma3 (superseded) |
| 10 | gemma4 | 25.6M | e2b | excluded — thinking model; same family as gemma3 |
| 11 | llama3 | 25.3M | 8b | excluded — same family as llama3.2 |
| 12 | qwen2.5-coder | 21.7M | 1.5b | excluded — same family as qwen2.5 |
| 13 | qwen3.5 | 20.8M | 0.8b | excluded — same family as qwen2.5 (Qwen series) |
| 14 | phi3 | 18.2M | 3.8b | excluded — smallest variant ~2.2 GiB at Q4, predicted ~10.6 t/s: fails floor 20 at every rung |
| 15 | llava | 15.0M | 7b | excluded — vision model, too big |
| 16 | mxbai-embed-large | 15.0M | — | excluded — embedding model |
| 17 | gpt-oss | 13.1M | 20b | excluded — thinking model; too big |
| 18 | qwen3-coder | 9.5M | 30b | excluded — same family; too big |
| 19 | gemma | 8.3M | 2b | excluded — same family as gemma3 |
| 20 | **smollm2** | **4M** | **1.7b** | **SELECTED** |

Selected, in popularity order: **llama3.2:1b, qwen2.5:1.5b, gemma3:1b,
smollm2:1.7b** — the first four families in the popularity ranking that
satisfy all rules. SmolLM2 was also a study #1 family, giving a direct
cross-study replication check. Its official repo ships safetensors
only, so every rung on its ladder is self-quantized via the pinned
toolchain — the same provenance path as study #1's SmolLM2 variants.

---

## Reproduction guide (Windows 10/11 and Linux)

You need about **20 GB of free disk** and a **Vulkan-capable GPU**
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
   - https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct-GGUF
   - https://huggingface.co/google/gemma-3-1b-it
3. Create a read token at https://huggingface.co/settings/tokens and:

```powershell
hf auth login
```

(If `hf` is not found: `python -m pip install "huggingface_hub[cli]"`.)

### Step 6 — run the benchmark

```powershell
python full_benchmark.py ^
    "meta-llama/Llama-3.2-1B-Instruct-GGUF" ^
    "Qwen/Qwen2.5-1.5B-Instruct-GGUF" ^
    "google/gemma-3-1b-it-qat-q4_0-gguf=google/gemma-3-1b-it" ^
    "HuggingFaceTB/SmolLM2-1.7B-Instruct"
```

Expect a few hours total (dominated by the 4 x 1,172 ARC questions).
Every phase prints its progress; on failure it stops with **possible
causes and fixes** — address the cause and rerun the same command to
resume.

**The speed floor is tier-specific.** The default `--floor 20` (worst
turn, tokens/s) is the comfort line calibrated on a **51.2 GB/s**
system-RAM machine (DDR4-3200 dual channel — the study #1 machine
class; live t/s ≈ 26 ÷ model size in GiB). This roster of ~1–2B models
is sized for that tier. On other tiers scale the floor with bandwidth
(102.4 GB/s → `--floor 40`, 25.6 GB/s → `--floor 10`) and expect the
ladder to land on different rungs. Pick the floor **before** the run
and keep it fixed: it is part of the protocol.

### Step 7 — outputs

| File | What it is |
|---|---|
| `benchmark-state.json` | resume state (safe to delete to start over) |
| `benchmark-results.json` | full results: selection history, ARC scores, McNemar ranking |
| `arc-results/*.csv` | per-question ARC results (pairwise analysis, timings) |
| `models/<family>/*.live-dump.json` | per-turn speed-gate data for every rung tested |

Rerunning is always safe: complete results are detected and reused.

---

## Provenance

Every selected model file traces to **first-party model-owner weights**
plus the **pinned toolchain**: llama.cpp build b10964 (commit b29c606e2)
for binaries and converter, with quantization done locally by
`llama-quantize`. No third-party quantizations are used for selection.
The model families were chosen by **Ollama library popularity** (pull
counts, snapshot 2026-09-23) under the pre-registered roster rules
(see "Roster selection" above), but all weights come from the model
owners' official Hugging Face repos. The QAT Q4_0 file for Gemma is
the first-party google/gemma-3-1b-it-qat-q4_0-gguf release; other Gemma
rungs are self-quantized from google/gemma-3-1b-it safetensors (the
`=` in the family spec separates "download repo" from "source repo").

## Protocol notes (pre-registered, fixed)

- **Speed metric:** worst turn across 5 fixed Arena conversations
  (corpus committed at `live-corpus.json`, seed 1024, reply-length
  p75 answer cap), each conversation depth-prefilled to the 4096
  reference depth via a `/tokenize`-sized corpus-text blob (the KV
  cost is content-independent, so the blob guarantees the measurement
  happens at depth). Verdict: worst >= reader line − 2*sigma (reader
  line 6.5 t/s = 300 wpm at 0.75 words/token, k=1 guarantee,
  Brysbaert 2019; sigma = standard error of per-conversation
  worsts). Floor 20 (k=3) is reported as headroom, not gated. After
  each conversation the gate also takes same-depth noise samples
  (identical follow-ups on the warm slot) — the machine's noise at
  depth, cleanly separated from the KV trend.
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

## Thinking-model category (study #2)

Thinking/reasoning models are judged by the same criteria as the
non-thinking category - the worst-turn speed gate and the full ARC
score - but always in a separate category, never mixed with the
non-thinking ranking.

**Mode rule (rule 8):** hybrid models run here with thinking ENABLED.
The same model may appear in the non-thinking category with thinking
disabled - the pair is a controlled mode comparison.

**Ruling (pre-registered):**

1. The user actively chose a thinking model, so the extra latency
   before an answer is an informed choice and is NOT gated.
2. Reasoning is measured descriptively, not as a penalty: reasoning
   tokens (the server's `reasoning_content`) and their estimated share
   of generated tokens are logged per turn.
3. Thinking is unrestricted: no reasoning budget is imposed. The
   completion cap is the answer cap + 2048 (`THINK_ALLOWANCE`); turns
   where the model spends the whole budget reasoning are flagged
   `answer_empty` in the dump.
4. The server is launched with `--reasoning-format deepseek` (via the
   script's `--thinking` flag) so reasoning text arrives in
   `reasoning_content`, separate from the answer.

**Roster (final, pre-registered 2026-09-24):** walking the same Ollama
popularity snapshot with the rules above minus rule 3, plus "must be a
thinking model (Ollama thinking tag)" and "must have a variant in this
machine's weight class (102.4 GB/s, floor 20: model file <= ~2.6 GiB
after the rung walk, i.e. roughly 3-4B parameters)", yields exactly
two families. Every other thinking family on the walk-down fails a
rule - see the exclusions below. The category is therefore a two-model
head-to-head; exact-McNemar still applies, and ARC scores are directly
comparable to the non-thinking category, because the ARC protocol is
raw-prompt single-token completions where thinking never engages.

- `Qwen/Qwen3.5-4B` (Ollama `qwen3.5:4b`, 20.8M pulls; paper:
  Qwen3.5-Omni Technical Report arXiv 2604.15804, family-level per
  rule 6; first-party safetensors - Qwen publishes no first-party
  Qwen3.5 GGUF, so this pick takes the full self-quantize path.
  Selected over qwen3:4b by rule 7 (latest generation). Variant note:
  the 4b is the 102.4-class member - 9b and up fail the gate). A hybrid model: run in this
category with thinking enabled, and in the non-thinking category
(thinking disabled) as the Qwen family's rule-7 representative there
- superseding the measured qwen2.5:3b, which is retired from the
roster (its result is retained in the results file as a
superseded-family data point)
- `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF` (Ollama `nemotron-3-nano:4b`,
  839K pulls; paper: Nemotron 3 white paper + Nano 3 technical report,
  arXiv 2512.19017; first-party GGUF, Q4_K_M ships at 2.8 GB - one of
  the very few 4b-class files that is itself borderline for the gate;
  the rung walk may have to descend to Q4_0 to pass floor 20). A hybrid model: run here with
  reasoning enabled; its non-thinking mode is NOT measured unless it
  is needed as a family representative (the NVIDIA family's
  non-thinking slot is not part of this study's roster)

Walk-down exclusions (thinking families, with the rule that removes
them): deepseek-r1 (93.1M - no class member: 1.5b is a 51.2-class
model, 7b is too big for the gate), qwen3 (superseded by
qwen3.5, rule 7), qwen3.6 / qwen3.8 / qwen3-vl (same Qwen family as
qwen3.5), gemma4 (e2b at 2.3B effective
is sub-class, author ruling; e4b ~5 GB fails the gate at every rung),
gpt-oss / glm-4.7-flash / glm-5.1 / magistral / minimax-m2.7 /
nemotron-3-super (no variant passes the gate), lfm2.5-thinking (1.2b,
sub-class, author ruling), phi4-mini-reasoning (reasoning in substance
but carries no Ollama thinking tag - category membership is
tag-defined, author ruling).



Reasoning capture uses `--reasoning-format deepseek`. Caveat: Gemma 4
marks thinking with its own channel tokens and LFM2.5's convention is
unverified - check the first turn dump of each family before a full run
(reasoning landing in `content` is a measured finding, not a silent miss).

Run it with `--thinking` and separate state/results files so the two
categories stay independent:

```
python3 full_benchmark.py --thinking \
  --state-file benchmark-state-thinking.json \
  --results-file benchmark-results-thinking.json \
  "Qwen/Qwen3.5-4B" \
  "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF"
```

(Pass `--thinking` on any `--arc-only` rerun too.)

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
