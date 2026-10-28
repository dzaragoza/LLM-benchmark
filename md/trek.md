# trek.md - the trek ledger


## the score-time frontier (practitioner reporting)

the best score at a patience level (the high-score level's time);
the ram column is the holder's memory TIER - the dyadic cut
(1/2/4/8/16 GiB) its measured vulkan0 ram fits

| patience | best score | holder | at | ram |
|---|---|---|---|---|
| <= 1s | 2 | Qwen3.5-0.8B IQ3_XS k=iq4_nl v=q4_1 | 1s | g2 |
| <= 2s | 2 | Qwen3.5-0.8B IQ3_XS k=iq4_nl v=q4_1 | 1s | g2 |
| <= 4s | 2 | Qwen3.5-0.8B IQ3_XS k=iq4_nl v=q4_1 | 1s | g2 |
| <= 8s | 2 | Qwen3.5-0.8B IQ3_XS k=iq4_nl v=q4_1 | 1s | g2 |
| <= 16s | 2 | Qwen3.5-0.8B IQ3_XS k=iq4_nl v=q4_1 | 1s | g2 |
| <= 32s | 2 | Qwen3.5-0.8B IQ3_XS k=iq4_nl v=q4_1 | 1s | g2 |
| <= 64s | 2 | Qwen3.5-0.8B IQ3_XS k=iq4_nl v=q4_1 | 1s | g2 |
| <= 128s | 2 | Qwen3.5-0.8B IQ3_XS k=iq4_nl v=q4_1 | 1s | g2 |
| <= 256s | 2 | Qwen3.5-0.8B IQ3_XS k=iq4_nl v=q4_1 | 1s | g2 |

## the score-by-ram-budget table (practitioner reporting)

the best score whose MEASURED vulkan0 ram (model + kv + compute) fits
a budget; the patience column is the holder's time tier - how long
you wait per level at that memory size

| ram budget | best score | holder | patience |
|---|---|---|---|
| <= 1.0 GiB | 1 | gemma-3-1b-it IQ3_XS k=q5_1 v=q4_0 | t1 |
| <= 2.0 GiB | 2 | Qwen3.5-0.8B IQ3_XS k=iq4_nl v=q4_1 | t1 |
| <= 4.0 GiB | 2 | Qwen3.5-0.8B IQ3_XS k=iq4_nl v=q4_1 | t1 |
| <= 8.0 GiB | 2 | Qwen3.5-0.8B IQ3_XS k=iq4_nl v=q4_1 | t1 |
| <= 16.0 GiB | 2 | Qwen3.5-0.8B IQ3_XS k=iq4_nl v=q4_1 | t1 |

_5000 candidates measured, 150 of 2,048 pairs swept; each pair one acquisition, the seed recorded in state._
