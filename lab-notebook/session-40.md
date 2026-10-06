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

## Addendum 4 - coverage as a discovery tool: three real bugs in code_edit.py, one testless gem in cells.py (2026-10-06, the author's "anything worth improving?")

THE AUTHOR'S RULING: coverage.py is a HELPER TO DISCOVER MISSING
TESTS, run from time to time - never a hook, never a metric. It
entered the toolbox this session (pip-installed in the sandbox, not
a repo dependency; no repo config committed).

THE FIRST RUN (--branch, full suite): code_edit.py 79% with 53
partial branches; the misses clustered in balance()'s character
loop - the core of the delimiter checker. Probing those paths found
THREE REAL BUGS (all mine per the tool-ownership ruling):

BUG 1 (false pass): an unclosed triple quote at end of buffer
returned None from balance() - the whole-buffer check (markup/json)
accepted corrupted edits (reproduced: an edit leaving an unterminated
""" sailed through). FIX: balance() now reports "unclosed triple
quote" after the loop. Region mode unchanged: a triple quote that
closes after the region is legal (a docstring opener) and the
region check tolerates it by design.

BUG 2 (false failure): _verify_result demanded the PATTERN still
match the result after a replace_regex - false-failing every
ordinary replacement (old_word -> new_word no longer matches
old_word; reproduced). FIX: the verify now checks the literal
replacement text is in the result, and skips the check when the
replacement carries backreferences (its text is not literal).

BUG 3 (false pass): balance() conflated a MISMATCHED closer (stack
non-empty, wrong species - corruption) with closer UNDERFLOW (empty
stack - legal, the opener may sit before the region), returning
"unbalanced" for both; balance_no_underflow then filtered BOTH
out, so a true mismatch inside a region was never caught. FIX:
underflow gets its own message ("closer underflow") and only
"unbalanced"/quote problems fail the region check - exactly what
the docstring always claimed.

TESTS ADDED: test_code_edit_balance_interior_paths (comments
carrying brackets, escapes inside strings, mismatch-vs-underflow
in the region), test_code_edit_unclosed_triple_quote_refused,
test_code_edit_replace_regex_verify_literal (literal + backref),
and test_banner_window in test_ruler_gate.py - bench/cells.py's
_banner_window (the trained-context cap reader that anchors the
ceiling search; pure log parsing, 9%-covered module) now has its
first test.

The mismatch test itself needed three attempts - my first two
cases were underflow from the REGION's viewpoint (the opener sat
outside it), teaching the design point afresh: regions are checked
as units and cannot see the buffer around them.

NUMBERS (discovery, not a metric): code_edit.py 79% -> 83%, 53 ->
49 partial branches; bench/cells.py 9% -> 16% (the testable logic;
the rest is live-hardware orchestration, correctly untested).
state_store.py's 53% noted as the next-lowest pure-repo module -
deferred, low priority.

VERIFIED: 166/166 pytest (162 + 4 new test functions), ty 0 via
the addendum-21 wrapper, ruff check +
format clean, md_check, js_check pass. Pre-commit runner still
fails under the sandbox command wrapper; all hooks run manually
green before the commit.

## Addendum 5 - the three-layer audit: architecture intact, README drifted, three bypasses removed (2026-10-06, the author's "A) do it, B) no bypasses")

THE AUDIT (against README's "Repository layout (three layers)", the
author's early definition): the layering DIRECTION holds - the top
is one orchestrator, the middle measures, the bottom owns ALL
outside contact; every HF/llama.cpp/llama-server call site verified
to route through the bottom interfaces. Two drifts and three
bypasses found; the author ruled "A) do it, B) no bypasses".

DRIFT (A - fixed): the README table still listed the retired
arc_eval.py and mcnemar.py (removed when the depth score became the
ranking, protocol v4.3) and omitted ruler_gate.py and the ENTIRE
bench/ package (born session 39 addendum 15 - the biggest structural
change since the table was written). The table now matches the
tree: bench/cells, certify, tournament, ladder, size_table,
state_store as middle layer; ruler_gate.py added; the retired
scripts noted below the table; git_ops.py added (below).

BYPASS 1 - bench/cells.py kill_stale_server shelled pkill
directly (middle layer process control). FIX: the subprocess moved
down into llama_server.kill_stale_server() (bottom); cells keeps
the thin wrapper with its prints. The same helper now also serves
full_benchmark's SIGINT shutdown, which had its OWN pkill - one
seam, two former bypasses gone.

BYPASS 2 - full_benchmark.py ran the git binary via subprocess in
git_pull_head, git_tail (add/commit/pull/push) and the SIGINT
handler: top-layer direct outside contact. FIX: new bottom-layer
git_ops.py (inside_work_tree, pull_rebase, add, commit,
staged_changes_exist, push - import only); git_tail and
git_pull_head rewired; behavior unchanged (the addendum-47
commit->pull->push order and the addendum-34 pre-tee pull both
preserved and still test-pinned). Distinct from git_push.py - that
is the sandbox's REST-API push workaround, not the bench machine's
plain-git seam; the docstrings cross-reference.

BYPASS 3 - ruler_gate.py probed http://127.0.0.1:{port}/health
with its own urllib (duplicating the HTTP layer). FIX:
llama_server.port_serves_health(port) returns "ok"/"error"/None;
ruler_gate's stale-server refusal rewired onto it, message text
unchanged.

TESTS: test_git_pull_head rewritten onto the git_ops seam
(monkeypatching full_benchmark.subprocess patched a module that no
longer imports it); test_git_pull_before_tee and
test_git_tail_pulls_before_push re-pinned to the new call names -
their regression PURPOSE is unchanged (the sequence and the
--autostash live in git_ops now, still asserted).

VERIFIED: 166/166 pytest, ty 0 via the addendum-21 wrapper, ruff
check + format clean, md_check, js_check pass. The final grep
audit: no git/pkill/urllib-urlopen contact outside the bottom
layers (the one hit is a package-name string in the requirements
check). --no-verify only because the pre-commit runner fails under
this sandbox's command wrapper (all hooks run manually green).

## Addendum 6 - code_edit as the only editor: the protocol row + the two improvements that retire the raw tool (2026-10-06, the author's variant B)

THE AUTHOR'S RULING (on the addendum-5 incident disclosure): the
protocol row lands, with the variant that code_edit must handle
EVERYTHING - where it can't yet, that is an improvement proposal, and
the raw tool may be used meanwhile. "The goal is to make code_edit
really good, so there's no reason to pick anything else."

WHY I HAD PICKED THE RAW TOOL (the honest gap analysis): the
session-5 refactor edits went through the SDK's raw search/replace,
which has neither verify-before-write nor transactionality - the
truncating edit that briefly mangled git_tail would have been
refused by code_edit's gates. But the deeper cause: the edit that
pushed me off code_edit was a replace whose target missed on
FORMATTING DRIFT (ruff format had since reformatted a line my
context was written against) - code_edit answered with a blind
"target not found", and rather than re-read and re-aim I reached for
the raw tool. Wrong call; the fix is to make re-aiming unnecessary.

IMPROVEMENT 1 - THE WHITESPACE-FLEXIBLE REPLACE RESCUE: a replace
target that misses exactly but matches EXACTLY ONE place
whitespace-flexibly (whitespace runs matched as \s+) is rescued -
the edit applies against the FILE's own text. Ambiguity stays a
refusal (never a guess); exact matching still wins when it matches.
This is the formatting-drift case: the target's semantics are
unambiguous, only its whitespace is stale.

IMPROVEMENT 2 - NOT-FOUND DIAGNOSTICS: a total miss now reports the
wanted first line AND the file's own near lines (the lines carrying
the target's signature), so the caller re-aims from the file's
reality instead of guessing. Shared _find_replace_target helper;
_apply and _verify_blocks both use it, so check/edit/preview/edit_many
all rescue identically.

THE PROTOCOL ROW ([P] "Vibe's editor"): Vibe owns code_edit.py and
edits program files THROUGH it; the raw tool is not to be picked
when code_edit can do the job; code_edit's goal is no-reason-to-pick-
anything-else.

TESTS: test_code_edit_replace_whitespace_flexible (rescue, exact
unchanged, total miss refused with context, file untouched).

VERIFIED: 167/167 pytest, ty 0 via the addendum-21 wrapper, ruff
check + format clean, md_check (with the new protocol row), js_check
pass. --no-verify only because the pre-commit runner fails under
this sandbox's command wrapper (all hooks run manually green).

## Addendum 7 - the bottom layer becomes infra/ (2026-10-06, the author's proposal)

THE AUTHOR'S PROPOSAL: the bottom layer becomes a package, so only
CLI-usable scripts live in the root directory. Ruled this session:
the package is infra/ (the author's pick from the options) and
tee_output.py is MIDDLE layer - it rides to bench/ ("that should be
layer 2. In bench").

THE MOVES (git mv, history preserved): hf_download.py, convert_quant.py llama_server.py, git_ops.py -> infra/; tee_output.py
-> bench/tee_output.py. infra/__init__.py created.

THE ROOT NOW: full_benchmark.py (top), speed_gate.py, ruler_gate.py,
depth_probe.py, session_replicate.py, size_predict.py, lag_analyze.py,
law_fit.py, tokenizer_probe.py (middle, all CLI+import), plus the
dev/tools that are their own CLIs (code_edit.py, git_push.py,
md_check.py, js_check.py, sandbox_check.py, ty_check.py).

REWIRING: every import site aliased to keep the call sites untouched
(import infra.llama_server as llama_server) - zero behavioral change,
all 9 root scripts, 5 bench modules, 3 test files; one from-import
(law_fit's RUNG_BITS) moved to from infra.hf_download. All edits via
code_edit per the addendum-6 protocol row.

DOCS: README layer table rows updated to infra/ paths; protocol.md's
Where-column citations (RAM reserve, snapshot scope, converter pins,
RUNG_BITS, memory witness, health timeouts) and model-selection.md's
RUNG_BITS citation updated.

VERIFIED: 167/167 pytest, ty 0 via the addendum-21 wrapper, ruff
check + format clean, md_check, js_check pass; --help smoke on every
root CLI (fb/sg/rg) and bench CLI (certify/size_table) exits 0; the
stale-import grep is empty. --no-verify only because the pre-commit
runner fails under this sandbox's command wrapper (all hooks run
manually green).

## Addendum 8 - code_search.py: the AST-based search tool (2026-10-06, the author's "implement it")

THE AUTHOR'S PROPOSAL ACCEPTED: dedicated search tooling, with the
standing removal clause - "if we find it not useful we can remove
it". The honest sizing from the discussion stands: grep covers
literal search fine; the gap is SEMANTIC search (grep cannot follow
`import infra.llama_server as llama_server` to the call sites of
start_server, or through assignment aliases like
kill_stale_server = _cells.kill_stale_server).

THE TOOL: code_search.py (root dev tool, own CLI + import), three
commands on the AST:
- defs SYMBOL: definition sites (def/class/assign alias/import
  binding), refusing unknown symbols rather than returning empty;
- refs SYMBOL: reference sites, resolving `from infra.hf_download
  import RUNG_BITS`-style bindings;
- calls FUNC: call sites, plain and module-qualified, resolving the
  addendum-7 import aliases (llama_server.start_server() is reported
  as infra.llama_server.start_server).
Philosophy: same as code_edit - refuse rather than guess (an
unresolvable alias is reported, never silently dropped).

VALIDATED ON THE SESSION'S OWN SEAMS: defs kill_stale_server finds
all three sites (infra def, bench wrapper, fb alias); calls
start_server resolves every site across the addendum-7 seams; refs
RUNG_BITS finds law_fit's from-import and the definition. This is
exactly the query set the addendum-5 audit needed a dozen greps for.

TESTS: tests/test_code_search.py - 5 tests (the three commands on
the live seams + the two refusals).

DOCS: README gains a dev-tools table (code_edit, code_search, the
gate wrappers, git_push, sandbox_check) - the tool family was
previously undocumented as a group.

VERIFIED: 172/172 pytest (167 + 5), ty 0 via the addendum-21
wrapper, ruff check + format clean, md_check, js_check pass.
--no-verify only because the pre-commit runner fails under this
sandbox's command wrapper (all hooks run manually green).

## Addendum 9 - the code-tools charter (2026-10-06, the author's ruling)

THE AUTHOR'S RULING on the code-tool family (code_edit, code_search,
the checkers): "The goal for the code tools is to improve the
workflow when gaps are detected. No point in reinventing the well if
other tools already do it well."

Standing interpretation: (1) a tool is BUILT when a concrete gap is
detected in the workflow (code_edit: verify-before-write edits; the
addendum-6 flexible-rescue and not-found diagnostics: the
formatting-drift gap; code_search: the semantic-search gap the
addendum-5/7 refactors exposed) - never speculatively; (2) existing
tools that already do the job well are ADOPTED, not rebuilt (ty for
type-checking via the wrapper, ruff for lint+format, pytest,
vulture for dead-code discovery, coverage.py as the missing-test
discovery helper - none of them reimplemented); (3) a built tool
carries a removal clause (code_search: "if we find it not useful we
can remove it") - usefulness is judged by whether it actually
improves the workflow, and honest reports back to the author; (4)
before building, the first question is always: does something
already existing do this well?

VERIFIED: md_check pass (notebook-only change; the code gates are
untouched - no --no-verify needed for a markdown-only commit, but
the pre-commit runner still fails under this sandbox's command
wrapper, so the md hook's check was run manually).
