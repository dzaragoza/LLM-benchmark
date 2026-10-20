# models.md — The Model Registry

The roster for the mechanical-sweet-spot benchmark, param-ascending (smallest first — the full benchmark starts at the top of this table). Params are `etc/registry_data.json`'s exact counts; the training window is each model's `max_position_embeddings`. Gated = HF repo requires license acceptance. The paper/report link is the model card's own arXiv citation, or the family's canonical report. Thinking = the card advertises a thinking/reasoning mode (hybrid models count as thinking).

| model name | params (B) | training window | repo | gated? | paper/report | thinking? |
|---|---|---|---|---|---|---|
| granite-4.0-h-350m | 0.3403 | 32,768 | ibm-granite/granite-4.0-h-350m | no | https://arxiv.org/abs/2510.17848 | unknown |
| granite-4.0-350m | 0.3524 | 32,768 | ibm-granite/granite-4.0-350m | no | https://arxiv.org/abs/2510.17848 | unknown |
| SmolLM2-360M-Instruct | 0.3618 | 8,192 | HuggingFaceTB/SmolLM2-360M-Instruct | no | https://arxiv.org/abs/2502.02737 | unknown |
| MiniCPM4-0.5B | 0.4339 | 32,768 | openbmb/MiniCPM4-0.5B | no | https://arxiv.org/abs/2506.07900 | unknown |
| Qwen2.5-0.5B-Instruct | 0.494 | 32,768 | Qwen/Qwen2.5-0.5B-Instruct | no | https://qwenlm.github.io/blog/qwen2.5/ | unknown |
| Qwen3-0.6B | 0.7516 | 40,960 | Qwen/Qwen3-0.6B | no | https://arxiv.org/abs/2505.09388 | thinking |
| Qwen3.5-0.8B | 0.8734 | 262,144 | Qwen/Qwen3.5-0.8B | no | https://qwen.ai/blog?id=qwen3.5 | thinking |
| MiniCPM5-1B | 1.081 | 131,072 | openbmb/MiniCPM5-1B | no | https://arxiv.org/abs/2506.07900 | thinking |
| MiniCPM-1B-sft | 1.36 | 4,096 | openbmb/MiniCPM-1B-sft-bf16 | no | https://arxiv.org/abs/2404.06395 | unknown |
| phi-1 | 1.418 | 2,048 | microsoft/phi-1 | no | https://arxiv.org/abs/2305.08945 | unknown |
| granite-4.0-h-1b | 1.462 | 131,072 | ibm-granite/granite-4.0-h-1b | no | https://arxiv.org/abs/2510.17848 | unknown |
| Qwen2.5-1.5B-Instruct | 1.544 | 32,768 | Qwen/Qwen2.5-1.5B-Instruct | no | https://qwenlm.github.io/blog/qwen2.5/ | unknown |
| granite-4.0-1b | 1.632 | 131,072 | ibm-granite/granite-4.0-1b | no | https://arxiv.org/abs/2510.17848 | unknown |
| SmolLM2-1.7B-Instruct | 1.711 | 8,192 | HuggingFaceTB/SmolLM2-1.7B-Instruct | no | https://arxiv.org/abs/2502.02737v1 | unknown |
| Qwen3-1.7B | 2.032 | 40,960 | Qwen/Qwen3-1.7B | no | https://arxiv.org/abs/2505.09388 | thinking |
| Qwen3.5-2B | 2.274 | 262,144 | Qwen/Qwen3.5-2B | no | https://qwen.ai/blog?id=qwen3.5 | thinking |
| MiniCPM5-2B | 2.517 | 131,072 | openbmb/MiniCPM5-2B | no | https://arxiv.org/abs/2506.07900 | thinking |
| granite-3.1-2b-instruct | 2.534 | 131,072 | ibm-granite/granite-3.1-2b-instruct | no | https://arxiv.org/abs/2502.07437 | unknown |
| granite-3.2-2b-instruct | 2.534 | 131,072 | ibm-granite/granite-3.2-2b-instruct | no | https://arxiv.org/abs/2504.07986 | unknown |
| granite-3.3-2b-instruct | 2.534 | 131,072 | ibm-granite/granite-3.3-2b-instruct | no | https://arxiv.org/abs/2505.13411 | thinking |
| granite-3.0-2b-instruct | 2.634 | 4,096 | ibm-granite/granite-3.0-2b-instruct | no | https://arxiv.org/abs/2412.11777 | unknown |
| MiniCPM-2B-sft | 2.725 | 4,096 | openbmb/MiniCPM-2B-sft-bf16 | no | https://arxiv.org/abs/2404.06395 | unknown |
| phi-2 | 2.78 | 2,048 | microsoft/phi-2 | no | https://arxiv.org/abs/2306.12244 | unknown |
| RWKV7-World-2.9B | 2.948 | 2,048 | RWKV/RWKV7-Goose-World3-2.9B-HF | no | https://arxiv.org/abs/2503.14456 | unknown |
| AI21-Jamba2-3B | 3.029 | 262,144 | ai21labs/AI21-Jamba2-3B | no | https://arxiv.org/abs/2408.12570 | unknown |
| SmolLM3-3B | 3.075 | 65,536 | HuggingFaceTB/SmolLM3-3B | no | https://arxiv.org/abs/2506.09313 | thinking |
| Qwen2.5-3B-Instruct | 3.086 | 32,768 | Qwen/Qwen2.5-3B-Instruct | no | https://qwenlm.github.io/blog/qwen2.5/ | unknown |
| granite-4.0-h-micro | 3.191 | 131,072 | ibm-granite/granite-4.0-h-micro | no | https://arxiv.org/abs/2510.17848 | unknown |
| AI21-Jamba-Reasoning-3B | 3.197 | 262,144 | ai21labs/AI21-Jamba-Reasoning-3B | no | https://arxiv.org/abs/2507.02782 | unknown |
| granite-4.0-micro | 3.403 | 131,072 | ibm-granite/granite-4.0-micro | no | https://arxiv.org/abs/2510.17848 | unknown |
| granite-4.1-3b | 3.403 | 131,072 | ibm-granite/granite-4.1-3b | no | https://arxiv.org/abs/2510.17848 | unknown |
| granite-4.2-3b | 3.66 | 131,072 | ibm-granite/granite-4.2-3b | no | https://arxiv.org/abs/2510.17848 | thinking |
| Phi-3-mini-128k-instruct | 3.821 | 131,072 | microsoft/Phi-3-mini-128k-instruct | no | https://arxiv.org/abs/2404.14219 | unknown |
| Phi-3-mini-4k-instruct | 3.821 | 4,096 | microsoft/Phi-3-mini-4k-instruct | no | https://arxiv.org/abs/2404.14219 | unknown |
| Phi-3.5-mini-instruct | 3.821 | 131,072 | microsoft/Phi-3.5-mini-instruct | no | https://arxiv.org/abs/2404.14219 | unknown |
| phi-4-mini-instruct | 3.836 | 131,072 | microsoft/phi-4-mini-instruct | no | https://huggingface.co/papers/2503.01743 | unknown |
| Ministral-3-3B-Instruct-2512 | 3.849 | 262,144 | mistralai/Ministral-3-3B-Instruct-2512 | no | https://arxiv.org/abs/2601.08584 | non-thinking |
| Qwen3-4B-Instruct-2507 | 4.022 | 262,144 | Qwen/Qwen3-4B-Instruct-2507 | no | https://arxiv.org/abs/2505.09388 | thinking |
| MiniCPM3-4B | 4.074 | 32,768 | openbmb/MiniCPM3-4B | no | https://arxiv.org/abs/2404.06395 | unknown |
| gemma-3-4b-it | 4.3 | unknown | google/gemma-3-4b-it | yes | https://blog.google/technology/developers/gemma-3/ | unknown |
| Qwen3.5-4B | 4.66 | 262,144 | Qwen/Qwen3.5-4B | no | https://qwen.ai/blog?id=qwen3.5 | thinking |
| gemma-4-e2b-it | 5.123 | 131,072 | google/gemma-4-e2b-it | no | https://arxiv.org/abs/2607.02770 | thinking |
| mistral-7b-instruct-v0.3 | 7.248 | 32,768 | mistralai/Mistral-7B-Instruct-v0.3 | no | https://arxiv.org/abs/2310.06825 | unknown |
| OLMo-2-1124-7B-Instruct | 7.299 | 4,096 | allenai/OLMo-2-1124-7B-Instruct | no | https://arxiv.org/abs/2501.00656 | unknown |
| Qwen2.5-7B-Instruct | 7.616 | 32,768 | Qwen/Qwen2.5-7B-Instruct | no | https://arxiv.org/abs/2309.00071 | unknown |
| gemma-4-e4b-it | 7.996 | 131,072 | google/gemma-4-e4b-it | no | https://arxiv.org/abs/2607.02770 | thinking |
| granite-3.3-8b-instruct | 8.171 | 131,072 | ibm-granite/granite-3.3-8b-instruct | no | https://arxiv.org/abs/2505.13411 | thinking |
| Qwen3-8B | 8.191 | 40,960 | Qwen/Qwen3-8B | no | https://arxiv.org/abs/2309.00071 | thinking |
| Ministral-3-8B-Instruct-2512 | 8.918 | 262,144 | mistralai/Ministral-3-8B-Instruct-2512 | no | https://arxiv.org/abs/2601.08584 | non-thinking |
| Qwen3.5-9B | 9.653 | 262,144 | Qwen/Qwen3.5-9B | no | https://qwen.ai/blog?id=qwen3.5 | thinking |
| Phi-4-14B | 14.66 | 16,384 | microsoft/phi-4 | no | https://arxiv.org/abs/2412.08905 | unknown |
| Qwen3-14B | 14.77 | 40,960 | Qwen/Qwen3-14B | no | https://arxiv.org/abs/2309.00071 | thinking |
| Llama-3.1-8B-Instruct | unknown | unknown | meta-llama/Llama-3.1-8B-Instruct | yes | https://ai.meta.com/blog/meta-llama-3-1/ | unknown |
| Llama-3.2-1B-Instruct | unknown | unknown | meta-llama/Llama-3.2-1B-Instruct | yes | https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/MODEL_CARD.md | unknown |
| Llama-3.2-3B-Instruct | unknown | unknown | meta-llama/Llama-3.2-3B-Instruct | yes | https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/MODEL_CARD.md | unknown |
| gemma-2-2b-it | unknown | unknown | google/gemma-2-2b-it | yes | https://arxiv.org/abs/2408.00118 | unknown |
| gemma-3-12b-it | unknown | unknown | google/gemma-3-12b-it | yes | https://blog.google/technology/developers/gemma-3/ | unknown |
| gemma-3-1b-it | unknown | unknown | google/gemma-3-1b-it | yes | https://blog.google/technology/developers/gemma-3/ | unknown |
| gemma-3-27b-it | unknown | unknown | google/gemma-3-27b-it | yes | https://blog.google/technology/developers/gemma-3/ | unknown |
