# The certified models — what to run and what it takes

The f16 context-depth tournament on a 102.4 GB/s system-RAM machine,
certified to 2 sigma. One section per gold-medal model, deepest
certified depth first: the optimum settings, the memory it needs, and
the memory bandwidth your machine must have.

## Qwen2.5-1.5B-Instruct

**The deepest certified model in the study: gold at 16k context.**

- **Optimum settings**: f16 weights (the `Qwen2.5-1.5B-Instruct-f16`
  GGUF), context = the depth you need, up to **16,384 tokens** — the
  2-sigma certified ceiling at f16. It also holds gold at 8k and 4k.
  Beyond 16k it died to the free-word-extraction gate (one hair under
  the certification bar at 32k), so treat 16k as its proven limit.
- **Quant**: f16 — the study's first pass measures every model at full
  f16 precision to establish maximum quality and maximum size on the
  102.4 GB/s machine class before any compression is considered. No
  smaller quant of this model has been certified yet; when one is, it
  appears here.
- **Memory**: **4 GiB** of system RAM at 16k context — llama-server's
  own memory breakdown at that depth: weights 3.31 GiB + KV context
  0.44 GiB + compute buffers 0.09 GiB = 3.85 GiB total, rounded up.
- **Minimum bandwidth**: **24.3 GB/s** to stay above the 5 w/s reader
  line at its worst measured turn (21.1 t/s at 102.4 GB/s; speed scales
  linearly with bandwidth).

## granite-4.0-h-1b

**The fewest-parameter gold medalist: gold at 4k context.**

- **Optimum settings**: f16 weights, context = **4,096 tokens** — its
  trained window is 4k, which makes 4k its terminal rung. It accepted
  there under the 2-sigma bar and is the smallest certified model in
  the study.
- **Quant**: f16 — same ruling as above: full precision first, the
  compression study comes later.
- **Memory**: **4 GiB** of system RAM at 4k context — llama-server's
  own memory breakdown: weights 3.01 GiB + KV context 0.09 GiB +
  compute buffers 0.06 GiB = 3.15 GiB total, rounded up. Smaller than
  Qwen at every depth, as its smaller weights predict.
- **Minimum bandwidth**: **22.5 GB/s** (worst measured turn 22.8 t/s at
  102.4 GB/s).

## Bandwidth: what meets the minimum

Both winners need ~24 GB/s. Speed scales linearly with memory bandwidth
(validated at 102.4 GB/s): your machine's memory bandwidth must be at
least min-BW × (5 ÷ measured t/s). Configurations that clear it:

| Configuration | Bandwidth | Verdict |
|---|---|---|
| DDR5-6400 dual channel | 102.4 GB/s | far above the line |
| DDR5-5600 dual channel | 89.6 GB/s | far above the line |
| DDR5-4800 dual channel | 76.8 GB/s | far above the line |
| DDR4-3200 dual channel | 51.2 GB/s | comfortably above |
| DDR5-4800 single channel | 38.4 GB/s | comfortably above |
| DDR4-2400 dual channel | 38.4 GB/s | comfortably above |
| DDR4-3200 single channel | 25.6 GB/s | just above the line |
| DDR4-2400 single channel | 19.2 GB/s | below — no certified depth guaranteed readable |

## How the numbers are measured

- **Memory**: llama-server's own memory breakdown at the model's
  certified depth — weights + KV context + compute buffers, the
  serving footprint as the runtime itself accounts it. On the iGPU all
  of it lives in system RAM, but part may reside in the UMA region the
  BIOS reserves for the GPU — budget your machine's UMA carve-out
  (typically 512 MiB–2 GiB in BIOS settings) on top of the number
  above.
- **Bandwidth**: the linear law — min bandwidth = 102.4 × 5 ÷ measured
  worst-turn t/s.
- **Gold medal**: exclusive per depth — among the models certified at
  2 sigma (Wilson lower bound ≥ 0.50, ≥ 10 cells per gate), the one
  with the fewest parameters.
- Deeper rungs (32k–256k): no gold medal yet. This page updates with
  every new gold.
- The full protocol and evidence trail: [protocol.md](../md/protocol.md).
