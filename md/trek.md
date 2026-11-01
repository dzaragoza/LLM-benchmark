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

life 6: movement 1 of 20 in the epoch; life score -1 (the spawn/teleport baseline); epoch start at gemma-3-12b-it Q4_0 (the next teleport's target)

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
| t1 | 4 | 10 | 0 | 0 | yes |
| t2 | 4 | 12 | 0.0433 | 0.0644 | no |
| t4 | 4 | 13 | 0.121 | 0.156 | no |
| t8 | 4 | 14 | 0.234 | 0.283 | no |
| t16 | 4 | 18 | 0.388 | 0.45 | no |
| t32 | 4 | 20 | 0.68 | 0.758 | no |
| t64 | 8 | 22 | 0.235 | 0.278 | no |
| t128 | 11 | 22 | 0.159 | 0.193 | no |

quorum: unmet; not blocked

## the progress (closed cells per tier)

the cells closed at each time tier (every candidate settled
with a verdict within the tier's seconds) of 54
total cells

| tier | closed cells | total | progress |
|---|---|---|---|
| t1 | 10 | 54 | 18.5% |
| t2 | 10 | 54 | 18.5% |
| t4 | 10 | 54 | 18.5% |
| t8 | 13 | 54 | 24.1% |
| t16 | 15 | 54 | 27.8% |
| t32 | 17 | 54 | 31.5% |
| t64 | 17 | 54 | 31.5% |
| t128 | 41 | 54 | 75.9% |

_459 candidates measured (776 exam levels recorded; a re-run at a bigger budget is new evidence) of 54 pairs x 3 x 3 kv = 486 total, 94.4%); the histories are the single source of truth, the tables derive on every ledger write._
