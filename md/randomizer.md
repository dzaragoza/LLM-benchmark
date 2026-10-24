# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 176 done candidates, top 8 (8 of 176)
- params median: **2.6295 B**
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
| 19 | Phi-3-mini-4k-instruct | 1 | IQ3_XS | fast |
| 20 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 21 | granite-3.1-2b-instruct | 1 | Q3_K_S | fast |
| 22 | gemma-3-4b-it | 1 | Q5_1 | fast |
| 23 | phi-4-mini-instruct | 1 | Q5_1 | fast |
| 24 | Phi-3.5-mini-instruct | 1 | IQ4_XS | fast |
| 25 | granite-4.0-h-1b | 1 | Q5_K_M | slow |
| 26 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 27 | Qwen3-0.6B | 0 | IQ3_XS | fast |
| 28 | Qwen3-0.6B | 0 | Q4_0 | fast |
| 29 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 30 | gemma-3-1b-it | 0 | IQ3_S | fast |
| 31 | gemma-3-1b-it | 0 | Q5_0 | fast |
| 32 | gemma-3-1b-it | 0 | Q3_K_M | fast |
| 33 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 34 | Qwen3-1.7B | 0 | Q4_1 | fast |
| 35 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 36 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 37 | Qwen3-0.6B | 0 | Q5_K_S | fast |
| 38 | granite-3.0-2b-instruct | 0 | Q3_K_L | fast |
| 39 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 40 | SmolLM2-1.7B-Instruct | 0 | Q4_0 | fast |
| 41 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 42 | granite-4.1-3b | 0 | IQ2_M | fast |
| 43 | granite-3.0-2b-instruct | 0 | Q6_K | fast |
| 44 | Qwen3-2B | 0 | IQ4_XS | fast |
| 45 | MiniCPM3-4B | 0 | Q3_K_M | fast |
| 46 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 47 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 48 | Phi-3-mini-128k-instruct | 0 | Q5_0 | fast |
| 49 | MiniCPM3-4B | 0 | IQ3_XXS | fast |
| 50 | SmolLM3-3B | 0 | Q4_K_S | fast |
| 51 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 52 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 53 | Qwen2.5-3B-Instruct | 0 | IQ2_M | slow |
| 54 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 55 | gemma-3-4b-it | 0 | Q5_K_M | slow |
| 56 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 57 | granite-4.0-1b | -1 | Q1_0 | slow |
| 58 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 59 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 60 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 61 | granite-4.0-1b | -1 | Q4_1 | slow |
| 62 | phi-2 | -1 | Q2_0 | slow |
| 63 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 64 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 65 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 66 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 67 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 68 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 69 | MiniCPM5-1B | -1 | Q6_K | slow |
| 70 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 71 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 72 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 73 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 74 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 75 | Qwen3.5-2B | -1 | Q2_K | slow |
| 76 | phi-1 | -1 | IQ3_S | slow |
| 77 | phi-2 | -1 | IQ4_XS | slow |
| 78 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 79 | phi-1 | -1 | Q2_K_S | medium |
| 80 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 81 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 82 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 83 | gemma-3-1b-it | -1 | F16 | medium |
| 84 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 85 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 86 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 87 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 88 | granite-4.0-350m | -1 | Q5_0 | fast |
| 89 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 90 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 91 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 92 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 93 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 94 | Qwen3-2B | -1 | Q4_K_M | slow |
| 95 | granite-4.0-micro | -1 | Q4_0 | slow |
| 96 | phi-2 | -1 | Q5_1 | medium |
| 97 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 98 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 99 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 100 | Qwen3-2B | -1 | IQ3_XS | slow |
| 101 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 102 | Qwen3-2B | -1 | IQ3_S | slow |
| 103 | phi-2 | -1 | IQ1_M | slow |
| 104 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 105 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 106 | MiniCPM4-0.5B | -1 | F16 | fast |
| 107 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 108 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 109 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 110 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 111 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 112 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 113 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 114 | Qwen3-2B | -1 | IQ2_XS | slow |
| 115 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 116 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 117 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |
| 118 | Ministral-3-3B-Instruct-2512 | -1 | IQ2_S | slow |
| 119 | granite-4.0-h-1b | -1 | Q4_0 | slow |
| 120 | Qwen3.5-0.8B | -1 | IQ2_M | slow |
| 121 | MiniCPM-1B-sft | -1 | Q5_K_S | slow |
| 122 | Qwen3-2B | -1 | Q4_0 | slow |
| 123 | SmolLM2-360M-Instruct | -1 | IQ2_S | slow |
| 124 | MiniCPM4-0.5B | -1 | IQ3_XS | fast |
| 125 | AI21-Jamba2-3B | -1 | IQ3_XS | slow |
| 126 | Qwen2.5-3B-Instruct | -1 | Q2_0 | slow |
| 127 | MiniCPM3-4B | -1 | TQ1_0 | slow |
| 128 | Qwen3.5-2B | -1 | IQ1_M | slow |
| 129 | granite-4.0-350m | -1 | Q3_K_M | slow |
| 130 | granite-4.0-1b | -1 | IQ4_NL | medium |
| 131 | Qwen3.5-2B | -1 | IQ3_XS | slow |
| 132 | MiniCPM-2B-sft | -1 | Q5_K_S | slow |
| 133 | AI21-Jamba-Reasoning-3B | -1 | Q6_K | slow |
| 134 | gemma-2-2b-it | -1 | TQ2_0 | slow |
| 135 | granite-4.0-h-350m | -1 | Q6_K | fast |
| 136 | MiniCPM4-0.5B | -1 | IQ3_S | slow |
| 137 | SmolLM3-3B | -1 | IQ1_M | slow |
| 138 | granite-4.0-h-350m | -1 | Q4_1 | fast |
| 139 | granite-4.0-h-micro | -1 | IQ1_M | medium |
| 140 | Qwen3-2B | -1 | F16 | slow |
| 141 | granite-3.1-2b-instruct | -1 | Q4_1 | slow |
| 142 | RWKV7-World-2.9B | -1 | IQ4_XS | slow |
| 143 | Llama-3.2-1B-Instruct | -1 | IQ1_S | slow |
| 144 | Qwen2.5-0.5B-Instruct | -1 | TQ2_0 | slow |
| 145 | Qwen2.5-1.5B-Instruct | -1 | Q3_K_S | fast |
| 146 | granite-3.2-2b-instruct | -1 | F16 | slow |
| 147 | MiniCPM5-2B | -1 | Q4_1 | slow |
| 148 | Qwen3-0.6B | -1 | IQ2_XXS | medium |
| 149 | Qwen3.5-2B | -1 | Q4_0 | slow |
| 150 | MiniCPM5-1B | -1 | Q5_0 | slow |
| 151 | granite-4.0-1b | -1 | IQ3_XS | slow |
| 152 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | fast |
| 153 | MiniCPM-1B-sft | -1 | Q1_0 | medium |
| 154 | Llama-3.2-3B-Instruct | -1 | IQ2_XS | slow |
| 155 | Llama-3.2-1B-Instruct | -1 | IQ2_XXS | medium |
| 156 | MiniCPM4-0.5B | -1 | IQ2_XXS | slow |
| 157 | MiniCPM-2B-sft | -1 | Q4_K_M | slow |
| 158 | granite-4.0-h-350m | -1 | Q8_0 | fast |
| 159 | AI21-Jamba-Reasoning-3B | -1 | IQ4_XS | slow |
| 160 | Qwen3-2B | -1 | Q2_K_S | slow |
| 161 | Llama-3.2-3B-Instruct | -1 | IQ3_XS | slow |
| 162 | Llama-3.2-1B-Instruct | -1 | IQ2_S | slow |
| 163 | Qwen3-0.6B | -1 | IQ2_XS | slow |
| 164 | granite-4.0-h-1b | -1 | IQ4_NL | medium |
| 165 | granite-4.1-3b | -1 | Q1_0 | slow |
| 166 | SmolLM2-1.7B-Instruct | -1 | IQ2_M | slow |
| 167 | Qwen3-2B | -1 | IQ2_S | slow |
| 168 | granite-4.0-h-1b | -1 | Q3_K_M | fast |
| 169 | Qwen2.5-3B-Instruct | -1 | Q2_K_S | slow |
| 170 | MiniCPM4-0.5B | -1 | IQ3_M | slow |
| 171 | MiniCPM3-4B | -1 | Q3_K_S | slow |
| 172 | gemma-3-1b-it | -1 | IQ1_S | slow |
| 173 | granite-3.3-2b-instruct | -1 | IQ1_M | slow |
| 174 | MiniCPM5-2B | -1 | IQ3_XXS | slow |
| 175 | Phi-3-mini-4k-instruct | -1 | IQ4_XS | slow |
| 176 | SmolLM3-3B | -1 | Q5_0 | slow |

_176 candidates run of 2048; each one chance, the seed recorded in state._
