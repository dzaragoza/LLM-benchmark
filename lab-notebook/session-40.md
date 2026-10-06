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
