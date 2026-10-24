# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 181 done candidates, top 9 (9 of 181)
- params median: **2.725 B**
- quant levels: Q4 x3, Q5 x2, Q8 x2, Q3 x1, F16 x1
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
| 8 | granite-3.3-2b-instruct | 2 | Q4_K_S | fast |
| 9 | granite-4.1-3b | 2 | Q4_0 | fast |
| 10 | Phi-3-mini-4k-instruct | 2 | Q5_0 | fast |
| 11 | Phi-3.5-mini-instruct | 2 | Q4_K_M | medium |
| 12 | MiniCPM3-4B | 2 | Q4_K_S | medium |
| 13 | granite-4.1-3b | 2 | F16 | medium |
| 14 | Llama-3.2-1B-Instruct | 1 | Q4_1 | fast |
| 15 | Qwen3-0.6B | 1 | Q4_K_S | fast |
| 16 | Qwen3-1.7B | 1 | Q3_K_M | fast |
| 17 | Qwen3-2B | 1 | Q3_K_S | fast |
| 18 | granite-3.3-2b-instruct | 1 | Q3_K_M | fast |
| 19 | granite-3.0-2b-instruct | 1 | IQ3_XS | fast |
| 20 | Phi-3-mini-4k-instruct | 1 | IQ3_XS | fast |
| 21 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 22 | granite-3.1-2b-instruct | 1 | Q3_K_S | fast |
| 23 | gemma-3-4b-it | 1 | Q5_1 | fast |
| 24 | phi-4-mini-instruct | 1 | Q5_1 | fast |
| 25 | Phi-3.5-mini-instruct | 1 | IQ4_XS | fast |
| 26 | granite-4.0-h-1b | 1 | Q5_K_M | slow |
| 27 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 28 | Qwen3-0.6B | 0 | IQ3_XS | fast |
| 29 | Qwen3-0.6B | 0 | Q4_0 | fast |
| 30 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 31 | gemma-3-1b-it | 0 | IQ3_S | fast |
| 32 | gemma-3-1b-it | 0 | Q5_0 | fast |
| 33 | gemma-3-1b-it | 0 | Q3_K_M | fast |
| 34 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 35 | Qwen3-1.7B | 0 | Q4_1 | fast |
| 36 | granite-3.2-2b-instruct | 0 | IQ2_XXS | fast |
| 37 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 38 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 39 | Qwen3-0.6B | 0 | Q5_K_S | fast |
| 40 | granite-3.0-2b-instruct | 0 | Q3_K_L | fast |
| 41 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 42 | SmolLM2-1.7B-Instruct | 0 | Q4_0 | fast |
| 43 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 44 | granite-4.1-3b | 0 | IQ2_M | fast |
| 45 | granite-3.0-2b-instruct | 0 | Q6_K | fast |
| 46 | Qwen3-2B | 0 | IQ4_XS | fast |
| 47 | MiniCPM3-4B | 0 | Q3_K_M | fast |
| 48 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 49 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 50 | Phi-3-mini-128k-instruct | 0 | Q5_0 | fast |
| 51 | MiniCPM3-4B | 0 | IQ3_XXS | fast |
| 52 | SmolLM3-3B | 0 | Q4_K_S | fast |
| 53 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 54 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 55 | Qwen2.5-3B-Instruct | 0 | IQ2_M | slow |
| 56 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 57 | gemma-3-4b-it | 0 | Q5_K_M | slow |
| 58 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 59 | granite-4.0-1b | -1 | Q1_0 | slow |
| 60 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 61 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 62 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 63 | granite-4.0-1b | -1 | Q4_1 | slow |
| 64 | phi-2 | -1 | Q2_0 | slow |
| 65 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 66 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 67 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 68 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 69 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 70 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 71 | MiniCPM5-1B | -1 | Q6_K | slow |
| 72 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 73 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 74 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 75 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 76 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 77 | Qwen3.5-2B | -1 | Q2_K | slow |
| 78 | phi-1 | -1 | IQ3_S | slow |
| 79 | phi-2 | -1 | IQ4_XS | slow |
| 80 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 81 | phi-1 | -1 | Q2_K_S | medium |
| 82 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 83 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 84 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 85 | gemma-3-1b-it | -1 | F16 | medium |
| 86 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 87 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 88 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 89 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 90 | granite-4.0-350m | -1 | Q5_0 | fast |
| 91 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 92 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 93 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 94 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 95 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 96 | Qwen3-2B | -1 | Q4_K_M | slow |
| 97 | granite-4.0-micro | -1 | Q4_0 | slow |
| 98 | phi-2 | -1 | Q5_1 | medium |
| 99 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 100 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 101 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 102 | Qwen3-2B | -1 | IQ3_XS | slow |
| 103 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 104 | Qwen3-2B | -1 | IQ3_S | slow |
| 105 | phi-2 | -1 | IQ1_M | slow |
| 106 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 107 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 108 | MiniCPM4-0.5B | -1 | F16 | fast |
| 109 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 110 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 111 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 112 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 113 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 114 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 115 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 116 | Qwen3-2B | -1 | IQ2_XS | slow |
| 117 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 118 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 119 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |
| 120 | Ministral-3-3B-Instruct-2512 | -1 | IQ2_S | slow |
| 121 | granite-4.0-h-1b | -1 | Q4_0 | slow |
| 122 | Qwen3.5-0.8B | -1 | IQ2_M | slow |
| 123 | MiniCPM-1B-sft | -1 | Q5_K_S | slow |
| 124 | Qwen3-2B | -1 | Q4_0 | slow |
| 125 | SmolLM2-360M-Instruct | -1 | IQ2_S | slow |
| 126 | MiniCPM4-0.5B | -1 | IQ3_XS | fast |
| 127 | AI21-Jamba2-3B | -1 | IQ3_XS | slow |
| 128 | Qwen2.5-3B-Instruct | -1 | Q2_0 | slow |
| 129 | MiniCPM3-4B | -1 | TQ1_0 | slow |
| 130 | Qwen3.5-2B | -1 | IQ1_M | slow |
| 131 | granite-4.0-350m | -1 | Q3_K_M | slow |
| 132 | granite-4.0-1b | -1 | IQ4_NL | medium |
| 133 | Qwen3.5-2B | -1 | IQ3_XS | slow |
| 134 | MiniCPM-2B-sft | -1 | Q5_K_S | slow |
| 135 | AI21-Jamba-Reasoning-3B | -1 | Q6_K | slow |
| 136 | gemma-2-2b-it | -1 | TQ2_0 | slow |
| 137 | granite-4.0-h-350m | -1 | Q6_K | fast |
| 138 | MiniCPM4-0.5B | -1 | IQ3_S | slow |
| 139 | SmolLM3-3B | -1 | IQ1_M | slow |
| 140 | granite-4.0-h-350m | -1 | Q4_1 | fast |
| 141 | granite-4.0-h-micro | -1 | IQ1_M | medium |
| 142 | Qwen3-2B | -1 | F16 | slow |
| 143 | granite-3.1-2b-instruct | -1 | Q4_1 | slow |
| 144 | RWKV7-World-2.9B | -1 | IQ4_XS | slow |
| 145 | Llama-3.2-1B-Instruct | -1 | IQ1_S | slow |
| 146 | Qwen2.5-0.5B-Instruct | -1 | TQ2_0 | slow |
| 147 | Qwen2.5-1.5B-Instruct | -1 | Q3_K_S | fast |
| 148 | granite-3.2-2b-instruct | -1 | F16 | slow |
| 149 | MiniCPM5-2B | -1 | Q4_1 | slow |
| 150 | Qwen3-0.6B | -1 | IQ2_XXS | medium |
| 151 | Qwen3.5-2B | -1 | Q4_0 | slow |
| 152 | MiniCPM5-1B | -1 | Q5_0 | slow |
| 153 | granite-4.0-1b | -1 | IQ3_XS | slow |
| 154 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | fast |
| 155 | MiniCPM-1B-sft | -1 | Q1_0 | medium |
| 156 | Llama-3.2-3B-Instruct | -1 | IQ2_XS | slow |
| 157 | Llama-3.2-1B-Instruct | -1 | IQ2_XXS | medium |
| 158 | MiniCPM4-0.5B | -1 | IQ2_XXS | slow |
| 159 | MiniCPM-2B-sft | -1 | Q4_K_M | slow |
| 160 | granite-4.0-h-350m | -1 | Q8_0 | fast |
| 161 | AI21-Jamba-Reasoning-3B | -1 | IQ4_XS | slow |
| 162 | Qwen3-2B | -1 | Q2_K_S | slow |
| 163 | Llama-3.2-3B-Instruct | -1 | IQ3_XS | slow |
| 164 | Llama-3.2-1B-Instruct | -1 | IQ2_S | slow |
| 165 | Qwen3-0.6B | -1 | IQ2_XS | slow |
| 166 | granite-4.0-h-1b | -1 | IQ4_NL | medium |
| 167 | granite-4.1-3b | -1 | Q1_0 | slow |
| 168 | SmolLM2-1.7B-Instruct | -1 | IQ2_M | slow |
| 169 | Qwen3-2B | -1 | IQ2_S | slow |
| 170 | granite-4.0-h-1b | -1 | Q3_K_M | fast |
| 171 | Qwen2.5-3B-Instruct | -1 | Q2_K_S | slow |
| 172 | MiniCPM4-0.5B | -1 | IQ3_M | slow |
| 173 | MiniCPM3-4B | -1 | Q3_K_S | slow |
| 174 | gemma-3-1b-it | -1 | IQ1_S | slow |
| 175 | granite-3.3-2b-instruct | -1 | IQ1_M | slow |
| 176 | MiniCPM5-2B | -1 | IQ3_XXS | slow |
| 177 | Phi-3-mini-4k-instruct | -1 | IQ4_XS | slow |
| 178 | SmolLM3-3B | -1 | Q5_0 | slow |
| 179 | Qwen3.5-2B | -1 | Q5_0 | slow |
| 180 | gemma-2-2b-it | -1 | IQ2_XS | slow |
| 181 | phi-1 | -1 | IQ3_XS | medium |

_181 candidates run of 2048; each one chance, the seed recorded in state._
