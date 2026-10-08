# Session 44 - the no-backward-compatibility ruling

## Addendum 109 - R-21: no backward compatibility

The author's ruling: "Remove any backward compatibility in full
benchmark. In this repo nothing is backward compatible except
explicitly requested." Registered as R-21 and pinned by
tests/test_precommit_env.py.

Removed in this pass:

- `v6_prototype.py` - deleted outright. It was the v6.1 sketch
  (superseded by the v7 reframe the same day, session 42) and was
  referenced by nothing: no test, no hook, no requirement. The
  b10964 build path it and v7 share is unchanged.
- `find_server`'s pre-reorg HOME fallback
  (`~/technical_reports/llama-b10964-gpu`) - `infra/llama_server.py`
  now resolves the binary repo-relative only and returns None when
  absent; `full_benchmark.py`'s check_tooling already fails loudly
  with install guidance in that case, so the fallback was a silent
  second chance, exactly the kind of compat R-21 retires.
- `certify_cells` (bench/state_store.py) - the FWE re-grading reader
  for the retired `certify` namespace. Historical certify/certify_arc
  cells stay in state files as history, but nothing reads them;
  the reader is gone (R-05 RETIRED finished).
- `_task_store`'s `.get(task, "certify")` fallback - an unknown task
  now KeyErrors instead of silently writing into the retired FWE
  namespace.

Kept, deliberately (not compat shims - the variant-attribution
ruling of session 40, addendum 26, and R-05's "history stays
readable"):

- `stored_variant`/`legacy` plain-int cell attribution: the
  never-re-measure rule (addendum 8) requires it - cells measured
  before variant tracking are attributed to the stored selection,
  so they load instead of being re-measured at real GPU cost.
- `--task all` (the combined speed+vt controller): a live mode, not
  a compat path.
- The `reports/` study's "legacy encodings" wording: prose about
  GGUF legacy-vs-K-quant formats, unrelated to code compat.

Coverage note: 12 tests in test_precommit_env.py now (10 + 2 R-21
pins).

## Addendum 110 - R-22: the state schema

The author: "Yes schemas are helpful. Databases out until we really
need them. No XML please." Parquet explained (columnar, typed,
compressed - wrong for our small nested data, right as a derived
results export if the full grid ever wants cross-cell analytics).

R-22: `validate_state` in bench/state_store.py. The failure modes it
replaces:

- full_benchmark.py had a SECOND, unguarded `load_state` (raw
  json.load, crash on corrupt) - now the orchestrator's loader is
  the guarded one, exactly one loader.
