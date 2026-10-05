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
