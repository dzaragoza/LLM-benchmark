# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 169 done candidates, top 8 (8 of 169)
- params median: **2.958 B**
- quant levels: Q5 x2, Q4 x2, Q8 x2, Q3 x1, F16 x1
- high-score level time median: **27.3s**
- score median: **3**

_the machine sweet-spot band, live as the pool fills_

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | speed |
|---|---|---|---|---|
| 1 | granite-4.0-micro | 6 | Q5_1 | medium |
| 2 | granite-4.0-h-micro | 4 | Q4_0 | medium |
| 3 | MiniCPM-2B-sft | 3 | Q5_K_M | fast |
| 4 | granite-4.1-3b | 3 | Q3_K_M | medium |
| 5 | granite-4.0-h-1b | 3 | Q8_0 | slow |
| 6 | Qwen3.5-0.8B | 2 | Q8_0 | fast |
| 7 | MiniCPM-1B-sft | 2 | F16 | fast |
| 8 | granite-4.1-3b | 2 | Q4_0 | fast |
| 9 | Phi-3-mini-4k-instruct | 2 | Q5_0 | fast |
| 10 | Phi-3.5-mini-instruct | 2 | Q4_K_M | medium |
| 11 | MiniCPM3-4B | 2 | Q4_K_S | medium |
| 12 | granite-4.1-3b | 2 | F16 | medium |
| 13 | Llama-3.2-1B-Instruct | 1 | Q4_1 | fast |
| 14 | Qwen3-0.6B | 1 | Q4_K_S | fast |
| 15 | Qwen3-1.7B | 1 | Q3_K_M | fast |
| 16 | Qwen3-2B | 1 | Q3_K_S | fast |
| 17 | granite-3.3-2b-instruct | 1 | Q3_K_M | fast |
| 18 | Phi-3-mini-4k-instruct | 1 | IQ3_XS | fast |
| 19 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 20 | granite-3.1-2b-instruct | 1 | Q3_K_S | fast |
| 21 | gemma-3-4b-it | 1 | Q5_1 | fast |
| 22 | phi-4-mini-instruct | 1 | Q5_1 | fast |
| 23 | Phi-3.5-mini-instruct | 1 | IQ4_XS | fast |
| 24 | granite-4.0-h-1b | 1 | Q5_K_M | slow |
| 25 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 26 | Qwen3-0.6B | 0 | IQ3_XS | fast |
| 27 | Qwen3-0.6B | 0 | Q4_0 | fast |
| 28 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 29 | gemma-3-1b-it | 0 | IQ3_S | fast |
| 30 | gemma-3-1b-it | 0 | Q5_0 | fast |
| 31 | gemma-3-1b-it | 0 | Q3_K_M | fast |
| 32 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 33 | Qwen3-1.7B | 0 | Q4_1 | fast |
| 34 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 35 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 36 | Qwen3-0.6B | 0 | Q5_K_S | fast |
| 37 | granite-3.0-2b-instruct | 0 | Q3_K_L | fast |
| 38 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 39 | SmolLM2-1.7B-Instruct | 0 | Q4_0 | fast |
| 40 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 41 | granite-4.1-3b | 0 | IQ2_M | fast |
| 42 | granite-3.0-2b-instruct | 0 | Q6_K | fast |
| 43 | Qwen3-2B | 0 | IQ4_XS | fast |
| 44 | MiniCPM3-4B | 0 | Q3_K_M | fast |
| 45 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 46 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 47 | Phi-3-mini-128k-instruct | 0 | Q5_0 | fast |
| 48 | MiniCPM3-4B | 0 | IQ3_XXS | fast |
| 49 | SmolLM3-3B | 0 | Q4_K_S | fast |
| 50 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 51 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 52 | Qwen2.5-3B-Instruct | 0 | IQ2_M | slow |
| 53 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 54 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 55 | granite-4.0-1b | -1 | Q1_0 | slow |
| 56 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 57 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 58 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 59 | granite-4.0-1b | -1 | Q4_1 | slow |
| 60 | phi-2 | -1 | Q2_0 | slow |
| 61 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 62 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 63 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 64 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 65 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 66 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 67 | MiniCPM5-1B | -1 | Q6_K | slow |
| 68 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 69 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 70 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 71 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 72 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 73 | Qwen3.5-2B | -1 | Q2_K | slow |
| 74 | phi-1 | -1 | IQ3_S | slow |
| 75 | phi-2 | -1 | IQ4_XS | slow |
| 76 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 77 | phi-1 | -1 | Q2_K_S | medium |
| 78 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 79 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 80 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 81 | gemma-3-1b-it | -1 | F16 | medium |
| 82 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 83 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 84 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 85 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 86 | granite-4.0-350m | -1 | Q5_0 | fast |
| 87 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 88 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 89 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 90 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 91 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 92 | Qwen3-2B | -1 | Q4_K_M | slow |
| 93 | granite-4.0-micro | -1 | Q4_0 | slow |
| 94 | phi-2 | -1 | Q5_1 | medium |
| 95 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 96 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 97 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 98 | Qwen3-2B | -1 | IQ3_XS | slow |
| 99 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 100 | Qwen3-2B | -1 | IQ3_S | slow |
| 101 | phi-2 | -1 | IQ1_M | slow |
| 102 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 103 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 104 | MiniCPM4-0.5B | -1 | F16 | fast |
| 105 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 106 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 107 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 108 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 109 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 110 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 111 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 112 | Qwen3-2B | -1 | IQ2_XS | slow |
| 113 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 114 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 115 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |
| 116 | Ministral-3-3B-Instruct-2512 | -1 | IQ2_S | slow |
| 117 | granite-4.0-h-1b | -1 | Q4_0 | slow |
| 118 | Qwen3.5-0.8B | -1 | IQ2_M | slow |
| 119 | MiniCPM-1B-sft | -1 | Q5_K_S | slow |
| 120 | Qwen3-2B | -1 | Q4_0 | slow |
| 121 | SmolLM2-360M-Instruct | -1 | IQ2_S | slow |
| 122 | MiniCPM4-0.5B | -1 | IQ3_XS | fast |
| 123 | AI21-Jamba2-3B | -1 | IQ3_XS | slow |
| 124 | Qwen2.5-3B-Instruct | -1 | Q2_0 | slow |
| 125 | MiniCPM3-4B | -1 | TQ1_0 | slow |
| 126 | Qwen3.5-2B | -1 | IQ1_M | slow |
| 127 | granite-4.0-350m | -1 | Q3_K_M | slow |
| 128 | granite-4.0-1b | -1 | IQ4_NL | medium |
| 129 | Qwen3.5-2B | -1 | IQ3_XS | slow |
| 130 | MiniCPM-2B-sft | -1 | Q5_K_S | slow |
| 131 | AI21-Jamba-Reasoning-3B | -1 | Q6_K | slow |
| 132 | gemma-2-2b-it | -1 | TQ2_0 | slow |
| 133 | granite-4.0-h-350m | -1 | Q6_K | fast |
| 134 | MiniCPM4-0.5B | -1 | IQ3_S | slow |
| 135 | SmolLM3-3B | -1 | IQ1_M | slow |
| 136 | granite-4.0-h-350m | -1 | Q4_1 | fast |
| 137 | granite-4.0-h-micro | -1 | IQ1_M | medium |
| 138 | Qwen3-2B | -1 | F16 | slow |
| 139 | granite-3.1-2b-instruct | -1 | Q4_1 | slow |
| 140 | RWKV7-World-2.9B | -1 | IQ4_XS | slow |
| 141 | Llama-3.2-1B-Instruct | -1 | IQ1_S | slow |
| 142 | Qwen2.5-0.5B-Instruct | -1 | TQ2_0 | slow |
| 143 | Qwen2.5-1.5B-Instruct | -1 | Q3_K_S | fast |
| 144 | granite-3.2-2b-instruct | -1 | F16 | slow |
| 145 | MiniCPM5-2B | -1 | Q4_1 | slow |
| 146 | Qwen3-0.6B | -1 | IQ2_XXS | medium |
| 147 | Qwen3.5-2B | -1 | Q4_0 | slow |
| 148 | MiniCPM5-1B | -1 | Q5_0 | slow |
| 149 | granite-4.0-1b | -1 | IQ3_XS | slow |
| 150 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | fast |
| 151 | MiniCPM-1B-sft | -1 | Q1_0 | medium |
| 152 | Llama-3.2-3B-Instruct | -1 | IQ2_XS | slow |
| 153 | Llama-3.2-1B-Instruct | -1 | IQ2_XXS | medium |
| 154 | MiniCPM4-0.5B | -1 | IQ2_XXS | slow |
| 155 | MiniCPM-2B-sft | -1 | Q4_K_M | slow |
| 156 | granite-4.0-h-350m | -1 | Q8_0 | fast |
| 157 | AI21-Jamba-Reasoning-3B | -1 | IQ4_XS | slow |
| 158 | Qwen3-2B | -1 | Q2_K_S | slow |
| 159 | Llama-3.2-3B-Instruct | -1 | IQ3_XS | slow |
| 160 | Llama-3.2-1B-Instruct | -1 | IQ2_S | slow |
| 161 | Qwen3-0.6B | -1 | IQ2_XS | slow |
| 162 | granite-4.0-h-1b | -1 | IQ4_NL | medium |
| 163 | granite-4.1-3b | -1 | Q1_0 | slow |
| 164 | SmolLM2-1.7B-Instruct | -1 | IQ2_M | slow |
| 165 | Qwen3-2B | -1 | IQ2_S | slow |
| 166 | granite-4.0-h-1b | -1 | Q3_K_M | fast |
| 167 | Qwen2.5-3B-Instruct | -1 | Q2_K_S | slow |
| 168 | MiniCPM4-0.5B | -1 | IQ3_M | slow |
| 169 | MiniCPM3-4B | -1 | Q3_K_S | slow |

_169 candidates run of 2048; each one chance, the seed recorded in state._
