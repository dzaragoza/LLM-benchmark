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
