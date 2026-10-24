# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 163 done candidates, top 8 (8 of 163)
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
| 31 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 32 | Qwen3-1.7B | 0 | Q4_1 | fast |
| 33 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 34 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 35 | Qwen3-0.6B | 0 | Q5_K_S | fast |
| 36 | granite-3.0-2b-instruct | 0 | Q3_K_L | fast |
| 37 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 38 | SmolLM2-1.7B-Instruct | 0 | Q4_0 | fast |
| 39 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 40 | granite-3.0-2b-instruct | 0 | Q6_K | fast |
| 41 | Qwen3-2B | 0 | IQ4_XS | fast |
| 42 | MiniCPM3-4B | 0 | Q3_K_M | fast |
| 43 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 44 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 45 | Phi-3-mini-128k-instruct | 0 | Q5_0 | fast |
| 46 | MiniCPM3-4B | 0 | IQ3_XXS | fast |
| 47 | SmolLM3-3B | 0 | Q4_K_S | fast |
| 48 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 49 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 50 | Qwen2.5-3B-Instruct | 0 | IQ2_M | slow |
| 51 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 52 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 53 | granite-4.0-1b | -1 | Q1_0 | slow |
| 54 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 55 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 56 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 57 | granite-4.0-1b | -1 | Q4_1 | slow |
| 58 | phi-2 | -1 | Q2_0 | slow |
| 59 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 60 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 61 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 62 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 63 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 64 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 65 | MiniCPM5-1B | -1 | Q6_K | slow |
| 66 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 67 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 68 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 69 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 70 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 71 | Qwen3.5-2B | -1 | Q2_K | slow |
| 72 | phi-1 | -1 | IQ3_S | slow |
| 73 | phi-2 | -1 | IQ4_XS | slow |
| 74 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 75 | phi-1 | -1 | Q2_K_S | medium |
| 76 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 77 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 78 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 79 | gemma-3-1b-it | -1 | F16 | medium |
| 80 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 81 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 82 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 83 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 84 | granite-4.0-350m | -1 | Q5_0 | fast |
| 85 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 86 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 87 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 88 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 89 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 90 | Qwen3-2B | -1 | Q4_K_M | slow |
| 91 | granite-4.0-micro | -1 | Q4_0 | slow |
| 92 | phi-2 | -1 | Q5_1 | medium |
| 93 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 94 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 95 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 96 | Qwen3-2B | -1 | IQ3_XS | slow |
| 97 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 98 | Qwen3-2B | -1 | IQ3_S | slow |
| 99 | phi-2 | -1 | IQ1_M | slow |
| 100 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 101 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 102 | MiniCPM4-0.5B | -1 | F16 | fast |
| 103 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 104 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 105 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 106 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 107 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 108 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 109 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 110 | Qwen3-2B | -1 | IQ2_XS | slow |
| 111 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 112 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 113 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |
| 114 | Ministral-3-3B-Instruct-2512 | -1 | IQ2_S | slow |
| 115 | granite-4.0-h-1b | -1 | Q4_0 | slow |
| 116 | Qwen3.5-0.8B | -1 | IQ2_M | slow |
| 117 | MiniCPM-1B-sft | -1 | Q5_K_S | slow |
| 118 | Qwen3-2B | -1 | Q4_0 | slow |
| 119 | SmolLM2-360M-Instruct | -1 | IQ2_S | slow |
| 120 | MiniCPM4-0.5B | -1 | IQ3_XS | fast |
| 121 | AI21-Jamba2-3B | -1 | IQ3_XS | slow |
| 122 | Qwen2.5-3B-Instruct | -1 | Q2_0 | slow |
| 123 | MiniCPM3-4B | -1 | TQ1_0 | slow |
| 124 | Qwen3.5-2B | -1 | IQ1_M | slow |
| 125 | granite-4.0-350m | -1 | Q3_K_M | slow |
| 126 | granite-4.0-1b | -1 | IQ4_NL | medium |
| 127 | Qwen3.5-2B | -1 | IQ3_XS | slow |
| 128 | MiniCPM-2B-sft | -1 | Q5_K_S | slow |
| 129 | AI21-Jamba-Reasoning-3B | -1 | Q6_K | slow |
| 130 | gemma-2-2b-it | -1 | TQ2_0 | slow |
| 131 | granite-4.0-h-350m | -1 | Q6_K | fast |
| 132 | MiniCPM4-0.5B | -1 | IQ3_S | slow |
| 133 | SmolLM3-3B | -1 | IQ1_M | slow |
| 134 | granite-4.0-h-350m | -1 | Q4_1 | fast |
| 135 | granite-4.0-h-micro | -1 | IQ1_M | medium |
| 136 | Qwen3-2B | -1 | F16 | slow |
| 137 | granite-3.1-2b-instruct | -1 | Q4_1 | slow |
| 138 | RWKV7-World-2.9B | -1 | IQ4_XS | slow |
| 139 | Llama-3.2-1B-Instruct | -1 | IQ1_S | slow |
| 140 | Qwen2.5-0.5B-Instruct | -1 | TQ2_0 | slow |
| 141 | Qwen2.5-1.5B-Instruct | -1 | Q3_K_S | fast |
| 142 | granite-3.2-2b-instruct | -1 | F16 | slow |
| 143 | MiniCPM5-2B | -1 | Q4_1 | slow |
| 144 | Qwen3-0.6B | -1 | IQ2_XXS | medium |
| 145 | Qwen3.5-2B | -1 | Q4_0 | slow |
| 146 | MiniCPM5-1B | -1 | Q5_0 | slow |
| 147 | granite-4.0-1b | -1 | IQ3_XS | slow |
| 148 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | fast |
| 149 | MiniCPM-1B-sft | -1 | Q1_0 | medium |
| 150 | Llama-3.2-3B-Instruct | -1 | IQ2_XS | slow |
| 151 | Llama-3.2-1B-Instruct | -1 | IQ2_XXS | medium |
| 152 | MiniCPM4-0.5B | -1 | IQ2_XXS | slow |
| 153 | MiniCPM-2B-sft | -1 | Q4_K_M | slow |
| 154 | granite-4.0-h-350m | -1 | Q8_0 | fast |
| 155 | AI21-Jamba-Reasoning-3B | -1 | IQ4_XS | slow |
| 156 | Qwen3-2B | -1 | Q2_K_S | slow |
| 157 | Llama-3.2-3B-Instruct | -1 | IQ3_XS | slow |
| 158 | Llama-3.2-1B-Instruct | -1 | IQ2_S | slow |
| 159 | Qwen3-0.6B | -1 | IQ2_XS | slow |
| 160 | granite-4.0-h-1b | -1 | IQ4_NL | medium |
| 161 | granite-4.1-3b | -1 | Q1_0 | slow |
| 162 | SmolLM2-1.7B-Instruct | -1 | IQ2_M | slow |
| 163 | Qwen3-2B | -1 | IQ2_S | slow |

_163 candidates run of 2048; each one chance, the seed recorded in state._
