# randomizer.md - the randomizer ledger

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | speed |
|---|---|---|---|---|
| 1 | MiniCPM3-4B | 2 | Q4_K_S | medium |
| 2 | MiniCPM-2B-sft | 1 | Q3_K_S | fast |
| 3 | granite-3.0-2b-instruct | 0 | Q4_K_S | fast |
| 4 | MiniCPM3-4B | 0 | Q5_K_S | medium |
| 5 | Phi-3-mini-128k-instruct | -1 | IQ1_S | slow |
| 6 | granite-4.0-1b | -1 | Q1_0 | slow |
| 7 | Qwen2.5-3B-Instruct | -1 | Q5_1 | slow |
| 8 | gemma-3-4b-it | -1 | IQ1_S | slow |
| 9 | gemma-3-4b-it | -1 | IQ3_XS | slow |

_9 candidates run of 2048; each one chance, the seed recorded in state._
