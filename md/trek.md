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

life 1: movement 2 of 20 in the epoch; high -1, best at Llama-3.1-8B-Instruct Q4_0

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
| t1 | 4 | 23 | 0 | yes * |
| t2 | 4 | 26 | 0.0131 | yes |
| t4 | 4 | 28 | 0.0448 | no |
| t8 | 4 | 28 | 0.098 | no |
| t16 | 4 | 30 | 0.174 | no |
| t32 | 4 | 34 | 0.275 | no |
| t64 | 5 | 36 | 0.167 | no |
| t128 | 5 | 38 | 0.242 | no |

quorum: unmet; not blocked

_279 candidates measured (471 exam levels recorded; a re-run at a bigger budget is new evidence) of 54 pairs x 3 x 3 kv = 486 total, 57.4%); the histories are the single source of truth, the tables derive on every ledger write._
