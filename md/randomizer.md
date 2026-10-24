# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 187 done candidates, top 9 (9 of 187)
- params median: **2.534 B**
- quant levels: Q5 x2, Q4 x2, Q8 x2, Q3 x1, F16 x1, IQ3 x1
- high-score level time median: **19.6s**
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
| 8 | MiniCPM-1B-sft | 2 | IQ3_XXS | fast |
| 9 | granite-3.3-2b-instruct | 2 | Q4_K_S | fast |
| 10 | granite-4.1-3b | 2 | Q4_0 | fast |
| 11 | Phi-3-mini-4k-instruct | 2 | Q5_0 | fast |
| 12 | Phi-3.5-mini-instruct | 2 | Q4_K_M | medium |
| 13 | MiniCPM3-4B | 2 | Q4_K_S | medium |
| 14 | granite-4.1-3b | 2 | F16 | medium |
| 15 | Llama-3.2-1B-Instruct | 1 | Q4_1 | fast |
| 16 | Qwen3-0.6B | 1 | Q4_K_S | fast |
| 17 | Qwen3-1.7B | 1 | Q3_K_M | fast |
| 18 | Qwen3-2B | 1 | Q3_K_S | fast |
| 19 | granite-3.3-2b-instruct | 1 | Q3_K_M | fast |
| 20 | granite-3.0-2b-instruct | 1 | IQ3_XS | fast |
| 21 | Phi-3-mini-4k-instruct | 1 | IQ3_XS | fast |
| 22 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 23 | granite-3.1-2b-instruct | 1 | Q3_K_S | fast |
| 24 | gemma-3-4b-it | 1 | Q5_1 | fast |
| 25 | phi-4-mini-instruct | 1 | Q5_1 | fast |
| 26 | Phi-3.5-mini-instruct | 1 | IQ4_XS | fast |
| 27 | granite-4.0-h-1b | 1 | Q5_K_M | slow |
| 28 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 29 | Qwen3-0.6B | 0 | IQ3_XS | fast |
| 30 | Qwen3-0.6B | 0 | Q4_0 | fast |
| 31 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 32 | gemma-3-1b-it | 0 | IQ3_S | fast |
| 33 | gemma-3-1b-it | 0 | Q5_0 | fast |
| 34 | gemma-3-1b-it | 0 | Q3_K_M | fast |
| 35 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 36 | Qwen3-1.7B | 0 | Q4_1 | fast |
| 37 | granite-3.2-2b-instruct | 0 | IQ2_XXS | fast |
| 38 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 39 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 40 | Qwen3-0.6B | 0 | Q5_K_S | fast |
| 41 | granite-3.0-2b-instruct | 0 | Q3_K_L | fast |
| 42 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 43 | SmolLM2-1.7B-Instruct | 0 | Q4_0 | fast |
| 44 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 45 | granite-4.1-3b | 0 | IQ2_M | fast |
| 46 | granite-3.0-2b-instruct | 0 | Q6_K | fast |
| 47 | Qwen3-2B | 0 | IQ4_XS | fast |
| 48 | MiniCPM3-4B | 0 | Q3_K_M | fast |
| 49 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 50 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 51 | Phi-3-mini-128k-instruct | 0 | Q5_0 | fast |
| 52 | MiniCPM3-4B | 0 | IQ3_XXS | fast |
| 53 | SmolLM3-3B | 0 | Q4_K_S | fast |
| 54 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 55 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 56 | Qwen2.5-3B-Instruct | 0 | IQ2_M | slow |
| 57 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 58 | gemma-3-4b-it | 0 | Q5_K_M | slow |
| 59 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 60 | granite-4.0-1b | -1 | Q1_0 | slow |
| 61 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 62 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 63 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 64 | granite-4.0-1b | -1 | Q4_1 | slow |
| 65 | phi-2 | -1 | Q2_0 | slow |
| 66 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 67 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 68 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 69 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 70 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 71 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 72 | MiniCPM5-1B | -1 | Q6_K | slow |
| 73 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 74 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 75 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 76 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 77 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 78 | Qwen3.5-2B | -1 | Q2_K | slow |
| 79 | phi-1 | -1 | IQ3_S | slow |
| 80 | phi-2 | -1 | IQ4_XS | slow |
| 81 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 82 | phi-1 | -1 | Q2_K_S | medium |
| 83 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 84 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 85 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 86 | gemma-3-1b-it | -1 | F16 | medium |
| 87 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 88 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 89 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 90 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 91 | granite-4.0-350m | -1 | Q5_0 | fast |
| 92 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 93 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 94 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 95 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 96 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 97 | Qwen3-2B | -1 | Q4_K_M | slow |
| 98 | granite-4.0-micro | -1 | Q4_0 | slow |
| 99 | phi-2 | -1 | Q5_1 | medium |
| 100 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 101 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 102 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 103 | Qwen3-2B | -1 | IQ3_XS | slow |
| 104 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 105 | Qwen3-2B | -1 | IQ3_S | slow |
| 106 | phi-2 | -1 | IQ1_M | slow |
| 107 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 108 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 109 | MiniCPM4-0.5B | -1 | F16 | fast |
| 110 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 111 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 112 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 113 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 114 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 115 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 116 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 117 | Qwen3-2B | -1 | IQ2_XS | slow |
| 118 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 119 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 120 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |
| 121 | Ministral-3-3B-Instruct-2512 | -1 | IQ2_S | slow |
| 122 | granite-4.0-h-1b | -1 | Q4_0 | slow |
| 123 | Qwen3.5-0.8B | -1 | IQ2_M | slow |
| 124 | MiniCPM-1B-sft | -1 | Q5_K_S | slow |
| 125 | Qwen3-2B | -1 | Q4_0 | slow |
| 126 | SmolLM2-360M-Instruct | -1 | IQ2_S | slow |
| 127 | MiniCPM4-0.5B | -1 | IQ3_XS | fast |
| 128 | AI21-Jamba2-3B | -1 | IQ3_XS | slow |
| 129 | Qwen2.5-3B-Instruct | -1 | Q2_0 | slow |
| 130 | MiniCPM3-4B | -1 | TQ1_0 | slow |
| 131 | Qwen3.5-2B | -1 | IQ1_M | slow |
| 132 | granite-4.0-350m | -1 | Q3_K_M | slow |
| 133 | granite-4.0-1b | -1 | IQ4_NL | medium |
| 134 | Qwen3.5-2B | -1 | IQ3_XS | slow |
| 135 | MiniCPM-2B-sft | -1 | Q5_K_S | slow |
| 136 | AI21-Jamba-Reasoning-3B | -1 | Q6_K | slow |
| 137 | gemma-2-2b-it | -1 | TQ2_0 | slow |
| 138 | granite-4.0-h-350m | -1 | Q6_K | fast |
| 139 | MiniCPM4-0.5B | -1 | IQ3_S | slow |
| 140 | SmolLM3-3B | -1 | IQ1_M | slow |
| 141 | granite-4.0-h-350m | -1 | Q4_1 | fast |
| 142 | granite-4.0-h-micro | -1 | IQ1_M | medium |
| 143 | Qwen3-2B | -1 | F16 | slow |
| 144 | granite-3.1-2b-instruct | -1 | Q4_1 | slow |
| 145 | RWKV7-World-2.9B | -1 | IQ4_XS | slow |
| 146 | Llama-3.2-1B-Instruct | -1 | IQ1_S | slow |
| 147 | Qwen2.5-0.5B-Instruct | -1 | TQ2_0 | slow |
| 148 | Qwen2.5-1.5B-Instruct | -1 | Q3_K_S | fast |
| 149 | granite-3.2-2b-instruct | -1 | F16 | slow |
| 150 | MiniCPM5-2B | -1 | Q4_1 | slow |
| 151 | Qwen3-0.6B | -1 | IQ2_XXS | medium |
| 152 | Qwen3.5-2B | -1 | Q4_0 | slow |
| 153 | MiniCPM5-1B | -1 | Q5_0 | slow |
| 154 | granite-4.0-1b | -1 | IQ3_XS | slow |
| 155 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | fast |
| 156 | MiniCPM-1B-sft | -1 | Q1_0 | medium |
| 157 | Llama-3.2-3B-Instruct | -1 | IQ2_XS | slow |
| 158 | Llama-3.2-1B-Instruct | -1 | IQ2_XXS | medium |
| 159 | MiniCPM4-0.5B | -1 | IQ2_XXS | slow |
| 160 | MiniCPM-2B-sft | -1 | Q4_K_M | slow |
| 161 | granite-4.0-h-350m | -1 | Q8_0 | fast |
| 162 | AI21-Jamba-Reasoning-3B | -1 | IQ4_XS | slow |
| 163 | Qwen3-2B | -1 | Q2_K_S | slow |
| 164 | Llama-3.2-3B-Instruct | -1 | IQ3_XS | slow |
| 165 | Llama-3.2-1B-Instruct | -1 | IQ2_S | slow |
| 166 | Qwen3-0.6B | -1 | IQ2_XS | slow |
| 167 | granite-4.0-h-1b | -1 | IQ4_NL | medium |
| 168 | granite-4.1-3b | -1 | Q1_0 | slow |
| 169 | SmolLM2-1.7B-Instruct | -1 | IQ2_M | slow |
| 170 | Qwen3-2B | -1 | IQ2_S | slow |
| 171 | granite-4.0-h-1b | -1 | Q3_K_M | fast |
| 172 | Qwen2.5-3B-Instruct | -1 | Q2_K_S | slow |
| 173 | MiniCPM4-0.5B | -1 | IQ3_M | slow |
| 174 | MiniCPM3-4B | -1 | Q3_K_S | slow |
| 175 | gemma-3-1b-it | -1 | IQ1_S | slow |
| 176 | granite-3.3-2b-instruct | -1 | IQ1_M | slow |
| 177 | MiniCPM5-2B | -1 | IQ3_XXS | slow |
| 178 | Phi-3-mini-4k-instruct | -1 | IQ4_XS | slow |
| 179 | SmolLM3-3B | -1 | Q5_0 | slow |
| 180 | Qwen3.5-2B | -1 | Q5_0 | slow |
| 181 | gemma-2-2b-it | -1 | IQ2_XS | slow |
| 182 | phi-1 | -1 | IQ3_XS | medium |
| 183 | RWKV7-World-2.9B | -1 | TQ1_0 | slow |
| 184 | SmolLM2-360M-Instruct | -1 | IQ2_XXS | fast |
| 185 | AI21-Jamba2-3B | -1 | Q2_K_S | slow |
| 186 | SmolLM2-360M-Instruct | -1 | Q2_K_S | fast |
| 187 | gemma-3-1b-it | -1 | IQ3_XS | fast |

_187 candidates run of 2048; each one chance, the seed recorded in state._
