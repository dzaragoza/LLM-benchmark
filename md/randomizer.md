# randomizer.md - the randomizer ledger

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | speed |
|---|---|---|---|---|
| 1 | Phi-3-mini-4k-instruct | 2 | Q5_0 | fast |
| 2 | MiniCPM3-4B | 2 | Q4_K_S | medium |
| 3 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 4 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 5 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 6 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 7 | granite-4.0-1b | -1 | Q1_0 | slow |
| 8 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 9 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 10 | gemma-3-4b-it | -1 | IQ3_XS | slow |
| 11 | granite-4.0-1b | -1 | Q4_1 | slow |
| 12 | phi-2 | -1 | Q2_0 | slow |
| 13 | granite-4.0-h-1b | -1 | Q2_K_S | slow |
| 14 | granite-4.0-h-micro | -1 | Q2_0 | slow |
| 15 | SmolLM2-1.7B-Instruct | -1 | Q2_K_S | slow |
| 16 | granite-4.0-h-350m | -1 | TQ1_0 | slow |
| 17 | granite-3.3-2b-instruct | -1 | Q2_K | slow |
| 18 | granite-3.2-2b-instruct | -1 | TQ1_0 | slow |

_18 candidates run of 2048; each one chance, the seed recorded in state._
