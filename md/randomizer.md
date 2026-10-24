# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 135 done candidates, top 6 (6 of 135)
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
| 11 | Qwen3-1.7B | 1 | Q3_K_M | fast |
| 12 | Qwen3-2B | 1 | Q3_K_S | fast |
| 13 | granite-3.3-2b-instruct | 1 | Q3_K_M | fast |
| 14 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 15 | granite-3.1-2b-instruct | 1 | Q3_K_S | fast |
| 16 | phi-4-mini-instruct | 1 | Q5_1 | fast |
| 17 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 18 | Qwen3-0.6B | 0 | IQ3_XS | fast |
| 19 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 20 | gemma-3-1b-it | 0 | IQ3_S | fast |
| 21 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 22 | Qwen3-1.7B | 0 | Q4_1 | fast |
| 23 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 24 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 25 | Qwen3-0.6B | 0 | Q5_K_S | fast |
| 26 | granite-3.0-2b-instruct | 0 | Q3_K_L | fast |
| 27 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 28 | SmolLM2-1.7B-Instruct | 0 | Q4_0 | fast |
| 29 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 30 | granite-3.0-2b-instruct | 0 | Q6_K | fast |
| 31 | Qwen3-2B | 0 | IQ4_XS | fast |
| 32 | MiniCPM3-4B | 0 | Q3_K_M | fast |
| 33 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 34 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 35 | Phi-3-mini-128k-instruct | 0 | Q5_0 | fast |
| 36 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 37 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 38 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 39 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 40 | granite-4.0-1b | -1 | Q1_0 | slow |
| 41 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 42 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 43 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 44 | granite-4.0-1b | -1 | Q4_1 | slow |
| 45 | phi-2 | -1 | Q2_0 | slow |
| 46 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 47 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 48 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 49 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 50 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 51 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 52 | MiniCPM5-1B | -1 | Q6_K | slow |
| 53 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 54 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 55 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 56 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 57 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 58 | Qwen3.5-2B | -1 | Q2_K | slow |
| 59 | phi-1 | -1 | IQ3_S | slow |
| 60 | phi-2 | -1 | IQ4_XS | slow |
| 61 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 62 | phi-1 | -1 | Q2_K_S | medium |
| 63 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 64 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 65 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 66 | gemma-3-1b-it | -1 | F16 | medium |
| 67 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 68 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 69 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 70 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 71 | granite-4.0-350m | -1 | Q5_0 | fast |
| 72 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 73 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 74 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 75 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 76 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 77 | Qwen3-2B | -1 | Q4_K_M | slow |
| 78 | granite-4.0-micro | -1 | Q4_0 | slow |
| 79 | phi-2 | -1 | Q5_1 | medium |
| 80 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 81 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 82 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 83 | Qwen3-2B | -1 | IQ3_XS | slow |
| 84 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 85 | Qwen3-2B | -1 | IQ3_S | slow |
| 86 | phi-2 | -1 | IQ1_M | slow |
| 87 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 88 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 89 | MiniCPM4-0.5B | -1 | F16 | fast |
| 90 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 91 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 92 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 93 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 94 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 95 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 96 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 97 | Qwen3-2B | -1 | IQ2_XS | slow |
| 98 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 99 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 100 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |
| 101 | Ministral-3-3B-Instruct-2512 | -1 | IQ2_S | slow |
| 102 | granite-4.0-h-1b | -1 | Q4_0 | slow |
| 103 | Qwen3.5-0.8B | -1 | IQ2_M | slow |
| 104 | MiniCPM-1B-sft | -1 | Q5_K_S | slow |
| 105 | Qwen3-2B | -1 | Q4_0 | slow |
| 106 | SmolLM2-360M-Instruct | -1 | IQ2_S | slow |
| 107 | MiniCPM4-0.5B | -1 | IQ3_XS | fast |
| 108 | AI21-Jamba2-3B | -1 | IQ3_XS | slow |
| 109 | Qwen2.5-3B-Instruct | -1 | Q2_0 | slow |
| 110 | MiniCPM3-4B | -1 | TQ1_0 | slow |
| 111 | Qwen3.5-2B | -1 | IQ1_M | slow |
| 112 | granite-4.0-350m | -1 | Q3_K_M | slow |
| 113 | granite-4.0-1b | -1 | IQ4_NL | medium |
| 114 | Qwen3.5-2B | -1 | IQ3_XS | slow |
| 115 | MiniCPM-2B-sft | -1 | Q5_K_S | slow |
| 116 | AI21-Jamba-Reasoning-3B | -1 | Q6_K | slow |
| 117 | gemma-2-2b-it | -1 | TQ2_0 | slow |
| 118 | granite-4.0-h-350m | -1 | Q6_K | fast |
| 119 | MiniCPM4-0.5B | -1 | IQ3_S | slow |
| 120 | SmolLM3-3B | -1 | IQ1_M | slow |
| 121 | granite-4.0-h-350m | -1 | Q4_1 | fast |
| 122 | granite-4.0-h-micro | -1 | IQ1_M | medium |
| 123 | Qwen3-2B | -1 | F16 | slow |
| 124 | granite-3.1-2b-instruct | -1 | Q4_1 | slow |
| 125 | RWKV7-World-2.9B | -1 | IQ4_XS | slow |
| 126 | Llama-3.2-1B-Instruct | -1 | IQ1_S | slow |
| 127 | Qwen2.5-0.5B-Instruct | -1 | TQ2_0 | slow |
| 128 | Qwen2.5-1.5B-Instruct | -1 | Q3_K_S | fast |
| 129 | granite-3.2-2b-instruct | -1 | F16 | slow |
| 130 | MiniCPM5-2B | -1 | Q4_1 | slow |
| 131 | Qwen3-0.6B | -1 | IQ2_XXS | medium |
| 132 | Qwen3.5-2B | -1 | Q4_0 | slow |
| 133 | MiniCPM5-1B | -1 | Q5_0 | slow |
| 134 | granite-4.0-1b | -1 | IQ3_XS | slow |
| 135 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | fast |

_135 candidates run of 2048; each one chance, the seed recorded in state._
