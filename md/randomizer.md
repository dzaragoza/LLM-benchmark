# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 115 done candidates, top 5 (5 of 115)
- params median: **3.191 B**
- quant levels: Q4 x2, Q5 x1, Q8 x1, F16 x1
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
| 3 | granite-4.0-h-1b | 3 | Q8_0 | slow |
| 4 | MiniCPM-1B-sft | 2 | F16 | fast |
| 5 | granite-4.1-3b | 2 | Q4_0 | fast |
| 6 | Phi-3-mini-4k-instruct | 2 | Q5_0 | fast |
| 7 | Phi-3.5-mini-instruct | 2 | Q4_K_M | medium |
| 8 | MiniCPM3-4B | 2 | Q4_K_S | medium |
| 9 | Llama-3.2-1B-Instruct | 1 | Q4_1 | fast |
| 10 | Qwen3-2B | 1 | Q3_K_S | fast |
| 11 | granite-3.3-2b-instruct | 1 | Q3_K_M | fast |
| 12 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 13 | granite-3.1-2b-instruct | 1 | Q3_K_S | fast |
| 14 | phi-4-mini-instruct | 1 | Q5_1 | fast |
| 15 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 16 | Qwen3-0.6B | 0 | IQ3_XS | fast |
| 17 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 18 | gemma-3-1b-it | 0 | IQ3_S | fast |
| 19 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 20 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 21 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 22 | granite-3.0-2b-instruct | 0 | Q3_K_L | fast |
| 23 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 24 | SmolLM2-1.7B-Instruct | 0 | Q4_0 | fast |
| 25 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 26 | granite-3.0-2b-instruct | 0 | Q6_K | fast |
| 27 | Qwen3-2B | 0 | IQ4_XS | fast |
| 28 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 29 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 30 | Phi-3-mini-128k-instruct | 0 | Q5_0 | fast |
| 31 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 32 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 33 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 34 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 35 | granite-4.0-1b | -1 | Q1_0 | slow |
| 36 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 37 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 38 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 39 | granite-4.0-1b | -1 | Q4_1 | slow |
| 40 | phi-2 | -1 | Q2_0 | slow |
| 41 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 42 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 43 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 44 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 45 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 46 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 47 | MiniCPM5-1B | -1 | Q6_K | slow |
| 48 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 49 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 50 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 51 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 52 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 53 | Qwen3.5-2B | -1 | Q2_K | slow |
| 54 | phi-1 | -1 | IQ3_S | slow |
| 55 | phi-2 | -1 | IQ4_XS | slow |
| 56 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 57 | phi-1 | -1 | Q2_K_S | medium |
| 58 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 59 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 60 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 61 | gemma-3-1b-it | -1 | F16 | medium |
| 62 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 63 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 64 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 65 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 66 | granite-4.0-350m | -1 | Q5_0 | fast |
| 67 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 68 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 69 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 70 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 71 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 72 | Qwen3-2B | -1 | Q4_K_M | slow |
| 73 | granite-4.0-micro | -1 | Q4_0 | slow |
| 74 | phi-2 | -1 | Q5_1 | medium |
| 75 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 76 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 77 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 78 | Qwen3-2B | -1 | IQ3_XS | slow |
| 79 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 80 | Qwen3-2B | -1 | IQ3_S | slow |
| 81 | phi-2 | -1 | IQ1_M | slow |
| 82 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 83 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 84 | MiniCPM4-0.5B | -1 | F16 | fast |
| 85 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 86 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 87 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 88 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 89 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 90 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 91 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 92 | Qwen3-2B | -1 | IQ2_XS | slow |
| 93 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 94 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 95 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |
| 96 | Ministral-3-3B-Instruct-2512 | -1 | IQ2_S | slow |
| 97 | granite-4.0-h-1b | -1 | Q4_0 | slow |
| 98 | Qwen3.5-0.8B | -1 | IQ2_M | slow |
| 99 | MiniCPM-1B-sft | -1 | Q5_K_S | slow |
| 100 | Qwen3-2B | -1 | Q4_0 | slow |
| 101 | SmolLM2-360M-Instruct | -1 | IQ2_S | slow |
| 102 | MiniCPM4-0.5B | -1 | IQ3_XS | fast |
| 103 | AI21-Jamba2-3B | -1 | IQ3_XS | slow |
| 104 | Qwen2.5-3B-Instruct | -1 | Q2_0 | slow |
| 105 | MiniCPM3-4B | -1 | TQ1_0 | slow |
| 106 | Qwen3.5-2B | -1 | IQ1_M | slow |
| 107 | granite-4.0-350m | -1 | Q3_K_M | slow |
| 108 | granite-4.0-1b | -1 | IQ4_NL | medium |
| 109 | Qwen3.5-2B | -1 | IQ3_XS | slow |
| 110 | MiniCPM-2B-sft | -1 | Q5_K_S | slow |
| 111 | AI21-Jamba-Reasoning-3B | -1 | Q6_K | slow |
| 112 | gemma-2-2b-it | -1 | TQ2_0 | slow |
| 113 | granite-4.0-h-350m | -1 | Q6_K | fast |
| 114 | MiniCPM4-0.5B | -1 | IQ3_S | slow |
| 115 | SmolLM3-3B | -1 | IQ1_M | slow |

_115 candidates run of 2048; each one chance, the seed recorded in state._
