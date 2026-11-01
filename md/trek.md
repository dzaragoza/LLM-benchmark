# trek.md - the trek ledger (v3: derived from the exam histories)

## the score-patience frontier (practitioner reporting)

the best score achievable at a patience level (the per-level
time limit), derived from the shared exam histories; the vram
column is the tier's holder's vulkan0 memory (model + kv +
compute, the candidate's own launch) - what you need to run
the tier's champion

| patience | best score | holder | vram (GiB) |
|---|---|---|---|
| <= 1s | 4 | Qwen2.5-0.5B-Instruct Q8_0 k=q8_0 v=q8_0 | 0.75 |
| <= 2s | 4 | Qwen2.5-0.5B-Instruct Q8_0 k=q8_0 v=q8_0 | 0.75 |
| <= 4s | 4 | Qwen2.5-0.5B-Instruct Q8_0 k=q8_0 v=q8_0 | 0.75 |
| <= 8s | 4 | Qwen2.5-0.5B-Instruct Q8_0 k=q8_0 v=q8_0 | 0.75 |
| <= 16s | 4 | Qwen2.5-0.5B-Instruct Q8_0 k=q8_0 v=q8_0 | 0.75 |
| <= 32s | 4 | Qwen2.5-0.5B-Instruct Q8_0 k=q8_0 v=q8_0 | 0.75 |
| <= 64s | 8 | Mistral-Nemo-Instruct-2407 Q4_0 k=f16 v=f16 | 14.78 |
| <= 128s | 11 | Mistral-Nemo-Instruct-2407 Q4_0 k=f16 v=f16 | 14.78 |

## the walker (the current life)

life 6: movement 3 of 20 in the epoch; life score -1 (the spawn/teleport baseline); epoch start at Mistral-Nemo-Instruct-2407 Q4_0 (the next teleport's target)

## the radio (the stop condition)

the per-tier certification: each live cell's PER-TIER threat
(the score it achieves within the tier's seconds) priced by
the pools (the started-climb pool D, the genesis pool G),
summed (the union bound); a tier certifies when the 95%
upper confidence bound sum_p + 2*SE < 0.05 AND the quorum
(>= 2 cells pooled) AND a real champion (not the floor);
the SE is the pools' sampling error; '-' = not modelable
(a pool empty: keep searching)

<<<<<<< HEAD
| tier | champion | live cells | sum p | 2-sig upper | certified |
|---|---|---|---|---|---|
| t1 | 4 | 10 | 0 | 0 | yes |
| t2 | 4 | 12 | 0.0419 | 0.0626 | no |
| t4 | 4 | 13 | 0.117 | 0.152 | no |
| t8 | 4 | 14 | 0.226 | 0.274 | no |
| t16 | 4 | 17 | 0.373 | 0.433 | no |
| t32 | 4 | 19 | 0.652 | 0.728 | no |
| t64 | 8 | 21 | 0.226 | 0.267 | no |
| t128 | 11 | 21 | 0.153 | 0.186 | no |

quorum: unmet; not blocked

## the progress (evaluated cells, tier-weighted)

total: 54 cells x 8 time tiers = 432 possible evaluations

| tier (weight) | evaluated cells | contribution |
|---|---|---|
| t1 (1) | 1 | 1 |
| t2 (2) | 0 | 0 |
| t4 (3) | 1 | 3 |
| t8 (4) | 3 | 12 |
| t16 (5) | 2 | 10 |
| t32 (6) | 2 | 12 |
| t64 (7) | 0 | 0 |
| t128 (8) | 35 | 280 |

progress: 318 of 432 (73.6%); 10 cells not evaluated at any tier

_459 candidates measured (806 exam levels recorded; a re-run at a bigger budget is new evidence) of 54 pairs x 3 x 3 kv = 486 total, 94.4%); the histories are the single source of truth, the tables derive on every ledger write._
=======
| tier | champion | live cells | sum p | certified |
|---|---|---|---|---|
| t1 | 4 | 10 | 0 | yes * |
| t2 | 4 | 12 | 0.0418 | no |
| t4 | 4 | 13 | 0.117 | no |
| t8 | 4 | 14 | 0.226 | no |
| t16 | 4 | 17 | 0.372 | no |
| t32 | 4 | 19 | 0.65 | no |
| t64 | 8 | 20 | 0.226 | no |
| t128 | 11 | 20 | 0.153 | no |

quorum: unmet; not blocked

_459 candidates measured (809 exam levels recorded; a re-run at a bigger budget is new evidence) of 54 pairs x 3 x 3 kv = 486 total, 94.4%); the histories are the single source of truth, the tables derive on every ledger write._
>>>>>>> 3bfed73d7 (benchmark artifacts 2026-11-01 19:27 (addendum 78 auto-commit): state, results, per-turn dumps, mem sidecars, ladder dumps)
