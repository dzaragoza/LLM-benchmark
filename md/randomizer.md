# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 142 done candidates, top 7 (7 of 142)
- params median: **3.403 B**
- quant levels: Q5 x2, Q4 x2, Q3 x1, Q8 x1, F16 x1
- high-score level time median: **35s**
- score median: **3**

_the machine sweet-spot band, live as the pool fills_

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | speed |
|---|---|---|---|---|
| 1 | granite-4.0-micro | 6 | Q5_1 | medium |
| 2 | granite-4.0-h-micro | 4 | Q4_0 | medium |
| 3 | granite-4.1-3b | 3 | Q3_K_M | medium |
| 4 | granite-4.0-h-1b | 3 | Q8_0 | slow |
| 5 | MiniCPM-1B-sft | 2 | F16 | fast |
| 6 | granite-4.1-3b | 2 | Q4_0 | fast |
| 7 | Phi-3-mini-4k-instruct | 2 | Q5_0 | fast |
| 8 | Phi-3.5-mini-instruct | 2 | Q4_K_M | medium |
| 9 | MiniCPM3-4B | 2 | Q4_K_S | medium |
| 10 | granite-4.1-3b | 2 | F16 | medium |
| 11 | Llama-3.2-1B-Instruct | 1 | Q4_1 | fast |
| 12 | Qwen3-1.7B | 1 | Q3_K_M | fast |
| 13 | Qwen3-2B | 1 | Q3_K_S | fast |
| 14 | granite-3.3-2b-instruct | 1 | Q3_K_M | fast |
| 15 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 16 | granite-3.1-2b-instruct | 1 | Q3_K_S | fast |
| 17 | phi-4-mini-instruct | 1 | Q5_1 | fast |
| 18 | granite-4.0-h-1b | 1 | Q5_K_M | slow |
| 19 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 20 | Qwen3-0.6B | 0 | IQ3_XS | fast |
| 21 | Qwen3-0.6B | 0 | Q4_0 | fast |
| 22 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 23 | gemma-3-1b-it | 0 | IQ3_S | fast |
| 24 | gemma-3-1b-it | 0 | Q5_0 | fast |
| 25 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 26 | Qwen3-1.7B | 0 | Q4_1 | fast |
| 27 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 28 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 29 | Qwen3-0.6B | 0 | Q5_K_S | fast |
| 30 | granite-3.0-2b-instruct | 0 | Q3_K_L | fast |
| 31 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 32 | SmolLM2-1.7B-Instruct | 0 | Q4_0 | fast |
| 33 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 34 | granite-3.0-2b-instruct | 0 | Q6_K | fast |
| 35 | Qwen3-2B | 0 | IQ4_XS | fast |
| 36 | MiniCPM3-4B | 0 | Q3_K_M | fast |
| 37 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 38 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 39 | Phi-3-mini-128k-instruct | 0 | Q5_0 | fast |
| 40 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 41 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 42 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 43 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 44 | granite-4.0-1b | -1 | Q1_0 | slow |
| 45 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 46 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 47 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 48 | granite-4.0-1b | -1 | Q4_1 | slow |
| 49 | phi-2 | -1 | Q2_0 | slow |
| 50 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 51 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 52 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 53 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 54 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 55 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 56 | MiniCPM5-1B | -1 | Q6_K | slow |
| 57 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 58 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 59 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 60 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 61 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 62 | Qwen3.5-2B | -1 | Q2_K | slow |
| 63 | phi-1 | -1 | IQ3_S | slow |
| 64 | phi-2 | -1 | IQ4_XS | slow |
| 65 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 66 | phi-1 | -1 | Q2_K_S | medium |
| 67 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 68 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 69 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 70 | gemma-3-1b-it | -1 | F16 | medium |
| 71 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 72 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 73 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 74 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 75 | granite-4.0-350m | -1 | Q5_0 | fast |
| 76 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 77 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 78 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 79 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 80 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 81 | Qwen3-2B | -1 | Q4_K_M | slow |
| 82 | granite-4.0-micro | -1 | Q4_0 | slow |
| 83 | phi-2 | -1 | Q5_1 | medium |
| 84 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 85 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 86 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 87 | Qwen3-2B | -1 | IQ3_XS | slow |
| 88 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 89 | Qwen3-2B | -1 | IQ3_S | slow |
| 90 | phi-2 | -1 | IQ1_M | slow |
| 91 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 92 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 93 | MiniCPM4-0.5B | -1 | F16 | fast |
| 94 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 95 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 96 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 97 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 98 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 99 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 100 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 101 | Qwen3-2B | -1 | IQ2_XS | slow |
| 102 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 103 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 104 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |
| 105 | Ministral-3-3B-Instruct-2512 | -1 | IQ2_S | slow |
| 106 | granite-4.0-h-1b | -1 | Q4_0 | slow |
| 107 | Qwen3.5-0.8B | -1 | IQ2_M | slow |
| 108 | MiniCPM-1B-sft | -1 | Q5_K_S | slow |
| 109 | Qwen3-2B | -1 | Q4_0 | slow |
| 110 | SmolLM2-360M-Instruct | -1 | IQ2_S | slow |
| 111 | MiniCPM4-0.5B | -1 | IQ3_XS | fast |
| 112 | AI21-Jamba2-3B | -1 | IQ3_XS | slow |
| 113 | Qwen2.5-3B-Instruct | -1 | Q2_0 | slow |
| 114 | MiniCPM3-4B | -1 | TQ1_0 | slow |
| 115 | Qwen3.5-2B | -1 | IQ1_M | slow |
| 116 | granite-4.0-350m | -1 | Q3_K_M | slow |
| 117 | granite-4.0-1b | -1 | IQ4_NL | medium |
| 118 | Qwen3.5-2B | -1 | IQ3_XS | slow |
| 119 | MiniCPM-2B-sft | -1 | Q5_K_S | slow |
| 120 | AI21-Jamba-Reasoning-3B | -1 | Q6_K | slow |
| 121 | gemma-2-2b-it | -1 | TQ2_0 | slow |
| 122 | granite-4.0-h-350m | -1 | Q6_K | fast |
| 123 | MiniCPM4-0.5B | -1 | IQ3_S | slow |
| 124 | SmolLM3-3B | -1 | IQ1_M | slow |
| 125 | granite-4.0-h-350m | -1 | Q4_1 | fast |
| 126 | granite-4.0-h-micro | -1 | IQ1_M | medium |
| 127 | Qwen3-2B | -1 | F16 | slow |
| 128 | granite-3.1-2b-instruct | -1 | Q4_1 | slow |
| 129 | RWKV7-World-2.9B | -1 | IQ4_XS | slow |
| 130 | Llama-3.2-1B-Instruct | -1 | IQ1_S | slow |
| 131 | Qwen2.5-0.5B-Instruct | -1 | TQ2_0 | slow |
| 132 | Qwen2.5-1.5B-Instruct | -1 | Q3_K_S | fast |
| 133 | granite-3.2-2b-instruct | -1 | F16 | slow |
| 134 | MiniCPM5-2B | -1 | Q4_1 | slow |
| 135 | Qwen3-0.6B | -1 | IQ2_XXS | medium |
| 136 | Qwen3.5-2B | -1 | Q4_0 | slow |
| 137 | MiniCPM5-1B | -1 | Q5_0 | slow |
| 138 | granite-4.0-1b | -1 | IQ3_XS | slow |
| 139 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | fast |
| 140 | MiniCPM-1B-sft | -1 | Q1_0 | medium |
| 141 | Llama-3.2-3B-Instruct | -1 | IQ2_XS | slow |
| 142 | Llama-3.2-1B-Instruct | -1 | IQ2_XXS | medium |

_142 candidates run of 2048; each one chance, the seed recorded in state._
