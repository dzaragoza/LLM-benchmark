# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 78 done candidates, top 3 (3 of 78)
- params median: **2.614 B**
- model_quant mode: **IQ3_M**
- k_quant mode: **q4_1**
- v_quant mode: **iq4_nl**
- high-score level time median: **10.3s**
- score median: **2**
- vulkan0 ram median: **2.89 GiB**

_the machine sweet-spot band, live as the pool fills_

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | k | v | vulkan0 ram | speed |
|---|---|---|---|---|---|---|---|
| 1 | gemma-2-2b-it | 3 | IQ3_M | q4_1 | iq4_nl | 1.57 | fast |
| 2 | Qwen3.5-0.8B | 2 | Q5_K_M | q5_1 | f16 | 2.89 | fast |
| 3 | granite-4.1-3b | 2 | IQ3_XS | q4_0 | q5_1 | 4.87 | fast |
| 4 | Qwen3-0.6B | 1 | Q5_1 | q8_0 | q4_0 | 2.27 | fast |
| 5 | MiniCPM-1B-sft | 1 | IQ4_XS | f16 | q5_0 | 1.01 | fast |
| 6 | gemma-3-1b-it | 1 | IQ3_M | q5_0 | f16 | 0.82 | fast |
| 7 | granite-3.3-2b-instruct | 1 | Q5_1 | q4_1 | q5_0 | 5.25 | fast |
| 8 | granite-3.0-2b-instruct | 1 | F16 | q8_0 | f16 | 5.02 | fast |
| 9 | SmolLM3-3B | 1 | Q3_K_M | q4_1 | q5_0 | 3.07 | fast |
| 10 | granite-4.0-h-micro | 1 | Q5_K_S | q4_0 | q4_0 | 5.45 | fast |
| 11 | Qwen3-4B-Instruct-2507 | 1 | Q5_K_S | q5_1 | q5_0 | 15.89 | medium |
| 12 | Phi-3-mini-128k-instruct | 0 | IQ3_S | q5_0 | iq4_nl | 16.72 | fast |
| 13 | SmolLM2-1.7B-Instruct | 0 | Q8_0 | q4_1 | q8_0 | 2.40 | fast |
| 14 | RWKV7-World-2.9B | 0 | Q8_0 | q4_1 | q5_0 | 2.98 | fast |
| 15 | Qwen2.5-3B-Instruct | 0 | Q5_0 | q4_0 | q4_0 | 2.44 | fast |
| 16 | Qwen2.5-3B-Instruct | 0 | Q3_K_S | q8_0 | q4_1 | 1.93 | fast |
| 17 | granite-3.2-2b-instruct | 0 | Q3_K_M | f16 | q8_0 | 9.01 | fast |
| 18 | granite-4.0-h-1b | 0 | Q4_K_M | iq4_nl | q5_0 | 4.43 | slow |
| 19 | granite-4.0-1b | 0 | Q5_K_M | q5_1 | q5_0 | 4.84 | slow |
| 20 | Qwen3-2B | -1 | Q4_K_M | f16 | q4_1 | 3.46 | slow |
| 21 | SmolLM2-360M-Instruct | -1 | IQ2_XXS | f16 | q4_1 | 0.42 | fast |
| 22 | MiniCPM5-1B | -1 | IQ4_NL | q4_1 | f16 | 2.64 | medium |
| 23 | granite-3.2-2b-instruct | -1 | Q5_K_M | q5_1 | q8_0 | 6.40 | slow |
| 24 | SmolLM3-3B | -1 | IQ3_XS | q4_1 | q5_1 | 2.96 | slow |
| 25 | granite-4.0-h-micro | -1 | Q3_K_S | q4_0 | q5_0 | 4.99 | slow |
| 26 | Qwen2.5-0.5B-Instruct | -1 | IQ2_XXS | q8_0 | iq4_nl | 0.51 | fast |
| 27 | MiniCPM-2B-sft | -1 | IQ2_M | q4_1 | f16 | 2.05 | slow |
| 28 | Qwen2.5-1.5B-Instruct | -1 | IQ4_NL | f16 | iq4_nl | 1.52 | slow |
| 29 | Qwen2.5-1.5B-Instruct | -1 | IQ3_M | q8_0 | f16 | 1.48 | slow |
| 30 | Qwen3.5-2B | -1 | IQ1_S | q5_0 | q5_1 | 2.06 | slow |
| 31 | MiniCPM3-4B | -1 | Q2_K | q5_0 | q4_0 | 9.28 | slow |
| 32 | Phi-3-mini-128k-instruct | -1 | Q2_K_S | f16 | q4_1 | 32.90 | slow |
| 33 | granite-3.0-2b-instruct | -1 | TQ1_0 | q4_1 | q8_0 | 0.75 | slow |
| 34 | MiniCPM3-4B | -1 | IQ1_M | q8_0 | iq4_nl | 11.48 | slow |
| 35 | granite-4.0-h-1b | -1 | Q1_0 | q8_0 | q5_0 | 4.89 | medium |
| 36 | granite-4.0-1b | -1 | IQ3_S | q5_0 | q5_0 | 4.33 | medium |
| 37 | granite-4.2-3b | -1 | Q2_0 | q5_0 | q4_1 | 4.49 | slow |
| 38 | granite-4.0-1b | -1 | IQ3_S | q4_1 | iq4_nl | 3.86 | medium |
| 39 | SmolLM2-360M-Instruct | -1 | TQ1_0 | q4_0 | q4_1 | 0.31 | slow |
| 40 | Qwen3-1.7B | -1 | Q2_0 | q4_0 | q5_0 | 2.06 | slow |
| 41 | AI21-Jamba2-3B | -1 | Q2_K | f16 | q4_0 | 1.56 | slow |
| 42 | granite-4.0-h-350m | -1 | IQ2_XS | q4_0 | q4_1 | 2.35 | fast |
| 43 | granite-4.0-micro | -1 | F16 | q5_1 | q5_1 | 10.28 | slow |
| 44 | granite-3.0-2b-instruct | -1 | IQ3_S | f16 | iq4_nl | 1.32 | slow |
| 45 | Qwen3-4B-Instruct-2507 | -1 | IQ2_XXS | q8_0 | q5_0 | 17.23 | slow |
| 46 | granite-4.0-1b | -1 | Q4_K_S | q5_1 | q4_0 | 4.35 | slow |
| 47 | MiniCPM5-1B | -1 | Q5_1 | q5_0 | q5_1 | 1.87 | slow |
| 48 | phi-2 | -1 | IQ3_S | f16 | f16 | 1.79 | slow |
| 49 | SmolLM3-3B | -1 | Q2_0 | q8_0 | iq4_nl | 2.91 | slow |
| 50 | gemma-2-2b-it | -1 | Q4_K_S | iq4_nl | f16 | 2.01 | slow |
| 51 | granite-4.0-h-micro | -1 | IQ3_XS | q4_0 | q4_1 | 4.82 | slow |
| 52 | MiniCPM-2B-sft | -1 | TQ2_0 | q5_0 | f16 | 1.95 | slow |
| 53 | Ministral-3-3B-Instruct-2512 | -1 | Q2_0 | q5_0 | q5_0 | 10.35 | slow |
| 54 | Phi-3-mini-128k-instruct | -1 | IQ1_M | f16 | iq4_nl | 31.86 | slow |
| 55 | Qwen3-0.6B | -1 | Q1_0 | q4_1 | q5_1 | 1.75 | slow |
| 56 | MiniCPM-1B-sft | -1 | IQ1_S | q4_0 | q4_1 | 0.47 | slow |
| 57 | granite-4.0-h-micro | -1 | IQ2_XXS | q4_0 | q5_0 | 4.49 | slow |
| 58 | MiniCPM3-4B | -1 | Q8_0 | q4_1 | iq4_nl | 11.38 | slow |
| 59 | SmolLM2-360M-Instruct | -1 | IQ1_M | iq4_nl | q8_0 | 0.34 | fast |
| 60 | phi-4-mini-instruct | -1 | IQ3_S | iq4_nl | q5_0 | 6.95 | slow |
| 61 | Qwen3-4B-Instruct-2507 | -1 | TQ2_0 | q5_1 | q8_0 | 17.81 | slow |
| 62 | Llama-3.2-3B-Instruct | -1 | IQ3_XS | q5_0 | q5_0 | 6.37 | slow |
| 63 | granite-4.2-3b | -1 | IQ3_XS | iq4_nl | q4_0 | 4.40 | slow |
| 64 | phi-1 | -1 | IQ3_M | iq4_nl | iq4_nl | 0.74 | slow |
| 65 | Ministral-3-3B-Instruct-2512 | -1 | IQ4_NL | f16 | f16 | 28.23 | slow |
| 66 | Qwen2.5-1.5B-Instruct | -1 | Q8_0 | q5_1 | q4_0 | 1.91 | slow |
| 67 | granite-3.2-2b-instruct | -1 | Q5_K_S | q8_0 | f16 | 9.48 | slow |
| 68 | Ministral-3-3B-Instruct-2512 | -1 | IQ3_XXS | q8_0 | q5_0 | 13.03 | slow |
| 69 | SmolLM3-3B | -1 | Q1_0 | f16 | q5_1 | 3.80 | slow |
| 70 | SmolLM2-1.7B-Instruct | -1 | TQ1_0 | q5_1 | q5_1 | 1.03 | slow |
| 71 | AI21-Jamba2-3B | -1 | Q8_0 | q5_0 | q5_1 | 3.43 | slow |
| 72 | granite-4.0-h-350m | -1 | IQ1_S | q4_0 | q4_0 | 2.27 | fast |
| 73 | granite-4.2-3b | -1 | Q8_0 | iq4_nl | iq4_nl | 6.37 | slow |
| 74 | Qwen3-1.7B | -1 | Q2_K_S | q4_0 | q5_0 | 2.13 | slow |
| 75 | Qwen3-4B-Instruct-2507 | -1 | IQ2_S | q5_0 | q8_0 | 17.39 | slow |
| 76 | Phi-3-mini-128k-instruct | -1 | Q5_K_S | q4_0 | q8_0 | 22.09 | slow |
| 77 | Qwen2.5-0.5B-Instruct | -1 | IQ2_M | q4_1 | iq4_nl | 0.48 | slow |
| 78 | RWKV7-World-2.9B | -1 | IQ3_S | q5_1 | iq4_nl | 1.46 | slow |

_78 candidates run of 100,352; each one chance, the seed recorded in state._
