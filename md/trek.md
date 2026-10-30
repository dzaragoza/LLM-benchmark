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
| <= 16s | 1 | granite-3.3-8b-instruct Q2_K k=iq4_nl v=q8_0 | - |
| <= 32s | 1 | granite-3.3-8b-instruct Q2_K k=iq4_nl v=q8_0 | - |
| <= 64s | 1 | granite-3.3-8b-instruct Q2_K k=iq4_nl v=q8_0 | - |
| <= 128s | 1 | granite-3.3-8b-instruct Q2_K k=iq4_nl v=q8_0 | - |

## the walker (the current life)

life 1: movement 44 of 78 in the epoch; high 0, best at Qwen3-8B Q2_K

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
| t1 | -1 | 941 | 0 | no (floor champion) |
| t2 | -1 | 949 | 7.61 | no (floor champion) |
| t4 | -1 | 952 | 15.2 | no (floor champion) |
| t8 | -1 | 956 | 22.7 | no (floor champion) |
| t16 | 1 | 957 | 0.0647 | no |
| t32 | 1 | 958 | 0.117 | no |
| t64 | 1 | 960 | 0.181 | no |
| t128 | 1 | 960 | 0.257 | no |

quorum: unmet; not blocked

_931 candidates measured (of 960 pairs x 7 x 7 kv = 47,040 total, 2.0%); the histories are the single source of truth, the tables derive on every ledger write._
