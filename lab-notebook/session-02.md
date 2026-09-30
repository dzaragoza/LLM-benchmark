## Session 2 — 2026-09-21 (test machine confirmed)

**Machine:** Lenovo ThinkPad T14s Gen 4 (AMD), model 21F8CTO1WWNL2 (CTO = configured-to-order).

**Confirmed by author: AMD Ryzen 7 PRO 7840U with Radeon 780M.** Platform specs per Lenovo PSREF; RAM is LPDDR5X-6400, soldered, dual-channel 128-bit.

**Why this machine fits the study:**
- Exactly the 102.4 GB/s system-RAM tier — the clean 2× step from study #1's DDR4-3200 (51.2 GB/s). Same UMA shared-memory design.
- 780M iGPU: 12 RDNA 3 CUs, **has WMMA matrix instructions** (study #1's Vega: none). Direct test of prediction 4 (K-quant penalty).
- Zen 4 CPU (AVX-512 on the CPU side, unlike study #1's Zen 3 AVX2) — CPU-vs-Vulkan comparison will differ from study #1 in both directions.

**Study-relevant hardware summary:**

| Component | Spec |
|---|---|
| CPU | Ryzen 7 PRO 7840U — 8C/16T Zen 4 ("Phoenix"), up to ~5.1 GHz, 16 MB L3, AVX-512 |
| iGPU | Radeon 780M — 12 RDNA 3 CUs, WMMA matrix support, ~2.7–2.9 GHz |
| Memory | LPDDR5X-6400 soldered, dual channel (128-bit) → 102.4 GB/s theoretical, shared UMA |
| OS | openSUSE (user's daily driver — different from study #1's Windows 11; note for methods section) |

**Caveats on record:**
- Soldered RAM: no dual/single-channel ambiguity possible (always dual-channel on this chassis) — removes a study #1 risk class.
- Memory clock/power-state behavior under sustained load (laptop thermal envelope, 28 W-class APU vs study #1's 35–65 W desktop) may reduce sustained bandwidth vs peak. The pure memory-copy baseline (Session 3, planned) measures this before any LLM work.
- OS and backend differences vs study #1 (openSUSE/Linux, likely different Vulkan driver stack — RADV/Mesa vs Windows driver). Must be documented, not assumed equivalent.

**Open items:**
- Verify actual memory speed on the running machine (`dmidecode -t memory`) — LPDDR5X-6400 assumed from platform, not yet confirmed on this specific unit.
- Baseline memory-copy bandwidth measurement (Session 3) — GPU copy and CPU copy, before any llama.cpp runs.
- Pin llama.cpp build; confirm Vulkan reports WMMA availability.
- Model roster + fetch GGUFs.

## Framing note (2026-09-21) — "witness machine" methodology

Study #1's machine selection was ad hoc ("this is what I have"). Study #2 inverts it: the T14s Gen 4 / 7840U was *chosen* from the 102.4 GB/s class as a **witness machine** — a representative member of the tier, selected for tier-typical bandwidth (LPDDR5X-6400 dual channel), UMA shared-memory design (so the formula transfers), and matrix-capable iGPU (so prediction 4 is testable). The claim structure changes accordingly: study #1 claims "this machine"; study #2 claims "this *class*", with the witness machine as evidence. Limitation to state in the eventual report: one witness per tier is still n=1 for tier-level generalization.

