# randomizer.md - the randomizer ledger

## the top 5% dashboard

- measured: 4 done candidates, top 1 (1 of 4)
- params median: **3.821 B**
- model_quant mode: **Q4_1**
- k_quant mode: **q4_0**
- v_quant mode: **q8_0**
- high-score level time median: **11.1s**
- score median: **-1**
- vulkan0 ram median: **2.87 GiB**
- context median: **4,096**

_the machine sweet-spot band, live as the pool fills_

Every candidate gets ONE chance (no replacement). Rank:
highest score, tiebreak by time. Speed: the candidate's
whole run - fast <= 32s, medium <= 64s, slow <= 128s.

| rank | model | high score | quant @high | k | v | vulkan0 ram | ctx | speed |
|---|---|---|---|---|---|---|---|---|
| 1 | Phi-3-mini-4k-instruct | 0 | Q4_1 | q4_0 | q8_0 | 2.87 | 4,096 | fast |
| 2 | granite-3.3-2b-instruct | 0 | Q5_1 | q5_0 | f16 | 8.68 | 131,072 | fast |
| 3 | Phi-3-mini-128k-instruct | -1 | IQ2_S | iq4_nl | iq4_nl | 1.71 | 113,408 | slow |
| 4 | Llama-3.2-1B-Instruct | -1 | Q5_1 | f16 | f16 | 5.07 | 131,072 | slow |

_4 candidates run of 100,352; each one chance, the seed recorded in state._
