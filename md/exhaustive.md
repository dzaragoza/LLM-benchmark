# exhaustive.md - the exhaustive ledger

## the score frontier (t=128s)

for each score value, descending: the candidate that
reaches it the fastest (the smallest cumulative time -
the sum of its pass times, 128s PER LEVEL)

| score | candidate | total time (s) |
|---|---|---|
| 4 | Qwen2.5-0.5B-Instruct Q3_K_S k=q8_0 v=q5_1 | 4.6 |
| 3 | Qwen2.5-0.5B-Instruct Q3_K_M k=f16 v=f16 | 2.6 |
| 2 | Qwen2.5-0.5B-Instruct Q3_K_M k=f16 v=q4_1 | 1.9 |
| 1 | SmolLM2-360M-Instruct Q4_1 k=q5_0 v=f16 | 1.1 |
| 0 | granite-4.0-h-350m Q5_K_S k=f16 v=q4_0 | 0.6 |

## the per-level timers (current anchor)

the p95 per-GiB pass-rate anchor per level, and the timer a
1 GiB pair gets: min(1 GiB x p95 rate x 2, 128s). A pair's own
timer scales with its gguf size; no sized passes yet -> 128s

| level | p95 rate (s/GiB) | timer @1 GiB (s) |
|---|---|---|
| 0 | 74.38 | 128.0 (capped) |
| 1 | 20.51 | 41.0 |
| 2 | 21.21 | 42.4 |
| 3 | 2.55 | 5.1 |
| 4 | 2.76 | 5.5 |
| 5 | - | 128.0 (no sized passes yet) |

## the per-model best (t=128s)

per model (parameter size ascending): the highest score at
t=128s and the quant that achieved it; ties break by the
cumulative time (the sum of the pass times - 128s is PER
LEVEL, so a multi-level pass can total well over 128s)

| model | best score | quant | kv | total time (s) |
|---|---|---|---|---|
| granite-4.0-h-350m | 1 | Q5_K_M | k=f16 v=q4_1 | 1.4 |
| granite-4.0-350m | 2 | Q6_K | k=f16 v=iq4_nl | 7.7 |
| SmolLM2-360M-Instruct | 2 | Q5_0 | k=q4_0 v=q4_0 | 13.1 |
| MiniCPM4-0.5B | 0 | Q6_K | k=q4_0 v=q5_0 | 61.4 |
| Qwen2.5-0.5B-Instruct | 4 | Q3_K_S | k=q8_0 v=q5_1 | 4.6 |
| Qwen3-0.6B | - | (not measured) | - | - |
| Qwen3.5-0.8B | - | (not measured) | - | - |
| gemma-3-1b-it | - | (not measured) | - | - |
| MiniCPM5-1B | - | (not measured) | - | - |
| Llama-3.2-1B-Instruct | - | (not measured) | - | - |
| MiniCPM-1B-sft | - | (not measured) | - | - |
| phi-1 | - | (not measured) | - | - |
| granite-4.0-h-1b | - | (not measured) | - | - |
| Qwen2.5-1.5B-Instruct | - | (not measured) | - | - |
| granite-4.0-1b | - | (not measured) | - | - |
| SmolLM2-1.7B-Instruct | - | (not measured) | - | - |
| Qwen3-1.7B | - | (not measured) | - | - |
| Qwen3.5-2B | - | (not measured) | - | - |
| Qwen3-2B | - | (not measured) | - | - |
| MiniCPM5-2B | - | (not measured) | - | - |
| granite-3.1-2b-instruct | - | (not measured) | - | - |
| granite-3.2-2b-instruct | - | (not measured) | - | - |
| granite-3.3-2b-instruct | - | (not measured) | - | - |
| gemma-2-2b-it | - | (not measured) | - | - |
| granite-3.0-2b-instruct | - | (not measured) | - | - |
| MiniCPM-2B-sft | - | (not measured) | - | - |
| phi-2 | - | (not measured) | - | - |
| RWKV7-World-2.9B | - | (not measured) | - | - |
| AI21-Jamba2-3B | - | (not measured) | - | - |
| SmolLM3-3B | - | (not measured) | - | - |
| Qwen2.5-3B-Instruct | - | (not measured) | - | - |
| granite-4.0-h-micro | - | (not measured) | - | - |
| AI21-Jamba-Reasoning-3B | - | (not measured) | - | - |
| Llama-3.2-3B-Instruct | - | (not measured) | - | - |
| granite-4.0-micro | - | (not measured) | - | - |
| granite-4.1-3b | - | (not measured) | - | - |
| granite-4.2-3b | - | (not measured) | - | - |
| Phi-3-mini-128k-instruct | - | (not measured) | - | - |
| Phi-3-mini-4k-instruct | - | (not measured) | - | - |
| Phi-3.5-mini-instruct | - | (not measured) | - | - |
| phi-4-mini-instruct | - | (not measured) | - | - |
| Ministral-3-3B-Instruct-2512 | - | (not measured) | - | - |
| Qwen3-4B-Instruct-2507 | - | (not measured) | - | - |
| MiniCPM3-4B | - | (not measured) | - | - |
| gemma-3-4b-it | - | (not measured) | - | - |
| Qwen3.5-4B | - | (not measured) | - | - |
| gemma-4-e2b-it | - | (not measured) | - | - |
| Yi-1.5-6B-Chat | - | (not measured) | - | - |
| mistral-7b-instruct-v0.3 | - | (not measured) | - | - |
| OLMo-2-1124-7B-Instruct | - | (not measured) | - | - |
| Falcon3-7B-Instruct | - | (not measured) | - | - |
| Qwen2.5-7B-Instruct | - | (not measured) | - | - |
| gemma-4-e4b-it | - | (not measured) | - | - |
| Llama-3.1-8B-Instruct | - | (not measured) | - | - |
| granite-3.3-8b-instruct | - | (not measured) | - | - |
| Qwen3-8B | - | (not measured) | - | - |
| Yi-1.5-9B-Chat | - | (not measured) | - | - |
| Ministral-3-8B-Instruct-2512 | - | (not measured) | - | - |
| gemma-2-9b-it | - | (not measured) | - | - |
| Qwen3.5-9B | - | (not measured) | - | - |
| Falcon3-10B-Instruct | - | (not measured) | - | - |
| gemma-3-12b-it | - | (not measured) | - | - |
| Mistral-Nemo-Instruct-2407 | - | (not measured) | - | - |
| gemma-3-27b-it | - | (not measured) | - | - |
