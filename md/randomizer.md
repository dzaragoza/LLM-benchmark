# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 49 done candidates, top 2 (2 of 49)
- params median: **2.0773 B**
- model_quant mode: **IQ3_XS**
- k_quant mode: **q4_0**
- v_quant mode: **q5_1**
- high-score level time median: **5.6s**
- score median: **1.5**

_the machine sweet-spot band, live as the pool fills_

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | k | v | speed |
|---|---|---|---|---|---|---|
| 1 | granite-4.1-3b | 2 | IQ3_XS | q4_0 | q5_1 | fast |
| 2 | Qwen3-0.6B | 1 | Q5_1 | q8_0 | q4_0 | fast |
| 3 | gemma-3-1b-it | 1 | IQ3_M | q5_0 | f16 | fast |
| 4 | granite-3.3-2b-instruct | 1 | Q5_1 | q4_1 | q5_0 | fast |
| 5 | granite-3.0-2b-instruct | 1 | F16 | q8_0 | f16 | fast |
| 6 | granite-4.0-h-micro | 1 | Q5_K_S | q4_0 | q4_0 | fast |
| 7 | Qwen3-4B-Instruct-2507 | 1 | Q5_K_S | q5_1 | q5_0 | medium |
| 8 | Phi-3-mini-128k-instruct | 0 | IQ3_S | q5_0 | iq4_nl | fast |
| 9 | Qwen2.5-3B-Instruct | 0 | Q5_0 | q4_0 | q4_0 | fast |
| 10 | granite-3.2-2b-instruct | 0 | Q3_K_M | f16 | q8_0 | fast |
| 11 | Qwen3-2B | -1 | Q4_K_M | f16 | q4_1 | slow |
| 12 | SmolLM2-360M-Instruct | -1 | IQ2_XXS | f16 | q4_1 | fast |
| 13 | MiniCPM5-1B | -1 | IQ4_NL | q4_1 | f16 | medium |
| 14 | granite-3.2-2b-instruct | -1 | Q5_K_M | q5_1 | q8_0 | slow |
| 15 | SmolLM3-3B | -1 | IQ3_XS | q4_1 | q5_1 | slow |
| 16 | granite-4.0-h-micro | -1 | Q3_K_S | q4_0 | q5_0 | slow |
| 17 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | q8_0 | iq4_nl | fast |
| 18 | MiniCPM-2B-sft | -1 | IQ2_M | q4_1 | f16 | slow |
| 19 | Qwen2.5-1.5B-Instruct | -1 | IQ4_NL | f16 | iq4_nl | slow |
| 20 | Qwen2.5-1.5B-Instruct | -1 | IQ3_M | q8_0 | f16 | slow |
| 21 | Qwen3.5-2B | -1 | IQ1_S | q5_0 | q5_1 | slow |
| 22 | MiniCPM3-4B | -1 | Q2_K | q5_0 | q4_0 | slow |
| 23 | Phi-3-mini-128k-instruct | -1 | Q2_K_S | f16 | q4_1 | slow |
| 24 | granite-3.0-2b-instruct | -1 | TQ1_0 | q4_1 | q8_0 | slow |
| 25 | MiniCPM3-4B | -1 | IQ1_M | q8_0 | iq4_nl | slow |
| 26 | granite-4.0-h-1b | -1 | Q1_0 | q8_0 | q5_0 | medium |
| 27 | granite-4.0-1b | -1 | IQ3_S | q5_0 | q5_0 | medium |
| 28 | granite-4.2-3b | -1 | Q2_0 | q5_0 | q4_1 | slow |
| 29 | granite-4.0-1b | -1 | IQ3_S | q4_1 | iq4_nl | medium |
| 30 | SmolLM2-360M-Instruct | -1 | TQ1_0 | q4_0 | q4_1 | slow |
| 31 | Qwen3-1.7B | -1 | Q2_0 | q4_0 | q5_0 | slow |
| 32 | AI21-Jamba2-3B | -1 | Q2_K | f16 | q4_0 | slow |
| 33 | granite-4.0-h-350m | -1 | IQ2_XS | q4_0 | q4_1 | fast |
| 34 | granite-4.0-micro | -1 | F16 | q5_1 | q5_1 | slow |
| 35 | granite-3.0-2b-instruct | -1 | IQ3_S | f16 | iq4_nl | slow |
| 36 | Qwen3-4B-Instruct-2507 | -1 | IQ2_XXS | q8_0 | q5_0 | slow |
| 37 | granite-4.0-1b | -1 | Q4_K_S | q5_1 | q4_0 | slow |
| 38 | MiniCPM5-1B | -1 | Q5_1 | q5_0 | q5_1 | slow |
| 39 | phi-2 | -1 | IQ3_S | f16 | f16 | slow |
| 40 | SmolLM3-3B | -1 | Q2_0 | q8_0 | iq4_nl | slow |
| 41 | gemma-2-2b-it | -1 | Q4_K_S | iq4_nl | f16 | slow |
| 42 | granite-4.0-h-micro | -1 | IQ3_XS | q4_0 | q4_1 | slow |
| 43 | MiniCPM-2B-sft | -1 | TQ2_0 | q5_0 | f16 | slow |
| 44 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | q5_0 | q5_0 | slow |
| 45 | Phi-3-mini-128k-instruct | -1 | IQ1_M | f16 | iq4_nl | slow |
| 46 | Qwen3-0.6B | -1 | Q1_0 | q4_1 | q5_1 | slow |
| 47 | MiniCPM-1B-sft | -1 | IQ1_S | q4_0 | q4_1 | slow |
| 48 | granite-4.0-h-micro | -1 | IQ2_XXS | q4_0 | q5_0 | slow |
| 49 | MiniCPM3-4B | -1 | Q8_0 | q4_1 | iq4_nl | slow |

_49 candidates run of 100,352; each one chance, the seed recorded in state._
