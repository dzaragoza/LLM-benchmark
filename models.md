# models.md — The Model Registry

Every model the 256k screen has touched, in one place: the passes,
the fails, and the candidates with predicted values. Updated with
every probe; the lab notebook carries the full narrative.

RAM = cold whole-stack machine cost (MemAvailable delta) at depth
262,144. w/s = the scored-rung worst turn. Predictions use the
registered ceiling predictor (model-selection.md rule 2):
`cost = file(rung) + KV_eff(262144) x kvquant + 1.10 GiB`.

RAM OVER CEILING IS NOT A FAIL REASON (author ruling, session 36
addendum 3): the 4.96 GiB ceiling is always an estimate - a measured
RAM over ceiling is a NEW CEILING WITH A PASS, recorded as a
measurement; the fail reason is whatever the gates say (FWE, timeout).
Predicted-over at screen time still rejects (REJECTED, size reason).

TYPE RULE (author ruling, session 35 addendum 18): only INSTRUCT
models are suited to this benchmark - both gates are
instruction-shaped (the speed gate is a live conversation with a
following reader; FWE is an instruction-following extraction task).
One type per model in the whole document: the instruct tune; base
(pretrained) variants are rejected on type, not re-evaluated.

ONE-MODEL-ONE-TABLE, with the author's exception (addendum 20): a
model appears at most once per table, in exactly one table - EXCEPT
the CANDIDATES table, where a model may appear MULTIPLE TIMES, once
per settings configuration (a candidate is a model+configuration
pair, not a model).

---

## PASS (both gates at 262,144)

