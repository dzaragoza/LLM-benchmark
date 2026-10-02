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

### Session 36, addendum 3 - the six-point review; CANDIDATES fixed, tooling hardened, predictor recalibrated

THE CANDIDATES TABLE WAS BROKEN and BOTH gates missed it (author catch,
request 1). The breakage: a single BLANK LINE between the delimiter row
and the data row of the Jamba Q6_K table (models.md line 47, introduced
by the session-36 addendum-1 line-based restoration). GitHub splits a
GFM table at a blank line, so the Jamba row rendered as an orphaned
one-row table under a headerless pipe row - "broken". Why the tooling
did not catch it: md_check.check_tables closes the table block at the
blank line and validates only the header+delimiter pair (which is
well-formed) - the orphaned data row below is NEVER inspected; and
code_edit's auto-fixer covered MD058's "blank before header" and
"blank after body" but had no rule for a blank INSIDE a table. Both
fixed this session:

- md_check.check_tables now emits MD058 "blank line inside the table -
  GitHub splits the table and orphans the rows below" when the line
  after the block is blank and the line after THAT is a pipe row.
- code_edit._fix_markdown now AUTO-FIXES the case (the fix is unique
  and unambiguous - pop the blank between the delimiter row and the
  data row), keeping the addendum-17 ruling: mechanical rules are
  fixed, judgement rules are lint failures.
- Regression tests: test_md058_blank_line_inside_table (checker),
  test_fix_markdown_collapses_blank_line_inside_table (fixer).
  Suite: 127 passed (was 125).

THE RULING REGISTERED (request 5): RAM OVER CEILING IS NOT A FAIL
REASON. The 4.96 GiB ceiling is always an estimate; a measured RAM
over ceiling is a NEW CEILING WITH A PASS - a measurement, recorded
with the row, never the fail reason. The fail reason is whatever the
gates say. models.md header now carries the ruling and both FAIL rows
are re-worded: 2B Q8_0 fails on FWE 0/3 (5.22 GiB recorded as a
new-ceiling measurement), 4B Q2_K fails on the timeout (5.81 GiB
recorded likewise). RWKV7's reason was already FWE degeneration. The
REJECTED table keeps its size reason for PREDICTED-over configs (the
screen rejects on prediction; only measured attempts earn the
new-ceiling wording).

THE PREDICTOR RECALIBRATED (request 4, rule 2 rewritten): the
theoretical bytes-per-element factors UNDERESTIMATED the quantized-KV
rows by 9-15 percent. Backing the overhead out of the measured anchors:
2B q8_0 4.78 predicted vs 5.22 measured -> KV term 3.29 GiB ->
calibrated q8_0 factor 0.665 (theoretical 0.53125 x 1.25); 4B q4_0
4.95 predicted vs 5.81 measured -> KV term 7.22 GiB -> calibrated q4_0
factor 0.400 (theoretical 0.28125 x 1.42). The quantized cache costs
~25 percent (q8_0) to ~42 percent (q4_0) more than raw bytes -
quantization block book-keeping and fragmentation, not model state.
f16 stays 1.0 (near-exact: Jamba 4.40 vs 4.42, +0.5 percent). One
anchor per quantized factor; refine as more quantized-KV probes land.
Validation status now five anchors, listed in rule 2.

THE 4B TIMEOUT EXPLAINED (request 6): the harness's non-streaming
POST timeout is 1800s (llama_server.post_json default, llama_server.py
line 301). The FWE cell posts ONE non-streaming request carrying the
whole 261,888-token prompt (ruler_gate.ask -> post_json, "stream":
False). The FWE phase therefore needs prefill of 261,888 tokens
INSIDE one 1800s window: it must sustain >= 145.5 tok/s prefill. The
speed phase proves the machine could not: the speed census measured
the 4B at 7.3 t/s DECODE, and the mapped-census line - 7.63 GiB
mapped, 1.00 GiB resident, file 0.22 + anon 0.78 - is a
memory-bandwidth-bound profile; the q4_0 KV cache at 262k adds
further bandwidth pressure in prefill. The 0.01-GiB-predicted-edge
config died in the harness, not in the model. The speed gate never
sees this timeout because it STREAMS (speed_gate.py line 402,
"stream": True) - the reader collides mid-stream long before any
30-minute wall. The Jamba and 0.8B FWE cells fit the wall with
headroom because their prefills are fast enough; the 4B at Q2_K with
q4_0 KV could not prefill 262k in 30 minutes. Candidate discriminated:
the timeout is the HARNESS's non-streaming 1800s budget vs the 4B's
prefill rate at 262k with a q4_0 cache - not a capability verdict and
not swap (32 GB total RAM, 5.81 GiB cost). Registered. If a 4B-family
re-probe is ever wanted, the fix is harness-side: raise post_json's
timeout for depth-262k FWE cells or stream the FWE prefill.

