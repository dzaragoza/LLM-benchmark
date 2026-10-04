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
