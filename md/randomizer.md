# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 7 done candidates, top 1 (1 of 7)
- params median: **2.274 B**
- model_quant mode: **Q4_K_M**
- k_quant mode: **f16**
- v_quant mode: **q4_1**
- score median: **-1**

_the machine sweet-spot band, live as the pool fills_

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | k | v | speed |
|---|---|---|---|---|---|---|
| 1 | Qwen3-2B | -1 | Q4_K_M | f16 | q4_1 | slow |
| 2 | SmolLM2-360M-Instruct | -1 | IQ2_XXS | f16 | q4_1 | fast |
| 3 | MiniCPM5-1B | -1 | IQ4_NL | q4_1 | f16 | medium |
| 4 | granite-3.2-2b-instruct | -1 | Q5_K_M | q5_1 | q8_0 | slow |
| 5 | SmolLM3-3B | -1 | IQ3_XS | q4_1 | q5_1 | slow |
| 6 | granite-4.0-h-micro | -1 | Q3_K_S | q4_0 | q5_0 | slow |
| 7 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | q8_0 | iq4_nl | fast |

_7 candidates run of 100,352; each one chance, the seed recorded in state._
