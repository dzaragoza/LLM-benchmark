# Session 45 - 2026-10-09

Opened 2026-10-09 while the author's n=1 (seed-1 corpus, addendum
143) v7 run is still measuring on the T14s - today's work is design
registration + offline machinery, nothing touches the live run.

## Addendum 144 - the stingy climb: a second allocation policy (R-18 gains a sibling)

The author's ruling: "Register another variant to the greedy
algorithm: instead of picking the largest gain, it picks the
smallest." Registered as the STINGY climb - the established
counterpart to greedy in the allocation literature (greedy takes
the biggest affordable step, stingy the smallest).

The contract is UNCHANGED where it matters: same floor
(Q2_K, q4_0, q4_0), same single-axis one-notch upgrades, same
never-exceed-the-budget rule, same maximality termination (no
upgrade fits = done). Only the step PREFERENCE flips: greedy takes
the upgrade that lands CLOSEST to the budget (largest fit), stingy
the one that lands SMALLEST. Both climbs are myopic heuristics;
their paths are path-dependent and generally END at different
maximal configs.

WHY IT IS REGISTERED (the addendum-138 open question): the greedy
allocation is deliberately unoptimized, and the q/k/v quant-impact
question waits for full-roster data. A second, deliberately
contrasting policy at the SAME 4 GiB budget is the cheapest way to
make the argmax's allocation-sensitivity measurable: where the two
climbs agree, the plan is policy-insensitive; where they diverge
(the budget-tight cells), the score difference IS the quant-impact
evidence the author said to wait for.

Divergence measured on the real registry (roster_limit=12, offline
estimate): 6 of 33 (family, ctx) plans differ, ALL at the
budget-tight end - MiniCPM5-1B @131072 (greedy Q6_K/f16/f16 3.98
vs stingy Q8_0/f16/q8_0 3.52), Qwen3.5-0.8B @262144 (greedy
Q6_K/f16/f16 3.95 vs stingy Q8_0/f16/q8_0 3.44 - the exact cell
whose greedy-config score dropped in the n=1 run), and
granite-4.0-1b at 16384..131072 (greedy dives to Q2_K weights to
fund f16 KV; stingy keeps Q8_0/Q4_K weights with cheaper KV).
Every stingy row verified maximal (no single-axis upgrade fits)
and under budget.

Changes:
- bench/v7.py: greedy_allocations renamed climb_allocations(policy=
  "greedy"|"stingy") - the default IS R-18, byte-for-byte behavior
  (pinned); the climb loop takes the smallest-fitting upgrade under
  policy="stingy". certify_v7 gains alloc_policy, threaded from the
  new --v7-alloc CLI flag (full_benchmark.py).
- tests: the greedy rename propagates (R-21 - no compat alias);
  tests/test_v7_stingy.py pins addendum 144 (maximality, budget,
  floor, divergence-from-greedy, unknown-policy rejection, default-
  equals-R-18).

PRE-REGISTRATION for the stingy arm (run under --clean, never
mixed eras - addendum 129; separate cells from the greedy arm are
NOT comparable in one table):
- Hypothesis: at the diverging cells, stingy's higher-fidelity
  weights + cheaper KV scores DIFFERENT from greedy's cheaper
  weights + f16 KV - the sign is the open question (deeper cache
  fidelity vs smarter weights at fixed M).
- Predictions (quantitative, graded against the greedy-era cells):
  1. Qwen3.5-0.8B @262144 stingy (Q8_0/f16/q8_0) scores in
     [2.5, 4.0] (greedy Q6_K/f16/f16 scored 3.217 in the n=1 run).
  2. At the 27 agreeing cells, scores match the greedy cells
     within seed noise (same config, same corpus - the null arm
     that validates the comparison).
  3. granite-4.0-1b (greedy Q2_K weights at 32k+) scores HIGHER
     under stingy (Q8_0/Q4_K weights) - the weights-term
     sensitivity prediction; if it scores the same, the benchmark
     is weights-insensitive in that band, itself a finding.
- Grading: config-aware resume (addendum 134) does NOT cover a
  policy change - the plan quants drift, so the stored cells
  re-measure on the rerun; run with --clean anyway per addendum 129.

## Addendum 144b - the blind-allocation answer (registered for the record)

The author asked: what OTHER algorithm can choose the parameters
blind - optimum on size, assuming nothing about the importance of
the parameters? The answer registered: a GRID SEARCH is the only
policy that is truly assumption-free over the (wq, kq, vq) axes -
enumerate every feasible config, no order, no preference, no
path. But the grid is small enough that "search" is the honest
word: 7 weights rungs x 4 KV rungs x 4 KV rungs = 112 configs per
(family, ctx), each priced by the SAME estimator (no data
collected). The registered blind baseline is therefore the
MAXIMAL-FIDELITY config under budget: of the feasible set, take
the one maximizing the lexicographic fidelity order (F16 weights
first, then f16 K, then f16 V, tie-break smaller est) - the
config a practitioner with no quality prior would pick ("best
weights I can afford, then best cache"). It is blind in exactly
the author's sense: it uses ONLY size arithmetic (the estimator),
never a quality signal, and assumes nothing about which axis
matters. Registered as the FIDELITY CEILING baseline; NOT shipped
as a climb policy (it is not a climb - no path, no maximality
traversal; it is the exhaustive-search reduction). Evidence use:
when the full-roster data lands, the greedy and stingy configs
grade AGAINST this ceiling per cell - a climb that matches the
fidelity ceiling at a cell is policy-insensitive there; a climb
below it with a HIGHER score is direct quant-impact evidence.
No code change in this addendum; the baseline is derivable from
climb_allocations' own estimator arithmetic when the grading
needs it.


## Addendum 145 - the requirements review: two classes; the tool environment and the test strategy become requirements; the quality run goes daily

The author's rulings (three): "There should be a requirement
explicitly about the tool environment. And about test policy or
strategy. Can you review the requirements?"; "Let's have two types
of requirements, project and wow requirements. Project for
requirements about full_benchmark, wow about the wow."; "Change the
ci weekly workflow in github from weekly to daily."

THE REVIEW (all 29 requirements re-read against their subjects):

- PROJECT class (the benchmark machinery - full_benchmark, the
  bench/ controllers, state/results contracts, the v7 corpus):
  R-01..R-12, R-13..R-19. R-17 (the crash rail) stays project - its
  code lives in full_benchmark's entry path; R-16 (the corpus
  artifact) project by subject.
- WOW class (the way of working - environment, editor, hooks, CI,
  test policy): R-20..R-29.
- Gaps found by the review, now closed as new requirements:
  - R-30 (the tool environment): the environment was pinned only
    from the installed side (test_precommit_env checks the modules
    import) - nothing pinned that requirements.txt DECLARES them.
    R-30 makes the declaration explicit: every hook/test/CI
    dependency is in requirements.txt; a missing dependency is an
    environment bug (install it), never a reason to skip a hook or
    bypass a gate; a new tool enters through requirements.txt plus
    a pinning test.
  - R-31 (the test strategy): the layers existed in practice
    (deterministic pins, hypothesis properties, crosshair
    contracts, the full suite on push) but the POLICY was spread
    across addenda 116/117/119/127. R-31 registers the strategy:
    (1) deterministic pins, affected-subset in the commit hook via
    testmon; (2) hypothesis properties marked hypothesis_props,
    never in the 5s hook; (3) crosshair contracts; (4) the FULL
    suite on every push and daily in CI; a red push-regression
    blocks the next delivery (R-27). A bug that reaches a run
    becomes a regression test and, where the class warrants it, a
    requirement (wow.md rule 3). Coverage: a discovery helper,
    never a metric.

THE PROTOCOL SPLIT: md/protocol.md's Requirements section now
carries two tables - "Project requirements (the benchmark
machinery)" and "WoW requirements (the way of working)". R-numbers
are stable (no renumbering - history preserved); the class is the
table a row lives in. requirements_check.py is unchanged - it
scans the whole file for R-rows either way.

THE DAILY QUALITY RUN: weekly-quality.yml is retired (deleted);
daily-quality.yml replaces it - same steps plus the full pytest
suite (the R-31 daily home), cron 00:00 UTC DAILY. The weekly
cadence was addendum 24's; the author's ruling supersedes it.

Changes: md/protocol.md (the two-class split + R-30/R-31),
tests/test_tooling_reqs.py (Pins: R-30, R-31 - requirements.txt
declares the environment; the workflows install from it; the
hypothesis marker stays out of the hook; the layers have their
homes; the daily workflow exists, the weekly one is gone),
.github/workflows/daily-quality.yml (new), weekly-quality.yml
(deleted).

BONUS FIND (the pin paying for itself at birth): writing the R-31
pin caught a live regression - the addendum-119 testmon rewrite had
DROPPED the addendum-117 hypothesis deselect from the hook's pytest
command (no -m "not hypothesis_props"), so a commit touching
tests/test_properties.py would have run the slow property layer
inside the 5s hook. Restored in testmon_hook.py; the R-31 pin
(test_r31_hypothesis_never_in_the_hook) holds it from now on.


## Addendum 146 - ruff format never aborts the commit (the author's ruling)

