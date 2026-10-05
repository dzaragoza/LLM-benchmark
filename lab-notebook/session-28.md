# Session 28 - 2026-09-26 (protocol v2.1 roster: model selection anew; the memory shortcut)

Split from session-27.md (which had accumulated sessions 28-33 behind its own header) per the one-session-per-day audit, session 39 addendum 3. Content verbatim; addendum numbers unchanged. Addenda 33-36, committed 2026-09-26 (git: 3fa01ac, f4fae12, efd63ce, bdb308a).

### Session 28, addendum 33 — protocol v2.1 roster: model selection anew (the k=1 gate opens the door to the family champions)

**The author's request:** "Let's begin the model selection anew, this time: pick top popular 4 model families in the ollama list, where: (1) It is estimated the model will pass the speed gate in **quant 4** [corrected same-day from 'quants 4-8'], (2) is a non-thinking model or hybrid, so we can disable thinking for benchmark, (3) the model family has at least a peer reviewed paper, (4) pick the highest model in the family that can run." The author noted the new k=1 gate "might open the door to higher quant in the selected models or even bigger models" — confirmed below: at k=1 (5.0 w/s), size* ≈ 10.44 GiB (vs 2.79 GiB at floor 20), so every family's **highest runnable member** is now in reach, not just its smallest.

