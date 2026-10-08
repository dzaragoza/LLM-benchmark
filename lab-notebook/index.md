# Lab Notebook — LLMs on 102.4 GB/s System-RAM Machines

*Companion to the report draft. Every session logged; every prediction graded when the measurement lands. Format follows study #1 (Vega/DDR4, DOI 10.5281/zenodo.22855666).*

## Context

- **Previous study (51.2 GB/s):** effective bandwidth 34 GiB/s (~66% of peak), live t/s ≈ 26 ÷ size(GiB), 20 t/s threshold ⇒ 1.3 GiB budget. Champion: Qwen2.5-1.5B-Instruct Q5_0 (75.2% ARC, ~21 t/s live, 1.17 GiB).
- **This study:** 102.4 GB/s class, system-RAM machines only (DDR5-6400 dual channel, shared memory, iGPU). dGPU-VRAM inference out of scope.

## Sessions

One session per working day (the session-40 addendum-19 ruling). A merged file carries its day's sessions verbatim; the link names the day's first session.

- [Session 1 — 2026-09-21 (project setup, roster revision, first llama-bench, quant ladder, ARC runs — sessions 1-13)](session-01.md)
- [Session 14 — 2026-09-22 (run3, study #1 retroactive re-run, quant-damage proposal, live-speed spot-check — sessions 14-16, 18b)](session-14.md)
- [Session 18 — 2026-09-23 (live-bench instrument, selection runs, FINAL RANKING, multiplatform port — sessions 18c-18v, 19-22)](session-18.md)
- [Session 23 — 2026-09-24 (thinking-model category, T14s roster, first thinking measurement, the patience anchor — sessions 23-26)](session-23.md)
- [Session 27 — 2026-09-26 (protocol v2/v2.1, the reader guarantee, roster runs, protocol v3.0 — sessions 27-29)](session-27.md)
- [Session 30 — 2026-09-27/28 (the sentinel certificate; protocol v3.1 — the stall rate)](session-30.md)
- [Session 31 — 2026-09-28 through 09-30 (the lineage sweep, the parameter ceiling, RULER, protocol v4 — sessions 31-33)](session-31.md)
- [Session 34 — 2026-09-30 (the tee WoW; protocol v4.3 re-climb; addenda 41-43 committed 10-01)](session-34.md)
- [Session 35 — 2026-10-01 (the Q4_K_M sweep: context-over-parameters confirmed; the merged best-of pages)](session-35.md)
- [Session 36 — 2026-10-02 (the four-probe ceiling chase graded; the FWE difficulty knob; the tournament)](session-36.md)
- [Session 37 — 2026-10-03 (the n=21 completion; medals; certify as type + range; closed 10-04)](session-37.md)
- [Session 38 — 2026-10-04 (the VT gold certification graded; the speed gate redesign; the combined cell; the UMA census)](session-38.md)
- [Session 39 — 2026-10-05 (registry hygiene: wow.md section 10; protocol.md catch-up addendum 140; the session-per-day audit)](session-39.md)
- [Session 40 — 2026-10-06 (the VT heap ruling closed; the code_edit review; the quality toolbox; the architecture audit; infra/ package; code_search; the certification redesign — n=20, equidistant medals, the ascending ladder, ruling B; the tier rename, the nameless run, the speed-dead climb stop; the leaked-spec retrieval bug fixed; Ctrl-C during a download stops the run; the root-json cleanup; the 10:57 residuals; the taxonomy ruling; the one-session-per-day restructure)](session-40.md)
- [Session 41 — 2026-10-07 (protocol v5.x: requirements as a test-linked contract; ctx = depth, the window tax ruled away; the 4k-window trio revived; the answered-rung terminal fix; the state-name 404 crash fix)](session-41.md)
- [Session 42 — 2026-10-07 (the reframe: v7 fixed-budget reach benchmark, pilot shipped — session 42)](session-42.md)
- [Session 43 — 2026-10-08 (v7 merged into full_benchmark; the greedy allocation; ARC/FWE retired; the crash rail; the corpus artifact; R-16..R-19)](session-43.md)
- [session-44](session-44.md) - the no-backward-compatibility ruling: R-21; v6 prototype deleted, HOME fallback and FWE readers removed
- [session-44](session-44.md) - addendum 110: R-22 state schema, one guarded loader
- [session-44](session-44.md) - addendum 111: reachability honesty fix (span-2048 at ctx-2048 crash)
- [session-44](session-44.md) - addendum 112: preflight + contracts + boundary tests against estimate-vs-server drift
- [session-44](session-44.md) - addendum 113: zero-score diagnosis; run_cell instrumented with found tallies + answer samples
- [session-44](session-44.md) - addendum 114: R-23 answers always logged; scoring explained
- [session-44](session-44.md) - addendum 115: R-24 push per evaluated cell
- [session-44](session-44.md) - addendum 116: R-25 - pytest out of the hook, weekly CI owns it; hook <= 5s
- [session-44](session-44.md) - addendum 117: R-25 compromise - deterministic pytest in the hook, hypothesis weekly
- [session-44](session-44.md) - addendum 118: R-26 - all agent edits through code_edit.py- [session-44](session-44.md) - addendum 119: R-25 - testmon hook: affected tests only per commit, full suite on push
- [session-44](session-44.md) - addendum 120: v7 10x easier - K 20 -> 2, 80 questions per cell
- [session-44](session-44.md) - addendum 121: 5-minute cell ceiling (budget stop + k-major ordering)
- [session-44](session-44.md) - addendum 122: questions match prefill time (k inverse in span, 45-question cell)
- [session-44](session-44.md) - addendum 123: 2k span dropped, K=1 flat, 35-question cell; 2048-window families (phi-1, phi-2, RWKV7) earn no cell
- [session-44](session-44.md) - addendum 124: wall-clock ceiling removed; question count is the runtime knob
- [session-44](session-44.md) - addendum 125: partial credit (found/(h+1)) + --force cleans results
- [session-44](session-44.md) - addendum 126: no heredocs even for driving code_edit - CLI gains --blocks-file and --write
- [session-44](session-44.md) - addendum 127: R-27 - check the latest completed push-regression verdict on every pull
