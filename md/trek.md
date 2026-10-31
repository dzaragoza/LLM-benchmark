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
| <= 8s | 0 | Yi-1.5-9B-Chat Q3_K_M k=q5_0 v=q4_1 | 4.14 |
| <= 16s | 1 | granite-3.3-8b-instruct Q3_K_S k=q8_0 v=q8_0 | 13.46 |
| <= 32s | 4 | Yi-1.5-9B-Chat Q3_K_M k=f16 v=iq4_nl | 4.26 |
| <= 64s | 7 | granite-3.3-8b-instruct Q3_K_L k=f16 v=q4_1 | 7.52 |
| <= 128s | 10 | Qwen3-8B Q3_K_M k=q4_0 v=f16 | 7.33 |

## the walker (the current life)

life 1: movement 16 of 78 in the epoch; high 10, best at Qwen3-8B Q3_K_M

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
| t1 | -1 | 938 | 0 | no (floor champion) |
| t2 | -1 | 947 | 69.3 | no (floor champion) |
| t4 | -1 | 949 | 134 | no (floor champion) |
| t8 | 0 | 952 | 141 | no |
| t16 | 1 | 953 | 142 | no |
| t32 | 4 | 956 | 31.1 | no |
| t64 | 7 | 956 | 12 | no |
| t128 | 10 | 956 | 3.02 | no |

quorum: unmet; not blocked

_1,078 candidates measured (1,624 exam levels recorded; a re-run at a bigger budget is new evidence) of 960 pairs x 7 x 7 kv = 47,040 total, 2.3%); the histories are the single source of truth, the tables derive on every ledger write._
