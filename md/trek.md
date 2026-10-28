# trek.md - the trek ledger


## the score-time frontier (practitioner reporting)

the best score at a patience level (the high-score level's time);
the ram column is the holder's memory TIER - the dyadic cut
(1/2/4/8/16 GiB) its measured vulkan0 ram fits

| patience | best score | holder | at | ram |
|---|---|---|---|---|
| <= 1s | 3 | Qwen2.5-0.5B-Instruct Q2_K k=f16 v=q5_0 | 1s | g1 |
| <= 2s | 3 | Qwen2.5-0.5B-Instruct Q2_K k=f16 v=q5_0 | 1s | g1 |
| <= 4s | 3 | Qwen2.5-0.5B-Instruct Q2_K k=f16 v=q5_0 | 1s | g1 |
| <= 8s | 3 | Qwen2.5-0.5B-Instruct Q2_K k=f16 v=q5_0 | 1s | g1 |
| <= 16s | 3 | Qwen2.5-0.5B-Instruct Q2_K k=f16 v=q5_0 | 1s | g1 |
| <= 32s | 3 | Qwen2.5-0.5B-Instruct Q2_K k=f16 v=q5_0 | 1s | g1 |
| <= 64s | 3 | Qwen2.5-0.5B-Instruct Q2_K k=f16 v=q5_0 | 1s | g1 |
| <= 128s | 3 | Qwen2.5-0.5B-Instruct Q2_K k=f16 v=q5_0 | 1s | g1 |
| <= 256s | 3 | Qwen2.5-0.5B-Instruct Q2_K k=f16 v=q5_0 | 1s | g1 |

## the score-by-ram-budget table (practitioner reporting)

the best score whose MEASURED vulkan0 ram (model + kv + compute) fits
a budget; the patience column is the holder's time tier - how long
you wait per level at that memory size

| ram budget | best score | holder | patience |
|---|---|---|---|
| <= 1.0 GiB | 3 | Qwen2.5-0.5B-Instruct Q2_K k=f16 v=q5_0 | t1 |
| <= 2.0 GiB | 3 | Qwen2.5-0.5B-Instruct Q2_K k=f16 v=q5_0 | t1 |
| <= 4.0 GiB | 3 | Qwen2.5-0.5B-Instruct Q2_K k=f16 v=q5_0 | t1 |
| <= 8.0 GiB | 3 | Qwen2.5-0.5B-Instruct Q2_K k=f16 v=q5_0 | t1 |
| <= 16.0 GiB | 3 | Qwen2.5-0.5B-Instruct Q2_K k=f16 v=q5_0 | t1 |

_3871 candidates measured, 79 of 2,048 pairs swept; each pair one acquisition, the seed recorded in state._
