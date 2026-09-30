## Session 3 prep — tooling commands (pre-registered, not yet run)

**llama.cpp pinned to study #1's build (b10964, commit b29c606e2):**

```bash
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
git checkout b29c606e2
# verify: git log -1 --oneline  → must show b29c606e2
```

**Memory-copy baseline (new in this study — not done in study #1):**

- *Why:* establish the machine's real achievable bandwidth before any LLM work; grade prediction 1 (~68 GiB/s effective) against a measured ceiling, not the datasheet.
- *CPU side:* STREAM benchmark (classic, source-available, compiles on both Windows/MSVC and Linux/gcc). `Stream_Triad` is the number to record.
- *GPU side:* `clpeak` (OpenCL) for global-memory bandwidth. Caveat on record: llama.cpp uses Vulkan (RADV/Mesa on Linux, vendor driver on Windows), while clpeak uses OpenCL — driver stacks differ, so GPU-side number is indicative, not authoritative. Also record `vulkaninfo --summary` (Linux) to pin the Vulkan driver/Mesa version — the OS/driver difference vs study #1 is a documented variable, not noise.

Commands in the session log once run; results table to be added (CPU triad GB/s, GPU global BW GB/s, ratio to 102.4 GB/s peak).

## Session 3 — 2026-09-21 (memory baseline: clpeak run, llama.cpp binaries pinned)

**llama.cpp, pinned to study #1's build b10964 (commit b29c606, verified against the GitHub release page):**
- CPU-only Linux prebuilt: `llama-b10964-bin-ubuntu-x64.tar.gz`
- Vulkan Linux prebuilt: `llama-b10964-bin-ubuntu-vulkan-x64.tar.gz`
- Both from https://github.com/ggml-org/llama.cpp/releases/tag/b10964 — **asset names verified via GitHub API after an initial error.**
- **Correction (this study's first):** the first command given used `.zip` filenames — Linux assets are `.tar.gz`. The earlier "verification" treated a resolving redirect as a working link; the user's 404s exposed it. Lesson recorded: verify downloads against the release's asset manifest (API), not by opening a guessed URL. Methodological note: same failure class as study #1's Session-23 protocol error — plausible-looking commands unchecked against reality.
- Note on record: prebuilt = Ubuntu-linked binaries; on openSUSE they may need `libgomp`/Vulkan loader present — verify `ldd` at install time. If dependency friction appears, fall back to source build at the same commit.
- Windows machine currently unavailable; Windows baseline deferred (planned: same release's `llama-b10964-bin-win-cpu-x64.zip` / `llama-b10964-bin-win-vulkan-x64.zip` + STREAM).

**STREAM on openSUSE:** package expected in OBS `benchmark` repo (`zypper addrepo .../benchmark/openSUSE_Slowroll/benchmark.repo; zypper install stream`); package name to be confirmed with `zypper se stream` at install time. Fallback: compile from source (same flags as planned for Windows — preferable anyway for cross-machine provenance).

**STREAM — decision: build from source on both machines (matching provenance).** Decided 2026-09-21. Reference source: the canonical `stream.c` from the STREAM benchmark home page (Virginia CS, John McCalpin's benchmark) — fetch, don't transcribe. Build flags pinned:

- Linux: `gcc -O3 -mcmodel=large -fopenmp -DSTREAM_ARRAY_SIZE=400000000 -DNTIMES=20 stream.c -o stream`
- Windows (later): `cl -O2 -openmp -DSTREAM_ARRAY_SIZE=400000000 -DNTIMES=20 stream.c` (Native Tools Command Prompt)
- `-DSTREAM_ARRAY_SIZE=400000000` → 3 GB/array × 4 arrays = 12 GB working set, far beyond the 16 MB L3 — measures DRAM, not cache. Machine has 32 GB, so headroom is fine.
- Record: full output of every kernel (Copy/Scale/Add/Triad), plus `OMP_NUM_THREADS` used (default = all 16 threads) and CPU governor/power state if settable. On a laptop, consider one run on AC power with performance governor — thermal envelope note from Session 2 applies; log battery/AC status with each run.

**STREAM results (run 2026-09-21, T14s, source-built, 16 threads, 8.9 GiB working set):**

| Kernel | Best rate (GB/s) |
|---|---|
| Copy | 60,297 |
| Scale | 34,873 |
| Add | 38,327 |
| Triad | 38,187 |

**Headline CPU numbers: Triad 38.2 GB/s, Copy 60.3 GB/s.**

**Thread-count check (run 2026-09-22, author-initiated):** hypothesis — the 16-thread (SMT) default depressed CPU BW. Re-run with `OMP_NUM_THREADS=8`, same binary/arrays/protocol: **Copy 61.5 (+1.9%), Scale 35.0, Add 37.8, Triad 38.5 GB/s (+0.8%).** Verdict: within ~2% on every kernel — **SMT was not the bottleneck; the CPU STREAM ceiling is per-core load/store throughput-bound.** No study conclusion changes (CPU ~60–65% of peak vs iGPU ~80% stands; instrument-category lesson stands; headline numbers use llama-bench implied BW, untouched). Session-3 open note ("consider 16-thread secondary check for CPU runs") now closed: tested, no effect.

**Analysis (pre-registered prediction check — prediction 1, CPU side):**
- STREAM counts read+write traffic: Triad = 2 reads + 1 write per element → 38.2 GB/s reported ≈ 38.2 GB/s of actual DRAM traffic... but the conventional comparison is: reported Copy (read+write, 2 streams) 60.3 GB/s, reported Triad (3 streams) 38.2 GB/s. Either way, the CPU cannot saturate the 102.4 GB/s bus.
- clpeak's CPU DRAM read: 67.2 GB/s; copy: 35.9; triad: 37.7 — consistent with STREAM (independent instruments agree, ~±5%). Good instrument cross-validation on record.
- **The key observation: CPU-side streaming ceiling is ~60–67 GB/s (≈60–65% of 102.4 peak), while the iGPU's clpeak global BW was ~82 GB/s (80%).** The 780M is substantially better at saturating LPDDR5X than the Zen 4 cores are — consistent with study #1's finding that the iGPU wins prefill, and it foreshadows that the CPU-vs-Vulkan generation comparison may flip harder than in study #1 (where CPU *won* generation).
- Prediction 1 (68 GiB/s effective for LLMs on this class) sits *between* the CPU ceiling (~60–67) and the GPU ceiling (~82). If llama.cpp Vulkan achieves its usual 80–85% of the GPU's raw ceiling, effective ≈ 65–70 GiB/s → prediction 1 still plausible, tight against the upper edge. First llama-bench number grades it.

**clpeak run (author, on T14s, openSUSE, RADV PHOENIX Mesa 26.2.1):**

| Measurement | Value | Note |
|---|---|---|
| GPU global memory BW | **81.0–82.3 GB/s** | 79–80% of 102.4 GB/s theoretical |
| GPU coopmat fp16 (16×16×16) | 12.98 TFLOPS | **matrix support confirmed** — prediction 4 is testable |
| GPU coopmat int8 | 12.99 TOPS | quantized matrix path available |
| GPU int8 dot-product | ~11.0 TOPS | shader-level int8 |
| CPU DRAM read | 67.2 GB/s | CPU side of the bus |
| CPU DRAM copy/triad | 35.9 / 37.7 GB/s | clpeak counts read+write traffic; read is the streaming-comparable number |
| Reported VRAM | 10,922 MB | ~half of 32 GB system RAM as UMA carve-out — the study #1 "reservation" lesson applies here too; document this state and keep it fixed |
| CPU AVX-512 | confirmed (5134 MHz) | also VNNI int8: 4.07 TOPS MT |
| Vulkan driver | RADV PHOENIX, Mesa 26.2.1, Vulkan 1.4.354 | documented stack difference vs study #1 (Windows vendor driver) |
| OpenCL | none found | clpeak ran via its Vulkan backend |

**Preliminary read on predictions (not yet graded — no llama.cpp data):**
- Prediction 1 said ~68 GiB/s *effective* LLM bandwidth (66% of peak). The GPU's raw streaming ceiling measures ~82 GB/s (80% of peak). If llama.cpp achieves its usual 80–85% of raw copy bandwidth, effective lands ~65–70 GiB/s — **prediction 1 currently looks plausible**, possibly slightly conservative. Grade pending llama-bench.
- Study #1 comparison: Vega machine's effective 34 GiB/s vs 51.2 peak (66%); this machine's raw GPU already at 80%. The higher efficiency at the higher tier is itself interesting if it holds.
- The UMA VRAM carve-out (~10.7 GB) is this study's analogue of study #1's 2 GB BIOS reservation confusion — pin it on record *now* so there's no Session-23-style correction later.

**Open items:**
- STREAM on CPU (clpeak's CPU DRAM numbers suffice for now, but classic STREAM triad on both machines would give the cross-study retrospective baseline) — optional.
- Install the two llama.cpp prebuilt bundles; `ldd` check; smoke-test `llama-bench` on one small model, Vulkan device should report coopmat/int8 support.
- Model roster decision.

### Session 3 addendum 2 — model selection for the 3B smoke test (2026-09-21)

Method: top-8 Ollama families by pulls (llama3.1 119.7M, deepseek-r1 93M, llama3.2 84M, qwen2.5 40.7M, gemma3 40.6M, qwen3 37.6M, mistral 33.6M, gemma2 33M; embeddings excluded), filtered for: 3B-class member, research paper available, non-thinking (strict-ARC protocol), fits ~2.2–2.5 GiB Q5 budget.

**Selected: Qwen2.5-3B-Instruct** (paper arXiv:2412.15115).
- Exact match to prediction 6's pre-registered profile (2024-gen non-thinking instruct, 3B, named as the example).
- Cross-study continuity: same family as study #1's champion (Qwen2.5-1.5B Q5_0, 75.2% ARC) → paired comparison across bandwidth tiers.
- Known cost: Qwen family speed penalty (~10%, large vocab) — budget adjusted to ~2.4 GiB for this family.
- Runner-up: Llama3.2-3B (model card + Llama 3 paper arXiv:2407.21783) — family-independent check if Qwen disappoints. Phi3-3.8B noted (Q5 ≈ 2.8 GiB, budget edge).

**First bench plan:** smoke test with official Qwen2.5-3B-Instruct GGUF Q4_K_M (~1.9 GiB) to grade prediction 1 (speed formula); Q5_0 for the accuracy run to be self-quantized from official safetensors (pinned converter) as in study #1 — official repo expected to ship Q4_K_M/Q8_0 only.

**Tooling note (author, 2026-09-21):** `llama-bench` supports `-hf` to pull models directly from Hugging Face at bench time — no separate download step. Author can verify any HF model/repo availability with HF tooling on request.

**Bench commands (final form):**

```bash
# Vulkan — check startup log says RADV PHOENIX / AMD, not llvmpipe
./llama-bench -hf Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M -t 8 -p 512 -n 128 -r 3 -ngl 99

# CPU (same model, no GPU offload, both thread counts)
./llama-bench -hf Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M -t 8  -p 512 -n 128 -r 3 -ngl 0
./llama-bench -hf Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M -t 16 -p 512 -n 128 -r 3 -ngl 0
```

**Protocol deviation from study #1 (documented, deliberate):** study #1 excluded prompt processing (`-p 0`) after its Session-23 correction. This study measures **pp512 alongside tg128**. Rationale: (1) study #1's own §1.3 argues time-to-first-token dominates interactive feel; (2) the iGPU's matrix cores should show up in prefill far more than in generation — pp is where RDNA 3 vs Vega should diverge most; (3) study #1 captured pp128/pp2048 for its Vulkan-vs-CPU comparison, so pp strengthens cross-study comparability. Both protocols documented; deviation auditable.

**pp512 pre-registered predictions (before any measurement):**
- **Vulkan pp512: 450–700 t/s** (point ~550) for Qwen2.5-3B Q4_K_M. Study #1's Vega did 322 t/s on the 1.5B; clpeak shows ~13 TFLOPS coopmat fp16 (vs Vega's shader-only fp16), but the 3B model roughly doubles FLOPs/token. Wide band is honest — depends on how well llama.cpp b10964 uses coopmat via RADV.
- **CPU pp512: 250–400 t/s** at `-t 8`; `-t 16` within ±20% of `-t 8` (compute-bound phases may scale with SMT, memory-bound ones won't).
- **Vulkan prefill advantage: ≥1.5× CPU** (study #1: 2×). Matrix cores should hold the prefill crown against AVX-512/VNNI.

(`-hf repo:tag` resolves the quant by filename pattern; first-party Qwen repo per the provenance rule. Note: `-t 8` was study #1's protocol on a 8-core CPU; the 7840U has 8 cores/16 threads so the flag carries over unchanged — but for the CPU run, consider also `-t 16` as a secondary check since SMT may matter for memory streaming.)

**Unnumbered prediction 7 (on record before the run): Vulkan wins generation on this machine.** Study #1: CPU beat Vulkan by 31% on generation (Vega era, no matrix cores, CPU had full bus access). This machine: CPU streaming ceiling ~60–67 GB/s (STREAM/clpeak) vs iGPU ~82 GB/s (clpeak) — the iGPU is now the better memory-streaming engine. Prediction: Vulkan tg128 > CPU tg128 for Qwen2.5-3B Q4_K_M. Grade with the paired run above.
