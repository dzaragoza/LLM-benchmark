# ei.md - the ei ledger

## the time-tier crowns

- t1 (<= 1s): **Qwen3.5-0.8B IQ3_S k=q4_0 v=q4_0, score 1 @ 1s**
- t2 (<= 2s): **gemma-3-1b-it Q3_K_S k=q8_0 v=q4_0, score 2 @ 2s**
- t4 (<= 4s): **granite-3.2-2b-instruct IQ4_NL k=q4_0 v=q5_0, score 1 @ 3s**
- t8 (<= 8s): **Mistral-Nemo-Instruct-2407 Q2_K k=q5_1 v=q4_1, score 2 @ 5s**
- t16 (<= 16s): **granite-3.2-2b-instruct IQ4_NL k=f16 v=f16, score 5 @ 8s**
- t32 (<= 32s): **granite-4.1-3b Q6_K k=q5_1 v=q4_0, score 7 @ 32s**
- t64 (<= 64s): **Falcon3-10B-Instruct Q2_K k=q5_0 v=q8_0, score 7 @ 48s**
- t128 (<= 128s): **Falcon3-10B-Instruct Q6_K k=q4_1 v=q5_1, score 14 @ 82s**
- the weakest tier: **t1** (the PoI target)

## the score-time frontier (practitioner reporting)

the best score at a patience level (the high-score level's time);
the ram column is the holder's memory TIER - the dyadic cut
(1/2/4/8/16 GiB) its measured vulkan0 ram fits

| patience | best score | holder | at | ram |
|---|---|---|---|---|
| <= 1s | 1 | Qwen3.5-0.8B IQ3_S k=q4_0 v=q4_0 | 1s | g2 |
| <= 2s | 2 | gemma-3-1b-it Q3_K_S k=q8_0 v=q4_0 | 2s | g1 |
| <= 4s | 2 | gemma-3-1b-it Q3_K_S k=q8_0 v=q4_0 | 2s | g1 |
| <= 8s | 2 | gemma-3-1b-it Q3_K_S k=q8_0 v=q4_0 | 2s | g1 |
| <= 16s | 5 | granite-3.2-2b-instruct IQ4_NL k=f16 v=f16 | 8s | g16 |
| <= 32s | 7 | granite-4.1-3b Q6_K k=q5_1 v=q4_0 | 32s | g8 |
| <= 64s | 7 | granite-4.1-3b Q6_K k=q5_1 v=q4_0 | 32s | g8 |
| <= 128s | 14 | Falcon3-10B-Instruct Q6_K k=q4_1 v=q5_1 | 82s | g16 |
| <= 256s | 14 | Falcon3-10B-Instruct Q6_K k=q4_1 v=q5_1 | 82s | g16 |

## the score-by-ram-budget table (practitioner reporting)

the best score whose MEASURED vulkan0 ram (model + kv + compute) fits
a budget; the patience column is the holder's time tier - how long
you wait per level at that memory size

| ram budget | best score | holder | patience |
|---|---|---|---|
| <= 1.0 GiB | 2 | gemma-3-1b-it Q3_K_S k=q8_0 v=q4_0 | t2 |
| <= 2.0 GiB | 2 | gemma-3-1b-it Q3_K_S k=q8_0 v=q4_0 | t2 |
| <= 4.0 GiB | 2 | gemma-3-1b-it Q3_K_S k=q8_0 v=q4_0 | t2 |
| <= 8.0 GiB | 7 | Falcon3-10B-Instruct Q2_K k=q5_0 v=q8_0 | t64 |
| <= 16.0 GiB | 14 | Falcon3-10B-Instruct Q6_K k=q4_1 v=q5_1 | t128 |

_1310 candidates measured, 108 of 2,048 pairs swept; each pair one acquisition, the seed recorded in state._
