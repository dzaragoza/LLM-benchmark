# exhaustive.md - the exhaustive ledger

## the score frontier (t=128s)

for each score value, descending: the candidate that
reaches it the fastest (the smallest cumulative time -
the sum of its pass times, 128s PER LEVEL)

| score | candidate | total time (s) |
|---|---|---|
| 5 | Qwen3.5-0.8B Q6_K k=q5_0 v=q5_1 | 9.5 |
| 4 | Qwen2.5-0.5B-Instruct Q3_K_S k=q8_0 v=q5_1 | 4.6 |
| 3 | Qwen2.5-0.5B-Instruct Q3_K_M k=f16 v=f16 | 2.5 |
| 2 | Qwen2.5-0.5B-Instruct Q3_K_M k=f16 v=q4_1 | 1.9 |
| 1 | SmolLM2-360M-Instruct Q4_1 k=q5_0 v=f16 | 1.1 |
| 0 | granite-4.0-h-350m Q5_K_S k=f16 v=q4_0 | 0.6 |

## the per-model best (t=128s)

per model (parameter size ascending): the highest score at
t=128s and the quant that achieved it; ties break by the
cumulative time (the sum of the pass times - 128s is PER
LEVEL, so a multi-level pass can total well over 128s)

| model | best score | quant | kv | total time (s) |
|---|---|---|---|---|
| granite-4.0-h-350m | 1 | Q5_K_M | k=f16 v=q4_1 | 1.4 |
| granite-4.0-350m | 2 | F16 | k=f16 v=q5_0 | 22.2 |
| SmolLM2-360M-Instruct | 1 | Q4_1 | k=q5_0 v=f16 | 1.1 |
| MiniCPM4-0.5B | -1 | Q2_K | k=f16 v=f16 | 0.0 |
| Qwen2.5-0.5B-Instruct | 4 | Q3_K_S | k=q8_0 v=q5_1 | 4.6 |
| Qwen3-0.6B | 2 | Q5_K_S | k=q8_0 v=iq4_nl | 3.2 |
| Qwen3.5-0.8B | 5 | Q6_K | k=q5_0 v=q5_1 | 9.5 |
| gemma-3-1b-it | 2 | Q5_0 | k=q4_1 v=f16 | 4.6 |
| MiniCPM5-1B | -1 | Q2_K | k=f16 v=f16 | 0.0 |
| Llama-3.2-1B-Instruct | 4 | Q4_1 | k=q8_0 v=f16 | 7.1 |
| MiniCPM-1B-sft | 3 | Q5_1 | k=q4_0 v=q5_1 | 10.9 |
| phi-1 | -1 | Q2_K | k=f16 v=f16 | 0.0 |
| granite-4.0-h-1b | 2 | Q5_1 | k=q4_1 v=q5_0 | 13.7 |
| Qwen2.5-1.5B-Instruct | 0 | Q8_0 | k=q8_0 v=q4_1 | 2.4 |
| granite-4.0-1b | -1 | Q2_K | k=f16 v=f16 | 0.0 |
| SmolLM2-1.7B-Instruct | 1 | Q4_1 | k=q8_0 v=f16 | 8.3 |
| Qwen3-1.7B | 3 | Q4_K_S | k=q4_0 v=q4_1 | 9.1 |
| Qwen3.5-2B | 2 | Q3_K_M | k=f16 v=q4_1 | 8.1 |
| Qwen3-2B | 3 | Q3_K_M | k=q4_1 v=q4_1 | 12.7 |
| MiniCPM5-2B | -1 | Q2_K | k=f16 v=f16 | 0.0 |
| granite-3.1-2b-instruct | 3 | Q4_1 | k=q4_0 v=q4_0 | 15.7 |
| granite-3.2-2b-instruct | 3 | Q4_0 | k=q8_0 v=q5_0 | 14.8 |
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
