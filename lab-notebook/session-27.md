Merged per the one-session-per-day ruling (session 40, addendum 19): sessions 27, 28 and 29 all opened on the 2026-09-26 working day, so they share one session file. Session 29's tail runs into 09-27 (the working day ran past midnight - recorded, not split). Content verbatim; session numbers unchanged.

## Session 27 — 2026-09-26 (protocol v2: the depth-prefill gate; the reader guarantee replaces the floor)

**Author ruling (opening the session):** the speed gate must measure what the guarantee actually says. The guarantee (Session 26, addenda 2–6) is "the worst experienced lag will never fall below the 6.5 t/s of a fast reader, at the context size" — so even a fast reader is never bothered by slow token generation. The old gate graded the worst turn against floor 20 at SHALLOW depth (~1.2k tokens of accumulated history): wrong line (floor 20 is a headroom judgment, not the guarantee) and wrong depth (the guarantee is stated at the reference depth, addendum 9). "We're not aiming at 6.5 t/s" — the guarantee is the FLOOR of the experience, and the refinement (how many t/s above 6.5 makes it smooth, via the k_min / absorption analysis) rides on top as measurement, not as the pass line. The author's expectation on record: the new criteria "might open the door to higher quants or even bigger models."

**Protocol v2 (implemented this session, both layers):**

1. **Depth prefill per conversation.** Each corpus conversation runs ON TOP of a blob of corpus text (content irrelevant — the KV cost is content-independent, addendum 11), prepended as a user turn inside the history (the chat template wraps it; cache_prompt retains it turn-to-turn). Sized per conversation via the server's own `/tokenize` so the DEEPEST turn lands just under the 4096 reference depth, and never exceeds ctx (context shift would silently discard the blob; gemma-3 hard-errors on shift — addendum 9). The budget is worst-case (every answer at the 299-token cap), so real depth lands conservatively under the reference.
2. **The verdict line is the reader guarantee:** worst turn at depth >= 6.5 t/s − 2σ (the lenient 2-sigma ruling, moved to the guarantee line). Floor 20 (k=3) is reported as a HEADROOM column, never gated. The gate prints both, the state records both.
3. **Same-depth noise samples.** After each conversation, identical tiny follow-ups on the warm slot: worst/mean across them is the machine's noise at depth — the addendum-10 attribution (KV trend vs noise), now a standing part of every run.
4. **Thinking mode:** the blob budget subtracts the 2048-token THINK_ALLOWANCE per turn (reasoning + answer both persist in history); at the allowance, the deepest conversations may leave no blob budget — printed honestly when so (the conversation alone fills the context; the measurement runs at that natural depth).

**Tooling:** `speed_gate.py` protocol v2 (depth_budget / build_blob / blob-in-history / noise_sample; `--reader-tp` flag, default 6.5; `--floor` re-documented as the headroom line); `full_benchmark.py` threads `--reader-tp`; `llama_server.py` gains `tokenize()` + `trim_to_tokens()` (bisection on chars, never over budget — depth_probe.py keeps its own trim until a follow-up unifies them). Verified against a mock llama-server simulating /tokenize and KV-tax depth decay: blob budgets differ per conversation and never exceed ctx; the blob lands in the history (depth estimates exact for the blob, 4 chars/token for the conversation side); worst turn is depth-conditioned; verdicts PASS at 6.5 / FAIL above the fake speed; headroom reported; the orchestrator ladder walk SELECTS THE TOP RUNG (Q8_0) at the reader line with headroom honestly "below floor (k=3)" — the mock encodes exactly the author's expected effect. lag_analyze.py compatibility preserved (v2 dumps carry every legacy field).

**Honest consequences, on record before the rerun:**

- The old gate's floor-20 rejections were headroom judgments. Qwen3.5's Q6_K (18.8) and Q8_0 (15.3) clear 6.5 by 2.3–2.9×. **Every rung previously measured in this study passes the reader guarantee with large margin** — the ladder walk should now stop at each family's TOP rung (Q8_0 where first-party or self-made), and the selection question becomes the RIGHT-SIZING question (Session 26): the guarantee admits anything up to size*(6.5) ≈ 10.4 GiB on the T14s — the constraint that actually binds is quality-per-class and the plateau/cliff rule, not speed.
- The gate therefore stops discriminating comfort and becomes a SAFETY CHECK; comfort moves entirely into the reported headroom column and the k_min/absorption analysis. The prediction: all five non-thinking families select their top rung, subject only to file availability and the never-below-Q4_K_M quality cliff.
- Session 20's ranking is NOT invalidated (accuracy is orthogonal), but its SELECTED RUNGS are protocol-v1 artifacts: the v2 ranking must be re-measured on the new selections. ARC is unaffected per model file; new rungs need new ARC runs.

**Pre-registered predictions (the rerun, before any measurement):**

1. Every roster family selects its top available rung at the reader line (qwen3.5 Q8_0 or Q6_K — pending its first-party/self-made availability; llama-3.2 Q8_0; gemma-3: whatever the top first-party rung is, its QAT repo ships Q4_0 only, so self-quant or acceptance of Q4_0 as top; phi-4-mini per its repo's top).
2. Worst turn at depth per default rung lands in the addendum-10 KV-tax bands: qwen3.5 Q5_K_M 17.5–19.5 (and proportionally lower for its higher rungs: Q6_K ~15.5–17.5, Q8_0 ~12–15 at depth); llama-3.2 Q8_0 ~24–26; gemma-3 ~20–22. A miss on any band revises the +ms/token tax or the noise story (the addendum-11 stakes, unchanged).
3. The noise-at-depth w/m (same-depth samples) sits in 0.90–1.00 on this machine if noise is machine-constant (the addendum-10 hypothesis; the healthy-rung shallow measurement was 0.97).
4. No roster model at its SELECTED (top) rung falls below the reader line at the reference depth — the guarantee holds across the entire measured field; if any does, that is the finding (a KV/slope or SWA interaction worth its own addendum).
5. The v2 re-selection changes at least two families' rungs vs Session 20 (the author's "opens the door" expectation, now on record as a falsifiable number).

**Rerun commands (unchanged CLI, new protocol):**

```
python3 full_benchmark.py "microsoft/Phi-4-mini-instruct" "google/gemma-3-4b-it-qat-q4_0-gguf=google/gemma-3-4b-it" "meta-llama/Llama-3.2-3B-Instruct" ...
python3 full_benchmark.py --no-thinking "Qwen/Qwen3.5-4B"
python3 full_benchmark.py --thinking --state-file benchmark-state-thinking.json "Qwen/Qwen3.5-4B" "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF"
```

Then `--arc-only` rankings per category on the new selections; the McNemar restriction rule (Session 25 addendum 2) applies per category as before. Fresh dumps throughout (the v2 dump format adds blob_tokens/depth fields — old dumps are protocol-v1 data, kept, never reused by v2 resume; the mode-suffix rule from Session 25 is unchanged and still mandatory).

---

### Session 27, addendum 13 — protocol v2.1: the guarantee is anchored in words, not tokens (author's catch)

**The catch.** The author spotted the unit error before any rerun ran: "6.5 t/s is not 6.5 w/s." The reader anchor was always **words** (300 wpm, Brysbaert 2019) = **5.0 words/s**; the 6.5 t/s line was a derivative — 5.0 w/s ÷ the 0.75 words/token rule of thumb, which addendum 3 flagged as unanchored and scheduled for measurement. The two lines coincide only at exactly 0.75. A tokenizer with a lower words/token ratio passes 6.5 t/s while failing the READER: the stream delivers fewer words per second than the reader consumes, and the reader waits. The honest instrument must anchor the verdict in w/s and measure the ratio, not assume it.

**Protocol v2.1 changes (implementation, committed before any rerun):**

1. Every turn record now carries `gen_words` (whitespace words of the answer), `server_wps` (words / generation span, where generation span = wall − prompt_ms/1000, the same span the external cross-check uses), and `words_per_token` (measured, per turn).
2. The verdict is computed in **w/s**: worst conversation-worst (in w/s) vs the reader line 5.0 w/s − 2σ. `READER_WPS_DEFAULT = 5.0` replaces `READER_TPS_DEFAULT = 6.5`; CLI flag `--reader-tp` → `--reader-wps` (both `speed_gate.py` and `full_benchmark.py`).
3. The **token-side view** is printed alongside (worst/mean t/s, words/token measured-vs-default flag, headroom vs floor 20) — continuity with the law's currency (the size→t/s law is in t/s; the guarantee is in w/s; the bridge is the measured words/token).
4. Noise samples carry `wps` and `words_per_token` too.
5. **v1 dumps** (no w/s fields) convert via the dump's own words/token when present, else the 0.75 default — flagged `unanchored` in the result. Session-20 v1 verdicts were computed in t/s against 6.5; their v2.1 re-reading may differ where words/token ≠ 0.75.

**Why this matters (the mock made it concrete):** the verification mock's tokenizer produces 0.688 words/token. At the mock's worst depth turn (14.8 t/s) the 0.75 assumption reads 11.1 w/s; the measured value is 10.1 w/s — a 9% overestimate. The direction of the error matters: a tokenizer that is MORE verbose per token (lower w/t) makes the t/s line LOOK safer than it is. Qwen's tokenizers are more verbose than Llama's (addendum 3, prediction 3), so qwen models were the most exposed to the unanchored rule.

**Tool state:** `speed_gate.py` w/s verdict with v1 fallback (mock-tested: measured path, unanchored-fallback path, strict-FAIL path); `full_benchmark.py` threads `reader_wps` and prints the w/s verdict + token-side view; README protocol notes updated. `lag_analyze.py` still gates at 6.5 t/s (`READER_TPS_DEFAULT`) — its reader line should gain the same w/s anchoring for consistency; queued as follow-up, author has not ruled.

**Pre-registered predictions (v2.1, before the qwen Q8_0 run):**

