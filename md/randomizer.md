# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 120 done candidates, top 6 (6 of 120)
- params median: **3.297 B**
- quant levels: Q5 x2, Q4 x2, Q8 x1, F16 x1
- high-score level time median: **25s**
- score median: **2.5**

_the machine sweet-spot band, live as the pool fills_

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | speed |
|---|---|---|---|---|
| 1 | granite-4.0-micro | 6 | Q5_1 | medium |
| 2 | granite-4.0-h-micro | 4 | Q4_0 | medium |
| 3 | granite-4.0-h-1b | 3 | Q8_0 | slow |
| 4 | MiniCPM-1B-sft | 2 | F16 | fast |
| 5 | granite-4.1-3b | 2 | Q4_0 | fast |
| 6 | Phi-3-mini-4k-instruct | 2 | Q5_0 | fast |
| 7 | Phi-3.5-mini-instruct | 2 | Q4_K_M | medium |
| 8 | MiniCPM3-4B | 2 | Q4_K_S | medium |
| 9 | granite-4.1-3b | 2 | F16 | medium |
| 10 | Llama-3.2-1B-Instruct | 1 | Q4_1 | fast |
| 11 | Qwen3-2B | 1 | Q3_K_S | fast |
| 12 | granite-3.3-2b-instruct | 1 | Q3_K_M | fast |
| 13 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 14 | granite-3.1-2b-instruct | 1 | Q3_K_S | fast |
| 15 | phi-4-mini-instruct | 1 | Q5_1 | fast |
| 16 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 17 | Qwen3-0.6B | 0 | IQ3_XS | fast |
| 18 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 19 | gemma-3-1b-it | 0 | IQ3_S | fast |
| 20 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 21 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 22 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 23 | granite-3.0-2b-instruct | 0 | Q3_K_L | fast |
| 24 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 25 | SmolLM2-1.7B-Instruct | 0 | Q4_0 | fast |
| 26 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 27 | granite-3.0-2b-instruct | 0 | Q6_K | fast |
| 28 | Qwen3-2B | 0 | IQ4_XS | fast |
| 29 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 30 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 31 | Phi-3-mini-128k-instruct | 0 | Q5_0 | fast |
| 32 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 33 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 34 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 35 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 36 | granite-4.0-1b | -1 | Q1_0 | slow |
| 37 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 38 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 39 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 40 | granite-4.0-1b | -1 | Q4_1 | slow |
| 41 | phi-2 | -1 | Q2_0 | slow |
| 42 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 43 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 44 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 45 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 46 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 47 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 48 | MiniCPM5-1B | -1 | Q6_K | slow |
| 49 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 50 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 51 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 52 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 53 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 54 | Qwen3.5-2B | -1 | Q2_K | slow |
| 55 | phi-1 | -1 | IQ3_S | slow |
| 56 | phi-2 | -1 | IQ4_XS | slow |
| 57 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 58 | phi-1 | -1 | Q2_K_S | medium |
| 59 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 60 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 61 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 62 | gemma-3-1b-it | -1 | F16 | medium |
| 63 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 64 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 65 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 66 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 67 | granite-4.0-350m | -1 | Q5_0 | fast |
| 68 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 69 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 70 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 71 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 72 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 73 | Qwen3-2B | -1 | Q4_K_M | slow |
| 74 | granite-4.0-micro | -1 | Q4_0 | slow |
| 75 | phi-2 | -1 | Q5_1 | medium |
| 76 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 77 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 78 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 79 | Qwen3-2B | -1 | IQ3_XS | slow |
| 80 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 81 | Qwen3-2B | -1 | IQ3_S | slow |
| 82 | phi-2 | -1 | IQ1_M | slow |
| 83 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 84 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 85 | MiniCPM4-0.5B | -1 | F16 | fast |
| 86 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 87 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 88 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 89 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 90 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 91 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 92 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 93 | Qwen3-2B | -1 | IQ2_XS | slow |
| 94 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 95 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 96 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |
| 97 | Ministral-3-3B-Instruct-2512 | -1 | IQ2_S | slow |
| 98 | granite-4.0-h-1b | -1 | Q4_0 | slow |
| 99 | Qwen3.5-0.8B | -1 | IQ2_M | slow |
| 100 | MiniCPM-1B-sft | -1 | Q5_K_S | slow |
| 101 | Qwen3-2B | -1 | Q4_0 | slow |
| 102 | SmolLM2-360M-Instruct | -1 | IQ2_S | slow |
| 103 | MiniCPM4-0.5B | -1 | IQ3_XS | fast |
| 104 | AI21-Jamba2-3B | -1 | IQ3_XS | slow |
| 105 | Qwen2.5-3B-Instruct | -1 | Q2_0 | slow |
| 106 | MiniCPM3-4B | -1 | TQ1_0 | slow |
| 107 | Qwen3.5-2B | -1 | IQ1_M | slow |
| 108 | granite-4.0-350m | -1 | Q3_K_M | slow |
| 109 | granite-4.0-1b | -1 | IQ4_NL | medium |
| 110 | Qwen3.5-2B | -1 | IQ3_XS | slow |
| 111 | MiniCPM-2B-sft | -1 | Q5_K_S | slow |
| 112 | AI21-Jamba-Reasoning-3B | -1 | Q6_K | slow |
| 113 | gemma-2-2b-it | -1 | TQ2_0 | slow |
| 114 | granite-4.0-h-350m | -1 | Q6_K | fast |
| 115 | MiniCPM4-0.5B | -1 | IQ3_S | slow |
| 116 | SmolLM3-3B | -1 | IQ1_M | slow |
| 117 | granite-4.0-h-350m | -1 | Q4_1 | fast |
| 118 | granite-4.0-h-micro | -1 | IQ1_M | medium |
| 119 | Qwen3-2B | -1 | F16 | slow |
| 120 | granite-3.1-2b-instruct | -1 | Q4_1 | slow |

_120 candidates run of 2048; each one chance, the seed recorded in state._
