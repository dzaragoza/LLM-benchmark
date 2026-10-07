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

## Addendum 10 - the quality-toolbox rulings (2026-10-06, the author's four rulings)

ON THE "anything missing?" QUESTION, four rulings:

1. MUTATION TESTING: adopted for a once-in-a-while trial, per the
   coverage clause - a helper to find weak tests, never a metric,
   never a hook. mutmut installed sandbox-side (not a repo
   dependency); [tool.mutmut] in pyproject.toml points it at
   code_edit.py + md_check.py with the four pure test files
   (test_code_edit, test_python_syntax_gate, test_replace_verified,
   test_safe_append_md - test_seams imports other root modules and
   mutmut's staging dir does not copy them, so the selection is the
   files that exercise the mutated module alone).

2. CI RUNNER: REJECTED - the author's ruling: "you see the only one
   changing code" is Vibe; the pre-commit hooks + the notebook's
   VERIFIED lines are the enforcement. No GitHub Actions.

3. DEPENDENCY AUDITING: adopted as once-in-a-while (pip-audit,
   sandbox-side). FIRST RUN: requirements.txt -> "No known
   vulnerabilities found". The author's version question answered
   below (addendum 10 closing).

4. COMPLEXITY MEASUREMENT: REJECTED - the author's ruling verbatim:
   "that is an arbitrary metric, that leads to uncle Bob style
   code: a plethora of small functions that do something minimal,
   and instead of being able to read a piece of code in one place,
   you end up reading the same split in small functions everywhere
   in the code." The registry records: no complexity tool, ever;
   readability is judged by the reader, not by a number.