- state_store's old loader caught ALL exceptions and started
  fresh - silent loss of measured cells (the never-re-measure
  store's worst failure).

The schema is strict where machinery reads typed values (cell
records: int or {v,...}; v7 score: number or null) and loose where
state is prose (verdicts, tournament metadata). StateSchemaError is
a plain exception, so the crash rail owns it: traceback to
results.txt, git tail runs, the corrupt file is never wiped.

The R-22 pin class found its own test bug while at it: the corrupt
fixtures must nest under families.<name>, not at the state top
level - the validator correctly ignored the misplaced ones
(schemas work).

## Addendum 111 - the reachability honesty fix (first live v7 crash)

The first live pilot run crashed at the ctx=2048 cells: the
span-2048 grade HTTP-400'd ("request (2237 tokens) exceeds the
available context size (2048 tokens)"). R-19's reachability rule
(span <= window) ignored the template + query tail and the
generation headroom the server reserves for max_tokens.

Fix: `grade_reachable(span, hops, window)` - span +
PROMPT_OVERHEAD_TOKENS(128) + max(GEN_HEADROOM_TOKENS(192),
gen(hops)) <= window. The 2048-span grade at ctx=2048 is now
EXCLUDED, not asked. Plus: certify_v7 isolates a per-cell run_cell
failure into entry["error"] and moves on - one bad cell no longer
kills the run (the crash rail still owns real crashes).

The two tests that encoded the buggy rule (span==window reachable)
were corrected; a regression test pins the exact crash
(2048-span at 2048-window is unreachable). Suite 246.

Note for the rerun: ctx=2048 cells now have max_score 0 for every
family (no reachable grades); the first grade that can fire is
span=2048 at ctx>=2368... in practice ctx=4096. The ctx=2048 rung
of the grid is structurally inert - worth remembering when reading
the argmax (a 0/0 cell is excluded from ranking, not a zero score).

## Addendum 112 - preventing estimate-vs-server drift (the author: "do all")

Three layers, from measurement to proof:

1. PREFLIGHT (bench/v7.py): preflight_reachable_grades tokenizes
   the smallest and largest reachable grade's rendered prompt on
   the LIVE server per cell and raises PreflightError on overflow -
   reported per cell, never a crash. Both live crashes would have
   been caught before any question was asked.
2. PROPERTIES + CONTRACTS: hypothesis pins soundness (reachable =>
   the whole request fits) and monotone-in-window; crosshair proves
   monotonicity and BOUNDARY TIGHTNESS (minimal accepted window is
   exactly span+overhead+gen; one less is unreachable) - the exact
   spot the old span<=window rule was wrong. A first soundness
   contract draft was a tautology; crosshair flagged it (false at
   (1,0,1,0,128)) and it was replaced - the verifier auditing the
   contract author.
3. BOUNDARY INTEGRATION (tests/test_v7_run_cell.py): a
   FakeWindowServer with the real 400 semantics must agree with
   grade_reachable at every (window, grade) pair - run_cell never
   emits a request the server would reject. The old rule fails this
   at span==window, the exact live crash.

The process lesson, registered: never assert a token budget that
has not been MEASURED against the live server - arithmetic estimates
are for choosing what to ask, /tokenize is for verifying it fits.

## Addendum 113 - the zero-score diagnosis

The author: "not a single model has scored a single point - dumb
models, too hard, or broken?"

Machinery ruled out (the test was NOT broken): scorer sanity-checked
against a known-good answer; prompt structure verified (chains
embedded before the cut, template renders); and the historical
certify_vt for the same families shows the pipeline produces real
signal (granite-4.0-350m depth 4096: [0, 0, 4, 0, 0, 0]).

The reading: mostly #1. The two measured families are 350M models
whose historical vt verdicts are all "dead" - they failed the EASIER
old task (5 names at shallow depth). v7's pass rule is ALL h+1
names; a model that historically found 0-4 of 5 scores 0 under
all-or-nothing. Also #2 in the sense that the pilot's only-measured
cells so far are the dumbest half; MiniCPM4-0.5B and Qwen3.5-0.8B
are unmeasured.

Open suspect: run_cell uses ask()'s default no_thinking=True;
granite-4.0-h is a hybrid reasoning model - suppressed thinking may
cripple it specifically. History cannot arbitrate (old runs also
suppressed). Registered for the next run's reading.

Instrumented (run_cell): per-grade FOUND tallies (g["found"] - the
partial-credit sum that was being discarded) and three sample
answers per grade (one pass, up to two fails, answer capped at 200
chars). The next run's state separates "found some names" from
"answered debris" from "answered nothing" - evidence, not vibes.

## Addendum 114 - R-23: answers are always logged

The author: "start logging the answers, they are always important to
have for debugging. it should be a requirement." Registered as R-23.

run_cell(answers_path=...) writes one JSON line per question -
window, grade, expected names, value, found, ok, the RAW answer -
appended (never overwritten) next to the family's server log:
models/tournament-results/<fam>/<fam>-ctx<ctx>-v7-answers.jsonl.
Pinned by two tests (line count == asked; append on rerun).

Also registered (the author's ruling on thinking suppression):
no_thinking=True is the default and stays - if a designer offers a
no-thinking mode and the model cannot work in it, that is a design
issue of the model, not a harness bug. The granite-4.0-h suspect is
closed on that ruling: the finding (if it materializes) is reported
as-is.

Scoring, explained (the author asked):

- A cell's questions partition into GRADES = (span, hops) pairs;
  K=20 questions per grade.
- score = the MEAN over grades of (passes/asked) - a grade's rate,
  averaged equally: an 80% at 2k-span counts exactly as much as an
  80% at 256k, so reach earns its full weight.
- A PASS is ALL h+1 names of the chain (upstream VT's rule) - a
  partial trace is a broken trace. found/expected is logged per
  question for diagnosis, but earns nothing.
- UNREACHABLE grades (span + overhead + gen > window) are EXCLUDED
  from the mean - excluded, not failed (R-19).
- Example: ctx=16384 cell, window covers spans 2048..16384 => 15
  reachable grades; all-fail => 0.0/15.

## Addendum 115 - R-24: push per evaluated cell

The author: "make the benchmark push to git every time a context is
evaluated, so you can get results." Registered as R-24.

certify_v7(on_cell_commit=...) fires after each evaluated cell's
state save; full_benchmark wires it to v7_cell_commit - the
verdict_commit pattern (addendum 31) applied per v7 cell: stamp the
cell result, tee off, git_tail (state + answers JSONL + server log
+ results), tee back on. Failures are caught and printed, never
fatal - a git outage costs watchability, not the run. Skipped
(already-measured) cells do not fire; --no-git/dry-run disable it.

## Addendum 116 - R-25: the 5s hook

The author: "remove the [pytest] hook and move it to the weekly. We
can check properties by hand from time to time. Let's keep git
commit to <= 5s."

Measured: pytest --all-files is 28.2s of the ~36s hook (hypothesis
properties dominating); ruff/ruff-format/ty/md/requirements are
1.1-2.9s each. The pytest hook is REMOVED from .pre-commit-config;
the weekly workflow runs the full suite explicitly plus via
coverage. The remaining hook suite measures ~8s cold / ~4s warm
(ruff first-run installs its venv). R-20's intent is unchanged -
the hooks that remain are never bypassed; R-25 registers the speed
budget. Also: the agent stops pre-running `pre-commit run
--all-files` manually before committing (double effort) - commit
directly, git runs the hook once; investigate only on failure.

## Addendum 117 - R-25 compromise: hypothesis weekly, deterministic pytest in the hook

The author: "in the hook run pytest but not hypothesis. hypothesis
in the weekly."

tests/test_properties.py carries pytestmark = hypothesis_props; the
hook runs pytest -m "not hypothesis_props" (233 deterministic tests,
~20s - the honest number: the suite's cost is 234 small tests plus
import overhead, not just hypothesis); the weekly runs the full 255.
The R-20/R-25 pin asserts all six hook ids, the marker selection in
the hook entry, and the full-suite weekly step - properties can
neither silently re-enter the commit gate nor silently lose their
scheduled home.


## Addendum 118 - R-26: all agent edits through code_edit

The author: "make it a requirement, this cannot continue, we
developed a tool explicitly for the purpose of saving time, and
we're not using it :("

Registered as R-26. Every agent edit to repo files goes through
AI_tools/code_edit.py (edit, write, edit_many, safe_append,
replace_verified). Hand-rolled string replacement (heredocs, sed,
python -c open/replace/write) is prohibited: it is not a
transaction, and session 44 paid real debugging time for it (the
R-25 half-applied config edit - a mid-script assert skipped the
later steps silently; also the mystery rolled-back commits, whose
failure output tail hid the hook's rollback message). The session
notebook's chronological append is the one soft exception.

This addendum itself was written through code_edit (the insert and
this append) - eating the dog food from here on. Pinned by
tests/test_code_edit_required.py (transaction all-or-nothing;
atomic verified edit; the tool surface importable).


## Addendum 119 - R-25: the testmon hook (the remaining 4 seconds)

The author: "Let's find a use for the remaining 4 seconds. Is it
possible to tie a test to a file changed in pytest? It would be
amazing to have it run the unit tests corresponding to the files
changed only. More complex test go still in github."

pytest-testmon does exactly this: it maps every test to the source
lines it covers (.testmondata), and at commit time runs only the
tests whose covered code changed. Measured on the baseline map
(258 tests, one ~30s full run to build):

  bench/state_store.py changed  -> 41 tests, 2.8s
  bench/cells.py changed        ->  6 tests, 1.3s
  nothing changed              ->  0 tests, 0.2s

Wired as hook id `testmon` (testmon_hook.py) with the contract:
no map -> exit 0 with a note (the first full run is CI's job);
0 selected -> pass; affected failures -> non-zero, the commit
blocks; the map updates on success. The full suite (incl.
hypothesis) + crosshair still run on every push (push-regression).

The no-map pin test caught a real bug: the hook first resolved
.testmondata relative to the repo root, so a chdir'd test run
found the repo's live map instead of the empty tmp dir - the DB
path is now Path.cwd(), which is what pre-commit actually gives
us. Pinned by tests/test_testmon_hook.py (Pins: R-25).

Caveat: .testmondata is per-machine (gitignored). On the T14s the
first commit after pulling this passes through with the no-map
note until one full `python3 -m pytest tests/ -q --testmon`
(~30s) seeds the map.


## Addendum 120 - v7 made 10x easier: K 20 -> 2

The author: "The rest is too hard. It takes forever to run a
cell. Make it 10 times easier."

The lever is K, the questions per (span, hops) grade. The worst
cell was 8 spans x 5 hops x 20 = 800 questions, each paying its
span's prefill - hours per cell. K=2 makes it 80 questions,
exactly 10x fewer, without touching the grade grid or the
all-h+1-names pass rule (the difficulty structure is unchanged;
only the sampling thins out).

Consequences:
- the corpus artifact (state/v7-corpus.json) rebuilds on next
  launch - its grid block records k, so the mismatch is detected
  automatically and every contender gets the same new chains
- a grade pass-rate now moves in 0.5 steps (0, 1 or 2 of 2);
  fine-grained scores need bigger K later
- previously certified v7 cells measured at K=20 are NOT
  comparable with new K=2 cells - clear the v7 blocks before
  re-measuring (the old runs stay in the answers JSONLs)

Pinned by tests/test_v7_k_easier.py (K==2; 80 questions per full
cell).


## Addendum 121 - the 5-minute cell ceiling

The author: "Let's aim for 5 minutes max per cell."

K=2 (addendum 120) removed 10x of the work; the ceiling removes
the hardware variance - a cell on a slow machine can no longer
run for hours. Two pieces in run_cell:

- CELL_BUDGET_SECONDS = 300: a wall-clock check before each
  question; over budget -> stop asking, score what landed, mark
  the record budget_hit=True and wall_seconds so the truncation
  is visible in state, never silent
- k-major question order (k_i outermost): a truncated cell
  covers every (span, hops) grade at least once before any grade
  gets its second sample - the grid stays covered

Per-question elapsed_s now lands in the answers JSONL - the next
run gives real prefill+generation numbers to calibrate the
ceiling against.

Pinned by tests/test_v7_cell_budget.py (budget==300; k-major
grade coverage).


## Addendum 122 - questions match prefill time

The author: "OK prefill rate is a good indicator. Make the
questions match prefill time."

questions_for_span(span) = max(1, round(K * SPANS[0] / span)).
Prefill is ~s tokens at ~618 tok/s (T14s, measured over 1,908
speed-gate turns), so inverse question counts equalize prefill
time per span: span 2048 earns K=2 questions, 4096 gets 1, and
everything >= 4x the smallest span floors at 1 (every grade stays
measured). The full cell drops from 80 to 45 questions. The
corpus artifact records k_per_span in its grid block, so the
mismatch rebuilds it on next launch.

Pinned by tests/test_v7_prefill_match.py (inverse law; floor;
equal prefill product) and the updated 45-question grid pin.


## Addendum 123 - the 2k span dropped; K=1 flat

The author: "Honestly just drop the 2k span. Then everything is
k=1."

With the prefill-matched ladder floored at 1 for every span above
2048, dropping the 2k span makes the ladder vestigial - so the
simplification is total: SPANS and CTX_GRID both start at 4096,
K=1 flat, questions_for_span deleted, the k-major loop collapsed
to a single span-major sweep. A full cell is 7 spans x 5 hops x 1
= 35 questions.

The honest consequence, pinned rather than silently dropped:
phi-1, phi-2 and RWKV7-World-2.9B all have a 2048 window - below
the smallest ctx rung now - so they place in the registry but earn
no cell. (gemma-3-1b-it, Llama-3.2-1B, gemma-3-4b were already out
- missing registry extracts.) If the author wants the 2048-window
families back, the 4096 ctx rung is the knob, not the span grid.

Old K=2-era v7 cells in state are not comparable with the new
K=1 cells - clear the v7 blocks before re-measuring.
