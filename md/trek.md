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
| <= 64s | 5 | gemma-4-e4b-it Q4_0 k=f16 v=f16 | 4.95 |
| <= 128s | 5 | gemma-4-e4b-it Q8_0 k=f16 v=f16 | 6.96 |

## the walker (the current life)

life 2: movement 3 of 12 in the epoch; high 0, best at gemma-3-1b-it Q4_0

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
| t1 | 4 | 9 | 0 | yes * |
| t2 | 4 | 15 | 0.0092 | yes |
| t4 | 4 | 17 | 0.0421 | no |
| t8 | 4 | 19 | 0.103 | no |
| t16 | 4 | 20 | 0.197 | no |
| t32 | 4 | 21 | 0.326 | no |
| t64 | 5 | 21 | 0.217 | no |
| t128 | 5 | 21 | 0.321 | no |

quorum: unmet; not blocked

_184 candidates measured (327 exam levels recorded; a re-run at a bigger budget is new evidence) of 30 pairs x 3 x 3 kv = 270 total, 68.1%); the histories are the single source of truth, the tables derive on every ledger write._
