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
