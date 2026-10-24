# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 146 done candidates, top 7 (7 of 146)
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
| 13 | Qwen3-1.7B | 1 | Q3_K_M | fast |
| 14 | Qwen3-2B | 1 | Q3_K_S | fast |
| 15 | granite-3.3-2b-instruct | 1 | Q3_K_M | fast |
| 16 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 17 | granite-3.1-2b-instruct | 1 | Q3_K_S | fast |
| 18 | phi-4-mini-instruct | 1 | Q5_1 | fast |
| 19 | granite-4.0-h-1b | 1 | Q5_K_M | slow |
| 20 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 21 | Qwen3-0.6B | 0 | IQ3_XS | fast |
| 22 | Qwen3-0.6B | 0 | Q4_0 | fast |
| 23 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 24 | gemma-3-1b-it | 0 | IQ3_S | fast |
| 25 | gemma-3-1b-it | 0 | Q5_0 | fast |
| 26 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 27 | Qwen3-1.7B | 0 | Q4_1 | fast |
| 28 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 29 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 30 | Qwen3-0.6B | 0 | Q5_K_S | fast |
| 31 | granite-3.0-2b-instruct | 0 | Q3_K_L | fast |
| 32 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 33 | SmolLM2-1.7B-Instruct | 0 | Q4_0 | fast |
| 34 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 35 | granite-3.0-2b-instruct | 0 | Q6_K | fast |
| 36 | Qwen3-2B | 0 | IQ4_XS | fast |
| 37 | MiniCPM3-4B | 0 | Q3_K_M | fast |
| 38 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 39 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 40 | Phi-3-mini-128k-instruct | 0 | Q5_0 | fast |
| 41 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 42 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 43 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 44 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 45 | granite-4.0-1b | -1 | Q1_0 | slow |
| 46 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 47 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 48 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 49 | granite-4.0-1b | -1 | Q4_1 | slow |
| 50 | phi-2 | -1 | Q2_0 | slow |
| 51 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 52 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 53 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 54 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 55 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 56 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 57 | MiniCPM5-1B | -1 | Q6_K | slow |
| 58 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 59 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 60 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 61 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 62 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 63 | Qwen3.5-2B | -1 | Q2_K | slow |
| 64 | phi-1 | -1 | IQ3_S | slow |
| 65 | phi-2 | -1 | IQ4_XS | slow |
| 66 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 67 | phi-1 | -1 | Q2_K_S | medium |
| 68 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 69 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 70 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 71 | gemma-3-1b-it | -1 | F16 | medium |
| 72 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 73 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 74 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 75 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 76 | granite-4.0-350m | -1 | Q5_0 | fast |
| 77 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 78 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 79 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 80 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 81 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 82 | Qwen3-2B | -1 | Q4_K_M | slow |
| 83 | granite-4.0-micro | -1 | Q4_0 | slow |
| 84 | phi-2 | -1 | Q5_1 | medium |
| 85 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 86 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 87 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 88 | Qwen3-2B | -1 | IQ3_XS | slow |
| 89 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 90 | Qwen3-2B | -1 | IQ3_S | slow |
| 91 | phi-2 | -1 | IQ1_M | slow |
| 92 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 93 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 94 | MiniCPM4-0.5B | -1 | F16 | fast |
| 95 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 96 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 97 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 98 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 99 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 100 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 101 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 102 | Qwen3-2B | -1 | IQ2_XS | slow |
| 103 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 104 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 105 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |
| 106 | Ministral-3-3B-Instruct-2512 | -1 | IQ2_S | slow |
| 107 | granite-4.0-h-1b | -1 | Q4_0 | slow |
| 108 | Qwen3.5-0.8B | -1 | IQ2_M | slow |
| 109 | MiniCPM-1B-sft | -1 | Q5_K_S | slow |
| 110 | Qwen3-2B | -1 | Q4_0 | slow |
| 111 | SmolLM2-360M-Instruct | -1 | IQ2_S | slow |
| 112 | MiniCPM4-0.5B | -1 | IQ3_XS | fast |
| 113 | AI21-Jamba2-3B | -1 | IQ3_XS | slow |
| 114 | Qwen2.5-3B-Instruct | -1 | Q2_0 | slow |
| 115 | MiniCPM3-4B | -1 | TQ1_0 | slow |
| 116 | Qwen3.5-2B | -1 | IQ1_M | slow |
| 117 | granite-4.0-350m | -1 | Q3_K_M | slow |
| 118 | granite-4.0-1b | -1 | IQ4_NL | medium |
| 119 | Qwen3.5-2B | -1 | IQ3_XS | slow |
| 120 | MiniCPM-2B-sft | -1 | Q5_K_S | slow |
| 121 | AI21-Jamba-Reasoning-3B | -1 | Q6_K | slow |
| 122 | gemma-2-2b-it | -1 | TQ2_0 | slow |
| 123 | granite-4.0-h-350m | -1 | Q6_K | fast |
| 124 | MiniCPM4-0.5B | -1 | IQ3_S | slow |
| 125 | SmolLM3-3B | -1 | IQ1_M | slow |
| 126 | granite-4.0-h-350m | -1 | Q4_1 | fast |
| 127 | granite-4.0-h-micro | -1 | IQ1_M | medium |
| 128 | Qwen3-2B | -1 | F16 | slow |
| 129 | granite-3.1-2b-instruct | -1 | Q4_1 | slow |
| 130 | RWKV7-World-2.9B | -1 | IQ4_XS | slow |
| 131 | Llama-3.2-1B-Instruct | -1 | IQ1_S | slow |
| 132 | Qwen2.5-0.5B-Instruct | -1 | TQ2_0 | slow |
| 133 | Qwen2.5-1.5B-Instruct | -1 | Q3_K_S | fast |
| 134 | granite-3.2-2b-instruct | -1 | F16 | slow |
| 135 | MiniCPM5-2B | -1 | Q4_1 | slow |
| 136 | Qwen3-0.6B | -1 | IQ2_XXS | medium |
| 137 | Qwen3.5-2B | -1 | Q4_0 | slow |
| 138 | MiniCPM5-1B | -1 | Q5_0 | slow |
| 139 | granite-4.0-1b | -1 | IQ3_XS | slow |
| 140 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | fast |
| 141 | MiniCPM-1B-sft | -1 | Q1_0 | medium |
| 142 | Llama-3.2-3B-Instruct | -1 | IQ2_XS | slow |
| 143 | Llama-3.2-1B-Instruct | -1 | IQ2_XXS | medium |
| 144 | MiniCPM4-0.5B | -1 | IQ2_XXS | slow |
| 145 | MiniCPM-2B-sft | -1 | Q4_K_M | slow |
| 146 | granite-4.0-h-350m | -1 | Q8_0 | fast |

_146 candidates run of 2048; each one chance, the seed recorded in state._
