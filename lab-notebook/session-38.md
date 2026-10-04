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
