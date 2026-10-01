# Lab Notebook — LLMs on 102.4 GB/s System-RAM Machines

*Companion to the report draft. Every session logged; every prediction graded when the measurement lands. Format follows study #1 (Vega/DDR4, DOI 10.5281/zenodo.22855666).*

## Context

- **Previous study (51.2 GB/s):** effective bandwidth 34 GiB/s (~66% of peak), live t/s ≈ 26 ÷ size(GiB), 20 t/s threshold ⇒ 1.3 GiB budget. Champion: Qwen2.5-1.5B-Instruct Q5_0 (75.2% ARC, ~21 t/s live, 1.17 GiB).
- **This study:** 102.4 GB/s class, system-RAM machines only (DDR5-6400 dual channel, shared memory, iGPU). dGPU-VRAM inference out of scope.


## Sessions

- [Session 1 — 2026-09-21 (project setup, no measurements)](session-01.md)
- [Session 2 — 2026-09-21 (test machine confirmed)](session-02.md)
- [Session 3 prep — tooling commands (pre-registered, not yet run)](session-03.md)
- [Session 4 — 2026-09-21 (first llama-bench: Qwen2.5-3B Q4_K_M, prediction grading)](session-04.md)
- [Session 5 — 2026-09-21 (quant ladder, Qwen2.5-3B, all first-party)](session-05.md)
- [Session 6 — 2026-09-21 (Windows machine STREAM calibration, WSL2)](session-06.md)
- [Session 7 — 2026-09-21 (roster revision: stricter selection algorithm)](session-07.md)
- [Session 21 — 2026-09-23 (multiplatform port: Windows run prep + pre-registered predictions)](session-21.md)
- [Session 22 — 2026-09-23 (study #2 roster ruling: fresh selection at 51.2 GB/s, popularity-sourced)](session-22.md)
- [Session 23 — 2026-09-24 (thinking-model category: rulings, tooling, predictions)](session-23.md)
- [Session 24 — 2026-09-24 (T14s thinking roster: procedure re-run, two-category structure)](session-24.md)
- [Session 25 — 2026-09-24 (first thinking-category measurement: Qwen3.5-4B)](session-25.md)
- [Session 27 — 2026-09-26 (protocol v2: the depth-prefill gate; the reader guarantee replaces the floor)](session-27.md)
- [Session 34](session-34.md)
- [Session 35 — 2026-10-01 (the Q4_K_M sweep: context-over-parameters confirmed; the merged best-of pages)](session-35.md)
