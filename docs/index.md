# Pick your model

Pick the **largest context size that fits your machine** from the list below. Bigger context means the model can work with longer documents — more pages, more code, longer conversations — without losing track of what was said at the beginning. A model certified at 16k handles a 16k-token document reliably; at smaller sizes everything fits more easily, so when in doubt, go bigger if your machine allows.

Each section is one certified choice: the model, the configuration to run it with, and what your machine needs.

> **Two kinds of machine — check yours before reading the numbers:**
>
> **System RAM + iGPU** (integrated graphics: AMD Radeon 780M, Intel Arc iGPU, Apple M-series, most laptops): the model runs from your **system RAM** — use the *RAM needed* number.
>
> **VRAM + dedicated GPU** (a separate graphics card: RTX 4060, RX 7600, ...): the model runs from the card's **VRAM** — use the *VRAM needed* number.
>
> A dedicated GPU is **optional**. Both winners run perfectly well from system RAM on an iGPU.
>
> **The bandwidth requirement is only for iGPU systems.** Any dedicated GPU on the market meets it by a wide margin - memory bandwidth only becomes a constraint when the model is served from system RAM.

## 16k context

- **Model**: Qwen2.5-1.5B-Instruct
- **Configuration**: `Qwen2.5-1.5B-Instruct-f16.gguf` — f16 weights, f16 K cache, f16 V cache, context 16,384
- **Memory bandwidth needed (iGPU only)**: 25 GB/s — minimum configurations that meet it:
  - DDR4-3200 single channel (25.6 GB/s)
  - DDR4-1600 dual channel (25.6 GB/s)
- **System RAM needed (iGPU)**: 4 GiB
- **VRAM needed (dedicated GPU, optional)**: 4 GiB
- **Example**:

```bash
llama-server -m Qwen2.5-1.5B-Instruct-f16.gguf -c 16384 --cache-type-k f16 --cache-type-v f16 -fa on --parallel 1
```

## 8k context

- **Model**: Qwen2.5-1.5B-Instruct
- **Configuration**: `Qwen2.5-1.5B-Instruct-f16.gguf` — f16 weights, f16 K cache, f16 V cache, context 8,192
- **Memory bandwidth needed (iGPU only)**: 23 GB/s — minimum configuration that meets it:
  - DDR4-2933 single channel (23.5 GB/s)
- **System RAM needed (iGPU)**: 4 GiB
- **VRAM needed (dedicated GPU, optional)**: 4 GiB
- **Example**:

```bash
llama-server -m Qwen2.5-1.5B-Instruct-f16.gguf -c 8192 --cache-type-k f16 --cache-type-v f16 -fa on --parallel 1
```

## 4k context

- **Model**: granite-4.0-h-1b
- **Configuration**: `granite-4.0-h-1b-f16.gguf` — f16 weights, f16 K cache, f16 V cache, context 4,096
- **Memory bandwidth needed (iGPU only)**: 23 GB/s — minimum configuration that meets it:
  - DDR4-2933 single channel (23.5 GB/s)
- **System RAM needed (iGPU)**: 4 GiB
- **VRAM needed (dedicated GPU, optional)**: 4 GiB
- **Example**:

```bash
llama-server -m granite-4.0-h-1b-f16.gguf -c 4096 --cache-type-k f16 --cache-type-v f16 -fa on --parallel 1
```
