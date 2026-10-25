# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 37 done candidates, top 1 (1 of 37)
- params median: **0.7516 B**
- model_quant mode: **Q5_1**
- k_quant mode: **q8_0**
- v_quant mode: **q4_0**
- high-score level time median: **0.9s**
- score median: **1**

_the machine sweet-spot band, live as the pool fills_

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | k | v | speed |
|---|---|---|---|---|---|---|
| 1 | Qwen3-0.6B | 1 | Q5_1 | q8_0 | q4_0 | fast |
| 2 | gemma-3-1b-it | 1 | IQ3_M | q5_0 | f16 | fast |
| 3 | granite-3.3-2b-instruct | 1 | Q5_1 | q4_1 | q5_0 | fast |
| 4 | granite-3.0-2b-instruct | 1 | F16 | q8_0 | f16 | fast |
| 5 | granite-4.0-h-micro | 1 | Q5_K_S | q4_0 | q4_0 | fast |
| 6 | Qwen3-4B-Instruct-2507 | 1 | Q5_K_S | q5_1 | q5_0 | medium |
| 7 | Qwen2.5-3B-Instruct | 0 | Q5_0 | q4_0 | q4_0 | fast |
| 8 | Qwen3-2B | -1 | Q4_K_M | f16 | q4_1 | slow |
| 9 | SmolLM2-360M-Instruct | -1 | IQ2_XXS | f16 | q4_1 | fast |
| 10 | MiniCPM5-1B | -1 | IQ4_NL | q4_1 | f16 | medium |
| 11 | granite-3.2-2b-instruct | -1 | Q5_K_M | q5_1 | q8_0 | slow |
| 12 | SmolLM3-3B | -1 | IQ3_XS | q4_1 | q5_1 | slow |
| 13 | granite-4.0-h-micro | -1 | Q3_K_S | q4_0 | q5_0 | slow |
| 14 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | q8_0 | iq4_nl | fast |
| 15 | MiniCPM-2B-sft | -1 | IQ2_M | q4_1 | f16 | slow |
| 16 | Qwen2.5-1.5B-Instruct | -1 | IQ4_NL | f16 | iq4_nl | slow |
| 17 | Qwen2.5-1.5B-Instruct | -1 | IQ3_M | q8_0 | f16 | slow |
| 18 | Qwen3.5-2B | -1 | IQ1_S | q5_0 | q5_1 | slow |
| 19 | MiniCPM3-4B | -1 | Q2_K | q5_0 | q4_0 | slow |
| 20 | Phi-3-mini-128k-instruct | -1 | Q2_K_S | f16 | q4_1 | slow |
| 21 | granite-3.0-2b-instruct | -1 | TQ1_0 | q4_1 | q8_0 | slow |
| 22 | MiniCPM3-4B | -1 | IQ1_M | q8_0 | iq4_nl | slow |
| 23 | granite-4.0-h-1b | -1 | Q1_0 | q8_0 | q5_0 | medium |
| 24 | granite-4.0-1b | -1 | IQ3_S | q5_0 | q5_0 | medium |
| 25 | granite-4.2-3b | -1 | Q2_0 | q5_0 | q4_1 | slow |
| 26 | granite-4.0-1b | -1 | IQ3_S | q4_1 | iq4_nl | medium |
| 27 | SmolLM2-360M-Instruct | -1 | TQ1_0 | q4_0 | q4_1 | slow |
| 28 | Qwen3-1.7B | -1 | Q2_0 | q4_0 | q5_0 | slow |
| 29 | AI21-Jamba2-3B | -1 | Q2_K | f16 | q4_0 | slow |
| 30 | granite-4.0-h-350m | -1 | IQ2_XS | q4_0 | q4_1 | fast |
| 31 | granite-4.0-micro | -1 | F16 | q5_1 | q5_1 | slow |
| 32 | granite-3.0-2b-instruct | -1 | IQ3_S | f16 | iq4_nl | slow |
| 33 | Qwen3-4B-Instruct-2507 | -1 | IQ2_XXS | q8_0 | q5_0 | slow |
| 34 | granite-4.0-1b | -1 | Q4_K_S | q5_1 | q4_0 | slow |
| 35 | MiniCPM5-1B | -1 | Q5_1 | q5_0 | q5_1 | slow |
| 36 | phi-2 | -1 | IQ3_S | f16 | f16 | slow |
| 37 | SmolLM3-3B | -1 | Q2_0 | q8_0 | iq4_nl | slow |

_37 candidates run of 100,352; each one chance, the seed recorded in state._
