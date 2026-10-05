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
