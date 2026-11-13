# exhaustive.md - the exhaustive ledger

## the score frontier (t=128s)

for each score value, descending: the candidate that
reaches it the fastest (the smallest cumulative time -
the sum of its pass times, 128s PER LEVEL)

| score | candidate | total time (s) |
|---|---|---|
| 0 | granite-4.0-h-350m Q4_0 k=q4_0 v=f16 | 0.9 |

## the per-level timers

flat: every exam level gets the full 128s (no adaptive scaling)

| level | timer (s) |
|---|---|
| 0 | 128.0 |
| 1 | 128.0 |

## the per-model best (t=128s)

per model (parameter size ascending): the highest score at
t=128s and the quant that achieved it; ties break by the
cumulative time (the sum of the pass times - 128s is PER
LEVEL, so a multi-level pass can total well over 128s)

| model | best score | quant | kv | total time (s) |
|---|---|---|---|---|
| granite-4.0-h-350m | 0 | Q4_0 | k=q4_0 v=f16 | 0.9 |
| granite-4.0-350m | - | (not measured) | - | - |
| SmolLM2-360M-Instruct | - | (not measured) | - | - |
| MiniCPM4-0.5B | - | (not measured) | - | - |
| Qwen2.5-0.5B-Instruct | - | (not measured) | - | - |
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
