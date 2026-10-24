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
| 7 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 8 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 9 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 10 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 11 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 12 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 13 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 14 | granite-3.2-2b-instruct | 0 | Q6_K | fast |
| 15 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 16 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 17 | granite-4.0-1b | -1 | Q1_0 | slow |
| 18 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 19 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 20 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 21 | granite-4.0-1b | -1 | Q4_1 | slow |
| 22 | phi-2 | -1 | Q2_0 | slow |
| 23 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 24 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 25 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 26 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 27 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 28 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 29 | MiniCPM5-1B | -1 | Q6_K | slow |
| 30 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 31 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 32 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 33 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 34 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 35 | Qwen3.5-2B | -1 | Q2_K | slow |
| 36 | phi-1 | -1 | IQ3_S | slow |
| 37 | phi-2 | -1 | IQ4_XS | slow |
| 38 | MiniCPM5-2B | -1 | Q5_1 | slow |
| 39 | phi-1 | -1 | Q2_K_S | medium |
| 40 | Llama-3.2-1B-Instruct | -1 | Q1_0 | slow |
| 41 | Qwen3.5-2B | -1 | Q3_K_L | slow |
| 42 | phi-4-mini-instruct | -1 | Q4_K_S | slow |
| 43 | gemma-3-1b-it | -1 | F16 | medium |

_43 candidates run of 2048; each one chance, the seed recorded in state._
