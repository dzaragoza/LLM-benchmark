# Session 38 - 2026-10-03

Opened 2026-10-03 (the calendar says 2026-10-04 by now, but the working
day is the 3rd's continuation - the VT gold run launched last local
night is STILL RUNNING on the author's machine, currently around the
128k rung). Carrying over from session 37 (closed, 82 addenda):

- The VT gold certification (addendum 80) is mid-run: 2 sigma, 5/5
  pass bar, rungs 4,096-262,144, full 9-family roster, seeds = run
  numbers, cells in the separate certify_vt namespace.
- The morning grading ladder is REGISTERED (addendum 81): 5/5 at 2s;
  else the largest x/5 at 2s re-graded from the stored partials; else
  silver at the same ladder. Zero re-measurement either way.
- The FWE medal bar ruling landed at session close: the sites show
  ONLY 2-sigma at the 3/3 perfect-retrieval bar (Jamba2 gold from
  32,768 up, the 0.8B gold at 4,096-16,384 - the tradeoff readable
  directly in the runs table).
- code_edit hardening (addendum 82): replace_verified takes per-pair
  counts; the working rule is replace_verified for any non-trivial
  edit, never raw open/write.

## Addendum 1 - session 38 open, the VT run's state mid-flight

The VT run is not to be disturbed: it writes its cells to
state/benchmark-state-tournament.json (certify_vt namespace) as it
goes, one save per cell, so an interruption loses nothing measured.
No analysis of the partial results happens until the run completes -
the grading ladder (session 37 addendum 81) is applied to the COMPLETE
cell map, in order, with no peeking-driven bar shopping.

## Addendum 2 (registered pre-measurement, 2026-10-04): the speed gate REDESIGNED - stalls per conversation, the FWE/VT shape