**Author rulings (this session, recorded before any measurement):**
- **Ruling A — one owner = one family.** llama3.1 and llama3.2 are ONE Meta family (reversing the study #1 precedent that treated them as separate rows). Only llama3.1:8b takes a slot; the llama3.2:3b row is absorbed.
- **Ruling B — rule 7 applies: latest generation, always.** "People want the latest and greatest, so that's what we measure." qwen3.5 supersedes qwen2.5; gemma4 supersedes gemma3. Superseded measured data stays in the results file as superseded data points.
- **Ruling C — borderline handling mooted.** The qwen2.5:14b / gemma3:12b quant-4 borderline-straddle question dissolved under rulings A+B: rule 7's replacements both pass quant 4 with margin.
- Notification request: the author wants an audible/notification ping when an answer is ready — no such tool exists in the sandbox catalog (checked, 93 tools); the chat reply landing IS the ping.

**Selection rules (v2.1 roster, pre-registered):** (1) Ollama library popularity walk-down (snapshot 2026-09-26); (2) distinct families — one slot per OWNER (ruling A); (3) non-thinking or hybrid (thinking disabled for the benchmark); (4) predicted to pass the speed gate at **quant 4** (Q4_K_M, the inclusion filter — the ladder walk itself still starts at Q8_0 and takes the first PASS); (5) first-party weights only — no third-party repos; (6) published paper (technical report / peer-reviewed); (7) latest generation supersedes older within family (ruling B); (8) highest runnable member within family ("can run" = file + KV + OS fits 32 GB RAM).

**The fitted law (Session 26):** `1/t = size_GiB/76.5 + 1/74` (BW_eff = 76.5 GiB/s = 80% of theoretical 102.4; t_inf = 74 t/s; R² 0.9996 within-model on the Qwen3.5-4B ladder; cross-family error ±15%, pooled R² = 0.16). Words/token band 0.65–0.80 for estimates (Qwen3.5-4B measured 0.680, the family value for qwen3.5:9b); at k=1 size* ≈ 10.44 GiB.

**Popularity walk-down (snapshot 2026-09-26), with quant-4 gate estimates** (Q4_K_M size; t/s = law ±15%; w/s band 0.65–0.80 w/t):

| # | ollama row | pulls | verdict |
|---|---|---|---|
| 1 | llama3.1 | 119.9M | **SELECT (Meta family): Llama-3.1-8B-Instruct** — highest runnable (70b = 40.05 GiB can't run); Q4_K_M 4.56 GiB → 13.7 t/s (11.6–15.7) → 7.5–12.6 w/s: passes |
| 2 | deepseek-r1 | 93.2M | excluded — thinking-only, no off switch (distills are always-reasoning) |
| 3 | nomic-embed-text | 87.2M | excluded — embedding model |
| 4 | llama3.2 | 84.4M | excluded — same owner as llama3.1 (ruling A); its 3b passes quant 4 easily but the Meta slot is taken by the more popular row, whose 8b is the higher model |
| 5 | qwen2.5 | 41.0M | superseded by qwen3.5 (rule 7, ruling B); qwen2.5:14b itself was borderline at quant 4 (8.38 GiB → 8.1 t/s → 4.5–7.5 w/s, straddling 5.0) |
| 6 | gemma3 | 40.7M | superseded by gemma4 (rule 7, ruling B); gemma3:12b itself was borderline (QAT Q4_0 7.54 GiB → 8.9 t/s → 4.9–8.2 w/s) |
| 7 | qwen3 | 38.1M | superseded by qwen3.5 (same Qwen family) |
| 8 | mistral | 33.7M | **SELECT (Mistral family): Mistral-7B-Instruct-v0.3** — the Mistral-brand family row (mistral-nemo 5.7M and ministral-3 1.5M are separate lower-ranked rows); Q4_K_M ~4.1 GiB → ~14.9 t/s → 9.7–11.9 w/s: passes |
| — | gemma2 / llama3 / qwen2.5-coder | 33.4M / 25.3M / 21.8M | excluded — superseded or same family |
| — | gemma4 | 25.8M | absorbed into the gemma3 slot by rule 7 (ruling B): **Gemma-4-12B** is the Google family's pick |
| — | qwen3.5 | 21.0M | absorbed into the qwen2.5 slot by rule 7 (ruling B): **Qwen3.5-9B** is the Qwen family's pick |
| — | phi3 / gpt-oss / smollm2 | 18.2M / 13.2M / 4.0M | not reached — slots full after four families |

**Selected roster (pre-registered before any measurement):**

| family | pick | HF source | paper | quant-4 estimate | predicted rung selection |
|---|---|---|---|---|---|
| Meta | Llama-3.1-8B-Instruct | safetensors, gated (license accepted) | The Llama 3 Herd of Models, arXiv 2407.21783 | 4.56 GiB → 13.7 t/s → 7.5–12.6 w/s | Q6_K (6.14 GiB → 10.7 t/s → 6.9–8.5 w/s); Q8_0 7.95 GiB → 8.5 t/s → 5.5–6.8 w/s borderline — walk may stop at Q8_0 or descend to Q6_K |
| Qwen | Qwen3.5-9B | safetensors only, self-quantize path | Qwen3.5-Omni Technical Report arXiv 2604.15804 (family-level, ruled sufficient in the thinking roster v4) | 6.14 GiB → 10.7 t/s → 6.9–8.5 w/s (w/t 0.680 measured family value → ~7.2 point) | Q6_K (6.9 GiB → 9.6 t/s → 6.3–7.7 w/s); Q8_0 8.9 GiB → 7.7 t/s → 5.0–6.2 w/s borderline-fails confident |
| Google | Gemma-4-12B-it | QAT Q4_0 GGUF first-party (google/gemma-4-12B-it-qat-q4_0-gguf, gated); other rungs convert from google/gemma-4-12B-it safetensors | Gemma 4 Technical Report, arXiv 2607.02770 | 7.08 GiB → 9.4 t/s → 6.1–7.5 w/s | Q5_K_M (8.1 GiB → 8.4 t/s → 5.4–6.7 w/s) or QAT Q4_0; Q6_K 9.2 GiB → 7.5 t/s → 4.9–6.0 w/s borderline; Q8_0 11.9 GiB → 5.9 t/s → 3.8–4.7 w/s fails |
| Mistral | Mistral-7B-Instruct-v0.3 | safetensors, public | Mistral 7B, arXiv 2310.06825 | ~4.1 GiB → ~14.9 t/s → 9.7–11.9 w/s | Q8_0 (7.2 GiB → 9.3 t/s → 6.0–7.4 w/s) or Q6_K (5.5 GiB → 11.7 t/s → 7.6–9.4 w/s) |

**Provenance paths (all verified this session):** Meta/Qwen3.5/Mistral take the safetensors → f16 → rung self-quantize path (pinned llama.cpp b10964); Meta gated (license accepted), Mistral public, Qwen3.5 public. Gemma-4: first-party QAT Q4_0 GGUF exists (gated); non-QAT rungs convert from safetensors. Note the Gemma-4 disabled-thinking behavior: with thinking off the 12b still emits the `<|channel>thought` wrapper with an EMPTY thought block (only E2B/E4B cannot disable) — the speed gate and ARC must handle the wrapper; first-turn dump check mandatory (the open `--chat-template-kwargs` server-flag issue #20409; per-request kwarg primary), as the standing flag requires for every hybrid.

**The commands (author's machine, pull-first):**

    git pull --ff-only
    python3 full_benchmark.py --no-thinking "meta-llama/Llama-3.1-8B-Instruct" "Qwen/Qwen3.5-9B" "google/gemma-4-12B-it-qat-q4_0-gguf=google/gemma-4-12B-it" "mistralai/Mistral-7B-Instruct-v0.3"

**Pre-registered predictions (recorded before any v2.1-roster measurement):**
1. **Llama-3.1-8B:** Q8_0 (7.95 GiB → law 8.5 t/s → 5.5–6.8 w/s) borderline at k=1 — prediction: FAILS the confident verdict, Q6_K PASSES; selected rung Q6_K, worst 9.1–12.3 t/s. Llama-family w/t unknown — a first measurable (predicted in 0.65–0.80).
2. **Qwen3.5-9B:** Q8_0 (8.9 GiB → 7.7 t/s → 5.0–6.2 w/s) borderline-fails confident; Q6_K PASSES at measured family w/t 0.680 → ~6.5 w/s point; selected rung Q6_K, worst 8.2–11.1 t/s.
3. **Gemma-4-12B:** Q8_0 FAILS (3.8–4.7 w/s); Q6_K borderline (4.9–6.0); Q5_K_M PASSES at point estimate (5.4–6.7); the walk treats the first-party QAT Q4_0 as the Q4 rung. Prediction: selected rung Q5_K_M, or QAT Q4_0 if Q5_K_M misses confident; worst at Q5_K_M 7.1–9.7 t/s.
4. **Mistral-7B-v0.3:** Q8_0 (6.0–7.4 w/s) passes at point but the band straddles 5.0; Q6_K passes with margin. Prediction: selected Q8_0 or Q6_K; worst at Q8_0 7.9–10.7 t/s.
5. **Law transfer (the study's cross-family claim):** each pick's measured worst t/s lands within ±15% of the law's prediction at its selected rung's file size — grading the cross-family transfer at 8–12B scale (law fitted at 4B scale).
6. **Words/token:** llama/mistral/gemma4 w/t land in 0.65–0.80; qwen3.5:9b w/t within ±10% of the measured 0.680 family value.
7. **Mode blindness (gemma4):** with thinking disabled, reasoning_chars = 0 on every turn despite the empty `<|channel>thought` wrapper — wrapper tokens are parse artifacts, not reasoning.
8. **No selection descends below Q4_K_M** (the quant-4 inclusion filter holds for every family).

### Session 28, addendum 34 — the early-fail optimization: a sub-reader-line turn aborts the rung in flight

**The author's ruling:** "In the speed gate, as soon as a conversation fails the check for the reader catching up with the output of the model, consider that quant fail. It is impossible to recover from that."

**The logic, verified against the instrument:** the verdict is a MIN — worst turn within a conversation, worst conversation within a rung, worst rep within a bench. A min is monotone: once one turn measures below the reader line, no later turn, conversation, or rep can raise the worst. The 2-sigma lenient branch could previously rescue such a rung (a sub-line worst with large scatter across conversations still PASSED) — that rescue is exactly the "recovery" the author rules impossible, and it is hereby RETIRED. The verdict is now strict: **PASS (confident) only if EVERY conversation's worst turn is at or above the reader line; any sub-line conversation fails the rung outright.** Sigma stays in the output as a reported diagnostic (the spread of conversation worsts), no longer a verdict input.

**The optimization (implemented in speed_gate.py, mock-tested end to end):**
- `run_conversation` takes `reader_wps`; the first turn measured below the line is flagged `below_reader_line: 1` in the dump, prints the abort reason, and breaks — remaining turns of that conversation are not generated.
- `bench_model` propagates the flag: remaining conversations and remaining reps are skipped ("early-fail - skipping the remaining N conversation(s) and any further reps"). The dump is still written and graded honestly — a partial dump with the flagged turn always FAILs the strict verdict.
- `bench`/`full_benchmark.py` pass the reader line down from the CLI (`--reader-wps`), so the pipeline's ladder walk gets the same early abort; a doomed rung now costs one conversation instead of five.
- Turn-level check (not conversation-level): the conversation's worst is itself a min over its turns, so the abort fires mid-conversation at the offending turn — the earliest possible point.
- Honest scope note: the check applies to turns with a measured `server_wps` (v2.1 turns); empty answers have no w/s and cannot early-fail (they carry the existing empty-answer warning instead).

**Mock-server verification (three cases):** (1) healthy 10 w/s run — no flag, all 9 turns, PASS (confident); (2) a dip to 4 w/s at conv 2 turn 2 — the turn is flagged, the conversation aborts at turn 2, conv 3 is skipped, verdict FAIL; (3) the retired rescue — a 4.5 w/s worst with large conversation scatter now FAILs (previously PASS within 2-sigma). The test caught one mock artifact worth recording: an instant-responding mock produces a negative generation span (wall < prompt_ms) and therefore no measurable w/s — the real server never does, and the check correctly skips unmeasurable turns rather than false-failing.

**Consequences, recorded:**
1. **Runtime:** a failing rung costs ~1 conversation (~2 minutes at 12B scale) instead of 5 — the ladder walk's dominant cost was the doomed rungs (the predicted-descending ladders of addendum 33: llama3.1-8b and gemma4-12b are expected to fail Q8_0 first, qwen3.5-9b likewise). Estimated saving per family: ~8-15 minutes of bench time per failed rung.
2. **Strictness:** the ladder's first PASS is now the first rung whose EVERY conversation clears the line — the addendum-33 predicted-rung tables are unchanged (their bands assumed the strict reading), but borderline bands (llama3.1-8b Q8_0 at 5.5-6.8 w/s) may now select one rung lower than a lenient reading would have.
3. **Prediction grading unaffected:** predictions are compared against the measured worst of the SELECTED rung; early-fail only shortens the path to it.
4. The dumps of early-failed rungs are partial by design (flagged) — the per-rung dump record keeps the flag, so post-hoc analyses (lag_analyze, collision simulation) can distinguish "failed at conv 2 turn 2" from "ran all five and failed on the worst".

**Pre-registered expectation for the study #3 run:** with the early-fail in place, each predicted-failing top rung (llama3.1-8b Q8_0, qwen3.5-9b Q8_0, gemma4-12b Q8_0/Q6_K) aborts within its first or second conversation; if any of them instead runs all five conversations, that itself is a graded surprise (the law's ±15% band is generous in the wrong direction).

### Session 28, addendum 35 — the memory shortcut: rungs that cannot fit in RAM are skipped before download

**The trigger (author's catch, from the crashed first study #3 run):** "We forgot to take into account the amount of memory available in the system, that's another shortcut." The first pipeline run also exposed a second bug: the Llama-3.1-8B safetensors phase downloaded **32.1 GB** where ~16 GB of safetensors suffices - `snapshot_download` pulled the whole repo, including Meta's `original/*.pth` duplicates - and the reconstruction died with a writer-channel error (SIGSEGV in fish) at 63%.

**Two fixes, both verified with stubbed-hub tests:**

1. **The memory shortcut (the author's ruling):** before any network traffic, `hf_download.acquire()` now estimates the rung's size and compares against usable system RAM.
   - Size estimate, no download: exact when the repo ships the rung GGUF (HF tree metadata via `HfApi.list_repo_tree`); ratio-scaled from the fp16/safetensors total otherwise (RUNG_BITS: Q8_0 8.5, Q6_K 6.6, Q5_K_M 5.7, Q4_K_M 4.8, Q4_0 4.5, Q3_K_M 3.9, Q2_K 3.4 bits/weight; rung ≈ fp16_giB × bits/16; `original/` excluded from the source total).
   - RAM: `/proc/meminfo` (Linux), `sysctl hw.memsize` (macOS), `GlobalMemoryStatusEx` (Windows). Usable = total − 4 GiB reserve (OS + KV at the 4096 reference depth; the T14s: 32 − 4 = 28 GiB).
   - Infeasible rungs return plan `"infeasible: exceeds system RAM"`; the orchestrator marks the rung `FAIL (infeasible: exceeds system RAM)` and walks on down the ladder. No download, no conversion, no bench.
   - Never a false skip: when either estimate is undetectable, the rung proceeds as before. A disk-space warning (rung × 2 worst case) prints but does not block.
   - Tested: a 70B-class repo (150 GiB safetensors → Q8_0 est. 79.7 GiB) on a forced-32 GiB machine → skipped, zero download calls; an exact-size 40 GiB Q8_0 GGUF → skipped; a feasible 8 GiB-source repo → proceeds to download.

2. **Scoped snapshot download (the crash's cause):** `snapshot_download` now passes `allow_patterns = ["*.safetensors", "*.json", "*.txt", "tokenizer.model", "tokenizer.model.v3"]` - the conversion path needs the safetensors and tokenizer/config files only. Meta's `original/*.pth` (an entire second copy of the weights in PyTorch format), vision-tower extras and anything else no longer download: the Llama-3.1-8B source phase drops from ~32 GB to ~15 GB, halving the download and removing the writer-channel crash trigger (the background writer was juggling 17 files including a 16 GB .pth).

**One ladder consequence surfaced by the pending gemma-4 run (fixed in the same commit):** the default ladder had no Q4_0 rung, so the first-party QAT Q4_0 GGUF (addendum 33's stated gemma-4 path) would never have been reached - the pipeline would have self-quantized Q4_K_M from safetensors and skipped the QAT file entirely. The default ladder is now `[Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q4_0, Q3_K_M, Q2_K]`: self-quantized K-quants stay preferred, with the first-party QAT Q4_0 as the same-bit-width fallback (verified: `find_rung_file` matches `m-Q4_0.gguf` for rung Q4_0 and does not cross-match Q4_K_M/Q4_K_S; the gemma-4 QAT repo ships a single 6.98 GB file `gemma-4-12b-it-qat-q4_0.gguf`, not sharded, plus an mmproj that is correctly excluded).

**Also recorded: the crashed run left no state damage** - the phase-1 failure is idempotent (the state file had already recorded the partial phases), so the rerun resumes cleanly. The author's download can be rerun as-is after `git pull --ff-only`.

**The revised run command (unchanged for the author; the fixes are internal):**

    git pull --ff-only
    python3 full_benchmark.py --no-thinking "meta-llama/Llama-3.1-8B-Instruct" "Qwen/Qwen3.5-9B" "google/gemma-4-12B-it-qat-q4_0-gguf=google/gemma-4-12B-it" "mistralai/Mistral-7B-Instruct-v0.3"

### Session 28, addendum 36 — the memory report: llama.cpp's own accounting + the kernel's peak RSS

**The author's request:** "can we get information from llama-cpp about memory usage? that would be good to report too."

**Two sources, one authoritative number.** llama.cpp reports its own startup accounting (model size, KV cache, compute/graph buffers) in the server banner - which the pipeline discarded to /dev/null until now. The banner's wording moves between builds, so the parser is best-effort (structured keys where recognizable: kv_cache_gib, cpu_buffers_gib, graph_overhead_gib; plus the raw size-bearing banner lines kept verbatim, last 40). The AUTHORITATIVE number is the kernel's peak resident set size (VmHWM, /proc/<pid>/status) read at server teardown - everything the launch took: weights + KV cache + compute buffers + runtime overhead. It is the honest "can it run here" quantity, and the validation target for addendum 35's size estimates (the estimate's usable-RAM reserve can now be graded against the measured peak per rung).

**Implementation:**
- `llama_server.start_server(log_path=...)`: the server's stdout/stderr is captured to `<model>.server.log` (truncated per launch) instead of /dev/null.
- `llama_server.peak_rss_gib(proc)`: VmHWM in GiB, read BEFORE teardown terminates the process (Linux /proc only; None elsewhere - the report is skipped, never faked).
- `llama_server.parse_memory_log(log_path)`: best-effort banner parse (structured keys + verbatim lines).
- `speed_gate.bench_model`: reads peak RSS in the teardown finally-block, prints it per rep ("memory: peak RSS X GiB"), summarizes across reps ("MEMORY: peak RSS X GiB ... N GiB beyond the file (KV + buffers + runtime)"), and returns the reports; `speed_gate.bench` persists them to a sidecar `<dump>.mem.json` (the dump's turn-list format and the resume machinery untouched); on dump reuse the sidecar's peak is re-printed. `full_benchmark.py` phase 4 prints "memory: peak RSS X GiB" per rung from the sidecar.
- `depth_probe.py`: reports peak RSS per depth (the KV term is IN the number at depth D - the depth-conditioned memory cost).

**Tested with a mock server + a real sleeping process:** banner parse (512 MiB KV -> 0.5 GiB, missing file -> empty), VmHWM read on a live PID, end-to-end bench_model -> report -> sidecar write -> reuse print. The mock's ~0 GiB peaks are the sleep process's honest RSS, not a bug; a real launch reports real numbers.

**The report's role in the study:** the machine's memory ceiling enters the data. Each rung's dump now carries the measured peak RSS alongside its worst w/s - so the study reports not just "passes the reader line at Q6_K" but "passes at Q6_K taking X GiB peak", and the 32 GB ceiling's actual headroom (28 GiB usable estimate vs measured peak) is a graded column, validating addendum 35's 4 GiB reserve assumption rung by rung.

**Pre-registered expectation:** llama.cpp peak RSS ~ file size + 1.5-2.5 GiB (KV at 4096 + Vulkan compute buffers + runtime) for the 7-12B picks; if the measured "beyond the file" exceeds 3 GiB on any pick, the 4 GiB reserve in the memory shortcut was too tight and gets re-fitted from these very numbers.
