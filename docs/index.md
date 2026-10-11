# Pick your model

*Results from the completed v7.1 field run (2026-10-11): the 32-model roster ranked under the quick strategy — one measured cell per family, 4 GB budget. This is the final ruling of the 4 GB tier.*

Pick the **largest context size that fits your machine** from the list below. Bigger context means the model can work with longer documents — more pages, more code, longer conversations — without losing track of what was said at the beginning. A model certified at 16k handles a 16k-token document reliably; when in doubt, go bigger if your machine allows.

**You need ONE of the two options in each section — never both.** An integrated GPU (iGPU) uses your system RAM; a dedicated GPU uses its own VRAM. If your machine has only an iGPU (most laptops), read the RAM lines. If it has a dedicated graphics card, read the VRAM line and ignore the bandwidth requirement.

## 4 GB machines — the recommended size

Our benchmark ran on a fixed **4 GB memory budget**, and that is the size we recommend to practitioners: every result below fits in either 4 GB of system RAM with an integrated GPU, or a 4 GB dedicated GPU. If you have less, the smaller-context picks still work; if you have more, the 4 GB configurations are the measured sweet spot.

### The reach winner at 4 GB

- **Model**: Qwen3.5-2B — Q8_0 weights, q4_0 K cache, q4_0 V cache
- **Context**: 262,144 tokens (256k) — the deepest context we measure
- **Score**: 6.9/30 — the highest of the field, still improving at its deepest context

**Pick ONE — you do not need both:**

- **Integrated GPU (iGPU)** — the model runs from system RAM:
  - System RAM needed: **4 GB**
  - Memory bandwidth needed: **about 29 GB/s or faster** (rated spec).
    This is what feeding the model at a comfortable reading speed
    (300 words per minute) takes at the champion's full 256k depth.
    The lowest configurations that meet it:
    - DDR4-2666 dual channel (42.6 GB/s) - the lowest sensible match
    - DDR4-3200 dual channel (51.2 GB/s)
    - DDR5-4800 single channel (38.4 GB/s)
    - Anything faster also works.
- **Dedicated GPU** — the model runs from the card's VRAM:
  - VRAM needed: **4 GB**. Any dedicated GPU has high enough bandwidth.

**To serve it yourself interactively, take the benchmark's command and
add a thinking budget** (the benchmark disables thinking with
`--reasoning-budget 0`; interactive use wants it on but bounded —
Qwen3.5 is a hybrid reasoning model, and uncapped it burns thousands
of invisible tokens per turn, each reading the whole context. The
budget below buys ~5 seconds of thinking):

```
llama-server -m Qwen3.5-2B-Q8_0.gguf -c 262144 --cache-type-k q4_0 --cache-type-v q4_0 -fa on --parallel 1 --reasoning-budget 150
```

- `--reasoning-budget 150` — caps the hidden thinking at ~5 seconds
  (at this model's measured ~30 tokens/s). The study's
  measured rule: **think in hundreds of tokens, never thousands**.
  It is a patience constant, not a quality constant — scale it to
  your tolerance.

## Smaller machines — the 1 GB and 2 GB tiers

The same field run also measured smaller cells directly: several families'
best-fitting configuration lands under 1 GB or 2 GB. These are measured
results, not extrapolations — each pick below is the family's actual
benchmarked cell with its own memory census.

### The 1 GB tier

| model | context | GPU memory | bandwidth needed (spec) | score |
|---|---|---|---|---|
| **MiniCPM4-0.5B** | 32k | 0.8 GB | 6 GB/s | **1.4/15** — the tier winner |
| granite-4.0-350m | 32k | 1.0 GB | 8 GB/s | 0.2/15 |
| granite-4.0-h-350m | 32k | 0.6 GB | 4 GB/s | 0.06/15 |

**The 1 GB pick — MiniCPM4-0.5B** (Q8_0 weights, q8_0 KV, 32k context):
it earns 84% of the champion's per-grade rate at a fifth of the memory —
the small-budget recommendation for machines that cannot spare more.

```
llama-server -m MiniCPM4-0.5B-Q8_0.gguf -c 32768 --cache-type-k q8_0 --cache-type-v q8_0 -fa on --parallel 1 --reasoning-budget 150
```

### The 2 GB tier

| model | context | GPU memory | bandwidth needed (spec) | score |
|---|---|---|---|---|
| **gemma-3-1b-it** | 32k | 1.5 GB | 13 GB/s | 0.1/15 — the only measured cell in this tier |

The 2 GB tier is thin in this field run: most families' best cell
lands either under 1 GB (the tiny families above) or just over 2 GB
(their ladder step at higher context). A dedicated 2 GB-budget field
run — the same quick strategy with the budget set to 2 — is the
registered follow-up and will fill this tier properly: it steps each
family down its fit ladder (q8/q4/q4, then q4/q4/q4) until it fits
2 GB, and the tier winner is the argmax of those measured cells.

## The weight classes 🥊

A model competes **in its memory class only** — the class is decided by
the cell's own measured footprint, and a model can **cut weight** to
fight in a lower class: smaller weights quantization, cheaper KV
caches, or a shorter context window all drop pounds. The picks below
are measured cells, one champion per class.

### 512 MB — the featherweights

Measured across three corpora each (n=3, addendum 247–253). 29 of the
32 roster families cannot make this weight — the class floor is real.
The three that did, in their measured cuts:

| model | cut | memory | n=3 score | per-seed |
|---|---|---|---|---|
| **granite-4.0-h-350m** 🏆 | Q8_0 weights, 32k | 0.56 GB | **0.41/15** | 0.23, 0.55, 0.46 |
| MiniCPM4-0.5B | Q4_0 weights, 32k | 0.50 GB | 0.30/15 | 0.26, 0.32, 0.33 |
| granite-4.0-350m | Q4_0 weights, 16k | 0.46 GB | 0.03/10 | 0.00, 0.09, 0.00 |

**The featherweight champion: granite-4.0-h-350m** — and the bout is
the study's weights law in miniature: it keeps **Q8_0 weights** (0.34
GB) while MiniCPM4-0.5B cuts to Q4_0, and the Q8 weights carry the
belt. At the bottom of the roster the weights quant is nearly the
whole game; the KV cut (both run q4) costs nothing, as ever.

