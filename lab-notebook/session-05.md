## Session 5 — 2026-09-21 (quant ladder, Qwen2.5-3B, all first-party)

| Quant | Size (GiB) | tg128 (t/s) | Implied BW (GiB/s) |
|---|---|---|---|
| Q4_0 | 1.86 | 40.31 ± 0.15 | 75.0 |
| Q4_K_M | 1.95 | 38.27 ± 0.14 | 74.6 |
| Q5_0 | 2.21 | 34.40 ± 0.04 | 76.0 |
| Q5_K_M | 2.27 | 33.84 ± 0.15 | 76.8 |
| Q6_K | 2.60 | 29.53 ± 0.04 | 76.8 |

**Grading:**

1. **Prediction 4 (K-quant penalty shrinks or vanishes): GRADED PASS — vanished, cleanly.** Per-byte bandwidth is flat across the ladder (74.6–76.8 GiB/s, ±1.5%). The raw t/s gap in the Q4 pair (40.31 vs 38.27, +5.3% for Q4_0) is almost entirely explained by file size (1.86 vs 1.95 GiB, 4.6% smaller) — at equal bytes, the encodings are equivalent. Study #1's 7–11% legacy advantage (Vega, no matrix cores) did not survive the jump to RDNA 3 + coopmat + int-dot. **Study #1 recommendation #5 ("prefer legacy encodings") has an expiry condition: it applies to pre-matrix-core iGPUs only.**
2. **Ladder-flat prediction (implied ~74 ± 5% at every quant): PASS.** Tightest confirmation yet of "size is destiny."
3. **Q6_K ~25–27 t/s prediction: MISSED** (measured 29.53). Root cause: I predicted against the listed 2.79 GB, actual bench size 2.60 GiB — per-formula the result is exact (75/2.60 = 28.8). Prediction arithmetic error, not a formula failure. Recorded.
4. **Repeatability check:** Q4_K_M re-measured 38.27 vs Session 4's 38.40 (−0.3%) — consistent with study #1's ±0.7% bench noise. Instrument validated.

**Emerging picture:**
- Effective bandwidth on this machine: **~75 GiB/s flat** (73% of theoretical), family spread smaller than study #1's.
- Live t/s rule for this machine: **live ≈ 60 ÷ size (GiB)**, confirmed across 6 configurations and 2 families.
- Every rung of the ladder is comfortably above the 20 t/s live line (Q6_K ≈ 23.6 live; Q5_0 ≈ 27.5 live; Q4_0 ≈ 32 live).
- **Champion-shaping observation:** on study #1's machine, the 20 t/s line forced Q5_0. Here even Q6_K passes with margin, and Q8_0 (3.62 GiB → ~16.6 live) fails. So the *speed* constraint alone permits up to ~2.9–3.0 GiB — the champion quant for Qwen2.5-3B will be decided by **ARC accuracy**, not speed: if quant recovery flattens at Q5 (study #1's finding), Q5_0/Q5_K_M; if it keeps climbing, Q6_K. The accuracy runs are now the deciding experiment.

**Next:** strict-ARC harness port to Linux (Python, same question cache as study #1, n=800, ±3.3 pp bins) and run the ladder through it. Also pending: Llama3.2-3B and Phi-3.5-mini self-quantization (deferred).

### Session 5 addendum — Q8_0 and FP16 runs (author proposal: "we may get a surprise in our size prediction")

Rationale on record: Q6_K beat the live-threshold prediction with margin; pushing past the budget boundary to see where the model actually breaks. First-party files available: Q8_0 (3.62 GB listed); FP16 ships as a 2-part split file (fp16-00001/00002-of-00002, 3.98 + 2.82 GB = 6.80 GB total) — llama-bench `-hf` may not handle split GGUFs; verify, else concatenate (`gguf-split --merge`) or self-convert. **Wait — split files:** llama.cpp supports `gguf-split` natively; `llama-bench -m` accepts the first shard. If `-hf` fails on the split, local path is the fallback.

**Command:**

```bash
./llama-bench \
  -hf Qwen/Qwen2.5-3B-Instruct-GGUF:Q8_0 \
  -t 8 -p 0 -n 128 -r 3 -ngl 99
```

**Pre-registered predictions (before the run):**
- **Q8_0 (3.62 GB listed, expect ~3.45 GiB): tg128 ≈ 21–23 t/s** (formula: 75 ÷ 3.45 ≈ 21.7; ±5%). Live ≈ 17–18 — **below the 20 t/s comfort line.** Prediction: Q8_0 fails the comfort threshold, but bench tg128 ≥ 20 still verifies.
- **The "surprise" the author is probing for:** the ladder's implied bandwidth has *risen slightly* with quant level (74.6 → 76.8 GiB/s from Q4_K_M to Q6_K). If that trend is real (better locality, fewer dequant ops per byte), **Q8_0's implied BW could exceed 78–80 GiB/s**, making it faster than the naive formula predicts. Pre-registered: if Q8_0 implied BW > 78, the formula gains a quant-level correction term and the size budget grows.
- **FP16 (~6.35 GiB): tg128 ≈ 11–12 t/s** if formula holds; also tests whether fp16 tensor path (no dequant at all) preserves the high end of the bandwidth curve. Not a comfort-threshold candidate — pure data for the formula's upper end.
- Update to prediction 2 (size budget): if Q8_0 lands ≥ 22 bench t/s (≥17.5 live), the "budget at 20 t/s live" stays ~3.0 GiB. If the surprise materializes, revise budget upward accordingly.

**Q8_0 result (2026-09-21):** 3.36 GiB → **23.38 ± 0.15 t/s**. Implied bandwidth: **78.6 GiB/s** (76.8% of theoretical peak).

**Grading the "surprise" prediction: PARTIAL HIT — the trend is real.**
- Naive prediction was 21–23 t/s from flat 75 GiB/s; measured 23.38 — top of the band and **above** the flat-formula point (21.7).
- Implied BW by quant: Q4_K_M 74.6 → Q5_0 76.0 → Q5_K_M 76.8 → Q6_K 76.8 → **Q8_0 78.6 GiB/s**. Monotonic-ish rise of ~5% across the ladder. The formula gains a **quant-level correction term**: higher-bit quants stream slightly more efficiently (plausible mechanism: fewer dequant arithmetic ops per byte, better memory access regularity). Effect is modest but consistent.
- **Comfort-line arithmetic, updated:** 23.38 bench ≈ 18.7 live — still just below 20. But the *budget* at 20 t/s live now computes as 75–78 × 0.80 ≈ **60–62 GiB/s effective live** → budget ≈ **3.0–3.1 GiB**, and at the Q8_0-implied 78.6: 20 live = 78.6 × 0.80 ÷ 20 ≈ 3.14 GiB. Call it: **size budget ≈ 3.0–3.2 GiB** (was 2.6 predicted, 3.0 assumed). The boundary is softer than study #1's — champion selection is firmly an accuracy question.
- FP16 run still pending (split-file handling) — would pin the top of the correction curve.
- Caveat on record: single model family; the correction term is provisional until a second family shows the same slope (candidate: Gemma3-4B QAT only ships Q4_0, so the cross-family check needs the self-quantized Llama3.2 or Phi-3.5 ladder later).

