# randomizer.md - the randomizer ledger

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | speed |
|---|---|---|---|---|
| 1 | granite-4.0-micro | 6 | Q5_1 | medium |
| 2 | granite-4.0-h-1b | 3 | Q8_0 | slow |
| 3 | granite-4.1-3b | 2 | Q4_0 | fast |
| 4 | Phi-3-mini-4k-instruct | 2 | Q5_0 | fast |
| 5 | Phi-3.5-mini-instruct | 2 | Q4_K_M | medium |
| 6 | MiniCPM3-4B | 2 | Q4_K_S | medium |
| 7 | Llama-3.2-1B-Instruct | 1 | Q4_1 | fast |
| 8 | Qwen3-2B | 1 | Q3_K_S | fast |
| 9 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 10 | phi-4-mini-instruct | 1 | Q5_1 | fast |
| 11 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 12 | Qwen3-0.6B | 0 | IQ3_XS | fast |
| 13 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 14 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 15 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 16 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 17 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 18 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 19 | Qwen3-2B | 0 | IQ4_XS | fast |
| 20 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 21 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 22 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 23 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 24 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 25 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 26 | granite-4.0-1b | -1 | Q1_0 | slow |
| 27 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 28 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 29 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 30 | granite-4.0-1b | -1 | Q4_1 | slow |
| 31 | phi-2 | -1 | Q2_0 | slow |
| 32 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 33 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 34 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 35 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 36 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 37 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 38 | MiniCPM5-1B | -1 | Q6_K | slow |
| 39 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 40 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 41 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 42 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 43 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 44 | Qwen3.5-2B | -1 | Q2_K | slow |
| 45 | phi-1 | -1 | IQ3_S | slow |
| 46 | phi-2 | -1 | IQ4_XS | slow |
| 47 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 48 | phi-1 | -1 | Q2_K_S | medium |
| 49 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 50 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 51 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 52 | gemma-3-1b-it | -1 | F16 | medium |
| 53 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 54 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 55 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 56 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 57 | granite-4.0-350m | -1 | Q5_0 | fast |
| 58 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 59 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 60 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 61 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 62 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 63 | Qwen3-2B | -1 | Q4_K_M | slow |
| 64 | granite-4.0-micro | -1 | Q4_0 | slow |
| 65 | phi-2 | -1 | Q5_1 | medium |
| 66 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 67 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 68 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 69 | Qwen3-2B | -1 | IQ3_XS | slow |
| 70 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 71 | Qwen3-2B | -1 | IQ3_S | slow |
| 72 | phi-2 | -1 | IQ1_M | slow |
| 73 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 74 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 75 | MiniCPM4-0.5B | -1 | F16 | fast |
| 76 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 77 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 78 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 79 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 80 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 81 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 82 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 83 | Qwen3-2B | -1 | IQ2_XS | slow |
| 84 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 85 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 86 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |

_86 candidates run of 2048; each one chance, the seed recorded in state._
