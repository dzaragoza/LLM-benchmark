# Pick your model

Pick the **largest context size that fits your machine** from the list below. Bigger context means the model can work with longer documents — more pages, more code, longer conversations — without losing track of what was said at the beginning. A model certified at 16k handles a 16k-token document reliably; at smaller sizes everything fits more easily, so when in doubt, go bigger if your machine allows.

Each section is one certified choice: the model, the configuration to run it with, and what your machine needs.

## 16k context

- **Model**: Qwen2.5-1.5B-Instruct
- **Configuration**: f16 GGUF (`Qwen2.5-1.5B-Instruct-f16`), context 16,384
- **Memory bandwidth needed**: 25 GB/s
  - single channel: DDR5-4800 or faster
  - dual channel: DDR4-3200 or faster
  - quad channel: any listed generation
- **RAM needed (iGPU)**: 4 GiB
- **VRAM needed (dedicated GPU)**: 4 GiB

## 8k context

- **Model**: Qwen2.5-1.5B-Instruct
- **Configuration**: f16 GGUF (`Qwen2.5-1.5B-Instruct-f16`), context 8,192
- **Memory bandwidth needed**: 23 GB/s
  - single channel: DDR5-4800 or faster
  - dual channel: DDR4-3200 or faster
  - quad channel: any listed generation
- **RAM needed (iGPU)**: 4 GiB
- **VRAM needed (dedicated GPU)**: 4 GiB

## 4k context

- **Model**: granite-4.0-h-1b
- **Configuration**: f16 GGUF (`granite-4.0-h-1b-f16`), context 4,096
- **Memory bandwidth needed**: 23 GB/s
  - single channel: DDR5-4800 or faster
  - dual channel: DDR4-3200 or faster
  - quad channel: any listed generation
- **RAM needed (iGPU)**: 4 GiB
- **VRAM needed (dedicated GPU)**: 4 GiB