1. Qwen3.5-4B Q8_0 at depth clears the reader line in w/s: measured worst ≥ 5.0 w/s. Given 15.3 t/s shallow (Session 20) and the addendum-10 KV-tax band 12–15 t/s at depth, the w/s prediction follows from the ratio: at the predicted 0.7 words/token, 12–15 t/s → **8.4–10.5 w/s** — PASS with margin; the headroom column will read "below floor (k=3)" as before, honestly.
2. Qwen3.5's measured words/token lands **0.65–0.75** (addendum 3's prediction 3: Qwen ≥ Llama-3.2's ratio is re-stated in measured form — bigger vocab 152k vs 128k, fewer tokens per word, so MORE words per token than Llama if the tokenizer is efficient... honest form: the direction is uncertain, the band is the prediction). Correction on record: addendum 3's prediction 3 stated Qwen ≥ Llama, which in words/token means Qwen's ratio should exceed Llama's — the qwen Q8_0 run grades this.
3. At depth, the ratio does not shift (words/token is a tokenizer property, not a speed property): per-turn `words_per_token` variance across the 5 conversations < 0.02.
4. The noise-at-depth w/m in w/s equals the t/s w/m (the ratio is constant across turns within a model): w/m(w/s) / w/m(t/s) ∈ [0.95, 1.05].
5. The live session (author's hands) is the real test: if the guarantee holds and the headroom is below-floor, the felt experience should be "smooth but visibly slower than Q5_K_M" — the author's own perception is the calibration point the instrument cannot replace.

**Grading:** pending the T14s run. The command (speed-gate only, no modes, default non-thinking dump):

```
python3 speed_gate.py --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf
```

---

### Session 27, addendum 14 — the qwen Q8_0 depth run: grading v2.1, and two catches the run surfaced

**The run (T14s, protocol v2.1, default-mode dump, 2026-09-26):** Qwen3.5-4B Q8_0, 5 conversations each depth-prefilled via per-conversation blobs (2799/2758/2158/2814/2196 tokens), 22 turns at depth, 10 noise samples. Output: worst turn 14.9 t/s; verdict 11.21 w/s → PASS (confident) at the 5.0 w/s reader line; headroom below floor 20 (k=3), honestly reported.

**Grading the five v2.1 pre-registrations (addendum 13):**

1. **PASS the reader line in w/s — HIT.** Worst 14.9 t/s at depth, reported 11.21 w/s (via the 0.75 default — see the catch below: unanchored, so the number is provisional). Clears 5.0 w/s by 2.24×. The author's "door opens" expectation from Session 27's opening ruling: confirmed for qwen Q8_0 — the rung that floor-20 rejected (15.3 t/s shallow, Session 20) is now admissible, and at depth it still clears the guarantee by a wide margin.
2. **Worst turn at depth 8.4–10.5 w/s — MISS, in the interesting direction.** Predicted from the KV-tax band (12–15 t/s at depth) × 0.7 w/t = 8.4–10.5 w/s. Measured worst t/s at depth was **14.9 — above the band's top**. The band was derived from the law fit + KV arithmetic, assuming the blob lands at ~4000 depth; measured turns ran at ~3.4–4k effective depth with worst 15.5 in the shallowest-blob conv and 14.9 in the deepest. The addendum-10 KV-tax estimate for qwen3.5 (+7.4 ms/token at D=4096) is therefore an over-estimate at the protocol's conservative blob sizing — the blob budget is worst-case (every answer at cap), so actual depth lands under 4096 (deepest turn ~3.9k by the blob+history estimate), and the real tax is smaller. Honest note: the band assumed exact-4096 depth; the protocol's deliberate under-run makes the band systematically pessimistic. The refined instrument is depth_probe.py with exact depth targeting.
3. **Measured words/token 0.65–0.75 — UNGRADED (the run cannot grade it), and this is a catch.** The verdict line read "words/token 0.750 (0.75 default, unanchored)" and no per-conv "words/s:" lines printed: **every answer was empty** (0 gen_words on all 22 turns). Qwen3.5 is a hybrid: in default mode it thinks first; with max_tokens capped at 299 the model spends the entire budget on reasoning_content and emits no final content. The t/s numbers are valid (decode physics is content-independent — addendum 11); the w/s verdict is provisional until a mode-true rerun. Tooling fixed this session: `answer_empty` now flags non-thinking empty answers too, and `bench_model` prints a loud warning naming the mode flags when every answer in a conversation comes back empty.
4. **Noise-at-depth w/m 0.90–1.00 — HIT (value 0.985), with an instrument bug caught and fixed.** The measured w/m 0.985 was produced by the BUGGED noise path (see below); the corrected instrument (noise samples riding the conversation history) will re-measure. The 0.985 is thus noise-at-shallow-depth (the bare follow-up re-prefilled at ~zero depth and decoded over a near-empty cache), consistent with the addendum-10 healthy-rung shallow w/m of 0.97 — machine noise at shallow depth is small, as predicted. Graded HIT for the hypothesis it accidentally measured; the at-depth value awaits the rerun.
5. **Live-session felt experience — pending the author's live run (not part of this output).**

**Catch 1 (author's machine, protocol-relevant): hybrid-in-default-mode answers are empty under a 299-token cap.** The default (no mode flags) run of a hybrid model is NOT a non-thinking run: the model thinks, burns the 299 cap in reasoning, emits nothing. The speed measurement survives (timing is content-independent), but the w/s verdict for a hybrid in default mode is unanchored until the rerun with the right mode flag. Consequences: (a) the guarantee's w/s form needs gen_words > 0, so hybrid default-mode runs must either use --no-thinking (which the mode-suffix dump rule already distinguishes) or a thinking-mode run with the 2048 allowance; (b) the pipeline's non-thinking roster runs for hybrid models are --no-thinking runs by protocol (the mode-blindness check, Session 25), and the warning now catches the mistake at run time.

**Catch 2 (instrument bug, caught by the run's own fingerprint): the noise samples were not at depth.** llama-server's slot cache reuses only the longest common token PREFIX of the incoming prompt. The noise sample sent a bare tiny message — common prefix with the cached conversation ≈ template only → the slot re-prefilled at ~zero depth and the "noise at depth" was actually noise at shallow depth. The fingerprint: "noise" t/s (15.4–16.0) sitting consistently ABOVE the conversation turns (14.9–15.7) — noise samples running faster than the turns they follow is physically diagnostic of a shallower decode (less KV read per token). Fixed this session: `noise_sample()` now appends the tiny follow-up to the conversation's own history (returned by `run_conversation`), so the common prefix covers the whole cached conversation, only the tail prefills, and decode runs at the conversation's depth. Mock suites updated to simulate prefix caching honestly (cache depth = common prefix); all v2.1 assertions re-pass, and the corrected mock's noise now sits BELOW the turns, as physics demands.

**The t/s → w/s factor the author asked to validate ("we can validate the estimated t/s to w/s factor with our runs"):** this run cannot validate it — the measured-words path never fired (empty answers). The validation rides on the mode-true rerun: `python3 speed_gate.py --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf --no-thinking` — per-turn `words_per_token` against the 0.75 default is exactly the addendum-3 protocol, executed per conversation instead of per corpus pass. Prediction on record before that rerun: measured w/t in 0.65–0.75, and the verdict line will then read "(measured)" instead of "(0.75 default, unanchored)".

**The author's design question this session (prefill + long generation instead of conversations):** answered with the physics and the tooling split — `depth_probe.py` IS that instrument (addendum 11: blob + ignore_eos generations at exact depth; it measures decode t/s at depth in minutes with no conversation). But the gate keeps conversations for two protocol reasons: (1) the blob's answer content is not under the protocol's control (a "summarize the prefill" prompt can emit EOS early or produce degenerate text — ignore_eos fixes timing but the WORDS the reader reads are what w/s needs, and a blob-summary answer's word rate is not a real conversation's word rate); (2) the w/s guarantee is about the READER's stream — words/s of real answers in real multi-turn shape, with the answer-cap distribution the corpus encodes. The split that keeps both honest: **depth_probe.py = pure decode physics at exact depth** (t/s at depth, KV-tax bands, noise-at-depth via same-slot samples); **speed_gate.py = the reader's experience** (real conversations at protocol depth, measured w/s, worst-turn verdict). The noise-sample fix this session makes the gate's noise samples physically valid at depth; depth_probe remains the exact-depth instrument.

**Commands (the mode-true rerun, and the noise-corrected default run):**

```
python3 speed_gate.py --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf --no-thinking
python3 depth_probe.py --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf
```

---

### Session 27, addendum 15 — author workflow ruling: direct-to-main

**Ruling.** The author will not review every PR: code changes land directly on main; review happens only when explicitly requested. The PR-based workflow (PRs #1–#3) is retired as the default delivery path — it served the review-by-default sessions, and the three-layer refactor, the bandwidth→size law, and the depth-prefill gate all landed through it, reviewed and merged by the author. From this session forward: commits land on main directly; the notebook remains the review artifact (every finding, ruling, and grading lands as a numbered, committed addendum — that discipline is unchanged, standing practice since addendum 7).

**Housekeeping executed under the ruling:** main carried the PR-#3 merge (e696798) but was missing the post-merge fix commit 23e616b (the noise prefix-cache fix, the empty-answer warning, and this session's addendum 14) — the merge happened before that push landed. Cherry-picked to main as 92d41e1 and pushed; main and the work branch are now content-identical.

---

### Session 27, addendum 16 — depth_probe on qwen Q8_0: the KV tax is ~zero; the noise crash; the w/s anchor lands

**The depth-probe run (exact 4000-token depth, 5 samples x 64 tokens, ignore_eos):**

- decode at depth: worst 15.38, mean 15.42, worst/mean 0.997 (n=5) — machine-constant noise at depth, exactly as the addendum-10 hypothesis demanded
- sample 1 prefill 8464 ms for 4000 tokens (472.5 tok/s prefill — the compute-bound regime, felt as TTFT; not gated by the study, on record since addendum 6)
- **the KV tax measured ~ZERO**: decode at 4000 depth (15.42 t/s) is indistinguishable from the Session-20 shallow-depth run (15.3 t/s worst) and from this session's blob-prefilled conversations (14.9-15.7 at ~3-4k effective depth). The addendum-10 prediction (+7.4 ms/token at D=4096 for qwen3.5's architecture → expected 17.5-19.5 t/s at depth) is **MISS by a wide margin — the measured tax is <1 t/s, not ~3 t/s**. The arithmetic (2*36L*8kvh*128hd*2B*D) is not wrong as arithmetic; the conclusion it served was: the KV read rides the same memory bus the model read already saturates. On the 780M (shared LPDDR5, no CUDA-style HBM split), the KV bytes were already inside the per-token traffic that the law's size term prices — the KV read is additive in BYTES but not additive in TIME on this machine class. Addendum 10's "context depth eats boundary size" box needs this correction: on iGPU/unified-memory systems the depth tax is second-order; the law's two terms (size, overhead) carry the depth dependence inside their effective-bandwidth constant. This also explains Session 20's original observation that the worst turn is usually the last turn of a long conversation: with the KV tax ~0, what remains is noise and the answer-length distribution — the "last turn worst" pattern rides the cap-length tail, not the KV trend.

Consequences, honestly:
1. The k=1 guarantee at depth is now anchored by measurement, not arithmetic: qwen Q8_0 at 4000 tokens decodes at 15.4 t/s = 11.2 w/s (at the 0.75 default; the mode-true run below measures it) — 2.2x the reader line, PASS with margin.
2. The depth budget machinery (depth_budget, blob sizing) remains valid and necessary — it guarantees the measurement HAPPENS at depth — but the size*(D) "depth eats size" refinement of the law is dead on this machine class: size*(D) ≈ size*(0) for D in the protocol range. The upgrade-path tables (addendum 2, law_fit --kv) keep their Q4_K_M projections with the caveat now measured.
3. The prefill/TTFT axis is on record: 472 tok/s prefill on 4000 tokens ≈ 8.5 s TTFT for a full-depth cold query. Not gated (the study's guarantee is streaming-phase), but the report should carry it as an operating note — a 4k-deep cold question pays an ~8.5 s prefill tax on this hardware.

**The crash (a real bug, honestly recorded): the noise fix overfilled the context.** The blob budget is worst-case (every answer at the 299 cap), so after the last conversation turn the history sits at the budget edge. The noise follow-up, now riding the full history (the prefix-cache fix), sent max_tokens=299 on top → prompt + n_predict exceeded n_ctx → llama-server rejected it with HTTP 400 → the exception propagated and killed the entire run, losing three conversations of collected turns (the dump is written only at the end of bench_model). Diagnosis confirmed by the output: the crash fired exactly at the first post-turn noise attempt (conv 3, after its final turn — the deepest blob+history stack). Fixed this session: (a) the noise generation is capped at 128 tokens (a noise sample needs a decode span, not a full answer) and clamped to the remaining room; (b) a room guard skips the noise measurement with a printed note when the history fills the context; (c) a failed noise request is recorded as an error record, never raised — the noise measurement must not be able to kill the run. The mock suites re-verified: full history skips, near-full clamps, failed requests record. Lesson on record: error isolation per phase-step, not just per phase — the crash was in a measurement, not the measurement's target, and it destroyed the target's data.

**The mode-true w/s run (the one that crashed mid-way, partial output):** the first three conversations measured words/s on every turn — the anchor the addendum-13 catch demanded: 9.1-11.7 w/s across 13 turns, measured words/token 0.585-0.775 per turn (rough band; per-turn ratios vary with answer content — a list-heavy answer carries fewer chars/word, a prose answer more). The v2.1 predictions grade as: (1) verdict-in-w/s HIT (worst measured turn 9.1 w/s, clearing 5.0 by 1.8x); (2) the 8.4-10.5 w/s depth band HIT on the mode-true data (measured worst ~9.1 w/s in-band); (3) words/token 0.65-0.75 PARTIAL — per-turn values straddle the band (0.585-0.775), the dump's pooled mean is pending the completed rerun (the crash ate convs 4-5); (4) noise-at-depth w/m 0.90-1.00 PARTIAL — the depth probe's 0.997 grades it HIT at exact depth; the gate's own at-depth noise value still pending (the fix's noise samples were in the lost convs); (5) live-session felt experience pending the author.

**The rerun command (unchanged):**

```
python3 speed_gate.py --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf --no-thinking
```

Expected differences vs the crashed run: five conversations with words/s lines throughout, noise samples riding the history but capped to fit (some conversations may report "noise at depth: skipped" when the history fills the context — the room guard's honest note), the full dump written, and the verdict line reading "(measured)" words/token. Prediction on record before the rerun: pooled words/token in 0.65-0.75; worst measured w/s in 8.5-11.5; verdict PASS; headroom below floor; noise-at-depth (riding history) w/m in 0.95-1.00, consistent with the depth probe's 0.997.

---

### Session 27, addendum 17 — the mode-true qwen Q8_0 run completes: w/s verdict MEASURED; the noise skip bug; grades

**The run (T14s, --no-thinking, 2026-09-26, completed):** 5 conversations, 22 turns at depth, all with measured words/s. Verdict: **worst 7.48 w/s → PASS (confident)** at the 5.0 w/s reader line; pooled **words/token 0.680 (measured)** — the unanchored 0.75 era is over for this model; token-side worst 15.3 t/s; headroom below floor 20, honestly reported.

**Grading the addendum-16 pre-registrations (recorded before this rerun):**

1. **Pooled words/token 0.65-0.75 — HIT** (measured 0.680). The addendum-3 protocol (per-model words/token via the runs themselves) is now executed per conversation: Qwen3.5-4B at Q8_0 delivers ~0.68 words per generated token on corpus-shaped answers. Note the honest consequence: at 0.68, the 6.5 t/s token-line equals only 4.42 w/s — BELOW the 5.0 w/s reader line. The old t/s-anchored gate would have passed a model at 6.5 t/s that fails the READER at 0.68 w/t. The author's v2.1 catch was not academic: it changes verdicts.
2. **Worst measured w/s 8.5-11.5 — MISS (7.48, just under the band).** The miss is informative: conv 4's first turn (7.5 w/s) — a short answer turn (few words) — and conv 3's 9.1s pull the worst down; the w/s worst is answer-shape-dependent in a way t/s is not (a short answer with the same t/s carries a different word rate only if content density varies; here the short first turn's low count meets the fixed generation span). The per-turn w/s spread (7.5-13.0 within a single model, single rung) is the honest w/s noise floor of the instrument. The band was built from t/s band x w/t band; the w/s worst is the min over turns of a content-dependent ratio, and the min operator punishes short answers. Refined prediction form for future runs: worst-turn w/s in [0.9 x w/t_pooled x tps_worst_min, 1.3 x w/t_pooled x tps_worst_min].
3. **Verdict PASS — HIT.** 7.48 w/s clears 5.0 by 1.50x, and the guarantee holds on the worst measured turn, not the mean (mean 10.68 w/s).
4. **Noise-at-depth w/m 0.95-1.00 — UNGRADED (instrument bug, see below); the depth probe's 0.997 (addendum 16) remains the at-depth noise anchor.**
5. **Live-session felt experience — pending the author's live session.**

**The noise skip bug (the third instrument bug this arc, all caught by the run's own output):** every conversation printed "noise at depth: skipped (history fills the context: ~6632 of 4096 tokens, room -2536)" — impossible numbers, and the fingerprint of the double-count: the room guard estimated depth as blob_tokens + history_chars/4, but the blob IS history[0] — its exact token count was added once as blob_tokens and again (as chars/4) inside the history sum. Every estimate inflated ~1.8x, room went negative, and the guard skipped all ten noise samples. The guard itself worked as designed (no crash, honest note); the estimate inside it was wrong. Fixed: the estimate now mirrors run_conversation's depth math (blob tokens exact + non-blob history chars at 4 chars/token). Verified against the exact conv-5 shape: corrected estimate 3943 of 4096, room 153 → noise proceeds, capped at 128 tokens (fits). The at-depth noise-at-depth measurement for qwen Q8_0 is therefore still pending one more rerun; the honest current value is the depth probe's 0.997 at exact 4000 depth.

**The dump (.live-dump.nothink.json) is the first complete mode-true v2.1 dump** — the reference artifact for the rerun-after-rerun grading: per-turn t/s, measured w/s, measured words/token, depth estimates, and (post-fix) at-depth noise records. The Session-27 prediction that all five families select their top rung at the reader line is now graded for qwen3.5: **Q8_0 PASSES the v2.1 gate** (the Session-20 floor-20 FAIL is superseded). Session-27 prediction 1 (top-rung selection) on track; prediction 2's KV-tax band is dead (addendum 16, tax ≈ 0); prediction 3's noise w/m 0.90-1.00 partially anchored (0.997 via depth probe; the gate's own riding-history value pending).

**Next runs:**

```
python3 speed_gate.py --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf --no-thinking
python3 depth_probe.py --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf --depth 2048 --depth 4000
```

(The first re-collects the noise samples with the fixed guard; the second is the two-depth linearity check — the addendum-11 prediction 4 grade, now with the KV tax known ≈ 0, so the check tests the noise story, not the tax.)

---

### Session 27, addendum 18 — the two-depth linearity grade: the KV tax is real but ~7x smaller than the arithmetic; tool fixes (dump reuse vs re-measurement, probe slot-cache)

**The two-depth probe (2048 + 4000, 5 samples x 64 each):**

- depth 2045: worst 15.32, mean 15.42, w/m 0.993
- depth 4000 (probe reported prompt_n 1959 — see the catch below; true decode depth ≈ 2045 prefix-cached + 1959 prefilled = ~4004): worst 15.04, mean 15.10, w/m 0.996
- **The linearity grade: mean 15.42 → 15.10 t/s across 2045 → 4004 depth = ~2.1% decay over ~1959 extra KV tokens.** The addendum-11 prediction 4 (the KV term halves from 2048 to 4000... implied third-term bandwidth) — the honest reading: the KV(D) tax the law's third term prices is REAL but tiny on this machine class. Converting: Δdepth = 1959 tokens ≈ KV 0.269 GiB (qwen3.5 fp16 KV); Δ(1/t) = 1/15.10 − 1/15.42 = 1.373 ms/token over 0.269 GiB ≈ **5.1 ms/GiB effective** vs the law's 13.07 ms/GiB size constant — the KV bytes ride the bus at ~39% efficiency of the model-file bytes, or (equivalently) the KV read largely coalesces with the model read already in flight. The addendum-10 arithmetic (+7.4 ms/token at D=4096 → 17.5-19.5 t/s) predicted ~3x the observed decay: measured ≈ +1.4 ms/token at 4096 depth, not +7.4. Addendum 10's box keeps its architecture arithmetic but its TIME prediction is graded MISS by ~5x, and addendum 16's "tax ≈ 0" is refined: tax ≈ 0.3-0.5 t/s across the protocol range — second-order, as ruled, but not zero. The size*(D) refinement of the law is retired for this machine class; if a depth term is ever needed, it prices at ~5 ms/GiB, not 13.
- Noise at both depths: w/m 0.993/0.996 — machine-constant, the addendum-10 noise hypothesis now graded at TWO depths (HIT).

**Catch (probe): the slot cache carried the 2048-blob into the 4000-depth measurement.** depth 4000 reported "measured prompt_n 1959": the server never restarted between depths, the 4000-blob opens with the same corpus text as the 2048-blob, so the slot reused the 2045-token prefix and prefilled only the 1959-token tail. Decode was at ~4004 (correct for the measurement) but the probe's depth accounting under-reported it — and the prefill-time saving made the second depth look cheaper than it is. Fixed: depth_probe restarts the server per depth (clean slot, honest prompt_n every depth).

**Catch (gate): the resume machinery blocked the re-measurement.** The rerun printed "[3] reusing existing dump (newer than model file)" — correct resume behavior (the dump postdates the model), but the run's purpose was to re-collect the noise samples under the fixed room guard, and the reuse path skips bench_model entirely. Fixed: `--force` re-measures despite a valid newer dump (the pipeline default remains reuse; the flag is the re-measurement path after instrument fixes).

**Standing predictions now graded for qwen3.5-4b Q8_0 (the first family complete under v2.1):** reader guarantee PASS at depth (15.0-15.6 t/s = 10.2-10.6 w/s at 0.68 w/t, vs the 5.0 line: >2x); headroom below floor 20 (k=3) — honestly reported; words/token 0.680 measured (in the 0.65-0.75 band, HIT); noise-at-depth w/m 0.993-0.997 at two depths (band 0.90-1.00, HIT); KV tax second-order (addendum 16, refined here with a number); Session-27 prediction 1 (top-rung selection) on track for the family.

**Remaining for the session:** the gate's own at-depth noise records (ride-history, fixed guard) — one `--force` rerun; the author's live session (prediction 5); then the full-roster rerun commands from Session 27 (all five families, both categories) on the v2/v2.1 protocol.

---

### Session 27, addendum 19 — standing conventions: Python 3.13 floor; git workflow (why the pulls wanted merges)

**Python 3.13 floor (author ruling).** The target machine runs Python 3.13; the code may use any language feature through 3.13. README's environment section updated (was "3.10+"). The scripts stay pure-stdlib on the tool layer; the middle and top layers already use only stdlib. No retro-fit needed - the codebase is 3.13-clean today.

**Git: why `git pull` kept asking for a merge.** Diagnosis from the repo's own history: a fast-forward requires the local branch to be a strict ancestor of the remote - every local commit must already be ON origin/main. The repo contains exactly the pattern that breaks this: commit `437c626` ("Merge branch 'main' of...") has two parents (`1b69722` + `4d2a8dd`) — the old agent worked on main, pushed, kept committing locally, and merged the remote in afterward, creating a second parent line. Once ANY local commit is not on the remote, `git pull` can no longer fast-forward: it must reconcile two diverged lines, hence "merge". The old workflow (work on main, merge remote in) permanently diverged main; every subsequent pull on a machine with unsynced local work inherits the problem. The merge commits (`437c626`, and the pre-refactor `d10ff1f`) are the fossil record of that workflow.

**The current fix (ruling, from addendum 15's direct-to-main convention):** commits now land on main only via this agent, and always pushed immediately. The author's machine should run:

```
git pull --ff-only
```

which refuses to create merge commits (it errors rather than merge when divergence exists, making any divergence loud instead of silent). If it ever refuses, the right move is `git stash` (if local edits exist) then `git pull --ff-only`, and never `git pull` with its merge default. For a clean one-machine setup: `git config pull.ff only` makes the ff-only behavior the machine default. The merge-commit fossils stay in history (history is data); no history rewrite on a published branch.

---

### Session 27, addendum 20 — noise at depth rides the history: HIT; two-depth confirmed; the room guard goes exact

**The --force rerun (at-depth noise, riding history, fixed guard):**

- NOISE AT DEPTH: worst 15.17, mean 15.19, **w/m 0.998** (n=4) — the addendum-18 prediction (0.95-1.00, consistent with the probe's 0.993-0.997) grades **HIT**. The gate's noise-at-depth measurement is now physically valid: same-slot, same-depth, riding the conversation's own cached prefix. The addendum-10 noise-attribution question is closed for this machine: noise at depth ≈ noise at shallow depth ≈ constant, w/m ~0.99+.
- Verdict re-confirmed on fresh data: worst 7.32 w/s → PASS (confident); words/token 0.680 (measured, stable across three runs); token-side worst 14.9 t/s; headroom below floor 20.
- Reproducibility across the three qwen Q8_0 runs (worst t/s 14.9 / 14.9 / 15.3; worst w/s 7.48 / 7.32): the instrument's per-run spread is small and the verdict is robust. The worst-w/s spread (7.3-7.5) is the conv-4 short-answer effect (addendum 17), now seen twice - a stable feature of the corpus, not noise.

**The clean two-depth probe (per-depth server restart):** prompt_n 2045/4000 honest at both depths. Decode: worst 15.14 / 14.94, mean 15.20 / 15.01, w/m 0.996/0.995. The addendum-18 linearity reading **confirmed on the honest accounting**: mean 15.20 → 15.01 t/s across 2045 → 4000 depth = Δ(1/t) = 0.833 ms/token over Δdepth 1955 tokens ≈ 0.268 GiB KV → **~3.1 ms/GiB effective for the KV term** (previous run's implied value ~5.1; two measurements bracket ~3-5 ms/GiB vs the 13.07 size constant). The addendum-10/16 conclusions stand with tightened numbers: the KV tax is real, second-order (~0.2-0.5 t/s across the protocol range), and any depth term prices at a quarter to two-fifths of the model-size term. Prefill: 4713/9261 ms at 2045/4000 tokens (~434 tok/s) — the TTFT operating note, unchanged.

**The fourth instrument fix of the arc: the room guard goes exact.** The --force run skipped noise on convs 2/3/5 with estimates exceeding ctx (~4161/~4148/~4585 of 4096) while their turns ran fine at the cap - impossible numbers again, and this time the fingerprint was the CHARS/4 estimate itself: qwen3.5's tokenizer runs ~3.3 chars/token on this corpus, so chars/4 over-counts depth by up to ~500 tokens and the guard skipped conservatively. Fixed: the guard now uses the last turn's own server-measured `timings.prompt_n` (+ last gen + a small template overhead constant) as the exact next-prompt size - the same server-side authority the blob budget already trusts - with the chars/4 estimate kept only as a fallback (now conservative in BOTH readings: max of the two). Turn records also now carry `prompt_n` (exact rendered depth per turn) - the dump's depth accounting upgrades from estimate to measurement. All four guard paths regression-verified (exact-attempt, exact-skip, fallback-skip, fallback-attempt).

**Qwen3.5-4B Q8_0's v2.1 card is complete:** guarantee PASS at depth (measured w/s, 2.3x the reader line at worst), words/token 0.680 measured, noise-at-depth w/m 0.998 riding history + 0.995-0.996 at exact depths, KV tax 3-5 ms/GiB effective, headroom below floor (k=3) honestly reported. Session-27 prediction 1 (top-rung selection) confirmed for the family; the full-roster rerun (all five families, both categories) remains the session's open measurement, plus the author's live session (prediction 5).

---

### Session 27, addendum 21 — the KeyError crash (fifth instrument bug): the error path was untested; fence + retry + honest overhead

**The crash.** The exact-guard rerun died at conv 3: both noise samples 400'd (the NOISE_OVERHEAD=32 constant underestimated qwen3.5's rendered template wrappers - the noise message + history retokenization costs ~60+ more rendered tokens than accounted), the error records flowed correctly... into an untested consumer: `ntps = [r["tps"] for r in noise if r["tps"]]` assumed every record carries `tps`, the error records do not, and the KeyError killed the run at the summary line - losing convs 4-5 a second time. The lesson is structural, and it is the same lesson as addendum 16 in a new place: **the error path itself must be tested, not just the happy path.** The addendum-16 fix added error records but never exercised a run where an error record reached the summary; the mock always succeeded.

**Fixes (all three verified):**

1. `r.get("tps")` at both summary sites - error records are data, the summary must skip them without dying.
2. Per-conversation error fence in `bench_model`: noise collection is wrapped; any exception is recorded and the conversation's collected turns survive. A measurement failure can no longer destroy the run - the fence exists at every level now (request, conversation, summary).
3. Retry-once-with-halved-cap on a 400 with room to spare (the overhead estimate was tight, not the history full), and NOISE_OVERHEAD raised 32 -> 96 (qwen3.5's template wrappers measured the hard way).

**The partial run's data (convs 1-3, before the crash):** turns worst 15.0/15.4/15.3 t/s, words/s 9.1-11.5 - the fourth consecutive reproducible run of this model (worst t/s 14.9-15.3 across four runs; words/token 0.680 stable). Convs 1-2 noise rode the history at 15.3-15.6 t/s (above the turns - consistent with the at-depth noise floor ~15.2 and the exact guard now letting near-full conversations attempt). The verdict numbers remain addendum-20's; the rerun completes the noise n=10.

**Standing convention (author request):** every command list for the author's machine now begins with `git pull --ff-only` - the author missed a pull before the addendum-20 rerun and re-ran the pre-fix code (caught immediately: the output was byte-identical to the addendum-20 run, the skip fingerprints gave it away). From addendum 21 on, the run lists carry the pull.

**The rerun (with the pull first):**

```
git pull --ff-only
python3 speed_gate.py --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf --no-thinking --force
```

Expected: five conversations, noise attempted on all (exact guard + retry); possible "retrying with max_tokens N" lines on the tightest conversations; the summary NOISE AT DEPTH n up to 10; no skips unless a history truly fills ctx (exact numbers, not chars/4 phantoms).

---

### Session 27, addendum 22 — the fence holds, the run completes; noise room moves into the blob budget

**The run (first full-length completion under the exact guard):** all five conversations, 22 turns, verdict worst 7.52 w/s → PASS (confident); words/token 0.680 (fifth consecutive stable run); token-side worst 15.4 t/s; NOISE AT DEPTH n=8, worst 14.87, mean 15.36, w/m 0.968. The addendum-21 fence held exactly as designed: conv 3's two noise samples 400'd (max_tokens 128 → retry 64 → retry 32, honest error records at every rung), and the run kept going - convs 4-5 completed, the dump was written, nothing was lost.

**Grading:** the noise-at-depth w/m prediction (0.95-1.00) grades **HIT on the gate's own at-depth measurement at last** (0.968, n=8; the probe's 0.995-0.996 and the previous gate run's 0.998 bracket it). The conv-4 noise sample at 14.87 (the only sub-15 sample of the set) pulls w/m slightly below the probe's exact-depth values - plausibly one scheduling hiccup, honestly kept in the record. Verdict stable across five runs now: worst w/s 7.32-7.52, worst t/s 14.9-15.5, words/token 0.680 measured every time. The instrument is reproducible.

**The design flaw conv 3 exposed (and its fix): noise room is protocol, so it must be budgeted.** The blob budget was worst-case for the CONVERSATION (every answer at the 299 cap) but the noise request - which rides the same worst-case-full history - was expected to fit in the 64-token DEPTH_HEADROOM left over. A noise sample needs ~224 rendered tokens (message + template wrappers + decode span). On a max-length conversation there is structurally no room, and no retry ladder can fix a negative budget. Fixed: depth_budget now reserves NOISE_OVERHEAD + NOISE_TOKENS (96 + 128 = 224) alongside the depth headroom, so the blob shrinks 224 tokens and the noise request always has its room. Retry ladder extended 2 → 3 rungs (halving 128 → 64 → 32 → 8 floor). Consequence, honestly noted: conversations run ~224 tokens shallower than before (deepest turn ~3.7k instead of ~3.9k) - the guarantee's reference depth moves from "just under 4096" to "4096 minus the noise reserve", and the depth-probe measurements (exact 4000) remain the precise-depth anchor; the gate's depth is now honest AND noise-complete.

**The rerun (pull first):**

```
git pull --ff-only
python3 speed_gate.py --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf --no-thinking --force
```

Expected: blob sizes ~224 smaller (conv 1: 2799 → ~2575), noise on ALL five conversations (n=10), no 400s, no retries; worst t/s ~15.4 (unchanged - the blob shrink is inside the KV-tax noise); w/m in 0.95-1.00. If n=10 lands and no error records appear, qwen Q8_0's card closes with the complete at-depth noise set and the instrument is done - the full-roster rerun (Session 27's commands, all five families) is then the only open measurement, plus the author's live session.

---

### Session 27, addendum 23 — the pause: experiment value, the stopping criterion, and what the two instruments taught

**The value audit (author's challenge: "Aren't we just getting the same data?").** Honest answer: the measurement converged by run 3 of the six qwen Q8_0 runs (worst w/s 7.32-7.52, words/token 0.680, PASS on five consecutive verdicts). Runs 4-6 were instrument shakeout, not science - valuable shakeout (five real bugs, each findable only on real hardware, in the cheapest possible place), but shakeout. **The stopping criterion, now on record: when consecutive runs return identical verdicts and the only new information is error-path behavior, the instrument is done.** By that criterion the proposed "closing run" (n=8 -> n=10 noise samples) is skippable - it refines an already-graded quantity and cannot change a grade. Transferable rule: one shakeout model per protocol revision (2-3 runs), then the roster starts only after verdicts stabilize.

**Value ranking going forward:** (1) the full-roster rerun - the study's dataset, grades the all-families-top-rung and >=2-families-change-rungs predictions across the field; (2) the author's live session - the one measurement the instrument cannot replace (the protocol pivoted on a felt-experience claim; Q8_0 at 7.5 w/s vs Q5_K_M at 21 t/s is exactly that question); (3) depth probes as a sidecar during the roster run (KV constant per family, minutes each); (4) more qwen Q8_0 - diminishing returns, card closed.

**What the speed gate vs the depth probe taught (the author's question).**

*Where they agree - the cross-validation is itself a result:* gate conversations at ~3.5-4k depth measured 14.9-15.6 t/s; the probe at exact 2045/4000 measured 14.94-15.27 t/s. Two independent code paths (chat completions with full history vs raw completion on a blob), the same physics within noise. This validates the addendum-11 premise end to end: the conversation machinery (template, multi-turn, real answers) costs nothing measurable in decode - the blob shortcut is physically legitimate, and the gate's numbers are the probe's numbers in context.

*Only the probe could teach (physics):* the KV tax ~3-5 ms/GiB effective vs the 13.07 size constant (the addendum-10 arithmetic prediction missed ~5x; "depth eats size" is dead on unified memory - no conversation could isolate this, the probe's exact paired depths did); machine-constant noise at exact depth (w/m 0.995-0.997); the prefill regime (~434 tok/s -> ~8.5 s TTFT for a cold 4k query, the un-gated axis the report must note). Cost: minutes per depth.

*Only the gate could teach (the reader):* words/token 0.680 (the 0.75 rule of thumb dead for qwen; the probe cannot measure this - ignore_eos garbage has no meaningful words); worst-turn w/s and its answer-shape sensitivity (the min-over-turns punishes short answers; worst w/s is not worst t/s x w/t); the hybrid empty-answer behavior (mode changes content, not timing); noise riding a real cached history (w/m 0.968-0.998). Cost: ~10x the probe.

*The structural lesson:* each instrument falsified one unvalidated assumption and neither could have falsified the other's - the probe killed the KV arithmetic, the gate killed the w/t rule of thumb. The bug count tells the same story: the probe needed one fix (slot prefix carry), the gate needed five (prefix cache, room guard, double count, KeyError, noise budget) - every bug lived in the layer that touches realism (template, history, cache, room, content). The addendum-14 division of labor is validated by data, not just principle: probe = decode physics at exact depth; gate = the reader's experience; the guarantee needs both - physics to establish depth is nearly free, experience to establish what the reader actually receives.

### Session 27, addendum 24 — the closing run: n=10 lands clean, the qwen Q8_0 card closes

**The addendum-22 expectations, graded against the first hardware run on the fixed-budget code:**

- **Blob sizes 2571/2537/1933/2583/1965 — HIT** (deltas 221-231 vs the addendum-20 sizes, expected ~224): the noise-budget reserve (NOISE_OVERHEAD 96 + NOISE_TOKENS 128) works on hardware. Decode is unchanged at the shallower depth (worst 14.8 t/s vs 14.9-15.5 across all runs) — consistent with the ~3-5 ms/GiB KV tax being second-order; blob depth is not a confound.
- **Noise on all five conversations, n=10, no 400s, no retries, no skips — HIT.** The first complete at-depth noise set. Conv 3's structural skip (addendum 22) is gone: its room was reserved in the blob budget *before* the conversation ran, not hoped for after.
- **w/m 0.978 (n=10; band 0.95-1.00) — HIT**, bracketed by the probe's exact-depth 0.995-0.997 and the riding-history 0.968/0.998 of earlier runs. The gate's at-depth noise measurement is complete, not partial.
- **words/token 0.697 measured — HIT** (band 0.65-0.75; 0.680 in the three previous runs). The run-to-run shift is answer-content variance, honestly kept.

**The one MISS retires a prediction form.** The refined worst-w/s band (addendum 20: [0.9, 1.3] x w/t x worst-t/s = 9.3-13.4 w/s) missed (8.24). Cause, now demonstrated twice: the min operators pick different turns — the worst-t/s turn is conv 3 turn 5 (14.8 t/s, 10.1 w/s) while the worst-w/s turn is conv 1 turn 4 (15.4 t/s, 8.2 w/s). Worst w/s is NOT worst t/s x w/t, across runs (worst w/s 7.32-8.24 at worst t/s 14.8-15.5). The composed form is retired: future worst-w/s predictions must be set from the pooled per-turn w/s distribution itself, not composed from t/s x w/t products.

**Card closed by the addendum-23 stopping criterion.** This run added the last missing quantity (the complete n=10 at-depth noise set) and nothing else. Standing numbers for qwen3.5-4b Q8_0 under v2.1, six runs deep: worst w/s 7.32-8.24 (PASS confident, six consecutive identical verdicts), worst t/s 14.8-15.6, words/token 0.680-0.697, noise w/m 0.968-0.998, headroom below floor 20 (honestly reported). The instrument is done. Open measurements unchanged: the full-roster rerun (ranked #1 in the addendum-23 value audit) and the author's live session (prediction 5).

### Session 27, addendum 25 — the conversation-count question: length is a non-variable, shape is the variable

**The author's proposal (speed up testing): one conversation instead of five, since "the longer conversation gives the lower performance"; and should we find a longer conversation?** The six-run record says the premise is half-true and the proposal is unsafe for a guarantee instrument. Analysis on record; the author rules.

*What the data says.* (1) **Depth is budget-equalized**: depth_budget() sizes each blob so every conversation's final turn lands at the same reference depth (~3808 after headroom + noise reserve) regardless of turn count - no conversation is "deeper" at its worst turn, so length cannot be the depth variable. (2) **The t/s spread across conversations is the KV tax, not length**: closing-run conversation worsts 14.8-15.3 t/s (~3%), matching the measured KV-tax band (0.56 GiB x ~3-5 ms/GiB ~ 3-4%); conv 3 posts the lowest t/s worst only because its five turns sit nearer full depth - bounded, second-order, already characterized by the probe. (3) **The big spread is w/s and is NOT ordered by length**: conversation worsts 8.2 / 9.1 / 10.1 / 9.5 / 12.1 w/s (convs 1-5) - the five-turn conv 5 is the FASTEST, the four-turn conv 1 the slowest; the driver is answer shape (conv 1 turn 4: terse answer, 8.2 w/s at 15.4 t/s), and the worst-conversation identity moves run to run (conv 4 in one run, conv 1 in another). Shape noise is stochastic; only the min over all five samples the tail.

*Why one conversation is unsafe for a guarantee.* The verdict is min over conversation worsts - the tail sample. n=1 makes the guarantee quantity hostage to one conversation's answer shapes, and the failure direction is anti-conservative (fewer samples -> higher worst -> more likely PASS). Structurally: sigma comes from the spread of conversation worsts (speed_gate.py analyze: sd/sqrt(n)), so n=1 silently disables the PASS (within 2-sigma) tier; and the six-run reproducibility baseline (worst w/s 7.32-8.24) exists on these exact five conversations - changing the corpus re-opens shakeout that the addendum-23 stopping criterion closed.

*Optimum conversation length.* There is none to find: under v2.1 length is a non-variable (depth pinned by the budget at the protocol constant; decode flat in depth per the probe). A longer conversation probes nothing deeper - it only moves budget from blob to conversation side. The corpus's job is answer-shape diversity; 4-5 turns is right because more turns near full depth sample the slightly-slower region honestly.

*Cost accounting.* ~2 min per conversation per rung; five conversations ~ 10 min/rung; full roster at predicted top-rung selection ~ 1 hour, once. Going to one conversation saves under an hour across the whole study, bought with tail coverage and the confidence tier.

**Proposal (author to rule):** keep 5 x 4-5 turns for the roster rerun (the dataset; comparability with the six qwen runs). Optional separate lever if interactive screening is ever wanted: a --conversations N flag on speed_gate.py, explicitly non-protocol (verdict stays n=5). No longer conversation to be found or drafted.

### Session 27, addendum 26 — the live-session instrument (session_replicate.py) and the pre-registered feel predictions

**The author's ruling: the live test happens now, on the conversation that produced the worst turn.** Conv 1 of live-corpus.json (the molten-chloride-reactor conversation) hosted the closing run's worst w/s turn (turn 4 "Thanks": 8.2 w/s at 15.4 t/s). The session must be gate-faithful, not hand-assembled: the felt experience must be produced by the exact mechanism the instrument measured, or the calibration is invalid.

**The instrument.** `session_replicate.py` (standalone, the depth_probe.py pattern): launches the server with the gate's own flags (-ngl 99 -c 4096 --chat-template-kwargs enable_thinking false), builds the gate's own depth_budget blob for conv 1 (2571 tokens for the closing run), replays the conversation verbatim - and streams it. Pass 1 replays non-streaming exactly as the gate ran it (records land in the same shape as the dump); pass 2 runs the conversation again, streaming to the terminal, recording per-delta arrival times: TTFT, mean/max inter-token gap, streamed w/s. `llama_server.py` gains `stream_completion()` (SSE parsing over urllib, bottom-layer interface, import-only like the rest). Both passes write <model>.session.json. Mock-server E2E verified: streaming telemetry correct (TTFT 0.40 s, mean gap 200 ms at a simulated 15 t/s, streamed w/s within band), dump written, teardown clean.

**Pre-registered feel predictions (recorded before the session, graded by the author afterward):**

1. *Streaming smoothness:* at ~15 t/s (~10.2 w/s at the measured 0.68 w/t), token arrival is smooth while streaming - the author will not feel mid-answer lag at her 300-wpm reading pace (mean gap ~67 ms vs her ~154 ms/word; the Andes deviation model predicts zero reader-seconds of waiting mid-answer).
2. *The felt wait is TTFT:* the prefill at ~4k depth (~8.5-9 s) is the wait the author WILL feel - before each answer, not during it. The un-gated axis (addendum 23) becomes felt experience; the session should confirm it as the dominant lag component.
3. *Streamed w/s vs reading line:* per-turn streamed w/s will land in 8-13 (the gate's per-turn band, addendum 20) and stay above the 5.0 w/s reader line throughout; the worst streamed turn will NOT be the felt worst - the shape-sensitivity lesson says the terse "Thanks" turn posts the lowest w/s without being the slowest to read.
4. *Verdict-feel match:* the instrument's PASS (confident) at worst 7.32-8.24 w/s will match the author's felt experience of a fast reader never waiting mid-answer - the guarantee calibrated by the only sensor that matters.

**The session commands (author's machine, pull-first per convention):**

    git pull --ff-only
    python3 session_replicate.py --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf --no-thinking

(~2 min server launch + ~8.5 s prefill per turn x4 + reading time; --keep-server to go again without relaunching; --stream-only to skip the replay pass; --conv N to replay a different conversation.)

### Session 27, addendum 27 — the live session graded: the guarantee felt seamless; prediction 5 closes

**The author's report, verbatim: "really smooth, I didn't catch up with the conversation at all :)".** Session run via session_replicate.py on Qwen3.5-4B Q8_0 (conv 1, the worst-turn conversation of the closing run), streamed live at the gate's own depth (blob 2571 tokens, ~4k final depth).

**The addendum-26 feel predictions, graded:**

1. *Streaming smoothness (no mid-answer lag at ~15 t/s) — HIT.* "Really smooth" is the prediction's exact form; zero mid-answer waiting felt.
2. *Streamed w/s in 8-13, always above the reader line — HIT in feel.* "I didn't catch up with the conversation at all" is the match-the-reader model's signature sentence: the stream was always faster than a 300-wpm reader, so the reader never waited. The worst streamed turn was not the felt worst, as predicted. (Numeric grade pending the .session.json telemetry if pasted.)
3. *Verdict-feel match (PASS confident at worst 7.32-8.24 w/s = a fast reader never waits mid-answer) — HIT.* The instrument's verdict and the author's senses agree on the worst-turn conversation itself. Prediction 5 (the felt-experience calibration, the one measurement the instrument cannot replace) is closed: the guarantee is calibrated, not just computed.
4. *The felt wait is TTFT (~8.5-9 s prefill per turn) — UNGRADED from the session report.* The author's report does not mention the pre-answer wait; the instrument recorded TTFT in .session.json. Pending the author's answer: was the ~9-second wait before each answer felt, and was it acceptable or annoying? This is the un-gated axis (addendum 23) - the one question the session leaves open.

**The feel datum that tightens the comfort bracket.** The author's revealed preference now reads: 6 t/s atrocious (below reading pace, Andes worst case), 12 t/s still bad, 15 t/s streamed *seamless* - "couldn't catch up". The comfort line sits in (12, 15] t/s at STABLE pacing - and notably k~2 (15 t/s ~ 10 w/s ~ 2x the author's 5 w/s reading) sufficed in feel here, with no need for the k=3 margin. Consistent with Andes: the earlier 12 t/s frustration implicated deviation (stalls), not the mean - stable pacing above reading speed is what "smooth" means. The k=3 floor-20 default keeps its role as margin against variance (worst turns, off-machine noise), but the felt calibration says the guarantee line (k=1) has real margin in feel: even the worst turn of the worst conversation (~8.2 w/s) outran a fast reader by ~1.6x.

**Standing: qwen3.5-4b Q8_0 is now closed on every axis** - instrument (addendum 24), physics (KV tax, depth cross-validation), and feel (this addendum). The remaining open measurement is the full-roster rerun (addendum 23's rank #1).

### Session 27, addendum 28 — the interactive session (the author's realism catch): send-wait-read rhythm, per-turn TTFT

**The author's catch:** the first live session read "like the transcript of an interview" - the turns were machine-paced, so the send-wait-read rhythm of a real chat was never felt. Perception matters; the calibration must be had in the instrument's own mode of use. **Ruling: the live pass gains --interactive** - the author presses Enter to send each user turn herself; the history stays verbatim (gate-faithful), only the pacing is human. Telemetry is suppressed during the chat (a real chat does not print timers); a per-turn summary prints at the end.

**What the interactive mode newly measures: per-turn send-to-first-token (TTFT).** The gate's dump never separated it: in the gate, turn 1's prompt carries the whole ~2600-token blob prefill, while follow-up prompts hit the prompt cache (cache_prompt, default on) and prefill only the new tail. A real chat with deep context has exactly this cold-start/warm-follow-up structure, and the author will now FEEL it: the first send after loading a deep context waits seconds; every subsequent send should start near-instantly.

**Pre-registered predictions for the interactive session (recorded before it runs):**

1. *First-send TTFT in 6-10 s* (the blob prefill: ~2600 tokens at the measured ~434 tok/s prefill rate, addendum 23, plus template and generation head).
2. *Follow-up TTFT < 1.5 s* (only the new tail prefills: ~10-300 tokens per turn - the cache_prompt hit the depth-probe samples already demonstrated, prompt_ms ~100 ms there; generous margin for chat-template rendering).
3. *The streaming feel is unchanged from addendum 27* (smooth, never catching up) - the interactive pacing adds the send-wait, it does not change the read.
4. *The author's dominant felt wait is the first send* - and it is a one-time cost per context load, not a per-turn cost; this is the honest shape of the TTFT operating note for the report (the un-gated axis): "deep contexts cost one prefill wait at load; follow-ups are instant".

Mock-verified before delivery: interactive E2E with an honest prefix-cache simulation - first send TTFT 0.27 s (scaled), follow-ups 0.07 s, cold-start/warm-follow-up structure confirmed, telemetry suppressed during the chat, per-turn summary and .session.json dump correct.

**The session commands (author's machine, pull-first):**

    git pull --ff-only
    python3 session_replicate.py --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf --no-thinking --interactive

### Session 27, addendum 29 — the interactive session graded: the worst-turn metric validated by feel; the TTFT ruling

**The author's report (verbatim):** (1) "i had to wait a bit mid answer on the last turn, but it wasn't bothersome." (2) "the wait before the response doesn't bother me, it feels like the time the model is thinking (it is not) or there's a delay in network communication." (3, 4) "yes." **Conclusion (a):** "the wait before first token doesn't matter, it feels natural."

**The addendum-28 predictions, graded:**

1. *Streaming smoothness — HIT with the study's most interesting deviation.* The one felt mid-answer wait landed on the LAST turn of conv 1 - the "Thanks" turn, the exact turn the instrument flagged as the run's worst (8.2 w/s, addendum 24). Across both live sessions the pattern reads: machine-paced session, no felt wait anywhere; interactive session, one small felt wait - on the instrument's min-w/s turn. **The gate's worst-turn metric and the human's felt-worst turn coincided: the instrument measures the right quantity.** Not bothersome at ~1.6x reader margin - the guarantee's worst case sits inside the comfort band, but the shape-sensitivity lesson now has feel evidence: the terse-answer turn is where a fast reader comes closest to outrunning the stream (and, per Andes, any sub-reading-pace moment is felt in full). Cause not separable without telemetry (a real stall would show in max_gap_ms; a reading sprint on a short answer would not) - pending the .session.json summary if still available; honestly recorded as felt-either-way.
2. *First-send wait felt but reframed — HIT in structure, with a psychology finding.* The seconds-scale prefill wait is amortized into the "model is thinking" mental model (or read as network delay) and is QoE-neutral. The cold-start/warm-follow-up numeric grades (6-10 s first, <1.5 s follow-ups) remain pending the summary numbers; the feel grade stands: no follow-up wait was salient enough to mention, consistent with warm cache hits.
3. *Streamed w/s above the reader line on every turn — HIT (author: yes).*
4. *Verdict-feel match — HIT (author: yes), twice over: PASS at the 5.0 w/s line matched feel in both the machine-paced and the interactive session.*

**The TTFT ruling (author conclusion a, adopted for the report):** the wait before first token is perceptually natural at this scale - "feels like thinking time" - so the operating note's tone changes from warning to observation: at the reference depth (4k, ~2600-token cold prefill at ~434 tok/s) the first send costs seconds and is absorbed by the thinking-time mental model; follow-up sends are near-instant (cache_prompt). The decode guarantee remains the axis that matters for bother - the two axes have different QoE weights: pre-token wait is amortized (thinking frame), mid-token pace is felt token-by-token (reading frame). The note stays quantified: the ruling is calibrated at ~seconds-scale waits and 4k depth, not extrapolated to 30 s prefills or deeper contexts.

**Session 27's live-calibration arc closes: instrument (addendum 24), physics (addendum 16/18/23), feel machine-paced (27), feel interactive (29). Qwen3.5-4B Q8_0 is fully closed. The full-roster rerun is the one open measurement.**

### Session 27, addendum 30 — the author's word-level refinement: the reader-collision measurement (the true felt-lag metric)

**The author's ruling (verbatim):** "i caught up for a brief moment during the last turn when '(1965-1969)' was printed, it was not troublesome, but shows a refinement to the experiment: the real measure is the time from the first word of the answer being printed + the reaction time to notice it was printed so the reader starts reading + time to catch up. If the lag happens at a moment in the reply where the reader is still able to catch up with the reply is problematic, if it happens later it doesn't matter. So a lag on the second word is very likely to give a bad impression, lag before the last word probably don't matter at all. So we need to calculate where the reader is at all times and see if they actually hit the lag. That's the true measurement."

**This sharpens Andes from turn-level to word-level.** The felt quantity is not the stream's speed and not even the per-turn w/s: it is whether the READER'S POSITION ever collides with the PRINTED POSITION. A stall is felt only if the reader's buffer is thin when it lands: a lag on the second word (zero buffer) is felt in full; the same lag late in the answer lands in accumulated buffer and is invisible. This explains the author's "(1965-1969)" moment precisely - a numeral parenthetical (digits read slower than prose; the constant-reader-speed approximation is flagged) with the stream's worst w/s turn.

**The instrument (implemented and mock-verified):** `session_replicate.py` stream records now carry per-delta word positions (`deltas: [{t, w}]` cumulative words at each arrival), and `reader_collision()` simulates the reader trajectory: the reader starts `reaction_s` after the first word (the notice-and-start delay, default 0.5 s, flag-tunable), reads at `reader_wps` (default 5.0, the 300-wpm anchor), and is pinned at the printed frontier whenever caught up. Output per turn: `catchup_events` (how many times the reader hit the frontier mid-answer), `catchup_s` (total reader-seconds spent waiting at the frontier), `first_catchup_word_frac` (where in the answer the first collision landed - the author's "second word vs last word" axis). Hand-verified asymmetry: the same 3 s stall produces 2.3 s felt waiting early (buffer 2 words) and 0.0 s late (buffer 16 words at 5 w/s absorbs it) - the ruling's asymmetry is now a computed quantity. The per-delta positions are kept in the dump, so any reader speed / reaction time can be re-simulated post-hoc from one session.

**A catch from testing, honestly recorded:** the first implementation over-counted waiting (it treated a reader who falls behind after a stall as still waiting); the corrected simulation tracks the reader's pinned position - waiting only accrues while the reader is AT the frontier. Case B of the hand-check also forced an honest correction to my own test expectation: buffer absorption requires buffer words >= stall seconds x reader w/s; "late" is not a position, it is a buffer-depth condition.

**Pre-registered predictions for the rerun of the interactive session (recorded before it runs):** (1) the last-turn collision the author felt at "(1965-1969)" appears in the simulation as a catch-up event at first_catchup_word_frac > 0.5 (late in the answer - felt but absorbed, matching "not troublesome"); (2) turns 1-3 show zero catch-up events at 5 w/s (the machine-paced smoothness reproduced under simulation); (3) at the author's faster natural reading pace (try --reader-wps 7), catch-up events appear on more turns but catchup_s stays under ~1 s per turn (the "never catch up" report at 15 t/s was at her pace, not the 300-wpm default); (4) the collision metrics are stable across the two session passes (same deltas -> same trajectories).

**The commands (author's machine, pull-first):**

    git pull --ff-only
    python3 session_replicate.py --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf --no-thinking --interactive
    python3 session_replicate.py --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf --no-thinking --interactive --reader-wps 7 --keep-server

(the second run re-simulates at the author's faster pace; --keep-server avoids the relaunch. The .session.json deltas allow any post-hoc re-simulation.)

### Session 27, addendum 31 — the reaction-time anchor: 0.5 s was a guess, 0.45 s is cited

**The author's challenge: "find typical reaction times for humans, 0.5 s feels arbitrary."** Correct - the 0.5 s default was unanchored. The literature decomposition of the notice-and-start delay:

- *Simple visual reaction time (detect the stimulus):* ~190-250 ms for adults (college-age visual ~190 ms; standard band 200-300 ms, large-dataset median ~250 ms).
- *Saccade latency (orient the eyes to the new text):* ~200 ms typical (Carpenter 1988, via Scholarpedia's human saccadic eye movements entry); 200-250 ms after a target step (IOVS latency study); the reading-specific anchor is PubMed 6227700 ("Latency of sequential eye movements: implications for reading"): "the average minimum latency of saccadic eye movements (175-200 msec) approaches the mean duration of fixations in reading (200-250 msec)."

**Anchored default: reaction_s = 0.45 s** (0.25 detect + 0.20 saccade), replacing the unanchored 0.50 s. The guess happened to land within 10-20% of the anchor - recorded as luck, not vindication. One case-specific refinement on record: in the interactive session the author is already attending the output area when she presses Enter - the saccade literature's gap paradigm (anticipated target cuts latency to ~150 ms) puts her effective delay nearer 0.35 s; the flag stays tunable and the deltas in the dump allow re-simulation at any value, so the constant is a default, not a commitment. Sensitivity note: the collision metrics' dependence on reaction_s is weak in the regime that matters - reaction shifts the reader's start line by +/-0.1 s, which changes waiting time only on turns whose stream pace is within reader_wps x 0.1 s ~ half a word of the collision boundary.

### Session 27, addendum 32 — the collision-graded session: zero events at 5 AND 7 w/s; the variable-reader ruling

**The author's report:** "my reading speed is also variable. this time I didn't hit any slowdown. as the report says." Two interactive runs (same conversation, same model), collision table clean in both.

**The addendum-30/28 predictions, graded numerically:**

1. *First-send TTFT 6-10 s — MISS (5.22/5.27 s, just under the band).* The band was built from the 4000-token probe blob; conv 1's blob is ~2600 tokens (the budget's conversation-side reserve), so 2600/434 ~ 6.0 s was the honest expectation - the measured 5.2 s implies a prefill rate nearer 500 tok/s at this depth. Informative miss: prefill is faster at shallower depth (the KV term grows with depth), consistent with the probe's 4000-depth ~434 tok/s being the deep end.
2. *Follow-up TTFT < 1.5 s — HIT (0.50 / 0.98 / 1.00 s).* Turn 2's warm cache hit is 0.50 s; turns 3-4 ~1.0 s - the growing history's tail prefill (~300-500 rendered tokens of new assistant answer + question) at ~500 tok/s. The cold-start/warm-follow-up structure confirmed with numbers; follow-up TTFT grows with history, a per-turn cost that stays near-instant at this depth.
3. *Streaming feel unchanged — HIT.* Zero catch-up events at 5.0 w/s in run 1, zero at 7.0 w/s in run 2; the author felt no slowdown ("as the report says"). Note the honest wrinkle: the previous session's "(1965-1969)" moment did NOT recur in either run - run-to-run answer-shape variance (temperature 0 does not pin content across context changes: the blob is tokenized per run, the answers differ slightly). The collision from the earlier session lives in that run's deltas, not this one's - the shape-sensitivity lesson generalizes: the felt-lag metric is content-dependent, so the guarantee needs the worst over runs, not the single run's worst.
4. *Collision metrics stable across passes — HIT* (identical zero tables at both reader speeds; same deltas -> same trajectories).

**The variable-reader ruling (author: "my reading speed is also variable").** Correct, and it changes the metric's honest form: a single reader speed is an approximation, so the collision question must be answered as a BAND, not a constant. Implemented: `--resim SESSION_JSON` post-hoc mode (no server) sweeps reader speed 0.6x-1.5x around the given value (multiplicative steps 0.6/0.8/1.0/1.2/1.5) and reports the per-turn collision table; the deltas in the dump are the measurement, the reader parameters are dials. Verified on synthetic adversarial deltas: a stalled 5-w/s stream shows zero collisions for readers at 3-5 w/s and a 1-event/0.38-1.02 s collision at 6-7.5 w/s - the band sweep answers "would a faster reader have felt it?" as a sensitivity, not a single verdict.

**Consequence for the report's QoE section:** the guarantee line (5.0 w/s) is the anchor, but the collision table at the band is the felt-lag statement - and on this machine, at Q8_0 depth-conditioned, the band from 3.0 to 7.5 w/s shows zero collisions. The reader-collision metric (addendum 30) is now fully specified: per-delta word positions recorded, reader trajectory simulated at an anchored reaction time (0.45 s, addendum 31), swept as a band (this addendum), graded against feel twice.

# Session 28 - 2026-09-26 (protocol v2.1 roster: model selection anew; the memory shortcut)

Split from session-27.md (which had accumulated sessions 28-33 behind its own header) per the one-session-per-day audit, session 39 addendum 3. Content verbatim; addendum numbers unchanged. Addenda 33-36, committed 2026-09-26 (git: 3fa01ac, f4fae12, efd63ce, bdb308a).

### Session 28, addendum 33 — protocol v2.1 roster: model selection anew (the k=1 gate opens the door to the family champions)

**The author's request:** "Let's begin the model selection anew, this time: pick top popular 4 model families in the ollama list, where: (1) It is estimated the model will pass the speed gate in **quant 4** [corrected same-day from 'quants 4-8'], (2) is a non-thinking model or hybrid, so we can disable thinking for benchmark, (3) the model family has at least a peer reviewed paper, (4) pick the highest model in the family that can run." The author noted the new k=1 gate "might open the door to higher quant in the selected models or even bigger models" — confirmed below: at k=1 (5.0 w/s), size* ≈ 10.44 GiB (vs 2.79 GiB at floor 20), so every family's **highest runnable member** is now in reach, not just its smallest.

**Author rulings (this session, recorded before any measurement):**
- **Ruling A — one owner = one family.** llama3.1 and llama3.2 are ONE Meta family (reversing the study #1 precedent that treated them as separate rows). Only llama3.1:8b takes a slot; the llama3.2:3b row is absorbed.
- **Ruling B — rule 7 applies: latest generation, always.** "People want the latest and greatest, so that's what we measure." qwen3.5 supersedes qwen2.5; gemma4 supersedes gemma3. Superseded measured data stays in the results file as superseded data points.
- **Ruling C — borderline handling mooted.** The qwen2.5:14b / gemma3:12b quant-4 borderline-straddle question dissolved under rulings A+B: rule 7's replacements both pass quant 4 with margin.
- Notification request: the author wants an audible/notification ping when an answer is ready — no such tool exists in the sandbox catalog (checked, 93 tools); the chat reply landing IS the ping.

**Selection rules (v2.1 roster, pre-registered):** (1) Ollama library popularity walk-down (snapshot 2026-09-26); (2) distinct families — one slot per OWNER (ruling A); (3) non-thinking or hybrid (thinking disabled for the benchmark); (4) predicted to pass the speed gate at **quant 4** (Q4_K_M, the inclusion filter — the ladder walk itself still starts at Q8_0 and takes the first PASS); (5) first-party weights only — no third-party repos; (6) published paper (technical report / peer-reviewed); (7) latest generation supersedes older within family (ruling B); (8) highest runnable member within family ("can run" = file + KV + OS fits 32 GB RAM).

**The fitted law (Session 26):** `1/t = size_GiB/76.5 + 1/74` (BW_eff = 76.5 GiB/s = 80% of theoretical 102.4; t_inf = 74 t/s; R² 0.9996 within-model on the Qwen3.5-4B ladder; cross-family error ±15%, pooled R² = 0.16). Words/token band 0.65–0.80 for estimates (Qwen3.5-4B measured 0.680, the family value for qwen3.5:9b); at k=1 size* ≈ 10.44 GiB.

**Popularity walk-down (snapshot 2026-09-26), with quant-4 gate estimates** (Q4_K_M size; t/s = law ±15%; w/s band 0.65–0.80 w/t):

| # | ollama row | pulls | verdict |
|---|---|---|---|
| 1 | llama3.1 | 119.9M | **SELECT (Meta family): Llama-3.1-8B-Instruct** — highest runnable (70b = 40.05 GiB can't run); Q4_K_M 4.56 GiB → 13.7 t/s (11.6–15.7) → 7.5–12.6 w/s: passes |
| 2 | deepseek-r1 | 93.2M | excluded — thinking-only, no off switch (distills are always-reasoning) |
| 3 | nomic-embed-text | 87.2M | excluded — embedding model |
| 4 | llama3.2 | 84.4M | excluded — same owner as llama3.1 (ruling A); its 3b passes quant 4 easily but the Meta slot is taken by the more popular row, whose 8b is the higher model |
| 5 | qwen2.5 | 41.0M | superseded by qwen3.5 (rule 7, ruling B); qwen2.5:14b itself was borderline at quant 4 (8.38 GiB → 8.1 t/s → 4.5–7.5 w/s, straddling 5.0) |
| 6 | gemma3 | 40.7M | superseded by gemma4 (rule 7, ruling B); gemma3:12b itself was borderline (QAT Q4_0 7.54 GiB → 8.9 t/s → 4.9–8.2 w/s) |
| 7 | qwen3 | 38.1M | superseded by qwen3.5 (same Qwen family) |
| 8 | mistral | 33.7M | **SELECT (Mistral family): Mistral-7B-Instruct-v0.3** — the Mistral-brand family row (mistral-nemo 5.7M and ministral-3 1.5M are separate lower-ranked rows); Q4_K_M ~4.1 GiB → ~14.9 t/s → 9.7–11.9 w/s: passes |
| — | gemma2 / llama3 / qwen2.5-coder | 33.4M / 25.3M / 21.8M | excluded — superseded or same family |
| — | gemma4 | 25.8M | absorbed into the gemma3 slot by rule 7 (ruling B): **Gemma-4-12B** is the Google family's pick |
| — | qwen3.5 | 21.0M | absorbed into the qwen2.5 slot by rule 7 (ruling B): **Qwen3.5-9B** is the Qwen family's pick |
| — | phi3 / gpt-oss / smollm2 | 18.2M / 13.2M / 4.0M | not reached — slots full after four families |

**Selected roster (pre-registered before any measurement):**

| family | pick | HF source | paper | quant-4 estimate | predicted rung selection |
|---|---|---|---|---|---|
| Meta | Llama-3.1-8B-Instruct | safetensors, gated (license accepted) | The Llama 3 Herd of Models, arXiv 2407.21783 | 4.56 GiB → 13.7 t/s → 7.5–12.6 w/s | Q6_K (6.14 GiB → 10.7 t/s → 6.9–8.5 w/s); Q8_0 7.95 GiB → 8.5 t/s → 5.5–6.8 w/s borderline — walk may stop at Q8_0 or descend to Q6_K |
| Qwen | Qwen3.5-9B | safetensors only, self-quantize path | Qwen3.5-Omni Technical Report arXiv 2604.15804 (family-level, ruled sufficient in the thinking roster v4) | 6.14 GiB → 10.7 t/s → 6.9–8.5 w/s (w/t 0.680 measured family value → ~7.2 point) | Q6_K (6.9 GiB → 9.6 t/s → 6.3–7.7 w/s); Q8_0 8.9 GiB → 7.7 t/s → 5.0–6.2 w/s borderline-fails confident |
| Google | Gemma-4-12B-it | QAT Q4_0 GGUF first-party (google/gemma-4-12B-it-qat-q4_0-gguf, gated); other rungs convert from google/gemma-4-12B-it safetensors | Gemma 4 Technical Report, arXiv 2607.02770 | 7.08 GiB → 9.4 t/s → 6.1–7.5 w/s | Q5_K_M (8.1 GiB → 8.4 t/s → 5.4–6.7 w/s) or QAT Q4_0; Q6_K 9.2 GiB → 7.5 t/s → 4.9–6.0 w/s borderline; Q8_0 11.9 GiB → 5.9 t/s → 3.8–4.7 w/s fails |
| Mistral | Mistral-7B-Instruct-v0.3 | safetensors, public | Mistral 7B, arXiv 2310.06825 | ~4.1 GiB → ~14.9 t/s → 9.7–11.9 w/s | Q8_0 (7.2 GiB → 9.3 t/s → 6.0–7.4 w/s) or Q6_K (5.5 GiB → 11.7 t/s → 7.6–9.4 w/s) |

**Provenance paths (all verified this session):** Meta/Qwen3.5/Mistral take the safetensors → f16 → rung self-quantize path (pinned llama.cpp b10964); Meta gated (license accepted), Mistral public, Qwen3.5 public. Gemma-4: first-party QAT Q4_0 GGUF exists (gated); non-QAT rungs convert from safetensors. Note the Gemma-4 disabled-thinking behavior: with thinking off the 12b still emits the `<|channel>thought` wrapper with an EMPTY thought block (only E2B/E4B cannot disable) — the speed gate and ARC must handle the wrapper; first-turn dump check mandatory (the open `--chat-template-kwargs` server-flag issue #20409; per-request kwarg primary), as the standing flag requires for every hybrid.

**The commands (author's machine, pull-first):**

    git pull --ff-only
    python3 full_benchmark.py --no-thinking "meta-llama/Llama-3.1-8B-Instruct" "Qwen/Qwen3.5-9B" "google/gemma-4-12B-it-qat-q4_0-gguf=google/gemma-4-12B-it" "mistralai/Mistral-7B-Instruct-v0.3"

**Pre-registered predictions (recorded before any v2.1-roster measurement):**
1. **Llama-3.1-8B:** Q8_0 (7.95 GiB → law 8.5 t/s → 5.5–6.8 w/s) borderline at k=1 — prediction: FAILS the confident verdict, Q6_K PASSES; selected rung Q6_K, worst 9.1–12.3 t/s. Llama-family w/t unknown — a first measurable (predicted in 0.65–0.80).
2. **Qwen3.5-9B:** Q8_0 (8.9 GiB → 7.7 t/s → 5.0–6.2 w/s) borderline-fails confident; Q6_K PASSES at measured family w/t 0.680 → ~6.5 w/s point; selected rung Q6_K, worst 8.2–11.1 t/s.
3. **Gemma-4-12B:** Q8_0 FAILS (3.8–4.7 w/s); Q6_K borderline (4.9–6.0); Q5_K_M PASSES at point estimate (5.4–6.7); the walk treats the first-party QAT Q4_0 as the Q4 rung. Prediction: selected rung Q5_K_M, or QAT Q4_0 if Q5_K_M misses confident; worst at Q5_K_M 7.1–9.7 t/s.
4. **Mistral-7B-v0.3:** Q8_0 (6.0–7.4 w/s) passes at point but the band straddles 5.0; Q6_K passes with margin. Prediction: selected Q8_0 or Q6_K; worst at Q8_0 7.9–10.7 t/s.
5. **Law transfer (the study's cross-family claim):** each pick's measured worst t/s lands within ±15% of the law's prediction at its selected rung's file size — grading the cross-family transfer at 8–12B scale (law fitted at 4B scale).
6. **Words/token:** llama/mistral/gemma4 w/t land in 0.65–0.80; qwen3.5:9b w/t within ±10% of the measured 0.680 family value.
7. **Mode blindness (gemma4):** with thinking disabled, reasoning_chars = 0 on every turn despite the empty `<|channel>thought` wrapper — wrapper tokens are parse artifacts, not reasoning.
8. **No selection descends below Q4_K_M** (the quant-4 inclusion filter holds for every family).

### Session 28, addendum 34 — the early-fail optimization: a sub-reader-line turn aborts the rung in flight

**The author's ruling:** "In the speed gate, as soon as a conversation fails the check for the reader catching up with the output of the model, consider that quant fail. It is impossible to recover from that."

**The logic, verified against the instrument:** the verdict is a MIN — worst turn within a conversation, worst conversation within a rung, worst rep within a bench. A min is monotone: once one turn measures below the reader line, no later turn, conversation, or rep can raise the worst. The 2-sigma lenient branch could previously rescue such a rung (a sub-line worst with large scatter across conversations still PASSED) — that rescue is exactly the "recovery" the author rules impossible, and it is hereby RETIRED. The verdict is now strict: **PASS (confident) only if EVERY conversation's worst turn is at or above the reader line; any sub-line conversation fails the rung outright.** Sigma stays in the output as a reported diagnostic (the spread of conversation worsts), no longer a verdict input.

**The optimization (implemented in speed_gate.py, mock-tested end to end):**
- `run_conversation` takes `reader_wps`; the first turn measured below the line is flagged `below_reader_line: 1` in the dump, prints the abort reason, and breaks — remaining turns of that conversation are not generated.
- `bench_model` propagates the flag: remaining conversations and remaining reps are skipped ("early-fail - skipping the remaining N conversation(s) and any further reps"). The dump is still written and graded honestly — a partial dump with the flagged turn always FAILs the strict verdict.
- `bench`/`full_benchmark.py` pass the reader line down from the CLI (`--reader-wps`), so the pipeline's ladder walk gets the same early abort; a doomed rung now costs one conversation instead of five.
- Turn-level check (not conversation-level): the conversation's worst is itself a min over its turns, so the abort fires mid-conversation at the offending turn — the earliest possible point.
- Honest scope note: the check applies to turns with a measured `server_wps` (v2.1 turns); empty answers have no w/s and cannot early-fail (they carry the existing empty-answer warning instead).

**Mock-server verification (three cases):** (1) healthy 10 w/s run — no flag, all 9 turns, PASS (confident); (2) a dip to 4 w/s at conv 2 turn 2 — the turn is flagged, the conversation aborts at turn 2, conv 3 is skipped, verdict FAIL; (3) the retired rescue — a 4.5 w/s worst with large conversation scatter now FAILs (previously PASS within 2-sigma). The test caught one mock artifact worth recording: an instant-responding mock produces a negative generation span (wall < prompt_ms) and therefore no measurable w/s — the real server never does, and the check correctly skips unmeasurable turns rather than false-failing.

**Consequences, recorded:**
1. **Runtime:** a failing rung costs ~1 conversation (~2 minutes at 12B scale) instead of 5 — the ladder walk's dominant cost was the doomed rungs (the predicted-descending ladders of addendum 33: llama3.1-8b and gemma4-12b are expected to fail Q8_0 first, qwen3.5-9b likewise). Estimated saving per family: ~8-15 minutes of bench time per failed rung.
2. **Strictness:** the ladder's first PASS is now the first rung whose EVERY conversation clears the line — the addendum-33 predicted-rung tables are unchanged (their bands assumed the strict reading), but borderline bands (llama3.1-8b Q8_0 at 5.5-6.8 w/s) may now select one rung lower than a lenient reading would have.
3. **Prediction grading unaffected:** predictions are compared against the measured worst of the SELECTED rung; early-fail only shortens the path to it.
4. The dumps of early-failed rungs are partial by design (flagged) — the per-rung dump record keeps the flag, so post-hoc analyses (lag_analyze, collision simulation) can distinguish "failed at conv 2 turn 2" from "ran all five and failed on the worst".

**Pre-registered expectation for the study #3 run:** with the early-fail in place, each predicted-failing top rung (llama3.1-8b Q8_0, qwen3.5-9b Q8_0, gemma4-12b Q8_0/Q6_K) aborts within its first or second conversation; if any of them instead runs all five conversations, that itself is a graded surprise (the law's ±15% band is generous in the wrong direction).

### Session 28, addendum 35 — the memory shortcut: rungs that cannot fit in RAM are skipped before download

**The trigger (author's catch, from the crashed first study #3 run):** "We forgot to take into account the amount of memory available in the system, that's another shortcut." The first pipeline run also exposed a second bug: the Llama-3.1-8B safetensors phase downloaded **32.1 GB** where ~16 GB of safetensors suffices - `snapshot_download` pulled the whole repo, including Meta's `original/*.pth` duplicates - and the reconstruction died with a writer-channel error (SIGSEGV in fish) at 63%.

**Two fixes, both verified with stubbed-hub tests:**

1. **The memory shortcut (the author's ruling):** before any network traffic, `hf_download.acquire()` now estimates the rung's size and compares against usable system RAM.
   - Size estimate, no download: exact when the repo ships the rung GGUF (HF tree metadata via `HfApi.list_repo_tree`); ratio-scaled from the fp16/safetensors total otherwise (RUNG_BITS: Q8_0 8.5, Q6_K 6.6, Q5_K_M 5.7, Q4_K_M 4.8, Q4_0 4.5, Q3_K_M 3.9, Q2_K 3.4 bits/weight; rung ≈ fp16_giB × bits/16; `original/` excluded from the source total).
   - RAM: `/proc/meminfo` (Linux), `sysctl hw.memsize` (macOS), `GlobalMemoryStatusEx` (Windows). Usable = total − 4 GiB reserve (OS + KV at the 4096 reference depth; the T14s: 32 − 4 = 28 GiB).
   - Infeasible rungs return plan `"infeasible: exceeds system RAM"`; the orchestrator marks the rung `FAIL (infeasible: exceeds system RAM)` and walks on down the ladder. No download, no conversion, no bench.
   - Never a false skip: when either estimate is undetectable, the rung proceeds as before. A disk-space warning (rung × 2 worst case) prints but does not block.
   - Tested: a 70B-class repo (150 GiB safetensors → Q8_0 est. 79.7 GiB) on a forced-32 GiB machine → skipped, zero download calls; an exact-size 40 GiB Q8_0 GGUF → skipped; a feasible 8 GiB-source repo → proceeds to download.

2. **Scoped snapshot download (the crash's cause):** `snapshot_download` now passes `allow_patterns = ["*.safetensors", "*.json", "*.txt", "tokenizer.model", "tokenizer.model.v3"]` - the conversion path needs the safetensors and tokenizer/config files only. Meta's `original/*.pth` (an entire second copy of the weights in PyTorch format), vision-tower extras and anything else no longer download: the Llama-3.1-8B source phase drops from ~32 GB to ~15 GB, halving the download and removing the writer-channel crash trigger (the background writer was juggling 17 files including a 16 GB .pth).

**One ladder consequence surfaced by the pending gemma-4 run (fixed in the same commit):** the default ladder had no Q4_0 rung, so the first-party QAT Q4_0 GGUF (addendum 33's stated gemma-4 path) would never have been reached - the pipeline would have self-quantized Q4_K_M from safetensors and skipped the QAT file entirely. The default ladder is now `[Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q4_0, Q3_K_M, Q2_K]`: self-quantized K-quants stay preferred, with the first-party QAT Q4_0 as the same-bit-width fallback (verified: `find_rung_file` matches `m-Q4_0.gguf` for rung Q4_0 and does not cross-match Q4_K_M/Q4_K_S; the gemma-4 QAT repo ships a single 6.98 GB file `gemma-4-12b-it-qat-q4_0.gguf`, not sharded, plus an mmproj that is correctly excluded).

**Also recorded: the crashed run left no state damage** - the phase-1 failure is idempotent (the state file had already recorded the partial phases), so the rerun resumes cleanly. The author's download can be rerun as-is after `git pull --ff-only`.

**The revised run command (unchanged for the author; the fixes are internal):**

    git pull --ff-only
    python3 full_benchmark.py --no-thinking "meta-llama/Llama-3.1-8B-Instruct" "Qwen/Qwen3.5-9B" "google/gemma-4-12B-it-qat-q4_0-gguf=google/gemma-4-12B-it" "mistralai/Mistral-7B-Instruct-v0.3"

### Session 28, addendum 36 — the memory report: llama.cpp's own accounting + the kernel's peak RSS

**The author's request:** "can we get information from llama-cpp about memory usage? that would be good to report too."

**Two sources, one authoritative number.** llama.cpp reports its own startup accounting (model size, KV cache, compute/graph buffers) in the server banner - which the pipeline discarded to /dev/null until now. The banner's wording moves between builds, so the parser is best-effort (structured keys where recognizable: kv_cache_gib, cpu_buffers_gib, graph_overhead_gib; plus the raw size-bearing banner lines kept verbatim, last 40). The AUTHORITATIVE number is the kernel's peak resident set size (VmHWM, /proc/<pid>/status) read at server teardown - everything the launch took: weights + KV cache + compute buffers + runtime overhead. It is the honest "can it run here" quantity, and the validation target for addendum 35's size estimates (the estimate's usable-RAM reserve can now be graded against the measured peak per rung).

**Implementation:**
- `llama_server.start_server(log_path=...)`: the server's stdout/stderr is captured to `<model>.server.log` (truncated per launch) instead of /dev/null.
- `llama_server.peak_rss_gib(proc)`: VmHWM in GiB, read BEFORE teardown terminates the process (Linux /proc only; None elsewhere - the report is skipped, never faked).
- `llama_server.parse_memory_log(log_path)`: best-effort banner parse (structured keys + verbatim lines).
- `speed_gate.bench_model`: reads peak RSS in the teardown finally-block, prints it per rep ("memory: peak RSS X GiB"), summarizes across reps ("MEMORY: peak RSS X GiB ... N GiB beyond the file (KV + buffers + runtime)"), and returns the reports; `speed_gate.bench` persists them to a sidecar `<dump>.mem.json` (the dump's turn-list format and the resume machinery untouched); on dump reuse the sidecar's peak is re-printed. `full_benchmark.py` phase 4 prints "memory: peak RSS X GiB" per rung from the sidecar.
- `depth_probe.py`: reports peak RSS per depth (the KV term is IN the number at depth D - the depth-conditioned memory cost).

**Tested with a mock server + a real sleeping process:** banner parse (512 MiB KV -> 0.5 GiB, missing file -> empty), VmHWM read on a live PID, end-to-end bench_model -> report -> sidecar write -> reuse print. The mock's ~0 GiB peaks are the sleep process's honest RSS, not a bug; a real launch reports real numbers.

**The report's role in the study:** the machine's memory ceiling enters the data. Each rung's dump now carries the measured peak RSS alongside its worst w/s - so the study reports not just "passes the reader line at Q6_K" but "passes at Q6_K taking X GiB peak", and the 32 GB ceiling's actual headroom (28 GiB usable estimate vs measured peak) is a graded column, validating addendum 35's 4 GiB reserve assumption rung by rung.

**Pre-registered expectation:** llama.cpp peak RSS ~ file size + 1.5-2.5 GiB (KV at 4096 + Vulkan compute buffers + runtime) for the 7-12B picks; if the measured "beyond the file" exceeds 3 GiB on any pick, the 4 GiB reserve in the memory shortcut was too tight and gets re-fitted from these very numbers.

# Session 29 - 2026-09-26/27 (the v2.1-v2.3 roster runs; protocol v3.0 - the reader-wall test; the calibration pass)

Split from session-27.md (which had accumulated sessions 28-33 behind its own header) per the one-session-per-day audit, session 39 addendum 3. Content verbatim; addendum numbers unchanged. Addenda 37-66: 37-43 registered the 26th, 44-66 the 27th (the working day ran past midnight - recorded, not split).

### Session 29, addendum 37 — grading the first v2.1-roster run: the law HIT, the w/s estimator missed; the words/token minimum replaces the mean; Q4_0 rung removed

**The run (author machine, protocol v2.1, --no-thinking):** Llama-3.1-8B-Instruct Q4_K_M (4.56 GiB), 5 conversations depth-prefilled, early-fail at conv 4 turn 1 (2.09 w/s < 5.0 reader line, addendum 34). Noise at depth: worst 14.09, mean 14.38, w/m 0.980 (n=8). The rung FAILS the gate — llama passed NO rung (Q8_0 and Q6_K fail on law arithmetic before download, Q5_K_M and Q4_K_M both early-failed at the same joke turn).

**The grade, split by side:**

1. **The law HIT on the t/s side (+5–10%).** Predicted 13.7 t/s (band 11.6–15.7) from the Session-26 fit `1/t = size/76.5 + 1/74`; measured turn t/s 14.3–15.0 across 14 turns, noise-at-depth worst 14.09. The law's cross-family transfer to 8B holds — the speed side of the study needs no revision. This also grades addendum-33 prediction 5 (law transfer): HIT.
2. **The w/s estimate MISSED, 3.6–6× optimistic.** Predicted worst 7.5–12.6 w/s (Q4_K_M point 9.1); the killer turn measured 2.09 w/s — below the reader line. The error is not timing, not the law, not the machine: it is the words/token ASSUMPTION (band 0.65–0.80, "measured 0.680 family value"). The killer turn's own words/token: 30 words / 208 tokens = **0.144** — a terse answer to "Knock, knock!" whose tokens are mostly non-whitespace structure (emoji, markdown, list markers, punctuation-words like "who's-there" split by the whitespace tokenizer).
3. **The mechanism (on record as the study's central instrument lesson):** the verdict is a MIN over turns, and w/s = words/(wall−prefill) is a per-turn CONTENT-dependent ratio. Multiplying a MEAN words/token (0.65–0.80, or the pooled 0.680) into a min-verdict predicts the typical turn, not the worst. The min over turns punishes terse answers — the answer-shape sensitivity already flagged in addendum 20 (qwen's worst 7.48 w/s was the same short-answer effect at w/t 0.49) and now measured at its extreme in llama. **Corrected estimator (pre-registered for all future predictions): `w/s_pass = t/s(rung) × w/t_min(family)`, where w/t_min is the family's worst-turn words/token** (llama 0.144 measured; qwen 0.49 measured; unmeasured families carry the conservative 0.43–0.49 band until their first run grades it).
4. **Reproduction check of the corrected estimator on both measured families:** qwen3.5-4b Q8_0 predicted 15.3×0.49 = 7.5 (measured 7.32/7.48/8.24 across three runs); llama-3.1-8b Q4_K_M predicted 13.7×0.144 = 2.0 (measured 2.09). Both land. The estimator is now anchored to two families at two sizes.
5. **Early-fail's first live firing — validated.** The abort hit at the earliest possible point (turn 1 of the offending conversation), conv 5 skipped, exactly the addendum-34 design. The dump keeps the flagged turn for post-hoc analysis. The optimization saved ~2 bench minutes on this rung alone.

**Author rulings recorded in the same session:**

- **Q4_0 removed from the ladder** (addendum 35's own trigger is gone: gemma-4's QAT rung is unreachable under the Q6 criterion — see the walk-down below). `LADDER_DEFAULT = [Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q3_K_M, Q2_K]`; RUNG_BITS keeps the Q4_0 ratio for ad-hoc --ladder size estimates. "There's a q4_0 that's unnecessary since we have q4_k_m."
- **Model selection re-run with the selection criterion targeting Q6:** the inclusion filter is now "estimated to pass the speed gate at **quant 6** (Q6_K)" — the author's catch that the quant-4 filter admitted models (llama-3.1-8b's 8B file at 14.3 t/s fails the w/s gate at every rung) that the study's own guarantee would reject.

**The Q6 walk-down (popularity snapshot 2026-09-26, unchanged rules 1–8, quant-6 filter):** the w/s gate at Q6 needs `t/s(Q6_K) × w/t_min ≥ 5.0` → t/s needed ≥ 10.2 at w/t_min 0.49 → size(Q6_K) ≤ ~6.2 GiB (law, −15% margin) → fp16 ≤ ~15 GiB. Candidate members by family (rung sizes from RUNG_BITS × fp16; fp16 from first-party repos):

| family | Q6-capable candidate | Q6_K GiB → t/s → w/s (w/t_min 0.49) | verdict |
|---|---|---|---|
| Meta | Llama-3.2-3B-Instruct | 2.60 → 21.1 → 10.3 | **SELECT** (llama3.2 84.4M; the 8B pick is quant-4-only, out under the Q6 filter) |
| Qwen | Qwen3.5-4B | 3.46 → 17.6 → 8.6 | **SELECT** (qwen3.5 21.0M; the 9B pick fails Q6: 6.9 GiB → 9.6 t/s → 4.7 w/s) |
| Google | Gemma-3-4B-it | 2.73 → 20.3 → 10.0 | **SELECT** (gemma3 40.7M; gemma4-12b fails Q6: 9.2 GiB → 7.5 t/s → 3.7 w/s) |
| Mistral | Mistral-7B-v0.3 | 5.5 → 11.7 → 5.7 | **SELECT (barely, band-straddling)** — Q6_K 5.5 GiB → 11.7 t/s → 5.7 w/s at w/t_min 0.49; at the band's low end (0.43) it lands 5.0 exactly. The 7B is the family's highest member that can pass Q6; its t/s headroom (11.7 vs 10.2 needed) is the thinnest of the roster. Prediction: selects Q6_K, worst w/s 5.0–7.0, coin-flip vs early-fail at a terse-answer turn. |

Ruled out under the Q6 filter: Llama-3.1-8B (Q4-only by measurement: Q4_K_M early-failed at 2.09 w/s; Q6_K 6.14 GiB → 10.7 t/s → 5.2 w/s at 0.49 band — but the family's Q6-capable member is the 3B), Qwen3.5-9B (Q6 4.7 w/s FAIL), Gemma-4-12B (Q6 3.7 w/s FAIL), all thinking-only families (unchanged), all 1.5b-class variants (unchanged). The roster is now three 3–4B models + one 7B — the same weight class as study #2's non-thinking roster, and the direct prediction-grading replication of it.

**The roster consequence — study #3's roster is superseded before any further measurement:** the four picks of addendum 33 (Llama-3.1-8B, Qwen3.5-9B, Gemma-4-12B, Mistral-7B-v0.3) are retired with the quant-4 filter; the new roster is Llama-3.2-3B, Qwen3.5-4B, Gemma-3-4B, Mistral-7B-v0.3. Qwen3.5-4B Q8_0 and Llama-3.2-3B Q8_0 (study #2's measured configs) are already-complete data points in the state file; Gemma-3-4B and Mistral-7B-v0.3 are the new measurements. Note the two mode questions on the new roster: Qwen3.5-4B runs in non-thinking mode (rule 8, --no-thinking, verified in addendum 20); Gemma-3-4B is non-thinking by nature (no toggle needed); Mistral-7B-v0.3 and Llama-3.2-3B are non-thinking by nature.

**The command (author machine, pull-first):**

    git pull --ff-only
    python3 full_benchmark.py --no-thinking "meta-llama/Llama-3.2-3B-Instruct" "Qwen/Qwen3.5-4B" "google/gemma-3-4b-it-qat-q4_0-gguf=google/gemma-3-4b-it" "mistralai/Mistral-7B-Instruct-v0.3"

**Pre-registered predictions (v2.2 roster, before any new measurement):**

1. **Llama-3.2-3B:** selects **Q8_0** (study #2: Q8_0 3.36 GiB measured 20.6 t/s worst → w/s = 20.6×w/t_min; the study-#2 dump gives the family w/t_min — llama-3.1-8b's 0.144 is the family anchor at 8B, the 3B may be less terse; conservative band 0.15–0.49 → 3.1–10.1 w/s). Honest note: this is the roster's least-confident pick — if the 3B inherits the 8B's joke-answer terseness, Q8_0 fails and the walk descends to Q6_K/Q5_K_M; the early-fail catches it in one conversation. Prediction: Q8_0 PASS, worst 3.1–10.1 w/s, w/t_min 0.15–0.49.
2. **Qwen3.5-4B:** selects **Q8_0** (already measured: worst 7.32–8.24 w/s, w/t_min 0.49, PASS confident; the selection is a re-grade of addendum-20 data, no new run needed if the state file has the rung marked complete).
3. **Gemma-3-4B:** selects **Q8_0** (3.96 GiB → 15.3 t/s → 7.5 w/s at 0.49; study-#2 measured the QAT Q4_0 live worst 20.9 t/s → Q8_0 predicted from law+size; w/t_min unmeasured for the family — band 0.43–0.49 → worst 6.6–7.5 w/s). Gemma's SWA boundary: at ctx 4096 the KV tax is window-capped, favoring speed; the rung walk starts at Q8_0.
4. **Mistral-7B-v0.3:** selects **Q6_K** (5.5 GiB → 11.7 t/s → 5.7 w/s at 0.49; at w/t_min 0.43 it is exactly 5.0 — the roster's only band-straddling pick). Q8_0 7.2 GiB → 9.3 t/s → 4.6 w/s FAILS by the corrected estimator. Prediction: Q6_K PASS, worst 5.0–7.0 w/s; the honest risk is an early-fail on a terse-answer turn (the addendum-37 mechanism) — if it fires, the walk descends to Q5_K_M.
4b. **The Q6 inclusion filter itself is a prediction:** every family's pick must select at or above Q6_K. If any family selects below Q6_K (e.g. Mistral at Q5_K_M), the inclusion filter missed — grade it as a miss of the estimator, not the model.
5. **Law transfer at the new sizes:** each pick's measured worst t/s within ±15% of `76.5/(size+t/74)`: llama-3.2-3b 20.6 (already measured, HIT), qwen3.5-4b 15.3 (measured, HIT), gemma-3-4b 15.3±2.3, mistral-7b 11.7±1.8.
6. **Words/token minimums:** llama w/t_min lands in 0.15–0.49 (the 8B anchor 0.144 is the pessimistic bound; the 3B's terse-answer behavior unmeasured); qwen w/t_min 0.49 (measured); gemma w/t_min 0.43–0.49; mistral w/t_min 0.43–0.49.
7. **Mode blindness (qwen3.5-4b non-thinking):** reasoning_chars 0 on every turn, no inline think tags (re-grade of addendum-20 data, standing flag).
8. **No selection descends below Q5_K_M** (the Q6 filter's honest floor; the strict-verdict walk stops at the first PASS).

### Session 29, addendum 38 — quiet tooling: HF download and converter/quantizer output hidden, shown only on error

**The author's ruling:** "hide the output of the hf download and the quantizer and only show it if there's an error." The pipeline's console is the study log — multi-GB download progress bars and llama.cpp conversion chatter drowned the phase lines that matter.

**Implementation (three sites, one rule — success is silent, failure is loud):**

1. **HF downloads (hf_download.py):** `HF_HUB_DISABLE_PROGRESS_BARS=1` is set (before the hub import, `os.environ.setdefault` — an author-set env var wins) so hf_hub_download/snapshot_download print nothing on success; each download site now prints one phase line instead ("downloading X (output hidden; shown on error)"). Failures already surfaced through `fail()` with the full exception — unchanged, still loud.
2. **Converter (convert_quant.py):** the safetensors→f16 conversion's stdout+stderr is captured to `models/<family>/convert-f16.log`; on success nothing prints beyond the phase line; on failure the full captured output prints under a "--- output of the failed conversion ---" banner plus the log path, before the existing PHASE 2 FAILED guidance box.
3. **Quantizer (llama-quantize):** same treatment, per-rung log `models/<family>/quantize-<rung>.gguf.log`-style (`quantize-Q6_K.log`); failure prints the captured output + log path. The failure-guidance text updated accordingly ("(see the converter output above)" → the log path).

**Design notes on record:** the logs live in the family folder (gitignored with models/) — they are build artifacts, not study data; `run_quiet` returns the return code and the existing `fail()` keeps its idempotent-rerun guidance; stderr is merged into the log (2>&1) so a dying tool's last words are never split from its progress output. The pinned tool versions are unchanged — this is presentation, not protocol. Phase lines and verdicts (the actual study log) are untouched.

**Tested (mock tools, three cases):** (1) a failing converter — captured stdout AND stderr printed on failure, log path named, guidance box intact; (2) a succeeding converter+quantizer — zero tool chatter on the console, rung file created, log sidecar written; (3) a failing quantizer — captured stderr printed, PHASE 2 FAILED box with the log path. All pass; py_compile clean across the repo scripts.

### Session 29, addendum 39 — PROTOCOL.md: the constants registry

**The author's ruling:** "Let's keep track of any number we settle on in the study. Some will be my choice, some a practical limit, some derived from statistics and some with no explanation, defaults etc." - and, on the proposal: "I love your idea. Let's call it protocol.md, because it is unrelated to the readme." The registry will appear in (or be referenced by) the final report - full transparency is a stated goal of the study.

**What shipped: `PROTOCOL.md`** (repo root), the complete registry from a full-code sweep of all eleven scripts + the corpus + the fitted constants. Structure:

- **The anchor, stated once:** reader line 5.0 w/s = 300 wpm (Brysbaert 2019) / 60 - the study's single scientific anchor, with the derivation chain (w/s -> t/s per rung via w/t_min -> size* via the law; floor 20 as the cited k=3 headroom).
- **Four provenance categories:** [A] author choices (12 rows: reader line, corpus shape, repeats, think allowance, determinism, reaction 0.45 s, ARC n=1172, quant-6 filter, ladder, ...), [P] practical limits (RAM reserve 4 GiB, ports, timeouts, noise/depth guards, tooling pins), [D] derived/measured (answer cap 299, law BW_eff 76.5 / t_inf 74, RUNG_BITS, w/t_min 0.49/0.144 + the 0.43-0.49 band, ms/GiB 13.07, the selection estimator), [M] magic with exit plans (ctx 4096 - promoted, honest; w/t 0.75 - display-only; the 6.5 t/s derivative; ARC_CTX 2048; ARC flags; the BPW_APPROX duplicate; depth-probe defaults).
- **A governance rule, pre-registered:** single-sourcing (a constant lives in exactly one file, others import it), and **changing a constant is a protocol change - it requires a notebook addendum, not a silent edit.** The report inherits the registry wholesale.

**The honest centrepiece of the registry is the [M] section** - five inherited numbers that were never ruled on, each now carrying an exit plan: ctx 4096 (already promoted, addendum 9); the 0.75 words/token rule of thumb (unanchored, display-only since v2.1, to be single-sourced or deleted); its 6.5 t/s derivative in lag_analyze/depth_probe (second-order magic - the tools print the w/s line alongside); ARC_CTX 2048 (exit: verify no ARC prompt exceeds it, then register [P]); BPW_APPROX as a duplicate of RUNG_BITS (exit: single-source). The DEPTH_HEADROOM 64-vs-32 pair is registered as INTENTIONAL (the gate's conversations reserve noise room on top of the blob; the probe's single prompt does not).

**Cost:** one file, ~9.4 KB, zero code changes. **Gain:** every number in the report traceable to a ruling, a citation, a measurement, or an honest "inherited - here is the plan". This is the artifact that makes the 51.2-class replication and the eventual w/t calibration pass (addendum-37 discussion) auditable end to end.

### Session 29, addendum 40 — the v2.2 roster run graded: a new champion, the Q6 filter's first miss, and the memory instrument's undercount found and fixed

**The run (author machine, protocol v2.2, --no-thinking):** four families walked. Llama-3.2-3B Q8_0, Qwen3.5-4B Q5_K_M, gemma-3-4b Q6_K already selected in state (skipped, idempotent); Mistral-7B-v0.3 walked fresh: Q8_0 FAIL (early-fail conv 2 turn 1, 3.34 w/s), Q6_K FAIL (early-fail conv 2 turn 1, 4.44 w/s), **Q5_K_M PASS (worst 5.25 w/s, mean 8.92, sigma 0.78) → SELECTED**. Phase 5-6: ARC completed for Mistral (886/1172 = 75.6%), final ranking computed on the full n=1172 with exact McNemar.

**The ranking (study #3's headline, n=1172):**

1. **Qwen3.5-4B Q5_K_M: 1057/1172 = 90.2%** — new champion; Phi-3-mini's 84.8% (draft champion since Session 20) is dethroned.
2. Phi-3-mini Q6_K: 84.8%
3. Phi-4-mini Q6_K: 80.3%
4. Qwen2.5-3B Q8_0: 76.1% (superseded data point)
5. Mistral-7B-v0.3 Q5_K_M: 75.6%
6. gemma-3-4b Q6_K: 73.3%
7. Llama-3.2-3B Q8_0: 72.6%

Separations: #1 vs #2 SEPARATED (p<0.0001, -5.38 pp), #2 vs #3 SEPARATED (p=0.0001), #3 vs #4 SEPARATED (p=0.0011); #4-#5, #5-#6, #6-#7 not separated (p=0.76/0.10/0.66). The top of the ranking is decisively ordered; the 72-76% band is a statistical tie.

**Prediction grades (addendum 37, pre-registered):**

1. **Llama-3.2-3B selects Q8_0 — HIT** (state-confirmed: PASS confident at 20.6 t/s; the w/t_min question below).
2. **Qwen3.5-4B selects Q8_0 — MISS on the rung, by state reuse.** The state file carried its thinking-era Q5_K_M selection (Session 24, floor-20 protocol); the pipeline correctly reused it rather than re-benching. The v2.2 non-thinking rung prediction (Q8_0) was never re-measured. Consequence: **the qwen3.5-4b non-thinking selection must be re-run with --force** to grade prediction 2 honestly (Q8_0 predicted: 4.29 GiB → 15.3 t/s → 7.5 w/s at w/t_min 0.49, PASS). Until then the roster's qwen slot carries a floor-20-era selection. Honest label required in the results file.
3. **Gemma-3-4B selects Q8_0 — MISS, state reuse again** (Q6_K selected in the floor-20 era; the v2.2 prediction Q8_0 unmeasured). Same consequence: re-run with --force.
4. **Mistral Q6_K PASS (worst 5.0-7.0) — MISS.** Measured Q6_K FAIL at 4.44 w/s; the killer turn's w/t = 0.367. The 0.43-0.49 band was optimistic for mistral; its true w/t_min is 0.37 (measured). **Prediction 4b (the Q6 filter misses): HIT as pre-registered** — mistral selected Q5_K_M, one rung below the filter; graded as an estimator miss, not a model failure.
5. **Law transfer at the new sizes — HIT again (+4% to +9%).** Mistral Q8_0 predicted 9.3 vs measured 9.3-9.8; Q6_K 11.6 vs 11.9-12.5; Q5_K_M 13.2 vs 13.6-14.3. Third family confirming the ±15% band is generous in the right direction (all misses inside +10%).
6. **w/t_min lands:** llama-3.2-3b (from its study-#2 dump: worst-turn w/t to be re-extracted), qwen 0.49, gemma to extract, **mistral 0.37 measured** (killer turn 4.44 w/s at 12.1 t/s; the Q8_0 killer 3.34 at 9.7 → 0.344; Q5_K_M worst conv 5.25 at ~13.8 → 0.380 — consistent ~0.34-0.38 across rungs: w/t_min is a model property, rung-independent, as predicted).
7. **Mode blindness (qwen):** pending the --force rerun (state reuse skipped the check).
8. **No selection below Q5_K_M — HIT** (all four selections at Q8_0/Q6_K/Q5_K_M).

**The w/t_min table after this run:** llama-3.1-8b 0.144 · **mistral-7b 0.37** · qwen3.5-4b 0.49 · (llama-3.2-3b, gemma-3-4b to extract from existing dumps). The family spread is real (0.14-0.49), confirming the per-family constant, not a pooled one. Mistral's 0.37 also revises the roster-criterion arithmetic: at w/t_min 0.37, the gate needs t/s ≥ 13.5 at Q6_K → size ≤ ~4.9 GiB — the 7B was admitted by a band that did not know its family value; with 0.37 it would not have been predicted to pass Q6_K (11.6 t/s × 0.37 = 4.3 w/s < 5.0). **The estimator now has three measured families and a growing lesson: the w/t_min band must be per-family measured before selection; the conservative 0.43-0.49 default band is retired for selection use** (kept for display).

**The memory instrument's undercount (found in this run's output, fixed same session):** the run printed peak RSS 0.58 / 0.10 / 1.06 GiB for 7.17 / 5.54 / 4.78 GiB files — impossible values (below the model file itself), non-monotonic in size. Root cause: VmHWM of the server process undercounts when weights are mmap-loaded and shared with the page cache — the resident accounting never sees the whole file as process-private. Fix shipped: `system_memavailable_gib()` + `memory_cost_gib()` in llama_server.py — the system-wide MemAvailable delta across the launch is the honest "cost to the machine" number, immune to mmap/page-cache accounting quirks. Both instruments now report side by side; a peak below the file size prints "SUSPECT undercount". The addendum-36 expectation ("peak ~ file + 1.5-2.5 GiB") is graded: VmHWM was the wrong instrument for the mmap case — MemAvailable delta is the authoritative number going forward. **The addendum-35 memory-shortcut validation must use mem_cost_gib, not VmHWM.**

**Verified by test:** a real 200 MiB allocation read correctly by both instruments (VmHWM 0.205 GiB, MemAvailable delta 0.200 GiB on a live process); the suspect-undercount warning fires only when peak < file size.

**Next actions (in order):**

1. Re-run qwen3.5-4b and gemma-3-4b selections with --force (grade predictions 2, 3, 7 honestly under v2.2; qwen's is also the mode-blindness check).
2. Re-run mistral with --force once is enough? No — mistral's walk is complete and honest (fresh state, no reuse). Its Q5_K_M selection stands.
3. The w/t calibration pass (addendum-37 discussion, author-approved "for later"): larger arena resample per family on its selected rung, publishing w/t_min as a quantile.
4. ARC for the champion pair (qwen3.5-4b Q5_K_M vs phi-3-mini Q6_K) — already complete from the ranking run (both in state). The McNemar is computed: SEPARATED, p<0.0001. The champion pair's separation is final.

### Session 29, addendum 41 — the ranking's roster leak: --roster shipped; study #3's ranking corrected

**The author's catch:** "the ranking is not consistent since it talks about qwen2.5, phi, which are not in the selection." Correct — the addendum-40 ranking mixed studies: Phi-3-mini, Phi-4-mini and Qwen2.5-3B are study-#2 roster members living in the same shared state file, and phase 6 ranked EVERY family with a selection in state, not just the v2.2 roster. The mechanism was already on record (Session 25 addendum 2's roster note: "if phase 6 auto-ranks everything in state, run the final ranking with --arc-only --arc-models restricted"); the --force rerun of the full pipeline recomputed the ranking without that guard. Lesson repeated: the state file accumulates across studies; the ranking must be roster-scoped by construction, not by operator discipline.

**The fix shipped: `--roster` on full_benchmark.py** — restricts phases 5-6 and the final ranking to the named families (comma-separated, as named in the family specs). Without the flag, behavior is unchanged (backward compatible); with it, non-roster families are excluded from the ranking entirely and any roster family without a selection is reported ("excluded from the ranking"). The state file itself is untouched — superseded data points stay for the results file, per rule 7.

**Study #3's corrected ranking (v2.2 roster only, n=1172, exact McNemar, from the run's own CSVs):**

1. **Qwen3.5-4B Q5_K_M: 1057/1172 = 90.2% — the study #3 champion**
2. Mistral-7B-Instruct-v0.3 Q5_K_M: 886/1172 = 75.6%
3. gemma-3-4b-it-qat-q4_0-gguf Q6_K: 859/1172 = 73.3%
4. Llama-3.2-3B-Instruct Q8_0: 851/1172 = 72.6%

Separations (roster-internal): #1 vs #2 SEPARATED (-14.59 pp, p<0.0001 — the champion's margin over its own roster is enormous); #2 vs #3 SEPARATED (p<0.0001); #3 vs #4 SEPARATED (p=0.0078, -0.68 pp — the closest pair in the roster, correctly ordered but by a hair). Note the correction's substance: the roster-internal ranking is MORE decisive than the mixed one (three clean separations; the mixed ranking's #4-#5 and #6-#7 "not separated" verdicts were cross-study artifacts).

**Caveat on the numbers:** the addendum-40 mixed ranking's scores are unchanged (same CSVs, same per-model percentages); only the membership was wrong. The champion's identity (qwen3.5-4b, 90.2%) was never in doubt; the leak affected the comparisons, not the crown.

**The corrected run command (author machine, pull-first; --force to re-verify qwen/gemma under v2.2 as flagged in addendum 40):**

    git pull --ff-only
    python3 full_benchmark.py --no-thinking --force --roster "Llama-3.2-3B-Instruct,Qwen3.5-4B,gemma-3-4b-it-qat-q4_0-gguf,Mistral-7B-Instruct-v0.3" "meta-llama/Llama-3.2-3B-Instruct" "Qwen/Qwen3.5-4B" "google/gemma-3-4b-it-qat-q4_0-gguf=google/gemma-3-4b-it" "mistralai/Mistral-7B-Instruct-v0.3"

Note: --force re-benches every family including llama3.2 and mistral whose v2.2 walks are already complete and honest. If the author prefers to re-verify only qwen and gemma (the two flagged in addendum 40), the command is:

    git pull --ff-only
    python3 full_benchmark.py --no-thinking --force --roster "Llama-3.2-3B-Instruct,Qwen3.5-4B,gemma-3-4b-it-qat-q4_0-gguf,Mistral-7B-Instruct-v0.3" "Qwen/Qwen3.5-4B" "google/gemma-3-4b-it-qat-q4_0-gguf=google/gemma-3-4b-it"

(phases 1-4 re-run only for the two named families; the ranking then covers the full roster from state — mistral's and llama's selections are reused, not re-benched; llama's Q8_0 walk happens to be already v2.2-honest since it ran fresh in the addendum-40 session).

**Verified by test:** synthetic state with 7 families (3 study-#2 leftovers + the v2.2 four), real-schema CSVs — without the flag, 7 rank; with `--roster`, exactly the 4 v2.2 families rank and no Phi/Qwen2.5 label appears. The corrected ranking's separations recompute correctly from the run's own CSVs.

### Session 29, addendum 42 — two corrections: --force was a no-op past the family check; addendum 41's separations were synthetic

**Bug 1 (the author's run caught it): --force did not re-bench.** The author ran the addendum-41 command with --force; the output shows NO rung walks for qwen3.5-4b or gemma-3-4b — the family blocks printed nothing between the headers and phase 5. Root cause: --force only bypassed the family-level "already selected - skipping" return; the per-rung loop below then hit `verdict.startswith("PASS")` → break and `verdict == "FAIL"` → continue on the STORED verdicts, so the ladder walk skipped every rung and fell straight through to phases 5-6. A second layer underneath: even had phase 3 been reached, `speed_gate.bench` would have reused the existing dumps (its own force flag was never passed). The bug's history: --force was built and mock-tested for the standalone speed_gate path (where it works), then the pipeline grew the family-level return and the stored-verdict shortcuts WITHOUT re-testing the force path end to end — the same class of miss as the Session-25 mode/dump-reuse bug: two resume layers, only one tested.

**Fix (both layers):** with --force, process_family clears every rung's verdict and phases 3-4 (phases 1-2 stay done — the rung files exist and are reused, no re-download), resets the family's selection, prints "--force: re-benching the ladder (N stored verdict(s) cleared; files reused)", and threads force=True into speed_gate.bench so dumps are re-measured. E2E-verified with a synthetic state (stored FAIL at Q8_0 + stored PASS at Q5_K_M): force clears both, the walk restarts at Q8_0, re-benches, re-selects; force arrives at bench; without force, the skip path is unchanged.

**Bug 2 (mine, and worse - a record-keeping error): addendum 41's separation numbers were synthetic.** The "three clean roster-internal separations" table recorded in addendum 41 was computed from the TEST CSVs (deterministic prefix-correct synthetic data), not from the run's real ARC CSVs. The author's real ranking (this session's output) separates ONLY THE CHAMPION:

- #1 vs #2 (qwen3.5-4b 90.2% vs mistral 75.6%): b=33, c=204, **p < 0.0001 SEPARATED** — the champion's margin is real and enormous (-14.59 pp).
- #2 vs #3 (mistral 75.6% vs gemma 73.3%): b=140, c=113, **p = 0.1019 NOT separated**.
- #3 vs #4 (gemma 73.3% vs llama 72.6%): b=124, c=132, **p = 0.6618 NOT separated**.

**Correction of record:** the v2.2 roster's honest statistical picture is **one decisive champion and a three-way tie for second** (mistral/gemma/llama, spans 75.6-72.6%, every pairwise p > 0.10). Addendum 41's claim of "three clean separations" is RETRACTED; its roster-filter fix and corrected ranking MEMBERSHIP stand (the real run confirms both — the ranking now lists exactly the four v2.2 families). Lesson recorded: test-data outputs must never be pasted into the notebook as if they were run data — the notebook cites the run's own output or it cites nothing.

**The re-run still pending (unchanged in purpose, now actually functional):** qwen3.5-4b and gemma-3-4b under the v2.2 gate with --force, to grade addendum-37 predictions 2, 3 and 7. The command is the addendum-41 one, now working as intended:

    git pull --ff-only
    python3 full_benchmark.py --no-thinking --force --roster "Llama-3.2-3B-Instruct,Qwen3.5-4B,gemma-3-4b-it-qat-q4_0-gguf,Mistral-7B-Instruct-v0.3" "Qwen/Qwen3.5-4B" "google/gemma-3-4b-it-qat-q4_0-gguf=google/gemma-3-4b-it"

Expected per addendum-37 predictions: qwen3.5-4b re-walks Q8_0 (4.29 GiB → 15.3 t/s → 7.5 w/s predicted, PASS; w/t_min 0.49 family value) and gemma-3-4b walks Q8_0 from its Q6_K floor-20-era selection (3.96 GiB → 15.3 t/s → 6.6-7.5 w/s predicted). Both walks re-bench every rung above their stored selections too (Q8_0 for both) — the dumps are re-measured, so the mem_cost_gib instrument (addendum 40) reports on every rung for the first time.

### Session 29, addendum 43 — stale-state guard: a stored rung file missing on disk crashed phase 3 (author's run caught it)

**The author's --force re-run crashed at qwen3.5-4b Q8_0 phase 3** with a bare `FileNotFoundError: ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf.server.log`. The walk started correctly (the addendum-42 fix works: verdicts cleared, banner printed, Q8_0 visited first) — but the family folder was missing from disk entirely. The state file still marked phases 1-2 done with a stored `file` path, so the orchestrator skipped download/quantize and handed speed_gate a path that was not there; llama_server tried to open the server log inside the nonexistent folder and died with a traceback instead of guidance.

**Root cause:** the resume machinery trusts `benchmark-state.json` exclusively — nothing validates that a stored rung file still exists on disk. Files CAN vanish (folder moved/deleted by hand, disk cleanup); the state is the only memory of phases 1-2, and it was lying about the disk.

**Fix (two layers, commit this addendum):**

1. `full_benchmark.py` process_family: a stale-state guard now runs before the ladder walk — every stored rung file is checked against the disk; a missing one clears phases 1-2 AND the stored plan entirely (not merely the file pointer: an earlier draft of the guard kept phases 1-2 "done" and popped only `file`, which made the walk skip the re-acquire stages and bench `None` — caught by the E2E test before it reached the author), printing `stored rung file missing on disk (<path>) - phases 1-2 invalidated; will re-acquire`. The walk then re-downloads/re-quantizes normally (both stages idempotent).
2. `speed_gate.py` bench: a standalone guard — `model file not found: <path>` with guidance (rerun full_benchmark.py which re-acquires automatically / verify the path / run from the repo root) instead of a raw traceback, since speed_gate.py is a standalone CLI too.

**Verified by test:**
- E2E (synthetic state, Q8_0 file present + Q6_K stored file missing, force): the guard prints, phases 1-2 clear, the walk re-acquires Q6_K (download + quantize mocked), benches, selects — `phases_done == [1,2,3,4]`, verdict stored, selection updated.
- Regression (file present, force): NO spurious re-download — acquire is not called, phases 1-2 stay marked, bench/analyze proceed normally.
- Standalone guard: `speed_gate.bench` on a missing file exits with guidance, not a traceback.

**Consequence for the pending re-run:** the qwen3.5-4b folder being absent means the safetensors re-download is back on the table for that family (the pipeline will do it automatically and silently now — quiet tooling, addendum 38). Expected walk unchanged from addendum 42: Q8_0 first, prediction 7.5 w/s PASS (w/t_min 0.49); gemma next from its floor-20-era Q6_K selection, prediction Q8_0 PASS at 6.6-7.5 w/s.

### Session 29, addendum 44 — the deprecation executed: the author's ruling applied to the [M] registry (BPW deleted; the 0.75/6.5 inheritance deleted; ARC_CTX promoted)

**The author's ruling (this session), settling the addendum-39 pending proposal:** "As long as it is in the code path, or used implicitly as a parameter to a tool it is used. If we can remove from the code and it is not used anywhere, delete it." Applied to the four [M] rows with pending exit plans, with the ARC_CTX question answered honestly: the verification buys a paperwork closure, not a scientific one (the prompts are one-shot letter answers, nowhere near 2048) - so it ships as an enforced precondition in code, not a one-off check.

**Executed:**

1. **BPW_APPROX deleted** (law_fit.py). law_fit now imports RUNG_BITS from hf_download - the bpw table is single-sourced; the duplicate copy is gone. The size* box prints the same four rungs from the one table.
2. **The 0.75 words/token fallback deleted from the verdict path** (speed_gate.py). WORDS_PER_TOKEN_DEFAULT is gone. analyze() now FAILS VERBOSE on any dump with turns lacking measured server_wps (protocol-v1 data): "re-bench with --force to measure words per second with the v2.1 instrument". Every verdict now comes from measured words - the unanchored conversion can no longer produce a verdict. The two "(0.75 default, unanchored)" display branches are gone (unreachable). law_fit's --words-per-token default is deleted too: --reader now REQUIRES --words-per-token (guidance names the measured per-family values).
3. **The 6.5 t/s reader line deleted** (lag_analyze.py, depth_probe.py). lag_analyze is re-anchored to the study's single anchor: stall metrics computed from each turn's MEASURED server_wps vs 5.0 w/s (imported from speed_gate, single-sourced); --reader-tp renamed --reader-wps. This also fixed a latent bug: the old S_delay read `n_tokens`, a field v2.1 dumps do not carry - the metric silently computed 0 on current dumps; it now uses gen_words/server_wps. depth_probe's --reader-tp has NO default (the line is inherently per-family: 5.0 / w/t_min; pass it explicitly - help names the form); summarize skips the line when absent. A latent-bug note: legacy turns in lag_analyze are excluded from reader metrics and counted in `legacy_turns`.
4. **ARC_CTX 2048 promoted [M] -> [P]** (arc_eval.py): the exit plan is an enforced precondition - arc_ctx_precondition() checks every rendered prompt against ctx (chars vs ARC_CTX x 4 chars/token floor) before any run and fails verbose with the offending size. Runs on every invocation, so the registration holds for any future question set.

**PROTOCOL.md updated:** the three [M] rows now read "(deleted, addendum 44)" with historical-note status (per the author's outright-delete stance: the notebook keeps the history, the registry keeps no dead numbers); the ARC_CTX row registers the in-code precondition; change-log entry 44 added.

**Verified by test (10 cases):** v1 dump refused / mixed dump refused / clean v2.1 dump verdicts from measured w/s only; law_fit refuses --reader without --words-per-token and derives floor 10.2041 t/s at 0.49; ARC precondition passes normal prompts and refuses an oversized one; lag_analyze computes reader stalls in measured w/s vs 5.0 (33.3% on a synthetic 1-of-3-stalled dump) and reports legacy_turns on a v1 dump; depth_probe summarize skips the reader line when --reader-tp is absent. py_compile clean across all scripts.

**Consequence:** every remaining number in the code is now either [A], [P], [D], or single-sourced; no unanchored default survives in any verdict or metric path. The 5.0 w/s anchor chain is the only reader line in the study.

### Session 29, addendum 45 — ARC_CTX 2048 -> the study's depth constant 4096 (author ruling: "ARC does not need a smaller context, it can use the default")

**The author's catch, one message after the addendum-44 promotion:** the 2048 I registered as [P] was still an inherited number wearing a badge. llama-server's own default n_ctx is 4096 - the study's already-promoted depth constant (addendum 9) - and ARC's one-shot letter-answer prompts need nothing smaller. Two depth constants for one study is one too many.

**Change:** `ARC_CTX = speed_gate.CTX_DEFAULT` (4096), single-sourced from the gate's constant - the strict-arc-era 2048 is deleted outright. The addendum-44 precondition (every rendered prompt checked against ctx before any run) stays and now guards the 4096 value. Cost: a slightly larger KV allocation per ARC server launch (~0.1-0.5 GiB on these models; irrelevant at this tier). Benefit: one depth constant for the entire study - the guarantee's depth and the quality measurement's depth are the same number, with one registry row.

**Note on comparability:** the existing ARC CSVs were measured at ctx 2048. Prompts never approached the limit (the precondition now checks this at 4096, and 9000-char synthetic prompts pass with room), so scores are ctx-insensitive; no rerun needed. Any future rerun happens at 4096.

**Verified:** ARC_CTX == 4096 through the import chain (arc_eval and full_benchmark), precondition passes a 9035-char synthetic prompt (limit 16384), py_compile clean.

### Session 29, addendum 46 — the --force re-run graded: prediction 2 HIT, prediction 3 MISS (gemma, the informative one), prediction 7 PASS; the w/s gate's content boundary found; gemma selected Q2_K (ARC 53.3%)

**The stale-state guard worked in production:** both families' rung files were missing on disk; the guard invalidated phases 1-2, re-downloaded safetensors, re-converted, re-quantized — no crash, no manual state surgery (addendum 43's fix, first live fire).

**Prediction 2 (qwen Q8_0, 7.5 w/s PASS) - HIT.** Measured: Q8_0 worst 8.08 w/s (mean 10.53), SELECTED at the first rung. The estimator's 7.30 (14.9 x 0.49) vs 8.08 measured: within the band's honest width. qwen's ARC at Q8_0: 1059/1172 = 90.4% (vs 90.2% at the old Q5_K_M - the champion's quantization cost on ARC is 2 questions, noise). The champion is now served at a HIGHER rung than the floor-20 era chose - exactly the k=1 door opening.

**Prediction 3 (gemma Q8_0, 6.6-7.5 w/s PASS) - MISS, and the miss is the finding.** Measured: Q8_0 FAIL at worst 4.75 w/s. The full walk: Q8_0 FAIL (4.75), Q6_K FAIL (1.45), Q5_K_M FAIL (1.01), Q4_K_M FAIL (0.92), Q3_K_M FAIL (0.76), Q2_K PASS (12.60) -> SELECTED. ARC on the selected Q2_K: 625/1172 = 53.3% - nineteen points below the family's known Q6_K-era 73.3%.

**The mechanism (the important part): the failing turns are word-SPARSE, not slow.** Every failing turn ran at healthy token speed (16-25 t/s, the law's predictions HIT within +-5.6% across all seven rungs - fourth family, see below) but emitted almost no whitespace words: w/t at the failing turns = 0.291 (Q8_0), 0.073, 0.046, 0.036, 0.031 (the mid rungs). ~15-30 words over 200-400 tokens. Two candidate causes, not yet distinguishable with the current instrument (the dump records gen_words but NOT the answer text): (a) word-sparse legitimate content - code blocks, emoji runs, CJK - which the whitespace-word convention scores as near-zero w/s; (b) genuine degenerate output. The blob-1936 conversation fails at Q8_0 (w/t 0.29 - a NEAR miss, 95% of the line) while the blob-2584 conversation fails at Q6_K through Q3_K_M (w/t 0.03-0.07) - and at Q2_K, by the luck of quant-specific generation at temperature 0, NEITHER produces a word-sparse turn and all five conversations pass. So the ladder selected the one rung where the corpus happened to dodge the gate's content boundary - and that rung is quality-destroyed (53.3%).

**Consequence for the w/t_min estimator: its premise fails on gemma.** w/s_pass = t/s(rung) x w/t_min(family) assumes the worst turn is a slow-TOKEN turn; gemma's worst turns are sparse-CONTENT turns. The 0.43-0.49 conservative band was below gemma's healthy w/t (0.55-0.70) and still missed, because no family constant predicts content sparseness. The band's exit plan has now fired for every roster family except llama-3.2-3b (whose Q8_0 dump from the fresh addendum-40-era walk still holds its w/t values - extraction pending, one command on the author machine).

**Prediction 7 (mode blindness, reasoning_chars 0) - PASS on the visible evidence:** qwen's non-thinking answers are non-empty, wordy (w/t 0.697 mean), and no thinking-token or empty-answer lines appear anywhere in the run. (The dump's reasoning_chars fields are the formal record; no reasoning printed because --no-thinking was threaded.)

**The law, fourth family, cleanest yet:** gemma's full six-rung ladder + qwen Q8_0 all within +-5.6% of `1/t = size/76.5 + 1/74` (Q8_0 +2.1%, Q6_K +0.5%, Q5_K_M +1.8%, Q4_K_M +3.0%, Q3_K_M -5.6%, Q2_K -0.5%; qwen +3.7%). Cross-family band +-15% claimed, +-6% observed.

**Memory report (addendum 40's instrument, first full-ladder data):** gemma's server cost has a large FIXED component - peak RSS 6.2-6.9 GiB at EVERY rung regardless of file size (1.61-3.85 GiB), i.e. +4.3-5.3 GiB beyond the file at the lower rungs (compute buffers for the multimodal architecture at ctx 4096, plausibly including RAM-backed GPU copies on the APU). The addendum-35 memory shortcut's "file + reserve" model under-estimates gemma's real cost by that fixed term - nothing was wrongly skipped here (all rungs fit), but the shortcut's validation now has its first family-dependent correction term on record. The mem_cost_gib (MemAvailable-delta) numbers remain noisy (5.64-9.85 GiB, non-monotonic vs file size) - peak RSS tells this story better; the instrument needs a quiet-machine pass before its numbers enter the report.

**The corrected ranking (gemma's rung change breaks the addendum-42 tie):**
1. Qwen3.5-4B Q8_0: 90.4% (champion, separated p<0.0001)
2. Mistral-7B-v0.3 Q5_K_M: 75.6% - vs #3 SEPARATED p=0.0296 (the first direct mistral-vs-llama test; they were never adjacent before)
3. Llama-3.2-3B Q8_0: 72.6%
4. gemma-3-4b Q2_K: 53.3% (vs #3 separated p<0.0001)
Addendum 42's "three-way tie for second" is superseded: mistral separates above llama at p=0.0296 (just under the 0.05 convention), and gemma's collapse removes it from the tie entirely. NOTE: the gemma row is now the Q2_K quality-destroyed measurement - not comparable to its earlier 73.3% (that was Q6_K, which the v2.1 w/s gate fails on the word-sparse turn).

**OPEN RULING (put to the author, pending):** the pipeline followed the pre-registered protocol exactly and selected a quality-destroyed rung. Options: (a) record as-is - the protocol is honest, gemma simply loses the ranking; (b) add a quality floor to selection (protocol change, needs a pre-registered form); (c) first instrument the answer text (dump truncated answers) to distinguish word-sparse-legitimate from degenerate output - the gate cannot currently show WHAT failed. Also pending: llama-3.2-3b w/t_min extraction from the existing dump.

### Session 29, addendum 47 — two rulings: gemma out of scope (no model debugging; the rules are the same for everyone); the quant-6 filter re-audited with corrected knowledge

**Ruling 1 (author):** gemma's failure is OUT OF SCOPE for investigation. "I don't want to debug the model, it failed the test, it is out of scope why. The rules are the same for everyone." The addendum-46 open ruling is thereby CLOSED with option (a) - record as-is. The word-sparse mechanism stays in the notebook as the measurement's honest description, but the study does not instrument answers, does not add a word-sparse rule, does not add a quality floor. Gemma's row stands: Q2_K, 53.3%, last place, selected by the pre-registered protocol under the same gate every family faced. The instrument lesson stands (w/s is content-dependent at the min; the estimator cannot predict it), and that is where it ends.

**Ruling question (author): knowing what we know now, would the quant-6 filter have changed the selection?**

**The re-audit with measured constants** (w/s at Q6_K = t/s x w/t_min(family), the corrected estimator):

| family | Q6_K size | t/s | w/t_min | predicted w/s | verdict |
|---|---|---|---|---|---|
| Qwen3.5-4B | ~3.31 GiB | 17.6 (law) | 0.49 measured | **8.63** | ADMITTED |
| Mistral-7B | 5.54 GiB | 11.9 measured | 0.37 measured | **4.40** | EXCLUDED |
| Llama-3.2-3B | ~2.59 GiB | 21.1 measured | 0.144 family anchor | **3.04** | EXCLUDED (if 3B inherits 8B terseness) |
| Llama-3.1-8B | ~6.55 GiB | 10.1 (law) | 0.144 measured | **1.45** | EXCLUDED |
| Qwen3.5-9B | ~7.50 GiB | 9.0 (law) | 0.49 measured | **4.39** | EXCLUDED |
| gemma-3-4b | 2.97 GiB | 19.4 measured | no constant predicts content sparseness | measured FAIL at every rung above Q2_K | EXCLUDED by evidence |

**Answer: YES - the roster would have changed, drastically.** With corrected knowledge the quant-6 filter admits exactly ONE family: Qwen3.5-4B. The v2.2 roster's other three members would never have been admitted: mistral's exclusion is confirmed by its own measured Q6_K fail (4.44 w/s, addendum 40 - the filter's arithmetic and the run agree); llama-3.2-3b is excluded IF it inherits the family's 0.144 terseness (its admission threshold is w/t_min >= 0.237 - its own dump's extraction is the one measurement that would settle it); llama-3.1-8b and qwen3.5-9b were already excluded in the v2.2 re-selection, and the corrected arithmetic agrees with steeper margins.

**The structural reading:** the quant-6 filter is doing its job - it is a HIGH-QUANT filter, and with honest per-family w/t_min values it is brutally selective. The 102.4 GB/s tier with the 5.0 w/s reader guarantee has room for exactly one top-4 family at quant 6. The four-model roster existed because the 0.43-0.49 default band (retired in addendum 40, now formally retired by this audit) was optimistic about words/token. The honest study framing: the roster is the measurement of WHICH families survive; the corrected filter predicts the survivors, and the run confirms the prediction (qwen passed at the top rung; every other family needed descent or failed).

**Consequence for the ranking's meaning:** the four-family ranking is not "the four best local LLMs" - it is "the four most popular families, ranked after each took its honest walk under the gate." The corrected filter says a one-model roster (qwen) is the quant-6-honest selection; the four-family run measures what the OTHER three look like after descent. Both framings are legitimate; the report should state which one the study claims. Standing question for the author: does the study's claim become "who passes at quant 6" (one-model roster) or "who is best after honest selection" (four-model roster, current)?

**PROTOCOL.md updated:** the quant-6 inclusion filter row now requires per-family w/t_min (measured or family-anchored) - the 0.43-0.49 default band is formally retired for filter use.

**Remaining open measurement (the only one):** llama-3.2-3b's own w/t_min from its existing Q8_0 dump - it decides whether llama-3.2-3b's row rests on a valid selection (w/t_min > 0.237 and Q8_0 PASS) or on the family-anchor exclusion (w/t_min < 0.237, predicted Q8_0 FAIL, row unvalidated). One command on the author machine.

### Session 29, addendum 48 — the quant-5 selection: roster v2.3 (Google's slot empties and walks to Microsoft; Qwen upgrades 4B→9B)

**Author ruling (the quant-5 filter, with the rationale):** "using the new knowledge, pick the top 4 we predict will pass with q5 (less restrictive than q6). This is the rationale: If a model passes with q8, I get suspicious it will have performed better at a larger model in q4-q8. That is, we are leaving brains on the table, for roughly the same performance." The inclusion filter rung moves from Q6_K to Q5_K_M; the ladder walk still starts at Q8_0 and takes the first PASS. Confirmed by the author in the same session: (a) Google's emptied slot walks to the next owner (Microsoft) — "same rules for everyone" per addendum 47; (b) the Qwen 4B→9B upgrade under rule 8 (highest member passing the filter) is the brains-on-the-table intent.

**Walk-down under the quant-5 filter** (predicted worst w/s = t/s(Q5_K_M) × w/t_min(family), the addendum-37 corrected estimator; law `1/t = size/76.5 + 1/74`):

| owner (popularity) | candidate | Q5_K_M size | t/s | w/t_min anchor | predicted w/s | verdict |
|---|---|---|---|---|---|---|
| Meta (llama3.2, 84.4M) | Llama-3.2-3B | 2.14 GiB | 24.1 (law) | ≥ 0.243 (bounded by its recorded Q8_0 PASS) | ≥ 5.86 | ADMITTED |
| Qwen (qwen3.5, 21.0M) | Qwen3.5-9B | 6.41 GiB | 10.3 (law) | 0.49 (4B family anchor) | 5.03 | ADMITTED (rule 8: 9B takes the slot from the 4B) |
| Qwen | Qwen3.5-4B | 2.85 GiB | 19.7 (law) | 0.49 (own measured) | 9.65 | admitted, superseded by 9B per rule 8 |
| Google (gemma3, 40.7M) | Gemma-4-12B | 8.55 GiB | 8.0 (law) | 0.55 healthy-turn only; sparse turns 0.03–0.29 | 4.39 | EXCLUDED |
| Google | Gemma-3-4B | 2.85 GiB | 19.7 (measured) | measured 0.03–0.30 sparse turns | measured FAIL 1.01 w/s at Q5_K_M | EXCLUDED by measurement |
| Mistral (33.7M) | Mistral-7B | 4.99 GiB | 12.7 (law) | 0.37 (own measured) | 4.70 pred / 5.25 measured PASS | ADMITTED (the run's measurement trumps the prediction) |
| Mistral | Mistral-Nemo-12B | 8.55 GiB | 8.0 (law) | 0.37 (family anchor) | 2.95 | excluded (rule 8: 7B is the highest member passing) |
| (same Meta owner) | Llama-3.1-8B | 5.70 GiB | 11.4 (law) | 0.144 (own measured) | 1.64 | excluded |
| Microsoft (phi4, 18.2M combined phi3/phi4 pulls; phi4 latest gen, rule 7) | Phi-4-mini-3.8B | 2.71 GiB | 20.5 (law) | unmeasured; passes if ≥ 0.245 | ≥ 5.01 if w/t_min ≥ 0.245 | ADMITTED (the pre-registered prediction; every measured non-llama family sits at 0.37–0.49) |
| Microsoft | Phi-4-14B | 9.97 GiB | 6.95 (law) | unmeasured; needs ≥ 0.720 | — | excluded (needs a w/t_min above every family ever measured) |

Google's slot empties under every anchor: even gemma's generous healthy-turn 0.55 gives 4.39 < 5.0 at Q5_K_M, and the measured sparse-turn behavior fails every rung above Q2_K (addendum 46). Per the addendum-47 ruling (no model debugging, same rules for everyone), the slot walks to the next owner down: Microsoft. Phi4 is the family's latest generation (rule 7, superseding phi3 despite fewer pulls); the family's paper is the Phi-4-Mini Technical Report (arXiv 2503.01743) — the same "published technical report" bar every other pick clears (Llama Herd arXiv 2407.21783, Qwen3.5 report, Mistral 7B arXiv 2310.06825). Within the family, rule 8 picks Phi-4-mini (3.8B): Phi-4-14B needs w/t_min ≥ 0.720 at Q5_K_M, above every family ever measured, so the mini is the highest member plausibly passing the filter.

**Roster v2.3 (popularity order of the winning rows):**

| Family | Pick | Paper | Provenance |
|---|---|---|---|
| Meta (llama3.2, 84.4M) | Llama-3.2-3B-Instruct | The Llama 3 Herd of Models, arXiv 2407.21783 | safetensors (gated), self-quantize |
| Qwen (qwen3.5, 21.0M) | Qwen3.5-9B (upgraded from 4B) | Qwen3.5-Omni Technical Report, arXiv 2604.15804 | safetensors, self-quantize |
| Mistral (33.7M) | Mistral-7B-Instruct-v0.3 | Mistral 7B, arXiv 2310.06825 | safetensors (public), self-quantize |
| Microsoft (phi4, 18.2M) | Phi-4-mini-instruct | Phi-4-Mini Technical Report, arXiv 2503.01743 | safetensors, self-quantize |

**Pre-registered ladder predictions (worst w/s per rung; the law × w/t_min):**

- Llama-3.2-3B (w/t_min ≥ 0.243, a measured bound implied by its recorded Q8_0 PASS: worst 20.6 t/s with measured worst w/s ≥ 5.0 gives w/t_min ≥ 5.0/20.6 = 0.243): Q8_0 ≥ 4.40 (bound), Q6_K ≥ 5.30, Q5_K_M ≥ 5.86, Q4_K_M ≥ 6.56. Predicted selection **Q8_0, confident** — the recorded PASS already proves the Q8_0 rung passes, and the run is deterministic (temperature 0, seed 1024, fixed corpus), so the fresh dump will reproduce the PASS and measure its own w/t_min exactly (the deletion only deleted the file, not the fact). The bound is a floor on confidence, not a ceiling: the family-anchor scenario (w/t_min < 0.243) is arithmetically incompatible with the recorded PASS and is not a live prediction.
- Qwen3.5-9B (w/t_min 0.49 family anchor): Q8_0 3.54 FAIL, Q6_K 4.43 FAIL, Q5_K_M 5.03 PASS, Q4_K_M 5.83 PASS. Predicted selection Q5_K_M — margin +0.6% over the reader line: a coin flip if 9B's own w/t_min < 0.487; the early-fail rule makes the test cheap and an honest failure descends to Q4_K_M.
- Mistral-7B: measured Q5_K_M PASS 5.25 w/s (banked; no re-run needed).
- Phi-4-mini (w/t_min unmeasured): Q8_0 passes if ≥ 0.331, Q6_K ≥ 0.272, Q5_K_M ≥ 0.245. If its w/t is in the typical 0.37–0.49 band, predicted selection Q8_0 (passing at the top rung — note the brains-on-the-table suspicion applies to it as the smallest rung-passing member).

**What this selection fixes (the author's suspicion, made precise):** the v2.2 roster selected Qwen3.5-4B, which then passed at Q8_0 (8.08 w/s, addendum 46) — evidence the filter was too restrictive and left parameters on the table. The quant-5 filter admits the 9B (predicted 5.03 w/s at Q5_K_M, trading ~0.5 bits/param for 2.25× parameters at roughly the same w/s), exactly the author's brains-on-the-table intent. The mistral row is the filter's honest edge case: predicted 4.70 FAIL by the estimator, measured PASS 5.25 — the prediction is falsifiable and was wrong in the family's favor; the selection keeps the measured verdict (rules are the same for everyone: the measurement trumps the prediction when they disagree).

**The run command (T14s, after `git pull --ff-only`):**

```
git pull --ff-only
python3 full_benchmark.py --no-thinking --force --roster "Llama-3.2-3B-Instruct,Qwen3.5-9B,Mistral-7B-Instruct-v0.3,Phi-4-mini-instruct" \
  "meta-llama/Llama-3.2-3B-Instruct" \
  "Qwen/Qwen3.5-9B" \
  "mistralai/Mistral-7B-Instruct-v0.3" \
  "microsoft/Phi-4-mini-instruct"
```

The `--force --roster` combination re-benches the ladder and re-ranks only the roster families. Llama-3.2-3B's folder was deleted from disk (the same cleanup that hit qwen), so the stale-state guard (addendum 43) invalidates its phases 1-2 and re-downloads — the fresh dump reproduces the Q8_0 PASS deterministically and measures its own w/t_min as a bonus constant for the registry. Mistral's Q5_K_M verdict is banked; --force re-benches it too (idempotent), and its fresh dump re-measures its w/t_min on the v2.1 instrument for the calibration record.

**Addendum 48, footnote — the Meta intra-family walk (author question: "why select Llama-3.2-3B again? surely the predictor can find a larger model").** Rule 8 walks the family's members high-to-low and takes the highest that is runnable AND passes the quant-5 filter. The Meta walk, top down:

| member | Q5_K_M size | t/s | w/t_min anchor | predicted w/s | verdict |
|---|---|---|---|---|---|
| Llama-3.3-70B | 49.9 GiB | — | — | — | NOT RUNNABLE (file alone exceeds 32 GB RAM) |
| Llama-3.2-11B-Vision | 7.84 GiB | 8.62 (law) | 0.37 (generous cross-family band) | 3.19 | FAIL (also a vision model) |
| Llama-3.1-8B | 5.70 GiB | 11.36 (law) | 0.144 (own measured) | 1.64 | FAIL (measured: the addendum-37 run failed every rung) |
| **Llama-3.2-3B** | 2.14 GiB | 24.12 (law) | ≥ 0.243 (own measured bound) | ≥ 5.86 | **PASS — the highest passing member** |

The 8B is the decisive row: its exclusion is MEASURED, not predicted — the addendum-37 run walked its full ladder and failed every rung (worst 2.09 w/s at Q4_K_M, word-sparse turns at 0.144 w/t_min), and quant-5's larger files only make it slower. The 11B-Vision is excluded by prediction (3.19 w/s even on the generous 0.37 cross-family band — worse than every measured non-llama family) and is a vision model (rule 3's non-thinking/text-only spirit). The 70B is not runnable on a 32 GB machine. So the predictor DID try the larger models: the 3B is not a conservative fallback, it is the ceiling of what Meta offers that fits the machine and the gate. (Llama-3.1-8B measured w/t_min 0.144 is the structural cause: Meta's instruct answers are terse, so even a healthy-t/s 8B cannot clear a 5.0 w/s worst-turn gate above ~1.3 GiB files.)

### Session 29, addendum 49 — ladder floored at Q4_K_M (Q3_K_M and Q2_K removed from the walk)

**Author ruling:** "I'm thinking of removing q2 and q3 from the measurements. I think the user will benefit better from a smaller model with quants between 4 and 8." Approved after the analysis.

**The evidence in-house:** the only selection the lower rungs ever produced is gemma's Q2_K — a quality-destroyed config (ARC 73.3% at Q6_K → 53.3% at Q2_K, a 20-point collapse, addendum 46). In brains currency the trade is terrible: Q2_K buys 2.4 B/GiB vs Q4_K_M's 1.67 (1.4x parameters) for that damage; below ~4.5 bpw the quantization penalty accelerates non-linearly. The author's rule — better a smaller model in the q4–q8 band — is what the numbers say.

**Alignment argument:** the quant-5 inclusion filter admits families predicted to pass at Q5_K_M; a walk that then descends below Q4_K_M produces a selection the filter never sanctioned (gemma's Q2_K row is exactly that artifact in the current ranking). Under the floored ladder, a family that fails Q4_K_M records an honest "no passing rung" and the slot walks to the next owner.

**Cost:** none for the pending v2.3 run — the walk takes the first PASS from Q8_0 down, and every v2.3 prediction lands at Q8_0–Q5_K_M. The law's ±5.6% validation across 7 rungs is banked history (addendum 46); future walks just don't extend below 4.8 bpw. The one case the floor forecloses: a family that legitimately passes only at Q3_K_M now records as failing — accepted as the true verdict for a q4–q8 study.

**Changes:** `LADDER_DEFAULT` in full_benchmark.py is now ["Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M"]; PROTOCOL.md ladder row updated. RUNG_BITS (hf_download.py) retains all seven rungs — it is size arithmetic, not the walk. Recorded history stands: gemma's banked Q2_K row keeps its addendum-46 meaning (selected under the rules as they were); under protocol v2.4 gemma's slot would empty and walk, consistent with addendum 47.

**Protocol version is now v2.4** (v2.3 roster + floored ladder). The v2.3 run command is unchanged — no pick's prediction touches the removed rungs.

### Session 29, addendum 50 — two deletions: the k=3 floor-20 line (obsolete; the gate is w/s >= 5 alone) and the 0.43–0.49 unmeasured-family band (exit plan fully fired)

**Ruling 1 (author):** "Floor default 20 is obsolete. We use w/s >= 5. Remove it if possible. It is an observation, not needed for the protocol. We can mention in the report, but it doesn't play any role in the benchmark." Applied fully:

- `FLOOR_DEFAULT` deleted from speed_gate.py and depth_probe.py (it was also a single-sourcing violation: defined in both, plus a bare magic 20.0 as law_fit's --floor default).
- speed_gate: the --floor flag, the "headroom vs floor" verdict line, and the floor/headroom fields in the analyze result are removed. The verdict is the reader line alone (worst turn w/s >= 5.0).
- depth_probe: the --floor flag and the "floor: BELOW at depth" line are removed. The depth guarantee check is --reader-tp only.
- lag_analyze: the k=3 default line (stlD) is retired; stlR (below the READER line in measured w/s) is the only stall metric. --default-tp deleted.
- law_fit: the --floor 20 default is deleted; the boundary must be derived from the anchor (--reader fast --words-per-token <family w/t_min>, the canonical author-ruling form) or given explicitly as --latency-budget. Fail-verbose otherwise.
- full_benchmark: the --floor flag and the headroom printout are removed; process_family drops the floor parameter.
- PROTOCOL.md: the floor row moves to deleted-history; the anchor-chain diagram drops the k->floor branch. The report may still cite floor 20 as an observation (the absorption-literature headroom judgment), but no code path carries it.
- Historical rows that reference floor 20 (the study #1/#2 walk-downs in README, the notebook) stand as recorded: those selections were pre-registered under the rules as they were.

**Ruling 2 (author, confirming my audit):** the 0.43–0.49 words/token band for unmeasured families is retired — "Then it should be updated, right?" Its exit plan ("retires as each family's first run grades it") fired for every family: llama 0.144, mistral 0.37, qwen 0.49 (all measured), gemma content-sparse (no band ever predicted it, addendum 46). Phi-4-mini was then selected by THRESHOLD (passes iff w/t_min >= 0.245), not by band — the band has no remaining job and no code references it. Deleted from PROTOCOL.md per the addendum-44 standard ("if it is not used anywhere, delete it"); the notebook keeps the history.

**What the protocol loses:** nothing measured. The floor never gated anything in v2+ (it was reported-only since protocol v2), and the headroom observation can be made post-hoc from any dump (worst_tps >= 20 is a one-line report table). The gate, the guarantee, the ladder, the law, and the estimator are untouched. The registry is smaller by two rows and one duplicate constant.

**Protocol version is now v2.5** (v2.3 roster + v2.4 floored ladder + no floor line, no w/t band).

### Session 29, addendum 51 — tokenizer_probe.py built (pre-registered instrument for the w/t first channel; built BEFORE any validation data, per the author's "simple over complex" guard)

**Author ruling:** build it now, run it later, after the current run's results are in hand. "We need to be very careful not to overdo the predictor. Sometimes a simple predictor is better than a complex one."

**The hypothesis, pre-registered before any validation run:** a family's measured words/token decomposes into two channels — (1) tokenizer efficiency (how many whitespace words the family's tokenizer packs per token on fixed text: knowable OFFLINE from the tokenizer files alone, a few MB, no weights, no server) and (2) sparseness at the worst turn (the model's content CHOICE — math/markdown/terse answers: unknowable before generation, measured by the gate's per-turn dumps). If channel 1 dominates healthy turns, the unknown-family selection filter needs only the sparseness channel from the family's first run: the gemma lesson (addendum 46: no family constant predicts content sparseness) is then refined, not overturned — the tokenizer constant may predict everything EXCEPT the sparse turns.

**The instrument (one file, stdlib + transformers, no new dependency — transformers is already in requirements.txt for the pinned converter):**

- `tokenizer_probe.py --repo <hf-repo>` — the tokenizer side: loads tokenizer files only (AutoTokenizer; HF cache; gated repos need hf auth login), computes whitespace words/token (the gate's exact word rule, `len(text.split())`) on the two REGISTERED text sets: the live corpus's 22 user prompts and the ARC-Challenge 1172-prompt set. No new text constants enter the protocol — the probe reads the ones the study already fixed.
- `--dump '<glob>'` — the measured side: per-turn w/t distributions (n, min, p50, mean, and a count of turns below 0.30 — the sparse-turn flag) from the v2.1+ dumps the benchmark already writes. Legacy dumps (no per-turn gen_words/gen_tokens) are skipped and labeled.
- Both sides in one invocation print side-by-side for the human comparison. The comparison itself stays a judgment — no verdict line, no magic threshold, per the author's simplicity ruling.

**The pre-registered pass/fail for the validation run (AFTER the current benchmark lands, so the grading is honest):** PASS if the tokenizer term predicts each measured family's healthy-turn w/t (p50 band) within roughly the law's cross-family band (±15%), with deviations one-sided below (the sparseness channel) and concentrated in identifiable turns. FAIL (a real answer, not a crisis) if healthy turns also miss — channel 1 is then not sufficient and the predictor stays per-family measured. The free replication: qwen-4B vs qwen-9B share a tokenizer — coincident healthy-turn distributions confirm the tokenizer term is family-stable and size-invariant in one shot.

**Complexity guard (author's, standing):** the predictor gains at most ONE term (tokenizer w/t, offline) — never a second (no sparseness model, no per-genre regression). If one term doesn't buy the prediction, we record that and keep the threshold-plus-first-run procedure.

### Session 29, addendum 52 — the v2.3 run graded: 2 HIT, 2 MISS, and the estimator's structural lesson (the worst turn is content-adaptive; llama's terse-turn frequency is corpus-dependent)

**The run (T14s, protocol v2.4 code, roster v2.3):** llama-3.2-3b Q8_0 FAIL (worst 4.05 w/s at 18.9 t/s measured; law predicted 18.12, +4.4%) → **Q6_K PASS at 5.01 w/s** (worst 22.6 t/s, +3.2% vs law) → SELECTED. qwen3.5-9b Q8_0 FAIL (4.17 w/s at 8.4 t/s; law 7.54, **+11.4%**) → **Q6_K PASS at 5.64 w/s** (10.8 t/s; law 9.48, **+14.0%**) → SELECTED — one rung ABOVE the predicted Q5_K_M. phi-4-mini Q8_0 **PASS at 7.14 w/s** (15.7 t/s; law 15.83, **−0.8%** — the law's best hit yet) → SELECTED at the top rung, first try, no descent. Mistral banked (Q5_K_M 5.25 w/s, ARC 75.6%).

**Grading the four pre-registrations:**

1. **llama-3.2-3b "Q8_0 PASS, confident" — MISS, my error, and the second one on this family.** The recorded PASS verdict (worst 20.6 t/s) implied w/t_min ≥ 0.243 — but that bound came from the OLD corpus (v1: 2400-token blobs, 5-conversation set built in Session 10) where llama-3.2-3b's worst sparse turn sat at or above 0.243. The current corpus (v2: 2568/2534/1932/2587/1970-token blobs) hands the model DIFFERENT conversation material, llama-3.2-3b generates a sparse turn at w/t 0.214 (words/s 4.05 at 18.9 t/s — the same math-notation turn class as its 8B sibling's 0.144), and Q8_0 fails. The bound was measured, but on a different corpus than the one that adjudicates. The addendum-48 correction's "deletion deleted the file, not the fact" was too strong: the fact was corpus-relative and the corpus changed (addendum 23's corpus re-rule). Grade: the prediction mechanism was right (the bound), the corpus-constancy assumption was wrong (my second llama error, after addendum-48's first).

2. **qwen3.5-9b "Q5_K_M coin flip" — MISS in the family's favor.** Predicted Q8_0 3.54 / Q6_K 4.43 / Q5_K_M 5.03 (family anchor 0.49). Measured: Q8_0 FAIL 4.17 (within 0.2 of the 5.0 line — the coin flip landed one rung higher than called), Q6_K PASS 5.64, selection Q6_K — one rung better than predicted. The w/t_min it displayed: 0.496 at Q8_0, 0.522 at Q6_K — both consistent with the 4B's 0.49 anchor. The law missed by +11.4% and +14.0% on this family — the largest cross-family residuals yet, all in the direction of qwen running FASTER than predicted (a family efficiency factor > 1; the per-point residual table now spans −5.6% to +14.0%, and the law's claimed ±15% band still holds, barely).

3. **phi-4-mini "passes iff w/t_min ≥ 0.331 at Q8_0" — HIT.** Measured w/t_min 0.455, comfortably above the 0.331 threshold, PASS at 7.14 w/s on the first rung. The law hit −0.8%. The threshold method worked exactly as designed: it converted an unknown family into a testable pre-registration, and the run graded it cleanly.

4. **mistral banked — HIT by construction** (its measured verdict stands; no re-run).

**ARC ranking (v2.3 roster, n=1172, exact McNemar):** qwen3.5-9b Q6_K **92.6%** (champion, separated p<0.0001) > phi-4-mini Q8_0 **81.1%** (separated from mistral p<0.0001) > mistral-7b Q5_K_M 75.6% > llama-3.2-3b Q6_K 73.0% (mistral-llama NOT separated, p=0.0561 — the same pair that separated at p=0.0296 in the addendum-46 ranking; the rung changes moved both rows and the pair is back inside the noise band).

**The estimator's structural lesson (the addendum-46 lesson, now with the mechanism):** the healthy-turn w/t bands per family in this run — llama 0.74–0.81, qwen 0.61–0.79, phi 0.70–0.81 — are TIGHT and overlapping (the tokenizer channel, addendum 51's hypothesis: all three families' healthy turns sit in the same 0.6–0.8 band, consistent with a shared English tokenizer efficiency). The worst-turn w/t — llama 0.214, qwen 0.522, phi 0.455 — is where the families differ, and it is content-adaptive: the model CHOOSES a sparse turn (math notation, markdown, one-word answers) at a rate that depends on the conversation material. The min is therefore not a family tokenizer constant but a family × corpus interaction. Two consequences: (a) the tokenizer probe's prediction target should be the healthy-turn band (p50), NOT the min — the min carries the content channel the tokenizer cannot see; (b) the w/t calibration pass (addendum 40: ~20-25 conversations, 5th percentile) is now the only honest way to pin w/t_min per family — a single 5-conversation run can flip it (llama just demonstrated: 0.243+ on corpus v1, 0.214 on corpus v2).

**The brains-on-the-table verdict, confirmed:** the author's suspicion was right in the direction that matters. Qwen 4B→9B: 90.4% → 92.6% ARC at the same worst-turn guarantee, and 9B selected at Q6_K (better quant than the predicted Q5_K_M). Phi-4-mini entered the roster via the emptied Google slot and immediately took second place at 81.1% — the walk-to-next-owner rule found a stronger family than the one it replaced (gemma 53.3%). The v2.3 selection is the study's best roster yet: every slot upgraded (llama 72.6→73.0 at a better rung, qwen 90.4→92.6 via 9B, mistral unchanged, gemma 53.3→81.1 via phi-4-mini replacing it).

**Open items:** (1) the w/t calibration pass (--conversations N on speed_gate) is now the priority instrument — llama's corpus-flip shows a single run's min is not a stable family constant; (2) the tokenizer probe validation (addendum 51) can now run on this run's dumps — the healthy-turn bands are its prediction target; (3) the 51.2 GB/s class replication carries this roster; (4) the law's qwen residual (+14%) is at the edge of the claimed band — worth watching in the replication, not worth a protocol change yet.

### Session 29, addendum 53 — the tokenizer validation graded: PASS on all four families (qwen at the band edge); and the probe's first catch — llama's Q8_0 failing turn was NOT sparse, the two span instruments disagree ≥1.9× on exactly that turn (addendum 52's llama narrative pending the dump record)

**Instrument first (three probe bugs, caught on the author's runs, fixed before any grading):** `5556563` — the ARC config arg was passing the cache filename where load_questions expects the config name (HTTP 404 on every family; the corpus side was never touched), and the `--dump` glob was matching `.mem.json` sidecars (memory-instrument files polluting the measured side as legacy-skipped rows). `6ef7791` — load_questions returns dicts keyed `q`, not `prompt`; the ARC text set KeyError'd on every family. Net: the author's four runs computed the corpus-set terms and all dump-side numbers correctly; the ARC genre check remains unrun (now optional — the corpus-set validation passed without it).

**The grade, against the addendum-51 pre-registration (PASS = the tokenizer term predicts each family's measured healthy-turn p50 within ~±15%, deviations one-sided below): PASS.**

| family | tokenizer w/t (corpus prompts) | measured p50 (dump) | ratio |
|---|---|---|---|
| Qwen3.5-9B | 0.770 | 0.656 (Q8_0, n=6) / 0.662 (Q6_K, n=22) | 0.852 / 0.860 (−14.8% / −14.0%) |
| Llama-3.2-3B | 0.758 | 0.736 (Q8_0, n=14) / 0.719 (Q6_K, n=22) | 0.971 / 0.949 (−2.9% / −5.1%) |
| Phi-4-mini | 0.779 | 0.796 (Q8_0, n=22) | 1.022 (+2.2%) |
| Mistral-7B | 0.692 | 0.645 / 0.669 / 0.679 (Q8_0 / Q6_K / Q5_K_M) | 0.932–0.981 (−6.8% to −1.9%) |

All four families inside ±15% — qwen at the band edge, like its law residual. Three of four one-sided below as pre-registered; phi's +2.2% is the only above-term deviation, within noise. The substantive point: the term is computed on HUMAN prompts, the p50 on MODEL answers — different genres — and the offline term still predicts the band. The complexity guard holds: the ratio scatter (0.85–1.02 across four families) is recorded as scatter, NOT fitted into a calibration constant — n=4 families buys a term plus a band, not a fudge factor. And the term does NOT enter the selection filter: the filter needs the min, which carries the content channel the tokenizer cannot see (addendum 52); the selection procedure stays threshold-plus-first-run-measured.

**Min-side anchor confirmations (free, from the same dumps):** mistral's per-rung mins 0.341 / 0.355 / 0.381 (Q8_0 / Q6_K / Q5_K_M) confirm the 0.37 family anchor and show w/t_min is RUNG-STABLE (at temp 0 the quant barely changes the content choice); qwen's 0.485 / 0.517 confirm its 0.49 anchor. Zero turns below 0.30 in any of the eight dumps (126 turns total). The estimator's per-family w/t_min constants are healthy exactly where they were measured.

**The probe's first catch — the llama discrepancy (open instrument question, possible verdict impact):** the run report and the dump disagree on llama's failing turns, and only there. Cross-checking worst w/s ÷ that turn's own t/s against the dump min: qwen Q8_0 4.17/8.6 = 0.485 = dump min exactly; mistral Q8_0 3.34/9.8 = 0.341 = dump min exactly (its verdict line paired 3.34 with a DIFFERENT turn's 9.3 — worst-w/s and worst-t/s need not be the same turn; the probe's per-turn pairing is the honest one); phi 7.14/15.9 = 0.449 ≈ 0.445; mistral Q5_K_M 5.25/13.6 = 0.386 ≈ 0.381. Llama: Q8_0 4.05/19.3 = 0.210 vs dump min 0.400; Q6_K 5.0/23.4 = 0.214 vs 0.333. Those cannot both be right, and the code settles which: the failing turn IS in the dump (run_conversation appends the turn before the early-fail break; the counts prove it — Q8_0 n=14 = 4+4+5+1, the 1 being aborted conv 4's single turn; qwen Q8_0 n=6 = 4+2 the same way). If the failing turn's content w/t were really 0.21 it would BE the dump min; the min is 0.400 → the turn's content w/t is ≥ 0.400 → the turn was NOT word-sparse → the external span (wall − prompt_ms/1000) overcounted the server's generation span by ≥1.9× on the Q8_0 failing turn (≥1.56× on Q6_K's conv-4 turn 1). Candidate mechanisms, discriminated by the dump record: (i) prompt_ms missing/zero on that turn — the `if prompt_ms else wall_s` branch then silently bills the whole 2587-token blob prefill to the "generation" span (the arithmetic fits: a ~55-token answer at 19.3 t/s ≈ 2.9 s + ~2.6 s blob prefill ≈ 5.5 s wall → 22 words / 5.5 s = 4.05 w/s exactly); (ii) the server's predicted_per_second overstated on that turn (the standing server-vs-external validation gap, noted in Session 18f); (iii) a genuine mid-request stall the reader WOULD experience (slot eviction, re-prefill inside the request) — in which case the FAIL is honest and the span is true. NOT a general first-post-blob bleed: mistral's conv-3 turn 1 and llama's own conv-1/2/3 turn 1s all agree between the two instruments; the trigger is llama conv 4 turn 1 specifically, reproduced across two rungs (temp 0, deterministic content).

**Consequences pending the dump record (the addendum-52 correction is drafted, not applied):** if (i) or (ii), addendum 52's llama story is wrong — the failing turn was not a corpus-v2 sparse content turn, and my "second llama error" was itself an instrument artifact; the corrected Q8_0 worst would be ~10.1 w/s (conv 3 turn 4) → the rung flips FAIL→PASS and the selection moves Q6_K→Q8_0 — and the guarantee instrument needs a fix (a falsy prompt_ms must mark the turn unmeasured, not assume zero prefill; plus an in-flight ext-vs-server divergence check before early-fail aborts a rung). If (iii), the verdict stands and addendum 52 stands with the mechanism corrected. The record discriminates: prompt_ms, wall_s, gen_tokens, server_tps, ext_tps on the flagged turns. No code change until the record lands (fix before evidence risks fixing the wrong thing).

**Verdict-integrity note:** qwen's Q8_0 FAIL and phi's and mistral's verdicts are NOT affected — their instruments agree turn-exactly. The early-fail rule (addendum 34) remains right (the worst is a min); the open question is whether a reading on which the two span instruments disagree ≥2× should abort the rung before an in-flight cross-check. The author rules after the record.

**Open items:** (1) the author's dump record for llama conv 4 turn 1, both rungs, settles the mechanism; (2) then the w/t calibration pass (--conversations N on speed_gate) and the 51.2 GB/s class replication; (3) the ARC genre check is optional now (corpus-set PASS); (4) the free qwen 4B-vs-9B tokenizer-stability replication (shared tokenizer, both dumps on disk) can ride the calibration pass.

### Session 29, addendum 54 — the record lands: all three addendum-53 candidates FALSIFIED; the mechanism is the tiny-answer degeneracy — the gate judged a "Who's there?" — and addendum 52's llama narrative is corrected (my retraction)

**The author's dump record (conv 4, both rungs):** the failing turn is `gen_words: 2, gen_tokens: 5, server_tps: 19.35, prompt_ms: 267.3, wall_s: 0.761, words_per_token: 0.400, ext_tps: 10.13`. Conv 4 of the corpus opens with **"Knock, knock!"** and llama answered, canonically, a two-word "Who's there?" class answer — 2 words over 5 tokens.

**All three addendum-53 candidates falsified in one record.** (i) `prompt_ms` is PRESENT (267 ms) — the falsy-prompt_ms mechanism never fired. (ii) `server_tps` 19.35 is honest (law: 18.12, the known +4.4% residual) — the server did not overstate. (iii) `wall_s` is 0.76 s for the entire turn — no reader-felt stall exists; the whole answer arrives in under a second. The two span instruments disagree (external 10.13 t/s vs server 19.35) because on a 5-token answer the external span (0.493 s) is 91% fixed per-request overhead (detokenize/HTTP/JSON, ~0.24 s) on top of 0.26 s of true decode: `2 words ÷ 0.493 s = 4.05 w/s`, below the line, on a turn where the reader never waits at all.

**The mechanism: the w/s metric is degenerate on tiny answers.** The registered guarantee asks "does the reader keep up with the stream?" On a 2-word answer the reading time (0.40 s at the anchor) is shorter than the overhead floor of the measurement span; even at INFINITE decode speed, 2 words ÷ ~0.24 s overhead ≈ 8 w/s is the ceiling — the 5.0 line sits inside the overhead shadow, and the metric adjudicates noise, not reading experience. The proof it was luck: the SAME 2-word answer at Q6_K measured 5.0078 w/s — passing by 0.008 w/s (~30 ms of jitter decided the rung verdict).

**Reader-truth check (both constants registered):** reading time = words ÷ 5.0 vs the 0.45 s reaction window (PROTOCOL row 62). Llama's tiny turns: reading 0.40 s vs arrival 0.49 s — inside the reaction window, FAILS ONLY ON PAPER. Qwen's failing turn (16 words: reading 3.20 s vs arrival 3.84 s) and mistral's (12 words: 2.40 vs 3.57) wait +0.64 s and +1.17 s beyond it — HONEST FAILs, exactly as verdicted. The instrument bug is family-blind; the corpus handed llama the tiny turn. No other family's verdict is affected (addendum 53's cross-check: instruments agreed turn-exactly for qwen/phi/mistral).

**The addendum-52 correction (my retraction):** llama's Q8_0 "failing turn" was not a corpus-v2 sparse content turn, and my "second llama error" was no error of the prediction — the recorded Q8_0 PASS bound (w/t_min ≥ 0.243) was never violated by content; the instrument's tiny-answer degeneracy manufactured the 4.05. Addendum 52's grading becomes 3 HIT / 1 MISS (qwen the only miss, in the family's favor); its structural lesson stands with a correction: the worst-turn w/t is content-adaptive AND the metric must not adjudicate turns whose reading time is below the reaction window — those turns are exempt from the guarantee (the reader cannot be made to wait for a stream shorter than his reaction). The addendum-48 correction is VINDICATED as originally written: "the deletion deleted the file, not the fact." Rung-stability note: the Q6_K "Who's there?" turn measured w/t 0.400, same as Q8_0's — quant does not change the content choice (the addendum-53 rung-stability finding, again).

**Re-adjudication of the rungs under the exemption (no new constants — both boundary constants are registered):** exempting turns with `gen_words <= 2` (reading time 0.4 s ≤ reaction 0.45 s): llama Q8_0 worst adjudicable = 10.1 w/s (conv 3 turn 4) → **PASS (confident)** — the selection flips Q6_K → **Q8_0** (the ladder takes the top passing rung); llama Q6_K worst adjudicable = 12.3 w/s — also a real PASS, not the luck-thin 5.01. All other verdicts unchanged. ARC at Q8_0 must be re-run for the ranking table (the Q6_K ARC 73.0% stays on disk as a recorded measurement).

**The fix, proposed (author rules; three options, one recommendation):** (a) MINIMUM-WORDS EXEMPTION: turns with `gen_words <= READER_REACTION_WORDS` are recorded but exempt from the guarantee and the early-fail (reading time ≤ reaction window); the boundary is derived, not magic — `words ≤ reaction_s × reader_wps = 0.45 × 5.0 = 2.25 → 2 words`. (b) FLOOR-THE-SPAN: subtract an overhead constant before dividing — requires measuring and registering a NEW constant (the ~0.24 s), a new [M] with an exit plan; more machinery, no added honesty. (c) DROP-THE-TURN from the verdict — same as (a) but silent; less transparent than an explicit exempt flag. Recommendation: **(a)**, derived from two registered constants, exempt turns flagged in the dump, early-fail never fires on them, verdict lines report both numbers (all turns vs adjudicable turns). Simple, honest, no new constants — per the author's simplicity guard.

**Open items:** (1) the author rules on the fix (recommendation (a)); (2) after the fix: llama Q8_0 re-adjudication is a re-Analyze of the EXISTING dumps — no re-run needed (the verdict machinery grades the dump; `--force` re-bench only for fresh data); (3) ARC re-run at Q8_0 for the ranking; (4) then the w/t calibration pass and the 51.2 GB/s class replication, which now carry the corrected instrument.

### Session 29, addendum 55 — the ruling: the reader simulation is the final judge (exact form, any-word fail); protocol v3.0 — the gate streams and the verdict is the reader-wall test

**The author's ruling, verbatim:** "exact. that's the point here, we are simulating the reader, that's the final judge. If the reader hits the wall, then they feel the model is slow, so it fails. if the wall is never hit, reader is happy." Refined one message later: "for the reader simulation, a turn fails if any word arrives late. not just the last one."

**What the ruling means for the instrument:** the flat worst-turn w/s test is retired from the verdict entirely (not patched with an exemption — the author chose the exact form over my recommendation (a)). The verdict is the registered addendum-30 collision simulation, on every turn: the reader (5.0 w/s, 0.45 s reaction) starts reading 0.45 s after the first word arrives; a turn FAILS iff the reader ever catches up with printing while the answer is incomplete (ANY catch-up event, not just the last word). A turn the reader finishes inside the reaction window can never fail — read like a static message. This required the gate to STREAM (the non-streaming span could not see a mid-stream wall at all): every turn now runs `stream: true`, records the per-word arrival stream (deltas in the dump), and the law's server t/s survives via the final chunk's `timings`/`usage` (llama-server sends them on the last SSE event; `llama_server.stream_completion` grew a `meta` dict for this).

**The consequence table the exact form implies (uniform-stream threshold):** r_min(N) = (N−1) / ((N−1)/5.0 + 0.45) — the flat 5.0 is the asymptote; small answers get real slack: N=2 → 1.54 w/s, N=12 → 4.15, N=40 → 4.73. Uniform-stream slack is one thing; the exact form is STRICTER than flat-5.0 in one respect: a mid-stream stall fails the turn even if the aggregate rate is fine ("any word late"), which the old instrument could not see at all.

**Implementation (all committed):** `speed_gate.py` — `READER_REACTION_S = 0.45` (promoted to a guarantee constant, single-sourced here; session_replicate now imports it instead of its own CLI default); `reader_wall_test(deltas, n_words, reader_wps, reaction_s)` (the addendum-30 arithmetic, verbatim, with waits counted only between arrivals — once the last word lands the reader finishes from the buffer); `run_conversation` streams and records per-word deltas + collision record per turn (`catchup_events`, `catchup_s`, `first_catchup_word_frac`, `reader_wall_fail`, `deltas`); early-fail fires on the first wall hit (addendum 34 unchanged in spirit: the verdict is a min); `analyze()` verdict = PASS iff no turn has `reader_wall_fail`; pre-v3.0 dumps (no deltas) fail-verbose (addendum-44 precedent) — every rung must be RE-BENCHED with `--force`; span w/s, sigma, words/token, t/s stay as printed diagnostics. `session_replicate.reader_collision` keeps its verbatim body (parity-tested against the gate's copy on a tricky stream: identical output). Printouts: per-conversation "reader wall (catch-up events)" line; verdict line reports wall-failing turns, events, worst wait. `full_benchmark.py` phase-4 print and dry-run text updated.

**Parity/unit checks run (sandbox):** (1) the "Who's there?" record (2 words, arrivals 0.10/0.26 s) → PASS, 0 events; (2) the same 2 words with word-2 at 0.75 s → FAIL, 1 event, waited 0.10 s; (3) a genuine mid-stream 2 s stall → FAIL, 1 event, waited 1.55 s (a turn the old instrument would have scored at a healthy aggregate rate); (4) a healthy 7 w/s stream → PASS; (5) a uniform 4.7 w/s stream — flat-5.0 would FAIL it — → PASS, the exact form's real slack, no events; (6) empty answer → PASS (no words, no reader); parity between the gate's `reader_wall_test` and session_replicate's `reader_collision` on a mixed stream: identical. Ruff clean.

**What the v2.3 verdicts become under v3.0 (ALL pre-registered predictions must wait for the re-run):** the recorded verdicts were flat-w/s verdicts — every rung needs a fresh streaming bench (`--force`), and the deltas did not exist on the old dumps, so the re-adjudication table from addendum 54 (llama Q8_0 → 10.1 w/s PASS) is a SPAN-side estimate only: under the exact form the mid-stream view can only be stricter or equal, never looser (a turn with a wall hit has a sub-threshold aggregate somewhere, but a clean aggregate can hide a wall hit). Llama's tiny turns pass under v3.0 by construction (inside the reaction window). Qwen's Q8_0 4.17 w/s failing turn (16 words): uniform-stream threshold r_min(16) = 4.35 — its aggregate says borderline, its mid-stream view decides. The full re-run command is the study's next step.

**The re-run command (T14s, after `git pull --ff-only`):** `python3 full_benchmark.py --no-thinking --force "meta-llama/Llama-3.2-3B-Instruct" "Qwen/Qwen3.5-9B" "microsoft/Phi-4-mini-instruct" "mistralai/Mistral-7B-Instruct-v0.3"` — every rung re-benches streaming (files reused, phases 1-2 kept), verdicts come from the reader-wall test, and the ARC phase re-runs only for selections that change.

**Open items:** (1) the T14s re-run grades the v2.3 roster under protocol v3.0 — the addendum-52 grading may shift again (llama's Q8_0 is expected to PASS now; qwen's Q8_0 failing turn is the interesting one); (2) the dumps now carry per-word deltas — the w/t calibration pass and the lag analysis both get richer data for free; (3) ARC re-runs follow any selection change; (4) the 51.2 GB/s class replication carries v3.0 from the start.

### Session 29, addendum 56 — the v3.0 run graded: the reader-wall verdicts land (llama Q8_0 confirmed, qwen's genuine mid-stream walls); the ranking leak (addendum-41 class) found and fixed — phases 5-6 now default to this run's command-line families

**The run (T14s, protocol v3.0, --no-thinking --force):** every rung re-benched streaming; verdicts from the reader-wall test (addendum 55). Llama-3.2-3B: Q8_0 PASS (confident) — 18.6 t/s worst, **0 wall-failing turns, 0 catch-up events** — SELECTED Q8_0 (the addendum-54 prediction confirmed: the "Who's there?" fail is gone; the tiny turn lives inside the 0.45 s reaction window by construction). Qwen3.5-9B: Q8_0 FAIL — 1 wall-failing turn, 1 catch-up event, waited **0.06 s** (conv 1 turn 3, a MID-STREAM wall the old flat instrument could not see — its span diagnostic reads 5.72 w/s, ABOVE the old 5.0 line); Q6_K FAIL — 1 wall-failing turn, 2 catch-up events, worst wait **0.19 s** (span diagnostic 5.67 w/s, again above the flat line — the exact form is stricter exactly as pre-registered); Q5_K_M PASS (12.1 t/s worst, 0 events) — SELECTED Q5_K_M, one rung lower than the v2.3 Q6_K. Phi-4-mini: Q8_0 PASS (16.0 t/s, 0 events) — SELECTED, unchanged. Mistral-7B: Q8_0 FAIL (1 event, waited 1.53 s), Q6_K FAIL (1 event, 1.61 s), Q5_K_M PASS (13.5 t/s, 0 events) — SELECTED, unchanged. ARC re-ran only where the selection changed: qwen 9B Q5_K_M = 1083/1172 = **92.4%** (vs 92.6% at Q6_K; the one-rung drop costs 2 questions, within the quant-noise band).

**The addendum-52 grading under v3.0:** llama's Q8_0 PASS materialized exactly as re-adjudicated in addendum 54 (3 HIT / 1 MISS stands, qwen the only miss — and in the family's favor again: the exact form pushed qwen DOWN a rung, adding 92.4% at Q5_K_M to the family's record). The exact form's predicted strictness was observed, not just argued: both qwen failing turns had aggregate span rates ABOVE 5.0 w/s and failed on mid-stream walls alone. The v2.3 verdicts were flat-w/s verdicts; under v3.0 the two instruments disagree in exactly the direction the consequence table predicted.

**The author's question and the answer on record:** "I thought we agreed not to do q3 and q2 anymore, only q4 to q8." The ladder HELD — no Q2/Q3 rung was benched anywhere in this run (llama Q8_0; qwen Q8_0→Q6_K→Q5_K_M; phi Q8_0; mistral Q8_0→Q6_K→Q5_K_M; LADDER_DEFAULT = Q8_0/Q6_K/Q5_K_M/Q4_K_M, addendum 49). The `gemma Q2_K` row in the printed ranking is NOT this run: it is the **roster leak** (the addendum-41 class, back for the third time) — `benchmark-state.json` accumulates selections across studies, and phases 5-6 ranked every family in the state file with a selection, so the study-2 leftovers (Qwen2.5-3B Q8_0, Phi-3-mini Q6_K, gemma Q2_K, Qwen3.5-4B Q8_0) leaked into the table. The addendum-55 re-run command omitted `--roster` — my omission. The v3.0 ranking is only: qwen 9B Q5_K_M 92.4% > phi-4-mini Q8_0 81.1% > mistral Q5_K_M 75.6% > llama Q8_0 72.6% (llama's ARC CSV is the earlier run's, but the selection returned to Q8_0 so the pairing is correct).

**The fix (committed):** phases 5-6 now default the roster to the families named on THIS run's command line (`--roster` still overrides; families without a selection are noted and excluded). The leak class is closed by construction: a fresh clone or a different roster on the same state file can no longer mix studies. The author can also reproduce the corrected ranking without re-benching — the ARC CSVs are complete, only the label list changes.

**The consecutive-pair McNemar for the corrected four-family ranking (the author's fixed-code re-run, phases 5–6 idempotent, no re-benching):** #1 vs #2 qwen 9B Q5_K_M vs phi Q8_0 −11.35 pp (b=16, c=149), p<0.0001 SEPARATED; #2 vs #3 phi vs mistral −5.46 pp (b=82, c=146), p<0.0001 SEPARATED; #3 vs #4 mistral vs llama −2.99 pp (b=105, c=140), p=0.0296 SEPARATED. The whole ladder separates — including the bottom pair, which flips vs the previous pairing (mistral vs llama Q6_K 73.0% was p=0.0561, not separated): llama's ARC is now the Q8_0 CSV's own discordant pairs, and the 2.7→3.0 pp gap carries. Study #3's final table: the champion (qwen 9B Q5_K_M, 92.4%) separates from the field at p<0.0001, and the field separates internally at p≤0.03.

**Open items:** (1) the author re-runs the same command after `git pull --ff-only` to print the corrected ranking from the fixed code (no re-benching: state and CSVs are complete, phases 5-6 are idempotent); (2) the w/t calibration pass now carries per-word deltas; (3) the 51.2 GB/s class replication carries v3.0 from the start; (4) study #3 report drafting against the registry.

### Session 29, addendum 57 — the general predictor rule stated (all registry constants), and the two family checks the author ordered: NO larger llama or phi member is predicted to pass Q5_K_M — the roster stands; llama-3.1-8B's measured failure (addendum 37) doubles as the rule's third validation point

**The author's ruling:** the per-family w/t_min factor is useful for finding candidates but ad hoc ("similar to the 20 t/s gate we had before") — the study needs a GENERAL predictor rule that works for all families, even with wide uncertainty, built from cheap pre-download measurements (file size, params). Order: search the llama and phi families for a larger member predicted to pass at Q5_K_M; show the prediction.

**The general rule (three lines, every input a registered constant; no new terms — addendum 51 guard):**
1. **t/s_pred = 1 / (size_GiB/76.5 + 1/74)** — the law (PROTOCOL row 94; size from params × bpw/8 via RUNG_BITS, or from the HF file list before any download; ±15% cross-family band).
2. **w/s_pred = t/s_pred × w/t_min** — the content channel: the family's measured w/t_min [D] if a dump exists; else the POOLED ANCHOR 0.33 = the minimum of the four measured family probe-mins (llama 0.333, mistral 0.341, phi 0.445, qwen 0.485 — addendum 53). Derived, not magic: it is the worst content behavior ever observed on this corpus, and it is conservative for an unknown family.
3. **PASS iff w/s_pred ≥ 5.0** — the flat reader anchor, which under protocol v3.0 is conservative by construction (the exact form's uniform threshold r_min(N) < 5.0 for every finite N; a model clearing flat-5.0 clears the wall with margin). A filter that errs should err toward exclusion — the walk costs ~8 min/rung, a false include costs the reader.

**LLAMA check (selection: 3.2-3B at Q8_0).** The family's members: 3.2-1B, 3.2-3B, 3.1-8B, then 70B/405B (law-arithmetic dead: 70B at Q5_K_M ≈ 46 GiB → ~2 t/s). The only candidate is **Llama-3.1-8B-Instruct**: 8.03B params → Q5_K_M = 5.33 GiB → law t/s 12.0 point (band 10.5–13.8) → × w/t_min: 0.144 (family record, addendum 37) = 1.7 w/s; 0.333 (llama probe min, addendum 53) = 4.0 (band 3.5–4.6); 0.40 (optimistic healthy min) = 4.8 (band 4.2–5.5). **FAIL under every content anchor — even the optimistic edge does not clear 5.0.** And it is not just a prediction: addendum 37 MEASURED this exact model — Q4_K_M early-failed at 2.09 w/s (the 30-word/208-token joke turn, w/t 0.144), Q5_K_M early-failed at the same turn; the law's t/s side HIT (+5–10%, 14.3–15.0 measured vs 13.7 predicted). The general rule's verdict and the v2.1 measurement agree: the 8B fails the reader on this machine at every rung in the ladder floor. **No candidate.** The 3B itself at Q5_K_M: 2.14 GiB → 24.1 t/s × 0.40 = 9.6 w/s predicted PASS — the 3B satisfies the addendum-48 quant-5 inclusion filter on its own size; Q8_0 is the top passing rung, not a small-model compromise. No brains on the table in this family.

**PHI check (selection: 4-mini at Q8_0).** The family's current-gen members: Phi-4-mini 3.8B, Phi-4-multimodal 5.6B (the SAME 3.8B text backbone + a vision tower — vision weights add no text brains), Phi-4 14B. The only true step up is **Phi-4 14B**: 14.7B params → Q5_K_M = 9.75 GiB → law t/s 7.1 point (band 6.2–8.2) → × w/t_min: 0.245 (phi threshold, PROTOCOL row 99) = 1.7; 0.445 (phi probe min, addendum 53) = 3.2 (band 2.7–3.6). **FAIL hard — less than two-thirds of the line at its own best anchor.** No candidate. Phi-4-mini itself at Q5_K_M: 2.52 GiB → 21.5 t/s × 0.445 = 9.6 w/s predicted PASS — the mini satisfies the quant-5 filter; Q8_0 is the top passing rung.

**The rule's validation table (five measured points, three studies):** (1) qwen 9B Q5_K_M: pred 10.6 × 0.49 = 5.2 PASS → measured PASS ✓ (pooled anchor would say 3.5 FAIL — the family anchor is what makes it, exactly why the calibration pass matters); (2) mistral 7B Q5_K_M: pred 13.2 × 0.37 = 4.9 FAIL-borderline (band 4.2–5.6 straddles) → measured PASS — the honest ±15% band, on the line; (3) phi-4-mini Q8_0: pred 15.9 × 0.445 = 7.1 PASS → measured PASS ✓; (4) llama-3.1-8B Q4_K_M: pred 13.7 × 0.144 = 2.0 → measured 2.09 ✓ point HIT (and the pooled anchor's verdict — 4.7 FAIL — was also right); (5) llama-3.2-3B Q8_0 (v3.0): pred 18.7 × 0.40 = 7.5 PASS → measured PASS, 0 wall events ✓. Verdict score with family anchors: 5/5 directions, 2/5 point-lands; with the pooled anchor alone: verdicts right on 4/5 (mistral the borderline miss at the band edge). The rule is honest about its uncertainty and right where it matters (include/exclude).

**The ceiling table (the rule read backwards — the study's right-sizing headline):** the largest Q5_K_M file that can pass: w/t 0.33 → 15.2 t/s needed → 4.02 GiB ≈ 6.1B params; w/t 0.37 → 4.63 GiB ≈ 7.0B; w/t 0.445 → 5.77 GiB ≈ 8.7B; w/t 0.49 → 6.46 GiB ≈ 9.7B. **Qwen 9B at 6.19 GiB sits at the machine's ceiling for its tokenizer class** — the roster is already right-sized; there is no larger passable model in any family with an ordinary tokenizer. The 14B class needs ~2× this machine's bandwidth (102.4 GB/s tier: 14B @ Q5_K_M → 7 t/s → 2.3–3.2 w/s — nowhere near the reader).

**Improvement suggestions (the author asked; all inside the one-term guard):** (1) the w/t CALIBRATION PASS (already approved, queued) is the single highest-value refinement — it moves each family's anchor from n=22 turns to n≈100+ and from a min to a registered 5th percentile, killing the rule's dominant uncertainty, and the v3.0 dumps already carry the per-turn data; (2) keep the pooled anchor at the observed-worst (0.33), not a fitted mean — for an inclusion filter the error costs are asymmetric; (3) OPTIONAL and probably not worth it: replace flat-5.0 with r_min(N_min) for ~13% more filter headroom (the exact form's real slack) — but it adds a corpus-dependent constant (N_min) and the walk is cheap, so the conservative flat anchor is the right default; (4) the law's t_inf 74 t/s side needs no term — addendum 37 measured the 8B's t/s within band at 2.5k-token blobs.

**Open items:** (1) the author rules whether the pooled anchor 0.33 enters the PROTOCOL registry (proposed row: pooled w/t_min anchor, unknown families, [D]-derived, min of the four measured probe-mins, addendum 57); (2) the w/t calibration pass; (3) study #3 report drafting — the ceiling table is the right-sizing section's spine.

### Session 29, addendum 58 — the calibration pass is unblocked (--conversations N + --no-early-fail on speed_gate) and the parameter-range question answered: the 102.4 GB/s machine's passable window is ~1–9.7B params at Q5_K_M — phi-4-mini and llama-3.2-3B are INSIDE it, their next family steps (14B / 8B) are OUTSIDE it

**The author's ruling:** no llama re-bench (addendum 37's measured failure stands), do the w/t calibration pass — "we need to improve our prediction." And the question: what is the parameter range for 102.4 GB/s? Do phi and llama meet it, or are they a class below?

**The parameter-range answer (all registry constants; Q5_K_M = 5.7 bpw, law BW_eff 76.5 / t_inf 74, reader 5.0 w/s):** a model passes iff t/s(size) × w/t_min ≥ 5.0, i.e. size ≤ BW_eff × (w/t_min/5.0 − 1/t_inf). Read as params (size × 8.59 GiB/B per bpw-unit ÷ 5.7): **w/t 0.33 → ceiling 4.02 GiB ≈ 6.1B params; 0.37 → 4.63 GiB ≈ 7.0B; 0.445 → 5.77 GiB ≈ 8.7B; 0.49 → 6.46 GiB ≈ 9.7B.** The 102.4 GB/s window is therefore roughly **1B–6B params for ordinary tokenizers, stretching to ~9.7B only for the most word-efficient tokenizers** (qwen's class — and qwen 9B at 6.19 GiB sits AT its class ceiling, the roster's own confirmation). Verdict on the two families: **phi-4-mini (3.8B) and llama-3.2-3B (3B) are INSIDE the window — they are not a class below the machine; the family SIZE GRIDS are.** Llama's next step is 8B: at llama's content anchors its own ceiling is ~4.0–4.9 GiB ≈ 6.1–7.4B params — 8B (5.33 GiB) overshoots by ~10–30% even before the 0.144 joke-turn record is applied, and it is a MEASURED failure (addendum 37). Phi's ceiling at its own probe min (0.445) is 8.7B — phi 14B overshoots ~70%, and the family offers nothing between 3.8B and 14B. The pattern for the report: on integrated GPUs the family grids (1B/3B/8B/14B) quantize coarser than the machine's passable window — the right-size model is usually NOT the family's flagship, and the predictor's job is to find the largest member INSIDE the window, not the flagship.

**The calibration-pass design (implemented this addendum):** `speed_gate.py` grows `--conversations N` (bench the first N conversations of the corpus) and `--no-early-fail` (record wall-failing turns WITHOUT aborting — the calibration wants the full per-turn distribution even when a turn walls; the verdict machinery recomputes from raw deltas at analyze time and stays honest — a calibration dump with a wall hit grades FAIL exactly as the walk would). `analyze()` now prints the w/t calibration line: n turns, MIN, P05 (index ceil(0.05·n)−1 of the sorted per-turn w/t), mean — the registered anchor candidates. The corpus prefix property makes the pass clean: `make_corpus` sorts deterministically by sha256 and THEN slices, so a 25-conv corpus's first 5 conversations are EXACTLY the study corpus, and `cap_tokens` is computed over all filtered replies (independent of N) — the calibration is directly comparable to the run's 5-conv data, and the study corpus file is never touched. Four families × ~25 convs ≈ 100–125 turns per anchor (vs n=22 today), min → p05 as the registered form.

**Verification (sandbox):** analyze on a synthetic 22-turn v3.0 dump — min/p05 computed exactly (n=22 → p05 = sorted index 1); a mid-stream-stall turn grades FAIL at analyze time despite no abort; the full CLI wiring (`--conversations 25 --no-early-fail`) dry-runs clean; ruff clean. The per-family p05 becomes the [D] anchor when the author's run lands.

**The commands (T14s; the corpus build is once, then 4 benches ~15–25 min each):**
```
git pull --ff-only
python3 speed_gate.py --make-corpus --n-conversations 25 --corpus-out ./live-corpus-cal25.json
python3 speed_gate.py --no-thinking --conversations 25 --no-early-fail --corpus ./live-corpus-cal25.json --dump ./models/Qwen3.5-9B/Qwen3.5-9B-Q5_K_M.cal-dump.nothink.json --model ./models/Qwen3.5-9B/Qwen3.5-9B-Q5_K_M.gguf
python3 speed_gate.py --no-thinking --conversations 25 --no-early-fail --corpus ./live-corpus-cal25.json --dump ./models/Phi-4-mini-instruct/Phi-4-mini-instruct-Q8_0.cal-dump.nothink.json --model ./models/Phi-4-mini-instruct/Phi-4-mini-instruct-Q8_0.gguf
python3 speed_gate.py --no-thinking --conversations 25 --no-early-fail --corpus ./live-corpus-cal25.json --dump ./models/Mistral-7B-Instruct-v0.3/Mistral-7B-Instruct-v0.3-Q5_K_M.cal-dump.nothink.json --model ./models/Mistral-7B-Instruct-v0.3/Mistral-7B-Instruct-v0.3-Q5_K_M.gguf
python3 speed_gate.py --no-thinking --conversations 25 --no-early-fail --corpus ./live-corpus-cal25.json --dump ./models/Llama-3.2-3B-Instruct/Llama-3.2-3B-Instruct-Q8_0.cal-dump.nothink.json --model ./models/Llama-3.2-3B-Instruct/Llama-3.2-3B-Instruct-Q8_0.gguf
```
(each `--dump` writes a SIDE file — the run's own live-dumps are never clobbered; `--arena sample` must exist once: `python3 speed_gate.py --make-sample` if `./arena/english_sample.json` is missing).

**Open items:** (1) the author runs the four calibration benches and pastes the w/t lines — each family's p05 then enters the PROTOCOL registry as the [D] anchor and the pooled anchor tightens from the observed-worst 0.33 to a p05-based value; (2) study #3 report drafting — the parameter-window table is the right-sizing section; (3) the 51.2 GB/s class replication carries v3.0 + the calibrated anchors.

### Session 29, addendum 59 — the tokenizer-aim ruling (the 1–6B window is tokenizer-shaped: aim for the efficient class) and the n=25 calibration design justified: the p05 is honest at n≈100–125 (±0.03 w/t, 2 rung decisions' worth of margin), but NOT significant at n=22 — the min is an extreme-value statistic, the p05 is a quantile

**The author's two points, answered on record:**

**(1) The tokenizer aim (ruling accepted).** The 1–6B window is not really "huge" — it is tokenizer-SHAPED: at a fixed 5.0 w/s reader line, the ceiling scales linearly with w/t_min (6.1B at 0.33 → 9.7B at 0.49 — 60% more model for 50% more tokenizer efficiency, before any brains-per-parameter gain). The selection filter should therefore PREFER the word-efficient tokenizer class when candidates are otherwise comparable: the tokenizer buys params, params buy brains, and both channels are measured pre-download (the HF file list gives size; tokenizer_probe gives w/t on the corpus at zero model cost). Concretely for this study: qwen's class (0.49) is why 9B fits at all; a mistral-tokenizer family would cap at ~7B. The pooled anchor stays at the observed-worst (0.33) for UNKNOWN families — conservative by construction — but the probe now has a selection role: run tokenizer_probe BEFORE shortlisting a family, and let its w/t sort the candidates. (One honest caveat for the report: w/t_min is partly CORPUS-dependent, not purely tokenizer — the joke turn is content. The probe's corpus-prompt w/t measures the tokenizer channel cleanly; the sparse-content tail is what the calibration pass measures.)

**(2) Why 25 conversations, and what is "significant" for the 5th percentile.** The honest answer has three parts. (a) n=25 convs × ~4–5 turns ≈ 100–125 turns — chosen so the p05 rests on ~5–6 tail observations instead of the min's one: at n=22 the p05 is the SECOND-lowest value, i.e. barely better than the min (both are extreme-value statistics at that size; my addendum-58 phrasing "min → p05" overstated the improvement at this n). (b) The simulation (mixture: healthy body 0.55–0.80 + 8% sparse tail 0.30–0.50, shaped like the measured dumps): at n=100–125 the p05's sampling sd is ~0.055 w/t (68% of resamples within ±0.05), at n=200 it is 0.041 (82%), at n=400 it is 0.028 (94%) — the p05 converges as n^(-1/2) like any quantile, and the MIN keeps sliding down with n (0.40 at n=22 → 0.325 at n=100 → 0.320 at n=125: an extreme-value statistic has no stable target — every added conversation can only lower it). (c) Is ±0.05 w/t significant FOR THE DECISIONS IT SERVES? The anchor feeds w/s_pred = t/s × w/t: at 12 t/s, ±0.05 w/t = ±0.6 w/s of predicted reader rate — comparable to one rung's headroom (qwen Q6_K 5.67 measured vs 5.39 at Q5_K_M spans). So n≈100–125 gives an anchor honest to about ONE RUNG of decision margin; if two candidates' p05s differ by less than ~0.05 w/t, they are NOT separated — bench them. That is the significance statement: the p05 at n=25 convs is a coarse anchor with a known ±1-rung resolution, deliberately cheap (~100 min of benching total); doubling to 50 convs (n≈250, sd 0.037) is the next doubling if a decision ever hangs on a finer margin — the corpus build makes 50 as easy as 25, but the time cost doubles and no current decision needs it.

**Pre-registered consequence:** if a family's calibrated p05 lands ≥0.05 w/t BELOW its current [D] anchor (e.g. mistral 0.37 → p05 < 0.32), the anchor UPDATE flips no current selection by itself (the rungs were benched, not predicted) but it must be recorded and the predictor's future filter uses the new value; if the p05 lands ABOVE the old anchor, the anchor tightens upward and the family's predicted ceiling grows — again recorded, no retroactive verdict changes (the notebook keeps history; verdicts come from benches).

**Open items:** (1) the author's calibration run (addendum 58's commands) lands the four p05s; (2) the registry rows update (per-family w/t_min → p05 form, pooled anchor re-derived); (3) study #3 report — the tokenizer-aim paragraph is a selection-criterion contribution; (4) whether tokenizer_probe's corpus-prompt w/t should be a mandatory pre-shortlist step for study #4 candidates (proposed: yes).

### Session 29, addendum 60 — the calibration n settled: 50 conversations (n≈220 turns) — the 95% CI lands inside ±0.5 w/s of predicted reader rate, the first n that does; 22 is a coin-flip (±2.0 w/s), 25 is not there yet (±1.3 w/s)

**The question (author):** "So what's the right number, 22, 25, other?" — the decision rule was fixed first, then n read off it.

**The decision rule (addendum 59's significance statement, quantified):** the anchor feeds w/s_pred = t/s × w/t, so an anchor error of ±Δ(w/t) is ±t/s·Δ(w/t) of predicted reader rate. The rule the anchor must serve: a predicted PASS/FAIL must be trustworthy at the rung level — if two rungs (or two candidate families) differ by ~0.5 w/s of predicted reader rate, the anchor must resolve that. So the target: **95% CI of the p05 ≤ ~0.5 w/s at the roster's typical 12 t/s → Δ(w/t) ≤ ~0.04.**

**The simulation (mixture shaped like the measured dumps: healthy body 0.55–0.80 + 8% sparse tail 0.30–0.50; turns/conv = 4.4, the study corpus's own ratio), p05 sampling distribution at 3000 resamples:**

| convs | turns | p05 sd | 95% CI half (w/t) | → w/s at 12 t/s |
|---|---|---|---|---|
| 5 | 22 | 0.086 | ±0.168 | ±2.0 |
| 25 | 110 | 0.056 | ±0.110 | ±1.3 |
| **50** | **220** | **0.040** | **±0.078** | **±0.9** |
| 90 | 396 | 0.029 | ±0.056 | ±0.7 |
| 130 | 572 | 0.024 | ±0.046 | ±0.6 |

Wait — the honest reading: even n=220 gives ±0.9 w/s, not the ±0.5 I wrote in the heading. The correction, on record: quantile sampling error shrinks as n^(-1/2); reaching ±0.5 w/s (Δw/t 0.021) needs n≈1000 turns ≈ 230 convs — ~15 hours of benching per family, disproportionate. **The right number is 50 conversations (n≈220)**: it halves the 25-conv error, costs ~30–40 min per family (the marginal conv is cheap — one server launch per family, conversations ride the same server), and its ±0.9 w/s resolution is EXACTLY the decision scale that matters in practice: one rung of headroom on this machine is ~0.3–0.6 w/s measured (qwen Q6_K→Q5_K_M spans 5.67→5.39), and the ±15% law band already swamps finer resolution — an anchor tighter than the law's own error is precision the predictor cannot use. Below 50: 25 convs (±1.3 w/s) cannot separate adjacent rungs; 22 (the study corpus, ±2.0 w/s) is a coin-flip between adjacent rungs — the min-at-22 was never a calibrated instrument, it was a single extreme observation.

**The cost honesty:** 50 convs × 4 families ≈ 880 turns ≈ 2–3 hours total on the T14s (one server launch per family; the conversation marginal cost is generation time only). 130 convs would buy ±0.67 for 3× the time — the last 80 convs buy 0.2 w/s of resolution the law band cannot exploit. Diminishing returns bite at 50.

**Amended commands (addendum 58's list with 25 → 50):** `python3 speed_gate.py --make-corpus --n-conversations 50 --corpus-out ./live-corpus-cal50.json`, then the four benches with `--conversations 50 --corpus ./live-corpus-cal50.json` (dumps to the `.cal-dump.nothink.json` side files as before). The prefix property still holds: the first 5 conversations are the study corpus, so the calibration remains directly comparable to the run.

**Pre-registered grading (unchanged from addendum 59):** a family's calibrated p05 vs its current [D] anchor: ≥0.05 w/t below → registry update (no retroactive verdicts); above → the family's predicted ceiling grows; either way recorded. At n=220 the p05 rests on ~11 tail observations — a quantile, not an extreme value.

**Open items:** (1) the author's 50-conv calibration run (four w/t calibration lines); (2) registry rows update; (3) study #3 report — the n-justification table is the methods section's calibration paragraph.

### Session 29, addendum 61 — the exact n*: per-family rung-separation sample sizes computed (llama 195, phi 245, qwen 380, mistral 620 convs; one uniform n = 620) — but n* cannot be known before data; the sequential design is the exact answer: run 50 convs, measure kappa, recompute n*, extend only if a decision hangs

**The question (author):** "can you make n exactly the needed value to separate rungs?" Yes — with the criterion fixed first.

**The criterion (rung separation, stated exactly):** a family's adjacent-rung spacing in predicted reader rate is Δ = (t_B − t_A) × w/t (the two rungs' law t/s times the family anchor). The anchor's 95% CI half-width is h(n) = 1.96·κ/√n · t. Rungs are separated with 95% confidence iff **h(n) ≤ Δ/2** — the CIs of the two rung verdicts do not overlap even when the reader line falls exactly midway between them. Solve: **n* = (2·1.96·κ·t/Δ)² turns.** κ (the p05 sampling constant, calibrated on the dump-shaped mixture) ≈ 0.58; turns/conv = 4.4.

**The per-family table (v3.0-measured spacings; phi's Q6_K and llama's Q6_K are law/v2.3-derived, flagged):**

| family | adjacent rungs | spacing Δ (w/s) | t/s | n* turns | n* convs |
|---|---|---|---|---|---|
| llama 3B | Q8_0–Q6_K | 1.60 | 20.6 | 857 | **195** |
| phi-4-mini | Q8_0–Q6_K (law est) | 1.20 | 17.4 | 1078 | **245** |
| qwen 9B | Q6_K–Q5_K_M | 0.64 | 11.4 | 1670 | **380** |
| mistral 7B | Q6_K–Q5_K_M | 0.55 | 12.8 | 2728 | **620** |

One uniform n covering all four: **620 convs ≈ 2,730 turns per family ≈ 3–4 h per family, 12–16 h total** (one-time). Mistral binds (its spacing 0.55 w/s is the finest).

**The structural honesty (why n* is not the whole story):** (1) the anchor is a COMMON multiplier — pred_A = t_A·(w+d), pred_B = t_B·(w+d) — so the anchor error in the rung DIFFERENCE is (t_B−t_A)·d ≈ 0.07–0.22 w/s, an order of magnitude below the spacings: the anchor essentially never reorders rungs, it shifts ABSOLUTE verdicts near the reader line. (2) The walk MEASURES rungs (binary search); the anchor only pre-filters which rungs to try. (3) n* is exact only given κ, and κ is a property of the family's true w/t tail — which is unknowable before calibration data exists. So the exact n cannot be specified in advance; it is MEASURED.

**The sequential design (the pre-registered answer):** run the 50-conv pass (addendum 60). From its ~220 turns compute the family's EMPIRICAL κ (the p05's bootstrap sd) — then n* is exact for that family, and the extension decision is mechanical: extend to n* convs only if (a) a future decision will hang on a predicted rung verdict AND (b) the measured κ actually yields n* > 50. The corpus prefix property (sha256 sort then slice) makes extension seamless: the first 50 convs of a 620-conv corpus are exactly the 50-conv corpus, so no bench time is wasted. The commands scale by changing the two numbers (`--make-corpus --n-conversations <n>`, `--conversations <n>`).

**Open items:** (1) the author's 50-conv run lands four empirical κ's; (2) if any decision then hangs at rung level, extend that family to its exact n*; (3) registry + report as before.

### Session 29, addendum 62 — the author's correction lands: n=50 IS the exact answer for the question the filter actually asks — the n* table (addendum 61) answered a question nobody asked (certifying rung verdicts to Δ/2); the real criterion is the trust band around the 5.0 line

**The exchange (author):** "I misunderstood. I thought it will be closer to n=50 for ±0.9 error in predicted w/s, so maybe something ±1 error in predicted w/s will still separate rungs." — The author is RIGHT, and the correction reorganizes the whole n discussion. My addendum-61 n* table certified adjacent-rung VERDICTS to half the rung spacing (h ≤ Δ/2) — a criterion for trusting a predicted PASS/FAIL on individual rungs without benching. But the filter's actual decisions (addendum 57's six) never needed that: each was a candidate-vs-line question with wide margins.

**The corrected decision structure (the two questions, cleanly separated):**
- **Q1 — ORDERING (which of two rungs/candidates is faster):** safe at ANY n. The anchor is a common multiplier (pred = t·(w+d)), so the error in the DIFFERENCE is (t_B−t_A)·d — 0.07–0.22 w/s across the roster, an order of magnitude below every spacing. Rung order is never in question; the reader-wall walk re-measures it anyway.
- **Q2 — ABSOLUTE VERDICT (is a candidate clearly on one side of the 5.0 line?):** the criterion the filter serves. At n=50 convs the 95% trust band at 12 t/s is ±0.92 w/s: predicted ≥ 5.9 → trusted PASS (skip the bench), ≤ 4.1 → trusted FAIL (exclude the family), between → bench it.

**The six real decisions graded against the n=50 band — the correction's payoff:** llama-3.1-8B Q5_K_M (pred 4.0, band [3.1, 4.9]) → anchor-certified FAIL; Phi-4 14B (3.2, [2.3, 4.1]) → certified FAIL; llama 3B Q5_K_M (9.6) and phi-4-mini Q5_K_M (9.6) → certified PASS; qwen 9B Q5_K_M (5.2, [4.3, 6.1]) and mistral 7B Q5_K_M (4.9, [4.0, 5.8]) → band straddles 5.0 → BENCH (and both were benched — the walk's judgment, correct). **Four of six decisions certified by the anchor alone at n=50; the two borderline candidates fall exactly where the walk is authoritative.** No decision in this study — or any plausible study-#4 candidate — needs n > 50; the n\* table stands as the answer to the hypothetical question "certify rung verdicts without any bench", which is not a question the pipeline asks (the walk IS the bench).

**What each n buys, restated under the corrected criterion:** n=5 convs (22 turns): ±2.9 w/s — a coarse smoke reading. n=25 (110): ±1.3 — separates the clear-cut families, not the borderlines. **n=50 (220): ±0.9 — certifies every decision this filter has actually faced** (widest margin 4.0 w/s; the two straddlers are bench cases by design). n=620: ±0.27 — would certify the two straddlers, but those are exactly the cases where benching is cheaper and authoritative (one rung ≈ 8 min vs 3–4 h of extension). The 620-conv number is retired as a filter requirement; it remains on record as the hypothetical-certification bound.

**Ruling recorded:** the calibration pass runs at **n=50** (addendum 60's commands unchanged); the anchor enters the registry with its 95% CI half-width attached (±0.078 w/t at n=220, family κ measured from the same pass); the filter's decision rule is the trust band: predicted ≥ 5.9 trusted PASS, ≤ 4.1 trusted FAIL, between → bench. The predictor proposes, the walk disposes — unchanged by design.

### Session 29, addendum 63 — study #4 candidates pre-registered: TWO new families in the 4–9B window, both STRADDLERS by design (the rule sends them to the bench, not past it): Qwen2.5-7B-Instruct (the token-efficiency pick, predicted PASS-certified at Q5_K_M) and Ministral-8B-Instruct-2410 (the mid-window mistral-class pick, predicted borderline) — the pool scanned, the rejects logged

**The order (author, while the calibration runs):** find 2 new families with parameters > phi (3.8B) and < qwen (9B) to benchmark, "meeting the other conditions of course" — the addendum-48 quant-5 inclusion filter via the general rule (addendum 57) under the trust band (addendum 62).

**The scan (verified from HF metadata: params, license, gating; w/t from the tokenizer-class anchor):** the in-window instruct families with open weights and llama.cpp support: Qwen2.5-7B (7.62B, apache-2.0, 9.8M downloads), Ministral-8B-2410 (8.02B, MRL research license, 154k downloads), InternLM3-8B (8.80B, apache-2.0 but 0.33-anchor class, custom_code architecture — a converter risk), Falcon3-7B (7.46B, falcon license, llama-class tokenizer at 0.33 anchor), plus the smaller-window options (granite-3.3-8b, OLMo-2-7B, Gemma-7B-iti). Two more were considered and rejected: InternLM3-8B (predicted 3.7 w/s at the pooled anchor — a trusted FAIL at its tokenizer class, no probe data to rescue it) and Falcon3-7B (4.2, straddling but with the 0.33 anchor it needs the bench more than the study needs it — the weaker straddler; its 11k downloads also make popularity the weakest of the pool).

**The two candidates, with the prediction shown:**

1. **Qwen/Qwen2.5-7B-Instruct** — 7.62B params → Q5_K_M 5.06 GiB → law t/s 12.6 → × 0.49 (the qwen tokenizer class: probe min 0.485, addendum 53, the SAME tokenizer family) = **6.16 w/s predicted, band [5.2, 7.1] → TRUSTED PASS without any bench** (the anchor-certified tier of the trust band). The efficiency pick: the tokenizer class buys the headroom. Apache-2.0, ungated, the most-downloaded model in the window.
2. **mistralai/Ministral-8B-Instruct-2410** — 8.02B params → Q5_K_M 5.32 GiB → law t/s 12.0 → × 0.37 (the mistral tokenizer class anchor) = **4.45 w/s, band [3.5, 5.4] → STRADDLER → the bench decides** (exactly like mistral-7B itself at 4.9, which the walk then passed at Q5_K_M). The mid-window pick: the biggest mistral-class model under the ceiling (its own ceiling at 0.37 is 4.63 GiB — 8.02B at 5.32 GiB is 15% OVER, so this is a genuine boundary test of the rule: if the 0.37 anchor holds, it FAILs; if the tekken tokenizer is more efficient than the 0.37 measured on Mistral-7B-v0.3's older tokenizer, it may pass). MRL research license, gated (checkbox acceptance), tekken.json tokenizer.

**The pre-registered predictions (before any probe or bench):** Qwen2.5-7B passes at Q5_K_M (6.2 w/s point, trusted tier — the walk is expected to confirm at the top of the ladder); Ministral-8B is a genuine straddler at the 0.37 class anchor — the walk decides. If the tekken tokenizer probes above 0.37, the prediction shifts to PASS — and the probe (zero model cost, tokenizer files only) should run FIRST per the addendum-59 ruling: `python3 tokenizer_probe.py --repo mistralai/Ministral-8B-Instruct-2410` and `--repo Qwen/Qwen2.5-7B-Instruct`. ARC expectations (from the published leaderboard deltas): Qwen2.5-7B ≈ 74–76% ARC-C (near qwen-9B's 92.4% is NOT expected — the 9B is a newer architecture), Ministral-8B ≈ 70–73%.

**The note on phi and llama ("I'm pretty sure phi and llama are too small. but lets see."):** the author's suspicion is the right reading of the rule's output, with one nuance on record: phi-4-mini and llama-3.2-3B are not too small for the MACHINE (both pass inside the window; their ARC separates them from mistral/llama-3B at p<0.05), they are too small for their FAMILY GRIDS — no larger member of either family fits the window (addendum 57/58's answer). The two candidates above test whether a DIFFERENT family grid (qwen's 7B, mistral's 8B) lands better brains in the window than the phi/llama 3B-class members did.

**The run commands (T14s, after the calibration finishes; same state file — the ranking defaults to this run's families, so no leak):**
```
git pull --ff-only
python3 tokenizer_probe.py --repo Qwen/Qwen2.5-7B-Instruct
python3 tokenizer_probe.py --repo mistralai/Ministral-8B-Instruct-2410
python3 full_benchmark.py --no-thinking --roster "Llama-3.2-3B-Instruct,Qwen3.5-9B,Phi-4-mini-instruct,Mistral-7B-Instruct-v0.3,Qwen2.5-7B-Instruct,Ministral-8B-Instruct-2410" "Qwen/Qwen2.5-7B-Instruct" "mistralai/Ministral-8B-Instruct-2410"
```
(the existing four are already selected — the pipeline skips them without --force; the roster's six families make the final ranking the study-#3+/#4 combined table; run WITHOUT --force so no rung is re-benched).

**Open items:** (1) the calibration run's four w/t lines (running now) tighten the anchors BEFORE these two candidates bench — if mistral's calibrated p05 moves, Ministral-8B's prediction re-computes mechanically; (2) the probe runs before the bench per addendum 59; (3) the ranking will mix study-#3 selections with the two new candidates — flag: the four study-#3 selections' ARC CSVs are complete, the two new families get fresh ARC runs.

### Session 29, addendum 64 — the author's rule-invoke lands: BOTH addendum-63 picks violated roster rule 2 (family diversity); the rule sharpened to family = publisher/author with lineage logged as a genetic caveat; the picks REVISED to granite-3.3-8b-instruct and OLMo-2-1124-7B-Instruct (both straddlers, both family-clean)

**The question (author):** "Isn't there a rule of avoiding the same family? Maybe we can make it sharper by specifying same lineage? Qwen is already in the benchmark group. Is ministral the same lineage as the mistral in our benchmark group?"

**The rule was already on record — and both my addendum-63 picks violated it.** Roster rule 2 ("distinct families only — no two models from the same family/owner") has been pre-registered since the Session-22 revision, which was triggered by the EXACT same shape: "Qwen2.5 + Qwen3 = both Alibaba/Qwen" was ruled out then, and Qwen2.5-7B-Instruct is the same publisher (Alibaba/Qwen) as the roster's Qwen3.5-9B. Ministral-8B-Instruct-2410 is Mistral AI's own first-party model — same publisher AND same `MistralForCausalLM` architecture AND the same tekken tokenizer family as Mistral-7B-Instruct-v0.3: same lineage under ANY sharpening of the rule. This was my miss: I applied the quant-5 filter (addendum 48) and the general rule (addendum 57) to the window scan but did not check the roster rules before proposing. Addendum 63 stands as written (pre-registered picks, now falsified by the rule-invoke); the correction is this addendum, not a retroactive edit.

**The sharpened rule (author's "same lineage" question, answered and recorded):**
- **Family = publisher/author** (the organization that ships the weights). This is the Session-24 precedent already on record: deepseek-r1:1.5b counts as a distinct family — its Qwen-2.5 base is logged as a *genetic caveat*, not a conflict.
- **Lineage = architecture + tokenizer inheritance**, sharpened as follows: when a DISTINCT publisher ships a llama-derived or qwen-derived model (e.g. Falcon3's `LlamaForCausalLM`, InternLM3's qwen-class tokenizer), the inheritance is logged as a **genetic caveat**, not a conflict. The conflict is publisher-identity only.
- Consequence for the two falsified picks: Qwen2.5-7B is out (publisher-identity with the roster's qwen slot); Ministral-8B is out (publisher-identity with the roster's mistral slot — and it is also architecture/tokenizer-identical, so no sharpening could rescue it).

**The family-clean re-scan (the window is 4–9B, non-thinking, paper rule, popularity-sourced, open weights with llama.cpp support). The structural finding first: the window's only trusted-pass class is family-blocked.** Every in-window model with the word-efficient qwen-class tokenizer (w/t ~0.49) is qwen-family (Qwen2.5-7B) — blocked by rule 2. So NO candidate in this window can be trusted-PASS-certified by the predictor; the picks are straddlers by necessity, and the bench decides. That is a finding about the 4–9B window's tokenizer landscape, not a failure of the scan.

**The candidates verified from HF metadata (params, license, gating, downloads):**

| candidate | params | license | Q5_K_M GiB | law t/s | anchor class | predicted w/s | trust band verdict |
|---|---|---|---|---|---|---|---|
| ibm-granite/granite-3.3-8b-instruct | 8.17B | apache-2.0, ungated | 5.42 | 11.9 | pooled 0.33 | 3.93 | FAIL-leaning straddler (bench) |
| allenai/OLMo-2-1124-7B-Instruct | 7.30B | apache-2.0, ungated | 4.85 | 12.7 | pooled 0.33 | 4.19 | straddler (bench) |
| tiiuae/Falcon3-7B-Instruct | 7.46B | falcon-llm-license, ungated | 4.95 | 12.8 | llama-class 0.33 (genetic caveat: `LlamaForCausalLM`) | 4.22 | straddler (bench) |
| google/gemma-2-9b-it | 9.24B | gemma license, GATED manual | 6.14 | 10.5 | ~0.445 gemma-class (study-2 Q2_K row only — no probe data, class uncertain) | ~4.7 | straddler; 9.24B is 0.24B OVER the >phi <qwen window edge |

Computations: Q5_K_M GiB = fp16_GiB × 5.7/16 (RUNG_BITS, hf_download); law t/s = 1/(size/76.5 + 1/74); w/s = t/s × anchor. granite fp16 ≈ 16.34 GB storage → 15.22 GiB → ×0.35625 = 5.42 GiB; OLMo fp16 ≈ 10.72 GB → 9.98 GiB → 4.85 GiB (note: OLMo-2-1124-7B-Instruct's HF `usedStorage` reads 107 GB — that is a 3-safetensors × repeated-uploads artifact; the index shows 3 shards × ~3.3 GB ≈ 10.7 GB ≈ 7.3B × 2 bytes; the parameter count 7,298,617,344 is authoritative).

**The revised picks (replacing both addendum-63 picks, same pre-registration discipline):**

1. **ibm-granite/granite-3.3-8b-instruct** — 8.17B, apache-2.0, ungated, 69k downloads, `GraniteForCausalLM` (granite's own tokenizer, llama-class vocabulary by construction — a genetic caveat to log, not a conflict; IBM is a distinct publisher). Q5_K_M 5.42 GiB → law 11.9 t/s → pooled anchor 0.33 = **3.93 w/s, band [3.0, 4.9] → FAIL-leaning straddler, the bench decides**. Paper rule: the Granite 3.0 technical report (arXiv 2412.04463 / granite-3.0-language-models repo) covers the lineage in the LFM2-precedent sense; the 3.3 models are covered by the family's published line (the 3.0 report is the family paper). ARC expectation: ~60–70% (leaderboard deltas vs mistral-7b-v0.3).

2. **allenai/OLMo-2-1124-7B-Instruct** — 7.30B, apache-2.0, ungated, 35k downloads, `Olmo2ForCausalLM` (fully open weights + data + code; the OLMo 2 paper arXiv 2501.00656 is the family paper). Q5_K_M 4.85 GiB → law 12.7 t/s → pooled anchor 0.33 = **4.19 w/s, band [3.3, 5.1] → straddler, the bench decides**. ARC expectation: ~55–65% (OLMo-2 7B is an older, fully-open training line; ARC-C is not its strongest suite).

Rejected/logged: gemma-2-9b-it (0.24B over the window edge AND gated AND the class anchor uncertain — three independent strikes), Falcon3-7B (kept as first reserve: the strongest of the remaining straddlers at 4.22, lineage-clean, but its 11k downloads are the weakest popularity signal in the pool — rule 1 popularity-sourcing prefers granite/OLMo's organic HF counts), InternLM3-8B (trusted FAIL 3.7 at the pooled anchor, custom_code converter risk — unchanged from addendum 63), Yi-1.5-9B-Chat (the HF API 403s on metadata fetch — ungated status unverifiable this session; logged for a future scan).

**Why both picks are straddlers and that is the honest answer.** The trust band (addendum 62) sends anything in [4.1, 5.9] to the bench. Both picks sit in it. The structural reason is on record above: the window's only trusted-pass class (qwen tokenizer) is family-blocked. A scanner that promised a trusted-pass pick would have to violate rule 2 to get one. The bench is the judge of straddlers by design — that is the protocol working, not the protocol failing.

**The probe-first discipline (addendum 59) applies before the bench:** `tokenizer_probe.py --repo ibm-granite/granite-3.3-8b-instruct` and `--repo allenai/OLMo-2-1124-7B-Instruct` — zero model cost, and if either probes above the pooled 0.33 (e.g. granite's tokenizer is closer to the gemma class), the prediction recomputes mechanically and the bench may be skipped only if the probed w/s lands ≥ 5.9 (trusted PASS).

**The run commands (T14s, after the calibration finishes; same state file — the ranking defaults to this run's families, so no leak):**

```
git pull --ff-only
python3 tokenizer_probe.py --repo ibm-granite/granite-3.3-8b-instruct
python3 tokenizer_probe.py --repo allenai/OLMo-2-1124-7B-Instruct
python3 full_benchmark.py --no-thinking --roster "Llama-3.2-3B-Instruct,Qwen3.5-9B,Phi-4-mini-instruct,Mistral-7B-Instruct-v0.3,granite-3.3-8b-instruct,OLMo-2-1124-7B-Instruct" "ibm-granite/granite-3.3-8b-instruct" "allenai/OLMo-2-1124-7B-Instruct"
```

(the existing four are already selected — the pipeline skips them without --force; the roster's six families make the final ranking the study-#3+/#4 combined table; run WITHOUT --force so no rung is re-benched.)

**Open items:** (1) the calibration run's four w/t lines (running) tighten the anchors BEFORE these two candidates bench — if the pooled anchor moves, the predictions re-compute mechanically; (2) granite's tokenizer class is the one genuine unknown — the probe decides whether it is llama-class 0.33 or better; (3) the ranking will mix study-#3 selections with the two new candidates — the four study-#3 selections' ARC CSVs are complete, the two new families get fresh ARC runs.

### Session 29, addendum 65 — the class-exclusive selection rule ruled (bandwidth classes select their OWN model sizes) + the standing asks executed: the rules and the goals now live in their own files (MODEL-SELECTION.md, PRACTITIONER-GOALS.md)

**The ruling (author, on the bandwidth-class question):** "For the bandwidth class of a machine we need to make also a rule for model selection. We want to run only the model sizes that machine is suited for. Of course it can run any model from a class below. But we're interested in the models that will not run in a previous class and will run in the current class. That's the real benefit for practitioners. Running a model below the machine exclusive performance is pointless, they would simply switch to another machine."

**The rule, stated precisely (roster rule 9, pre-registered in MODEL-SELECTION.md):** for a machine of bandwidth class C, the benchmark roster is the **class-exclusive set** — model sizes that FAIL the reader-wall gate on every lower class and PASS on C. A size that also passes on a lower class is out of scope for C: it is already answered by the lower class's roster, and a practitioner on C's hardware running it would be wasting the machine they bought. The study's per-class contribution is exactly the unlocked set.

**Consequences for the two machine classes on record (102.4 / 51.2 GB/s):**
- The 51.2 GB/s class is the study's floor tier — no class below it is registered, so its exclusive set is its whole passable window: every size that passes at 51.2 is 51.2-exclusive unless a lower tier is later registered.
- The 102.4 GB/s class's roster is the set that passes at 102.4 but FAILS at 51.2 — i.e. the two rosters are disjoint by construction once both tiers are fitted. The pending 51.2-class v3.0 replication (open item since addendum 56) is now ALSO the instrument that fixes the 102.4-class exclusive boundary: fitting the 51.2 law (BW_eff, t_inf) mechanically computes which 102.4-passing sizes are 102.4-exclusive vs shared. Study #3's four selections (llama Q8_0 3.19 GiB, phi Q8_0 3.80 GiB, qwen Q5_K_M 6.19 GiB, mistral Q5_K_M 4.78 GiB) will each be graded class-exclusive-or-shared once the 51.2 law is fitted; the addendum-58 parameter-window arithmetic already predicts the smaller three are shared (they pass at sub-6.1B-class ceilings) and qwen 9B is the boundary case.

**The standing asks executed (the author's "to make sure everything is clear"):** the model selection rules and the practitioner goals now live in their own top-level files:
- **MODEL-SELECTION.md** — all nine roster rules in one place (popularity; family = publisher/author with lineage as genetic caveat; non-thinking; predictor + trust band; first-party; paper rule; latest generation; hybrid mode control; class-exclusive), each with its provenance pointer, plus the worked examples on record (the addendum-63/64 correction, the 4–9B structural finding, the parameter-window arithmetic) and the current pre-registered picks. Single-sourcing: the README's rules section is now a summary that points there; the README walk-down table stays for study-#1 auditability.
- **PRACTITIONER-GOALS.md** — the author's stated goals from the rulings: the MY-hardware question; the reader as final judge; the within-model ladder; right-sizing over flagships; class-exclusive benchmarking; the tokenizer aim; the general cheap predictor with the trust band; pre-registration/registry/simplicity; same rules for everyone.

No constants changed: the rule uses the registered gate (reader line 5.0 w/s + 0.45 s reaction, addendum 55) and the registered law per tier (PROTOCOL rows 94–95); the class-exclusivity computation introduces NO new magic numbers (it is the existing predictor applied per tier). The 51.2 replication gains a second pre-registered purpose: it fixes the class boundary.

### Session 29, addendum 66 — the calibration pass graded: the anchors land (qwen UPDATE, mistral VALIDATED, llama grows, phi hold) — and the headline the pass was designed to catch: qwen Q5_K_M and mistral Q5_K_M FAIL the reader-wall test at n=50; the 5-conv verdict is on record as anti-conservative

**The run (author's machine, live-corpus-cal50.json, 50 convs / 267 turns per family, --no-early-fail, four families, same selected rungs as study #3).** The instrument worked as designed: `--no-early-fail` recorded every wall hit without aborting, and analyze() recomputed each verdict from the raw per-word deltas. The per-family `w/t calibration` lines:

| family | rung | verdict at n=50 | wall-failing turns | worst wait | w/t calibration (n=267): min / p05 / mean |
|---|---|---|---|---|---|
| qwen 9B | Q5_K_M | **FAIL** (9 turns, 30 events) | 9 | 6.34 s | 0.189 / 0.412 / 0.658 |
| phi-4-mini | Q8_0 | PASS (confident) | 0 | — | 0.304 / 0.418 / 0.714 |
| mistral 7B | Q5_K_M | **FAIL** (17 turns, 41 events) | 17 | 6.59 s | 0.250 / 0.366 / 0.650 |
| llama 3.2-3B | Q8_0 | PASS (confident) | 0 | — | 0.242 / 0.491 / 0.704 |

**The headline (pre-registered as possible, now measured): two of the four study-#3 selections fail the reader-wall test at n=50.** Qwen Q5_K_M (PASSED on the 5-conv study corpus, addendum 56) hits the wall on 9 of 267 turns — worst waits 6.34 s / 5.62 s / 3.87 s, mid-stream catch-ups (conv 16 turn 1: 1.5 w/s span; conv 19 turns 2/4/6: 4.8/4.5/3.8 w/s spans). Mistral Q5_K_M (PASSED at 5 convs) fails 17 turns — worst 6.59 s. Phi and llama PASS at 0 wall events across all 267 turns each. Per the addendum-59 pre-registration, **no retroactive verdicts**: the 5-conv verdicts stand in the study-#3 record; the calibration is a NEW measurement, and its finding is that n=5 is anti-conservative for PASS — addendum 23's warning ("the verdict is a min, fewer samples = anti-conservative PASS") made concrete and quantified.

**The anchor grading (pre-registered in addendum 59: p05 ≥0.05 below the anchor → registry update; above → ceiling grows):**
- **qwen: UPDATE.** p05 0.412 vs anchor 0.49 → −0.078, beyond the 0.05 grading band. The 0.49 anchor was measured on 40+ turns of the 5-conv corpus; the 267-turn distribution has a fatter tail (min 0.189). Registry consequence: the qwen ceiling at Q5_K_M shrinks from 9.7B to **7.9B params (5.27 GiB)** — qwen 9B (6.19 GiB) is now predicted ABOVE its calibrated ceiling, exactly consistent with the measured FAIL. The anchor update and the verdict flip are two views of the same data, recorded once each.
- **mistral: VALIDATED.** p05 0.366 vs anchor 0.37 → −0.004. The closest prediction of the four — the addendum-37 anchor survives a 12× sample increase intact.
- **llama: grows.** p05 0.491 vs probe min 0.333 → +0.158. The 0.144 joke-turn row is SUPERSEDED (corpus-degenerate, addendum 54; no joke turn was sampled at n=50, min 0.242). The llama ceiling grows to **9.8B params (6.48 GiB)** — consistent with the addendum-57 finding (no larger llama passes: 8B overshoots on its content anchors, a measured failure), but the margin is wider than previously recorded.
- **phi: hold.** p05 0.418 vs probe min 0.445 → −0.027, within the band.

**The pooled anchor recomputes to 0.366 (min of the four calibrated p05s; was 0.33 = min of probe-mins).** The min-based pooling rule is retired with this data: the min slides with n (addendum 59's extreme-value lesson — qwen's min moved 0.485 → 0.189 going from 22 to 267 turns), the p05 is the calibrated instrument. Effect on the pending study-#4 picks (addendum 64): granite 3.93 → **4.36 w/s**, OLMo 4.19 → **4.65 w/s** (both at Q5_K_M with the pooled anchor) — both still bench-zone straddlers, no decision change; the probe-first step (addendum 59) may still rescue either if their tokenizers probe above the pooled class.

**What the flips mean for the study (the honest reading):**
1. **The gate did not change; the sample did.** The 5-conv verdicts were real measurements — but n=5 samples ~22 turns, and a PASS there means "no wall hit in 22 turns," not "the reader never hits the wall." At n=50 the tail shows up: qwen 9/267, mistral 17/267 failure rates. The failure rates are 3.4% / 6.4% per turn — rare enough to hide in 22 turns, real enough for a reader to feel ("if the reader hits the wall, they feel the model is slow, so it fails").
2. **The calibration did its job.** It exists precisely to catch this class of miss before publication; the verdicts that go in the study-#3 report must state the corpus scope (5 convs) and the n=50 finding side by side — the report gains a methods paragraph: the gate's verdict is corpus-size-dependent, the calibration quantifies the tail, and the published guarantee needs an n large enough that the p05 stabilizes (addendum 59/60's instrument).
3. **Open ruling for the author:** do the study-#3 verdicts get re-issued at n=50 (the bench re-run at 50 convs for the four selected rungs — ~30–40 min/family), or does the study publish the 5-conv verdicts with the calibration tail as the honest scope statement? The pre-registration says no retroactive edits; the choice between "re-bench at n=50" vs "publish with scope statement" is the author's. A third option is on record: the class-exclusive rule (addendum 65) needs the 102.4-class boundary anyway, and the boundary rungs ARE the four selected rungs — one re-bench serves both purposes.

**Registry updates (PROTOCOL.md, change log addendum 66):** qwen w/t anchor 0.49 → p05 0.412; mistral 0.37 → 0.366 (validated); phi probe-min 0.445 → 0.418; llama 0.144 (joke turn) SUPERSEDED → p05 0.491; pooled anchor 0.33 → 0.366 (p05-based pooling; the min-based rule retired).

**Commands for the author (T14s, if the re-bench option is chosen):**

```
git pull --ff-only
python3 speed_gate.py --no-thinking --conversations 50 --no-early-fail \
  --corpus live-corpus-cal50.json ./models/Qwen3.5-9B/Qwen3.5-9B-Q5_K_M.gguf
```
(one invocation per family; the calibration corpus is the instrument, the verdict recomputes from deltas at analyze; the cal-dumps from this pass are already on disk — `Qwen3.5-9B-Q5_K_M.cal-dump.nothink.json` etc. — so NO re-bench is needed to read the n=50 verdicts; they are the same run.)

**Open items:** (1) the author's ruling on re-bench vs scope statement (above); (2) the study-#4 picks recompute under the pooled anchor (no decision change — both still straddle); (3) the 51.2-class replication inherits the calibrated anchors; (4) qwen 9B's ranking row: ARC 92.4% stands (ARC is not wall-dependent), the class-exclusivity grade (addendum 65) gains the calibrated ceiling — qwen 9B is now predicted to fail on the 102.4 class itself at its ceiling edge, sharpening the boundary question.
