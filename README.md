# LLM-benchmark — local LLM selection & benchmarking

Companion repository for **"Small Models, Big Claims"** — an independent
measurement study of small instruct LLMs running from system RAM on
integrated GPUs, with the llama.cpp Vulkan backend.

**📄 Report (study #1):** [DOI: 10.5281/zenodo.22855666](https://doi.org/10.5281/zenodo.22855666)

---

## 🌐 The practitioner pages 🖼️ the study's main artifact

The study's deliverable is not the paper - it is the two static pages a practitioner
opens to answer "which Q8_0 model should I run on my machine?". Both run offline,
no build step, no JavaScript dependencies:

- **[cpu-picker.html](cpu-picker.html)** 🖥️ **Local LLM picker — CPU/iGPU** — serving from **system RAM**:
  pick your DDR generation, JEDEC speed and channel count (DDR to DDR5, single to
  octa), enter your RAM, get the highest-ARC measured model that fits and clears the
  300-wpm reader line at your bandwidth.
- **[gpu-picker.html](gpu-picker.html)** 🖨️ **Local LLM picker — GPU** — serving from a **GPU**: enter your
  card's VRAM, get the same recommendation (bandwidth is never the constraint on
  current cards - the page shows the derivation).

Every recommendation is backed by a v3.1-protocol measurement (reader-wall stall rate,
ARC-Challenge) - the pages only recommend models the study actually ran.
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
  4. **Analyze** (protocol v3.0, addendum 55): the verdict is the
     READER-WALL TEST — the gate streams every turn and simulates the
     registered reader (5.0 w/s = 300 wpm, Brysbaert 2019; 0.45 s
     reaction) on the per-word arrival stream. PASS only if the
     reader NEVER hits the wall on any turn (fails iff ANY word
     arrives after the reader is ready for it — a wall hit is
     unrecoverable, so the bench aborts in flight, addendum 34).
     The flat worst-turn w/s is printed as a diagnostic only (the
     addendum-54 lesson: the span of a tiny answer is pipeline
     overhead, not reading experience). First PASS wins.
- **Stage B — accuracy**: full strict **ARC-Challenge** (1,172 questions,
  logprob letter scoring, temperature 0) on each selected model.
- **Stage C — ranking**: exact **McNemar** pairwise tests; the final
  output is the ranking with separation verdicts.

The script is **idempotent and resumable**: `state/benchmark-state.json` is
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
| Middle | `bench/cells.py` | one-cell primitives: the speed, FWE and VT cell measurements (session 39, addendum 15) | import only |
| Middle | `bench/certify.py` | the gold-certification ladder walk (certify cells, medals) | CLI + import |
| Middle | `bench/tournament.py` | the multi-family tournament (depth ladder per family, medals) | CLI + import |
| Middle | `bench/ladder.py` | ladder helpers (the depth ladder walk) | import only |
| Middle | `bench/size_table.py` | the per-context recommendation table (recommend = fits AND 0 stalls) | CLI + import |
| Middle | `bench/state_store.py` | state load/save, task measurement and storage helpers | import only |
| Middle | `speed_gate.py` | the worst-turn speed gate (live conversations, mode-suffixed dumps, verdict) | CLI + import |
| Middle | `ruler_gate.py` | the RULER instrument: VT (variable tracking), FWE, and the depth probes | CLI + import |
| Bottom | `infra/hf_download.py` | every Hugging Face interaction: downloads, repo listings, ARC question fetch | import only |
| Bottom | `infra/convert_quant.py` | llama.cpp conversion tooling: safetensors -> f16, f16 -> rung | import only |
| Bottom | `infra/llama_server.py` | llama-server lifecycle (launch, health, teardown), HTTP, and stale-server kills | import only |
| Bottom | `infra/git_ops.py` | the git binary seam: add/commit/pull/push for the artifact tail (session 40, addendum 5) | import only |

The middle layer never talks to an outside tool directly — all
Hugging Face, llama.cpp-converter, llama-server and git contact
happens in the bottom-layer interfaces. The former `live-bench.py`
was split along the same seam: its measurement half lives in
`speed_gate.py`, its server-management half in `infra/llama_server.py`.
The retired `arc_eval.py` and `mcnemar.py` were middle layer until
the depth score became the ranking (protocol v4.3).


Dev tools (own CLIs, tested like everything else):

