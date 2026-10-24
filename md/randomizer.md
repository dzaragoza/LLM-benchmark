# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 124 done candidates, top 6 (6 of 124)
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
| 11 | Qwen3-2B | 1 | Q3_K_S | fast |
| 12 | granite-3.3-2b-instruct | 1 | Q3_K_M | fast |
| 13 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 14 | granite-3.1-2b-instruct | 1 | Q3_K_S | fast |
| 15 | phi-4-mini-instruct | 1 | Q5_1 | fast |
| 16 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 17 | Qwen3-0.6B | 0 | IQ3_XS | fast |
| 18 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 19 | gemma-3-1b-it | 0 | IQ3_S | fast |
| 20 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 21 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 22 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 23 | Qwen3-0.6B | 0 | Q5_K_S | fast |
| 24 | granite-3.0-2b-instruct | 0 | Q3_K_L | fast |
| 25 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 26 | SmolLM2-1.7B-Instruct | 0 | Q4_0 | fast |
| 27 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 28 | granite-3.0-2b-instruct | 0 | Q6_K | fast |
| 29 | Qwen3-2B | 0 | IQ4_XS | fast |
| 30 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 31 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 32 | Phi-3-mini-128k-instruct | 0 | Q5_0 | fast |
| 33 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 34 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 35 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 36 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 37 | granite-4.0-1b | -1 | Q1_0 | slow |
| 38 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 39 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 40 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 41 | granite-4.0-1b | -1 | Q4_1 | slow |
| 42 | phi-2 | -1 | Q2_0 | slow |
| 43 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 44 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 45 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 46 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 47 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 48 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 49 | MiniCPM5-1B | -1 | Q6_K | slow |
| 50 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 51 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 52 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 53 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 54 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 55 | Qwen3.5-2B | -1 | Q2_K | slow |
| 56 | phi-1 | -1 | IQ3_S | slow |
| 57 | phi-2 | -1 | IQ4_XS | slow |
| 58 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 59 | phi-1 | -1 | Q2_K_S | medium |
| 60 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 61 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 62 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 63 | gemma-3-1b-it | -1 | F16 | medium |
| 64 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 65 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 66 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 67 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 68 | granite-4.0-350m | -1 | Q5_0 | fast |
| 69 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 70 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 71 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 72 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 73 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 74 | Qwen3-2B | -1 | Q4_K_M | slow |
| 75 | granite-4.0-micro | -1 | Q4_0 | slow |
| 76 | phi-2 | -1 | Q5_1 | medium |
| 77 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 78 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 79 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 80 | Qwen3-2B | -1 | IQ3_XS | slow |
| 81 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 82 | Qwen3-2B | -1 | IQ3_S | slow |
| 83 | phi-2 | -1 | IQ1_M | slow |
| 84 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 85 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 86 | MiniCPM4-0.5B | -1 | F16 | fast |
| 87 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 88 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 89 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 90 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 91 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 92 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 93 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 94 | Qwen3-2B | -1 | IQ2_XS | slow |
| 95 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 96 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 97 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |
| 98 | Ministral-3-3B-Instruct-2512 | -1 | IQ2_S | slow |
| 99 | granite-4.0-h-1b | -1 | Q4_0 | slow |
| 100 | Qwen3.5-0.8B | -1 | IQ2_M | slow |
| 101 | MiniCPM-1B-sft | -1 | Q5_K_S | slow |
| 102 | Qwen3-2B | -1 | Q4_0 | slow |
| 103 | SmolLM2-360M-Instruct | -1 | IQ2_S | slow |
| 104 | MiniCPM4-0.5B | -1 | IQ3_XS | fast |
| 105 | AI21-Jamba2-3B | -1 | IQ3_XS | slow |
| 106 | Qwen2.5-3B-Instruct | -1 | Q2_0 | slow |
| 107 | MiniCPM3-4B | -1 | TQ1_0 | slow |
| 108 | Qwen3.5-2B | -1 | IQ1_M | slow |
| 109 | granite-4.0-350m | -1 | Q3_K_M | slow |
| 110 | granite-4.0-1b | -1 | IQ4_NL | medium |
| 111 | Qwen3.5-2B | -1 | IQ3_XS | slow |
| 112 | MiniCPM-2B-sft | -1 | Q5_K_S | slow |
| 113 | AI21-Jamba-Reasoning-3B | -1 | Q6_K | slow |
| 114 | gemma-2-2b-it | -1 | TQ2_0 | slow |
| 115 | granite-4.0-h-350m | -1 | Q6_K | fast |
| 116 | MiniCPM4-0.5B | -1 | IQ3_S | slow |
| 117 | SmolLM3-3B | -1 | IQ1_M | slow |
| 118 | granite-4.0-h-350m | -1 | Q4_1 | fast |
| 119 | granite-4.0-h-micro | -1 | IQ1_M | medium |
| 120 | Qwen3-2B | -1 | F16 | slow |
| 121 | granite-3.1-2b-instruct | -1 | Q4_1 | slow |
| 122 | RWKV7-World-2.9B | -1 | IQ4_XS | slow |
| 123 | Llama-3.2-1B-Instruct | -1 | IQ1_S | slow |
| 124 | Qwen2.5-0.5B-Instruct | -1 | TQ2_0 | slow |

_124 candidates run of 2048; each one chance, the seed recorded in state._
