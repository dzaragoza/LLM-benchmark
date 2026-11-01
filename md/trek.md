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
| <= 64s | 6 | granite-3.3-8b-instruct Q8_0 k=q8_0 v=q8_0 | 14.74 |
| <= 128s | 8 | Ministral-3-3B-Instruct-2512 Q8_0 k=f16 v=q4_0 | 14.91 |

## the walker (the current life)

life 3: movement 15 of 20 in the epoch; life score -1 (the spawn/teleport baseline); epoch start at Ministral-3-3B-Instruct-2512 Q4_0 (the next teleport's target)

## the radio (the stop condition's progress)

the per-tier certification: the live cells' summed probability
of beating the tier's champion (the union bound); a tier is
certified when the sum < 0.01 AND the quorum (>= 2 cells
pooled) AND a real champion (not the floor); the * marks the
eager tier (tier 1 - its certification rests on the
support-cap assumption); '-' = not modelable (a pool empty:
keep searching)

| tier | champion | live cells | sum p | certified |
|---|---|---|---|---|
| t1 | 4 | 11 | 0 | yes * |
| t2 | 4 | 13 | 0.0121 | yes |
| t4 | 4 | 15 | 0.0476 | no |
| t8 | 4 | 19 | 0.11 | no |
| t16 | 4 | 21 | 0.204 | no |
| t32 | 4 | 23 | 0.41 | no |
| t64 | 6 | 25 | 0.429 | no |
| t128 | 8 | 27 | 0.401 | no |

quorum: unmet; not blocked

_450 candidates measured (689 exam levels recorded; a re-run at a bigger budget is new evidence) of 54 pairs x 3 x 3 kv = 486 total, 92.6%); the histories are the single source of truth, the tables derive on every ledger write._
