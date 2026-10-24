# randomizer.md - the randomizer ledger

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | speed |
|---|---|---|---|---|
| 1 | Phi-3-mini-4k-instruct | 2 | Q5_0 | fast |
| 2 | MiniCPM3-4B | 2 | Q4_K_S | medium |
| 3 | Llama-3.2-1B-Instruct | 1 | Q4_1 | fast |
| 4 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 5 | granite-4.0-h-350m | 0 | Q5_K_S | fast |
| 6 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 7 | Qwen3-0.6B | 0 | IQ4_NL | fast |
| 8 | granite-4.0-h-micro | 0 | Q2_K | fast |
| 9 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 10 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 11 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 12 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 13 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 14 | granite-4.0-1b | -1 | Q1_0 | slow |
| 15 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 16 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 17 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 18 | granite-4.0-1b | -1 | Q4_1 | slow |
| 19 | phi-2 | -1 | Q2_0 | slow |
| 20 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 21 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 22 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 23 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 24 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 25 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 26 | MiniCPM5-1B | -1 | Q6_K | slow |
| 27 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 28 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 29 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 30 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |
| 31 | MiniCPM-2B-sft | -1 | IQ1_M | slow |
| 32 | Qwen3.5-2B | -1 | Q2_K | slow |
| 33 | phi-1 | -1 | IQ3_S | slow |
| 34 | phi-2 | -1 | IQ4_XS | slow |
| 35 | MiniCPM5-2B | -1 | Q5_1 | slow |

_35 candidates run of 2048; each one chance, the seed recorded in state._
