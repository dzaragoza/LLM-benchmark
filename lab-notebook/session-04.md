## Session 4 — 2026-09-21 (first llama-bench: Qwen2.5-3B Q4_K_M, prediction grading)

**Device selection confirmed:** startup log shows `AMD Radeon 780M Graphics (RADV PHOENIX) | uma: 1 | fp16: dot2 | int dot: 1 | matrix cores: KHR_coopmat` — correct GPU, no llvmpipe, UMA confirmed, coopmat active. Build b29c606e2 (10964) matches study #1's pin.

**Author context note (from study #1, underreported in the report):** the CPU-skip rationale in study #1 was that GPU prefill was substantially faster with acceptable tg loss — CPU comparisons were secondary. Recorded here for accurate cross-study framing.

**Results:**

| Config | pp512 (t/s) | tg128 (t/s) |
|---|---|---|
| Vulkan, -ngl 99, -t 8 | **759.5 ± 33.0** | **38.40 ± 0.36** |
| CPU, -t 8 | 50.21 ± 0.71 | 22.86 ± 0.11 |
| CPU, -t 16 | 43.82 ± 0.60 | 16.24 ± 0.86 |

Model: 1.95 GiB, 3.40 B params (Q4_K_M). CPU binary loaded `libggml-cpu-zen4.so` (AVX-512 path confirmed).

**Prediction grading:**

1. **Prediction 1 (~68 GiB/s effective): GRADED PASS, conservative.** Implied bandwidth = 38.40 × 1.95 = **74.9 GiB/s** (~73% of 102.4 peak; 91% of the clpeak raw GPU ceiling of 82). Point prediction was 68 → measured +10%. Within the ±15% band. Note: this is a *K-quant* — study #1 found K-quants 7–11% slower than legacy, so the legacy-encoding effective bandwidth on this machine may be ~80 GiB/s. Efficiency (73%) is *higher* than study #1's 66% — the tier scales super-linearly so far.
2. **Prediction 5 (2× at equal file size, ±15%): GRADED FAIL, optimistic direction.** Qwen2.5 Q4_0 on study #1's machine implied ~28.1 GiB/s (28.35 t/s × 0.99 GiB); here 74.9 GiB/s in a K-quant → **~2.7×**, not 2×. The bandwidth tier doubled but efficiency also rose (66→73%), compounding. The formula transfers, the *efficiency constant* does not. Correction on record.
3. **Prediction 7 (Vulkan wins generation): GRADED PASS, strongly.** 38.4 vs 22.9 t/s — Vulkan +68%, a full reversal of study #1's −31%. The better streaming engine won, as the baseline data suggested.
4. **tg smoke-test band (32–35): MISSED, ~10% optimistic** — measured 38.4, above the band's top, below the 42 "suspicious" guardrail. The miss came from underestimating efficiency (73% vs the ~66% assumed). Honest accounting: my third measurable miss this study (after the .zip links and this band).
5. **Vulkan pp512 band (450–700): MISSED, optimistic direction** — measured 759.5, ~9% above the top of the band. coopmat is being exploited well by b10964/RADV.
6. **CPU pp512 band (250–400): BADLY WRONG.** Measured 50.2 — 5–8× below prediction. Study #1's Zen 3 did 157 t/s on the 1.5B; even adjusting for the 2× larger model (~78 expected), 50 is ~35% below that. **Open question, needs investigation:** possible causes — Q4_K_M dequant path in the zen4 CPU backend, batched prefill codepath differences at b10964, power/thermal state of the 28 W APU during sustained CPU load, or thread-pinning effects. Do not conclude until checked (e.g., re-run with `-t 8 --threads-batch 8`, monitor clocks, test Q4_0 for the dequant hypothesis).
7. **CPU `-t 16` vs `-t 8` (±20%): PASS** — pp 43.8 vs 50.2 (−13%), tg 16.2 vs 22.9 (−29%, just outside for tg). SMT hurts on this workload; `-t 8` is the right CPU protocol, consistent with study #1.
8. **Vulkan prefill advantage ≥1.5× CPU: PASS, spectacularally** — 759.5/50.2 = **15×** (study #1: 2×). Combination of coopmat prefill strength and unexpectedly weak CPU prefill (item 6 — the 15× is inflated by whatever ails the CPU pp path; the true hardware ratio is lower).

**Live-speed estimate:** if study #1's live/bench ≈ 0.80 holds, 38.4 bench → ~31 t/s live for this 1.95 GiB model. The 20 t/s comfort threshold budget on this machine ≈ 26/0.80-adjusted... formula: live t/s ≈ (74.9 × 0.80) ÷ size ≈ **60 ÷ size (GiB)** for this class, ~2.4× study #1's 26. 20 t/s live ⇒ **~3.0 GiB budget** (vs predicted 2.6). Prediction 2 directionally right, conservative.

**Next steps:**
- Investigate the CPU pp512 anomaly — **CLOSED as out of scope (author decision, 2026-09-21):** the study's purpose is picking the fastest benchmark mode, not debugging CPU prefill. GPU wins both phases decisively; CPU is a dead end on this machine. Any future mention of the "15×" prefill ratio in reporting must carry the caveat that CPU pp underperformed scaled expectations, uninvestigated.
- Quant ladder for Qwen2.5-3B (Q4_0/Q5_0/Q5_K_M/Q6_K as available; self-quantize Q5_0 from safetensors) → grades prediction 4 (K-quant penalty on matrix-core GPU).
- Strict-ARC harness port to Linux + Qwen2.5-3B Q4_K_M accuracy → first data point for prediction 6's 74–79% ARC band.

### Session 4 addendum — cross-family model bench (planned, commands issued)

**Selection criteria (author-set):** top-8 Ollama families, first-party GGUF + technical report, ≥3B-class only (no smaller-parameter repeats of an owned family), within ~3.0 GiB budget. Qwen2.5-3B already measured.

**Roster:** Llama3.2-3B-Instruct (Meta, runner-up family), Gemma3-4B-it (largest in budget, 2025-gen folklore test), Phi-3.5-mini-instruct 3.8B (third family; tech report in model card — Phi-3.5 not arXiv-papered, flagged). Excluded: all <3B (author rule); Llama3.1-8B/Mistral-7B/Gemma2-9B (over budget; optional over-ceiling cautionary candidate = Llama3.1-8B Q4, decision pending).

**Command (single invocation, three -hf flags):**

```bash
./llama-bench \
  -hf meta-llama/Llama-3.2-3B-Instruct-GGUF:Q4_K_M \
  -hf google/gemma-3-4b-it-GGUF:Q4_K_M \
  -hf microsoft/Phi-3.5-mini-instruct-gguf:Q4_K_M \
  -t 8 -p 512 -n 128 -r 3 -ngl 99
```

**Provenance flags:** meta-llama repo is gated (license acceptance may be required for -hf); Google GGUF repo names to be verified by author with HF tooling; Phi-3.5-mini gguf repo name to be verified likewise.

**Pre-registered predictions (before the run):**
- Implied bandwidth (tg128 × size GiB) lands **70–80 GiB/s for all three** — formula claims size is destiny, family ±10%. Qwen2.5-3B measured 74.9.
- **Bet against the formula: Gemma3-4B** — architecture/vision-weight inflation is the likeliest pattern-breaker; a break = finding on formula family-dependence.
- Llama3.2: possible ~10% vocab-related penalty (128k tokenizer, Qwen mechanism).
- pp512: no cross-family prediction yet (compute-bound, architecture-dependent); collect first, model later.

**Update (author decision, 2026-09-21):** self-quantization conversions (Llama3.2, Phi-3.5) deferred. Gemma3-4B first-party QAT Q4_0 benched now. Provenance verification results on record: Meta and Microsoft ship no first-party GGUFs (safetensors only); Google ships `google/gemma-3-4b-it-qat-q4_0-gguf` (files: `gemma-3-4b-it-q4_0.gguf` + mmproj f16). Llama3.2/Phi-3.5 → self-quantize from safetensors later (study #1 champion workflow, pinned converter).

**Gemma command:**

```bash
./llama-bench -hf google/gemma-3-4b-it-qat-q4_0-gguf -t 8 -p 512 -n 128 -r 3 -ngl 99
```

**Pre-registered for Gemma (before the run):**
- File: ~2.5 GiB expected (Q4_0, 4B params + vision tower weights in mmproj file — text-only bench loads only the LM gguf; mmproj ignored by llama-bench).
- tg128 prediction: implied bandwidth at the **top of or above the 70–80 GiB/s band** — Q4_0 is a legacy encoding, and study #1 found legacy > K-quant by 7–11% on Vega. If that transfers to RDNA 3/coopmat, expect implied ~78–88 GiB/s → tg128 ≈ 31–35 t/s for a 2.5 GiB file.
- pp512: no prediction (architecture unknown territory — Gemma3's architecture is the most divergent of the roster).
- QAT caveat: weights were quantization-aware-trained for Q4_0 — accuracy comparison vs plain PTQ Q4_K_M models is not apples-to-apples; any ARC advantage must carry that label.

**Protocol update (author, 2026-09-21): pp measurement dropped.** All future benches use `-p 0` (study #1 protocol restored). Rationale: backend choice is settled (GPU dominates both phases), pp adds no decision value.

### Gemma3-4B results (2026-09-21)

**⚠️ Provenance anomaly — RESOLVED (author certification, 2026-09-21):** the 401 error was the Google repo license gate; the author accepted the Gemma license and re-downloaded via `hf download google/gemma-3-4b-it-qat-q4_0-gguf` — fetched 4 files, 4.01 GB, snapshot `15f73f5eee9c28f53afefef5723e29680c2fc78a`. Provenance certified by author: first-party Google release, pinned to this snapshot. Run is citable. (Lesson for the report: llama-bench will silently use a cached file when repo auth fails — check the log for auth errors on every gated-repo run.)

| Config | pp512 (t/s) | tg128 (t/s) |
|---|---|---|
| Vulkan, QAT Q4_0, 2.93 GiB, 3.88 B | 740.5 ± 13.7 | **23.96 ± 0.16** |

**Implied bandwidth: 23.96 × 2.93 = 70.2 GiB/s** (69% of 102.4 peak).

**Grading:**
- In-band prediction (70–80 GiB/s): **PASS, at the bottom edge.**
- Legacy-encoding-advantage prediction (top or above band): **MISSED.** Q4_0 showed *no* speed advantage over Qwen's Q4_K_M (70.2 vs 74.9 GiB/s implied) — the study #1 finding of legacy > K-quant did **not** reproduce here. First hint that the K-quant penalty vanished on matrix-core hardware (prediction 4: penalty "shrinks or vanishes"). **Caveat:** this is a cross-family comparison (Gemma vs Qwen), so it's suggestive, not clean — the real test is the quant ladder on one model (Qwen2.5-3B Q4_0 vs Q4_K_M, same weights).
- File size surprise: 2.93 GiB, not the ~2.5 predicted — QAT Q4_0 at 3.88 B params ran bigger than the rough 0.6 GB/B rule suggested.
- pp512 740.5: comparable to Qwen3B's 759.5 despite 2× params — Gemma3's prefill efficiency per param is high; recorded, no prediction was made (correctly).

**Live estimate:** 23.96 bench × 0.80 ≈ **19 t/s live** — just under the 20 t/s comfort line. Gemma3-4B is effectively *at* the budget ceiling: the formula's budget said ~3.0 GiB max, and 2.93 GiB lands at ~19 t/s live. Consistent, and the threshold table's prediction (2.6 GiB) again proved conservative.

