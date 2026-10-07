# Which model should I run? — gold medal winners per context depth

The f16 context-depth tournament on a 102.4 GB/s system-RAM machine,
certified to 2 sigma. For each context depth that has a gold medal: the
winner (the certified model with the fewest parameters), the minimum RAM
you need to serve it from system memory (CPU/iGPU), the VRAM for GPU
serving, and the minimum memory bandwidth to stay above the 5 words/second
reader line — with the memory configurations that meet it.

Sorted deepest-first: if your machine clears the 16k row, that is the
deepest certified context in the study.

| Context depth | Gold medal model | Min RAM (CPU/iGPU) | Min VRAM (GPU) | Min bandwidth | Measured speed @102.4 GB/s |
|---|---|---|---|---|---|
| **16k** | Qwen2.5-1.5B-Instruct | 3.6 GiB | 3.6 GiB | 24.3 GB/s | 21.1 t/s |
| **8k** | Qwen2.5-1.5B-Instruct | 3.4 GiB | 3.4 GiB | 22.9 GB/s | 22.4 t/s |
| **4k** | granite-4.0-h-1b | 4.2 GiB | 4.2 GiB | 22.5 GB/s | 22.8 t/s |

Deeper rungs (32k–256k): no gold medal yet — 32,768 is measured but
unconquered; the deepest challenger died one hair under the certification
bar. This page updates with every new gold medal.

## Memory configurations that clear the bandwidth minimum

Speed scales linearly with memory bandwidth (measured at 102.4 GB/s):
your machine needs at least **24.3 GB/s** to run the deepest winner above
the reader line. These common configurations clear it:

| Configuration | Bandwidth | Runs |
|---|---|---|
| DDR5-6400 dual channel | 102.4 GB/s | all depths, far above the line |
| DDR5-5600 dual channel | 89.6 GB/s | all depths, far above the line |
| DDR5-4800 dual channel | 76.8 GB/s | all depths, far above the line |
| DDR4-3200 dual channel | 51.2 GB/s | all depths, comfortably |
| DDR5-4800 single channel | 38.4 GB/s | all depths, comfortably |
| DDR5-5600 single channel | 44.8 GB/s | all depths, comfortably |
| DDR5-6400 single channel | 51.2 GB/s | all depths, comfortably |
| DDR4-3200 single channel | 25.6 GB/s | all depths, just above the line |
| DDR4-2400 dual channel | 38.4 GB/s | all depths, comfortably |

Below 24.3 GB/s (e.g. DDR4-2400 single channel, 19.2 GB/s): no certified
depth is guaranteed readable; expect the reader line to be crossed.

GPU note: every current GPU clears the bandwidth minimum by a wide
margin — VRAM capacity is the only constraint on the GPU side. A card
with 4 GiB runs every winner at its certified depth.

## How the numbers are measured

- **RAM/VRAM**: the measured whole-stack machine cost (MemAvailable
  delta) at the model's certified depth, f16 weights — the same number
  for CPU and GPU serving; treat the fit boundary as soft within
  ~1 GiB.
- **Bandwidth**: the linear law validated on the 102.4 GB/s class —
  min bandwidth = 102.4 × 5 ÷ measured worst-turn t/s.
- **Gold medal**: exclusive per depth — among the models certified at
  2 sigma (Wilson lower bound ≥ 0.50, ≥ 10 cells per gate), the one
  with the fewest parameters.
- The full protocol and evidence trail: [protocol.md](../md/protocol.md).
