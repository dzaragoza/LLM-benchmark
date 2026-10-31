# trek.md - the trek ledger (v3: derived from the exam histories)

## the score-patience frontier (practitioner reporting)

the best score achievable at a patience level (the per-level
time limit), derived from the shared exam histories; the vram
column is the tier's holder's vulkan0 memory (model + kv +
compute, the candidate's own launch) - what you need to run
the tier's champion

| patience | best score | holder | vram (GiB) |
|---|---|---|---|
| <= 1s | - | (nothing measured yet) | - |
| <= 2s | - | (nothing measured yet) | - |
| <= 4s | - | (nothing measured yet) | - |
| <= 8s | - | (nothing measured yet) | - |
| <= 16s | 1 | granite-3.3-8b-instruct Q3_K_S k=q8_0 v=q8_0 | 13.46 |
| <= 32s | 1 | granite-3.3-8b-instruct Q3_K_S k=q8_0 v=f16 | 13.46 |
| <= 64s | 6 | Qwen3-8B Q3_K_S k=q4_1 v=q4_0 | 5.07 |
| <= 128s | 8 | Qwen3-8B Q3_K_S k=q4_1 v=q4_0 | 5.07 |

## the walker (the current life)

life 1: movement 1 of 78 in the epoch; high 8, best at Qwen3-8B Q3_K_S

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
| t1 | -1 | 940 | 0 | no (floor champion) |
| t2 | -1 | 950 | 25.1 | no (floor champion) |
| t4 | -1 | 952 | 49.6 | no (floor champion) |
| t8 | -1 | 955 | 73.5 | no (floor champion) |
| t16 | 1 | 957 | 30 | no |
| t32 | 1 | 959 | 37.9 | no |
| t64 | 6 | 959 | 0.736 | no |
| t128 | 8 | 959 | 0.257 | no |

quorum: unmet; not blocked

_980 candidates measured (1,077 exam levels recorded; a re-run at a bigger budget is new evidence) of 960 pairs x 7 x 7 kv = 47,040 total, 2.1%); the histories are the single source of truth, the tables derive on every ledger write._
