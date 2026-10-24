# randomizer.md - the randomizer ledger

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | speed |
|---|---|---|---|---|
| 1 | granite-4.0-micro | 6 | Q5_1 | medium |
| 2 | granite-4.0-h-1b | 3 | Q8_0 | slow |
| 3 | MiniCPM-1B-sft | 2 | F16 | fast |
| 4 | granite-4.1-3b | 2 | Q4_0 | fast |
| 5 | Phi-3-mini-4k-instruct | 2 | Q5_0 | fast |
| 6 | Phi-3.5-mini-instruct | 2 | Q4_K_M | medium |
| 7 | MiniCPM3-4B | 2 | Q4_K_S | medium |
| 8 | Llama-3.2-1B-Instruct | 1 | Q4_1 | fast |
| 9 | Qwen3-2B | 1 | Q3_K_S | fast |
| 10 | granite-3.3-2b-instruct | 1 | Q3_K_M | fast |
| 11 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 12 | phi-4-mini-instruct | 1 | Q5_1 | fast |
| 13 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 14 | Qwen3-0.6B | 0 | IQ3_XS | fast |
| 15 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 16 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 17 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 18 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 19 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 20 | SmolLM2-1.7B-Instruct | 0 | Q4_0 | fast |
| 21 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 22 | Qwen3-2B | 0 | IQ4_XS | fast |
| 23 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 24 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 25 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 26 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 27 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 28 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 29 | granite-4.0-1b | -1 | Q1_0 | slow |
| 30 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 31 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 32 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 33 | granite-4.0-1b | -1 | Q4_1 | slow |
| 34 | phi-2 | -1 | Q2_0 | slow |
| 35 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 36 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 37 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 38 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 39 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 40 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 41 | MiniCPM5-1B | -1 | Q6_K | slow |
| 42 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 43 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 44 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 45 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 46 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 47 | Qwen3.5-2B | -1 | Q2_K | slow |
| 48 | phi-1 | -1 | IQ3_S | slow |
| 49 | phi-2 | -1 | IQ4_XS | slow |
| 50 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 51 | phi-1 | -1 | Q2_K_S | medium |
| 52 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 53 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 54 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 55 | gemma-3-1b-it | -1 | F16 | medium |
| 56 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 57 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 58 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 59 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 60 | granite-4.0-350m | -1 | Q5_0 | fast |
| 61 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 62 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 63 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 64 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 65 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 66 | Qwen3-2B | -1 | Q4_K_M | slow |
| 67 | granite-4.0-micro | -1 | Q4_0 | slow |
| 68 | phi-2 | -1 | Q5_1 | medium |
| 69 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 70 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 71 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 72 | Qwen3-2B | -1 | IQ3_XS | slow |
| 73 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 74 | Qwen3-2B | -1 | IQ3_S | slow |
| 75 | phi-2 | -1 | IQ1_M | slow |
| 76 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 77 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 78 | MiniCPM4-0.5B | -1 | F16 | fast |
| 79 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 80 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 81 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 82 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 83 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 84 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 85 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 86 | Qwen3-2B | -1 | IQ2_XS | slow |
| 87 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 88 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 89 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |
| 90 | Ministral-3-3B-Instruct-2512 | -1 | IQ2_S | slow |
| 91 | granite-4.0-h-1b | -1 | Q4_0 | slow |
| 92 | Qwen3.5-0.8B | -1 | IQ2_M | slow |
| 93 | MiniCPM-1B-sft | -1 | Q5_K_S | slow |
| 94 | Qwen3-2B | -1 | Q4_0 | slow |

_94 candidates run of 2048; each one chance, the seed recorded in state._
