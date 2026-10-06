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

## Addendum 3 - code_edit.py review: four bugs found by experiment, fixed, gated (2026-10-06, the author's "do all" + tool ownership)

The author asked for a code_edit.py review with proposals, then ruled
"do all" and handed me the tool's ownership ("you're the user and
owner of that tool") - future code_edit issues are mine to fix
autonomously, with notebook registration. This addendum registers
the review and the four fixes.

FIX 1 - STALE REGIONS (the serious one). edit_many's delimiter check
consumed _last_edit_regions, a MODULE-GLOBAL written by the
PREVIOUS edit() call - regions from ANOTHER FILE. Failure mode is a
false PASS: the stale regions land on benign spans of the new file
and the file's own region - carrying a real unbalanced-quote
violation - is never checked (reproduced before the fix: the
violating edit_many sailed through). THE FIX: the global is
DELETED; _apply now returns (out, regions) and every caller
(edit, edit_many, preview, check) threads its own regions into
_check_delimiters(src, out, path, regions).

FIX 2 - edit_many SKIPPED THE MD GATES. edit() runs _fix_markdown +
_check_markdown; edit_many ran neither - an .md file edited via
edit_many got no MD047/MD058 auto-fix and no introduced-violation
gate. edit_many now runs both after _verify_result, mirroring edit().

FIX 3 - _verify_result FALSE-PASS WINDOW. The replace branch checked
only that the new text IS in the result - never that the old text is
GONE; an apply that silently missed left both texts in the buffer
and passed. Companion check added: for replace/replace_all with
new != old and old not contained in new, the old text surviving in
the result fails the edit. Legal cases (new == old; new contains
old) still pass.

FIX 4 - check() TOCTOU. check() verified against one read of the
file and then called preview() - a SECOND read - so the verdict and
the returned diff could disagree if the file changed between reads.
check() now computes the unified diff inline (difflib.unified_diff)
from its single read, and runs the md gates for parity; the
returned diff IS the verified result.

ALSO: removed duplicated pairs/closers bindings inside
_check_delimiters (dead - shadowed by the outer ones before
balance_no_underflow used them... in fact the outer ones were dead
and the inner ones live; the duplication is gone either way).

TESTS: four regression tests added to test_seams.py
(region_check_not_stale - a .c false-pass repro, since the original
.py repro is now refused earlier by the session-37 ast gate;
edit_many_runs_md_gates; verify_old_text_gone; check_single_read).
Two test-side bugs caught while landing them: a bare PosixPath
passed where code_edit takes str paths, and pytest.raises without a
pytest import (the file's idiom is try/except + assert raised) -
both fixed to the file's established style.

VERIFIED: 162/162 pytest (158 before + 4 new), ty 0 via the
addendum-21 wrapper, ruff check + format clean, md_check, js_check
pass. Pre-commit runner still fails under the sandbox command
wrapper (session-39 note); all hooks run manually green before the
commit.
