# Pick your model

Pick the **largest context size that fits your machine** from the list below. Bigger context means the model can work with longer documents — more pages, more code, longer conversations — without losing track of what was said at the beginning. A model certified at 16k handles a 16k-token document reliably; when in doubt, go bigger if your machine allows.

**You need ONE of the two options in each section — never both.** An integrated GPU (iGPU) uses your system RAM; a dedicated GPU uses its own VRAM. If your machine has only an iGPU (most laptops), read the RAM lines. If it has a dedicated graphics card, read the VRAM line and ignore the bandwidth requirement.

## 4 GB machines — the recommended size

Our benchmark ran on a fixed **4 GB memory budget**, and that is the size we recommend to practitioners: every result below fits in either 4 GB of system RAM with an integrated GPU, or a 4 GB dedicated GPU. If you have less, the smaller-context picks still work; if you have more, the 4 GB configurations are the measured sweet spot.

### The reach winner at 4 GB

- **Model**: Qwen3.5-2B — Q8_0 weights, q8_0 K cache, q5_0 V cache
- **Context**: 262,144 tokens (256k) — the deepest context we measure

**Pick ONE — you do not need both:**

- **Integrated GPU (iGPU)** — the model runs from system RAM:
  - System RAM needed: **4 GB**
  - Memory bandwidth needed: **51 GB/s**. Configurations that match exactly:
    - DDR4-3200 dual channel (51.2 GB/s)
    - DDR5-3200 dual channel (51.2 GB/s)
    - DDR5-6400 single channel (51.2 GB/s)
    - DDR4-1600 quad channel (51.2 GB/s)
- **Dedicated GPU** — the model runs from the card's VRAM:
  - VRAM needed: **4 GB**. Any dedicated GPU has high enough bandwidth.

**llama.cpp command line:**

```bash
llama-server -m Qwen3.5-2B-Q8_0.gguf -c 262144 --cache-type-k q8_0 --cache-type-v q5_0 -fa on --parallel 1
```

## All results (all measured within the 4 GB budget)

Every model below was measured under the same constraint: a fixed 4 GB GPU memory budget, one fixed test corpus, each model scored on how many facts it still finds when they live deep in its context window. The score is credit — partial recall earns partial credit, so a bigger window only pays when the model actually uses it. The iGPU bandwidth column shows what your system memory needs to feed the model at a comfortable reading speed.

| model | best context | GPU memory | iGPU bandwidth needed | score | how to read it |
|---|---|---|---|---|---|
| Qwen3.5-2B | 256k | 3.5 GB | 51 GB/s | 6.9/30 | the reach winner — still improving at its deepest context |
| Qwen3.5-0.8B | 128k | 3.9 GB | 56 GB/s | 4.5/25 | peaks at 128k, then the cache cost overtakes it |
| Qwen3-1.7B | 32k | 3.9 GB | 51 GB/s | 2.5/15 | its 40k trained window is the limit |
| granite-3.1-2b | 32k | 3.9 GB | 57 GB/s | 2.3/15 | peaks at 32k, declines deeper |
| Qwen2.5-1.5B | 32k | 3.8 GB | 56 GB/s | 1.7/15 | its 32k trained window is the limit |
| MiniCPM4-0.5B | 32k | 1.2 GB | 18 GB/s | 1.4/15 | the budget pick — fits in half the memory, half the bandwidth |
| MiniCPM5-2B | 128k | 3.7 GB | 54 GB/s | 1.2/25 | |

Models that scored zero are left out of the table: two granite hybrids answer the wrong thing (the value instead of the variable names) and two models could not run the benchmark at all — their full answer logs are in the repository for inspection.

**Memory numbers are the GPU footprint** — llama-server's own measured breakdown of weights + context + compute on the graphics side. The whole-machine figure is a little higher (the host keeps a small share); budget roughly half a GB more when planning system RAM.

**Bandwidth numbers** come from the study's measured law (`1/t = size/76.5 + 1/74`, fitted on the benchmark machine): they are what a system needs to feed each model at a comfortable reading speed (300 words per minute). A dedicated GPU meets them by default — the requirement only bites integrated graphics, which serve from system RAM.
