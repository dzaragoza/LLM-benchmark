# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 153 done candidates, top 7 (7 of 153)
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
| 21 | granite-4.0-h-1b | 1 | Q5_K_M | slow |
| 22 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 23 | Qwen3-0.6B | 0 | IQ3_XS | fast |
| 24 | Qwen3-0.6B | 0 | Q4_0 | fast |
| 25 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 26 | gemma-3-1b-it | 0 | IQ3_S | fast |
| 27 | gemma-3-1b-it | 0 | Q5_0 | fast |
| 28 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 29 | Qwen3-1.7B | 0 | Q4_1 | fast |
| 30 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 31 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 32 | Qwen3-0.6B | 0 | Q5_K_S | fast |
| 33 | granite-3.0-2b-instruct | 0 | Q3_K_L | fast |
| 34 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 35 | SmolLM2-1.7B-Instruct | 0 | Q4_0 | fast |
| 36 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 37 | granite-3.0-2b-instruct | 0 | Q6_K | fast |
| 38 | Qwen3-2B | 0 | IQ4_XS | fast |
| 39 | MiniCPM3-4B | 0 | Q3_K_M | fast |
| 40 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 41 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 42 | Phi-3-mini-128k-instruct | 0 | Q5_0 | fast |
| 43 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 44 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 45 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 46 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 47 | granite-4.0-1b | -1 | Q1_0 | slow |
| 48 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 49 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 50 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 51 | granite-4.0-1b | -1 | Q4_1 | slow |
| 52 | phi-2 | -1 | Q2_0 | slow |
| 53 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 54 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 55 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 56 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 57 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 58 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 59 | MiniCPM5-1B | -1 | Q6_K | slow |
| 60 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 61 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 62 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 63 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 64 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 65 | Qwen3.5-2B | -1 | Q2_K | slow |
| 66 | phi-1 | -1 | IQ3_S | slow |
| 67 | phi-2 | -1 | IQ4_XS | slow |
| 68 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 69 | phi-1 | -1 | Q2_K_S | medium |
| 70 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 71 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 72 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 73 | gemma-3-1b-it | -1 | F16 | medium |
| 74 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 75 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 76 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 77 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 78 | granite-4.0-350m | -1 | Q5_0 | fast |
| 79 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 80 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 81 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 82 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 83 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 84 | Qwen3-2B | -1 | Q4_K_M | slow |
| 85 | granite-4.0-micro | -1 | Q4_0 | slow |
| 86 | phi-2 | -1 | Q5_1 | medium |
| 87 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 88 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 89 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 90 | Qwen3-2B | -1 | IQ3_XS | slow |
| 91 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 92 | Qwen3-2B | -1 | IQ3_S | slow |
| 93 | phi-2 | -1 | IQ1_M | slow |
| 94 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 95 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 96 | MiniCPM4-0.5B | -1 | F16 | fast |
| 97 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 98 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 99 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 100 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 101 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 102 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 103 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 104 | Qwen3-2B | -1 | IQ2_XS | slow |
| 105 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 106 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 107 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |
| 108 | Ministral-3-3B-Instruct-2512 | -1 | IQ2_S | slow |
| 109 | granite-4.0-h-1b | -1 | Q4_0 | slow |
| 110 | Qwen3.5-0.8B | -1 | IQ2_M | slow |
| 111 | MiniCPM-1B-sft | -1 | Q5_K_S | slow |
| 112 | Qwen3-2B | -1 | Q4_0 | slow |
| 113 | SmolLM2-360M-Instruct | -1 | IQ2_S | slow |
| 114 | MiniCPM4-0.5B | -1 | IQ3_XS | fast |
| 115 | AI21-Jamba2-3B | -1 | IQ3_XS | slow |
| 116 | Qwen2.5-3B-Instruct | -1 | Q2_0 | slow |
| 117 | MiniCPM3-4B | -1 | TQ1_0 | slow |
| 118 | Qwen3.5-2B | -1 | IQ1_M | slow |
| 119 | granite-4.0-350m | -1 | Q3_K_M | slow |
| 120 | granite-4.0-1b | -1 | IQ4_NL | medium |
| 121 | Qwen3.5-2B | -1 | IQ3_XS | slow |
| 122 | MiniCPM-2B-sft | -1 | Q5_K_S | slow |
| 123 | AI21-Jamba-Reasoning-3B | -1 | Q6_K | slow |
| 124 | gemma-2-2b-it | -1 | TQ2_0 | slow |
| 125 | granite-4.0-h-350m | -1 | Q6_K | fast |
| 126 | MiniCPM4-0.5B | -1 | IQ3_S | slow |
| 127 | SmolLM3-3B | -1 | IQ1_M | slow |
| 128 | granite-4.0-h-350m | -1 | Q4_1 | fast |
| 129 | granite-4.0-h-micro | -1 | IQ1_M | medium |
| 130 | Qwen3-2B | -1 | F16 | slow |
| 131 | granite-3.1-2b-instruct | -1 | Q4_1 | slow |
| 132 | RWKV7-World-2.9B | -1 | IQ4_XS | slow |
| 133 | Llama-3.2-1B-Instruct | -1 | IQ1_S | slow |
| 134 | Qwen2.5-0.5B-Instruct | -1 | TQ2_0 | slow |
| 135 | Qwen2.5-1.5B-Instruct | -1 | Q3_K_S | fast |
| 136 | granite-3.2-2b-instruct | -1 | F16 | slow |
| 137 | MiniCPM5-2B | -1 | Q4_1 | slow |
| 138 | Qwen3-0.6B | -1 | IQ2_XXS | medium |
| 139 | Qwen3.5-2B | -1 | Q4_0 | slow |
| 140 | MiniCPM5-1B | -1 | Q5_0 | slow |
| 141 | granite-4.0-1b | -1 | IQ3_XS | slow |
| 142 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | fast |
| 143 | MiniCPM-1B-sft | -1 | Q1_0 | medium |
| 144 | Llama-3.2-3B-Instruct | -1 | IQ2_XS | slow |
| 145 | Llama-3.2-1B-Instruct | -1 | IQ2_XXS | medium |
| 146 | MiniCPM4-0.5B | -1 | IQ2_XXS | slow |
| 147 | MiniCPM-2B-sft | -1 | Q4_K_M | slow |
| 148 | granite-4.0-h-350m | -1 | Q8_0 | fast |
| 149 | AI21-Jamba-Reasoning-3B | -1 | IQ4_XS | slow |
| 150 | Qwen3-2B | -1 | Q2_K_S | slow |
| 151 | Llama-3.2-3B-Instruct | -1 | IQ3_XS | slow |
| 152 | Llama-3.2-1B-Instruct | -1 | IQ2_S | slow |
| 153 | Qwen3-0.6B | -1 | IQ2_XS | slow |

_153 candidates run of 2048; each one chance, the seed recorded in state._