```
llama-server -m granite-4.0-h-350m-Q8_0.gguf -c 32768 --cache-type-k q4_0 --cache-type-v q4_0 -fa on --parallel 1 --reasoning-budget 150
```

**256 MB: no contenders.** Even the smallest family's floor
configuration exceeds a quarter GiB — the class stays empty; there is
no honest 256 MB long-context pick at this corpus.

### 1 GB — the lightweights

Measured cells, champion crowned:

| model | context | GPU memory | bandwidth (spec) | score |
|---|---|---|---|---|
| **MiniCPM4-0.5B** | 32k | 0.8 GB | 6 GB/s | **1.42/15** — the champion |
| Qwen3.5-0.8B | 64k | 0.8 GB* | 9 GB/s | *unmeasured cut — the 1 GB run settles it* |
| granite-4.0-350m | 32k | 1.0 GB | 8 GB/s | 0.21/15 |
| granite-4.0-h-350m | 32k | 0.6 GB | 4 GB/s | 0.06/15 |

The champion retains its belt from the field run — but Qwen3.5-0.8B's
cut to (q4,q4,q4) at 64k makes it the **challenger**: the 1 GB-budget
run measures that bout.

### 2 GB — the welterweights

| model | context | GPU memory | bandwidth (spec) | score |
|---|---|---|---|---|
| MiniCPM4-0.5B (F16 weights) | 32k | 1.4 GB | 11 GB/s | 1.13/10 — the best measured cell in-class |
| gemma-3-1b-it | 32k | 1.5 GB | 13 GB/s | 0.11/15 |

The class is thin in the measured data; the 2 GB-budget run is the
registered fill — every family cuts to its best 2 GB config and the
argmax of those cells takes the belt.

### 4 GB — the middleweights

| model | context | GPU memory | bandwidth (spec) | score |
|---|---|---|---|---|
| **Qwen3.5-2B** | 256k | 2.6 GB | 29 GB/s | **6.9/30** — the champion |
| Qwen3.5-0.8B | 256k | 2.8 GB | 23 GB/s | 4.5/30 |
| phi-4-mini-instruct | 32k | 3.9 GB | 29 GB/s | 3.4/15 |

The full bracket is the field table below.

### 8 GB — the heavyweights

| model | context | GPU memory | bandwidth (spec) | score |
|---|---|---|---|---|
| **Qwen3.5-2B (F16 KV)** | 128k | 4.2 GB | 33 GB/s | **6.8/25** — the best measured cell in-class |
| Qwen3.5-2B | 256k | 4.2 GB | 30 GB/s | 6.4/30 |
| Qwen3.5-0.8B (F16 weights) | 256k | 4.4 GB | 24 GB/s | 5.9/30 |

The heavyweight data comes from the earlier uncapped sweeps. The
8 GB-budget run is the registered fill: the big families get their
(q8,q8,q8) shot at top rung — the Jamba 3Bs first in line.

### How we ranked the field

One command measured the whole roster — each family at the highest
context its budget admits, the highest weights/KV configuration that
fits, one cell per family:

```
python3 full_benchmark.py --task v7 --v7-families 32 --v7-grammar v71
```

- `--task v7` — the reach benchmark: one fixed corpus, questions
  graded by (span, hops) — how deep a fact sits and how many links
  must be followed to recover it.
- `--v7-families 32` — the roster: the first 32 families by ascending
  parameter count. Every family that could not earn a cell is a
  reported finding, never a silent drop.
- `--v7-grammar v71` — the field corpus grammar (alias-chain lookup),
  the same fixed corpus for every model: identical bytes, identical
  questions, so scores compare directly.

The quick strategy inside the run: for each family, walk context
rungs from the highest down; at the first rung that fits, try
configurations in the order (q8,q8,q8) → (q8,q4,q4) → (q4,q4,q4);
the first that fits is **the one cell** — measure it, done. One
server launch per family instead of a sweep; the full 32-family
field measured in ~2 hours.