THE AUTHOR'S VERSION QUESTION ("isn't it simpler to just update to
the latest versions instead of checking for vulnerability?"): YES
for this repo - the honest answer from the repo's own constraints:
the workflow is simple (no service, no exposed surface), so the
pip-audit finding (currently clean) mostly duplicates what an
update would fix anyway. The caveat that keeps the audit in the
toolbox: requirements.txt is NOT fully free - the converter pins
are llama.cpp-b10964-compatible (torch, transformers, gguf,
sentencepiece must stay compatible with the pinned checkout, the
requirements.txt header says so). "Update everything to latest" can
break the pinned converter path in ways an audit would not predict
and an update would not fix. Registered practice: updates are
fine ad hoc; the pinned-converter block changes only with a
llama.cpp bump; pip-audit runs once in a while as a check that
costs one command.
MUTATION RUN (mutmut, first trial): 1922/1922 mutants -> 584 killed, 1069 survived, 263 suspicious (mutmut's 'tests' classification - the mutant made a test fail in a way mutmut flags as suspicious), 6 timeouts, 0 untested. The survival number is INFLATED by the narrow test selection: only the 4 pure test files (13 tests) run against mutants; test_seams.py (~25 tests, the strongest code_edit file) is excluded because mutmut's mutants/ staging dir cannot import the other root modules test_seams references. So the tally is directional, not a score. SAMPLED-MUTANT VERDICT (4 inspected): (1) code_edit.x__file_type__mutmut_3 - real gap, minor: flips the extension fallback for extension-less paths (no test uses such a path); (2) code_edit.x__apply__mutmut_11 - EQUIVALENT mutant: start index 0 -> None, buf[None:] == buf[0:] in Python, unkillable by any test; (3) code_edit.x__check_delimiters__mutmut_1 - real gap, structural: the whole prose path is exercised only by test_seams/test_ruler_gate, both outside the selection; (4) code_edit.x__find_replace_target__mutmut_3 - real gap: n == 1 -> n != 1 inverts the fast path, killed only by a duplicate-target test the selection lacks. Interpretation: the survived set mixes real gaps (mostly paths only test_seams covers), equivalent mutants, and mutant-mechanics artifacts (e.g. _as_lines/_lines_of reported 'no tests' because the staging dir rewrites helper calls). VERDICT: keep mutmut in the once-in-a-while toolbox per its ruling, but always with the selection caveat - a fair code_edit score requires test_seams in the run, which mutmut's staging-dir design makes infeasible today (it would need the imported root modules copied into mutants/). Removal clause stands: if a future trial adds no finding beyond what coverage + the gates already surface, remove it.

## Addendum 11 - the certification redesign: equidistant medals, n=20, the ascending ladder (2026-10-06, the author's rulings)

Three rulings, one redesign:

1. N IS 20 AGAIN: TOURNAMENT_CLIMBS 21 -> 20. The author chose 21
   for the mode, the mode is retired, and 20 is the minimum for a
   2-sigma Wilson bound. All fixtures and docstrings re-pinned; the
   accept/dead arithmetic shifted (an all-pass candidate accepts at
   10 measured cells; an all-fail one dies at 8 consecutive fails).

2. EQUIDISTANT MEDALS: the author's ruling - bronze 5, silver 10,
   gold 15 at n=20. The mechanism: the sigma values stay 0.5/1/2,
   the THRESHOLDS carry the spacing - bronze lo(0.5s) >= 0.20
   (first k=5), silver lo(1s) >= 0.375 (first k=10), gold
   lo(2s) >= 0.50 (first k=15). The majority floor (k >= ceil(n/2))
   is DROPPED from combined_medal - at n=20 it demanded k >= 10 and
   would forbid the bronze tier entirely. Interim history: the
   author first asked for 0.5 sigma bronze, which landed one cell
   below silver (k=12 vs 13 at n=21) because every tier shared the
   lo >= 0.5 condition; the 0.25 threshold (k ~ 7) was tried, then
   superseded by the equidistant ruling the same session.

3. RUNG SELECTION: full_benchmark fills the LOWEST rung possible
   before going up. --certify without --rungs now walks the
   ascending ladder 4,096 -> 262,144; a rung is ANSWERED when a
   model crowns the requested tier and the ladder STOPS there;
   all-dead at a rung moves the ladder UP to the next depth.
   Evaluation order unchanged: most-promising candidate first.

RULING B (the author picked it over A): the certify LEVEL maps to
the medal TIER - at_least_one = bronze, 1_sigma = silver,
2_sigma = gold - and the combined controller's per-task accept/dead
math IS the tier's own (z, threshold) bar. So the rung-stopping
accept fires exactly when combined_medal returns the requested
tier; no separate controller bar exists anymore.

THE SPEED GATE clarification (the author): the gate is working as
intended - strictly wps >= 5, k=1 one conversation per cell,
n=20 cells. The stall-rate tolerance (PASS <= 5%) is an obsolete
protocol-v3.1 banner concept that survives only in the single-run
speed_gate output, not in the cell grading. The 100% speed pass
rate across every family is a genuine result.

RE-GRADED STATE (no re-measurement - cells re-grade from records):
Qwen3.5-0.8B @4096 SILVER (speed 11/11, fwe 15/15, vt 11/11, arc
5/8 - arc coverage is the gap); AI21-Jamba2-3B @131072 SILVER
(fwe 10/11, vt 5/7, arc 6/7 - small-n vt/arc); MiniCPM5-2B @65536
BRONZE; 15 other complete rungs none. The sandbox cannot run the
benchmark (no GGUF weights, no llama-server, no GPU) - the run
happens on the author's machine: python3 full_benchmark.py
--certify 2_sigma --task all.

## Addendum 12 - the tier rename + the nameless run (2026-10-06, the author's rulings)

1. THE TIERS ARE THE SIGMAS: bronze/silver/gold renamed to
   0.5_sigma / 1_sigma / 2_sigma - the author's consistency ruling.
   The certify level and the medal tier now share one vocabulary:
   at_least_one answers at 0.5_sigma, 1_sigma at 1_sigma, 2_sigma
   at 2_sigma. combined_medal returns the sigma names; the tests and
   docstrings re-pinned.

2. THE NAMELESS RUN: the families positional is now optional
   (nargs="*"). Omitted, full_benchmark takes every family already
   in the state file - each entry carries its spec (Qwen/Qwen3.5-0.8B
   etc.), so the certify ladder needs no names on the command line:
   python3 full_benchmark.py --certify 2_sigma --task all
   The state is the roster now. Explicit specs still override for
   fresh families.


## Addendum 13 - the speed-dead climb stop (2026-10-06, the author's optimization)

THE RULING: if a model is dead at rung k due to the SPEED gate, stop
climbing that model - it will not pass the gate at a higher rung,
because of the way the speed gate works. The gate measures at
depth + 2 * ANSWER_HEADROOM context, and stalling is monotonically
harder with depth, so a speed death at rung k is a permanent verdict
for every deeper rung of the ladder.

THE IMPLEMENTATION (bench/certify.py, the combined controller):
1. When the dead task is speed, the family persists
   fst["speed_dead_at"] = depth (saved immediately, before the
   DEAD printout) - the marker is family-level and lives in the
   state file, so it survives the rung loop and future invocations.
   A shallower death overwrites a deeper one (the earliest rung the
   gate failed is the truth); a non-speed death never writes it.
2. At candidate selection, before any measuring: a family whose
   speed_dead_at is set and <= the current rung is SKIPPED with
   entry["skipped"] = "speed gate died at {rung}" - mirroring the
   answered-rung skip, zero cells measured. The ascending ladder
   in full_benchmark.py shares the state object across rungs, so
   the marker applies naturally at every deeper rung.

HISTORICAL DATA: the marker is NOT seeded from the existing state -
no family has a recorded speed death yet (the gate passes 100%
everywhere in the current state), so there is nothing to backfill;
the marker accrues the first time a speed death actually happens.

TEST: test_speed_dead_stops_the_climb - a family whose speed cells
all fail gets verdict dead with speed_dead_at persisted; the deeper
rung skips it with zero _task_measure calls. 173/173 pytest, ty 0,
ruff check+format clean, md_check, js_check.

PROTOCOL ROW (P): both program-file edits went through code_edit.
The uniqueness friction seen twice here (the "rung already answered"
skip block appears in both the single-task and combined controllers)
is the known code_edit papercut - context disambiguation, not a tool
bug; an occurrence-index escape hatch remains a future improvement.


## Addendum 14 - the model-retrieval bug: the leaked spec (2026-10-06)

THE SYMPTOM (the author's report, the 10:22 certify run in
results.txt): every family that needed acquisition downloaded the
SAME wrong repo - Llama-3.2-3B, Phi-3, Phi-4 all printed
"[1] downloading safetensors from mistralai/Mistral-7B-Instruct-v0.3"
- and then every candidate errored "model file not found".

THE ROOT CAUSE: a leaked loop variable. Both controllers
(certify_rung, certify_rung_combined) build the candidate order with
`for spec in specs:` and later, in the candidate loop, call
`_acquire_missing_model(spec, ...)`. The candidate loop reuses the
name `spec` for the LAST value of the roster loop - so with the
nameless run (addendum 12) over benchmark-state.json every family
acquired the roster's last spec (Mistral-7B-Instruct-v0.3). With a
single-family roster the bug is invisible: the leak and the truth
coincide. The nameless run made the roster long and the bug loud.

THE FIX: the order tuple now carries each family own spec -
(fam, fst, cells, spec) - and the candidate loop unpacks it; the
promise sort unpacks it as _spec. Both controllers fixed; no
behavior change beyond the acquisition target.

THE REGRESSION TEST: test_certify_acquires_from_each_family_own_spec
- two families with missing models, a faked _acquire_missing_model
records what each candidate asks for; asserts each family gets its
OWN spec, not the last one. 174/174 pytest, ty 0, ruff check+format
clean, md_check, js_check.

CODE_EDIT NOTE (the owner's honesty): the fix needed 6 aimed edits
across two near-twin controller bodies. The exact `replace` blocks
collided with the twin (found 2 times) and the whitespace-flexible
fallback then landed some blocks on the WRONG twin, producing a
syntax error - caught and refused by the syntax gate, file
untouched both times, exactly as designed. The working path was
replace_all for the genuinely shared lines plus context-anchored
replace for the type lines. No code_edit change made: the refusal
behavior is correct; the friction is aiming twin regions, and the
occurrence-index idea (addendum 13) remains the candidate feature.


## Addendum 15 - Ctrl-C during a download now stops the run (2026-10-06)

THE SYMPTOM (the author's report): interrupting full_benchmark
during a model download did not stop it - it just moved to the next
model.

THE ROOT CAUSE: the Ctrl-C handler (session 38, addendum 8) stops
llama-server, stops logging, runs the git tail and exits via
SystemExit(130). Two per-family isolation guards swallowed that
exit: _acquire_missing_model in bench/certify.py (except
SystemExit: return None - a hub phase fail(1) was the intended
catch) and the sweep_families loop in full_benchmark.py (except
SystemExit - a process_family abort was the intended catch). The
130 was recorded as a family failure and the loop continued - the
author pressing Ctrl-C once during a long download merely skipped
to the next download.

THE FIX: both guards now re-raise SystemExit when e.code == 130 -
the interrupt is a RUN-level signal, not a family failure; every
other exit code keeps the addendum-78 isolation (recorded, the
sweep continues). The handler already does the clean shutdown, so
nothing else changes.

THE TEST: test_sigint_during_acquire_stops_the_run - a faked
hf_download.acquire raises SystemExit(130) for one family and
SystemExit(1) for the next; the 130 propagates out of
certify_rung_combined, the 1 stays isolated. 175/175 pytest, ty 0,
ruff check+format clean, md_check, js_check.


## Addendum 16 - the root-json cleanup (2026-10-06, the author's "do it")

24 JSON files lived at the repo root; three classes, one ruling:

1. THE STUDY TWINS MOVED TO state/ (19 files): every
   benchmark-results-<study>.json (ceil1 ceil4 ceilj ceilr f4k
   failed1k kvq4-q4 kvq8-q4 lineage lineage2 o8probe p2 q4 rebench
   sentinel) had its state twin already in state/ - the results now
   sit beside them. Four stray STATE files (thinking, kvprobe,
   sentinel, lineage) were root orphans of the same consolidation;
   the README already claimed state/benchmark-state-thinking.json,
   so the move fixed a real inconsistency. git mv preserves
   history. benchmark-results.json STAYS at the root: it is the
   RESULTS_FILE_DEFAULT of the default run.

2. THE CORPUS MOVED TO data/ (1 file): live-corpus-cal50.json is
   benchmark INPUT, not an artifact - its own directory.
   CORPUS_DEFAULT updated in speed_gate.py, tokenizer_probe.py,
   depth_probe.py, session_replicate.py (full_benchmark.py inherits
   speed_gate's); README and protocol references updated with it.

3. THE ONE-OFFS DELETED (3 files): live-dump-gallop.json,
   selection-recovered.json, selection-results.json - unreferenced
   by any code, added 2026-10-03 in a manual inspection session;
   git history keeps them.

Verification: the corpus default resolves and loads (50
   conversations), full_benchmark argparse intact, 175/175 pytest,
   ty 0, ruff check+format clean, md_check, js_check.

PROTOCOL NOTE: the protocol.md corpus row and the README thinking
   command now point at the true paths - protocol.md is current
   values only, and the current values changed.


## Addendum 17 - the 10:57 run: two residuals fixed (2026-10-06)

The 10:57 log shows the addendum-14 fix working (Llama-3.2-3B
downloads from meta-llama, its OWN repo) - two residuals remained:

1. THE NEVER-SELECTED FAMILY: Llama-3.1-8B-Instruct errored
   "model file not found (None)" - its state entry has
   selected=None (registered but never walked), so the rung
   resolved to None and _acquire_missing_model returned None
   without ever touching the network. Fix: the rung falls back to
   RUNG_DEFAULT (Q8_0) in both controllers - a family in the
   roster without a selection acquires at the study default.
   Regression test test_unselected_family_falls_back_to_default_rung
   asserts the acquisition asks for Q8_0, not None.

2. CTRL-C STILL DID NOT STOP (the author's second report): the
   handler ran - the SIGINT stamps ARE in results.txt - but the
   process kept waiting. Root cause: sys.exit(130) raises
   SystemExit inside the handler, and the main thread at that
   moment sits inside huggingface_hub's snapshot_download, whose
   hf_thread_map runs downloads in a ThreadPoolExecutor context
   manager - unwinding passes through executor.__exit__ ->
   shutdown(wait=True), which politely waits out every in-flight
   download before the exit takes effect. Fix: the handler ends in
   os._exit(130) AFTER the clean shutdown (llama-server killed, tee
   uninstalled, git tail run, stamps flushed) - a hard exit no
   executor can hold hostage. The addendum-8 sequence test
   re-pinned to the hard exit (os._exit monkeypatched to raise).

Both errors from the author's report are closed. 176/176 pytest,
ty 0, ruff check+format clean, md_check, js_check.

CODE_EDIT NOTE: the whitespace-flexible fallback once again
misfired - the addendum-17 comment block landed one line off,
gluing "args = argparse.Namespace(...)" onto the preceding assert
line (a SyntaxError-free but broken edit, caught by the test
failure and re-aimed). The fallback applying blocks at
whitespace-flexible positions when the exact text misses is the
recurring papercut; exact-match-or-refuse for non-twin regions is
the candidate hardening, noted for the next code_edit review.


## Addendum 18 - the taxonomy ruling (2026-10-06, the author's terms clarified)

THE QUESTION (the author): a lineage is a series of versions
(model1.0, model2.0...); a family is the same model at different
parameters (model1.0-1b, model1.0-3b...); a model is a specific
config (model1.0-1b q8 / q4...). Does the literature match?

THE ANSWER: close, but three adjustments. (1) The literature word
for the version axis is RELEASE (or version/generation); "lineage"
in the literature means PROVENANCE - what a model derives from
(fine-tune ancestry), not versioning. (2) FAMILY matches, but the
literature's extension is WIDER - a family bundles the sizes AND
the variants (instruct, base) of one release, sometimes across
releases; the study's usage narrows it to the size axis of a
single release. (3) The literature word for the config level is
VARIANT (or model instance/checkpoint; the GGUF community says
quant); the study's variant is the (family, rung, kv_k, kv_v)
tuple - the unit that gets a model file, a server launch, and
cells.

THE RULING: literature-compatible terms with EXPLICIT study
extensions, registered as a Taxonomy section in protocol.md
(between The anchor and [A]) - a term alone is not enough; what
the term COVERS here is stated, so there is no confusion:
release > family > variant, with examples (Qwen3.5-0.8B and
Qwen3.5-2B are ONE family; Qwen3.5-2B and Qwen2.5-3B are NOT) and
the literature note per term.

THE MIGRATION: none needed in code - the `families` key matches
the (narrowed) literature term; "lineage" was never a code term
(the lineage STUDIES compared releases, and their artifacts were
already consolidated in addendum 16). protocol.md change-log row
18 registers the section.

### Addendum 19 - the session-uniformity restructure: one session per working day (2026-10-06, the author's ruling)

THE RULING: a session starts every day there's work done; there cannot be more than one session per day. Fuzzy ends are the author's early-morning finishes - best judgement applies, and the judgement is the ALREADY-REGISTERED precedent: an early-morning finish belongs to the working day it started ("the working day ran past midnight - recorded, not split").

THE AUDIT: the notebook had five working days carrying multiple session openers, all pre-09-30 (the session-39 addendum-19 audit had already unified the 09-30+ era). Merged per the ruling - content verbatim, session numbers and addendum numbers UNCHANGED (citations across protocol.md, the registry, and the notebook reference session numbers constantly; the notebook never rewrites history, it only moves content by registered addendum):

1. 2026-09-21: sessions 1-13 + the session-3 prep merged into session-01.md (the lowest number of the day; the megafile's 09-21 sections - the selection-algorithm v2, directory rules, sessions 8-13 - moved in). Three pre-notebook commits on 2026-09-20 are noted in the merge header.
2. 2026-09-22: sessions 14, 15, 16 and 18b extracted from the session-07.md megafile into the NEW session-14.md.
3. 2026-09-23: sessions 18c-18v, 19, 20 (megafile) plus the session-21/22 files merged into the NEW session-18.md. The megafile session-07.md is now EMPTY OF FOREIGN SESSIONS and deleted; session 7's own content lives in session-01.md.
4. 2026-09-24: sessions 23, 24, 25 (and 26, already inside 25) merged into session-23.md. The 00:40-01:47 commits on 2026-09-25 are session 26's fuzzy tail of the 09-24 day - there is NO 2026-09-25 session (09-25 has no daytime work; its only commits are the early-morning tail).
5. 2026-09-26: sessions 27, 28, 29 merged into session-27.md (all three opened the 26th; 29's tail runs into the 27th, recorded not split).
6. 2026-09-28: sessions 31, 32, 33 merged into session-31.md (all three opened the 28th; 33's tail runs through 09-30, recorded not split - so there is no 2026-09-29 session either).

KEPT AS-IS: session 30 (opened the 27th), sessions 34-40 (one per day since 09-30, already compliant). Day-spanning sessions keep their OPENING day.

THE INDEX: one entry per working day; the merged entries name the day's first session and carry the day's session range. wow.md section 2 restated with the one-per-day rule and the fuzzy-end clause. Merge headers at the top of every merged file state the ruling, the day, and "content verbatim; session numbers unchanged" (the session-39 addendum-19 split precedent applied in reverse). Verified: every merged file's body reconstructs byte-identical from the pre-merge originals (a scripted line-exact diff against git HEAD).

### Addendum 20 - the missing phase 2: the certify path builds, not just downloads (2026-10-06, the author's "model download still broken")

THE REPORT: SIGINT behaves properly now (the 11:12 run's stamps show the clean shutdown), but every family in the nameless certify run still errored model-file-not-found. The 10:22 run's wrong-repo symptom was the addendum-14 leaked-spec bug (already fixed); the 11:12 run downloaded each family's OWN repo correctly - and then errored anyway.

THE ROOT CAUSE: _acquire_missing_model stops at PHASE 1. hf_download.acquire returns a FILE only when the rung GGUF can be downloaded ready-made; the Llama/Mistral/Phi repos ship safetensors, so acquire returns (None, "safetensors from <repo>, convert + quantize") - the file must be BUILT in phase 2 (convert_quant.create: safetensors -> f16 -> llama-quantize -> the rung). The certify controllers never ran phase 2 - the tournament path (full_benchmark.process_family) does, the certify path did not - so every build-required family errored model-file-not-found and the sweep moved on. The disk cleanup had deleted the built models, so the whole state roster tripped it at once.

THE FIX (both layers, the smallest correct change): (1) bench/certify._acquire_missing_model now runs convert_quant.create(fam, famdir, rung, plan) when acquire returns a plan without a file - the same phase 2 the tournament path runs; the built path lands in the family's tournament_entry exactly like a downloaded one. (2) infra/convert_quant.create guards its build: phase 1 must leave a source on disk (the rung file, an f16, or a safetensors/pytorch_model snapshot) before phase 2 can build - building from nothing crashed run_quiet on the missing family directory; it now reports "no local source to build <rung> from" and returns None (the candidate is recorded not-built, the run continues).

TESTS: test_certify_builds_the_model_when_acquire_returns_a_plan (the controller proceeds to measuring with the built file; 177 total). All gates: pytest 177/177, ty 0, ruff clean, md_check, js_check.

### Addendum 21 - the docs/ directory (2026-10-06, the author's ruling)

THE RULING: all root-level .md study documents move to docs/ - README.md alone stays at the root (the universal entry point), and the lab notebook keeps its own lab-notebook/ directory (its files are session artifacts, not study documents). Moved with git mv (history preserved): conversation up to 2026-09-27.md, lab-notebook-llms-on-102-4-gb-s-system-ram-machines.md, llm-benchmark-session-handoff-2026-09-24-conversation-refresh.md, model-selection.md, models.md, notebook.md, practitioner-goals.md, protocol.md, wow.md.

CROSS-REFERENCES UPDATED THE SAME COMMIT (the wow.md section-8 rule): etc/registry_data.py reads docs/models.md (the check command re-verified: 48 models, none missing); README.md links to docs/model-selection.md, docs/practitioner-goals.md, docs/protocol.md; the legacy notebook pointer's lab-notebook/index.md link re-anchored to ../lab-notebook/. Code's .md mentions elsewhere are comments/docstrings, not paths. wow.md section 8 registers the new home.

### Addendum 22 - the formal-methods pair: crosshair proves, hypothesis falsifies (2026-10-06, the author's "let's do crosshair and hypothesis")

THE AUTHOR, LEARNING FORMAL METHODS, RULED: crosshair (SMT-backed contract verification) + hypothesis (property-based testing) join the quality toolbox. The division of labor: a CONTRACT states what must hold for all inputs - crosshair PROVES it (z3) or returns a concrete counterexample; hypothesis SEARCHES for counterexamples where proof is infeasible (state, strings, corpus-shaped data). Same contracts, two tools.

THE INSTALL: pip package is crosshair-TOOL (a bare `pip install crosshair` grabs an unrelated SSH tool - found the hard way). Both added to requirements.txt under the tooling block.

THE TARGETS (the study's pure functions - the first honest beneficiaries): bench/certify.wilson_interval (the accept/dead math of every certify run) and infra/hf_download's file matchers (find_rung_file, has_safetensors).

TWO REAL FINDINGS ALREADY, ON DAY ONE:
1. CROSSHAIR: wilson_interval had no domain guard - negative n underflows to NaN, k > n breaks the sqrt (math domain error). The callers' tallies are inside the domain by construction, but the contract made it explicit: the guard now returns (0.0, 0.0) outside 0 <= k <= n, n >= 0, z >= 0.
2. HYPOTHESIS: float rounding at p=0/1 drifts the bound outside [0, 1] by ~1e-18 - a CI bound outside the parameter space is nonsense. Clamped: max(0.0, lo), min(1.0, hi).

THE FILES: tests/contracts.py (six contracts - wilson bounds, domain, z=0 degeneracy, the rung-file matcher's membership/token/no-gguf-no-match, the safetensors iff) - ALL PROVED, `crosshair check tests/contracts.py` exits clean. tests/test_properties.py (six properties - bounds, monotone-in-k, z=0 collapse, matcher membership, safetensors iff, all-pass saturation hi=1/lo=1/denom) - 6 passed. 183 tests total.

THE WILSON LESSON registered honestly: my first "all-pass reaches 1" property was WRONG - Wilson's lower bound at k=n is 1/denom < 1 (the honest interval never claims certainty from finite evidence); hypothesis caught it in seconds. The corrected property pins hi=1 exactly and lo=1/denom - a better statement than I first wrote, which is the whole point of the method.

RUN: `crosshair check tests/contracts.py` (proofs, ~1 min) and `python3 -m pytest tests/test_properties.py` (falsification, ~1.4 s). Not a pre-commit hook - the once-in-a-while class, like coverage and vulture.

### Addendum 23 - the verification spread: estimate, KV arithmetic, the law, the cell loaders (2026-10-06, the author's "do it")

THE SPREAD (the addendum-22 close: "good next candidates" - estimate_rung_gib, the law/ceiling functions, the cell arithmetic) is now under contract. tests/contracts.py grows to ELEVEN contracts (all proved): estimate_rung_gib (an estimate, when produced, is positive; no sources, no estimate - never a false skip), kv_gib (non-negative; linear in depth - kv(d)*2 == kv(2d)), law_worst (a positive fit predicts a positive worst-speed), and the three cell loaders (speed/vt/arc: the stored str-keys come back as exactly the stored int-keys - the state's stringly keys never leak).

ONE REAL FINDING, THE BEST KIND: crosshair crashed arc_cells on a corrupt state entry - {'': 0} (a non-numeric run key) kills int() and would take a whole certify run down with it. The state file is loaded JSON; corruption is a real failure mode, not a hypothetical. THE FIX: a shared _int_cells loader in bench/state_store.py - non-dict namespaces yield {}, non-numeric keys/values are skipped (the re-grade never sees them), all three loaders route through it. Crosshair proves the guarded contract; hypothesis pounds it with junk (none, ints, text, lists) and mixed-type dicts.

tests/test_properties.py grows to FOURTEEN properties: the loaders' roundtrip/depth-isolation/guarded/skips-corrupt quartet, kv_gib's linearity and monotonicity in depth, law_worst's positivity and decrease in size, the estimate's none-or-positive. 191 tests total. All gates: pytest 191/191, ty 0, ruff clean, md_check, crosshair ALL PROVED.

### Addendum 24 - crosshair joins the weekly run; the Monday workflow lands as a file (2026-10-06, the author's "to the weekly run it goes")

THE RULING: crosshair is a once-in-a-while tool (the addendum-22 close) and now goes to the weekly run - the author's confirmation. The Monday-midnight schedule had been RULED (coverage, hook-version updates, vulture; mutmut left out as too expensive) but never landed as a file - the audit found no .github/workflows/ at all. This addendum lands it: .github/workflows/weekly-quality.yml, cron 0 0 * * 1 (00:00 UTC Monday) plus workflow_dispatch (the manual trigger, for interrupted evaluations - the author's own use pattern).

THE STEPS, all verified locally before committing: coverage (the missing-test map, a discovery helper never a metric - 191 tests, 68% total), crosshair check tests/contracts.py (the eleven contract proofs, ~1 min), vulture --min-confidence 80 with the repo's artifact directories excluded (the known findings: signal-handler args, test kwargs - the false-positive class, fine for a discovery log), pre-commit autoupdate as a DRIFT REPORT (never auto-bumps: the diff prints HOOK DRIFT for review, nothing changes on its own). The hypothesis properties ride free - they run in the coverage step's pytest.

MUTMUT stays out (the author's "too expensive" ruling, uninterrupted). Nothing in the weekly run blocks commits - artifacts land in the run log for the next session to read.

### Addendum 25 - the full-capacity run: --force-rung (2026-10-06, the author's "all models at (q8, f16, f16) to measure their full capacity")

THE RULING: before any compression thinking, every model measures at its FULL capacity - the study default variant (Q8_0 weights, f16 K, f16 V). Compression starts only when the speed gate is hit; the gate's verdict, not intuition, decides when.

THE GAP: the certify controllers resolved each family's rung from its STORED selection (Phi-3's Q6_K, gemma's Q2_K, Qwen3.5-9B's Q5_K_M...) - selections made by the old blind search, i.e. ALREADY compressed choices. A full-capacity run was impossible without hand-editing state. THE FIX: --force-rung - both controllers take rung_override, applied ahead of the stored selection; without the flag nothing changes (the stored selections still govern). Test test_force_rung_overrides_stored_selection.

THE COMMANDS (the author's machine; the two-command WoW - dry-run pre-flight, then the real run):
  pkill -f llama-server; git pull
  and time python3 full_benchmark.py --certify 2_sigma --task all --force-rung --dry-run
  and time python3 full_benchmark.py --certify 2_sigma --task all --force-rung
  git add results.txt; and git commit -m "full-capacity run"; and git push

READ THIS BEFORE THE RUN: (1) the state carries 9 families, models/ has 8 - the run acquires the missing ones (addendum 20's phase-2 build path handles the safetensors repos). (2) At Q8_0 the big families are HEAVY - Llama-3.1-8B ~8.6 GiB, Mistral-7B ~7.7 GiB, Qwen3.5-9B ~9.2 GiB files, plus KV at depth; the ladder starts at 4,096 and the addendum-35 memory shortcut skips infeasible rungs before download. (3) The speed-dead climb stop (addendum 13) is active: a speed death at rung k permanently skips that family higher - with Q8_0 files the gate bites EARLIER, and those speed-death depths are exactly the compression signal the author wants. (4) Ctrl-C stops the run cleanly (addenda 8/15/17); a re-run resumes from stored cells, nothing re-measures.

### Addendum 26 - cells carry their variant (2026-10-06, the author's "we are going to try different variants for the same model, so let's keep track")

THE QUESTION: does a cell keep record of the model variant (q, k, v) that achieved the score? The honest answer was NO - the four cell namespaces stored only the graded value (stall count, word count, VT partial, ARC correct). The variant lived at FAMILY level (selected rung + the run's kv_quant_k/v), which was recoverable for cells measured under the stored selection - but the addendum-25 full-capacity run made the gap dangerous: a --force-rung Q8_0 cell is INDISTINGUISHABLE from a stored-selection cell in the same namespace, and the never-re-measure rule would silently trust a Q8_0 score for the stored Q6_K run later.

THE FIX, two halves:

(1) STORE: every cell record now carries the variant that measured it - {v: graded value, rung, kv_k, kv_v}. _task_store (the combined controller) and the single-task direct[...] stores route through the same record shape via cell_record. The variant is resolved exactly as the controllers resolve the model (the run's quants, then the tournament entry's, then the state default) - variant_of in bench/state_store.py.

(2) LOAD: the loaders (speed_cells, vt_cells, arc_cells, certify_cells via _int_cells) take the variant being certified (want) and the family's stored selection (legacy). A dict record loads only when its variant matches want; a LEGACY plain-int record - every pre-addendum-26 cell - matches only the stored selection, which is by construction the variant it was measured under (before --force-rung the controllers always ran the stored selection). A non-matching cell is UNMEASURED for the run, never silently trusted; it re-measures under the current variant. No filter (want=None) keeps the old read-everything behavior for discovery views.

THE MEDAL: combined_medal grades the STORED selection's variant only - a forced-rung medal would be meaningless, the medal is the family's certification of its selected config.

TESTS: test_cells_record_and_filter_by_variant (the record shape, the want/legacy filter, the no-filter view, the store's record), plus the three updated assertions on the new record shape. 193 tests total. All gates: pytest 193/193, ty 0, ruff clean, md_check.

### Addendum 27 - the partial-download guard (2026-10-06, the author's "there was an error")

THE ERROR: the full-capacity run died at phase 2 for Llama-3.2-3B - the converter crashed on FileNotFoundError model-00001-of-00002.safetensors, inside the family's own safetensors-source. THE CAUSE: an incomplete download. The repo ships TWO shards; the earlier interrupted run left ONE on disk. Both guards that decide "the safetensors are already here, skip the download" checked only that AT LEAST ONE *.safetensors exists - the partial source passed, the re-download never happened, and the converter died on the missing shard. THE FIX: st_source_complete in infra/hf_download.py - a safetensors-source counts as present only when EVERY shard named in its own model.safetensors.index.json exists on disk (unsharded repos: the single shard; a corrupt or unreadable index is incomplete, never silently trusted). Wired into both guards: the acquire skip check (a partial source now re-downloads) and the post-download verification (a second pass, then a hard fail if shards are still missing), plus the convert-side source check in infra/convert_quant.py. Test test_st_source_complete_guard (empty, unsharded, one-shard-missing, complete, corrupt-index).

### Addendum 28 - the from-scratch reset: param-ascending, on demand (2026-10-06, the author's ruling)

THE NEW RULES: (1) starting from scratch for models - the current state is ARCHIVED (state/benchmark-state-session40-archived.json, git mv, history preserved; to continue the old run later: --state-file that path), (2) the roster is EVERY model registered in models.md - all 48, including the REJECTED (the author's explicit choice: a fresh, machine-measured verdict for every registered model), (3) the order is BY PARAMETERS, ASCENDING - granite-4.0-350m first, GLM-4.5-Air last, (4) the downloader stays ON DEMAND: the orchestrator hands it specs one family at a time in this order, nothing is fetched ahead of need (already true - phase 1 runs per family inside the certify loop).

THE PARAMETER COUNTS: etc/registry_data.py grows params_b - parsed from the roster name where the name carries the size (0.8B, 350m...), explicit in PARAMS_B_OVERRIDE for the names that don't (phi-1 1.3B, phi-2 2.7B, the Phi minis 3.8B, the granite micros 7B, Jamba2-Mini 12B, Ling-lite 16.8B, GLM-4.5-Air 106B - model-card totals, MoE counts declared TOTAL not active). params_sorted_roster is the registry order; the registry check flags any roster model without a count (UNKNOWN: none today - all 48 counted).

THE ORCHESTRATOR: with no positional specs the families come from the state file as before - but now re-sorted param-ascending (param_ascending_specs; unregistered repos sort after the counted ones, by name, never silently mixed in); and when the state is FRESH - no family ever entered - the roster IS the registry's param-ascending list (the full-registered-roster fallback, stamped in the run log). etc/ becomes a package (__init__.py) for the import. Tests: test_param_ascending_selection (the spec sort, the roster completeness, the ascending invariant, the first-three order). 195 tests total. All gates: pytest 195/195, ty 0, ruff clean, md_check, registry check.

THE RUN (the author's machine; the state file is fresh - the roster fallback fires):
  pkill -f llama-server; git pull
  time python3 full_benchmark.py --certify 2_sigma --task all --force-rung --dry-run
  time python3 full_benchmark.py --certify 2_sigma --task all --force-rung
  git add results.txt; git commit -m "param-ascending from-scratch run"; git push
NOTE: at Q8_0 the roster's big models (Qwen3-30B, EXAONE-32B, GLM-4.5-Air 106B) are far over the machine's RAM - the addendum-35 memory shortcut skips infeasible rungs before download, and phase-A per-family isolation (addendum 78) records the failure and CONTINUES; their small-param cousins run first, as the author ordered.

### Addendum 29 - the new WoW: params from HF, never guessed (2026-10-06, the author's ruling)

THE RULING: (1) never guess a model's parameter count - RETRIEVE it from HF; (2) the goal is fast data acquisition - small rungs and small models first, NO hidden selection mechanism favoring any model, a super-easy next-pick; (3) difficulty tuning comes later - start with the current bars, adjust from the results.

THE RETRIEVAL: the name-parsing and the hand-declared override table from addendum 28 are DELETED. etc/registry_data.py fetches the counts from the hub: (1) safetensors repos - model_info's safetensors.total, the EXACT tensor count HF itself sums; (2) the three bin-only repos (MiniCPM-1B/2B-sft, MiniCPM3-4B) - HF exposes no tensor count for pickles, so the count is the exact pytorch_model.bin SIZE divided by the storage width the repo ships (bf16, 2 bytes/param) - a retrieved-from-HF value with an auditable derivation. Each entry records params_b AND params_source; the registry check fails when any roster model has no retrieved count (params not retrieved from HF: none today).

THE CORRECTIONS the real counts made to the guesses: Jamba2-Mini is 51.57B (not 12B), the granite micros are 3.19/3.40B (not 7B), phi-1 is 1.42B (not 1.3B), Hunyuan-A13B is 80.39B total. The order's head: granite-4.0-h-350m (0.34B), granite-4.0-350m (0.35B), MiniCPM4-0.5B (0.43B), Qwen3.5-0.8B (0.87B) ... tail: GLM-4.5-Air (110.47B). 45/48 via safetensors.total, 3 via bin size; all 48 recorded in the store, checked in.

THE MECHANISM (item 2, unchanged in shape, now honest in counts): the order is PARAM-ASCENDING x RUNG-ASCENDING - the smallest model at the smallest rung is always next; nothing about a family's history, promise, or ranking moves it. Test updated: test_param_ascending_selection asserts the retrieved sources and the new head order. 195 tests total. All gates: pytest 195/195, ty 0, ruff clean, md_check, registry check.

THE RUN (unchanged from addendum 28, the counts only reorder it):
  pkill -f llama-server; git pull
  time python3 full_benchmark.py --certify 2_sigma --task all --force-rung --dry-run
  time python3 full_benchmark.py --certify 2_sigma --task all --force-rung

### Addendum 30-31 - the f16 first pass, no cold starts, partial data ASAP (2026-10-06, the author's rulings)

RULING 1 (30): the first run covers how far we get at (f16, f16, f16) - full-precision weights AND full-precision KV. f16 is now a FIRST-CLASS RUNG: find_rung_file resolves a shipped f16 GGUF as the rung file (the old code skipped f16-named files as 'the quantize source' - that exclusion applies to QUANT rungs only), RUNG_BITS carries f16 = 16.0 (the feasibility estimate prices it honestly - most families will skip as infeasible before download, which IS the measurement), and convert_quant.create returns the f16 ITSELF for the f16 rung - no quantize step, no wasteful f16->f16 copy. The command is --force-rung f16.

RULING 2 (30): no cold starts. The RAM data comes from llama-server's own accounting (the -lv 5 memory breakdown, session 39 addendum 11), so the posix_fadvise cache-drop ritual before every launch is DELETED - all four sites (the speed cell, the FWE cell, the VT cell, and speed_gate.bench_model). The only thing cleaned between tests is the context: each cell launches its own server with its own -c and tears it down after; nothing else is evicted. The warm MemAvailable delta stays recorded per launch (harmless, cheap); drop_file_cache the FUNCTION stays in llama_server (unused by the bench path, still available for a one-off cost measurement).

RULING 3 (31): partial data ASAP. Every VERDICT - a family's medal (accept) or its death (dead) at a rung - commits and pushes the artifacts IMMEDIATELY (the same set as the git tail: state, results.txt, dumps, sidecars, logs), so the run is watchable from the repo while it runs. The hook: on_verdict callbacks on both certify controllers, fired after the entry lands, wrapped so a git failure NEVER stops the run (the tail catches the remainder); --no-git and dry runs opt out. The tee is uninstalled for the commit and reinstalled after (results.txt complete on disk at commit time).

Tests: test_f16_is_a_rung (resolution, the 16-bit estimate, create-returns-the-f16), test_verdict_hook_fires_on_accept_and_dead (the hook fires on accept, never blocks). 197 tests total. All gates: pytest 197/197, ty 0, ruff clean, md_check.

THE RUN (the f16 first pass - most families will skip as infeasible at f16; the ones that run are the real full-capacity frontier):
  pkill -f llama-server; git pull
  time python3 full_benchmark.py --certify 2_sigma --task all --force-rung f16 --dry-run
  time python3 full_benchmark.py --certify 2_sigma --task all --force-rung f16

### Addendum 32 - the per-test wall seconds (2026-10-06, the author's ruling)

RULING: the cell keeps the time per test. Every stored cell record now carries {t} - the WALL SECONDS the test took, rounded to 0.1s - so the expensive tests are visible and the cheap ones are too.

THE PLUMBING: _task_measure (bench/state_store.py) wraps each cell task in time.time() and returns the seconds as a fourth element; _task_store persists them into the record ({v, rung, kv_k, kv_v, t}); cell_record (the single-task controllers' writer) gains the same seconds parameter. The combined controller prints the seconds inline ([12s] in the cell line). Legacy records without {t} read as t=None - they predate timing; plain-int records (no variant) stay plain-int. The loaders/verdict math are untouched - {t} is bookkeeping, never a gate.

Tests: test_cell_record_carries_wall_seconds (the record shape, the rounding, the None, the plain-int legacy), the five _task_measure fakes and the direct-cell assertion updated for the fourth return element and the new record shape. 198 tests total. All gates: pytest 198/198, ty 0, ruff clean, md_check.

THE RUN (addendum 32 corrections, the author's rulings): the git tail is GONE - addendum 31's on_verdict hook commits and pushes every verdict already, a manual git tail is redundant; `time` is GONE - the per-test cost is now IN the records ({t}), the runner-pay seconds are the measurement. The command is just:

  pkill -f llama-server; git pull
  python3 full_benchmark.py --certify 2_sigma --task all --force-rung f16 --dry-run
  python3 full_benchmark.py --certify 2_sigma --task all --force-rung f16

### Addendum 33 - --force-rung takes the rung (2026-10-06, the f16 dry-run 404)

THE FAILURE: `--force-rung f16 --dry-run` died with huggingface_hub's RepositoryNotFoundError for `api/models/f16` - the rung name was queried as an HF REPO ID. The cause was argparse, not the hub: --force-rung was a store_true FLAG (addendum 25), so `f16` was swallowed as a POSITIONAL FAMILY SPEC and reached the downloader as `model_repo="f16"`. The author's natural typing of the command was never valid; the fix makes it valid.

THE FIX: --force-rung now takes an OPTIONAL value (nargs="?", const=True, default=False). `--force-rung f16` == `--rung f16 --force-rung` (main() folds the value into args.rung); bare `--force-rung` keeps the addendum-25 meaning (certify every family at --rung, default Q8_0); a spec-shaped value (`/` or `=` in it) is rejected LOUDLY ("--force-rung takes a RUNG (e.g. f16, Q8_0), not a family") - never silently a rung or a family. Note: with positional families after the flag, prefer `--force-rung f16 fam1 fam2` order or the explicit `--rung f16 --force-rung` form; the guard catches the spec-shaped mistake either way.

Tests: test_force_rung_takes_optional_value (the f16 fold, the bare flag, the --rung override, the spec-shaped guard). 199 tests total. All gates: pytest 199/199, ty 0, ruff clean, md_check.

THE RUN (corrected - same as addendum 30-31, now actually typeable):
  source .venv/bin/activate.fish
  pkill -f llama-server; git pull
  python3 full_benchmark.py --certify 2_sigma --task all --force-rung f16 --dry-run
  python3 full_benchmark.py --certify 2_sigma --task all --force-rung f16

### Addendum 35 - the simplification: ONE mode (2026-10-06, the author's ruling)

THE REFLECTION: tests, annotations, formal verification - and the benchmark still failed to START three times (the venv check, --force-rung f16 swallowed as a family spec, the promise sort re-ordering the param-ascending queue). The diagnosis: every failure lived in the ORCHESTRATION layer - main(), the parser, the flag wiring - and no test ever executed main() with a real argv. The toolbox verified the layers below the entry point; the entry point itself was untested.

THE CUT (the author: "cut outright"): full_benchmark.py is the CERTIFY orchestrator, period. The legacy modes are deleted - the ladder sweep (process_family, sweep_families, run_ladder, the phases 1-4 protocol), the tournament (--tournament, tournament_family, tournament_rank, fwe_flicker, rescore), --diagnose, --size-table, the run-time estimator, preflight_report's sweep-specific report, prepare_roster. bench/ladder.py, bench/tournament.py, bench/size_table.py, tests/test_estimator.py deleted; the legacy-mode tests cut; 1406 -> 519 lines, 27 flags -> 13. The tournament CSV readers stay (bench/tournament_helpers.py) - the store re-grades legacy cells from the committed CSVs. History is in git.

THE NEW GUARD: test_main_startup_smoke - main() runs END-TO-END with --dry-run, everything below the preflight faked (no network, no server, no hub). The exact command the author types is now a test: the registry fallback order, the --force-rung f16 fold, the roster's param-ascending handoff, the on_verdict opt-outs. The three failure classes that slipped through are now structurally covered.

THE STATE: ladder-state.json's families are readable (the certify path's variant filters and CSV re-grading unchanged); the archived state files stay. 168 tests total. All gates: pytest 168/168, ty 0, ruff clean, md_check.

### Addendum 36 - always 2 sigma; the medals are consequences (2026-10-06, the author's ruling)

THE RULING: "get rid of the --certify flag. we always certify to 2 sigma: dead, 0.5 sigma and 1 sigma are consequences, not goals." The --certify LEVEL flag is DELETED; certification is ALWAYS the 2-sigma bar (z=2, Wilson lower bound >= 0.50, floor 10 of 20 cells). The controller accepts at that bar and nothing else; a candidate that cannot reach it is dead.

THE CONSEQUENCES, DERIVED: combined_medal (unchanged math) grades the STORED evidence after the run - a clean accept is 2_sigma, weaker evidence grades 1_sigma or 0.5_sigma, none grades dead. The tiers were never separate goals; they are what the evidence says once the 2-sigma question has been asked.

THE MECHANICS: both controllers lose the level parameter; CERTIFY_LEVELS and the at_least_one branches are deleted (bench/constants.py, bench/certify.py); CERTIFY_Z / CERTIFY_BAR / CERTIFY_FLOOR are the single-sourced fixed bar. The entry dicts record level: "2_sigma" as a label of what was asked. Tests: the two at_least_one tests cut (the mode is gone), the VT early-reject updated (6 consecutive fails kill at the 2-sigma bar, best 14/20 -> lo 0.477 < 0.50), the medal test updated (a clean accept grades 2_sigma - derived, not requested). 166 tests total. All gates: pytest 166/166, ty 0, ruff clean, md_check.

THE RUN (one flag fewer):
  source .venv/bin/activate.fish
  pkill -f llama-server; git pull
  python3 full_benchmark.py --task all --force-rung f16 --dry-run
  python3 full_benchmark.py --task all --force-rung f16

### Addendum 37 - the five rulings: the v4.x conformance pass (2026-10-06, the author's rulings)

THE SURVEY asked "what else can be simplified or removed? Where are our weak spots in testing and formal validation?" - and the author ruled on five points. This addendum executes the five rulings.

RULING 1 (the stall-rate gate): "obsolete in v4.x, make it conform." The speed verdict is STRICTLY worst wps >= the reader line (5.0), k=1, one conversation per cell, n=21. The stall-rate tolerance is gone as a gate: bench/cells.py's speed check accepts on worst wps alone (the ceiling-rung diagnostic stays); speed_gate.analyze()'s verdict is strictly worst_wps >= reader_wps; the reader-wall collision simulation (addendum 55) is recorded per turn as DATA (stall_rate, catchup_s, first_catchup_word_frac) - never a gate. STALL_RATE_MAX stays only as the recorded config of the diagnostic.

RULING 2 (corpus building): "may be needed still... make it conform to 4.x protocol." bench() and the bench-CLI sweep are DELETED from speed_gate.py (the bench path is bench/cells.py's library, called inside the certify controllers); the CLI keeps only the corpus builders (--make-sample, --make-corpus).

RULING 3 (single-task certify): "not for a run - the orchestrator decides what needs to be run based on the cell content." Unchanged: the single-task certify controllers stay exactly as they are.

RULING 4 (the artifacts): "the html are live, they are the main artifact of the study. files.txt is obsolete. the log files, no idea." files.txt deleted; lineage2-ladder.log and overnight-lineage.log deleted (both recoverable from git history if ever wanted); cpu-picker.html and gpu-picker.html stay - the study's main artifacts.

RULING 5 (dead code): "fix." TOURNAMENT_MODEL_QUANTS / TOURNAMENT_KV_QUANTS (bench/constants.py), QUERY_TEMPLATE (ruler_gate.py), drop_file_cache (infra/llama_server.py) deleted. Three obsolete dump-reuse tests cut (they exercised the deleted bench()).

Tests: 163 total (the three dump-reuse tests cut with the bench path). All gates: pytest 163/163, ty 0 (only the sandbox's missing huggingface_hub/pyarrow imports), ruff clean, md_check, vulture clean (the sigint handler's required signum/frame signature aside). Sanity: analyze() verdicted on correct-shape dumps - worst 2.50 wps -> FAIL, worst 20.00 wps -> PASS (confident), stall_rate present as data both times.

ADDENDUM 37 CORRECTION (the author's follow-up): STALL_RATE_MAX is deleted entirely, with the stall_rate_max field of analyze's return - "we don't use it anymore. the decision of pass fail is sharp in the script. for the benchmark is about the medal it gets." The stall_rate stays as recorded data; there is no threshold anywhere.

### Addendum 38 - the survey's second round: the AI tools move, the verdict-path tests, and a REAL BUG found (2026-10-06, the author's rulings a-e)

THE RULINGS: (1) the root one-off analysis scripts stay pending review - the author needs to know what they do first; (2) md_check stays (a lightweight GFM linter we wrote), js_check may be replaced by another tool - suggestions pending; (3) code_edit.py and code_search.py move to AI_tools/ - the root is study-only; (4) the git tail stays - a bug's clue can live in the non-verdict artifacts; (5) bench/tournament_helpers.py explained to the author, its fate pending; (a) cell-level verdict-path tests: DO IT; (b) the accept/medal invariant: DO IT; (c) hypothesis properties for the store roundtrip and the medal's monotonicity: DO IT; (d) fake-hub tests for hf_download: DO IT; (e) the SIGINT handler: already covered (test_sigint_shutdown_sequence, test_sigint_during_acquire_stops_the_run).

THE MOVE (ruling 3): code_edit.py and code_search.py now live in AI_tools/; a root conftest.py puts AI_tools/ on the test path (the tests import them as before); pyproject's mutmut source_paths updated. The root is study-only again.

THE BUG (ruling b found it): combined_medal graded speed cells with `p >= TASK_PASS_BARS["speed"]` - and the speed bar is 0, so EVERY cell passed the medal's speed grade (a stall count is always >= 0), while the controller's own _task_load grades speed as `p == 0` (0 stalls = gold). A family whose EVERY speed cell failed still medalled 2_sigma. The two implementations of the same question had drifted exactly as feared; the invariant test (a clean 20/20 accept must grade 2_sigma, a all-speed-failed state must grade None) caught it. Fix: the medal grades speed at the equality bar, the same gold bar the loader grades at.

THE NEW TESTS (tests/test_verdict_path.py, 17 tests): the cell verdict path with fakes below the measurement seam - speed_pass verdicted strictly on worst wps (4.9 FAIL, 5.0 PASS, the ceiling_rung headroom band [5, 7.5)), the window-cap and floor structural refuses, speed_cell's stall-count record, analyze() on real dump files (stall_rate present as data, no threshold field anywhere), the accept=>2_sigma invariant, the equidistant-bar check per task, and the fake-hub acquire branch table (the rung-file download, the addendum-35 infeasible-before-download shortcut, the dry-run-downloads-nothing contract, the f16 plan, the addendum-27 partial-safetensors redownload, the empty-repo phase-1 fail, the addendum-30 quant-never-resolves-as-f16 catch).

THE PROPERTIES (ruling c): test_task_store_roundtrip (a stored cell loads back exactly - value, variant, {t} - through every task's loader) and test_combined_medal_monotone_in_evidence (turning failing cells into passes never lowers the tier). 182 tests total. All gates: pytest 182/182, ty 0 (sandbox missing hf/pyarrow only), ruff clean, md_check, vulture clean.

### Addendum 39 - ruling 5 executed: the tournament inheritance is deleted (2026-10-06, the author's ruling)

THE RULING: "remove it, it is obsolete." bench/tournament_helpers.py - the CSV reader that re-graded inherited tournament-fall cells from their committed climb CSVs - is deleted, and with it the whole inheritance path: certify_cells loses its models_dir/fam parameters and the tournament_falls loop (every cell is the certify run's own); _task_load's FWE wrapper and certify.py's caller updated. The roots scripts stay (ruling 1: "leave the scripts alone, I don't know what to do with them yet"); js_check stays (ruling 2: "keep it"). The tournament_entry fallback in variant_of/stored_variant STAYS - that is the live state's stored-selection field, not the CSV inheritance.

Tests: the two inheritance tests cut (test_certify_cells_inherit_from_falls, test_certify_cells_regrades_inherited_from_csv); the accepts_and_skips/dead/2-sigma-dead/vt tests reseeded on direct certify records instead of falls (the cell evidence the v4.x protocol actually stores). 180 tests total. All gates: pytest 180/180, ty 0, ruff clean, md_check, vulture clean.

### Addendum 40 - pre-registered: the missing ~25% of the bandwidth story, and the (k,v) scaling ladder (2026-10-06, the author's ruling + discussion)

THE CONTEXT: the f16 first pass ((f16,f16,f16), full capacity, param-ascending) is running. Its purpose: per-model wps degradation curves, the RAM ceiling where the speed gate bites, and the census + wps tuples that let us extrapolate above and below our 102.4 GB/s machine - the practitioner-recommendation layer of the study.

THE DECOMPOSITION (the discussion): decode cost per token has TWO depth-linear terms - the bandwidth term (bytes moved per token = weights(q) + KV(R)*bits/16) and the COMPUTE term (attention FLOPs over every cached position, also linear in R). So far the bandwidth story explains ~75% of the observed wps; the author's hypothesis: the missing ~25% is compute.

PRE-REGISTERED PREDICTIONS (framed BEFORE the ladder data exists, so the answer cannot be fitted to the result):

P1 (the discriminator - the (k,v) quant separates the terms): shrinking (k,v) f16->q8_0 HALVES the bandwidth term's depth-linear part but leaves the attention FLOPs unchanged. IF the missing ~25% is compute, a KV halving recovers LESS than the one-rung-of-speed the pure-bandwidth model predicts - and the shortfall IS the compute term, measured directly. If KV halving recovers exactly the bandwidth share, the residual is elsewhere (prefill interference, memory latency at larger working sets, TLB/page-table effects on system RAM).

P2 (the cheaper check, from the f16 pass alone): fit 1/wps(R) = a + b*R per family (pure bandwidth: a = weights bytes, b = KV bytes). The intercept predicts wps(0) ~= B/weights; if the MEASURED flat-context speed (the 4k rung, negligible KV) is already below B/W, part of the residual is depth-INDEPENDENT per-token compute (dequant, GEMM over weights - real on CPU), not the attention term. Depth-dependent residual beyond the KV-byte prediction = attention compute. NOTE: the f16 pass ALONE cannot separate the two linear-in-depth terms - the (k,v) ladder (P1) is the separator.

THE SCALING LADDER (the rule, pre-registered - a rule the orchestrator walks, not a hidden selection): when a model dies at the speed gate at rung R, the forward path is the (k,v) lever FIRST, then (q):
  1. (f16, f16, f16) dies at R
  2. (f16, q8_0, q8_0) - halves KV: exactly one rung of memory headroom, plus reduced attention bandwidth (may recover speed at R itself) - THE FIRST MOVE at every speed-gate death
  3. (f16, q4_0, q4_0) - quarters KV: two rungs
  4. asymmetric (f16, q8_0, q4_0) etc. - K and V tolerances differ (KIVI et al.); which side degrades less is an empirical question our cells answer per family
  5. only when KV is exhausted: (q8_0, ...) - the one-shot lever, paid on every task, LAST because it degrades the QUALITY axes (FWE/VT/ARC), not the depth axis
Why (k,v) first: the KV term is what DOUBLES each rung, so it is the rung-climbing lever; (q) buys a fixed GiB amount once. The memory equation total(R) = weights(q) + KV(R)*bits(k,v)/16 + compute is depth-separable, and every census already records its three terms per launch.

PRACTITIONER IMPLICATIONS (pre-registered): if P1 confirms compute, the recommendation flips qualitatively - on slower-bandwidth systems the KV quant is the dominant lever (memory-bound), on faster systems the compute ceiling dominates and NO quant helps (the crossover). Extrapolating BELOW our bandwidth is interpolation on the fitted slope (safe); extrapolating far ABOVE may hit the compute ceiling and flip from the memory story to a FLOPs story. The death-run patterns across families will locate the crossover.

FUTURE OPTIMIZATIONS (parked, the author's ruling "we can look it up later"): ARC could run first on a family's first cell (cheapest launch, hard kill); fwe+vt share the identical server shape (-c rung --parallel 1) and could ride ONE launch per cell - the biggest single amortization of the ~4 launches per cell; check the {t} records once the run produces them.

### Addendum 41 - the live run status on the picker page (2026-10-06, the author's ruling)

THE RULING: "start updating the web pages with this info. It helps me visualize too." run_status.py: reads the state file + results.txt the run is already committing (addendum 31's verdict pushes), derives the per-family verdict table for the CURRENT f16 pass, and rewrites the <div id="runStatus"> panel in cpu-picker.html in place - idempotent, regenerate with `python3 run_status.py`. The kill task is taken from the DEAD block immediately BEFORE each family's own verdict line (a later family's DEAD must not leak into an earlier family's row - tested).

THE EARLY PICTURE it visualizes (18:12, seven families in, all param-ascending): every family so far is DEAD at the 4,096 rung, and NONE on speed - the small models die on the QUALITY tasks, spread across the board: fwe kills granite-4.0-h-350m and MiniCPM5-1B, vt kills granite-4.0-350m and gemma-3-1b-it, arc kills MiniCPM4-0.5B, Qwen3.5-0.8B (2/8, the only non-zero tally) and Llama-3.2-1B-Instruct. The ARC early-reject is doing its job (6-8 cells, then dead - never 20). Note for the scaling discussion: the first pass measures MAX quality - a small model dying on quality at f16 will not be saved by ANY quant; the compression ladder only matters for models that survive quality and hit the SPEED gate. The interesting families are still ahead (the 1B+ tier and up).

### Addendum 42 - live_status.html: the standalone run page, with the gates' difficulty (2026-10-06, the author's ruling)

THE RULING: "better not mess up with the html. Create live_status.html for this info. Put also the difficulty in each gate." The runStatus panel is REVERTED out of cpu-picker.html (the picker pages are the study's polished artifacts - no generated content in them); run_status.py now writes a STANDALONE live_status.html, wholesale and idempotent: the four gates' difficulty panel (speed: strictly worst wps >= 5 with 0 stalls; fwe: >= 2 of 3 hidden words; vt: all 5 values across 4 hops; arc: >= 4 of 5 questions - plus the 2-sigma certification note), then the per-family verdict table in evaluation order with the kill task and last tally. Tests updated: extraction (the DEAD-block-before-the-family's-verdict ordering) + the standalone-page shape (gates panel present, idempotent render).

### Addendum 43 - difficulty = the kill rate (2026-10-06, the author's clarification)

THE CLARIFICATION: "for difficulty I meant kill rate." live_status.html's difficulty panel is now the per-gate KILL RATE, scoped to the current f16 pass (the pass's first --force-rung f16 header is the scope start - older runs in results.txt must not leak in; tested): families killed per gate, cells passed/measured, and the pass rate. The first picture (9 families in): arc is the most lethal gate so far (3 kills, 9% cell pass rate), then fwe (2, 58%) and vt (2, 30%), with speed trailing (2, 79%) - the sub-1B tier dies on quality, exactly as the full-capacity pass predicts. Two counting bugs caught by the pre-push hook's pytest before anything shipped: the tally regex demanded a literal trailing space after the k/n counts, and the panel SUMMED the cell lines' k/n - which is a RUNNING tally, double-counting every cell (the committed fixup regex and a second fix, respectively). The counting is per-CELL: each `cell N (rung R) task: ... -> PASS/FAIL` line contributes one measured cell, one pass if PASS; the k/n running tallies are never summed. The corrected panel (10 families in): speed 2 kills / 51 of 63 cells = 81%, fwe 2 / 39 of 63 = 62%, vt 2 / 22 of 63 = 35%, arc 4 / 4 of 63 = 6% - arc remains the most lethal bar by far, and the sub-1B tier dies on quality exactly as the full-capacity pass predicts. The panel updates as the run climbs.

### Addendum 44 - the recalibration trigger: the speed wall, not the panel (2026-10-06, the author's ruling)

THE RULING: "I like it. Indeed I'm planning to recalibrate at the moment models start hitting the speed wall. We're still far from it." The >= 50% aggregate-pass floor (session 38, addenda 12-13 - "if k needs to become zero to do so, we have a problem") stays the calibration principle, but its application point is now FIXED: the bars are recalibrated when the f16 pass starts producing SPEED-GATE deaths, not before. Rationale on record: the sub-1B tier's low arc pass rate (4/63 cells, addendum 43) is the expected full-capacity signal - a small model dying on quality will not be saved by ANY quant, so adjusting the arc bar on sub-1B-only data would calibrate to the weakest cohort. The discriminating regime for the QUALITY bars is the tier where models survive quality and the speed gate becomes the binding constraint; that is where the floor rule is re-applied (per gate, on the completed pass's aggregate, free re-grade from the stored x/k records - no re-measurement).

### Addendum 45 - infeasible: the trained window is out of the benchmark, not a speed death (2026-10-06, the author's rulings)

THE INVESTIGATION: three "speed" deaths at 4,096 looked weird (the author: "very weird for a model to die this early to the speed gate"), and the logs split them. phi-1: n_ctx_train 2,048 - the server capped -c 4352 down to 2,048 (the addendum-130e guard fired), every task HTTP-400'd ("request (3994 tokens) exceeds the available context size"), ZERO turns ever ran. MiniCPM-1B-sft-bf16: the same disease at n_ctx_train 4,096 (the rung needs 4,352 = 4,096 + 2x128 answer headroom; one headroom increment short). granite-4.0-1b: the only GENUINE speed death - n_ctx_train 131,072, full 4,352 ctx honored, real turns benched: 21.6-22.0 t/s best turns but collapses to 0.1-1.8 w/s with 2-5 wall-failing turns per conversation.

THE RULINGS: (1) "If the model doesn't even support 4k of context is out of the benchmark, don't count their statistics." A NEW VERDICT - infeasible: when the launch's banner shows the trained window below the rung's ctx, the family is OUT (never 'dead', never re-attempted at any rung - the cap only gets worse higher), zero cells in its entry, and neither its kills nor its cells (all FAIL-by-400) enter any statistic. The state records fst["infeasible"] = {window_cap, depth}; both controllers (combined and single-task) raise/record/skip on it; the verdict commits like any other (addendum 31). The two already-benched families are marked in the state retroactively (phi-1 window 2,048; MiniCPM-1B-sft window 4,096) - their stored FAIL cells remain in the state as raw data but the live panel cuts them. (2) granite-4.0-1b's speed death STANDS ("still is a result, so it goes to the statistics") - the author will manually probe it; the corrected panel (addendum-43 counting, infeasible excluded): speed 1 kill / 61 of 67 = 91%, fwe 2 / 63%, vt 2 / 43%, arc 5 / 10%.

IMPLEMENTATION: bench/state_store.WindowCap (raised by _task_measure on the cap error - speed, fwe and vt branches), the verdict path tested (test_window_cap_makes_the_family_infeasible_not_dead: verdict infeasible, zero cells, state record, never re-attempted); run_status.infeasible_families() detects the capped blocks (130e error + verdict line) and gate_kill_rates() cuts them before counting (tested: the capped family's PASS cell, FAIL cells and kill all vanish). 185 tests.

### Addendum 46 - the granite-4.0-1b investigation: fast degeneration, not slow generation (2026-10-06, the author's confirmation)

THE INVESTIGATION (the author: "Investigate granite-4.0-1b"): the per-turn dumps split the death cleanly. The SERVER IS FAST - every turn in all six cells streamed at a rock-steady 21.7-22.8 t/s (no stalls, no Vulkan noise). The OUTPUT IS DEGENERATE: the failing turns generate the full 299-token budget while containing 1-8 WORDS - cell 4 turn 2 is gen_tokens=299, gen_words=1 (a single unbroken subword stream); the deltas show words arriving at ~1/s. The fwe/vt CSVs show the same openly: "Her Her Her Her..." / "Overing Overing Ucept Ucept So..." - token soup. The reader-wall verdict is honest: you cannot read 299 tokens carrying one word of meaning, and the wps metric collapses as a CONTENT failure, not a bandwidth failure.

THE MECHANISM (the hypothesis, on record): granite-4.0-1b is a hybrid SSM (Mamba-2) - 5 of 9 early families are SSM/recurrent, the known law-exception architecture. The pattern fits SSM state degradation over 4k: early turns coherent (cell 5 turns 1-3: 20-22 real words/s), later turns collapse into subword repetition; the same degeneration kills its arc (0/6). The dense twin granite-4.0-h-1b produces readable text at the same depth and died on arc at 1/7 instead - consistent with the architecture story, not a per-family quirk. A cheap manual probe (the author's to run): short plain chat at 512 ctx - coherent there, degenerate at depth = state-length degradation confirmed.

THE AUTHOR'S CONFIRMATION AND RULING: "Your assessment is correct. It doesn't work at 4k." THE BENCHMARK IS NOT ADJUSTED for any model - unless the adjustment is something MINOR that applies across the board, like verbosity in the answer (the author's precedent). granite-4.0-1b's death stands as a genuine, reportable finding: the hybrid's SSM state cannot carry 4k tokens at 1B scale - exactly the kind of practitioner-facing answer the study exists to produce. The panel at this point (19 families, infeasible excluded): speed 1 kill / 94%, fwe 2 / 73%, vt 4 / 52%, arc 9 / 18% - the 1-2B tier keeps dying on quality, still no depth-driven speed wall.

### Addendum 47 - the disqualified row: the kill table carries the roster total (2026-10-06, the author's request)

THE REQUEST: "Add to the kill table the disqualified families, so it reflects the actual total." The kill-rate panel gains a DISQUALIFIED row (trained window below the first rung, addendum 45): kills + disqualified = the roster's actual verdicted total (now 20 + 5 = 25), while the disqualified cells and kills stay out of every per-gate statistic - the row makes the panel add up without contaminating it. Fix that shipped with it: infeasible_families() and the segment cutter now pair the 130e cap error with its verdict per VERDICT SEGMENT (a verdict line closes each family's block), not per run header - a header block holding two verdicts previously mis-attributed the cap; the cutter is linear (bounds from the verdict matches), no backtracking regex. 186 tests.

### Addendum 48 - disk headroom: watched on the page, gated before the f16 write (2026-10-06, the author's rulings 1+2)

THE ASK (the author's "do 1 and 2" over the disk-coverage survey): (1) the live page carries the machine's free disk - run_status.disk_free_gib() (statvfs at the repo root) renders a line under the subtitle: "free disk: 51.6 GiB (the f16 pipeline needs ~the source size free per family)". The f16 write is the pipeline's TRANSIENT PEAK - the safetensors source and the f16 gguf live together until the verified delete (addendum 42) - so the free space is run-relevant, not trivia. (2) convert_quant.create() now HARD-GATES the f16 conversion on disk: the source's on-disk size (the f16 is roughly its tensor payload) must be free BEFORE the converter starts - a refusal fails phase 2 loudly (the idempotent rerun resumes there), because a mid-write death would leave a partial gguf that a later run's local_rung could trust as a real rung file. The acquire-phase check stays advisory (local files may already exist); the conversion check cannot be - it is the last point before the peak. Tested: the low-disk refusal raises before any gguf exists. 187 tests.

### Addendum 49 - the base Qwen3-4B is off the roster (2026-10-06, the author's ruling)

THE RULING: "Keep only the instruct version. It is the better suited for the benchmark, right?" - yes: the type rule (session 35, addendum 18) is that only INSTRUCT models suit this benchmark (both gates are instruction-shaped), and Qwen3-4B is the base/pretrained tune. Removed from both registry stores (etc/registry_data.json's params entry + etc/registry_data.py's ROSTER); Qwen3-4B-Instruct-2507 (4.02B) stays. The roster is 47 families. Note: docs/models.md's REJECTED-table row for the base Qwen3-4B is historical screen evidence (the 256k-era ceiling reject) and stays as-is - the registry is the live roster, the doc is the record.

### Addendum 50 - the disk line names its host (2026-10-06, the author's catch)

THE CATCH: "I see there is 80 GB of disk. Maybe measuring the wrong partition?" - not a wrong partition, a wrong MACHINE: the page had been regenerated in the sandbox (which pulls the run's artifact commits and rewrites live_status.html), so the addendum-48 disk line was reporting the SANDBOX's 45.6 GiB of a 59 GiB disk, posing as the benchmark machine's headroom (the author's machine has 80 GB and clearly more free than the line claimed). The fix: the line names its host - "free disk: 45.6 GiB on <hostname>" plus a footnote that the page travels and the number belongs to whichever machine regenerated it. The addendum-48 hard gate (convert_quant's pre-conversion check) is unaffected: it runs ON the benchmark machine inside the run itself.

### Addendum 51 - the roster is CUT at gemma-4-e2b-it; the run stamps its own disk (2026-10-06, the author's rulings)

THE CUT: "Cut the list at gemma-4-e2b-it, the rest will not fit." The roster is now 38 families, ending at gemma-4-e2b-it (5.12B). Everything above it - Llama-3.1-8B (8.03B), Qwen3.5-9B (9.65B), Ling-lite (16.8B), gpt-oss-20b (20.9B), Qwen3-30B-A3B (30.5B), EXAONE-4.0-32B (32.0B), AI21-Jamba2-Mini (51.6B), Hunyuan-A13B (80.4B), GLM-4.5-Air (110.5B) - cannot fit the f16 pipeline on the author's 80 GB disk: the conversion's transient peak is source + gguf together (~2x steady-state), so from Ling-lite's ~67 GiB peak upward there is no headroom; the sub-10B stragglers (Llama-3.1-8B ~32, Qwen3.5-9B ~39) fit technically but were cut with the block per the author's disk ruling. Removed from BOTH registry stores (ROSTER + the JSON store); the models.md rows stay as the geometry record of what was cut. The state file holds only families below the cut, so the saved-specs path and the fresh-roster path agree.

THE DISK STAMP: "Do the hard disk space reporting in full benchmark, so it reads my disk." full_benchmark stamps the RUN'S OWN disk reading into the state file at startup - state["disk"] = {free_gib, host, at} - so the live page always reports the benchmark machine's headroom no matter which machine regenerates it (the addendum-50 host-naming was the patch; this is the cure: the number itself travels with the run's commits). run_status.run_disk() prefers the stamp and renders "free disk: X GiB on <host> (the benchmark machine's own reading, stamped by the run at ...)"; the local statvfs reading is the fallback only, for a state file with no stamp yet.

### Addendum 52 - the arc gate recalibrates to 4/5: the first kill-rate adjustment (2026-10-06, the author's ruling)

THE DATA (the addendum-43 panel, 186 cells, infeasible excluded): speed 82% per-cell pass, fwe 80%, vt 54%, arc 27%. Under the pre-registered >= 50% floor rule (session 38, addenda 12-13; the trigger fixed at addendum 44), ONE gate sat below the floor: arc. The sweep over stored cell records showed why: arc's GATE bar was 5/5 (correct == ARC_CELL_K) while its MEDAL bar was already 4/5 (TASK_PASS_BARS["arc"] = 4, addendum 8) - the gate demanded more than the medal, the one inconsistency the recalibration was always going to find first. At 4/5 the arc per-cell pass rate is 59% - above the floor with headroom.

THE CHANGE: the arc gate predicate is now TASK_PASS_BARS["arc"] (4/5), single-sourced from bench/constants.py (the certify.py duplicate definition is deleted - one bar, one place). Both predicates moved together: _task_load's stored-cell re-grade AND arc_pass's printed PASS/FAIL, so a run's printed verdicts and the free re-grade agree. vt stays at its 5/5 gate (54%, above the floor - barely, by design: vt is the reader's quality bar and the addendum-44 ruling says the floor rule re-fires when the panel moves); speed (0 stalls, equality) and fwe (2/3) untouched.

THE EFFECT (free, from stored cells - no re-measurement): every arc-killed family whose stored cells can reach the 4/5 bar re-grades on the next run's verdict pass; the kill panel's arc row will re-tally from the same stored records. The first arc-dead families (Qwen2.5-1.5B-Instruct, arc 4/10 at the 5/5 gate - the closest-to-a-medal note, addendum 44) are exactly the cohort this recalibration was waiting for.

### Addendum 53 - the 5/5 gate was the refactor's regression, not a new conclusion (2026-10-07, the author's catch)

THE CATCH: "the ARC gate was wrong! it should have been 4/5, that's the conclusion we reached in the previous version of full_benchmark. Oh well, some compute time lost. we need to pay more attention." Correct - addendum 8 set the arc bar at 4/5, and the session-38/40 refactor reintroduced a 5/5 gate in the two fresh-measurement predicates (arc_pass's return, _task_load's stored re-grade) while TASK_PASS_BARS kept the intended 4/5. The addendum-52 recalibration was therefore not a new difficulty ruling but the RESTORATION of the addendum-8 calibration, caught by the kill-rate floor rather than by review.

THE ATTENTION PAID (the structural fix): both fresh-measurement predicates are now pinned by tests against the same source of truth - test_arc_gate_grades_at_the_task_pass_bar (stored re-grade) and test_arc_pass_fresh_cell_grades_at_the_task_pass_bar (a faked-server 4/5 cell must PASS) assert the gate IS TASK_PASS_BARS["arc"], so a refactor that drifts the gate from the bar fails the suite, not the run. The lesson on record: bars live in ONE place (bench/constants.py, single-sourced; the certify.py duplicate is deleted); every predicate that grades must import from there; tests pin gate == bar per task.

NOTE (flagged, not changed): vt has the same shape - its gate is 5/5 (_task_load: p >= 5, vt_pass's gold) while its MEDAL bar is 4/5 (addendum 12). At the current panel (54% per-cell) it is above the floor and stays; if the author wants gate == bar consistency there too, it is the same one-line change plus a test - but it is a real difficulty change (54% -> 64%), not a restoration, so it needs a ruling.

### Addendum 54 - vt joins the consistency ruling: gate = 4/5 (2026-10-07, the author's ruling)

THE RULING: "Be consistent, we chose 4/5 for a reason." The vt gate moves to TASK_PASS_BARS["vt"] (4/5) everywhere - the same consistency as arc (addenda 52-53): _task_load's stored re-grade, certify_rung's single-task cells map, and vt_pass's fresh-cell return (row["acc"] >= bar/5; acc is the 0..5 names as a fraction). The addendum-12 medal bar (4/5) and the gate are now the same number from the same source (bench/constants.py). Effect on the panel: vt per-cell pass goes 54% -> 64% (136/186 at >= 4/5); vt-killed families with stored 4/5 cells re-grade for free on the next verdict pass. fwe's fresh-cell return (acc == 1.0 at 3/3 words) is NOT the same disease - fwe's cell k is 3 and its bar is 2/3 (addendum 13), graded through certify_cells; it stays.

THE DAY'S LEDGER (the author: "today was a day full of bug fixing. But I think the benchmark is in much better shape"): addenda 51-54 - the roster cut at gemma-4-e2b-it (disk ruling), the run stamps its own disk, arc's gate restored to its addendum-8 value, vt's gate aligned to its addendum-12 bar, both gates pinned to the single bar source by tests, and the certify.py bar duplicate deleted. Every verdict re-grades for free from stored cells - the compute cost was scheduling, not measurement.

### Addendum 55 - the state store's orphaned-fst bug: the f16 pass stored ZERO cells (2026-10-07, found answering "which family has a chance to climb")

THE FIND: the pushed state files carry only tournament_entry records - ZERO certify_* cell records across the entire from-scratch f16 pass, despite ~700 measured cells printed in results.txt. The pre-reset archived state (c427f35, the Q8_0 era) had records, so _task_store worked; the from-scratch pass broke it. The cause, reproduced with a fake fresh family: certify_rung_combined bound fst = state["families"].get(fam, {}) - for a family NOT YET IN STATE this is a DETACHED dict - while _acquire_missing_model later created a DIFFERENT dict via state["families"].setdefault(fam, {})["tournament_entry"]. Every _task_store mutated the orphan; save_state faithfully wrote the state's real (cell-less) entry. Consequences: (1) the never-re-measure store never stored - every restart re-measured every family from scratch (the restarts re-ran the dead families' cells instead of loading them); (2) the free re-grade promised by the addendum-52/54 gate recalibrations had nothing to re-grade from; (3) the kill panel's per-cell data came only from results.txt text.

THE FIX: both controllers bind fst = state["families"].setdefault(fam, {}) - the state's own entry, never a detached get. Verified end-to-end with a fake fresh family: the certify_* namespaces land in the saved state file, and the second pass loads them (ran_now 0 - the never-re-measure promise restored). Regression test test_fresh_family_cells_persist_to_the_state_file pins the exact shape (fresh family -> cells in the saved file -> rerun measures nothing). 191 tests.

THE MEASURE OF THE LOSS: every cell the pass measured is in results.txt (per-cell lines with x/k) but not machine-re-gradable; the ~700 cells re-measure once on the next run, then persist properly. The verdicts (dead/infeasible/medal) are all correct - they were computed from the live tallies in-process; only the DURABLE store was lost.

### Addendum 56 - the ladder never climbed: the accept break ended the run (2026-10-07, the author's catch)

THE CATCH: "the benchmark stopped at 4k, it never climbed." Qwen2.5-1.5B-Instruct took the study's first medal (2_sigma at 4,096) and main() stamped "the ladder stops here" and BREAK - the run ended at the moment of its greatest success. The cause: addendum 11's original semantics ("a rung is ANSWERED when a model crowns the requested tier and the ladder STOPS there") survived into v4.x verbatim, but the author's session-40 v4 ruling superseded it: "one model is crowned gold or every model is dead for gold, go to next rung" - the STOP is of the RUNG (the within-rung answered skip is correct: once a rung is answered, remaining families skip IT), never of the LADDER.

THE FIX: an accept now stamps "rung ANSWERED - the ladder moves up (medalist and survivors climb)" and the loop continues to the next depth. The medalist climbs with the survivors - at 8,192 Qwen2.5-1.5B-Instruct measures fresh cells at the deeper rung (the never-re-measure store loads only what its own variant measured at that depth). The all-dead branch was already correct (moves up). Test test_accept_answers_the_rung_and_climbs pins the semantics: an accept at 4,096 is followed by a call at 8,192, and the ANSWERED stamp says "moves up". 193 tests.
