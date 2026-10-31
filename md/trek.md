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
| <= 64s | 4 | Qwen2.5-0.5B-Instruct Q8_0 k=q8_0 v=q8_0 | 0.75 |
| <= 128s | 4 | Qwen2.5-0.5B-Instruct Q8_0 k=q8_0 v=q8_0 | 0.75 |

## the walker (the current life)

life 4: movement 4 of 7 in the epoch; high 4, best at Qwen2.5-0.5B-Instruct Q8_0

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
| t1 | 4 | 4 | 0 | yes * |
| t2 | 4 | 6 | 0.000275 | yes |
| t4 | 4 | 8 | 0.000553 | yes |
| t8 | 4 | 10 | 0.000835 | yes |
| t16 | 4 | 10 | 0.00112 | yes |
| t32 | 4 | 12 | 0.00141 | yes |
| t64 | 4 | 12 | 0.0017 | yes |
| t128 | 4 | 12 | 0.002 | yes |

quorum: unmet; not blocked

_99 candidates measured (131 exam levels recorded; a re-run at a bigger budget is new evidence) of 15 pairs x 3 x 3 kv = 135 total, 73.3%); the histories are the single source of truth, the tables derive on every ledger write._
