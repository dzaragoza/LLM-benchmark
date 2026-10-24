# randomizer.md - the randomizer ledger

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | speed |
|---|---|---|---|---|
| 1 | Phi-3-mini-4k-instruct | 2 | Q5_0 | fast |
| 2 | MiniCPM3-4B | 2 | Q4_K_S | medium |
| 3 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 4 | Qwen3-0.6B | 0 | Q3_K_L | fast |
| 5 | Phi-3-mini-128k-instruct | 0 | IQ3_XS | fast |
| 6 | SmolLM2-1.7B-Instruct | 0 | IQ3_M | fast |
| 7 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 8 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 9 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 10 | granite-4.0-1b | -1 | Q1_0 | slow |
| 11 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 12 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 13 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 14 | granite-4.0-1b | -1 | Q4_1 | slow |
| 15 | phi-2 | -1 | Q2_0 | slow |
| 16 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 17 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 18 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 19 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 20 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 21 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |
| 22 | MiniCPM5-1B | -1 | Q6_K | slow |
| 23 | Qwen3-4B-Instruct-2507 | -1 | Q3_K_L | slow |
| 24 | AI21-Jamba2-3B | -1 | Q5_K_S | slow |
| 25 | Qwen3-0.6B | -1 | Q1_0 | slow |
| 26 | Qwen2.5-3B-Instruct | -1 | Q3_K_S | fast |

_26 candidates run of 2048; each one chance, the seed recorded in state._