| model name | model quant | k quant | v quant | model size GiB | RAM | w/s | notes |
|---|---|---|---|---|---|---|---|
| Qwen3.5-0.8B | Q8_0 | f16 | f16 | 0.86 | 4.96 GiB | 9.3 | THE CHAMPION; sets the 4.96 GiB ceiling; trained window 262,144; speed PASS zero stalls, FWE 3/3 at 261,888 |
| Qwen3.5-2B | Q4_K_M | q5_0 | q5_0 | 1.22 | 3.48 GiB | 9.5 | the RAM champion (half the champion's cost); speed PASS 15.2 t/s worst turn, FWE 3/3; the quant-raise probe (Q8_0+q8_0) FAILED - 5.22 GiB over ceiling, FWE 0/3 (session 36 addendum 1); this Q4_K_M config is the 2B's ceiling config |
| AI21-Jamba2-3B | Q8_0 | f16 | f16 | 3.17 | 4.42 GiB | 6.1 | PASS on its first probe (session 36 addendum 1): 89% of ceiling, speed PASS 6.08 w/s worst turn (reader never waited), FWE 3/3 at 261,888; the FIRST NON-TRANSFORMER PASS in the study (hybrid mamba-attention, 2 full-attention layers carried the retrieval); predictor 4.40 GiB - off by 0.02 (0.5%) |

## FAIL

| model name | model quant | k quant | v quant | model size GiB | RAM | w/s | reason for failure |
|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | Q8_0 | q8_0 | q8_0 | 1.93 | 5.22 GiB | 8.2 | FWE 0/3 at 261,888 (speed PASS 8.18 w/s); the 5.22 GiB is a NEW-CEILING measurement, not the fail reason (author ruling, addendum 3: the ceiling is always an estimate); the quant-raise is closed (session 36 addendum 1) |
| Qwen3.5-4B | Q2_K | q4_0 | q4_0 | 1.82 | 5.81 GiB | 7.3 | TimeoutError at +94m into the FWE phase after a speed PASS at 262,144 (7.3 w/s); the 5.81 GiB is a NEW-CEILING measurement, not the fail reason (author ruling, addendum 3); analysis in session 36 addendum 3; the family closes at 4B for this machine (Q2_K is its floor config) |
| RWKV7-World-2.9B | Q8_0 | n/a | n/a | 3.03 | 3.58 GiB | 13.1 | FWE degeneration 0/3 at 261,888 - single-character repetition output, no extraction attempted; RAM and speed PASS (3.58 GiB, 13.11 w/s - the fastest depth-scorer in the study); pure recurrence cannot carry FWE at 256k (session 36 addendum 1) |

## CANDIDATES (predicted values)

(empty, session 36 addendum 5: the Jamba Q6_K row removed by
author ruling - a cheaper config of a passing family adds nothing;
the pool is settled for the report)

| model name | model quant (predicted) | k quant (predicted) | v quant (predicted) | model size GiB (predicted) | RAM (predicted) | w/s (predicted) | prediction notes |
|---|---|---|---|---|---|---|---|


## TOURNAMENT (the ranking instrument - session 36 addenda 10-20)

Five seeded climbs per participant up the dyadic ladder (4096..262144),
upstream RULER FWE parameters (k=3, alpha 2.0), seed = climb number,
early stop at the first non-perfect cell. Rank = mode of the climbs,
median fallback (marked). The speed gate is assumed passed (measured
at 256k for all participants), falsified when a ranking step needs it.

| rank | model | config (model q, k, v) | falls (climb 1-5) | passes/rung | rank statistic | notes |
|---|---|---|---|---|---|---|
| 1 (32,768) | Qwen3.5-2B | (Q4_K_M, q5_0, q5_0) | 65536, 4096, 32768, 262144, 16384 | [4 4 3 2 1 1 0] | median-fallback | THE TOURNAMENT CHAMPION (32,768 tok); the deepest climber - climb 4 is the only climb in the field to reach 262,144 (falling 1/3), and the most volatile (climb 2 fell at 4096); highest variance, highest ceiling |
| 2 (8,192) | AI21-Jamba2-3B | (Q8_0, f16, f16) | 8192, 4096, 4096, 65536, 8192 | [3 1 1 1 0 0 0] | median-fallback | second at 8,192 tok; climb 4 reached 65,536 (2/3 partial) - the hybrid's retrieval held mid-deepths on two of five seeds |
| 3 (4,096) | Qwen3.5-0.8B | (Q8_0, f16, f16) | 4096, 4096, 4096, 8192, 32768 | [2 1 1 0 0 0 0] | mode | THE FORMER CHAMPION, third at 4,096 tok; the 256k PASS (seed 1024, FWE 3/3 at 261,888) is SEED-CONDITIONAL - seeds 1-3 fell at 4,096 (2/3 partials, deep-scanning misses, not refusals); climb 5 reached 32,768 |

THE COMEBACK ROUND (session 36, addendum 35 - the author's run, 23 min):

| rank | model | config (model q, k, v) | falls (climb 1-5) | passes/rung | rank statistic | notes |
|---|---|---|---|---|---|---|
| 4 (16,384) | Llama-3.2-1B-Instruct | (Q8_0, q4_0, q4_0) | 16384, 4096, 4096, 32768, 32768 | [3 3 2 0 0 0 0] | median-fallback | THE COMEBACK CHAMPION (16,384 tok) - the only newcomer past the floor; climb 1 reached 16,384 and climb 4/5 reached 32,768; two 0/3 refusal-shaped misses ("I can't fulfill this request.") on seed 1 |
| 5 (4,096) | AI21-Jamba-Reasoning-3B | (Q8_0, f16, f16) | 8192, 4096, 16384, 4096, 4096 | [2 1 0 0 0 0 0] | mode | 4,096 tok; the reasoning tune climbs no deeper than its PASS sibling (8,192) - the thinking shape neither helps nor hurts FWE retrieval |
| 6 (4,096) | MiniCPM5-2B | (Q8_0, f16, q4_0) | 8192, 4096, 4096, 4096, 4096 | [1 0 0 0 0 0 0] | mode | 4,096 tok - the dead-on-ceiling entry did NOT buy depth; predicted deepest (32,768+), measured the floor: prediction FAILED |
| 7 (4,096) | MiniCPM5-1B | (Q8_0, f16, f16) | 4096 x5 | [0 0 0 0 0 0 0] | mode | 4,096 tok; zero holds anywhere - the smallest model in the field |
| 8 (4,096) | RWKV7-Goose-World3-2.9B-HF | (Q8_0, n/a, n/a) | 4096 x5 | [0 0 0 0 0 0 0] | mode | 4,096 tok; the structural hypothesis CONFIRMED at five seeds (all-4096 as predicted) - but the miss shape CHANGED: no single-character degeneration this time, instead "Sure, I understand. Please provide the text" confabulation (0/3) and partial scans (2/3, 1/3) - pure recurrence fails FWE, but HOW it fails is prompt-dependent |

ROUNDS 6-7 (session 36 addendum 39 - the author's run, 43 min; the
tournament is resumable so only seeds 6-7 ran):

| rank | model | config (model q, k, v) | falls (climb 1-7) | passes/rung | rank statistic | notes |
|---|---|---|---|---|---|---|
| 1 (32,768) | Qwen3.5-2B | (Q4_K_M, q5_0, q5_0) | 65536, 4096, 32768, 262144, 16384, 4096, 32768 | [5 5 4 2 1 1 0] | median-fallback | STANDS AS CHAMPION (32,768 tok, unchanged at n=7); the deepest and most volatile - climb 4 reached 262,144 in round 1 (falling 1/3) and climb 6 fell AT 262,144 (0/1) |
| 2 (8,192) | AI21-Jamba2-3B | (Q8_0, f16, f16) | 8192, 4096, 4096, 65536, 8192, 4096, 8192 | [4 1 1 1 0 0 0] | median-fallback | STANDS at 8,192 tok; seeds 6-7 fell at 4,096/8,192, consistent with its n=5 pattern |
| 3 (4,096) | Qwen3.5-0.8B | (Q8_0, f16, f16) | 4096, 4096, 4096, 8192, 32768, 262144, 32768 | [4 3 3 1 1 1 0] | mode | THE HEADLINE: climb 6 (seed 6) HELD EVERY RUNG TO 262,144, falling AT the top rung (0/1 at 262,144) - the former champion is one cell from a full hold; its mode stays 4,096 (4 of 7) but its ceiling is the field's second-highest |
| 4 (4,096) | Llama-3.2-1B-Instruct | (Q8_0, q4_0, q4_0) | 16384, 4096, 4096, 32768, 32768, 8192, 4096 | [4 3 2 0 0 0 0] | mode | DROPS FROM 16,384 (median, n=5) TO 4,096 (mode, n=7) - the comeback champion's climb-6/7 falls at 8,192/4,096 collapse its median; at n=7 its rank is no better than the floor-clearers |
| 5 (4,096) | AI21-Jamba-Reasoning-3B | (Q8_0, f16, f16) | 8192, 4096, 16384, 4096, 4096, 4096, 4096 | [2 1 0 0 0 0 0] | mode | 4,096 tok; clears the floor but only just |
| 6 (4,096) | MiniCPM5-2B | (Q8_0, f16, q4_0) | 8192, 4096, 4096, 4096, 4096, 8192, 4096 | [2 0 0 0 0 0 0] | mode | 4,096 tok; clears the floor |
| 7 (4,096) | RWKV7-Goose-World3-2.9B-HF | (Q8_0, n/a, n/a) | 4096, 4096, 4096, 4096, 4096, 8192, 4096 | [1 0 0 0 0 0 0] | mode | 4,096 tok; climb 6 (seed 6) HELD 8,192 - the first crack in the all-4096 structural claim: pure recurrence is not deterministically floor-bound, seed 6's word draws were retrievable |
| 8 (4,096) | MiniCPM5-1B | (Q8_0, f16, f16) | 4096 x7 | [0 0 0 0 0 0 0] | mode | 4,096 tok; zero holds in seven climbs (the disqualification this round produced was later reverted - addendum 44, mechanism retired session 37) |

The disqualification verdicts this round produced were later reverted (addendum 44); the disqualified mechanism is retired entirely (session 37, addendum 2 - a replacement policy is pending).

THE n=15 ROUND (session 36 addendum 46 - the author's run, 5h12m; seeds 8-15
fresh via resume, gemma's first 15; bars at n=15: reliable 10/15,
conservative 12/15):

| rank | model | config (model q, k, v) | falls (climb 1-15) | passes/rung | reliable (1s) | conservative (2s) | ceiling | rank statistic | notes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Qwen3.5-2B | (Q4_K_M, q5_0, q5_0) | 65536, 4096, 32768, 262144, 16384, 4096, 32768, 32768, 32768, 8192, 65536, 8192, 32768, 32768, top | [13 11 10 4 2 2 1] | 16,384 | 4,096 | 262,144 | mode | CO-CHAMPION (32,768, now a true MODE - 5x) and the field's only deep certification: reliable 16,384 (10/15), conservative 4,096 (13/15); climb 15 TOPPED OUT (the field's first full hold) |
| 2 | Qwen3.5-0.8B | (Q8_0, f16, f16) | 4096, 4096, 4096, 8192, 32768, 262144, 32768, 262144, 262144, 4096, 16384, top, 8192, 262144, 32768 | [11 9 8 5 5 5 1] | 4,096 | 0 | 262,144 | median-fallback | CO-CHAMPION (32,768, median): four climbs at 262,144-or-top - the ceiling beast; but its certified floor is only 4,096 (11/15): spectacular and untrustworthy |
| 3 | AI21-Jamba2-3B | (Q8_0, f16, f16) | 8192, 4096, 4096, 65536, 8192, 4096, 8192, 16384, 16384, 4096, top, 16384, 4096, 16384, 65536 | [10 7 3 3 1 1 1] | 4,096 | 0 | 262,144 | mode | DROPS from 8,192 to 4,096 (mode) - its n=5 8,192 was seed luck; climb 11 topped out; reliable only at the floor |
| 4 | Llama-3.2-1B-Instruct | (Q8_0, q4_0, q4_0) | 16384, 4096, 4096, 32768, 32768, 8192, 4096 + 8x 4096 | [4 3 2 0 0 0 0] | 0 | 0 | 32,768 | mode | fades further at n=15 - no certification anywhere |
| 5 | AI21-Jamba-Reasoning-3B | (Q8_0, f16, f16) | see state | [7 1 0 0 0 0 0] | 0 | 0 | 16,384 | mode | 7/15 at the floor - closer to reliable than its sibling was, but nothing above 8,192 |
| 6 | gemma-3-1b-it | (Q8_0, q4_0, q4_0) | see state | [1 1 0 0 0 0 0] | 0 | 0 | 16,384 | mode | the newcomer BARELY clears the floor: one climb (seed 2) held to 16,384, fourteen fell at 4,096; the single-kv-head shape is the field's weakest FWE retriever |
| 7 | RWKV7-Goose-World3-2.9B-HF | (Q8_0, n/a, n/a) | see state | [4 0 0 0 0 0 0] | 0 | 0 | 8,192 | mode | 4/15 at the floor but NOTHING above - recurrence is confirmed floor-adjacent; the seed-6 8,192 hold was an outlier |
| 8 | MiniCPM5-2B | (Q8_0, f16, q4_0) | see state | [3 0 0 0 0 0 0] | 0 | 0 | 8,192 | mode | 3/15 at the floor, nothing above |
| 9 | MiniCPM5-1B | (Q8_0, f16, f16) | 4096 x7 (n=7, seeds 8-21 pending) | [0 0 0 0 0 0 0] | 0 | 0 | 4,096 | mode | re-admitted (addendum 44); zero holds in 7 climbs so far |

THE n=21 ROUND (session 37 addendum 5 - the author's run, 5h03m,
21:50-02:53, seeds 16-21 fresh via resume; bars at n=21: reliable
13/21, conservative 16/21; collected under the OLD 3/3 criterion -
the run predated the 1/3 ruling, so this table is the LOWER-BOUND
picture; the addendum-4 re-score revises it under 1/3):

| rank | model | config (model q, k, v) | passes/rung | reliable (1s) | conservative (2s) | ceiling | rank | rank statistic | w/s @ reliable | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Qwen3.5-0.8B | (Q8_0, f16, f16) | [17 14 12 8 8 8 2] | 8,192 | 4,096 | 262,144 | 262,144 | mode | 34.85 w/s | SOLE CHAMPION at n=21 (262,144, mode 2x + median-deep tail): six climbs at 262,144-or-top, two full holds (seeds 12, 20); its reliable depth climbs from 4,096 to 8,192 (14/21) - the spectacular model is now the trustworthy one too |
| 2 | Qwen3.5-2B | (Q4_K_M, q5_0, q5_0) | [16 14 11 5 3 3 1] | 8,192 | 4,096 | 262,144 | 32,768 | mode | 27.79 w/s | the n=15 co-champion keeps the true mode (32,768) but loses the deep certification: reliable DROPS from 16,384 to 8,192 (14/21), conservative stays 4,096 (16/21); seeds 16-21 added two more 4,096 falls (climbs 16, 18, 20) |
| 3 | AI21-Jamba2-3B | (Q8_0, f16, f16) | [15 12 5 5 3 3 3] | 4,096 | 0 | 262,144 | 16,384 | mode | 6.84 w/s | the only family whose mode ROSE (4,096 -> 16,384, 4x): seeds 16-21 added a 16,384-heavy tail (16,384 x3, top x2, 4096) - the hybrid recovers depth with more samples; reliable stays 4,096, conservative 0 (12/21 short of 16/21) |
| 4 | Llama-3.2-1B-Instruct | (Q8_0, q4_0, q4_0) | [6 5 4 2 0 0 0] | 0 | 0 | 65,536 | 4,096 | mode | n/a | fades to pure floor - seeds 16-21 are 4,096 x4 + 65,536 x2; its n=5 16,384 was seed luck, confirmed dead at n=21 |
| 5 | AI21-Jamba-Reasoning-3B | (Q8_0, f16, f16) | [10 1 0 0 0 0 0] | 0 | 0 | 16,384 | 4,096 | mode | n/a | 10/21 at the floor, nothing above 8,192 - the floor-heavy sibling shape is stable |
| 6 | gemma-3-1b-it | (Q8_0, q4_0, q4_0) | [2 1 0 0 0 0 0] | 0 | 0 | 16,384 | 4,096 | mode | n/a | 2/21 at the floor - the single-kv-head shape stays the field's weakest FWE retriever |
| 7 | RWKV7-Goose-World3-2.9B-HF | (Q8_0, n/a, n/a) | [7 0 0 0 0 0 0] | 0 | 0 | 8,192 | 4,096 | mode | n/a | 7/21 at the floor, nothing above - the addendum-39 8,192 was an outlier, recurrence is floor-adjacent |
| 8 | MiniCPM5-2B | (Q8_0, f16, q4_0) | [3 0 0 0 0 0 0] | 0 | 0 | 8,192 | 4,096 | mode | n/a | 3/21 at the floor, nothing above |
| 9 | MiniCPM5-1B | (Q8_0, f16, f16) | [0 0 0 0 0 0 0] | 0 | 0 | 4,096 | 4,096 | mode | n/a | 0/21 - seeds 8-21 confirmed: zero holds in twenty-one climbs under 3/3; the re-score decides its fate under 1/3 |

n=21 GRADE (the addendum-45 questions, 3/3 criterion):
1. RELIABILITY BY CONTEXT: at n=21 two families certify RELIABLE
   (1 sigma): 0.8B at 8,192 (14/21), 2B at 8,192 (14/21); Jamba2 at
   4,096 (15/21). CONSERVATIVE (2 sigma): 0.8B and 2B at 4,096
   (17/21, 16/21). 16k+ is EMPTY of certification at n=21 - the
   deepest certified rung under 1 sigma is 8,192.
2. FIELD SIZE: the certified map needs TWO families (0.8B and 2B
   cover 4k-8k both sigma levels); the author's 8-family guess held
   the study but 7 of 9 families certify nothing.
3. LINEAGE: the Qwen3.5 lineage takes both certified rungs; the two
   MiniCPM variants and both Jambas show architecture (hybrid
   attention/recurrence) beats pure recurrence for FWE retrieval.
4. PREDICTOR CALIBRATION: gemma's entry prediction (4,096-16,384)
   was PARTIAL - it hit 16,384 as ceiling but never as mode or
   certification; the 0.8B's n=15 "spectacular and untrustworthy"
   called its n=21 promotion correctly.
5. SEED VARIANCE: the 0.8B's climb-to-climb spread is the field's
   widest (4,096 to top); the 2B's mode is stable 32,768 across
   n=7/15/21 - mode convergence happened for the champions.
6. ARCHITECTURE: pure recurrence (RWKV) holds only at the floor
   (7/21); hybrid (Jamba) recovers depth with samples; full
   attention + wide training window (Qwen3.5) dominates.
7. MISS SHAPES: every fall was a partial (addendum 26) - the 1/3
   criterion change re-scores those holds (addendum 4).
8. INSTRUMENT COST: 5h03m for 6 seeds x 9 families (~50 min/seed
   across the field) + the first reliable-depth w/s medians (0.8B
   34.85, 2B 27.79, Jamba2 6.84 w/s at 4,096-8,192).
9. PREDICTOR FALSIFICATION: none of the addendum-43 pre-registrations
   survived intact: the 2B's conservative 4-8k HIT (4,096), the 0.8B
   reliable-cell borderline called WRONG (it certified 8,192), gemma
   partial.
10. THE RECOMMENDATION TABLE (n=21, 3/3): 4k -> 0.8B (conservative
    4,096, 34.85 w/s); 8k -> 0.8B (reliable 8,192); 16k+ -> EMPTY -
    the certification phase (session 36 addendum 50) fills it.

## THE PRACTITIONER TABLE (session 37 - the certify controller answers)

The deliverable: per context rung, ONE model + config + quality level
that solves it well. Quality levels: silver = reliable (1 sigma Wilson
lower bound >= 0.5), gold = confident (2 sigma). w/s is NOT measured in
the benchmark anymore (addendum 15 - the RAM-ceiling assumption: a
config under the ceiling has the bandwidth for 5 w/s); historical w/s
figures are old-protocol records.

| rung (tokens) | model | config (model q, k, v) | quality | cells used | evidence |
|---|---|---|---|---|---|
| 4,096 | Qwen3.5-0.8B | (Q8_0, f16, f16) | gold (conservative 4,096, 17/21 at 1s) | n=21 tournament | session 36 addendum 42 |
| 8,192 | Qwen3.5-0.8B | (Q8_0, f16, f16) | silver (reliable 8,192, 14/21 at 1s) | n=21 tournament | session 36 addendum 42 |
| 16,384 | AI21-Jamba2-3B | (Q8_0, f16, f16) | silver (accept 11/11, 1s lo 0.917) | 3 inherited + 8 fresh cells (runs 9-21 never measured) | certify run 2026-10-03, addendum 17 |
| 32,768 | AI21-Jamba2-3B | (Q8_0, f16, f16) | silver (accept 11/11, 1s lo 0.917) | 3 inherited + 8 fresh cells | certify run 2026-10-03, rung log 13:00 |
| 65,536 | AI21-Jamba2-3B | (Q8_0, f16, f16) | silver (accept 11/11, 1s lo 0.917) | 3 inherited + 8 fresh cells | certify run 2026-10-03, rung log 13:38 |
| 131,072 | AI21-Jamba2-3B | (Q8_0, f16, f16) | silver (accept 10/11, 1s lo 0.785) | 3 inherited + 8 fresh cells (1 MISS at run 2) | certify run 2026-10-03, rung log 15:05 |
| 262,144 | AI21-Jamba2-3B | (Q8_0, f16, f16) | silver (accept 11/11, 1s lo 0.917) | 3 inherited + 8 fresh cells | certify run 2026-10-03, rung log 16:39-20:14 |
| 524,288+ | EMPTY | - | - | - | the next rungs to certify (cheapest-first) |

NOTE on the 16k answer (addendum 17): Jamba2 - the hybrid whose n=21
mode ROSE to 16,384 - certifies the rung at 11/11 with ZERO failures;
the sequential controller spent 8 fresh cells total (runs 1-8) and
skipped the other 8 families (the 21x9 worst case would have been 189
cells; the sequential design saved ~95% of the compute). The one
interrupted w/s trial (addendum 15's removal mid-flight) recorded
7.2 w/s at 16,384 before the ruling - a PASS and a bonus record, not
a certification input.

The domination rule is retired (session 37, addendum 2); a replacement policy is pending from the author.

NOBODY beat the bar (32,768, the first tournament's rank). The overall
field ranking stands: Qwen3.5-2B (32,768) > Jamba2-3B (8,192) >
Qwen3.5-0.8B (4,096) > Llama-3.2-1B (16,384*). NOTE: the Llama's
16,384 ranks it ABOVE the former champion on depth - the comeback
champion displaces two PASS models on the ladder.

UPDATE (certify run, 2026-10-03, rung log 13:00-20:14): Jamba2-3B beat
the bar and then some - it certified 32,768, 65,536, 131,072 AND
262,144 at 1 sigma in one sequential run (11/11, 11/11, 10/11, 11/11;
the single 131,072 MISS was the only fresh-cell failure of the run).
The certified-depth field ranking is now: Jamba2-3B (262,144) >
Qwen3.5-2B (8,192) > Qwen3.5-0.8B (8,192). Jamba2's reliable w/s was
measured at its former 4,096 reliable depth (6.84 w/s); its speed at
262,144 is unmeasured.

FINDINGS (session 36 addendum 26): nobody topped out (0/5 full holds
all three); every fall is a PARTIAL (2/3 or 1/3), never 0/3 - the
session-35 "poles only" finding is superseded (n=1 artifact); seed
variance at k=3 dwarfs depth effects - who passes depends more on the
seed's word draws than on the depth. The comeback round (Llama-3.2-1B,
MiniCPM5-2B, Jamba-Reasoning-3B, RWKV7-2.9B - addenda 16-18 entries)
now has a bar to beat: 32,768.

The disqualified mechanism (floor rule addendum 38, domination rule addendum 44) is RETIRED (session 37, addendum 2): no model is disqualified by tournament data; a replacement policy is pending from the author and will be registered when given.

## REJECTED

Strict reason list (author ruling, addendum 21, extended addendum 23):
no research paper | no model small enough (q2, q4, q4) > ceiling |
training window < 256k | thinking cannot be disabled | other. A model
is rejected on the FIRST reason that binds in the fair-chance order:
if even the floor config (Q2_K + K/V q4_0/q4_0) predicts RAM above the
4.96 GiB ceiling, the size binds; if the RAM fits but the trained
window is under 262,144 (no rope scaling), the window binds; thinking
tunes whose reasoning cannot be turned off close as thinking cannot
be disabled; everything else is other. BASE variants of an
already-instruct model are not recorded (author ruling, addendum 23):
the type rule implies their rejection - the instruct tune is the
family's one entry.

| model name | rejection reason | notes |
|---|---|---|
| Qwen3.5-9B | no model small enough (q2, q4, q4) > ceiling | best config Q2_K + q4_0/q4_0 = 7.05 GiB predicted; the family closes at 9B |
| gemma-4-e2b-it | training window < 256k | trained window 131,072, config.json verified (addendum 25): max_position_embeddings in text_config (the multimodal wrapper), rope_scaling absent |
| mistralai/Ministral-3-3B-Instruct-2512 | no model small enough (q2, q4, q4) > ceiling | KV 104 KiB/token f16 (26 layers x 8 kv heads x 128 head_dim) -> ~7.3 GiB q4_0 KV at 262k, over the ceiling before weights; the declared 262,144 window is also YaRN rope-scaled from an original 16,384 (params.json llama_4_scaling, factor 16) - closed by the no-rope-scaling rule; first-party GGUF exists (Q4_K_M 2.00 GiB), the earlier 'repo does not exist' was a stale-name probe, corrected addendum 24 |
| Qwen2.5-1.5B-Instruct | training window < 256k | window 32,768, config.json verified (addendum 25), rope_scaling absent; the RAM would fit (1.97 GiB q4_0 KV at 262k) - the window is the wall; v4.3 score 20,992 @ Q8_0 |
| Qwen3-1.7B | no model small enough (q2, q4, q4) > ceiling | KV 112 KiB/token -> q4_0 KV alone ~7.9 GiB > 4.96; window 40,960 and FWE broken at 40,704 besides |
| Qwen3-4B | no model small enough (q2, q4, q4) > ceiling | KV 144 KiB/token -> ~10.1 GiB q4_0 KV; window 40,960 besides |
| phi-4-mini-instruct | no model small enough (q2, q4, q4) > ceiling | KV 128 KiB/token -> ~9.0 GiB q4_0 KV; window 131,072; the deepest non-Qwen3.5 score (44,032 @ Q4_K_M) is 6x short |
| Phi-3.5-mini-instruct | no model small enough (q2, q4, q4) > ceiling | KV 384 KiB/token -> ~27 GiB q4_0 KV; FWE zero at Q4_K_M |
| Phi-3-mini-4k-instruct | no model small enough (q2, q4, q4) > ceiling | KV 384 KiB/token -> ~27 GiB q4_0 KV; window 4,096 |
| phi-1 | training window < 256k | window 2,048, config.json verified (addendum 25), rope_scaling absent; base/code model (type rule) - far under the 16k screen |
| phi-2 | no model small enough (q2, q4, q4) > ceiling | KV 320 KiB/token -> ~22.5 GiB q4_0 KV; window 2,048 besides |
| granite-3.0-2b-instruct | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 4,096; 4,096-class score |
| granite-3.1-2b-instruct | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; Q4 counting fell off the cliff (12,288 -> 6,144) |
| granite-3.2-2b-instruct | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; score 15,360 |
| granite-3.3-2b-instruct | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; score 26,624 |
| granite-4.0-350m | training window < 256k | window 32,768, config.json verified (addendum 25), rope_scaling absent; RAM would fit (1.97 GiB q4_0 KV); never passed the 16k screen on the f4k grid (quality) |
| granite-4.0-h-350m | training window < 256k | window 32,768, config.json verified (addendum 25), rope_scaling absent; RAM would fit (2.25 GiB q4_0 KV); never passed the 16k screen (quality) |
| granite-4.0-1b | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072 |
| granite-4.0-micro | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; MoE hybrid |
| granite-4.0-h-micro | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; MoE hybrid |
| granite-4.0-h-1b | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; MoE hybrid |
| granite-4.1-3b | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; score 18,432 |
| granite-4.2-3b | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; also corrupted f16 file in the Q4 resume |
| MiniCPM-1B-sft | no model small enough (q2, q4, q4) > ceiling | KV 104 KiB/token -> ~7.3 GiB q4_0 KV; window 4,096; 4,096-class score |
| MiniCPM-2B-sft | no model small enough (q2, q4, q4) > ceiling | KV 360 KiB/token -> ~25.3 GiB q4_0 KV; window 4,096 |
| MiniCPM3-4B | no model small enough (q2, q4, q4) > ceiling | KV 620 KiB/token -> ~43.6 GiB q4_0 KV; window 32,768 |
| MiniCPM4-0.5B | training window < 256k | window 32,768, config.json verified (addendum 25): rope_scaling present (longrope) - the window is doubly closed (trained short, extension rejected); RAM would fit (0.84 GiB q4_0 KV); never passed the 16k screen (quality) |
| MiniCPM5-1B | training window < 256k | window 131,072, config.json verified (addendum 25), rope_scaling absent; RAM would fit (1.69 GiB q4_0 KV) - the window is the wall |
| MiniCPM5-2B | training window < 256k | window 131,072, config.json verified (addendum 25), rope_scaling absent; RAM would fit (~4.2 GiB whole config at q4_0 KV) - the window is the wall; also FWE zero at Q4_K_M |
| AI21-Jamba-Reasoning-3B | thinking cannot be disabled | the reasoning tune has no non-thinking mode; same 262,144 window and thin KV as Jamba2-3B but the wrong shape for the gates |
| AI21-Jamba2-Mini | no model small enough (q2, q4, q4) > ceiling | 12B MoE (16 experts, 2 active): Q2_K weights alone ~4.75 GiB, over the ceiling before KV; window 262,144 |
| openai/gpt-oss-20b | training window < 256k | window 131,072, config.json verified (addendum 25): rope_scaling present (factor 32) - doubly closed; MoE besides (21B total, 3.6B active - Q2_K weights far over the ceiling); the addendum-20 KV note (48 KiB/token) stands |
| HuggingFaceTB/SmolLM3-3B | training window < 256k | window 65,536, config.json verified (addendum 25), rope_scaling absent; KV 72 KiB/token -> ~5.1 GiB q4_0 KV would also exceed the ceiling |
| tencent/Hunyuan-A13B-Instruct | training window < 256k | window 32,768, config.json verified (addendum 25): rope_scaling present (factor 8) - doubly closed; MoE (80B total, 13B active) besides |
| LGAI-EXAONE/EXAONE-4.0-32B | training window < 256k | window 131,072, config.json verified (addendum 25): rope_scaling present (factor 16) - doubly closed; KV 256 KiB/token (~18 GiB q4_0 KV) would also exceed the ceiling |
| inclusionAI/Ling-lite | training window < 256k | window 32,768, config.json verified (addendum 25), rope_scaling absent; KV 56 KiB/token -> ~3.9 GiB q4_0 at 262k would nearly fit - the window is the wall; the addendum-20 row carried a wrong repo name (Ling-lite-1.5B does not exist), corrected |
| zai-org/GLM-4.5-Air | training window < 256k | window 131,072, config.json verified (addendum 25), rope_scaling absent; MoE (106B total, 12B active) besides |
| meta-llama/Llama-3.2-1B-Instruct | training window < 256k | window 131,072, config.json verified by the author (addendum 22, gated repo); RAM would fit - KV 32 KiB/token f16 (16 layers x 8 kv heads x 64 head_dim) -> ~2.25 GiB q4_0 KV, whole config ~3.75 GiB - the window is the wall |
| meta-llama/Llama-3.1-8B-Instruct | no model small enough (q2, q4, q4) > ceiling | KV 128 KiB/token f16 (32 layers x 8 kv heads x 128 head_dim) -> ~9 GiB q4_0 KV at 262k, over the ceiling before weights; window 131,072 < 262,144 besides (both disqualifiers bind; size first per the fair-chance order); gated repo, numbers from the public model card |
| google/gemma-3-1b-it | training window < 256k | window 32,768, config.json verified by the author (addendum 22, gated repo); 1 kv head - thin KV, but the window binds hard |
| google/gemma-3-4b-it | training window < 256k | window 131,072, config.json verified by the author's pull (gated repo; the value nests in text_config - the gemma-3 multimodal wrapper); KV geometry not extractable from the author's pull output (layers/kv_heads printed None in the wrapper) - the window binds regardless |
| Qwen3-30B-A3B-Instruct-2507 | no model small enough (q2, q4, q4) > ceiling | window 262,144 but MoE: Q2_K weights alone far over the ceiling; KV 96 KiB/token -> 6.75 GiB q4_0 KV besides |
| Qwen3-4B-Instruct-2507 | no model small enough (q2, q4, q4) > ceiling | window 262,144 but KV 144 KiB/token -> ~10.1 GiB q4_0 KV (the 2507 refresh dropped the hybrid interval) |
| DSpark/EAGLE3 draft heads (RadixArk, z-lab, incoai, lightseekorg, Inferact, skt repos) | other | speculative-decoding DRAFT MODELS, not instruct models - sweep false positives, never candidates |
| community finetunes (NeoHorse-1-4B, JevK5, test tinies, reformer) | other | rule 5 (first-party weights) / not instruct models - sweep false positives |
| RWKV7-World-2.9B (the family) | other | the Q8_0 probe measured it: pure recurrence cannot carry FWE at 256k - the state degenerated at depth (miss text single-character repetitions, session 36 addendum 1); the Q6_K config is closed with it (same constant state, smaller weights - the limitation is config-independent at this scale); the speed result stands as a finding: 13.11 w/s at 262,144, the fastest depth-scorer in the study |
