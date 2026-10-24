# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 157 done candidates, top 7 (7 of 157)
- params median: **3.191 B**
- quant levels: Q4 x2, Q8 x2, Q5 x1, Q3 x1, F16 x1
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
| 5 | Qwen3.5-0.8B | 2 | Q8_0 | fast |
| 6 | MiniCPM-1B-sft | 2 | F16 | fast |
| 7 | granite-4.1-3b | 2 | Q4_0 | fast |
| 8 | Phi-3-mini-4k-instruct | 2 | Q5_0 | fast |
| 9 | Phi-3.5-mini-instruct | 2 | Q4_K_M | medium |
| 10 | MiniCPM3-4B | 2 | Q4_K_S | medium |
| 11 | granite-4.1-3b | 2 | F16 | medium |
| 12 | Llama-3.2-1B-Instruct | 1 | Q4_1 | fast |
| 13 | Qwen3-0.6B | 1 | Q4_K_S | fast |
| 14 | Qwen3-1.7B | 1 | Q3_K_M | fast |
| 15 | Qwen3-2B | 1 | Q3_K_S | fast |
| 16 | granite-3.3-2b-instruct | 1 | Q3_K_M | fast |
| 17 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 18 | granite-3.1-2b-instruct | 1 | Q3_K_S | fast |
| 19 | gemma-3-4b-it | 1 | Q5_1 | fast |
| 20 | phi-4-mini-instruct | 1 | Q5_1 | fast |
| 21 | Phi-3.5-mini-instruct | 1 | IQ4_XS | fast |
| 22 | granite-4.0-h-1b | 1 | Q5_K_M | slow |
| 23 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 24 | Qwen3-0.6B | 0 | IQ3_XS | fast |
| 25 | Qwen3-0.6B | 0 | Q4_0 | fast |
| 26 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 27 | gemma-3-1b-it | 0 | IQ3_S | fast |
| 28 | gemma-3-1b-it | 0 | Q5_0 | fast |
| 29 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 30 | Qwen3-1.7B | 0 | Q4_1 | fast |
| 31 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 32 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 33 | Qwen3-0.6B | 0 | Q5_K_S | fast |
| 34 | granite-3.0-2b-instruct | 0 | Q3_K_L | fast |
| 35 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 36 | SmolLM2-1.7B-Instruct | 0 | Q4_0 | fast |
| 37 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 38 | granite-3.0-2b-instruct | 0 | Q6_K | fast |
| 39 | Qwen3-2B | 0 | IQ4_XS | fast |
| 40 | MiniCPM3-4B | 0 | Q3_K_M | fast |
| 41 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 42 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 43 | Phi-3-mini-128k-instruct | 0 | Q5_0 | fast |
| 44 | MiniCPM3-4B | 0 | IQ3_XXS | fast |
| 45 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 46 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 47 | Qwen2.5-3B-Instruct | 0 | IQ2_M | slow |
| 48 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 49 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 50 | granite-4.0-1b | -1 | Q1_0 | slow |
| 51 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 52 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 53 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 54 | granite-4.0-1b | -1 | Q4_1 | slow |
| 55 | phi-2 | -1 | Q2_0 | slow |
| 56 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 57 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 58 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 59 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 60 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 61 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 62 | MiniCPM5-1B | -1 | Q6_K | slow |
| 63 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 64 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 65 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 66 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 67 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 68 | Qwen3.5-2B | -1 | Q2_K | slow |
| 69 | phi-1 | -1 | IQ3_S | slow |
| 70 | phi-2 | -1 | IQ4_XS | slow |
| 71 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 72 | phi-1 | -1 | Q2_K_S | medium |
| 73 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 74 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 75 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 76 | gemma-3-1b-it | -1 | F16 | medium |
| 77 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 78 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 79 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 80 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 81 | granite-4.0-350m | -1 | Q5_0 | fast |
| 82 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 83 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 84 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 85 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 86 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 87 | Qwen3-2B | -1 | Q4_K_M | slow |
| 88 | granite-4.0-micro | -1 | Q4_0 | slow |
| 89 | phi-2 | -1 | Q5_1 | medium |
| 90 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 91 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 92 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 93 | Qwen3-2B | -1 | IQ3_XS | slow |
| 94 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 95 | Qwen3-2B | -1 | IQ3_S | slow |
| 96 | phi-2 | -1 | IQ1_M | slow |
| 97 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 98 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 99 | MiniCPM4-0.5B | -1 | F16 | fast |
| 100 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 101 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 102 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 103 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 104 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 105 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 106 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 107 | Qwen3-2B | -1 | IQ2_XS | slow |
| 108 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 109 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 110 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |
| 111 | Ministral-3-3B-Instruct-2512 | -1 | IQ2_S | slow |
| 112 | granite-4.0-h-1b | -1 | Q4_0 | slow |
| 113 | Qwen3.5-0.8B | -1 | IQ2_M | slow |
| 114 | MiniCPM-1B-sft | -1 | Q5_K_S | slow |
| 115 | Qwen3-2B | -1 | Q4_0 | slow |
| 116 | SmolLM2-360M-Instruct | -1 | IQ2_S | slow |
| 117 | MiniCPM4-0.5B | -1 | IQ3_XS | fast |
| 118 | AI21-Jamba2-3B | -1 | IQ3_XS | slow |
| 119 | Qwen2.5-3B-Instruct | -1 | Q2_0 | slow |
| 120 | MiniCPM3-4B | -1 | TQ1_0 | slow |
| 121 | Qwen3.5-2B | -1 | IQ1_M | slow |
| 122 | granite-4.0-350m | -1 | Q3_K_M | slow |
| 123 | granite-4.0-1b | -1 | IQ4_NL | medium |
| 124 | Qwen3.5-2B | -1 | IQ3_XS | slow |
| 125 | MiniCPM-2B-sft | -1 | Q5_K_S | slow |
| 126 | AI21-Jamba-Reasoning-3B | -1 | Q6_K | slow |
| 127 | gemma-2-2b-it | -1 | TQ2_0 | slow |
| 128 | granite-4.0-h-350m | -1 | Q6_K | fast |
| 129 | MiniCPM4-0.5B | -1 | IQ3_S | slow |
| 130 | SmolLM3-3B | -1 | IQ1_M | slow |
| 131 | granite-4.0-h-350m | -1 | Q4_1 | fast |
| 132 | granite-4.0-h-micro | -1 | IQ1_M | medium |
| 133 | Qwen3-2B | -1 | F16 | slow |
| 134 | granite-3.1-2b-instruct | -1 | Q4_1 | slow |
| 135 | RWKV7-World-2.9B | -1 | IQ4_XS | slow |
| 136 | Llama-3.2-1B-Instruct | -1 | IQ1_S | slow |
| 137 | Qwen2.5-0.5B-Instruct | -1 | TQ2_0 | slow |
| 138 | Qwen2.5-1.5B-Instruct | -1 | Q3_K_S | fast |
| 139 | granite-3.2-2b-instruct | -1 | F16 | slow |
| 140 | MiniCPM5-2B | -1 | Q4_1 | slow |
| 141 | Qwen3-0.6B | -1 | IQ2_XXS | medium |
| 142 | Qwen3.5-2B | -1 | Q4_0 | slow |
| 143 | MiniCPM5-1B | -1 | Q5_0 | slow |
| 144 | granite-4.0-1b | -1 | IQ3_XS | slow |
| 145 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | fast |
| 146 | MiniCPM-1B-sft | -1 | Q1_0 | medium |
| 147 | Llama-3.2-3B-Instruct | -1 | IQ2_XS | slow |
| 148 | Llama-3.2-1B-Instruct | -1 | IQ2_XXS | medium |
| 149 | MiniCPM4-0.5B | -1 | IQ2_XXS | slow |
| 150 | MiniCPM-2B-sft | -1 | Q4_K_M | slow |
| 151 | granite-4.0-h-350m | -1 | Q8_0 | fast |
| 152 | AI21-Jamba-Reasoning-3B | -1 | IQ4_XS | slow |
| 153 | Qwen3-2B | -1 | Q2_K_S | slow |
| 154 | Llama-3.2-3B-Instruct | -1 | IQ3_XS | slow |
| 155 | Llama-3.2-1B-Instruct | -1 | IQ2_S | slow |
| 156 | Qwen3-0.6B | -1 | IQ2_XS | slow |
| 157 | granite-4.0-h-1b | -1 | IQ4_NL | medium |

_157 candidates run of 2048; each one chance, the seed recorded in state._