| Tool | Role |
|---|---|
| `code_edit.py` | the verified transactional editor (Vibe's editor, protocol [P]) |
| `code_search.py` | AST-based code search: defs/refs/calls with import-alias resolution |
| `ty_check.py`, `md_check.py`, `js_check.py` | the gate wrappers (ty env, markdown tables, picker pages) |
| `git_push.py` | the sandbox's REST-API push workaround |
| `sandbox_check.py` | the bench machine's pre-flight environment check |

The corpus build (`--make-sample` / `--make-corpus`) also lives in
`speed_gate.py`:

```
python3 speed_gate.py --make-sample
python3 speed_gate.py --make-corpus
```

Standalone instruments (outside the pipeline, one-shot experiments):

| Script | Role |
|---|---|
| `depth_probe.py` | decode speed at exact context depth (prefill blobs; the KV-tax instrument) |
| `lag_analyze.py` | post-hoc lag analysis over existing live dumps (Andes-style stall metrics) |
| `law_fit.py` | the bandwidth law fit + KV arithmetic (T_token = size x ms/GiB + overhead + KV) |
| `session_replicate.py` | replays the gate's conversation live, streaming, with per-token arrival telemetry (the felt-experience calibration instrument) |

---

## Roster selection (pre-registered, transparent)

The roster selection rules are fixed in advance and recorded in
full in **[model-selection.md](model-selection.md)** (ten rules).
The machine's RAM ceiling is measured FIRST (the gallop search on
the champion config), then candidates screen by the registered
ceiling predictor (rule 2): predicted machine cost at 262,144
tokens under the champion's ceiling (4.96 GiB), non-thinking mode
required, speed-gate predictor, first-party weights, paper rule,
v4.3 data hygiene, dry-run pre-flight, and verbatim commands. The
study's practitioner goals are recorded in
**[practitioner-goals.md](practitioner-goals.md)**. The study-#1
popularity walk-down history lives in the lab notebook.

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

Python 3.13+ required (the author's target machine runs 3.13; the
scripts are pure stdlib + the pinned deps, and may use any language
feature through 3.13).

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

