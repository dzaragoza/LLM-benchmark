# trek.md - the trek ledger (v2: derived from the exam histories)

## the score-patience frontier (practitioner reporting)

the best score achievable at a patience level (the per-level
time limit), derived from the shared exam histories

| patience | best score | holder |
|---|---|---|
| <= 1s | 2 | Llama-3.2-1B-Instruct IQ3_XXS k=q5_1 v=q5_0 |
| <= 2s | 2 | Llama-3.2-1B-Instruct IQ3_XXS k=q5_1 v=q5_0 |
| <= 4s | 2 | Llama-3.2-1B-Instruct IQ3_XXS k=q5_1 v=q5_0 |
| <= 8s | 2 | Llama-3.2-1B-Instruct IQ3_XS k=q8_0 v=q5_0 |
| <= 16s | 2 | Llama-3.2-1B-Instruct IQ3_XS k=q8_0 v=q5_0 |
| <= 32s | 2 | Llama-3.2-1B-Instruct IQ3_XS k=q8_0 v=q5_0 |
| <= 64s | 2 | Llama-3.2-1B-Instruct IQ3_XS k=q8_0 v=q5_0 |
| <= 128s | 2 | Llama-3.2-1B-Instruct IQ3_XS k=q8_0 v=q5_0 |

## the walkers (the budget ladder's progress)

| budget | position | movements | high | best cell |
|---|---|---|---|---|
| 1s | [9, 13] | 95 | 1 | gemma-3-1b-it Q2_K |
| 2s | [7, 13] | 95 | 1 | gemma-3-1b-it Q2_K |
| 4s | [7, 13] | 95 | 2 | Llama-3.2-1B-Instruct IQ3_XXS |
| 8s | [9, 10] | 95 | 2 | Llama-3.2-1B-Instruct IQ3_XXS |
| 16s | [9, 10] | 95 | 2 | Llama-3.2-1B-Instruct IQ3_XXS |
| 32s | [9, 10] | 2 | 2 | Llama-3.2-1B-Instruct IQ3_XXS |

_3,099 candidates measured (of 2048 pairs x 49 kv = 100,352 total); the histories are the single source of truth, the tables derive on every ledger write._
