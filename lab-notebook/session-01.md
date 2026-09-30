## Session 1 — 2026-09-21 (project setup, no measurements)

**Done:**
- Uploaded and reviewed study #1 report and the memory-bandwidth generations table.
- Scope decided: system-RAM machines only.
- Report draft started (goals, carry-over methodology, open questions).
- Pre-registered five cross-study predictions (see report draft §2).
- This notebook started.

**Open items:**
- Choose test machine (need DDR5-6400 dual-channel + modern iGPU; note: many laptops ship single-channel RAM — verify with a bandwidth tool before trusting the tier).
- Pin llama.cpp build + converter version.
- Prepare the strict-ARC harness + question cache from study #1 (identical, for paired comparison).
- Decide model roster.

**Predictions on record (status: pending):**
1. Effective bandwidth ~68 GiB/s (66% efficiency holds) → live t/s ≈ 52 ÷ size(GiB), ~46 for slow families
2. 20 t/s comfort threshold ⇒ ~2.6 GiB size budget
3. Quant recovery Q4→Q6 (+2.5–3.2 pp ARC) is hardware-independent
4. K-quant speed penalty (7–11%) shrinks or vanishes on matrix-core iGPUs
5. One formula across tiers: ~2× t/s at equal file size vs study #1, ±15%
6. **Champion configuration (detail in report draft §2.1):** 3B-class, Q5_0, ~2.2–2.5 GiB file, ~20–24 t/s live, strict-ARC 74–79%, 2024-gen non-thinking instruct family (e.g. Qwen2.5-3B). Verification rule: bench tg128 ≥ 52. Weakest links: ARC band (harness-transfer wildcard) and encoding availability.