**The speed line is tier-specific.** The gate's reader line is
5.0 w/s (the k=1 guarantee); the law that predicts it is calibrated
per machine tier (51.2 GB/s: live t/s ≈ 26 ÷ model size in GiB;
102.4 GB/s: the study #3 machine class). This roster of ~1–2B models
is sized for the 51.2 GB/s tier. On other tiers the same w/s gate
holds — the law refits per tier and the ladder lands on different
rungs. (The k=3 floor-20 comfort line is deleted, addendum 50: an
observation for the report, not a protocol constant.)

### Step 7 — outputs

| File | What it is |
|---|---|
| `state/benchmark-state.json` | resume state (safe to delete to start over) |
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

- **Speed metric (protocol v3.0/v3.1, addenda 55/66):** 50 fixed Arena
  conversations (instrument corpus `data/live-corpus-cal50.json`, seed 1024,
  reply-length p75 answer cap), each depth-prefilled to the 4096
  reference depth via a `/tokenize`-sized corpus-text blob (the KV
  cost is content-independent, so the blob guarantees the measurement
  happens at depth). The gate STREAMS every turn and records the
  per-word arrival stream; the verdict is the READER-WALL TEST: the
  registered reader (5.0 w/s = 300 wpm, Brysbaert 2019; 0.45 s
  reaction) is simulated on each turn's arrivals - a turn fails iff
  the reader EVER hits the wall (any catch-up event; a hit is
  unrecoverable - the verdict is a min - so the bench aborts in
  flight, addendum 34). The flat worst-turn w/s, sigma, the
  words/token ratio and the t/s view are printed as diagnostics
  (the flat test is retired from the verdict: the addendum-54
  degeneracy - a tiny answer's span is pipeline overhead, not
  reading experience). After each conversation the gate also takes
  same-depth noise samples (identical follow-ups on the warm slot)
  — the machine's noise at depth, cleanly separated from the KV
  trend.
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
  --state-file state/benchmark-state-thinking.json \
  --results-file benchmark-results-thinking.json \
  "Qwen/Qwen3.5-4B" \
  "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF"
```

(The addendum-86 tooling removed `--arc-only`/`--arc-models` — ARC now runs on every benched family automatically; pass `--thinking` on the rerun too, with its own state/results files.)

## Study #3 roster (protocol v2.3, T14s, pre-registered 2026-09-26)

The k=1 reader guarantee (worst turn >= 5.0 w/s at depth 4096,
addendum 33) opened the door to each family's highest runnable
member - but the first v2.1-roster run graded the selection
estimator itself (addendum 37): Llama-3.1-8B's law-predicted t/s
landed on target (+5-10%), yet the rung failed the w/s gate at its
worst turn - a terse answer whose words/token (0.144) was far
below the assumed 0.65-0.80 band. The verdict is a min over turns,
so the estimator now uses the family's worst-turn words/token, not
the mean. The v2.2 quant-6 filter then proved too restrictive with
measured constants (addendum 47 re-audit: exactly one family
admitted) - and the v2.2 run showed the cost of that: Qwen3.5-4B
passed at Q8_0, i.e. the filter had left a larger family member
on the table. The author's quant-5 ruling (addendum 48): "If a
model passes with q8, I get suspicious it will have performed
better at a larger model in q4-q8. That is, we are leaving brains
on the table, for roughly the same performance."

**Rules (v2.3):**

1. Ollama library popularity walk-down (snapshot 2026-09-26).
2. One slot per **owner** (author ruling: llama3.1 and llama3.2 are
   one Meta family).
3. Non-thinking or hybrid; hybrids run with thinking disabled.
4. Predicted to pass the gate at **quant 5** (Q5_K_M, the inclusion
   filter per the author's addendum-48 ruling; the estimate is
   t/s × per-family w/t_min, measured or family-anchored; the
   ladder walk still starts at Q8_0 and takes the first PASS).
5. First-party weights only (no third-party quantizations).
6. Published paper per family.
7. Latest generation supersedes older (author ruling: "people want
   the latest and greatest") - Qwen3.5 supersedes Qwen2.5; phi4
   supersedes phi3.
8. Highest runnable member of the family that passes the quant-5
   filter (file + KV + OS in 32 GB).

**Selected (popularity order of the winning rows):**

| Family | Pick | Paper | Provenance |
|---|---|---|---|
| Meta (llama3.2, 84.4M) | Llama-3.2-3B-Instruct | The Llama 3 Herd of Models, arXiv 2407.21783 | safetensors (gated), self-quantize |
| Qwen (qwen3.5, 21.0M) | Qwen3.5-9B | Qwen3.5-Omni Technical Report, arXiv 2604.15804 | safetensors, self-quantize |
| Mistral (33.7M) | Mistral-7B-Instruct-v0.3 | Mistral 7B, arXiv 2310.06825 | safetensors (public), self-quantize |
| Microsoft (phi4, 18.2M) | Phi-4-mini-instruct | Phi-4-Mini Technical Report, arXiv 2503.01743 | safetensors, self-quantize |

Google's slot empties under the quant-5 filter: gemma-3-4b is
excluded by measurement (word-sparse turns fail every rung above
Q2_K, addendum 46; no model debugging per the addendum-47 ruling)
and gemma-4-12b is excluded by prediction (4.39 w/s at Q5_K_M even
on the generous healthy-turn anchor). The slot walks to the next
owner: Microsoft (phi4). Other walk-down exclusions: deepseek-r1
(thinking-only), nomic-embed-text (embedding), qwen3 (superseded),
gemma2 (superseded), gpt-oss (thinking-only), Llama-3.1-8B
(quant-5 fail at 1.64 w/s, own measured w/t_min), Mistral-Nemo-12B
(quant-5 fail at 2.95 w/s), Phi-4-14B (needs w/t_min >= 0.720 at
Q5_K_M, above every family ever measured). Full walk-down with
law estimates and per-pick ladder predictions: lab-notebook
addendum 48.

**Run it (T14s or any 102.4 GB/s / 32 GB machine):**

```
python3 full_benchmark.py --no-thinking --force --roster \
  "Llama-3.2-3B-Instruct,Qwen3.5-9B,Mistral-7B-Instruct-v0.3,Phi-4-mini-instruct" \
  "meta-llama/Llama-3.2-3B-Instruct" \
  "Qwen/Qwen3.5-9B" \
  "mistralai/Mistral-7B-Instruct-v0.3" \
  "microsoft/Phi-4-mini-instruct"
```

All four are non-thinking or hybrid: the run uses `--no-thinking`.
Meta is license-gated on Hugging Face (accept the Llama 3 family
license and log in with `hf auth login`).

## Protocol (constants registry)

Every constant the study uses - author rulings, practical limits,
derived/measured values, and inherited defaults - is registered with
its provenance in [protocol.md](protocol.md). Governance rule: a
constant is single-sourced in the code, and changing one is a
protocol change requiring a notebook addendum.

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