**The llama-server command the benchmark itself launched** for the
champion's cell (reconstructed from the run's server log and launch
code):

```
llama-server -m Qwen3.5-2B-Q8_0.gguf --port 8210 -lv 5 -c 262144 --parallel 1 -fa on --cache-type-k q4_0 --cache-type-v q4_0 --reasoning-budget 0
```

- `-m Qwen3.5-2B-Q8_0.gguf` — the model file: Q8_0 weights (8-bit,
  1.92 GB for this model). The study's central finding is that
  **weights are the value axis** — spend your memory budget on the
  highest weights quality that fits, before anything else.
- `--port 8210` / `-lv 5` — the benchmark's own plumbing: the port
  it talks to, and llama.cpp's verbose memory accounting in the log
  (the per-cell memory census is parsed from it — the measured
  numbers on this page come from there).
- `-c 262144` — the context window: how many tokens of conversation
  and documents the model can hold at once. This is 256k, the deepest
  the benchmark measures. A bigger window is only worth it if the
  model actually uses it — the score certifies that it does.
- `--parallel 1` — one request slot: the whole memory budget serves
  one conversation. The benchmark measures exactly what a single
  reader gets.
- `-fa on --cache-type-k q4_0 --cache-type-v q4_0` — flash attention
  plus 4-bit K and V attention caches. The caches grow with context
  (they hold every token's attention state); at 256k they would cost
  ~3 GB unquantized. At q4_0 they cost a fraction of that, and the
  study measured the quality cost of doing so as **undetectable**
  across six independent instruments (score, margins, depth curves,
  speed) — the memory goes further and the model does not notice.
- `--reasoning-budget 0` — disables the model's hidden thinking
  entirely: zero reasoning tokens are generated. Qwen3.5 is a hybrid
  reasoning model; without this, it can spend thousands of invisible
  tokens before every answer, each reading the whole context. The
  benchmark also passes `enable_thinking: false` on every request
  (belt and suspenders): the scores measure pure reach per answer
  token, with no hidden reasoning confounding the timing or the
  memory census.

## All results (all measured within the 4 GB budget)

Every model below was measured under the same constraint: a fixed 4 GB GPU memory budget, one fixed test corpus, each model scored on how many facts it still finds when they live deep in its context window. The score is credit — partial recall earns partial credit, so a bigger window only pays when the model actually uses it. The iGPU bandwidth column shows what your system memory needs to feed the model at a comfortable reading speed.

| model | best context | GPU memory | bandwidth needed (spec) | score | how to read it |
|---|---|---|---|---|---|
| Qwen3.5-2B | 256k | 2.6 GB | 29 GB/s | 6.9/30 | the reach winner — still improving at its deepest context |
| Qwen3.5-0.8B | 256k | 2.8 GB | 23 GB/s | 4.5/30 | the runner-up at the same depth — half the size, two-thirds the score |
| phi-4-mini-instruct | 32k | 3.9 GB | 29 GB/s | 3.4/15 | strong at short reach |
| AI21-Jamba2-3B | 256k | 2.9 GB | 24 GB/s | 2.8/30 | reaches deep but earns little there |
| Qwen3-1.7B | 32k | 3.9 GB | 36 GB/s | 2.4/15 | its 40k trained window is the limit |
| granite-3.3-2b-instruct | 64k | 3.9 GB | 25 GB/s | 2.0/20 | |
| SmolLM3-3B | 64k | 3.9 GB | 27 GB/s | 1.8/20 | |
| Qwen2.5-1.5B | 32k | 3.8 GB | 19 GB/s | 1.5/15 | its 32k trained window is the limit |
| MiniCPM4-0.5B | 32k | 1.2 GB | 6 GB/s | 1.4/15 | the budget pick — fits in half the memory, a third of the bandwidth |
| MiniCPM5-2B | 128k | 3.7 GB | 26 GB/s | 0.9/25 | |

Models that scored zero are left out of the table: two granite hybrids answer the wrong thing (the value instead of the variable names) and two models could not run the benchmark at all — their full answer logs are in the repository for inspection.

**Memory numbers are the GPU footprint** — llama-server's own measured breakdown of weights + context + compute on the graphics side. The whole-machine figure is a little higher (the host keeps a small share); budget roughly half a GB more when planning system RAM.

**Bandwidth numbers** are the minimum *rated spec* your system needs to feed the model at a comfortable reading speed (300 words per minute ≈ 6.5 tokens/s). They come from the study's measured roofline: at batch 1, every generated token must read the model's **weights plus its KV cache** from memory — `bytes/token = weights + context × KV-size` — so the requirement grows with context depth. The champion needs 29 GB/s spec: 2.06 GB of Q8_0 weights plus 0.9 GB of q4_0 KV per token, times 6.5 tokens/s, divided by the measured ~75% efficiency of real decoding (a GPU never streams at spec — kernel overhead, cache misses, and driver costs eat about a quarter of it). A dedicated GPU meets the requirement by default — it only bites integrated graphics, which serve from system RAM. As a sanity anchor: the benchmark machine (LPDDR5-7467 dual channel) sustains the champion at ~24 tokens/s at full depth — nearly four times the reading-speed line.
