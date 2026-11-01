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
| <= 128s | 13 | gemma-3-12b-it Q4_0 k=q8_0 v=q4_0 | 10.09 |

## the walker (the current life)

life 3: movement 8 of 20 in the epoch; life score 0 (the spawn/teleport baseline); epoch start at Qwen2.5-0.5B-Instruct Q8_0 (the next teleport's target)

## the radio (the stop condition)

the per-tier certification: each live cell's PER-TIER threat
(the score it achieves within the tier's seconds) priced by
the pools (the started-climb pool D, the genesis pool G),
summed (the union bound); a tier certifies when the 95%
upper confidence bound sum_p + 2*SE < 0.05 AND the quorum
(>= 2 cells pooled) AND a real champion (not the floor);
the SE is the pools' sampling error; '-' = not modelable
(a pool empty: keep searching)

| tier | champion | live cells | sum p | 2-sig upper | certified |
|---|---|---|---|---|---|
| t1 | 4 | 9 | 0 | 0 | yes |
| t2 | 4 | 11 | 0.119 | 0.153 | no |
| t4 | 4 | 12 | 0.279 | 0.33 | no |
| t8 | 4 | 12 | 0.471 | 0.537 | no |
| t16 | 4 | 13 | 0.7 | 0.78 | no |
| t32 | 4 | 14 | 1.06 | 1.16 | no |
| t64 | 8 | 17 | 0.618 | 0.688 | no |
| t128 | 13 | 17 | 0.182 | 0.219 | no |

quorum: unmet; not blocked

## the progress (evaluated cells, tier-weighted)

total: 54 cells x 8 time tiers = 432 possible evaluations

| tier (weight) | evaluated cells | contribution |
|---|---|---|
| t1 (1) | 1 | 1 |
| t2 (2) | 0 | 0 |
| t4 (3) | 0 | 0 |
| t8 (4) | 1 | 4 |
| t16 (5) | 2 | 10 |
| t32 (6) | 3 | 18 |
| t64 (7) | 0 | 0 |
| t128 (8) | 38 | 304 |

progress: 337 of 432 (78.0%); 9 cells not evaluated at any tier

_468 candidates measured (905 exam levels recorded; a re-run at a bigger budget is new evidence) of 54 pairs x 3 x 3 kv = 486 total, 96.3%); the histories are the single source of truth, the tables derive on every ledger write._
