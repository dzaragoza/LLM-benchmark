# randomizer.md - the randomizer ledger

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | speed |
|---|---|---|---|---|
| 1 | granite-4.1-3b | 2 | Q4_0 | fast |
| 2 | Phi-3-mini-4k-instruct | 2 | Q5_0 | fast |
| 3 | MiniCPM3-4B | 2 | Q4_K_S | medium |
| 4 | Llama-3.2-1B-Instruct | 1 | Q4_1 | fast |
| 5 | Qwen3-2B | 1 | Q3_K_S | fast |
| 6 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 7 | phi-4-mini-instruct | 1 | Q5_1 | fast |
| 8 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 9 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 10 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 11 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 12 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 13 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 14 | Qwen3.5-2B | 0 | IQ2_M | fast |
| 15 | Qwen3-2B | 0 | IQ4_XS | fast |
| 16 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 17 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 18 | granite-3.3-2b-instruct | 0 | Q6_K | fast |
| 19 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 20 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 21 | granite-4.0-1b | -1 | Q1_0 | slow |
| 22 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 23 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 24 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 25 | granite-4.0-1b | -1 | Q4_1 | slow |
| 26 | phi-2 | -1 | Q2_0 | slow |
| 27 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 28 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 29 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 30 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 31 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 32 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 33 | MiniCPM5-1B | -1 | Q6_K | slow |
| 34 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 35 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 36 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 37 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 38 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 39 | Qwen3.5-2B | -1 | Q2_K | slow |
| 40 | phi-1 | -1 | IQ3_S | slow |
| 41 | phi-2 | -1 | IQ4_XS | slow |
| 42 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 43 | phi-1 | -1 | Q2_K_S | medium |
| 44 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 45 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 46 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 47 | gemma-3-1b-it | -1 | F16 | medium |
| 48 | Qwen3-1.7B | -1 | Q4_0 | slow |
| 49 | granite-3.2-2b-instruct | -1 | Q1_0 | slow |
| 50 | MiniCPM-2B-sft | -1 | Q4_K_S | slow |
| 51 | MiniCPM-1B-sft | -1 | Q2_K_S | slow |
| 52 | granite-4.0-350m | -1 | Q5_0 | fast |
| 53 | Phi-3-mini-4k-instruct | -1 | F16 | slow |
| 54 | Qwen2.5-1.5B-Instruct | -1 | IQ1_M | slow |
| 55 | RWKV7-World-2.9B | -1 | IQ3_S | slow |
| 56 | Qwen3.5-0.8B | -1 | IQ3_XS | slow |
| 57 | Qwen3-1.7B | -1 | Q5_0 | slow |
| 58 | Qwen3-2B | -1 | Q4_K_M | slow |
| 59 | granite-4.0-micro | -1 | Q4_0 | slow |

_59 candidates run of 2048; each one chance, the seed recorded in state._
