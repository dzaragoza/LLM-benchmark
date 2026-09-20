# LLM-benchmarks

Companion repository for **"Small Models, Big Claims: Choosing and Quantizing Local LLMs on an Integrated GPU"** — an independent measurement study of twelve model/quantization configurations across three model families on an AMD Radeon integrated GPU with the llama.cpp Vulkan backend.

**📄 Report:** [DOI: 10.5281/zenodo.22855666](https://doi.org/10.5281/zenodo.22855666)
**💬 Contact:** orcid.unaudited840@passmail.com · [@dzaragoza.bsky.social](https://bsky.app/profile/dzaragoza.bsky.social)
**🆔 ORCID:** [0009-0003-8529-2638](https://orcid.org/0009-0003-8529-2638)

---

## What's in this repo

| File | Description |
|---|---|
| `Small Models, Big Claims — Markdown Edition.md` | Full technical report (markdown source) |
| `Small Models, Big Claims — Print_PDF Edition.pdf` | Print edition (Computer Modern typesetting) |
| `strict-arc.py` | ARC-Challenge evaluation harness — strict letter-answer protocol, no chain-of-thought |
| `arc-ARC-Challenge-test-800.json` | Cached 800-question set (identical across all runs for paired comparison) |
| `notebook.md` | Lab notebook: 27 sessions with pre-registered predictions and outcomes |


## Key findings (TL;DR)

1. **Champion config:** Qwen2.5-1.5B-Instruct Q5_0 — 75.2% ARC, ~21 tokens/s live, 1.17 GiB
2. **Quant recovery:** Q4→Q6 buys ~+3 percentage points consistently across all three families
3. **Encoding matters for speed:** legacy Q5_0 decodes 7–11% faster than K-quant Q5_K_M, with no accuracy gain
4. **Bandwidth formula:** live t/s ≈ 26 ÷ file size in GiB (±10%)
5. **Paper benchmarks don't transfer across harnesses** — SmolLM2 scored ~20 points below its published impression under our protocol

## Reproducing the results

### Requirements

- [llama.cpp](https://github.com/ggml-org/llama.cpp) — tested with build b10964 (commit b29c606e2), Vulkan backend
- Vulkan-capable GPU (tested on AMD Radeon integrated graphics, 2 GB UMA reservation)
- Python 3.x (for `strict-arc.py`)

### Run the benchmark

```bash
# Download a model (example: the champion config)
huggingface-cli download Qwen/Qwen2.5-1.5B-Instruct-GGUF --include "*Q5_0*"

# Measure speed
llama-bench -m Qwen2.5-1.5B-Instruct-Q5_0.gguf -t 8 -p 0 -n 128 -r 3 -ngl 99

# Measure accuracy
python strict-arc.py --num 800 --model Qwen2.5-1.5B-Instruct-Q5_0.gguf
```

### SmolLM2 self-quantized variants

SmolLM2's official repo ships only Q4_K_M. The Q5_0, Q5_K_M, and Q6_K variants were converted locally:

```bash
huggingface-cli download HuggingFaceTB/SmolLM2-1.7B-Instruct
python convert_hf_to_gguf.py HuggingFaceTB/SmolLM2-1.7B-Instruct --outfile smollm2-1.7b-f16.gguf
llama-quantize smollm2-1.7b-f16.gguf smollm2-1.7b-Q5_0.gguf Q5_0
```

Converter pinned to llama.cpp commit 7d4b92b.

## Hardware

- **CPU:** AMD Ryzen 7 PRO 5755GE (Zen 3, 8C/16T)
- **iGPU:** AMD Radeon Graphics (Vega 8-class, GCN5 — no matrix cores, no integer dot product)
- **RAM:** 64 GB DDR4-3200 dual channel (~51.2 GB/s theoretical peak)
- **BIOS:** 2 GB UMA frame-buffer reservation

This is a worst-case GPU target. If the formula and recommendations hold here, they hold a fortiori on anything faster.

## Software pins

- llama.cpp: build b10964, commit b29c606e2
- Backend: Vulkan (Vulkan SDK, shader-based fp16)
- OS: Windows 11 (PowerShell)
- SmolLM2 converter: llama.cpp commit 7d4b92b

## License

- **Report and notebook:** CC BY 4.0
- **Code (`strict-arc.py`):** MIT

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
