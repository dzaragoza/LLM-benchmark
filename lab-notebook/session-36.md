## Session 36

Session 36 opens with the overnight run's results in (the four-probe ceiling chase, session 35 addendum 27's blocks, dry-run-verified addendum 28). The machine ran 21:43-01:25; every probe completed its ladder. The grading below is against the pre-registered predictions (session 35, day close).

### Session 36, addendum 1 - the overnight results, graded

THE HEADLINE: A NEW CHAMPION CONFIG - AI21-Jamba2-3B @ Q8_0 PASSES BOTH GATES AT 262,144 on its first-ever probe: speed PASS at 6.08 w/s worst turn (the reader never waited), FWE 3/3 words HIT at 261,888, cold machine cost 4.42 GiB (89% of the 4.96 ceiling), 54.4 min wall. The predictor called it 4.40 GiB / ~7 w/s - the RAM prediction was off by 0.02 GiB (0.5%), the w/s by 15% (conservative). The mamba-hybrid risk (FWE through recurrent state) DID NOT materialize: the hybrid's 2 full-attention layers carried the retrieval fine. THE FIRST NON-TRANSFORMER PASS in the study.

THE 2B QUANT-RAISE FAILS AT THE TOP RUNG: Q8_0 + q8_0/q8_0 at 262,144 - speed PASS at 8.18 w/s, cold cost 5.22 GiB (OVER the 4.96 ceiling by 0.26 GiB - the predictor said 4.78, the real machine took 5.22, a 9% underestimate: the q8_0 KV overhead plus buffers exceeded the model), FWE FAIL 0/3 words at 261,888 (the miss text opens "Based on the provided text, which appears to be" - the model found no coded words at this depth through the q8_0 cache; whether that is the q8_0 KV noise or a genuine capability drop from Q4_K_M's q5_0 cache is the open question). THE 2B's PASS ROW STANDS at Q4_K_M + q5_0/q5_0 (3.48 GiB, 9.5 w/s) - the quant-raise is closed: the ceiling does not buy precision at this size.

THE 4B TIMED OUT mid-ladder: speed PASS at 262,144 (7.3 w/s worst turn, cold cost 5.81 GiB - OVER the ceiling by 0.85 GiB; the predictor's 4.95 was 15% optimistic), then TimeoutError at +94m into the FWE phase (the FWE server at 262k with the q4_0 cache exceeded the harness timeout). Not a quality verdict - an infrastructure death. The 0.01-GiB edge did not survive contact with the real machine: at 5.81 GiB the 4B is 0.85 GiB over, and the timeout is consistent with the machine swapping under the load. The 4B returns to CANDIDATES with the measurement recorded (its RAM verdict is FAIL; a re-probe would need a smaller config, but Q2_K IS its floor config - the family closes at 4B for this machine).

THE RWKV RECURRENCE VERDICT: speed PASS at 13.11 w/s (the fastest depth-scorer ever measured in the study - pure recurrence pays in decode speed), cold cost 3.58 GiB (well under the ceiling; the predictor said 4.13, 13% conservative), FWE FAIL 0/3 at 261,888 - and the miss text is the tell: "h ... ... ... ... ... ... ... ... ..." - the model degenerated into single-character repetitions, it did not even attempt the extraction. This is not near-miss behavior: the constant-size state at 262k depth does not carry the task. The recurrent-state fidelity question is ANSWERED for FWE-at-256k: pure recurrence at this scale does not do exact retrieval through state alone. The mamba hybrid passes BECAUSE it keeps 2 full-attention layers; the pure recurrent does not.

THE PREDICTION GRADE: Jamba RAM 4.40 vs 4.42 (+0.5% - excellent); RWKV RAM 4.13 vs 3.58 (-13%, conservative side); 2B RAM 4.78 vs 5.22 (+9% under); 4B RAM 4.95 vs 5.81 (+15% under). w/s: Jamba ~7 vs 6.08 (conservative); RWKV ~8 vs 13.11 (way conservative); 2B ~9 vs 8.18 (good); 4B ~5 vs 7.3 (conservative). The predictor's systematic bias: it UNDERESTIMATES the machine cost of q8_0/q4_0 KV configs (the 2B and 4B rows) - the KV term's effective-size factors are slightly optimistic for quantized caches; the f16-KV rows (Jamba) are near-exact. Registered for the predictor's next calibration.

THE REGISTRY MOVES (models.md, this addendum):
- Jamba2-3B Q8_0 -> PASS (the new co-champion config: 3.17 file / 4.42 GiB / 6.1 w/s)
- Jamba2-3B Q6_K -> stays CANDIDATES (the spare; 3.81 predicted - now the top unpicked config in the pool)
- 2B Q8_0 quant-raise -> FAIL (5.22 GiB over ceiling + FWE 0/3; the attempt's numbers recorded)
- 4B Q2_K -> FAIL (5.81 GiB over ceiling + timeout; the attempt's numbers recorded - the timeout recorded as the failure reason with the RAM verdict)
- RWKV7 Q8_0 -> FAIL (FWE degeneration 0/3; speed 13.11 w/s and 3.58 GiB recorded - the RAM and speed are fine, the quality is not)
- RWKV7 Q6_K -> stays CANDIDATES? NO - closed: the Q6_K config would not change the FWE verdict (same state size, smaller weights); the recurrence limitation is config-independent at this scale. Moved to REJECTED (other: recurrence cannot carry FWE at 256k - measured, addendum 1).

THE POOL AFTER THE NIGHT: PASS 0.8B (4.96, the depth-score champion), 2B Q4_K_M (3.48, the RAM champion), Jamba2-3B Q8_0 (4.42, the new-family pass). FAIL carries the night's three measured attempts. CANDIDATES holds one unpicked config: Jamba2-3B Q6_K (3.81 predicted) - the natural next probe if the author wants the Jamba family's cheaper config on record.

### Session 36, addendum 2 - the registry moves; the report's roster is settled

MODELS.MD (all moves verified, one-model-one-table clean): PASS gains AI21-Jamba2-3B @ Q8_0 (3.17 / 4.42 GiB / 6.1 w/s - the first non-transformer PASS; the 2B's note updated: its quant-raise FAILED, this Q4_K_M config is its ceiling config). FAIL opens with the night's three measured 256k attempts: 2B Q8_0+q8_0 (5.22 GiB over ceiling AND FWE 0/3 - the quant-raise closed), 4B Q2_K+q4_0 (5.81 GiB over ceiling, timeout into FWE - the family closes at 4B for this machine, Q2_K is its floor config), RWKV7 Q8_0 (FWE degeneration, single-character repetition output at 261,888 - the family moves to REJECTED with the finding: 13.11 w/s, the fastest depth-scorer in the study, but pure recurrence cannot carry FWE at 256k). CANDIDATES shrinks to ONE unpicked config: AI21-Jamba2-3B @ Q6_K (predicted 3.81 GiB, 77% of ceiling - the natural next probe: does the family hold FWE at Q6_K).

THE PREDICTOR CALIBRATION DATA (for the report): f16-KV rows predict near-exact (Jamba: 4.40 vs 4.42, +0.5%); q8_0/q4_0 KV rows underestimate the machine cost by 9-15% (2B: 4.78 vs 5.22; 4B: 4.95 vs 5.81). The quantized-KV effective-size factors are the predictor's next calibration target. RWKV's RAM predicted 4.13 vs measured 3.58 (-13%, conservative side - the constant state costs less than the overhead term assumed).

THE ROSTER FOR THE REPORT (the author asked for the data - this is it): three PASS configs across two architectures -
| model | config | file | RAM | w/s | role |
| Qwen3.5-0.8B | Q8_0 + f16 K/V | 0.86 GiB | 4.96 GiB | 9.3 | the champion - the deepest proven depth per RAM byte; sets the ceiling |
| Qwen3.5-2B | Q4_K_M + q5_0/q5_0 | 1.22 GiB | 3.48 GiB | 9.5 | the RAM champion - 70% of the champion's cost at the same depth |
| AI21-Jamba2-3B | Q8_0 + f16 K/V | 3.17 GiB | 4.42 GiB | 6.1 | the non-transformer pass - hybrid mamba-attention carries FWE at 256k |
plus one candidate config unpicked (Jamba2-3B Q6_K, 3.81 predicted) and the night's three measured FAILs with their numbers. The speed-vs-depth-vs-RAM story: RWKV7 measured 13.11 w/s at 262,144 (a finding even in failure - pure recurrence is the fastest decode) but fails FWE; the Jamba hybrid is the middle path that passes everything.

OPEN FOR THE AUTHOR: (1) the Jamba Q6_K probe - one command, ~55 min, answers whether the family holds at 77% of ceiling; (2) the head-to-head the roster now invites: 0.8B vs 2B vs Jamba2-3B on a quality axis beyond FWE (the notebook's n=1 FWE is a screen, not a quality ranking); (3) the report itself - the roster above is the data table.
