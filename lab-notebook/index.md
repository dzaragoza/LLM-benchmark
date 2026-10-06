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
- [Session 28 — 2026-09-26 (protocol v2.1 roster: model selection anew; the memory shortcut)](session-28.md)
- [Session 29 — 2026-09-26/27 (the v2.1–v2.3 roster runs; protocol v3.0 — the reader-wall test; the calibration pass)](session-29.md)
- [Session 30 — 2026-09-27/28 (the sentinel certificate; protocol v3.1 — the stall rate)](session-30.md)
- [Session 31 — 2026-09-28 (the overnight lineage sweep graded — 7/7 PASS under v3.1)](session-31.md)
- [Session 32 — 2026-09-28 (the parameter ceiling derived; the whole-lineage roster)](session-32.md)
- [Session 33 — 2026-09-28 through 2026-09-30 (the registry catch-up 102–106; RULER built; protocol v4 — the depth ladder)](session-33.md)
- [Session 34 — 2026-09-30 (protocol v4.3 re-climb; the depth score is the ranking; addenda 41–43 committed 10-01)](session-34.md)
- [Session 35 — 2026-10-01 (the Q4_K_M sweep: context-over-parameters confirmed; the merged best-of pages)](session-35.md)
- [Session 36 — 2026-10-02 (the four-probe ceiling chase graded; the FWE difficulty knob; the tournament)](session-36.md)
- [Session 37 — 2026-10-03 (the n=21 completion; medals; certify as type + range; closed 10-04)](session-37.md)
- [Session 38 — 2026-10-04 (the VT gold certification graded; the speed gate redesign; the combined cell; the UMA census)](session-38.md)
- [Session 39 — 2026-10-05 (registry hygiene: wow.md section 10; protocol.md catch-up addendum 140; the session-per-day audit)](session-39.md)
- [Session 40 — 2026-10-06 (the VT heap ruling closed; the code_edit review — four bugs fixed, tool ownership transferred; the quality toolbox; the architecture audit; infra/ package; code_search; the certification redesign — n=20, equidistant medals, the ascending ladder, ruling B; the tier rename, the nameless run, the speed-dead climb stop; the leaked-spec retrieval bug fixed; Ctrl-C during a download stops the run; the root-json cleanup)](session-40.md)
