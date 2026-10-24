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
| 24 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 25 | granite-4.0-1b | -1 | Q1_0 | slow |
| 26 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 27 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 28 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 29 | granite-4.0-1b | -1 | Q4_1 | slow |
| 30 | phi-2 | -1 | Q2_0 | slow |
| 31 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 32 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 33 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 34 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 35 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 36 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 37 | MiniCPM5-1B | -1 | Q6_K | slow |
| 38 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 39 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 40 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 41 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 42 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 43 | Qwen3.5-2B | -1 | Q2_K | slow |
| 44 | phi-1 | -1 | IQ3_S | slow |
| 45 | phi-2 | -1 | IQ4_XS | slow |
| 46 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 47 | phi-1 | -1 | Q2_K_S | medium |
| 48 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 49 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 50 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 51 | gemma-3-1b-it | -1 | F16 | medium |
| 52 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 53 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 54 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 55 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 56 | granite-4.0-350m | -1 | Q5_0 | fast |
| 57 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 58 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 59 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 60 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 61 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 62 | Qwen3-2B | -1 | Q4_K_M | slow |
| 63 | granite-4.0-micro | -1 | Q4_0 | slow |
| 64 | phi-2 | -1 | Q5_1 | medium |
| 65 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 66 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 67 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 68 | Qwen3-2B | -1 | IQ3_XS | slow |
| 69 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 70 | Qwen3-2B | -1 | IQ3_S | slow |
| 71 | phi-2 | -1 | IQ1_M | slow |
| 72 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 73 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 74 | MiniCPM4-0.5B | -1 | F16 | fast |
| 75 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 76 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 77 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 78 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 79 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |

_79 candidates run of 2048; each one chance, the seed recorded in state._
