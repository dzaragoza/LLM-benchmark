# randomizer.md - the randomizer ledger

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
| 13 | phi-4-mini-instruct | 1 | Q5_1 | fast |
| 14 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 15 | Qwen3-0.6B | 0 | IQ3_XS | fast |
| 16 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 17 | gemma-3-1b-it | 0 | IQ3_S | fast |
| 18 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 19 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 20 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 21 | granite-3.0-2b-instruct | 0 | Q3_K_L | fast |
| 22 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 23 | SmolLM2-1.7B-Instruct | 0 | Q4_0 | fast |
| 24 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 25 | Qwen3-2B | 0 | IQ4_XS | fast |
| 26 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 27 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 28 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 29 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 30 | Phi-3.5-mini-instruct | 0 | Q2_K_S | slow |
| 31 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 32 | granite-4.0-1b | -1 | Q1_0 | slow |
| 33 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 34 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 35 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 36 | granite-4.0-1b | -1 | Q4_1 | slow |
| 37 | phi-2 | -1 | Q2_0 | slow |
| 38 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 39 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 40 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 41 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 42 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 43 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 44 | MiniCPM5-1B | -1 | Q6_K | slow |
| 45 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 46 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 47 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 48 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 49 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 50 | Qwen3.5-2B | -1 | Q2_K | slow |
| 51 | phi-1 | -1 | IQ3_S | slow |
| 52 | phi-2 | -1 | IQ4_XS | slow |
| 53 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 54 | phi-1 | -1 | Q2_K_S | medium |
| 55 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 56 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 57 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 58 | gemma-3-1b-it | -1 | F16 | medium |
| 59 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 60 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 61 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 62 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 63 | granite-4.0-350m | -1 | Q5_0 | fast |
| 64 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 65 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 66 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 67 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 68 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 69 | Qwen3-2B | -1 | Q4_K_M | slow |
| 70 | granite-4.0-micro | -1 | Q4_0 | slow |
| 71 | phi-2 | -1 | Q5_1 | medium |
| 72 | Qwen3.5-2B | -1 | Q5_1 | slow |
| 73 | Qwen2.5-1.5B-Instruct | -1 | Q1_0 | slow |
| 74 | MiniCPM4-0.5B | -1 | Q4_K_S | fast |
| 75 | Qwen3-2B | -1 | IQ3_XS | slow |
| 76 | AI21-Jamba-Reasoning-3B | -1 | IQ1_S | slow |
| 77 | Qwen3-2B | -1 | IQ3_S | slow |
| 78 | phi-2 | -1 | IQ1_M | slow |
| 79 | MiniCPM5-2B | -1 | IQ2_XS | slow |
| 80 | granite-4.0-h-micro | -1 | IQ2_XXS | slow |
| 81 | MiniCPM4-0.5B | -1 | F16 | fast |
| 82 | MiniCPM4-0.5B | -1 | IQ2_S | slow |
| 83 | RWKV7-World-2.9B | -1 | Q3_K_S | fast |
| 84 | Llama-3.2-1B-Instruct | -1 | Q2_K_S | fast |
| 85 | MiniCPM-2B-sft | -1 | IQ4_XS | slow |
| 86 | MiniCPM-2B-sft | -1 | IQ2_XXS | slow |
| 87 | gemma-2-2b-it | -1 | IQ1_S | slow |
| 88 | Qwen3.5-2B | -1 | IQ3_S | slow |
| 89 | Qwen3-2B | -1 | IQ2_XS | slow |
| 90 | MiniCPM5-1B | -1 | IQ3_S | slow |
| 91 | granite-4.0-h-350m | -1 | Q4_K_S | fast |
| 92 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | slow |
| 93 | Ministral-3-3B-Instruct-2512 | -1 | IQ2_S | slow |
| 94 | granite-4.0-h-1b | -1 | Q4_0 | slow |
| 95 | Qwen3.5-0.8B | -1 | IQ2_M | slow |
| 96 | MiniCPM-1B-sft | -1 | Q5_K_S | slow |
| 97 | Qwen3-2B | -1 | Q4_0 | slow |
| 98 | SmolLM2-360M-Instruct | -1 | IQ2_S | slow |
| 99 | MiniCPM4-0.5B | -1 | IQ3_XS | fast |
| 100 | AI21-Jamba2-3B | -1 | IQ3_XS | slow |
| 101 | Qwen2.5-3B-Instruct | -1 | Q2_0 | slow |
| 102 | MiniCPM3-4B | -1 | TQ1_0 | slow |
| 103 | Qwen3.5-2B | -1 | IQ1_M | slow |
| 104 | granite-4.0-350m | -1 | Q3_K_M | slow |
| 105 | granite-4.0-1b | -1 | IQ4_NL | medium |
| 106 | Qwen3.5-2B | -1 | IQ3_XS | slow |

_106 candidates run of 2048; each one chance, the seed recorded in state._

## the top 5% dashboard

- measured: 106 done candidates, top 5 (5 of 106)
- params median: **3.191 B**
- quant distribution: Q4_0 x2, Q5_1 x1, Q8_0 x1, F16 x1
- high-score level time median: **35s**
- score median: **3**

_the machine sweet-spot band, live as the pool fills_
