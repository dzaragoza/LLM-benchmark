# Pick your model

Pick the **largest context size that fits your machine** from the list below. Bigger context means the model can work with longer documents — more pages, more code, longer conversations — without losing track of what was said at the beginning. A model certified at 16k handles a 16k-token document reliably; when in doubt, go bigger if your machine allows.

**You need ONE of the two options in each section — never both.** An integrated GPU (iGPU) uses your system RAM; a dedicated GPU uses its own VRAM. If your machine has only an iGPU (most laptops), read the RAM line. If it has a dedicated graphics card, read the VRAM line and ignore the bandwidth requirement.

## 256k context — the best reach

- **Model**: Qwen3.5-2B — Q8_0 weights, q8_0 K cache, q5_0 V cache

**Pick ONE — you do not need both:**

- **Integrated GPU (iGPU)** — the model runs from system RAM:
  - System RAM needed: **4 GB**
- **Dedicated GPU** — the model runs from the card's VRAM:
  - VRAM needed: **4 GB**. Any dedicated GPU has high enough bandwidth.

**llama.cpp command line:**

```bash
llama-server -m Qwen3.5-2B-Q8_0.gguf -c 262144 --cache-type-k q8_0 --cache-type-v q5_0 -fa on --parallel 1
```

## All results

Every model below was measured with the same benchmark: a fixed 4 GB memory budget, one fixed test corpus, each model scored on how many facts it still finds when they live deep in its context window. The score is credit — partial recall earns partial credit, so a bigger window only pays when the model actually uses it.

| model | best context | memory (GPU) | score | how to read it |
|---|---|---|---|---|
| Qwen3.5-2B | 256k | 3.5 GB | 6.9/30 | the reach winner — still improving at its deepest context |
| Qwen3.5-0.8B | 128k | 3.9 GB | 4.5/25 | peaks at 128k, then the cache cost overtakes it |
| Qwen3-1.7B | 32k | 3.9 GB | 2.5/15 | its 40k trained window is the limit |
| granite-3.1-2b | 32k | 3.9 GB | 2.3/15 | peaks at 32k, declines deeper |
| Qwen2.5-1.5B | 32k | 3.8 GB | 1.7/15 | its 32k trained window is the limit |
| MiniCPM4-0.5B | 32k | 1.2 GB | 1.4/15 | |
| MiniCPM5-2B | 128k | 3.7 GB | 1.2/25 | |

Models that scored zero are left out of the table: two granite hybrids answer the wrong thing (the value instead of the variable names) and two models could not run the benchmark at all — their full answer logs are in the repository for inspection.

**Memory numbers are the GPU footprint** — llama-server's own measured breakdown of weights + context + compute on the graphics side. The whole-machine figure is a little higher (the host keeps a small share); budget roughly half a GB more when planning system RAM.
