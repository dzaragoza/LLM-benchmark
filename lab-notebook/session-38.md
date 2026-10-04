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
