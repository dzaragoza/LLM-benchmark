# models.md — The Model Registry

The roster for the mechanical-sweet-spot benchmark, param-ascending (smallest first — the full benchmark starts at the top of this table). Params are the registry's counts; the training window is each model's `max_position_embeddings` (its own `config.json`, the text config when the model nests one).

| model name | params (B) | training window |
|---|---|---|
| granite-4.0-h-350m | 0.30 | 32,768 |
| granite-4.0-350m | 0.40 | 32,768 |
| MiniCPM4-0.5B | 0.48 | 32,768 |
| Qwen3.5-0.8B | 0.62 | 262,144 |
| granite-4.0-h-micro | 0.29* | 131,072 |
| MiniCPM5-1B | 0.94 | 131,072 |
| granite-4.0-h-1b | 1.29 | 131,072 |
| Qwen2.5-1.5B-Instruct | 1.54* | 32,768 |
| MiniCPM-1B-sft | 1.52* | 4,096 |
| phi-1 | 1.31* | 2,048 |
| Qwen3-1.7B | 1.84 | 40,960 |
| Qwen3.5-2B | 1.82 | 262,144 |
| granite-4.0-1b | 1.88 | 131,072 |
| MiniCPM5-2B | 2.56 | 131,072 |
| granite-4.0-micro | 2.89* | 131,072 |
| AI21-Jamba2-3B | 2.66* | 262,144 |
| AI21-Jamba-Reasoning-3B | 2.66* | 262,144 |
| MiniCPM-2B-sft | 2.72* | 4,096 |
| granite-3.0-2b-instruct | 2.49* | 4,096 |
| granite-3.1-2b-instruct | 2.49* | 131,072 |
| granite-3.2-2b-instruct | 2.49* | 131,072 |
| granite-3.3-2b-instruct | 2.49* | 131,072 |
| phi-2 | 2.70* | 2,048 |
| RWKV7-World-2.9B | 2.92* | 2,048 |
| granite-4.1-3b | 3.06* | 131,072 |
| granite-4.2-3b | 3.06* | 131,072 |
| Qwen3.5-4B | 3.74 | 262,144 |
| Phi-3.5-mini-instruct | 3.82* | 131,072 |
| Phi-3-mini-4k-instruct | 3.82* | 4,096 |
| phi-4-mini-instruct | 4.24* | 131,072 |
| Qwen3-4B-Instruct-2507 | 4.02* | 262,144 |
| MiniCPM3-4B | 4.86* | 32,768 |
| Qwen3.5-9B | 8.00 | 262,144 |

\* approximate (estimated from the model config geometry, not the
registry store - the exact count arrives with the registry fetch).
Param-ascending order uses the exact counts where known; the
approximations sort correctly within their bands.
