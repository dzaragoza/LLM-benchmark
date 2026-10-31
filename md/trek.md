# trek.md - the trek ledger (v3: derived from the exam histories)

## the score-patience frontier (practitioner reporting)

the best score achievable at a patience level (the per-level
time limit), derived from the shared exam histories; the vram
column is the tier's holder's vulkan0 memory (model + kv +
compute, the candidate's own launch) - what you need to run
the tier's champion

| patience | best score | holder | vram (GiB) |
|---|---|---|---|
| <= 1s | 0 | gemma-3-1b-it F16 k=f16 v=f16 | 2.09 |
| <= 2s | 0 | gemma-3-1b-it F16 k=f16 v=f16 | 2.09 |
| <= 4s | 2 | gemma-3-1b-it F16 k=q4_0 v=f16 | 2.04 |
| <= 8s | 2 | gemma-3-1b-it F16 k=q4_0 v=f16 | 2.04 |
| <= 16s | 2 | gemma-3-1b-it F16 k=q4_0 v=f16 | 2.04 |
| <= 32s | 2 | gemma-3-1b-it F16 k=q4_0 v=f16 | 2.04 |
| <= 64s | 2 | gemma-3-1b-it F16 k=q4_0 v=f16 | 2.04 |
| <= 128s | 2 | gemma-3-1b-it F16 k=q4_0 v=f16 | 2.04 |

## the walker (the current life)

life 4: movement 0 of 7 in the epoch; high 2, best at gemma-3-1b-it F16

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
| t1 | 0 | 7 | 0 | yes * |
| t2 | 0 | 8 | 0.0472 | no |
| t4 | 2 | 10 | 0.000277 | yes |
| t8 | 2 | 12 | 0.000891 | yes |
| t16 | 2 | 12 | 0.0019 | yes |
| t32 | 2 | 14 | 0.00331 | yes |
| t64 | 2 | 14 | 0.00519 | yes |
| t128 | 2 | 14 | 0.00752 | yes |

quorum: unmet; not blocked

_72 candidates measured (81 exam levels recorded; a re-run at a bigger budget is new evidence) of 15 pairs x 3 x 3 kv = 135 total, 53.3%); the histories are the single source of truth, the tables derive on every ledger write._
