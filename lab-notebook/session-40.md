# Session 40 - 2026-10-06

Opened 2026-10-06 (the author's good-morning open). Carrying over
from session 39: the two open dead-code rulings
(_vt_shuffle_sublists_heap, recommended_max_rung) and the
session-39 census-coverage note.

## Addendum 1 - recommended_max_rung on the table (2026-10-06, the author's request)

The author asked for the recommended_max_rung explanation - the
ruling session 39 addendum 22 left open. THE FACTS: bench/size_table.py
builds one row per (family, rung) from committed evidence (-lv 5
census logs + speed dumps); a row's "recommend" verdict = holds the
reader line AND 0 stalls; recommended_max_rung(rows) collapses the
grid to the per-family HEADLINE - the deepest recommendable rung
(the practitioner's "how deep can I take this model" number).
Session 39 addendum 16 registered it as a headline ("the deepest
recommendable rung") but the --size-table CLI wires only
print_size_table (the grid); the headline is computed by TESTS ONLY
(test_seams.py exercises it). The question for the author: wire it
(one print block in the CLI path - the headline under the grid) or
delete it (the grid's * column carries the same information). This
addendum puts the facts on the table; the author's ruling decides.

## Addendum 2 - the VT heap ruling closed: code exonerated, registrations corrected (2026-10-06, the author's "fix vt")

THE VERDICT (from upstream source, fetched and read this session):
NVIDIA/RULER variable_tracking.py @ main has TWO haystack branches.
The ESSAY branch uses shuffle_sublists_heap (the heap interleave);
the NOISE branch - our instrument, type_haystack 'noise' - inserts
each chain's sentences at random positions via random.sample, sorted.
Our build_vt_task's insertion code (ruler_gate.py) is upstream's noise
path VERBATIM. The stored VT cells (103/335, the 4/5 bar calibration)
were measured with faithful code - no comparability problem, nothing
rewired.

THE ERROR: _vt_shuffle_sublists_heap was a transcription of the essay
branch's helper - dead on arrival for our noise instrument - and its
docstring story infected the registrations: the module header comment,
build_vt_task's docstring, test_ruler_gate's comments, protocol.md's
VT instrument row, and session 37's notebook entry all said "heap
shuffle". Five documents, one wrong claim, zero wrong behavior.

THE FIX: _vt_shuffle_sublists_heap DELETED (dead even upstream-style,
never called since its birth commit c278b6d); all living registrations
corrected to "random insertion positions, upstream's noise path
verbatim" (ruler_gate header + docstring, test comments, protocol.md
VT row). Session 37's text is HISTORY - corrected by this addendum,
not rewritten (the notebook never rewrites history; corrections ride
as new addenda).

Session 39 addendum 22's open ruling #1 closes: registration error,
code exonerated. Open ruling #2 (recommended_max_rung) stands -
the author deferred it ("revisit later", session 40 addendum 1).

VERIFIED: 158/158 pytest, ty 0 via the addendum-21 wrapper, ruff
check + format clean, md_check, js_check pass.
