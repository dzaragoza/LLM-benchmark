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
| <= 16s | - | (nothing measured yet) | - |
| <= 32s | - | (nothing measured yet) | - |
| <= 64s | - | (nothing measured yet) | - |
| <= 128s | - | (nothing measured yet) | - |

## the walker (the current life)

life 3: movement 1 of 7 in the epoch; high -1, best at gemma-4-e4b-it Q8_0

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
| t1 | -1 | 8 | 0 | no (floor champion) |
| t2 | -1 | 11 | 0 | no (floor champion) |
| t4 | -1 | 12 | 0 | no (floor champion) |
| t8 | -1 | 13 | 0 | no (floor champion) |
| t16 | -1 | 15 | 0 | no (floor champion) |
| t32 | -1 | 15 | 0 | no (floor champion) |
| t64 | -1 | 15 | 0 | no (floor champion) |
| t128 | -1 | 15 | 0 | no (floor champion) |

quorum: unmet; not blocked

_63 candidates measured (63 exam levels recorded; a re-run at a bigger budget is new evidence) of 15 pairs x 3 x 3 kv = 135 total, 46.7%); the histories are the single source of truth, the tables derive on every ledger write._