THE FWE DIAGNOSTIC PRE-REGISTERED (request 3): the 2B Q8_0's FWE 0/3
is unexplained - the Q4_K_M config holds FWE 3/3 at the same depth, so
either q8_0-KV noise (a cache-fidelity effect) or a capability drop
at the higher quant is the suspect, and n=1 per task cannot
discriminate noise from capability. Recommendation: n=5. The
registered precedent is the session-34 addendum-3 diagnostic (seeds
1024-1028, full answers read from the ruler-results CSV; the ladder
stays n=1 for scores). The diagnostic, pre-registered:

- 2B Q8_0+q8_0 FWE at depth 261,888, n=5, seeds 1024-1028, fresh CSV,
  answers read in full: 5/5 with near-miss partials -> cache-fidelity
  noise, the config gets a second chance at n=1 in the ladder; 0-2/5
  with miss texts like the overnight's -> capability drop, the
  quant-raise closes for good.
- Control arm, same session: 2B Q4_K_M+q5_0 (the PASS config) FWE at
  261,888, n=5, seeds 1024-1028 - expected 5/5; if the control arm
  flickers, the task itself is the noise, and the FWE cell's
  reliability question opens ahead of the config question.

Jamba2 acknowledged (request 2, no action beyond the record): the
first non-transformer PASS - a genuinely distinct model class in the
pool, carried by 2 full-attention layers over 1 KV head.

### Session 36, addendum 4 - author review of addendum 3; n justified, predictor discipline, timeout out of scope

THE BLANK-INSIDE-TABLE RULE IS MARKED BEYOND-THE-REFERENCE (request 1,
answered): the reference linter is markdownlint, and its MD058
(blanks-around-tables) checks blanks AROUND tables. On our exact
breakage - a blank between the delimiter row and the data row - the
reference linter is silent BY CONSTRUCTION: in its parse the blank
line already split the table, and the orphaned pipe rows below are not
a table at all (GFM requires a delimiter row), so there is nothing
for MD058 to be "around". Our check is a deliberate extension, kept
under the MD058 ID because it is the same failure class (GitHub
renders a broken table) and the same fix. md_check.py's docstring now
marks the rule with its derivation: markdownlint-covered vs
beyond-the-reference, and why. The checker and the auto-fixer stand
as shipped in addendum 3 (127 tests).

WHY n=5, NOT n=3 OR n=10 (request 3, the justification): what each
repetition buys is DISENTANGLING two hypotheses that n=1 cannot
separate -

  H-noise:  q8_0-KV quantization noise - the answer is right in the
            cache but a task draw flips it; per-task hit prob p_high,
            near 1, i.i.d. draws.
  H-cap:    capability drop at the higher quant - p_low, near 0.

The statistic that improves with n is the CONFUSION between these:
observing k hits out of n, the likelihood ratio between the two
hypotheses sharpens as n grows. With one anchor each - the PASS
config holds 3/3 and the overnight config went 0/3 - the realistic
posterior puts p_high around 0.9 (PASS-side) and p_low around 0.1
(fail-side). n=5 discriminates them decisively: under p=0.9, P(0 or 1
hits in 5) ~ 0.0009 - a 0-1/5 result is essentially impossible for
H-noise; under p=0.1, P(>=4 hits) ~ 0.0005 - a 4-5/5 result is
essentially impossible for H-cap. n=3 leaves the middle open (2/3 is
compatible with both at small likelihood cost), n=5 is the smallest n
whose BOTH tails are < 0.001, and beyond n=5 the tails shrink
exponentially but the decision boundary does not move - the extra
tasks buy no new discrimination. Cost side: each task is one
261,888-token prefill + 128-token generation at 8.2 w/s - a few
minutes of machine time; five tasks per arm, two arms (probe +
control) is the whole diagnostic. n=5 is not arbitrary - it is the
smallest n that closes both tails at the 1-in-1000 level with the
study's own anchors as the priors.

THE PREDICTOR STAYS UNDER TUNING (request 4, registered as standing
discipline): the calibration is now a PER-FACTOR one-anchor fit
(q8_0 0.665 from the 2B, q4_0 0.400 from the 4B, f16 1.0 from three
near-exact anchors). Each new measured config with a quantized KV
cache lands as a second anchor for its factor: if the two anchors
disagree by more than 5 percent, the single factor splits into a
per-model-class factor (the block sizes differ across families).
q5_0 is unmeasured and still carries its theoretical 0.34375 - the
first q5_0 probe grades it the same way. The predictor's calibration
status is now a living part of rule 2, updated every probe
(pre-registration discipline, unchanged).

THE 4B TIMEOUT INVESTIGATION IS OUT OF SCOPE (request 6, author
ruling): the timeout explanation stands as registered in addendum 3
(the harness's 1800s non-streaming budget vs the 4B's 262k prefill
rate), but the follow-up - raising post_json's timeout for
depth-262k FWE cells or streaming the FWE prefill - will NOT be
pursued; the 4B family stays closed on this machine due to time
constraints. The harness-side fix note stays in the notebook for
whomever revisits the family; no code change.
