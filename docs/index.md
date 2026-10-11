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
  - Memory bandwidth needed: **51 GB/s or faster**. The lowest
    configuration that meets it, and others that match it exactly:
    - DDR4-3200 dual channel (51.2 GB/s) - the lowest match
    - DDR5-3200 dual channel (51.2 GB/s)
    - DDR5-6400 single channel (51.2 GB/s)
    - DDR4-1600 quad channel (51.2 GB/s)
    - Anything faster also works.
- **Dedicated GPU** — the model runs from the card's VRAM:
  - VRAM needed: **4 GB**. Any dedicated GPU has high enough bandwidth.

**llama.cpp command line:**

```
llama-server -m Qwen3.5-2B-Q8_0.gguf -c 262144 --cache-type-k q4_0 --cache-type-v q4_0 -fa on --parallel 1 --reasoning-budget 512
```

**What each argument does:**

- `-m Qwen3.5-2B-Q8_0.gguf` — the model file. `Q8_0` is the weights
  quantization: 8-bit weights (1.92 GB for this model). The study's
  central finding is that **weights are the value axis** — spend your
  memory budget on the highest weights quality that fits, before
  anything else.
- `-c 262144` — the context window: how many tokens of conversation
  and documents the model can hold at once. This is 256k, the deepest
  the benchmark measures. A bigger window is only worth it if the
  model actually uses it — the score certifies that it does.
- `--cache-type-k q4_0 --cache-type-v q4_0` — quantize the K and V
  attention caches to 4 bits. The caches grow with context (they hold
  every token's attention state); at 256k they would cost ~3 GB
  unquantized. At q4_0 they cost a fraction of that, and the study
  measured the quality cost of doing so as **undetectable** across six
  independent instruments (score, margins, depth curves, speed) —
  the memory goes further and the model does not notice.
- `-fa on` — flash attention. A faster, more memory-efficient attention
  implementation. Required when quantizing the caches on llama-server.
- `--parallel 1` — one request slot. The whole memory budget serves a
  single conversation; more slots split the context window between them.
- `--reasoning-budget 512` — caps the model's hidden thinking. Qwen3.5 is
  a hybrid reasoning model: without a cap it can spend thousands of
  invisible tokens before every answer, each one reading the whole
  context — at 256k depth that is minutes of silence per turn. The
  benchmark itself runs with thinking disabled; for interactive use
  the study's measured rule is: **think in hundreds of tokens, never
  thousands**. Set the cap to what your patience allows — at this
  model's measured ~30 tokens/s, 512 thinking tokens cost about 17
  seconds before the answer starts.

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

## All results (all measured within the 4 GB budget)

Every model below was measured under the same constraint: a fixed 4 GB GPU memory budget, one fixed test corpus, each model scored on how many facts it still finds when they live deep in its context window. The score is credit — partial recall earns partial credit, so a bigger window only pays when the model actually uses it. The iGPU bandwidth column shows what your system memory needs to feed the model at a comfortable reading speed.

| model | best context | GPU memory | iGPU bandwidth needed | score | how to read it |
|---|---|---|---|---|---|
| Qwen3.5-2B | 256k | 2.6 GB | 51 GB/s | 6.9/30 | the reach winner — still improving at its deepest context |
| Qwen3.5-0.8B | 256k | 2.8 GB | 56 GB/s | 4.5/30 | the runner-up at the same depth — half the size, two-thirds the score |
| phi-4-mini-instruct | 32k | 3.9 GB | 51 GB/s | 3.4/15 | strong at short reach |
| AI21-Jamba2-3B | 256k | 2.9 GB | 54 GB/s | 2.8/30 | reaches deep but earns little there |
| Qwen3-1.7B | 32k | 3.9 GB | 51 GB/s | 2.4/15 | its 40k trained window is the limit |
| granite-3.3-2b-instruct | 64k | 3.9 GB | 57 GB/s | 2.0/20 | |
| SmolLM3-3B | 64k | 3.9 GB | 57 GB/s | 1.8/20 | |
| Qwen2.5-1.5B | 32k | 3.8 GB | 56 GB/s | 1.5/15 | its 32k trained window is the limit |
| MiniCPM4-0.5B | 32k | 1.2 GB | 18 GB/s | 1.4/15 | the budget pick — fits in half the memory, half the bandwidth |
| MiniCPM5-2B | 128k | 3.7 GB | 54 GB/s | 0.9/25 | |

Models that scored zero are left out of the table: two granite hybrids answer the wrong thing (the value instead of the variable names) and two models could not run the benchmark at all — their full answer logs are in the repository for inspection.

**Memory numbers are the GPU footprint** — llama-server's own measured breakdown of weights + context + compute on the graphics side. The whole-machine figure is a little higher (the host keeps a small share); budget roughly half a GB more when planning system RAM.

**Bandwidth numbers** are the minimum: your system needs at least this much, or faster. They come from the study's measured law, expressed in *effective* bandwidth — `1/t = size/76.5 + 1/74` — where **76.5 GiB/s is the measured efficiency of real decoding: about 75% of the memory's spec bandwidth**. A GPU never streams at spec — kernel overhead, cache misses, and driver costs eat about a quarter of it — so do not compare these numbers against your RAM's rated speed: compare against about 75% of it. These are what a system needs to feed each model at a comfortable reading speed (300 words per minute). A dedicated GPU meets the requirement by default — it only bites integrated graphics, which serve from system RAM.
