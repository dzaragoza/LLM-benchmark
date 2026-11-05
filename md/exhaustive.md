# exhaustive.md - the exhaustive ledger

## the top candidate by time tier

the highest score within each tier (ties break by time);
a candidate can top every tier

| tier | score | candidate | time (s) |
|---|---|---|---|
| <= 32s | 5 | Qwen3.5-0.8B Q6_K k=q5_0 v=q5_1 | 9.7 |
| <= 64s | 5 | Qwen3.5-0.8B Q6_K k=q5_0 v=q5_1 | 9.7 |
| <= 128s | 5 | Qwen3.5-0.8B Q6_K k=q5_0 v=q5_1 | 9.7 |

## the per-model best (t=128s)

per model (parameter size ascending): the highest score at
t=128s and the quant that achieved it; ties break by time

| model | best score | quant | kv | time (s) |
|---|---|---|---|---|
| granite-4.0-h-350m | 1 | Q5_K_M | k=f16 v=q4_1 | 1.4 |
| granite-4.0-350m | 2 | Q6_K | k=f16 v=iq4_nl | 7.8 |
| SmolLM2-360M-Instruct | 1 | Q4_1 | k=q5_0 v=f16 | 1.1 |
| MiniCPM4-0.5B | 0 | Q6_K | k=q4_0 v=q5_0 | 128.0 |
| Qwen2.5-0.5B-Instruct | 4 | Q6_K | k=f16 v=q8_0 | 4.6 |
| Qwen3-0.6B | 2 | Q5_K_S | k=q8_0 v=iq4_nl | 3.2 |
| Qwen3.5-0.8B | 5 | Q6_K | k=q5_0 v=q5_1 | 9.7 |
| gemma-3-1b-it | 2 | Q5_0 | k=q4_1 v=f16 | 4.7 |
| MiniCPM5-1B | -1 | Q2_K | k=f16 v=f16 | 0.0 |
| Llama-3.2-1B-Instruct | 4 | Q4_1 | k=q8_0 v=f16 | 7.3 |
| MiniCPM-1B-sft | 2 | Q4_K_S | k=f16 v=q4_1 | 7.9 |
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
