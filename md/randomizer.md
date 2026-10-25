# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 65 done candidates, top 3 (3 of 65)
- params median: **0.8734 B**
- model_quant mode: **Q5_K_M**
- k_quant mode: **q5_1**
- v_quant mode: **f16**
- high-score level time median: **0.9s**
- score median: **2**

_the machine sweet-spot band, live as the pool fills_

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | k | v | speed |
|---|---|---|---|---|---|---|
| 1 | Qwen3.5-0.8B | 2 | Q5_K_M | q5_1 | f16 | fast |
| 2 | granite-4.1-3b | 2 | IQ3_XS | q4_0 | q5_1 | fast |
| 3 | Qwen3-0.6B | 1 | Q5_1 | q8_0 | q4_0 | fast |
| 4 | gemma-3-1b-it | 1 | IQ3_M | q5_0 | f16 | fast |
| 5 | granite-3.3-2b-instruct | 1 | Q5_1 | q4_1 | q5_0 | fast |
| 6 | granite-3.0-2b-instruct | 1 | F16 | q8_0 | f16 | fast |
| 7 | granite-4.0-h-micro | 1 | Q5_K_S | q4_0 | q4_0 | fast |
| 8 | Qwen3-4B-Instruct-2507 | 1 | Q5_K_S | q5_1 | q5_0 | medium |
| 9 | Phi-3-mini-128k-instruct | 0 | IQ3_S | q5_0 | iq4_nl | fast |
| 10 | SmolLM2-1.7B-Instruct | 0 | Q8_0 | q4_1 | q8_0 | fast |
| 11 | RWKV7-World-2.9B | 0 | Q8_0 | q4_1 | q5_0 | fast |
| 12 | Qwen2.5-3B-Instruct | 0 | Q5_0 | q4_0 | q4_0 | fast |
| 13 | granite-3.2-2b-instruct | 0 | Q3_K_M | f16 | q8_0 | fast |
| 14 | Qwen3-2B | -1 | Q4_K_M | f16 | q4_1 | slow |
| 15 | SmolLM2-360M-Instruct | -1 | IQ2_XXS | f16 | q4_1 | fast |
| 16 | MiniCPM5-1B | -1 | IQ4_NL | q4_1 | f16 | medium |
| 17 | granite-3.2-2b-instruct | -1 | Q5_K_M | q5_1 | q8_0 | slow |
| 18 | SmolLM3-3B | -1 | IQ3_XS | q4_1 | q5_1 | slow |
| 19 | granite-4.0-h-micro | -1 | Q3_K_S | q4_0 | q5_0 | slow |
| 20 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | q8_0 | iq4_nl | fast |
| 21 | MiniCPM-2B-sft | -1 | IQ2_M | q4_1 | f16 | slow |
| 22 | Qwen2.5-1.5B-Instruct | -1 | IQ4_NL | f16 | iq4_nl | slow |
| 23 | Qwen2.5-1.5B-Instruct | -1 | IQ3_M | q8_0 | f16 | slow |
| 24 | Qwen3.5-2B | -1 | IQ1_S | q5_0 | q5_1 | slow |
| 25 | MiniCPM3-4B | -1 | Q2_K | q5_0 | q4_0 | slow |
| 26 | Phi-3-mini-128k-instruct | -1 | Q2_K_S | f16 | q4_1 | slow |
| 27 | granite-3.0-2b-instruct | -1 | TQ1_0 | q4_1 | q8_0 | slow |
| 28 | MiniCPM3-4B | -1 | IQ1_M | q8_0 | iq4_nl | slow |
| 29 | granite-4.0-h-1b | -1 | Q1_0 | q8_0 | q5_0 | medium |
| 30 | granite-4.0-1b | -1 | IQ3_S | q5_0 | q5_0 | medium |
| 31 | granite-4.2-3b | -1 | Q2_0 | q5_0 | q4_1 | slow |
| 32 | granite-4.0-1b | -1 | IQ3_S | q4_1 | iq4_nl | medium |
| 33 | SmolLM2-360M-Instruct | -1 | TQ1_0 | q4_0 | q4_1 | slow |
| 34 | Qwen3-1.7B | -1 | Q2_0 | q4_0 | q5_0 | slow |
| 35 | AI21-Jamba2-3B | -1 | Q2_K | f16 | q4_0 | slow |
| 36 | granite-4.0-h-350m | -1 | IQ2_XS | q4_0 | q4_1 | fast |
| 37 | granite-4.0-micro | -1 | F16 | q5_1 | q5_1 | slow |
| 38 | granite-3.0-2b-instruct | -1 | IQ3_S | f16 | iq4_nl | slow |
| 39 | Qwen3-4B-Instruct-2507 | -1 | IQ2_XXS | q8_0 | q5_0 | slow |
| 40 | granite-4.0-1b | -1 | Q4_K_S | q5_1 | q4_0 | slow |
| 41 | MiniCPM5-1B | -1 | Q5_1 | q5_0 | q5_1 | slow |
| 42 | phi-2 | -1 | IQ3_S | f16 | f16 | slow |
| 43 | SmolLM3-3B | -1 | Q2_0 | q8_0 | iq4_nl | slow |
| 44 | gemma-2-2b-it | -1 | Q4_K_S | iq4_nl | f16 | slow |
| 45 | granite-4.0-h-micro | -1 | IQ3_XS | q4_0 | q4_1 | slow |
| 46 | MiniCPM-2B-sft | -1 | TQ2_0 | q5_0 | f16 | slow |
| 47 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | q5_0 | q5_0 | slow |
| 48 | Phi-3-mini-128k-instruct | -1 | IQ1_M | f16 | iq4_nl | slow |
| 49 | Qwen3-0.6B | -1 | Q1_0 | q4_1 | q5_1 | slow |
| 50 | MiniCPM-1B-sft | -1 | IQ1_S | q4_0 | q4_1 | slow |
| 51 | granite-4.0-h-micro | -1 | IQ2_XXS | q4_0 | q5_0 | slow |
| 52 | MiniCPM3-4B | -1 | Q8_0 | q4_1 | iq4_nl | slow |
| 53 | SmolLM2-360M-Instruct | -1 | IQ1_M | iq4_nl | q8_0 | fast |
| 54 | phi-4-mini-instruct | -1 | IQ3_S | iq4_nl | q5_0 | slow |
| 55 | Qwen3-4B-Instruct-2507 | -1 | TQ2_0 | q5_1 | q8_0 | slow |
| 56 | Llama-3.2-3B-Instruct | -1 | IQ3_XS | q5_0 | q5_0 | slow |
| 57 | granite-4.2-3b | -1 | IQ3_XS | iq4_nl | q4_0 | slow |
| 58 | phi-1 | -1 | IQ3_M | iq4_nl | iq4_nl | slow |
| 59 | Ministral-3-3B-Instruct-2512 | -1 | IQ4_NL | f16 | f16 | slow |
| 60 | Qwen2.5-1.5B-Instruct | -1 | Q8_0 | q5_1 | q4_0 | slow |
| 61 | granite-3.2-2b-instruct | -1 | Q5_K_S | q8_0 | f16 | slow |
| 62 | Ministral-3-3B-Instruct-2512 | -1 | IQ3_XXS | q8_0 | q5_0 | slow |
| 63 | SmolLM3-3B | -1 | Q1_0 | f16 | q5_1 | slow |
| 64 | SmolLM2-1.7B-Instruct | -1 | TQ1_0 | q5_1 | q5_1 | slow |
| 65 | AI21-Jamba2-3B | -1 | Q8_0 | q5_0 | q5_1 | slow |

_65 candidates run of 100,352; each one chance, the seed recorded in state._
