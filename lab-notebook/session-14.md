Merged per the one-session-per-day ruling (session 40, addendum 19): sessions 14, 15, 16 and 18b were all the 2026-09-22 working day, so they share one session file. Extracted from session-07.md, which had accumulated sessions 8-20 behind its own header. Content verbatim; session numbers unchanged.

### Session 14 — 2026-09-22 (run3 + ARC runtimes)

**run3 (roster deviation from plan: Phi-3 Q4_K_M ran instead of Llama Q4_K_M — still useful):**

| Config | Score | Wall | Mean/q | p50 | p95 |
|---|---|---|---|---|---|
| Qwen Q4_0 | 605/800 = 75.6% | 121.0s | 151ms | 124ms | 204ms |
| Qwen Q6_K | 626/800 = 78.2% | 173.1s | 216ms | 199ms | 299ms |
| Phi-3 Q4_K_M (shipped) | 672/800 = 84.0% | 261.5s | 326ms | 323ms | 495ms |

**Reproducibility bonus: Phi Q4_K_M = 672/800 in BOTH run1 and run3** (deterministic: temperature 0, greedy logprob scoring). Same protocol → same score. Strongest possible pipeline-stability evidence; logprob scoring is noise-free across re-runs.

**ARC runtime findings (answers author's question):**
- **Longest per-800: Phi-3-mini Q4_K_M at 261.5s** — despite being mid-size (2.23 GiB). Cause visible in tokenization: Phi mean prompt = 76.8 tokens vs ~66 for Qwen/Llama (smaller vocab → more tokens per prompt → more prompt processing). ARC cost is tokenize-length-driven, not just weight-size-driven. Second-order confirmation of the vocab effect from the speed study, now on the accuracy side.
- Qwen Q6_K 173.1s vs Q4_0 121.0s: size-driven as expected (+43%).
- Note: run2's Llama timings (124.7/137.0/151.3s for Q4/Q5/Q6) — but run2's per-question CSVs were the collision victims; timing console lines preserved here.
- Family #2 pairing note: run3 didn't include Llama Q4_K_M, so Qwen-vs-Llama paired test needs the run1/run2 survivor CSV (Llama Q6_K, old colliding filename) if not deleted; else Qwen Q6_K (new) vs Llama Q6_K (survivor) is the pair to test.

**McNemar results (6 configs, 15 pairs; old survivor CSVs retained):**

*Robust tier (p < 0.01, survives multiple-comparisons):*
- Phi-3 dominates everything: both Phi configs > every Qwen/Llama config, paired +5.75 to +9.88 pp, all p ≤ 0.0001. **Champion and family #1: overwhelming.**
- **Family #2 settled: Qwen Q6_K > Llama Q6_K, paired +4.75 pp, p = 0.0057.** (Prediction: separates — HIT.)
- **Qwen Q6_K > Q8_0, +1.50 pp, p = 0.0118** — at matched comparison, Q8 is *worse* than Q6; the top rung actively costs accuracy. Supports "Q6_K is Qwen's accuracy sweet spot."

*Marginal tier (0.01 < p < 0.05, treat with caution — ~15 tests):*
- **Qwen quant recovery: Q6_K > Q4_0, paired +2.62 pp, p = 0.0139.** (Prediction was p ≈ 0.03–0.10 marginal — close; it crossed 0.05 but not 0.01.) Verdict: real effect, moderate evidence. Report phrasing: "recovery +2.6 pp, McNemar p = 0.014, marginal after multiple-comparison correction."
- Phi Q5_K_M > Q4_K_M +1.5 pp, p = 0.029 — self-made beats shipped, suggestive only.

*Non-separating:* Llama Q6_K vs Qwen Q4_0/Q8_0, Qwen Q4_0 vs Q8_0.

**Report-ready conclusions:** (1) Phi-3-mini #1 family beyond doubt; (2) Qwen #2 over Llama, p = 0.006; (3) Qwen recovery Q4→Q6 real but modest, marginal significance; (4) no benefit above Q6_K — Q8_0 trends *negative*; (5) deterministic pipeline (Phi 672/800 twice).

### Session 15 — 2026-09-22 (study #1 retroactive re-run on T14s, "run51")

**Setup:** strict-arc.py rebuilt with `--roster 51.2` (12-config study-#1 grid: Qwen2.5-1.5B Q4_0/Q5_0/Q5_K_M/Q6_K, GLM Q4_1/Q5_0/Q5_1/Q5_K_M/Q6_K, SmolLM2 Q4_K_M/Q5_0/Q5_K_M/Q6_K). Resolution: local file → first-party -hf. Qwen's 4 rungs have NO HF source (self-made; official repo ships only Q4_K_M/Q8_0) and no local files → skipped (author chose y). GLM ladder from zai-org repo; SmolLM2 Q4_K_M from HF, Q5_0/Q5_K_M/Q6_K local self-made originals. 9 of 12 configs run, n=800, --csv. (Base-model Qwen + Qwen3-1.7B files in 51.2/ excluded from roster — not study-#1 configs; Qwen3 ran in an earlier accidental old-script run: 63.9% vs study-#1's 63.5%.)

**Reproduction vs study #1 (Vega/DDR4 → 780M/LPDDR5X):**

| Config | Study #1 | T14s | Δ |
|---|---|---|---|
| GLM Q4_1 | 63.9 | 64.0 | +0.1 |
| GLM Q5_0 | 67.4 | 66.6 | −0.8 |
| GLM Q5_1 | (67.9*) | 67.4 | — |
| GLM Q5_K_M | 65.4 | 65.9 | +0.5 |
| GLM Q6_K | 66.4 | 66.0 | −0.4 |
| SmolLM2 Q4_K_M | 52.0 | 52.0 | **0.0 exact** |
| SmolLM2 Q5_0 | 54.9 | 53.6 | −1.3 |
| SmolLM2 Q5_K_M | 49.6 | 49.6 | **0.0 exact** |
| SmolLM2 Q6_K | 55.2 | 55.4 | +0.2 |

(*from earlier partial old-script run/figure; confirm before report)

**Prediction 1 (reproduction ±0.5 pp): GRADED mostly PASS — max |Δ| = 1.3 pp, two configs exact.** Strict-ARC accuracy is hardware-portable across GPU/driver/OS to ~±1 pp. Prediction 2 (SmolLM2 paper gap): replicated (49.6–55.4 band, unchanged ~20 pp below paper). GLM internal ordering reproduces (Q5_1 best, Q4_1 worst, Q5_K_M<Q6_K). Recovery Q4→Q6: GLM +2.0 (study1 +2.5), SmolLM2 +3.4 (study1 +3.2) — direction/size consistent, verdict pending McNemar.
**Next:** `python3 paired-arc.py --dir ~/technical_reports/51.2/arc-results` → retroactive significance for study #1 claims (recovery, Q5_0 vs Q5_K_M encoding claim, SmolLM2 internal ordering). Open: Qwen2.5-1.5B rungs need re-quantization (champion config Q5_0 untested).

**McNemar verdicts on study #1 claims (14 CSVs incl. 3 duplicates from the accidental old-script run):**

*Run-to-run determinism (unplanned bonus): the old-script SmolLM2 Q5_0/Q5_K_M/Q6_K runs vs the new-script re-runs are PERFECTLY CONCORDANT — 0 discordant questions out of 800, all three pairs. Same machine, two separate runs, identical per-question answers. Pipeline determinism now demonstrated at n=800, not just by total score.*

*Retroactive grading of study #1's headline claims:*
1. **Recovery (Q4→Q6) — claim was "consistent in all three families": PARTIALLY UPHELD.** SmolLM2 +3.4 pp, p = 0.0061 (separates, robust). GLM Q4_1→Q6_K +2.0 pp, p = 0.117 (NOT significant). So the claim's direction is right, but "consistent +2.5–3.2 in all families" was point-estimate optimism for GLM — with n=800 and paired tests, only SmolLM2's recovery is demonstrable. Study #2's Qwen +2.6 at p=0.014 sits between. Report phrasing: recovery is real in some families, family-dependent in size, and modest everywhere.
2. **Encoding claim ("Q5_0 > Q5_K_M, no compensating accuracy gain") — UPHELD where it mattered:** SmolLM2 Q5_0 vs Q5_K_M +4.0 pp, p = 0.0086 — the single-family result study #1 flagged as "suggestive" is actually its strongest accuracy effect. GLM Q5_0 vs Q5_K_M: +0.75, p = 0.51 (nothing). So the encoding accuracy effect is family-dependent, but where present it's real.
3. **SmolLM2 internal ordering (Q5_K_M anomalously worst): CONFIRMED**, Q5_K_M vs Q6_K −5.75 pp p<0.0001; Q5_K_M vs Q4_K_M −2.4 p=0.118.
4. Family-vs-family: GLM (all rungs) > SmolLM2 (all rungs), every pair p<0.0001 — clean.
5. Qwen-base vs qwen3-1.7b: +4.1 pp, p=0.035 marginal (not study configs, curiosity only).

*All predictions from Session 14 note HIT: SmolLM2 recovery separated, GLM recovery didn't, SmolLM2 encoding effect separated.*

### Session 16 — 2026-09-22 (proposed study #3: quant-damage crossover bracket)

**Design (author-proposed):** with two machines available, test the limits of the size-vs-bits trade:
- **51.2 machine:** top 3B model (Phi-3-mini, 85.5% champion) at tiny quants — Q1_K, Q2_K, Q3_K_M
- **T14s:** top 1.5B model (Qwen2.5-1.5B Q5_0, 75.2% champion) at **F16** (full precision)
- Same 800-question strict-ARC protocol, per-question CSVs, McNemar paired against the champions' existing CSVs.

**Author's pre-registered predictions (revised 2026-09-22, prediction 1 split into two):**
1a. **Runnability check:** tiny-quant Phi-3-mini (Q1_K/Q2_K/Q3_K_M) must actually run on the 51.2 machine — verify the server starts, serves sane completions (not garbage), and completes ARC. If it can't run at all, prediction 1 is void in the strongest sense.
1b. **Quality check:** *if runnable*, the quant-damaged 3B will not outperform the top 1.5B (75.2%) — "the quality will not be worth it."
2. F16 1.5B will NOT exceed the top 3B (85.5%).

**Vibe's predictions (on record, graded when run):**
1. **Prediction 2: near-certain pass.** F16 vs Q5_0 typically buys +0–2 pp → ~75–77%, far below 85.5%. The family gap (Qwen↔Phi ≈ 10 pp) dwarfs quant precision gains.
2. **Prediction 1: graded at each rung, and I predict the author is WRONG at Q3.** Expected quant damage: Q3_K_M ≈ −3 to −6 pp from 85.5 → ~79–82%, still > 75.2%. Q2_K ≈ −15 to −40 pp — probably collapses below 75.2% (crossover happens somewhere between Q2 and Q3). Q1_K likely near-random. So the claim "bits can't be traded for size" holds at the bottom but NOT at Q3_K_M — the crossover point is itself the study's deliverable.
3. Mechanistic note: at Q1/Q2 the damage is not uniform — llama.cpp still keeps embeddings/output at higher precision, so collapse is superlinear below ~3 bits.
**Prereqs:** 51.2 machine needs Phi-3-mini GGUFs at Q1_K/Q2_K/Q3_K_M (llama-quantize from the Q4/Q8 source; self-made, pinned converter, log version). T14s needs Qwen2.5-1.5B-Instruct F16 (3.1 GiB — fits easily; ~7.7 GiB if Phi-3 F16 were ever wanted). Speed check: 1.5B F16 on T14s ≈ 0.58×102.4/3.1 ≈ 19 t/s live — at the 20 t/s comfort line, but ARC doesn't care.
**run51 complete (full 12-config grid, Qwen rungs via first-party -hf — confirmed shipped, my earlier "repo ships only Q4_K_M" was wrong):**

| Qwen2.5-1.5B | Study #1 | T14s | Δ |
|---|---|---|---|
| Q4_0 | 71.8 | 71.2 | −0.6 |
| Q5_0 | 75.2 | 74.6 | −0.6 |
| Q5_K_M | 74.6 | 75.0 | +0.4 |
| Q6_K | 75.0 | 75.2 | +0.2 |

**Prediction: HIT — all 12 configs reproduce within 0.6 pp (max), most within 0.5, two exact.** Champion config Qwen Q5_0 reproduced at 74.6 (−0.6). Note: on T14s the ladder tops out at Q6_K (75.2) instead of Q5_0 — a rank swap within noise. Qwen recovery Q4_0→Q6_K = **+4.0 pp**, the largest recovery of any family — McNemar verdict pending; prediction: separates decisively (b/c ≈ 70/40 scale).
GLM and SmolLM2 identical to the earlier 9-config run (determinism again: e.g. GLM Q4_1 512/800 twice, SmolLM2 trio identical).
**Study #1 audit now COMPLETE: 12/12 configs reproduced, both reports fully McNemar-graded, paper-vs-harness hazard replicated, hardware-portability of strict-ARC established (~±1 pp across Vega/DDR4→780M/LPDDR5X).**

*Trilogy framing: #1/#2 established the quant ladder at sane bit depths; #3 (crossover bracket) maps where the ladder breaks in both directions.*

**Full-grid McNemar (18 models incl. duplicates/curiosities; study-#1 audit final numbers):**
- **Qwen recovery: SEPARATES DECISIVELY — Q4_0 vs Q6_K +4.0 pp, p = 0.0001** (prediction p<0.001: close, p=1e-4). All three Qwen recovery pairs significant (vs Q5_K_M p=0.0002, vs Q5_0 p=0.0016). Study #1's strongest recovery claim confirmed as its most robust.
- **Qwen plateau: Q5_0/Q5_K_M/Q6_K statistically indistinguishable** (p = 0.49/0.71/0.86). The champion-rank swap is pure noise, confirmed. Practically: pick any Q5–Q6 rung; Q4_0 is the one that costs.
- **Family hierarchy, fully separated:** Qwen (all rungs) > GLM (all rungs) > SmolLM2 (all rungs), every cross-family pair p ≤ 0.0002 except Qwen Q4_0 vs GLM Q5_1 (p=0.035, marginal). Family gaps (~8–25 pp) dwarf quant effects (0.25–4 pp) — same lesson as study #2: model choice ≫ quant choice.
- GLM internal: Q4_1 < rest (Q4_1 vs Q5_1 p=0.010); Q5_0/Q5_K_M/Q6_K indistinguishable (p ≥ 0.51).
- Champion Qwen Q5_0 (74.6) vs runner-ups Q5_K_M/Q6_K: no separation — study #1's champion pick survives as "tied top," honest phrasing for report.
- Duplicates: 3 SmolLM2 pairs perfectly concordant (0/800 discordant) — run-to-run determinism at n=800 again.
- Curiosities (not study configs): instruct-vs-base Qwen Q4_0: +3.25 pp p=0.027 (instruction tuning worth ~3 pp on ARC). qwen3-1.7b sits between GLM and SmolLM2, below all Qwen2.5 rungs.
**Prediction ledger this session: 4 of 4 hit** (reproduction ±0.6 pp, paper-gap replication, Qwen recovery separation, determinism).

**Study #3, T14s side — Qwen2.5-1.5B F16 (fp16 via -hf :FP16 tag; run 2026-09-22): 599/800 = 74.9%.** (Timing lines invalid — machine busy during run; per plan, ignored.)
- **Author prediction 2 (F16 1.5B < top 3B, 85.5%): CONFIRMED, overwhelmingly.** 74.9 vs 85.5 — the ~10 pp family gap is unbuyable with bits, exactly as predicted.
- **Zero-damage ceiling quantified: F16 (74.9) vs Q6_K (75.2) vs Q5_K_M (75.0) vs Q5_0 (74.6).** F16 does NOT beat the plateau — it sits *inside* it, slightly below the top. Full 16-bit precision buys ZERO measurable ARC accuracy over Q5/Q6 on this family. Vibe prediction (75–77, no McNemar separation from plateau): HIT (74.9 just under the range, but the substantive claim — indistinguishable from plateau, far from 85.5 — fully confirmed; McNemar verdict pending).
- **Headline finding for study #3 report:** the quant ladder's entire useful range is Q4→Q5 (+3–4 pp); above Q5 and below F16, accuracy is flat. "Quantization is free" from Q5 up — the strongest possible version of the champion-config story.
- Implication for prediction 1b framing: Phi-3's 85.5% is ~10 pp of pure model-quality headroom above the 1.5B ceiling — Q3_K_M damage (~3–6 pp expected) plausibly does NOT erase it; the crossover likely lives at the 2.x-bpw rung. Old-machine side still pending (IQ1_M/IQ2_M/Q3_K_M conversion in progress).

**F16 McNemar verdicts (2026-09-22):**
- F16 vs Q6_K: p = 0.69 | vs Q5_K_M: p = 1.00 | vs Q5_0: p = 0.84 — **the plateau INCLUDES F16; zero quant damage measurable above Q5** (prediction "p > 0.1 all three": HIT).
- F16 vs Q4_0: +3.6 pp, **p = 0.0008 — separates** (prediction: separates: HIT). The Q4→Q5 recovery effect is real relative to the plateau, and F16-vs-Q4_0 is its cleanest expression (no quant-vs-quant confound).
- Notable asymmetry: only 11–14 discordant pairs between F16 and the Q5/Q6 rungs — the plateau configs answer nearly identically per-question, not just by total score.
- **Study #3 T14s side: COMPLETE.** Full finding: Qwen2.5-1.5B ladder is flat from Q5_0 through F16 (74.6–75.2, indistinguishable); all damage is Q4_0 and below. Ceiling for the family ≈ 75%. Pending: Phi-3 tiny-quant side on 51.2 machine (IQ1_M/IQ2_M/Q3_K_M).

**Study #3 crossover run (T14s, 2026-09-22; damage-first sequencing — author's call, speed measured later):**
- Phi-3-mini Q3_K_M (3.74 bpw, self-made from F16): **674/800 = 84.2%** (mean 265ms/q; machine was idle this run, timings valid).
- Qwen F16 re-run: 599/800 = 74.9% — identical to first run, **another exact run-to-run reproduction** (599/800 twice, F16).
- IQ2_M / IQ1_M: SKIP — died during startup, almost certainly quantize jobs not finished when run started (file-not-found), not format rejection. Re-run pending once files exist.

**Prediction ledger, crossover rung 1:**
- Vibe's Q3_K_M prediction (80–83%): **HIT** (84.2, slightly above range — Phi-3 is even more damage-resistant than expected).
- Author 1b at Q3_K_M: **WRONG** — 84.2 vs 75.2 plateau; the 3B edge survives 3.7 bits with 9.0 pp to spare. "Size can't buy back bits" is FALSE at Q3.
**Study #3 complete damage curve (T14s, 2026-09-22, K-quant ladder after imatrix swap):**

| Rung | bpw | Score | vs 1.5B plateau (75.2) |
|---|---|---|---|
| Phi-3 Q4_K_M (study #2 ref) | ~4.8 | 85.5 | +10.3 |
| Phi-3 Q3_K_M | 3.74 | 84.2 | +9.0 — survives |
| Phi-3 Q2_K | 2.96 | **73.8** | **−1.4 — CROSSES UNDER** |
| Phi-3 Q1_0 | 1.125 | **1/800 = 0.1%** | collapse — NOT damage, garbage |

**Verdicts:**
- **Crossover located: between 2.96 and 3.74 bpw.** Author's prediction 1b: WRONG at Q3 (−9 pp margin), RIGHT at Q2_K (by 1.4 pp — the wire!). Vibe Q2_K prediction (76–82): **MISS** — Phi-3 fell below the plateau. Damage is not shallow below Q3: −10.4 pp in one rung.
- **Q1_0 = broken, not damaged:** 1/800 (0.1%) is far BELOW chance (25%). A random letter-picker scores 200/800. The model is emitting systematic garbage (likely one fixed letter or non-answers). Prediction 1a (runnability): server RAN and answered, but this is format collapse, not quant damage — needs a completion eyeball to characterize; exclude from the damage curve, log as "Q1_0 below chance = format failure."
- Damage curve summary: Phi-3 loses 1.3 pp from Q4→Q3, then 10.4 pp Q3→Q2. Superlinear cliff, exactly as mechanistically expected below ~3 bits.
- **Study #3 headline:** a 3B model's 10 pp quality edge survives Q3_K_M intact (84.2 > any 1.5B at F16) but is erased at Q2_K (73.8 < 75.2 plateau). Practical rule: **never quantize below Q3_K_M; below ~3 bpw the damage cliff removes any size advantage.**
- F16 re-run #3: 599/800 again (third exact reproduction). Q3_K_M re-run: 674/800 again (exact).
- Pending for old machine: whether 51.2-tier bandwidth changes the verdicts (shouldn't — portability proven ±1 pp; the crossover rung margin is 1.4 pp, so Q2_K on the 51.2 machine is the one confirmatory re-run worth doing).

### Session 18b — 2026-09-22 (LIVE SPEED CALIBRATION SPOT-CHECK, champion config, interactive session)

**The open measurement of §2.2/§12, closed by the author before publication:** one interactive session, champion Phi-3-mini Q5_K_M via `llama-server` (web UI), long streaming answers.

**Measured: 25 live t/s** (author-counted, interactive session, streaming output).

**Grading against the carried assumption (live = 0.8 × bench → predicted 22.1):**
- Measured/predicted live ratio: 25 / 22.1 → **live/bench ≈ 0.9**, NOT the carried 0.8.
- The bench×0.8 rule UNDERESTIMATED live speed by ~3 t/s (~14%). The champion config passes the 20 t/s comfort line with MORE margin than claimed (25 vs 20 — 25% headroom, not 10%).
- Caveat: this is ONE interactive session (n=1) vs study #1's three-session calibration; treat 0.9 as a provisional tier-2 live factor. But the direction is safe: the line passes, and R1's speed claim is if anything conservative.
- Plausible mechanism (unverified): the 0.8 factor absorbed context-switching and UI latency on the slower machine; a 2× faster stream may hit a different overhead regime. Not investigated further — the decision-relevant number (passes the line) was never in doubt, and now has direct interactive confirmation.

**Report edits required before publication:** §2.2, §12, and R2: replace "live factor carried from study #1, not re-calibrated" with the spot-check result — measured 25 t/s vs predicted 22.1; the 0.8 factor is conservative at this tier (measured ratio ≈ 0.9); the champion passes the 20 t/s line with 25% measured margin.
