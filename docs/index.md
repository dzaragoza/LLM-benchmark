# Pick your model

Pick the **largest context size that fits your machine** from the list below. Bigger context means the model can work with longer documents — more pages, more code, longer conversations — without losing track of what was said at the beginning. A model certified at 16k handles a 16k-token document reliably; at smaller sizes everything fits more easily, so when in doubt, go bigger if your machine allows.

**You need ONE of the two options in each section — never both.** An integrated GPU (iGPU) uses your system RAM; a dedicated GPU uses its own VRAM. If your machine has only an iGPU (most laptops), read the iGPU lines. If it has a dedicated graphics card, read the VRAM line and ignore the bandwidth requirement.

## 32k context

- **Model**: Qwen3-1.7B
- **Configuration**: `Qwen3-1.7B-f16.gguf` — f16 weights, f16 K cache, f16 V cache, context 32,768

**Pick ONE — you do not need both:**

- **Integrated GPU (iGPU)** — the model runs from system RAM:
  - System bandwidth needed: 55 GB/s. Minimum that matches:
    - DDR5-7200 single channel (57.6 GB/s)
    - DDR5-3600 dual channel (57.6 GB/s)
  - Minimum system RAM: 8 GiB
- **Dedicated GPU** — the model runs from the card's VRAM:
  - Minimum VRAM: 8 GiB. Any dedicated GPU has high enough bandwidth.

**llama.cpp command line:**

```bash
llama-server -m Qwen3-1.7B-f16.gguf -c 32768 --cache-type-k f16 --cache-type-v f16 -fa on --parallel 1
```

## 16k context

- **Model**: Qwen2.5-1.5B-Instruct
- **Configuration**: `Qwen2.5-1.5B-Instruct-f16.gguf` — f16 weights, f16 K cache, f16 V cache, context 16,384

**Pick ONE — you do not need both:**

- **Integrated GPU (iGPU)** — the model runs from system RAM:
  - System bandwidth needed: 25 GB/s. Minimum that matches:
    - DDR4-3200 single channel (25.6 GB/s)
    - DDR4-1600 dual channel (25.6 GB/s)
    - DDR5-3200 single channel (25.6 GB/s)
    - DDR3-1600 dual channel (25.6 GB/s)
    - DDR3-800 quad channel (25.6 GB/s)
  - Minimum system RAM: 4 GiB
- **Dedicated GPU** — the model runs from the card's VRAM:
  - Minimum VRAM: 4 GiB. Any dedicated GPU has high enough bandwidth.

**llama.cpp command line:**

```bash
llama-server -m Qwen2.5-1.5B-Instruct-f16.gguf -c 16384 --cache-type-k f16 --cache-type-v f16 -fa on --parallel 1
```

## 8k context

- **Model**: Qwen2.5-1.5B-Instruct
- **Configuration**: `Qwen2.5-1.5B-Instruct-f16.gguf` — f16 weights, f16 K cache, f16 V cache, context 8,192

**Pick ONE — you do not need both:**

- **Integrated GPU (iGPU)** — the model runs from system RAM:
  - System bandwidth needed: 23 GB/s. Minimum that matches:
    - DDR4-2933 single channel (23.5 GB/s)
  - Minimum system RAM: 4 GiB
- **Dedicated GPU** — the model runs from the card's VRAM:
  - Minimum VRAM: 4 GiB. Any dedicated GPU has high enough bandwidth.

**llama.cpp command line:**

```bash
llama-server -m Qwen2.5-1.5B-Instruct-f16.gguf -c 8192 --cache-type-k f16 --cache-type-v f16 -fa on --parallel 1
```

## 4k context

- **Model**: granite-4.0-h-1b
- **Configuration**: `granite-4.0-h-1b-f16.gguf` — f16 weights, f16 K cache, f16 V cache, context 4,096

**Pick ONE — you do not need both:**

- **Integrated GPU (iGPU)** — the model runs from system RAM:
  - System bandwidth needed: 23 GB/s. Minimum that matches:
    - DDR4-2933 single channel (23.5 GB/s)
  - Minimum system RAM: 4 GiB
- **Dedicated GPU** — the model runs from the card's VRAM:
  - Minimum VRAM: 4 GiB. Any dedicated GPU has high enough bandwidth.

**llama.cpp command line:**

```bash
llama-server -m granite-4.0-h-1b-f16.gguf -c 4096 --cache-type-k f16 --cache-type-v f16 -fa on --parallel 1
```