The author's clean-slate ruling: the old speed gate does not behave like
the other instruments and is REDESIGNED from scratch. Everything
protocol-v3.x (stall RATE <= 5%, n=50 corpus conversations, the
threshold = reader_wps - 2*sigma budget) is RETIRED from the
certification path. The corpus is now DEFINED as its first 21
conversations (the 50 was itself an arbitrary cut from a much larger
pool; the author's ruling 2026-10-04).

DESIGN (property-derived, no arbitrary thresholds):
- Measurement unit: the TURN. A turn stalls iff the 5 w/s reader
  (Brysbaert 2019, the external anchor) ever hits the wall on that
  turn's arrival stream - the binary event, unchanged.
- Run unit / cell: (model, rung, conversation r), r = 1..21,
  deterministic corpus order, seed = r. Same cell model as FWE/VT:
  never re-measured, resumable.
- k = 5: the MEDIAN number of turns in the 21-conversation corpus
  ([4,4,5,4,5,8,5,5,7,5,5,5,4,5,6,5,4,4,6,6,5], 107 turns). k is a
  property of the corpus, like FWE's 3 words and VT's 5 names.
- Per-cell record: stalls/k - the count of stalled turns in that
  conversation (0..len). Stored per cell, re-gradable at any bar
  forever (the exact analogue of x/3 and x/5).
- Bars, the same ladder as FWE/VT: gold candidate = 0 stalls per
  conversation (the perfect record); fallback = at most x stalls,
  chosen AFTER measurement from the stored records.
- n = 21 cells, gold = 2 sigma (Wilson lower bound >= 0.5), the same
  sequential controller: early accept (11/11 at 2s), early reject
  (mathematically dead), first accepted candidate answers the rung.
- Cells live in a separate certify_speed namespace. The FWE and VT
  evidence is never touched.

PREDICTIONS (falsifiable, stated before measurement):
- The certified region stalls rarely (the ladder's v3.1 runs showed 0
  wall-fail turns at every passing rung) -> gold candidates accept
  fast, at or near 11/11.
- The interesting cells are the CEILING rungs (worst w/s in
  [5, 7.5)) where the old instrument showed near-misses; the
  per-cell stall counts localize exactly which conversation/turn
  stalls - deterministic, reproducible.

## Addendum 3 (registered 2026-10-04): the COMBINED cell - speed, FWE and VT in one controller

The author's ruling: the three instruments now certify TOGETHER. A cell is
(model, rung, run) carrying THREE independent measurements - speed, FWE,
VT. A cell's task is measured only if missing (never twice); the three
tasks keep their own pass/fail tallies and their own accept/dead verdicts.

CONTROLLER:
- Candidate certifies the rung when ALL THREE tasks accept (each at the
  level's bar, the same sequential math as before).
- Candidate dies when ANY ONE task is dead - the next candidate is picked
  up. The other tasks' perfect runs do not rescue it.
- The cell run is shared: the lowest unmeasured run is picked across the
  three tasks, and only that cell's missing tasks are measured.

MEDALS (re-graded from the stored records, never re-measured):
- gold = all three tasks at their gold bars
  (speed 0 stalls, FWE 3/3, VT 5/5)
- silver = at least silver in all three
  (speed <=1 stall, FWE 2/3, VT 4/5)
- bronze = any pass at all (any task at its silver bar or better)

CLI: --task all with --certify dispatches to certify_rung_combined; the
per-task namespaces (certify, certify_vt, certify_speed) are untouched -
the single-task controllers remain available.

## Addendum 4 (registered 2026-10-04): the UMA carveout census - what smaps cannot see

The author's correction: the rig runs the VULKAN build with -ngl 99 on
the T14s APU (an iGPU, UMA design), NOT CPU-only as the assistant had
asserted. Two consequences:

1. The T14s BIOS reserves 2048 MiB as a dedicated UMA frame buffer.
   Pages allocated inside that carveout belong to the GPU and NEVER
   appear in the host process's /proc/<pid>/smaps - the addendum-23
   census undercounts exactly the offloaded fraction when the driver
   spills into the carveout.
2. The GPU table wants an accurate GPU-side number, not a proxy.

INSTRUMENT (amdgpu sysfs, /sys/class/drm/card*/device/):
- mem_info_vram_used: the carveout usage (hidden from smaps; sampled
  as a machine-wide DELTA across the launch window, so the compositor
  and other processes are excluded; negative deltas clamp to 0)
- mem_info_gtt_used: shared GTT usage (already resident in system RAM
  and visible to smaps - recorded for the GPU table, NOT added again)
- mem_info_vram_total: the BIOS reservation itself (2 GiB on the T14s)

CENSUS UNION (mapped_plus_gpu_gib): the smaps resident number stays
untouched and comparable to all pre-addendum-4 records; the carveout
delta lands in its own keys (gpu_vram_delta_gib, gpu_gtt_delta_gib,
carveout_hidden) and footprint_gib = resident + carveout is the new
honest grand total. Wired into all three census sites: fwe_pass,
vt_pass and the speed gate's bench_model. On non-AMD boxes the
interface returns None and the census degrades gracefully to the
addendum-23 behavior.

LIMITATION, on record: the delta is machine-wide, not per-process -
if another GPU client ran DURING a cell, its usage contaminates the
delta. The overnight runs are solo on the box, so this is acceptable;
the carveout_hidden flag (delta > 0.05 GiB) marks every affected cell.

## Addendum 5 (registered 2026-10-04): the third witness - llama's own accounting in the log

The author's ruling: capture llama.cpp's own memory accounting from the
start (we should have done this from the beginning). All three launch
sites (fwe_pass, vt_pass, speed bench_model) now pass -lv 5 so the
load-time tensor/KV/buffer banner lines land in the server log, where
addendum-36's parse_memory_log already extracts kv_cache_gib,
cpu_buffers_gib, graph_overhead_gib + raw banner_lines.

Per cell we now have THREE independent memory witnesses:
1. smaps census (resident, file/anon split; addendum 23)
2. amdgpu sysfs delta (the carveout, GTT; addendum 4)
3. llama's own load accounting (per-device buffer sizes; addendum 5)

VERIFICATION REQUIRED (first cell of the next run): check the server
log for the load_tensors/buffer-size lines. Verbosity mappings vary
across builds - if the lines are absent at -lv 5, try -lv 1 or 0
(some builds invert the scale; the banner guard reads n_ctx from the
log, so any regression there is caught by the gate itself).

Addendum 5, refinement 1: the -lv flag is single-sourced in
llama_server.py (LOG_VERBOSITY_ARGS) and applied inside start_server -
the author's ruling over the assistant's triplicated flags (every
launch site invents its own extras; the shared ones live in the
launcher). All three call sites build their own extra_args without
verbosity; start_server injects it before them.

Addendum 5, verification complete (2026-10-04, the author's manual
launch): -lv 5 prints the full accounting on the b10964-gpu build.
Confirmed lines (Qwen3.5-0.8B Q8_0, -ngl 99):
- the device enumeration: Vulkan0 = RADV PHOENIX 780M reporting a
  16383 MiB heap (the shared GTT view, NOT the 2 GiB carveout - the
  sysfs delta remains the carveout authority)
- load_tensors: offloaded 26/26 layers to GPU (full offload, from the
  log itself)
- Vulkan0 model buffer size = 763.78 MiB (llama's own GPU-side claim)
- Vulkan_Host model buffer size = 257.66 MiB (~25% of the model
  stays host-side even at -ngl 99 - a finding for the GPU table)
parse_memory_log (addendum 36) extended: vulkan_buffers_gib and
host_buffers_gib extracted as structured keys alongside kv_cache_gib;
regression test added against the author's real log lines.

Addendum 6: ARC joins the combined controller as the 4th task (the
author's ruling 2026-10-04: "deterministic questions, k=5 questions,
n=21, 2sigma confidence on answering 5/5; the only difference is
that arc doesn't care about context, so a single run at ctx 4k; the
medals now depend on 4 models").Design:- ARC_CELL_K = 5; cell = (family, run) with a 0..5 graded record
  (correct of 5), pass at gold = 5/5, bar at silver = 4/5.- arc_cell_questions(run): the full ARC-Challenge test split
  (ARC_NUM_DEFAULT = 1172) shuffled once with the study seed
  20260923; cell r takes questions 5*(r-1)..5*r. Deterministic - the
  same question never repeats across the n=21 cells and any cell is
  re-derivable from the seed alone.- Rung-independent: unlike speed/FWE/VT (per-rung namespaces), ARC
  is measured ONCE per family at ctx 4096 (a single llama-server
  launch per cell, -t 8 -c 4096 -ngl 99, raw /v1/completions,
  max_tokens=1, temperature=0, top-20 logprobs, letter scoring - the
  retired arc_eval.py protocol recovered from git history). Stored
  flat in certify_arc {run: correct}; inherited at every rung - a
  rung never re-measures it.- Bars: TASK_GOLD_BARS["arc"] = 5, TASK_SILVER_BARS["arc"] = 4. Gold
  = all four tasks at gold; silver = at least silver in all four;
  bronze = any pass at all. combined_medal re-grades from records
  (arc_cells is depth-free).- Bug found and fixed while integrating: _task_store mapped vt/speed
  to their namespaces but NOT arc, so ARC records silently landed in
  certify (the FWE namespace) under a rung key - arc_cells saw
  nothing and the medal returned None. Fixed with a regression test
  (test_arc_rung_independence_and_namespace).

Addendum 7: the medals are pure confidence tiers (the author's
refinement, 2026-10-05): "we will continue with the three medal
system, it is very clear to explain results. We can change the
criteria of what a pass or fail means tuning the test difficulty,
but the medals stay the same."- GOLD: 2 sigma confidence in EVERY test.
- SILVER: at least 1 sigma in EVERY test.
- BRONZE: at least one pass in EVERY test (it can work, but expect
  misses).
- Otherwise: no medal.The pass bars (the difficulty knob) now live in TASK_PASS_BARS
(speed 0 stalls, fwe 3 words, vt 5 names, arc 5 correct) and are
DECORATED from the medal logic: tuning a test's difficulty changes
what a pass means, never what a medal means. The old
TASK_GOLD_BARS/TASK_SILVER_BARS (bar-based medals, where silver FWE
was 2/3) are retired - a stored graded record is re-gradable at any
bar anyway, so difficulty changes cost nothing (no re-measurement,
ever).

Addendum 8: two rulings from the interrupted-run review (2026-10-05).1. ARC bar calibrated to 4/5 (TASK_PASS_BARS). The first combined
   run's records showed 5/5 was the hardest bar in the study - the
   best family (Jamba2) passed 3/7 cells, most pass at 4/5 - while
   4/5 keeps the separation (gemma, Llama-3.2-1B and MiniCPM5-1B
   stay dead). The author's design principle confirmed: k is the
   difficulty knob, the medals (2s/1s/one-pass in every test,
   addendum 7) never move. Every stored record re-grades free.
   The speed-gate prediction registered: 0 stalls passes until
   256k, where the author predicts NO model clears it (the one
   historical stall datum was n=1).
2. SIGINT handler (session 38, addendum 8): Ctrl-C now stops
   cleanly - pkill llama-server, tee uninstall, git commit+push
   (the addendum-78 tail) unless --no-git, then exit 130. The
   handler installs right after arg parsing, before any launch.

Memory-prediction pairs registered (to check against the next
run's three witnesses): (a) llama-server's own accounting should
report HIGHER totals than our smaps census (the UMA carveout is
invisible to smaps); (b) the ~80% bandwidth achievement may rise
to 90%+ once the hidden UMA part is counted - the working
hypothesis is the discrepancy was the hidden carveout traffic.

Addendum 9: git_tail now globs the per-model server logs (models/*/
*.arc-cell*.log, *-server.log, *window-probe.log). The lesson from
both interrupted runs: the Ctrl-C landed before the tail, so the
only copies of llama's own -lv 5 memory accounting sat uncommitted
on the author's disk - prediction B (bandwidth rising to 90%+ once
the UMA-hidden size is counted) needs those logs to compute. The
SIGINT handler (addendum 8) now runs the tail on interruption; this
glob makes the tail actually reach them.

Addendum 10: both memory predictions computed from the committed -lv 5
logs (254 files). Prediction A CONFIRMED: llama's own weight accounting
(1.0-3.2 GiB per family) is 3-8x our smaps census (0.14-0.42 GiB
resident) - the UMA/GTT-hidden fraction was exactly the missing witness,
and the machine-cost (MemAvailable) figures match llama weights plus
overhead. Prediction B CONFIRMED FOR ATTENTION MODELS ONLY, with a
correction: the true hybrid set is larger than the Jamba pair. The
arc-cell logs reveal llama_memory_recurrent layers in Qwen3.5-0.8B,
Qwen3.5-2B (qwen35 arch, full_attention_interval 4) and RWKV7 alongside
the Jambas - five of nine families are SSM/recurrent hybrids. Full BW
table (weights from model-buffer-size sums incl. the 0.00 placeholder
blocks, KV linear-scaled from the ctx-4096 memory breakdown, t/s =
worst turn of the earliest-rung speed cells):

  family                  rung  t/s  w GiB  denom  BW GiB/s  %102.4
  Llama-3.2-1B             8448  43.3  1.48   1.74     75.3    74%
  Qwen3.5-2B               4352  45.8  1.57   1.69     77.6    76%
  MiniCPM5-2B              8448  26.0  2.49   2.83     73.5    72%
  MiniCPM5-1B              8448  56.1  1.07   1.26     70.8    69%
  gemma-3-1b-it            4352  52.8  1.29   1.36     71.9    70%
  Qwen3.5-0.8B             4352  62.7  1.00   1.00     62.6    61%
  RWKV7-Goose-World3       8448  16.0  3.03   3.20     51.2    50%
  Jamba2-3B               131k    9.8  3.17   4.49     44.0    43%
  Jamba-Reasoning-3B       8448  10.8  3.17   3.26     35.3    34%

The attention models cluster at 70-76% of theoretical, NOT the 90%+
predicted - the remaining gap is likely the ~25% Vulkan_Host fraction
(cross-heap traffic) plus the KV-linear-scaling approximation. The
hybrids sit at 34-61% because the size x t/s law does not apply: SSM
layers read a bounded recurrent state per token, not the full weight
matrix, so their per-token traffic is a fraction of the denominator.
Correction to the earlier Jamba-only claim: the law exception is a
property of the architecture, not of one vendor. The Qwen3.5 parse bug
(first model-buffer-size lines are 0.00 placeholders before the real
Vulkan0/Vulkan_Host sizes) is resolved by summing all occurrences.

Addendum 11: the smaps census is RETIRED - llama-server's own accounting
is the memory witness. Ruling from the author after addendum 10: "at
least we know the llama-server measurements are reliable." The new
llama_server.memory_breakdown_gib() parses the -lv 5 memory-breakdown
table (both row shapes: the paren'd device line and the flat Host line)
into per-device model/context/compute plus weights_gib (summed over ALL
model-buffer-size lines - hybrid builds print a 0.00 placeholder before
the real split). All three census sites switched: fwe_cell, vt_cell and
the speed-gate mem report now record mem_census = {source, weights_gib,
model_gib, context_gib, compute_gib, total_gib, devices}. The smaps
mapped_plus_gpu_gib / amdgpu delta / peak-RSS machinery stays in
llama_server.py (the old records cite it) but is no longer called by
the benchmark; mem_cost_gib (MemAvailable) remains as the machine-level
witness. Blocking-gate ranking from the stored records at the current
bars (speed 0, fwe 3/3, vt 5/5, arc 4/5): VT is the most blocking gate
at 31% pass (103/335 cells), then fwe 47% (88/189), arc 60% (33/55),
speed 100% (111/111 - free until deep rungs).

Addendum 12: VT bar calibrated to 4/5 (TASK_PASS_BARS["vt"]). At 5/5 VT
was the most blocking gate at 31% (addendum 11); at 4/5 the stored
records re-grade to 61% and the blocking ranking flips: fwe 3/3 is now
the hardest bar at 47%, then vt 4/5 61%, arc 4/5 60%, speed 100%. The
per-family picture at 4/5: Qwen3.5-2B (57/57) and Qwen3.5-0.8B (54/55)
own VT - the hybrids with full_attention_interval 4 are the variable
trackers - while Jamba-Reasoning (1/28), MiniCPM5-1B (0/26) and RWKV7
(2/19) stay dead, so 4/5 keeps separation at both ends. Who's blocking
next: FWE 3/3, killing Jamba-Reasoning (0/9), RWKV7 (0/13), MiniCPM5-1B
(0/8) and gemma (3/16) outright.

Addendum 13: FWE bar calibrated to 2/3 (TASK_PASS_BARS["fwe"]). The
author's floor rule: keep the aggregate pass rate >= 50%, "if k needs to
become zero to do so, we have a problem". Re-grade ladder of the stored
records: k=3 -> 47%, k=2 -> 68%, k=1 -> 78%, k=0 -> 100% - 2/3 clears
the floor with margin, and the 3->2 move is where the big jump lives
(41 new passing cells: a 2/3 cell is a "found the list, missed one
word" recall, not a fluke). At the new bars the blocking ranking is:
arc 60% < vt 61% < fwe 68% < speed 100% - ARC and VT are now the
co-blocking gates. Separation survives: Jamba-Reasoning, MiniCPM5-1B
and RWKV7 still sit at 0 fwe passes; MiniCPM5-2B moves 1/16 -> 3/16
and gemma 3/16 -> 7/16 (still failing); the alive set is unchanged
(Qwen3.5-2B, Qwen3.5-0.8B, Jamba2), now with perfect fwe records
(13/13, 33/33, 67/69).

Addendum 14: roster widened to 12 and everyone's config standardized to
(q8 weights, f16 K, f16 V). Who changed: Qwen3.5-2B - its 90 cells were
all Q4_K_M (the session-34 context-over-parameters config; its arc logs
are Qwen3.5-2B-Q4_K_M.gguf.*), so the config move makes it a different
model instance. Ruling (author, via question): wipe the records, fresh
start - cells are never re-measured and the Q4_K_M cells belong to a
different config; the family re-enters with 0 cells at Q8_0. Three new
competitors join at (Q8_0, f16, f16): qwen2.5-1.5b-instruct (ladder: 32k
at 18 w/s worst span, vanilla attention), Qwen3.5-4B (ladder: 131k
window, 4.3 GiB Q8 near the 5 GiB BW ceiling) and Qwen3-1.7B (ladder:
32k at 7.6 w/s). Preflight caveat from models.md: the 4B and 3-1.7B were
closed at their FLOOR configs (q2/q4 KV); at f16 KV their deep rungs
may hit the RAM ceiling - the dry run's feasibility check reports it
per family, and a ceiling simply stops the climb (a config ceiling, not
a model failure).
