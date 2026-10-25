# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 19 done candidates, top 1 (1 of 19)
- params median: **4.022 B**
- model_quant mode: **Q5_K_S**
- k_quant mode: **q5_1**
- v_quant mode: **q5_0**
- high-score level time median: **59.9s**
- score median: **1**

_the machine sweet-spot band, live as the pool fills_

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | k | v | speed |
|---|---|---|---|---|---|---|
| 1 | Qwen3-4B-Instruct-2507 | 1 | Q5_K_S | q5_1 | q5_0 | medium |
| 2 | Qwen3-2B | -1 | Q4_K_M | f16 | q4_1 | slow |
| 3 | SmolLM2-360M-Instruct | -1 | IQ2_XXS | f16 | q4_1 | fast |
| 4 | MiniCPM5-1B | -1 | IQ4_NL | q4_1 | f16 | medium |
| 5 | granite-3.2-2b-instruct | -1 | Q5_K_M | q5_1 | q8_0 | slow |
| 6 | SmolLM3-3B | -1 | IQ3_XS | q4_1 | q5_1 | slow |
| 7 | granite-4.0-h-micro | -1 | Q3_K_S | q4_0 | q5_0 | slow |
| 8 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | q8_0 | iq4_nl | fast |
| 9 | MiniCPM-2B-sft | -1 | IQ2_M | q4_1 | f16 | slow |
| 10 | Qwen2.5-1.5B-Instruct | -1 | IQ4_NL | f16 | iq4_nl | slow |
| 11 | Qwen2.5-1.5B-Instruct | -1 | IQ3_M | q8_0 | f16 | slow |
| 12 | Qwen3.5-2B | -1 | IQ1_S | q5_0 | q5_1 | slow |
| 13 | MiniCPM3-4B | -1 | Q2_K | q5_0 | q4_0 | slow |
| 14 | Phi-3-mini-128k-instruct | -1 | Q2_K_S | f16 | q4_1 | slow |
| 15 | granite-3.0-2b-instruct | -1 | TQ1_0 | q4_1 | q8_0 | slow |
| 16 | MiniCPM3-4B | -1 | IQ1_M | q8_0 | iq4_nl | slow |
| 17 | granite-4.0-h-1b | -1 | Q1_0 | q8_0 | q5_0 | medium |
| 18 | granite-4.0-1b | -1 | IQ3_S | q5_0 | q5_0 | medium |
| 19 | granite-4.2-3b | -1 | Q2_0 | q5_0 | q4_1 | slow |

_19 candidates run of 100,352; each one chance, the seed recorded in state._