"Ruff format should not abort the commit, since it is only
formatting changes." Correct - the stock ruff-format hook exits
non-zero whenever it MODIFIES a file, which aborts the commit so
the human re-stages; for a formatting-only delta that is pure
friction (it cost a failed commit in BOTH of today's deliveries).

The fix (verified in a scratch repo before shipping): format_hook.py
replaces the stock entry - it runs ruff format on the hook's files,
RE-STAGES everything it touched, and exits 0. The commit proceeds
WITH the formatting already applied (the committed tree is the
formatted tree - verified by inspecting the scratch repo's HEAD).
The exit-0 is scoped to style deltas ONLY: a genuine ruff format
failure (a syntax-broken file) still exits non-zero and blocks the
commit - a broken file must not slip in under a formatting flag.
Ruff LINT (ruff with --fix) keeps its stock aborting behavior: a
lint finding is a code-quality signal, not a formatting delta.

Pinned by tests/test_format_hook.py (Pins: R-25): style delta ->
format + restage + exit 0; clean file -> silent pass; broken file
-> non-zero; exactly one ruff-format entry in the hook config (the
wrapper - the stock aborting entry is gone).


## Addendum 147 - the commit fires only when something ran; the CI strategy reworked (local-fast vs CI-complete)

Two rulings. First: "let's improve the commits after model
completion, make it push results only when something ran. now is
committing and pushing the models that we already evaluated..."
Correct - the addendum-132 per-model commit fired on the family
boundary even when every cell was skipped (the resume case): a
no-op re-push of already-evaluated artifacts. Fix: _flush_model_commit
fires only when at least one cell in the batch RAN (no "skipped"
key); a fully-skipped family commits nothing. The batch still
carries the whole family picture when at least one cell measured.
R-24 reworded; pinned by test_certify_v7_no_commit_when_nothing_ran.

Second: "Let's rework our ci strategy: we don't need the daily. we
run locally as much as we can under the 5s time to commit rule and
leave the rest to github ci to handle, including what was in the
daily. since we always check the latest results during pull, we
will catch any errors there. this is a wow requirement."

The strategy is now LOCAL-FAST vs CI-COMPLETE, with NO scheduled
runs: the commit hook owns everything that fits the 5s rule
(ruff, the format wrapper, ty, md, requirements, testmon-affected
pins); GitHub CI owns everything else on EVERY PUSH -
push-regression.yml absorbs the former daily steps (the full
pytest suite, crosshair contracts, coverage, vulture, the
pre-commit drift report). daily-quality.yml is DELETED (the
weekly predecessor was already gone - addendum 145's daily lived
exactly one session). The safety net is the pull check (R-27):
the latest COMPLETED push-regression verdict is checked on every
pull, so anything the fast hook missed is caught before the next
delivery. R-31 reworded to the final form; pins updated
(test_r31_layers_have_their_homes, test_r31_no_scheduled_workflows).

Note: the never-abort format wrapper (addendum 146) is part of the
local-fast side - formatting changes apply and re-stage without
aborting, keeping the 5s loop friction-free.


## Addendum 148 - the changed-test-files arm of the hook; testmon in CI

Two rulings. First: "OK. Run pytest with testmon in the github ci."
push-regression.yml now runs the full suite WITH --testmon - the map
seeds itself in CI, so any clone gets a warm map as a side effect of
the registered full-suite step.

Second: "But it leaves to us to manually run every test file that
changed. Can you make it part of pre commit hook?" Correct, and the
root cause is structural: the testmon map only knows tests that
have ALREADY RUN (test_execution rows). A new test file has no rows,
so testmon selects nothing for it - and an edited test file whose
only change is a new test likewise. The hook now owns that arm
directly: _changed_test_files() reads git status (staged, modified,
untracked; -uall so untracked directories list their files) and runs
every changed tests/*.py EXPLICITLY, before the testmon selection -
and even when no map exists (a fresh clone still gates its own new
tests). A failure in the explicit arm blocks the commit with the
same weight as a testmon-selected failure; the exit codes combine
(the explicit arm's failure short-circuits the testmon run).

The no-map note still fires when nothing changed - CI owns the
first full run, unchanged.

Pinned by tests/test_testmon_hook.py: the explicit arm runs (probe
in a scratch repo executes and reports), a failing changed test
file blocks, and the existing contract pins hold.


## Addendum 149 - code_edit robustness: the docstring-apostrophe fix and the quote-style rescue

The author's ask: "Any bug fixes or improvement to code edit? I
have seen you struggle with single quotes." Two real defects,
both demonstrated in today's session:

1. THE DOCSTRING-APOSTROPHE FALSE BLOCK. The region balance check
   (_check_delimiters) scanned each edited region as CODE even
   when the region sits inside a triple-quoted string - so editing
   docstring PROSE containing an apostrophe ("CI's job",
   "addendum-117's") read as an unclosed quote and blocked the
   edit (it cost two re-aimed edits in addendum 147's delivery).
   Fix: a region that sits inside a triple-quoted string is prose -
   the check requires only that the region keeps its triple-quote
   pairing even (a truncated docstring fragment still blocks);
   code regions keep the full quote/bracket balance check.

2. THE QUOTE-STYLE RESCUE. The addendum-146 format hook legally
   rewrites quote styles across the file (' -> " under the repo's
   ruff config), so an old_str written against the pre-format
   style stops matching exactly while the CODE is unchanged
   (this bit twice: the test_tooling_reqs.py re-aims). Fix: after
   the exact and whitespace-flexible passes fail, the finder tries
   the quote-swapped target (both directions) - uniqueness
   required, the same contract as the whitespace rescue; the
   FILE's own text is returned so the apply stays exact.

Both fixes verified against their live failure cases (6 direct
probes + the session-45 shapes), the guards regression-tested
(truncated code, broken triple-quote, quote opened in code still
block), and pinned by tests/test_code_edit_robustness.py (8
tests, Pins: R-26).


## Addendum 150 - the fakes land; the random climb replaces the fidelity ceiling

Two rulings. First: "Do the fakes" - tests/test_v7_fakes.py covers
the certify_v7 loop offline (the addendum-108 coverage hole): the
happy loop with census, server-never-comes-up, template-malfunction
labelling, preflight overflow, run_cell isolation, acquire failure,
config drift - every branch of the loop, no GPU. The addendum-112
discipline holds: fakes cover CONTROL FLOW, never the measurement
contract; production preflight keeps its live /tokenize call.

Second: "Fidelity sounds interesting. I don't like the
lexicographic order though, it inadvertently assigns importance to
the order the parameters are defined. What about random climb? One
step at a time in a random parameter. Stops when no parameter can
be risen. Always the same seed to allow reproduction."

CORRECT on the flaw: the lexicographic order of addendum 144b
(F16 weights, then f16 K, then f16 V) assigns importance by
definition order - exactly what a blind baseline must not do.
SUPERSEDED: the fidelity ceiling is retired, replaced by the
RANDOM climb (policy="random"): each step gathers every fitting
single-axis one-notch upgrade and a SEEDED rng (ALLOC_RANDOM_SEED,
registered; seeded per family via params) picks one; the stop is
the shared maximality contract (no upgrade fits). No ordering, no
step preference, reproducible - the assumption-free arm. Shipped
in climb_allocations + the --v7-alloc CLI choice; pinned by
tests/test_v7_random.py (maximal, under budget, reproducible,
diverges from greedy).

The three-way comparison (greedy vs stingy vs random at the same
budget) is the allocation-sensitivity evidence for the addendum-138
open question once the full-roster data is in.


## Addendum 151 - the WoW teeth audit: pins mutation-tested; two strengthened

The author's ask: "Let's check the wow requirements have teeth.
That they actually have an effect and stop you from breaking the
requirement." Method: for each WoW requirement, MUTATE the guarded
artifact, run the pin, expect failure; revert.

RESULTS (7 requirements mutation-tested):
- R-21 (compat shim reintroduced): BITES.
- R-24 (no-op push restored): BITES.
- R-28 (zero-max floor broken): BITES.
- R-30 (dep removed from requirements.txt): BITES.
- R-31 (scheduled workflow reintroduced): BITES.
- R-25/R-31 (hypothesis deselect dropped from ONE hook arm): DID NOT
  BITE - the pin checked the substring anywhere in the file, so
  breaking the testmon arm's deselect while the docstring and the
  explicit arm still mentioned the marker passed the pin. TOO WEAK.
- R-20 (bypass embedded in a longer command string): DID NOT BITE -
  the pin grepped for the flag as the WHOLE quoted literal, so
  "git commit --no-verify -q" escaped it. TOO WEAK.

THE TWO STRENGTHENED PINS:
- test_r31_hypothesis_never_in_the_hook now counts the deselects
  against the hook's subprocess call sites: EVERY pytest arm must
  deselect the marker (>= call sites), and the testmon arm must
  stay a testmon run.
- test_no_verify_is_not_used_in_history now scans for the flag
  inside ANY string literal in code (triple-quoted docstring blocks
  are stripped first - narrating the retired bypass is history,
  ty_check.py's docstring stays legal).

Both re-tested after strengthening: the mutations now FAIL the
pins, the clean tree passes all 26 WoW pin tests. The audit method
itself is registered: a pin that cannot fail is decoration - run
the mutation before trusting the pin.


## Addendum 152 - mutmut joins CI; wow.md trimmed of requirement-covered items

Two rulings. First: "We tried a test mutation tool but discarded it
because it was too slow. Add it to github ci." - mutmut (the
session-40 first trial: 1922 mutants, 584 killed, the selection
caveat on record) returns as a CI step in push-regression.yml,
NON-GATING (|| true): the tally lands in the run log for the next
session to read, never blocks a delivery - mutation survival is a
discovery helper like coverage, never a gate. Too slow locally is
exactly the addendum-147 split: CI owns what cannot fit the local
budget. The session-40 caveat stands: the [tool.mutmut] selection
is the 4 pure test files; a fair code_edit score still needs
test_seams (staging-dir limit, on record). The removal clause also
stands: if the CI trials add no finding beyond coverage + the
gates, remove it.

WATCH ITEM, on record: pushes are frequent during a live benchmark
(the artifact rail fires per model), and every push now runs the
mutmut sweep. If CI minutes or queue latency bite, the knob is a
separate manual-dispatch workflow - the author rules if it moves.

Second: "There's overlap between wow.md and requirements for wow.
Remove from wow.md the items already covered by requirements."
The overlap audit: former section 4 (Vibe uses the code_edit tool)
was FULLY covered by R-26 - removed, sections renumbered (4-9 now
Daniela-human/fish/naming/help/review). Section 3's
a-bug-becomes-a-regression-test clause now cites R-31 (the test
strategy's closing clause) instead of restating it. Section 10
(review on demand) and the scientific-method sections stay - no
requirement covers them (they are ways of working the requirements
table deliberately does not duplicate). Historical notebook
references to "wow.md section 4" resolve to R-26 - a pointer note
in wow.md section 3 states it.


## Addendum 152 - mutmut joins CI; wow.md trimmed of requirement-covered items

Two rulings. First: "We tried a test mutation tool but discarded it
because it was too slow. Add it to github ci." - mutmut (the
session-40 first trial: 1922 mutants, 584 killed, the selection
caveat on record) returns as a CI step in push-regression.yml,
NON-GATING (|| true): the tally lands in the run log for the next
session to read, never blocks a delivery - mutation survival is a
discovery helper like coverage, never a gate. Too slow locally is
exactly the addendum-147 split: CI owns what cannot fit the local
budget. The session-40 caveat stands: the [tool.mutmut] selection
is the 4 pure test files; a fair code_edit score still needs
test_seams (staging-dir limit, on record). The removal clause also
stands: if the CI trials add no finding beyond coverage + the
gates, remove it.

WATCH ITEM, on record: pushes are frequent during a live benchmark
(the artifact rail fires per model), and every push now runs the
mutmut sweep. If CI minutes or queue latency bite, the knob is a
separate manual-dispatch workflow - the author rules if it moves.

Second: "There's overlap between wow.md and requirements for wow.
Remove from wow.md the items already covered by requirements."
The overlap audit: former section 4 (Vibe uses the code_edit tool)
was FULLY covered by R-26 - removed, sections renumbered (4-9 now
Daniela-human/fish/naming/help/review). Section 3's
a-bug-becomes-a-regression-test clause now cites R-31 (the test
strategy's closing clause) instead of restating it. Section 10
(review on demand) and the scientific-method sections stay - no
requirement covers them (they are ways of working the requirements
table deliberately does not duplicate). Historical notebook
references to "wow.md section 4" resolve to R-26 - a pointer note
in wow.md section 3 states it.


## Addendum 153 - the reverse conversion: wow.md items become WoW requirements

The author's ask: "Now the other way. Can we make items in wow.md
into requirements for wow?" The v5.0 bar governs: a requirement is
a TESTABLE statement, so only items with a mechanically checkable
core convert; the human-discipline clauses stay in wow.md marked
"(Requirement-covered: R-xx)".

CONVERTED (five new WoW requirements, R-32..R-36):
- R-32 (reproducibility, wow.md rule 1): seeded runs, registered
  commands, registered seed constants. Pins: the corpus determinism
  test and the seeded random-climb reproduction test.
- R-33 (pre-registration, rule 1): the notebook carries the
  pre-registrations BEFORE the run, quantitative with bands. The
  pin checks the structure; the honesty stays in wow.md.
- R-34 (negative results, rule 1): a score-0 v7 cell carries either
  its answers log (evidence) or an error label - a bare unexplained
  0 fails. THE PIN FOUND THE LIVE DATA COMPLIANT.
- R-35 (one session per day, rule 2): the index links every session
  file; no orphans.
- R-36 (naming, rule 7): lowercase-kebab, ALL-CAPS reserved for
  README alone. THE PIN CAUGHT TWO PRE-EXISTING VIOLATORS on its
  first run - md/conversation up to 2026-09-27.md and the reports/
  Zenodo mirror (spaces in filenames) - both renamed via git mv
  (history preserved; the README cites the report by title and DOI,
  not path, so nothing broke). A pin born yesterday enforcing a
  session-36 rule: the requirement caught what the convention could
  not.

NOT CONVERTED (deliberately - no test can pin them): one-variable-
at-a-time, calibration-is-standing-work, rulings-are-explicit,
statistics-are-justified (all rule-1 disciplines); Daniela-is-human
(fish, checklists - rules 4/5); ask-for-help (rule 8);
review-on-demand (rule 9). These stay as the working agreement.

The requirements table now carries 36 requirements, all pinned.


## Addendum 154 - selection semantics made explicit; the page goes v7

The author's ruling: "Clear how you pick families. But make it
clear. We go with all candidates and pick the first n that are in
the list sorted by number of parameters. The fact that some cannot
run is a finding. Report them as such. Saying 12 was confusing."

The semantics were always first-N-param-ascending, but the
UNPLACEABLE were silently skipped inside climb_allocations - so
"we ran with 16" and the table showed 12 with no explanation.
Now: report_unplaceable=True makes the plan carry the findings
(family, params, reason) and certify_v7 PRINTS them before the
run - "4 of the first 16 candidates cannot earn a cell (findings)",
each with its reason (missing registry extract / window below the
grid / floor config over budget). The measured count is honest by
construction. THE FIRST-16 FINDINGS: gemma-3-1b-it and
Llama-3.2-1B-Instruct (missing extracts, recoverable via
etc/registry_data.py fetch), MiniCPM-1B-sft and phi-1 (windows
4096/2048 below the grid - the addendum-123 honest consequence).

Second ruling: "Let's make the result webpage based in V7. With
the data we have now." docs/index.md is now the v7 deliverable:
the argmax (Qwen3.5-2B at 262,144, Q8_0/q8_0/q5_0, 6.88/30, est
3.84 GiB) with its llama-server command line, the full 11-family
ranking with the reach curves, the findings table (the four
unplaceable, the labelled-not-scored malfunction classes), and the
what-the-numbers-mean section (credit scoring, exclusion-not-
failure, reproducibility). The v5-era per-rung gold sections are
retired from the page (history in the notebook and the registry).


## Addendum 155 - the dry run commits and pushes its plan

The author's catch: "dry run doesn't commit and push results. fix
that." Correct - the clean-finish git tail excluded dry runs, so
the plan (the findings report, the cell list, the feasibility
checks) existed only on the author's console. The agent reads the
repo; an unpushed plan is an unreadable plan.

Fix: the clean-finish tail's `not args.dry_run` condition is
deleted - the tail runs for dry runs too. The addendum-79 guard is
UNTOUCHED and still holds: the dry run never WRITES the state file
(the guard tests pin that); git_tail only commits what exists on
disk, so a dry-run commit carries the PRE-RUN state (unchanged, it
was never written) plus results.txt (the plan output - exactly the
readout the agent side needs). No fake state, no poisoned
measurements; the plan lands in the repo where it can be read.

The crash rail already had this shape (it runs under no_git
only, not dry_run) - the clean path now matches.


## Addendum 156 - the candidate count is mandatory

The author's ruling: "let's remove the default, make the number of
models mandatory." The --v7-families flag had default None with a
silent fallback to PILOT_FAMILIES=4 - exactly how the author's
"we ran 16" became a 4-family plan in the 11:11 dry run (nobody
stated the count; the pilot default answered). The count is now
MANDATORY at every entry point: --v7-families is required=True
(argparse exits 2 without it), and certify_v7's roster_limit is a
positional parameter with NO default (moved before the defaulted
params - a no-default parameter cannot follow defaulted ones).
PILOT_FAMILIES the constant stays only as an explicit value tests
pass; no code path defaults to it.

Pinned by tests/test_v7_mandatory_count.py (the flag is required,
no default accompanies it, certify_v7's signature carries no
fallback, --help documents the flag). The pin caught its own
delivery bug: the first CLI edit silently failed mid-transaction
(the tool refused a syntax-breaking intermediate state) and the
pin's required=True assertion failed - fixed before commit.


## Addendum 156 - the candidate count is mandatory

The author's ruling: "let's remove the default, make the number of
models mandatory." The --v7-families flag had default None with a
silent fallback to PILOT_FAMILIES=4 - exactly how the author's
"we ran 16" became a 4-family plan in the 11:11 dry run (nobody
stated the count; the pilot default answered). The count is now
MANDATORY at every entry point: --v7-families is required=True
(argparse exits 2 without it), and certify_v7's roster_limit is a
positional parameter with NO default (moved before the defaulted
params - a no-default parameter cannot follow defaulted ones).
PILOT_FAMILIES the constant stays only as an explicit value tests
pass; no code path defaults to it.

Pinned by tests/test_v7_mandatory_count.py (the flag is required,
no default accompanies it, certify_v7's signature carries no
fallback, --help documents the flag). The pin caught its own
delivery bug: the first CLI edit silently failed mid-transaction
(the tool refused a syntax-breaking intermediate state) and the
pin's required=True assertion failed - fixed before commit.


## Addendum 159 - nothing verification-shaped runs locally, ever

The author's ruling: "expand: no linter, no tests no formatter.
nothing. only ci run those. If not the experience is dramatically
degraded, you have infinite patience. I do not."

R-38 registered: the agent NEVER runs a test, a linter, a
formatter, a type check, coverage, vulture or mutmut locally - not
on a file, not on a test, not "just to be sure". The local loop is
edit (code_edit) -> commit -> push -> CI judges -> the verdict is
read on the next pull (R-27) and failures are fixed there. The
author's patience is the protected constraint: the local loop must
stay seconds-long; the agent's patience is infinite and irrelevant.

This closes the arc of the day: addendum 116 installed the 5s hook,
148 gave it the changed-test arm, 157 made it function-granular, 158
abolished it - 159 abolishes the hand-run habit too. Verification
is CI's job, all of it, only.

The delivery of this very addendum follows the rule: no local
verification was run; the CI verdict on the next pull grades this
commit.


## Addendum 160 - R-39: the CI verdict gates every git command

The author's ruling: "Let's make things clearer. before running
any git command, check the status of the last ci completed run in
github and fix any issues before continuing. any git command."

R-39 registered (R-27's final form): before ANY git command -
pull, commit, push, rebase, status - the agent checks the latest
COMPLETED push-regression verdict and fixes any red issues FIRST.
In-flight runs are never waited for; the previous completed verdict
governs. This closes the gap the email noise exposed: red runs
accumulating across my pushes because "next pull's verdict
governs" deferred the check instead of making it blocking.

The delivery of this addendum demonstrates the rule: the latest
completed run (37915318674) was read BEFORE the commit; its
failures - the fake climb_allocations stubs missing the
report_unplaceable kwarg (addendum 154's signature change) and the
four parser tests hitting the now-mandatory --v7-families
(addendum 156) - are fixed in this same commit.


## Addendum 162 - the comparison arms without wiping: separate files + the cell selector

The author's ruling: "Do not clean the results. let's use separate
results files. let's add the functionality to run only the cells we
want measured, no sense in measuring everything we know is not
going to change."

Two changes:
1. SEPARATE ARMS: --state-file/--results-file already exist as CLI
   flags; the answers JSONLs now carry the policy suffix (the greedy
   arm keeps the bare filenames - history unchanged; the stingy arm
   writes <fam>-ctx<ctx>-v7.stingy-answers.jsonl, the random arm
   .random) - no arm overwrites another's evidence, no --clean
   needed for a comparison run.
2. THE CELL SELECTOR (--v7-cells): comma-separated family:ctx pairs;
   only the listed cells measure, everything else reports
   "cell not selected (--v7-cells)" and is never touched. The
   three-way comparison plans diverge at only 8 (stingy) / 11
   (random) of 52 cells - the agreeing cells are already measured
   in the greedy arm and CANNOT change (same config, same corpus,
   same seed), so re-measuring them is pure cost. The comparison
   arms measure exactly the diverging cells.

Pre-registration (from the session's standing comparison table):
P1 Qwen3.5-2B@262k stingy (Q6_K/q8_0/q8_0) scores [5.0, 6.9],
   below greedy's 6.88 - the argmax family holds.
P2 Qwen3.5-0.8B@262k stingy (Q8_0/f16/q8_0) scores >= greedy's
   3.22 (better weights than greedy's Q6_K at that cell).
P3 granite-4.0-1b scores above its greedy 0.0 at >= 2 cells under
   stingy (the weights-term prediction).
P4 the agreeing cells are identical across arms by construction -
   the null arm.
A family-ranking flip = the allocation policy is a scoring
variable, not just a memory plan - register the finding.


## Addendum 163 - mutmut selection fixed; the I/O layer covered by a loopback stub

Two rulings. "Fix mutmut." The CI trial (addendum 152) crashed the
stats run on a pre-existing failure in the OLD selection - session
40's list named test files whose bare root-module imports break
under mutmut 3.x's staging dir. The selection now points at the
CURRENT test homes for both registered sources: test_seams.py (61
tests, the strongest code_edit file - the session-40 verdict that
a fair score requires it), test_code_edit_cli.py (PYTHONPATH-based,
staging-compatible), test_code_edit_robustness.py, and
test_md_check.py (the second source's home). The conftest sys.path
insert is staging-consistent (mutmut stages the whole tree), so
the staged mutants are the ones the tests exercise.

Second: "use fakes to test the io layer" - tests/test_io_fakes.py:
a loopback HTTP stub (real sockets, real urllib, an in-process
HTTPServer answering like llama-server) so the I/O layer runs its
REAL request paths offline: tokenize's round trip and its
no-tokens-field error, ask's content/reasoning_content contract
and its chat_template_kwargs injection, the HTTP-error body
surfacing (the addendum-102 crash shape), trim_to_tokens'
never-over-budget bisection, and wait_healthy's poll-to-green and
unreachable branches. The addendum-112 discipline holds: the stub
fakes the SERVER, never the measurement contract - production code
unmodified, no GPU, no binary.


## Addendum 164 - every tool failure fails the CI run

The author's ruling: "Make any tool failure in ci make the Ci run
fail." The last non-gating arm was mutmut's `|| true` (the
addendum-152/158 tolerance: the tally lands in the log, never
blocks). Removed - mutmut's exit code now gates the run like
every other tool. The CI run is now fully gating: ruff, ruff
format, ty, md_check, requirements_check, pytest, crosshair,
coverage, vulture, mutmut - ten tools, ten verdicts, no mercy
clause. A tool that fails IS a finding; a finding that cannot
fail the run is decoration (the addendum-151 lesson applied to
the workflow itself).


## Addendum 165 - wow.md becomes the authority document for interactions

The author's ruling: "Let's use wow.md as the authority document
for our interactions. It will be easier for both of us, instead of
relying on the conversation." Plus: "Add the Ci check last finished
run and fix before pull" - and the code_edit rule was confirmed
already present (R-26 / wow.md section 3).

wow.md gains section 0, "Daniela's session rules (live - the
authority section)", placed at the top: Vibe reads it FIRST every
prompt cycle and applies it in order. Five live rules seeded:
(1) CI before pull - the last completed verdict, reds fixed before
pulling, in-flight never waited on; (2) nothing runs locally (R-38);
(3) commands handed over immediately, bugs fixed as they come;
(4) every edit through code_edit (R-26); (5) speed first - the
author's time is the constraint.

The conversation-vs-document gap that motivated this: the author
updated rules in the Skill Hub and Vibe reasoned from chat remarks -
the two disagreed and neither was authoritative. Now the file is:
Daniela edits the section, commits, and the rules apply - the
commit is the announcement. This closes the drift class the whole
session struggled with (the every-prompt CI skill being "used",
mis-used, and disused with no shared source of truth).

Also this delivery: the red format finding fixed (test_io_fakes
stub dict, the formatter's own wrapping), read from the completed
CI verdict before this commit per the new rule 1.


## Addendum 166 - the multi-arm run: all three policies per cell, one file

The author's ruling: "Regarding the different arms greedy stingy
and random. Let's apply them together from the next run on. For
every cell greedy goes first, then stingy iff it produces a
different configuration, last random iff it produces a different
configuration to the other two. Store all this info in the cell in
a single file. So all the data is there."

--v7-multi-arm: certify_v7 computes all three plans, walks greedy's
cells, and per cell measures greedy, then stingy IFF its config
differs, then random IFF its config differs from both measured
arms. Each diverging arm gets its OWN launch cycle (a different
weights quant is a different GGUF with different cache flags - the
greedy server cannot serve it): stop, acquire, relaunch, health,
score. Every arm's config and score land in the SAME cell record -
state[family][ctx]["arms"] = {greedy: {...}, stingy: {...}, random:
{...}} - one file holds all the data. Cells where all three agree
measure once (the agreeing arms ARE the same measurement).

Also this delivery: wow.md rule 2 gains the explicit habits clause
("Do NOT run pytest... HABITS DO NOT OVERRIDE THIS RULE"), and the
red format finding from the completed verdict was fixed before the
push (test_io_fakes, second stub dict - the formatter's wrapping).


## Addendum 167 - the random climb's seed is ONE fixed constant, same for every cell

The author's sanity check before the multi-arm run: "Make sure the
random seed for random climb is fixed and is the same for every
cell." The addendum-150 form seeded ALLOC_RANDOM_SEED + params -
DIFFERENT streams per family (and params-dependent: reproducing a
plan required the registry's params, not the constant alone). The
registered text even said "seeded per family" - the author's check
caught a real reproducibility weakness.

Fixed: ONE fixed seed. A fresh random.Random(ALLOC_RANDOM_SEED) per
(family, ctx) - the same constant for every cell, no params-
dependence, no cross-cell stream coupling: the plan for any cell
reproduces from the registered constant alone. The pin's docstring
updated to match. R-29's "seeded per family" wording is corrected
by this addendum (the protocol row carries the new form).


## Addendum 169 - CI continues after any error; format is applied, never gated

The author's ruling: "Make ruff format di the formatting without
reporting error. Make the Ci continue even after error." Two
changes to push-regression.yml:

1. RUFF FORMAT APPLIES: `ruff format .` runs in place - formatting
   drift is fixed by the run, never reported as an error (the
   format gate is retired; the formatter's output is the fix).
2. CONTINUE-ON-ERROR EVERYWHERE: every tool step carries
   continue-on-error, so ALL tools always run - a red anywhere can
   never hide the steps below it again (the mutmut tally was being
   hidden by format reds dying at step 3). The verdict is the
   AGGREGATE: a final always()-gate reads every step's outcome and
   fails the run iff any tool failed. The log always carries the
   full ten-tool picture: lint, format (applied), ty, md,
   requirements, pytest, crosshair, coverage, vulture, mutmut.

Note: the format step writes to the CI workspace only - it does not
commit back; formatting drift is fixed on the next local delivery
(or by the author's editor). The step's purpose is that the rest of
the run sees a consistently formatted tree, without gating on it.


## Addendum 170 - the MEASURED budget gate; the audit; the page shows measured RAM

The author's ruling: "Census on Llama's deep cell: total 4.32
GiB (est 3.86) - this should have been an error. check always the
gpu memory usage in llama-cpp is under 4 gib! the estimate is
that, an estimate." Three parts:

1. THE RUNTIME GATE: BudgetExceeded - after every cell's census,
   the GPU footprint (Vulkan0 model+context+compute) is checked
   against the budget; over-budget raises, the cell is labelled
   error=budget, never scored. The estimate plans; the census
   decides.

2. THE AUDIT of all runs: one true violator on the GPU scope -
   granite-3.1-2b-instruct @65536, GPU 4.03 GiB (greedy 1.961,
   stingy 2.139). ERASED: the cells from both state files and the
   answers logs. The cells I had quoted with totals over 4
   (Llama 4.51/4.32, Qwen 4.33) are GPU-scope-compliant (3.95,
   3.99, 3.88) - the totals include the host share, out of scope
   per addendum 136. My earlier "safe direction" framing answered
   the wrong question and is corrected here.

3. THE PAGE: the winner's entry now shows llama-server's measured
   GPU breakdown (3.49 GiB for Qwen3.5-2B@262k), not the
   estimate; the whole-machine figure noted as the host-share-
   inclusive number.


## Addendum 171 - the estimator calibrated: an under-estimate is an error

The author's ruling: "check your estimator, every under estimation
in the estimator is an error. fix the estimator for gpu ram usage.
overall usage is irrelevant, only gpu counts."

THE AUDIT: 68 census records replayed est vs measured GPU. 24
under-estimates across 6 families - every one an error. The
decomposition found three wrong constants:

1. Q4_K weights: 0.56 bpB -> 0.65. The census measured 0.625
   (granite-4.0-1b) to 0.646 (Llama-3.2-1B) bits-per-weight; the
   old constant under-counted ~13% - the granite-3.1@65k budget
   violation (addendum 170) traces to exactly this. The register
   takes the measured UPPER bound: over-estimation costs a little
   fidelity, under-estimation violates the budget.
2. Q8_0 weights: 1.06 -> 1.0625 bpB. The census (granite-3.1-2b:
   2.507 GiB / 2.5335B params) shows the scale byte llama.cpp's
   q8_0 blocks carry; 1.06 was a hair light.
3. COMPUTE_FLOOR_GIB: 0.03 -> 0.06. The census shows a ~0.055 GPU
   compute floor across families; 0.03 under-counted every cell.

VERIFICATION: all 61 in-scope census records replay with est >=
measured GPU - zero under-estimates remain. Pinned by
tests/test_estimator_no_under.py: any future census record that
lands under its estimate fails CI (the pin replays the whole
state), and the calibrated constants are pinned by value.


## Addendum 172 - R-40: _0 encodings only below f16

The author's ruling: "k encodings are a risk for our size limit.
use _0 encodings for everything except f16. make it a requirement."

The weights ladder is now exactly [Q4_0, Q8_0, F16] - the legacy
block formats with EXACT structural sizes (q4_0: 18 bytes/32
weights = 0.5625 bpB; q8_0: 34/32 = 1.0625 bpB, census-confirmed).
No K-quant super-block bookkeeping: the k-scales are the size
hazard (Q4_K measured 0.625-0.646 vs the assumed 0.56 - the
granite-3.1@65k budget violation's root cause, addenda 170/171).
R-18's "k encoding below q8" clause is RETIRED; the floor config
is (Q4_0, q4_0, q4_0). Registered as R-40, pinned by
tests/test_r40_0_encodings.py (the ladder, no _K suffix anywhere,
the structural constants).

Consequences: plans re-compute with the coarser ladder (fewer
rungs = coarser climbs at the budget line; the q4_0 rung is
smaller than Q4_K so some cells gain headroom, others lose the
in-between steps). Stored cells whose configs carried _K encodings
drift from the new plans and re-measure (addendum 134).


## Addendum 173 - the ladders are EQUAL: the _0 family, both axes

The author's ruling: "make the ladders equal, _0 only" - the
weights ladder and the KV ladder now carry the SAME family: the
legacy _0/_1 block formats, structural sizes only:
Q4_0 (0.5625), Q4_1 (0.6250), Q5_0 (0.6875), Q5_1 (0.7500),
Q8_0 (1.0625), F16 (2.0) - weights and cache both, six rungs each.
The _1 variants carry a min-offset byte pair per block (the size
difference is structural: q4_1 is q4_0 + 0.0625 bpB exactly). The
R-40 pin extended: no _K anywhere, and the ladders' sets are equal.

Also fixed this delivery: the estimator pin's constants follow
the retired Q4_K (KeyError on CI), and the ty/E501 pair from the
pre-launch check.


## Addendum 174 - v7.1: the fresh-table restart; the _1 correction

The author's rulings: "Let's restart the benchmark with the new
machinery. let's call this version v7.1" and the correction "youre
wrong, we dont use _1" - the registered ladders are the _0 formats
ONLY: [Q4_0, Q5_0, Q8_0, F16], weights and KV both, EQUAL sets.
The _1 variants never enter a plan (my addendum-173 draft added
them to the ladders prematurely; corrected before the v7.1 run).

v7.1: a completely fresh state (benchmark-state-v7-1.json), every
cell measured from scratch under the full new machinery - equal
_0 ladders, structural sizes, the measured budget gate
(BudgetExceeded), the calibrated estimator, the multi-arm records,
the mandatory candidate count, the findings report. The v7.0
tables stand as history; the v7.1 table is the first fully-honest
one (no format risk, no estimate-only verdicts).


## Addendum 176 - three new CI gates: python compile, JSONL validation, the dry-run smoke

The author's ruling: "do 3 and 6. add too python compile" - the
CI gates extend:

1. PYTHON COMPILE, both versions: compileall over bench/infra/etc/
   tests/*.py on the workflow's 3.12 AND on 3.13 (the study's
   target, README: "Python 3.13+ required") via a second
   setup-python - version-specific syntax breakage caught at push.
2. ANSWERS JSONL VALIDATION: every committed *-answers.jsonl line
   parses and carries the required keys (window/grade/expected/
   value/found/ok/answer) - the mid-write crash class caught at
   push (validate_jsonl.py; the R-34 evidence contract as a gate).
3. THE DRY-RUN SMOKE: full_benchmark --task v7 --v7-families 16
   --dry-run --no-git runs the whole orchestrator end-to-end
   offline - the plan, the findings report, the summary. The exact
   class today's live crashes were (the --v7-cells
   UnboundLocalError, the dry-run tail bug) would have died HERE,
   at push, instead of on the author's machine.

Also this delivery: the aggregate gate reads four more outcomes;
the E501 pair from the ladder-refs fix; and the addendum-176
lesson from the crosshair miss - the check protocol now reads the
FULL TOOL VERDICTS block, every red named and fixed before any
push (no fixing the loud red while the quiet one sits).


## Addendum 177 - the census prints the GPU footprint; the compile gate keeps the default python

Two rulings: "in the benchmark don't print total ram usage, print
gpu ram usage. it is confusing to read because the estimates are
for gpu" - the census line now reads the estimate's own scope:
"census: GPU 3.49 GiB (est 3.84) - weights 1.9, context 1.4,
compute 0.06" (the whole-machine total is out of the print; the
no-device-split fallback says so explicitly). And "only check the
default python version fo compil" - the 3.13 setup-python gate is
removed; one compile gate on the workflow's default (3.12).


## Addendum 179 - the mutmut staging limit registered; the selection scoped to it

The third mutmut baseline crash (full_benchmark ModuleNotFound,
after code_edit and the same class twice) exposed the structural
limit: mutmut stages ONLY the mutated sources (AI_tools/) plus the
selected tests - the repo root never enters the staging dir, so
any test importing root modules (full_benchmark, infra.*) breaks
the baseline no matter the sys.path setup. test_seams imports
full_benchmark in 3 places - it cannot run in staging.

THE SCOPE: the mutmut selection drops test_seams (its code_edit
coverage is carried by test_code_edit_robustness and
test_code_edit_cli, which import only staged paths). The
session-40 verdict wanted seams IN for a fair score; the staging
limit rules that out - registered as the tool's known limit, not
silently worked around. code_edit's mutation score is a LOWER
BOUND over the cli+robustness tests.

Also this delivery: the I001 noqa on the seams import block (the
path-setup constraint suppresses the sort), the validator inline
(ty), the E402s - the full red-chain of the day burning off.


## Addendum 180 - the v7.1 analysis plan pre-registered: the quant effect by climb strategy

The author's plan for when the v7.1 run lands: "I want to add a
few other models if disk space allows it and analyze the effect
of quants in q,k,v based on the climb strategy. we could either
propose a climb strategy from the findings or declare one of the
three as the best."

THE ANALYSIS (pre-registered, graded when the arms blocks fill):
1. PER-CELL QUANT EFFECT: for every cell where >= 2 arms measured,
   the score delta against the config delta - which axis (wq, kq,
   vq) moved, in which direction, and what it cost/bought. The
   64-record v7.0 census said the estimator's terms were the
   story; the v7.1 arms say what the SCORE says.
2. THE PATTERN TEST: pool the deltas by axis - if weights moves
   dominate the score effect (the addendum-162 P2/P3 hint:
   Qwen3.5-0.8B@262k gained +48% from better weights), the
   allocation question has an answer: fund weights first.
3. THE VERDICT, one of three:
   a. ONE STRATEGY WINS - declare it (per-cell or overall);
   b. A PATTERN EMERGES - propose a climb strategy FROM it (e.g.
      "climb weights to the top rung before touching KV", or
      "the KV axis pays at deep ctx only") - registered as a
      proposal, measured by a targeted run;
   c. NO SIGNAL - the policies are score-equivalent within noise
      at the budget line; declare greedy the default (simplest)
      and register the insensitivity as the finding.
4. NEW MODELS: the disk-space question gates the roster
   extension - candidates from the findings-adjacent families
   (the granites 3.2/3.3 placeable but unmeasured; gemma-3-4b
   paper-sourced). Each addition = disk for its f16 + the _0
   rungs the climb visits.

The pre-registration: no strategy proposal before the deltas are
pooled; the verdict cites the cells that made it.


## Addendum 181 - the seams split re-arms the mutation selection; the position print

The author's rulings: "Do 1. Let's reduce the number of survivors."
and "Add to the benchmark to print the model position in the list
as x of n models in the benchmark."

1. THE SPLIT: test_seams.py's 56 code_edit-only tests move to
   tests/test_code_edit_seams.py - a file that imports nothing but
   code_edit, so it RUNS in mutmut's staging dir and re-enters
   the selection (addendum 179's staging limit, addressed at the
   test side instead of accepted). The 5 root-module tests stay
   in test_seams.py (check_requirements x2, score_fwe x2,
   resolve_f16_local - they import full_benchmark/ruler_gate/
   infra and cannot stage). The survivor-heavy core
   (_verify_blocks 411, _apply 273, _check_delimiters 242 - 926
   of the 1834) faces the strongest tests again; the next tally
   shows how many die. The session-40 verdict (seams in for a
   fair score) is finally honored via the split.

2. THE POSITION PRINT: every cell banner now reads
   "=== <fam> (model x of n) ctx=..." - the plan's param-ascending
   family order, computed once from the plan. The author's
   running-output readability ask.


## Addendum 182 - the formal layer built out where it is superior; the Wilson pin retired

The author's rulings: trust formal methods where they are clearly
better; keep tests only where they cover genuinely different risks;
remove tests that duplicate formal coverage.

DONE (all three from the author's picks):
1. MUTMUT SCOPE (#1): bench/v7.py cannot enter the staging dir
   (it imports infra/, the same staging limit as test_seams) - its
   pure core gets CONTRACTS instead (the proofs cover the same
   ground mutation testing would): the 4 new crosshair contracts
   (below). The mutmut source_paths stay AI_tools (the staging-
   compatible set); the estimator's mutation ground is now PROVEN,
   not sampled.
2. THE V7 GRID CONTRACTS (#5): spans/ctx ascending (the dyadic
   ladder law), the FORMAT THEOREMS - q4_0 = 18/32 and q8_0 =
   34/32 bytes/weight, weights_gib proven EXACTLY equal to the
   structural derivation over ALL params (crosshair, whole
   domain). The constants stop being registered magic: they are
   theorems about the block formats. The matching pin
   (test_v7_grid_theorems.py) carries the traceability markers
   (ascending grids, spans-fit-ctx = R-28's root, the format
   constants).
3. THE WILSON PIN RETIRED (#7 read as the equivalence cleanup):
   test_wilson_interval_extremes_and_middle checks 3 fixed
   points; the contract + 3 hypothesis properties prove the same
   bounds over the whole domain. The pin is deleted; the proofs
   stay (they are strictly stronger). THE PRECEDENT: when a pin's
   every assertion is an instance of a proven contract, the pin
   goes - the traceability marker moves to the contract file.

The split's own fixup: test_convert_quant_deletes_tensors_after_f16
moved back to test_seams (it imports infra - my grep missed the
from-import form); test_seams drops its unused code_edit import
(55/6 test split stands).


## Addendum 183 - the retirement audit: only the v7.1 machinery survives

The author's ruling: "We only need V7.1 machinery. Rest is dead
code." The import map, built from the code:

THE V7.1 LIVE SET (kept):
- full_benchmark.py (the orchestrator; its v7 task path)
- bench/v7.py, bench/state_store.py (validate_state, save/load),
  bench/constants.py (only what v7 + the gate read), bench/tee_output
- infra/* (llama_server, hf_download, convert_quant, git_ops),
  etc/registry_data.py, ruler_gate.py (the VT constants, task
  builders, score_vt, format_ok_vt - v7 imports it heavily)
- AI_tools/code_edit.py, md_check.py (the editor, R-26), the gates
  (requirements_check, validate_jsonl)

THE DEAD SET (retired):
- law_fit.py (12% coverage, imported only by depth_probe - also
  dead - and one contract ref): the standalone analysis tool.
- depth_probe.py, lag_analyze.py, session_replicate.py: the
  standalone instruments, nothing imports them.
- speed_gate.py: the streaming conversation gate - the v5 speed
  cells used it; v7 measures no speed cells. bench/cells.py (the
  v5 cell machinery) and bench/certify.py's rung controllers die
  with the vt/speed/all tasks.
- code_search.py: the dev tool, unused since session 40.
- size_predict.py: the v5-era size table.

THE TASKS: choices shrink to ["v7"] - vt/speed/all are the v5
controllers (R-05 already retired ARC/FWE; this finishes the set).
Historical state cells stay readable (R-22's schema reads them;
the readers for retired namespaces were already gone).

SEQUENCE: delete the dead set; strip full_benchmark's v5 task
branches and the v5 imports; the R-05 row's history clause covers
the retired cells. Suite follows (the v5 tests retire with the
code they pinned). Registered as one R-21 pass.


## Addendum 184 - speed_gate restored: the winner's certification step

The author's ruling: "Speed gate will be run on the overall
winner of the memory category. As soon as we have the 32 models
result, we measure speed gate on the winner. Get rid of the rest."

Addendum 183 retired speed_gate as dead code; the author's ruling
supersedes: the speed gate is NOT dead - it is the CERTIFICATION
step of the v7 deliverable (addendum 98's design: the argmax goes
through the speed gate at the winner's OWN ctx - a 262k
recommendation must hold the reader wall at 262k). The rest of
addendum 183's deletions stand (the v5 task controllers, the
standalone instruments, the v5 cells/certify machinery).

THE FLOW, registered: (1) the 32-model v7.1 run completes - the
argmax is the winner (model, config, ctx); (2) the speed gate
runs on THAT config at THAT ctx - the reader-wall verdict at the
recommended cell; (3) the page's winner section carries the
verdict (pass/stall-rate at the winner's ctx, the reader line).
The gate measures ONE cell - the winner's - not a per-model sweep:
the certification is the last gate the argmax passes before the
recommendation is published.

The pre-registration: the winner (currently Qwen3.5-2B@262k
Q8_0/q8_0/q5_0 at 4 GiB, subject to the 32-model field) passes
the reader-wall test at its own ctx - a stall-rate verdict at
the winner's depth, per the v3.1 protocol constants (5.0 w/s
line, 0.45 s reaction, cal-50 corpus, n=50 conversations).


## Addendum 185 - the retirement burn-off: v5 requirements RETIRED; the speed-gate certification parameters

The retirement's second pass, graded from CI (every red named):
- the v5 test files (code_search, size_predict) deleted with their
  modules; test_speed_gate stripped of its 9 v5-controller tests
  (the gate-native 21 stay - the winner's certification machinery);
  test_properties/contracts cleaned of the v5 machinery tests.
- R-01/02/03/06/09/10/11/13/14/15 RETIRED in the protocol - the
  v5 controller requirements, each with its live v7 successor
  named in the row (resume/config-drift, findings, contracts,
  answers logging, the argmax page). The traceability gate
  passes: 40 requirements, all pinned or retired.
- v7.py's acquire path import fixes (convert_quant, the E402s).

THE SPEED-GATE CERTIFICATION PARAMETERS (the author's ruling):
"we're doing only 2 sigma confidence, 20 conversations instead of
50. As long as 15 pass the gate it is done" - the winner's
certification: n=20 conversations from the cal-50 corpus, the
stall-rate verdict at 2-sigma confidence, PASS at >= 15/20
conversations stall-free (75% - the 2-sigma band on n=20). One
cell, one config, once - the last gate before the page.


## Addendum 186 - the search-strategy findings pre-registered (the paper's discussion skeleton)

The author's ask: "For this research we have been running all
the models from 8k to 256k with the three arms. Let's determine
what's the optimum strategy to look for the champion." The
skeleton below is REGISTERED BEFORE the full-32 field lands, so
the final numbers slot into a pre-registered structure rather
than a post-hoc narrative.

THE EXHAUSTIVE BASELINE (what v7.1 measured): the full grid -
every family x every trained-window-feasible rung x the three
allocation arms (only where they diverge). It is the gold
standard any cheaper search is graded against.

1. START DEEP. The separating information lives at the budget-
   binding rungs: shallow cells are cheap but nearly
   uninformative (all arms agree on config; scores cluster),
   and reach - the champion's defining feature - only exists
   at depth. RULE: start at min(trained_window,
   budget_feasible_depth); one cell, one arm, and the score
   there ranks the field's top half.

2. THE CLIMBING ARM IS A FUNCTION OF KV GEOMETRY, knowable
   from the registry BEFORE any measurement: weights-geometry
   families (many layers, wide KV) take GREEDY (weights
   fidelity is what scores); thin-KV families (few layers,
   single kv-head) take STINGY (the cache axis pays: Llama@
   131k +79%, MiniCPM5-2B both cells). RANDOM is the control,
   never the candidate - it won nowhere outright.

3. THE COARSE-TO-FINE SCHEDULE (3x cheaper than the grid):
   (a) one arm, deepest feasible rung, whole field -> the top-3
   candidates (~32 cells); (b) the candidates' full curves, one
   arm (~20 cells) - the shape (rising/peaked/declining) says
   whether deeper or other arms can help; (c) arms only at the
   finalists' budget-binding cells (~8 cells). ~50 cells vs the
   ~150 the grid cost; the loss is the null-arm verification,
   which the exhaustive baseline already banked.

4. SKIPPABLE, WITH REASONS: (a) shallow cells where the
   estimator proves all arms agree - the config is identical by
   arithmetic, the measurement re-proves nothing; (b) a family
   below ~0.5 at its BEST rung - the scores-desert is flat, no
   observed family jumps from 0.1 to 3.0 with depth, cut the
   family not the rung; (c) unreachable-by-window rungs (R-19
   machinery); (d) NEVER skippable: the winner's neighborhood -
   every rung of the top-2, every arm at their peak (the
   multi-arm deltas flip cells: Llama's +79%).

THE SCORING SYSTEM, for the discussion section:
ADVANTAGES - partial recall is measured, not discarded (a model
finding 3 of 5 names earns 3/5 - the desert's residents
separate BY HOW MUCH they fail); the fixed corpus makes scores
comparable across (family, ctx, config); the reach axis is
honest (unreachable grades excluded - a bigger window strictly
raises the attainable max, bigger cannot fake a win).
DISADVANTAGES - the credit signal is weak at the bottom (n=1
per grade: single-answer luck moves small scores - K=1 was
ruled for cost, the price is variance); single task shape (VT
only - a model bad at variable-tracking but good at
summarization scores zero: a fairness limit, not a capability
limit); one fixed haystack (a tokenizer-friendly family gets a
bonus unrelated to its window; the n+1 corpus seed rule is the
registered mitigation, unexercised so far).

FOR PRACTITIONERS: one line - the champion (model, config,
ctx) and the memory it needs. FOR RESEARCHERS: the search
findings above, the two-regime allocation rule, the format
theorems (the _0 sizes are structural and provable; the
K-quant bookkeeping hazard is a CLASS of estimator risk), and
the honest negatives (granite's value-vs-names malfunction,
MiniCPM5-1B's template echo, the scores-desert as the
difficulty signal).

GRADING: when the 32-model field lands, each numbered finding
grades against the full data - a prediction that fails is
registered as such (the pre-registration discipline; the
skeleton does not bend to fit).


## Addendum 187 - SmolLM3-3B exposed two under-estimates; the constants corrected

The author's question: "Any model that needs better vram
predictions to work properly?" - YES: SmolLM3-3B, the first
newcomer with census records, exposed two under-estimating
constants (caught by the addendum-171 replay pin - it would
have failed CI on the next push):

1. Q5_0 WEIGHTS: 0.6875 -> 0.70. The structural form (22 bytes/
   32 weights) under-counted ~1.6%: SmolLM3's measured Q5_0
   model buffer backs out to 0.6987 bpB. The format theorems
   held for q4_0/q8_0 (their block scales are exact) but the
   5-bit blocks carry padding the simple form misses - the
   register takes the measured upper bound (addendum 170: an
   under-estimate is an error). NOTE: the census-based constant
   means Q5_0 joins Q4_K's class (measured, not derived) - the
   q4_0/q8_0/f16 theorems stand.

2. COMPUTE FLOOR: 0.06 -> 0.075 GiB. SmolLM3's census intercept
   is 0.074; the floor under-counted every cell by ~0.014 GiB.
   The slope (1 KiB/token) was confirmed exactly (1.01 measured).

REPLAY: all census records in the v7.1 state now pass with est
>= measured GPU - zero under-estimates. The addendum-186 search-
strategy skeleton's skip rules rest on this estimator; the
corrections keep them honest.

ALSO: the crosshair red fixed for real - the tmp write is
crosshair's own sandbox artifact (not bytecode); the proof run
now carries --unblock=open:/tmp.


## Addendum 188 - R-41: closed form or retirement (Q5_0 retires); the BW efficiency factor on the page

Three rulings. First: "We need to either find a closed form for
q5_0 or retire it. Make a requirement to have a closed form
formula for size calculation." The investigation: SmolLM3's Q5_0
census backs out to 0.6987 bpB vs the structural 22/32 = 0.6875;
the embed-at-Q8 hypothesis fit SmolLM3 (0.6998 blended vs 2.001
measured - within 0.15%!) but does NOT generalize (the solved
vocab came out 44k/17k/25k across three families - inconsistent
with their real vocabs; llama.cpp's quantizer keeps
high-importance tensors above the target per-tensor, a mix
the (params, vocab) registry cannot predict). NO CLOSED FORM ->
Q5_0 RETIRES from both ladders. R-41 registered: every size
constant on a ladder must have a closed-form derivation from
the format's block structure; a census-calibrated constant is
a finding, not a ladder rung. The ladders are [Q4_0, Q8_0, F16]
weights / [q4_0, q8_0, f16] KV - every constant exact.

Second: the page's bandwidth note now carries the EFFICIENCY
FACTOR: the law's 76.5 GiB/s is the measured effective
bandwidth (~75% of spec) - "do not compare against your RAM's
rated speed; compare against ~75% of it." Spec bandwidth would
underpower every recommendation by a quarter.

Third: the champion's BW position computed (the demonstration
of the search strategy): Qwen3.5-2B@262k decodes 16.9 t/s ->
7.0 w/s at 76.5 eff - 1.4x the reader line; needs 51 GiB/s eff
(68 GB/s spec-equivalent). NEXT SIZE TARGET: the 6-8 GiB class
(Jamba2-3B@262k is 3.02 scoring at 8-GiB-class memory; the
doubling curve: 6 GiB -> 4.5 w/s (still readable), 8 GiB ->
3.5 w/s (below the line) - the 6 GiB budget is the natural
next grid for the search strategy.


## Addendum 189 - the q4_0/q8_0/f16 formula audit: the closed forms HOLD

The author's concern: "Check that the q4 and q8 matches the
formula. I'm very concerned that q5 didn't match." The audit
backs out the measured bpB from every cell's own census record
(both state files, the cell records only - arms without their
own census excluded to avoid config mismatches):

Q8_0 (closed form 34/32 = 1.0625): the FULLY-RESIDENT families
match to the fourth decimal - granite-3.1/3.2/3.3 (1.0625,
+0.00%), SmolLM3-3B (1.0625, +0.00%), Jamba2-3B (1.0626,
+0.01%). THE FORMULA IS EXACT where the census sees the whole
model. The -10..-17% records are the KNOWN host-offload
families (Qwen, Qwen3, MiniCPM5: part of the embedding stays
host-side, addendum 136) - the census records GPU-RESIDENT
weights, a deliberate under-count the estimator accepts rather
than modeling per-family offload splits. MiniCPM4-0.5B at f16
shows the same signature (-0.02%... wait, -0.02% is exact);
MiniCPM5-1B at f16 -18.57% confirms the offload class.

F16 (closed form 2.0): 1.9988-2.0004 across every fully-resident
family (+-0.06%) - EXACT. Llama +0.01%, granite, gemma,
Qwen2.5 all within 0.02%.

Q4_0 (closed form 18/32 = 0.5625): ZERO own-census records -
the runs never measured a Q4_0 cell with its own launch's
census (the addendum-187 alarm on Jamba2@262k stingy was the
config-mismatch false positive: the arm inherited the greedy
cell's Q8_0 census). Q4_0's formula is UNTESTED by census but
DERIVED from the same block arithmetic q8_0 proves exact
(16 payload + 2 scale per 32 weights; q8_0's 34/32 confirms the
2-byte scale byte is real).

THE Q5_0 CONTRAST, now sharp: q5_0 diverged +1.6% ON THE SAME
families where q8_0 is exact to 0.01% (SmolLM3: Q8_0 +0.00%,
Q5_0 +1.6%) - the divergence is the 5-BIT format's per-tensor
importance mix, not a census or offload artifact. The closed
forms that survive: q4_0/q8_0/f16 - all simple block shapes
(payload + ONE fp16 scale). The formats that fail: Q5_K, Q4_K,
Q5_0 - all the formats where llama.cpp layers extra bookkeeping
or per-tensor rules on top of the simple block. THE PATTERN:
the ladder's rule is "simple block format or retire" and the
census is the arbiter.

REGISTERED: the estimator's host-offload acceptance note moves
from folklore to audit result - the offload under-count is
-10..-19% for the affected families and CONSERVATIVE (never
over-quotes GPU), consistent with addendum 136's ruling.

## Addendum 190 - CI goes on-demand: the every-push suite is too expensive

The author's ruling: "We need to stop ci and you looking for
result of the tests. It's too expensive." The push-regression
suite (~5 min/run, 13 gates, mutmut the heaviest) ran on EVERY
push - and with the benchmark's artifact rail pushing per
model, that was dozens of paid minutes per benchmark run plus
my result-hunting turns on top.

THE CHANGE: the workflow's `on:` triggers shrink to
workflow_dispatch (manual) + a weekly Monday 03:00 UTC cron.
Ordinary pushes run NOTHING - no tests, no emails, no verdict
to hunt. The full 13-gate suite is unchanged and runs on
demand: the author (or the agent, when asked) dispatches it
when a check is wanted; the weekly cron is the standing
backstop. Wow.md rule 1 rewritten to match: read a verdict
only when asked or when a run is known dispatched - the
every-prompt and every-push habits are both retired, this time
by economics.

## Addendum 191 - no test updates either; the suite is frozen

The author's ruling: "Do not update tests either. Too
expensive. I think the benchmark is in a good place now."

The suite freezes at its current state: 253 tests, all green,
pinned to 40 requirements. No new test files, no edits to
existing ones - the author's ruling is that the marginal value
of further test work is below its cost. Wow.md rule 2 carries
it: nothing runs locally AND no test updates; the weekly CI
cron (addendum 190) verifies the frozen suite against whatever
the code becomes. If the code drifts and a frozen test breaks,
that is a finding REPORTED to the author - never a silent test
edit to make it pass.

SESSION STATE: the benchmark is in a good place - the author's
own words, on record as the session-close signal. v7.1
machinery complete and running; the 32-model extension filling
the state; the search-strategy skeleton pre-registered
(addendum 186); the format theorems audited (addendum 189);
the ladder [Q4_0, Q8_0, F16] with every constant closed-form;
CI on-demand; the suite frozen.


## Addendum 192 - the q5_0 source-verified closed form: our measurements CONFIRM it, and R-41's verdict stands sharpened

The author found the source-verified q5_0 analysis (llama.cpp
master, Oct 2026): block_q5_0 = 2 (d) + 4 (qh) + 16 (qs) = 22
bytes/32 weights = 0.6875 bpb exactly, straight from
ggml-common.h's struct. THE FORM IS REAL AND WE CONFIRM IT.

THE CROSS-CHECK against our census measurements:
- q8_0: their form 34/32 = 1.0625; our census measured
  1.0625-1.0626 on the fully-resident families (+0.00-0.01%).
  THEIR FORM AND OUR CENSUS AGREE TO THE FOURTH DECIMAL.
- q4_0: their form 18/32 = 0.5625 - the same block arithmetic
  we derive; untested by our census (no own-census records),
  now source-verified instead.
- q5_0: their form 0.6875; our census measured 0.6929-0.6987
  (+0.79/+1.15/+1.63% on granite/Jamba2/SmolLM3) - and THEIR
  OWN CAVEAT SECTION PREDICTS EXACTLY THIS: "embeddings, output
  head, and norms usually stay at fp16/f32, so real GGUF files
  come out slightly above 0.6875 x N."

THE SHARPENED UNDERSTANDING: the closed form is exact for the
QUANTIZED BLOCKS; the overshoot is the MIXED-PRECISION TENSORS
the quantizer keeps above the target. Neither pure hypothesis
fits the overshoot (embed@f16 predicts +5-14%, embed@q8
predicts +1.5-4% - the measured +0.8-1.6% is a PARTIAL,
importance-driven mix), which is why no closed form can predict
the FILE size from (params, vocab) alone.

R-41's VERDICT STANDS, now with the mechanism named: the
ladder's admission rule was "closed form for SIZE" - the precise
statement is "closed form for the whole FILE", and q5_0's file
size is block-exact PLUS a family-dependent mixed-precision
tail the registry cannot see. q5_0 stays retired from the
ladders; the census stays the arbiter; the source verification
is registered as the confirmation, not the reversal.

BONUS CONFIRMATIONS from their doc: the KV formula matches ours
(2 x layers x ctx x kv_heads x head_dim x 2 bytes f16 - the
same term in _alloc_total); the q4_1/q5_1 rows in their format
table match the constants we retired with the _1 ruling; the
GPU-offload note ("the formula is exact for GPU offload
(VRAM)") matches our addendum-136 GPU-scope ruling.

## Addendum 193 - the state files pruned to the approved ladders

The author's ruling before restarting: "Remove from the state
file any cell using quants outside the approved list. Then it
will be clean." Executed on all three state files: any CELL
whose (wq, kq, vq) is off the closed-form ladders
([Q4_0, Q8_0, F16] / [q4_0, q8_0, f16]) is deleted, and any
ARM record with an off-ladder config is pruned from its cell's
arms block. Verified: ZERO off-ladder records remain.

PRUNED: v7-1 state 15 cells + 27 arm records (the Q5_0-era
configs: the granite twins' 65k peaks at Q5_0/q8_0/q5_0,
SmolLM3's Q5_0 cells, MiniCPM5-2B's, Jamba2's stingy arm, the
champion's old q5_0-V cell); the v7.0 state 9 cells + 8 arms;
the stingy sidecar 3 cells. Kept: every on-ladder cell (60 in
v7-1, 44 in v7.0, 4 in the sidecar).

CONSEQUENCE, on record: the champion's 262k cell (Q8_0/q8_0/q5_0,
6.878) is GONE with its q5_0 V cache - the surviving best is
Qwen3.5-2B @131k (Q8_0/f16/f16, 6.787), a clean-ladder config.
The rerun will climb the approved ladders only: the champion's
262k cell re-measures at a q4_0/q8_0/f16 V cache, and the
ranking's deep end re-derives from clean configs. No config-
drift re-measures fire (the off-ladder cells are deleted, not
stored); the run measures exactly the missing clean cells plus
the never-measured newcomers.

## Addendum 194 - the clean-ladder run graded (addenda 180/186 pre-registrations)

THE FIELD: 23 families, 94 cells, 131 arm records, 36 multi-arm
cells - the single-era, single-ladder table. Every config
closed-form ([Q4_0, Q8_0, F16] / [q4_0, q8_0, f16]).

THE CHAMPION: Qwen3.5-2B, peak 6.79 @131k (Q8_0/f16/f16) -
with the stingy arm at 262k scoring 6.81 (Q4_0/f16/q8_0). THE
ARGMAX IS INTERIOR on the multi-arm record: 128k 6.79 -> 256k
6.40 (greedy) / 6.81 (stingy) - the reach curve peaks at 131k
and the deepest rung is a wash between the arms. The old
Q5_0-era champion cell (6.878 @262k q5_0-V) is superseded by
clean-ladder configs within 1%.

THE ADDENDUM-180 VERDICT, graded on the clean data: (b) - A
PATTERN, now with the full field. The per-axis deltas:
- WEIGHTS-GEOMETRY families (deep KV): greedy/Q8_0-weights wins
  (Qwen3.5-0.8B@262k F16/f16/q4_0 5.92 >> stingy 4.76; Llama@
  65536 F16/f16/q8_0 1.00 > 0.73; SmolLM3@16k Q8_0 1.52 > 1.36;
  granite-4.0-micro/4.1-3b at Q8_0 rungs).
- THIN-KV/CACHE-GEOMETRY families: the cache axis pays (Llama@
  131k stingy q8_0-KV 1.47 >> greedy 0.89; Jamba2 both deep
  cells stingy wins; Qwen3.5-2B@262k stingy 6.81 > 6.40 - the
  Q4_0/f16/q8_0 shape outperforms Q8_0/q8_0/q4_0).
- RANDOM: 5 outright wins (phi-4-mini both cells, MiniCPM5-2B@
  131k, granite-4.0-micro 2 cells, granite-4.1@32k) - no longer
  "never the candidate" (addendum 186's prediction FAILS on
  the clean ladders: the coarser ladder makes the random path
  occasionally the best maximal config). Registered as a failed
  prediction, not bent.

THE ADDENDUM-186 SKIP RULES, graded:
- "below ~0.5 at its best rung -> cut the family": HOLDS (the
  desert is flat: the sub-0.5 families never jumped).
- "start deep": HOLDS (the top-3 all measured deepest-first;
  the separating cells are the budget-binding ones).

THE NEWCOMERS: phi-4-mini-instruct debuts at #4 (2.98, Q4_0
config) - the first Q4_0-weights family to place top-5;
granite-4.1/4.2-3b and the micros land in the desert-to-mid
band. The granite MoE micros do NOT clear 0.5.


## Addendum 195 - the champion's per-ctx marginal analysis (the author's three-regime framework)

The author's ruling on reading a reach curve, registered verbatim in
substance: "An substantial increase in score between rungs indicates
that the model clearly benefits from a larger context as it can solve
larger problems. A minimal change means the model doesn't get affected
by the context size, but cannot take advantage of it. So adding extra
context at some point is detrimental, specially as it means a decrease
in quants, that doesn't affect this task, but may affect others."

Three regimes: (1) substantial rung-to-rung gain = the model converts
context into solved problems; (2) flat = context-agnostic; (3) PAST
THE USEFUL POINT the extra context is DETRIMENTAL - the climb pays for
it with quant drops that damage tasks outside this benchmark even when
the reach task itself survives.

THE CHAMPION DECOMPOSED (Qwen3.5-2B, greedy arm, score by span band):

- ctx=8192:   total=2.06  (4k: 2.06)
- ctx=16384:  total=3.09  (4k: 2.06 | 8k: 1.03)
- ctx=32768:  total=4.42  (4k: 2.06 | 8k: 1.03 | 16k: 1.33)
- ctx=65536:  total=5.67  (4k: 2.06 | 8k: 1.03 | 16k: 1.33 | 32k: 1.26)
- ctx=131072: total=6.79  (4k: 2.06 | 8k: 1.03 | 16k: 1.33 | 32k: 1.26 | 64k: 1.11)
- ctx=262144: total=6.40  (4k: 1.92 | 8k: 1.03 | 16k: 1.20 | 32k: 0.94 | 64k: 0.90 | 128k: 0.40)

REGIME 1 holds through 131k: the rung deltas +1.03, +1.33, +1.26,
+1.11 are substantial rung after rung - the model keeps converting new
context into found facts, and each new band's score says so directly
(no band re-measures; the old bands are constant, the gain is the new
band).

REGIME 3 begins at 262k, and the decomposition shows the mechanism
exactly as the author predicted: the kept bands pay the quant tax
(4k: -0.14, 16k: -0.13, 32k: -0.32, 64k: -0.21 = -0.80 total across
the climb's quant drops) while the new 128k band earns only +0.40.
Net rung delta: -0.39. The extra context costs MORE in degraded
encoding on the old bands than the new band pays back - the reach
task itself absorbs the drop, but a task sensitive to the quant would
not. This is the interpretive framework for the paper's discussion of
the scoring system: the marginal rung delta is the readout, and the
band-level decomposition separates "new band earns" from "old bands
pay" - the delta alone cannot tell a stall from a tax.

CAVEAT, registered: the 262k greedy cell pays the tax; the stingy arm
at 262k scores 6.81 - the deepest rung is arm-dependent, so the
"useful point" ruling (131k) is the GREEDY curve's ruling. The
champion's certification and the page's final argmax wait on the
author's tie-break between the 131k greedy peak and the stingy 256k
arm.


## Addendum 196 - the quant cost-benefit rule scoped, the probe design pre-registered, and the 8-hour budget plan

THE TAU RULE, SCOPED (from the addendum-195 discussion): a cost-benefit
rule for a climb rung - benefit = the new band's score (band
decomposition), cost = the GiB-equivalent of bits shaved per axis
(closed-form ladder constants: Q4_0=4.5, Q8_0=8.5, f16=16 bpw), accept
while benefit > tau x cost. The FIELD VERDICT from the 35 multi-arm
pairs: NO GLOBAL TAU EXPLAINS EVERY ARM. The arms never isolate one
axis (zero single-axis pairs in 94 cells); the same-size multi-axis
drop produces every sign of delta-score across families (champion
stingy +0.41 at 262k, Qwen3.5-0.8B stingy -1.16, Llama-3.2-1B stingy
+0.58, granite-3.3 stingy -1.16). RULING: the rule is a PER-FAMILY
STOPPING RULE for a single climb (the champion's 131k stop holds for
any tau >= 0.19), NOT a cross-arm or cross-family law. Registered as
scoped; overfitting to the champion is the failure mode it guards.

THE NOISE CONFESSION, on record: every cell asks 1 sample per grade
(5 questions per cell). At n=1, arm deltas inside roughly +-0.2 are
unattributable to physics vs sampling. Part of the tau rule's
unexplained residual is MEASUREMENT, not quant effect.

THE PROBE, PRE-REGISTERED (the author's ruling: "Let's try the probe
on the champion"): a --v7-probe-axes mode that measures one cell's
axis-down variants on the SAME corpus - base config plus w-only-down,
K-only-down, V-only-down, then the pairwise drops - giving the main
effects and interaction table for one family. Champion @131k target
set: Q8_0/f16/f16 (base), Q4_0/f16/f16 (w), Q8_0/q8_0/f16 (K),
Q8_0/f16/q8_0 (V), Q8_0/q8_0/q8_0 (KV), Q4_0/q8_0/q8_0 (w+KV).
REPEATS: n=3 per grade inside probe cells (seeded, registered) -
without this no quant conclusion is measurable; the paired same-corpus
questions partially cancel the noise. A QUANT-SENSITIVE SIDE TASK
(arithmetic woven into the chain) is registered as design intent
(below); no probe result is graded until it exists and runs beside
the reach score.

THE DESCENDING-STOP SKIP RULE, PRE-REGISTERED: reach curves are
monotone up to the peak (champion: +1.03/+1.33/+1.26/+1.11 then
-0.39), so a descending traversal (largest ctx first) may STOP at the
first substantial decrease - the rungs below the peak only re-confirm
what the descent already established. CAVEAT registered: at n=1 a
single noisy decrease can trigger a false stop; the descent uses the
same noise band (+-0.2) as the arm comparison before stopping.

THE 8-HOUR BUDGET (the author's allocation ruling): the full 23-family
run cost 6.19 h wall (94 cells, 122 timed arm-records, ~4 min/cell
mean; champion cells: 131k ~5 min, 262k ~9.6 min/arm). Allocation plan:
(1) champion probe, ~2.0-2.5 h (6 configs x n=3 at 131k, plus the
262k probe cells for the stingy anomaly); (2) n=3 re-measure of the
champion's curve, ~0.5 h; (3) the arithmetic side-task build and probe
integration, ~1 h of measurements; (4) reserve ~4 h for the field-level
follow-up the probe results point at. NO full-field re-run inside this
budget.

THE ARITHMETIC INTEGRATION, design ruling sought: the author wants the
quant-sensitive side task INSIDE the existing benchmark, one-dimensional
(a single fused score). Sketch registered: the reach chain's found
facts feed an arithmetic step (the value chain carries a small sum -
"VAR A = 75640 ... what is A + B?"), so the reach chain search doubles
as the quant-sensitive probe; the fused score reports reach credit and
arithmetic credit with a registered weight. ONE-DIMENSIONALITY NOTE:
fusing costs the ability to read the two effects separately in the
headline number; the per-grade records keep the decomposition. The
exact weight and corpus changes are Daniela's ruling before build.
