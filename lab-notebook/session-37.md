# Session 37 - 2026-10-03

Opened 2026-10-03. Carrying over from session 36 (closed, 51
addenda): the n=21 completion command is QUEUED, NOT RUN (the
author's last-night ruling: nothing else runs that day) - the state
still shows 8 families at n=15, MiniCPM5-1B at n=7. The grading,
the domination rule's first application with the w/s gate, and the
--certify instrument all wait on that run. The sequential-testing
doctrine (addenda 48-51) governs all new experiment design.


### Addendum 1 - the ARC+FWE hybrid benchmark idea (named future work)

The author's idea (registered as a future-benchmark proposal, not
scheduled): mix ARC and FWE - the coded words in the FWE haystack
match the answer to an ARC question. The needle is found by solving
ARC: the question is asked such that the answer is hidden in the
haystack, and retrieval requires reasoning (solve the ARC problem)
BEFORE or WHILE scanning. Difficulty knobs to figure out: the ARC
problem's difficulty tier, the FWE depth (haystack size), the coding
scheme (how the answer is embedded in the coded words), and
possibly the number of distractor code-words that look like the
answer.

WHY IT IS INTERESTING (analysis): FWE as built measures PURE
retrieval (the needle is findable by scanning; no reasoning
needed). ARC measures reasoning with no retrieval burden. The
hybrid measures REASONING-GATED RETRIEVAL: the model cannot pass by
scanning alone (it must know what the answer looks like before it
can recognize it in the coded haystack), and it cannot pass by
reasoning alone (the answer is not in the weights - it must
retrieve). This kills a confound we registered all session: the
refusal and confabulation miss shapes are invisible to the scoring
- a hybrid needle has more ways to be wrong in INFORMATIVE ways
(wrong-answer-found = reasoning error; right-answer-missed =
retrieval error; the miss SHAPE becomes diagnostic).

OPEN DESIGN QUESTIONS (to settle before any implementation):
1. How is the answer embedded? (the coded words ARE the answer
   string? the answer is the decode KEY for the coded words? the
   ARC answer selects among coded candidates?)
2. Grading: does a found-but-wrong answer score partial credit
   (the retrieval worked, the reasoning failed) - or is it a clean
   miss?
3. Does the upstream RULER methodology have an analogous task
   (some of its suite mixes reasoning with retrieval)? Worth a
   literature check before building.
4. Calibration: the difficulty must be set so the field
   discriminates (not all-pass/all-fail - the k-collapse lesson of
   session 36).

STATUS: idea registered; no design decisions made; not scheduled.
The certification phase (addendum 50, session 36) has priority.

### Addendum 2 - the FWE pass criterion relaxed to 1/3; the disqualified mechanism retired

Timestamp: 2026-10-03 (before the n=21 completion run). The author's
two rulings, both implemented before the run so its data is collected
under the new rules.

RULING (a) - FWE passes at >= 1/3 words. The verdict form (registered
136b) was all-or-nothing: a cell passed only on a perfect 3/3. The
relaxation: a task passes when >= 1 of the 3 expected words is found
(partial retrieval counts). Implementation: score_fwe returns
len(found) >= 1 (the per-word count stays the 0..k diagnostic);
run_fwe_depth now also returns words_found (the per-task partial list,
both from fresh runs and from the CSV cache) so the 1/3 vs 2/3 vs 3/3
distinction survives into results; the tournament climb print shows
"{words}/3 words -> HOLD/FALL". The n=1 cell semantics are unchanged
otherwise (fwe_pass returns acc == 1.0; one sample, one verdict).

DATA-CONSISTENCY FLAG (the meta rule - decided together, not silently):
all tournament data so far (n=15/n=7) was collected under 3/3. The
saved tournament_falls encode the OLD criterion, and under 1/3 some
recorded falls become holds (the addendum-26 finding: every fall so
far was a partial 1/3 or 2/3, never 0/3 - so under the new criterion
the recorded fall depths are LOWER BOUNDS on the true ones, and the
resume mechanism would skip climbs whose fall cells need re-scoring).
Options for the n=21 run: (a) fresh start - wipe tournament_falls and
re-run all 21 climbs per family under 1/3 (cleanest, ~5-6 h at the
n=15 pace, but discards resume); (b) re-score the saved climbs from
the raw per-cell CSVs (the partial counts are in the climb CSVs on the
author's machine) and resume from the re-scored falls; (c) keep the
historical falls as-is and collect only the new climbs under 1/3
(INCONSISTENT - mixing criteria in one rank statistic; not
recommended, listed for completeness). My recommendation is (b) if
the CSVs are intact, else (a). THE AUTHOR DECIDES before the run.

RULING (b) - the disqualified mechanism is RETIRED. Both rules are
gone: the addendum-38 floor rule (zero holds in seven climbs) and the
addendum-44 domination rule (2-sigma-certified A vs zero-hold
candidate, w/s-gated, tournament-data-only). No model is disqualified
by tournament data; MiniCPM5-1B stays in the field on its measurement
alone. The DISQUALIFIED section is deleted from models.md; the stale
verdict prose (the rounds 6-7 floor-rule verdict, the n=15
domination-rule status block) is removed - retired rules pollute. The
author will supply a NEW policy; it is NOT invented here and will be
registered as its own addendum when given.

Code: ruler_gate.score_fwe, ruler_gate.run_fwe_depth (words_found),
full_benchmark tournament climb print. Tests: score_fwe relaxed
criterion (1/3, 2/3, 3/3 pass; 0/3 fails) in test_ruler_gate and
test_seams. 138 pass.

### Addendum 3 - NIAH removed, superseded by FWE

The author's ruling: the niah_single task is deleted from
ruler_gate.py. FWE superseded it - every quality verdict since
addendum 136b is FWE, and the tournament never runs NIAH. Removed:
WORD_BANK, NEEDLE_TEMPLATE, QUERY_TEMPLATE, KEYS, make_needle,
haystack_paragraphs, build_task, show_task, score_answer, run_depth,
the --needles and --task CLI args (ruler_gate is now FWE-only; the
CSV name is fixed at *-fwe.csv), and the seven NIAH tests. The
ladder-results/*-niah.csv artifacts stay (they are history, not
code). ANSWER_HEADROOM stays - FWE uses it. 122 -> 130 tests (the
rescore test adds one below).

### Addendum 4 - the re-score instrument (the author's ruling: re-score)

The author chose option (b) from addendum 2: re-score the saved
falls from the raw per-cell CSVs. rescore_tournament (new
full_benchmark mode):

    python3 full_benchmark.py --rescore --state-file state/benchmark-state-tournament.json <families>

Read-only by default: it walks every family's tournament_falls,
reads each climb's cell CSVs (models/tournament-results/<fam>/
climbN/*-fwe.csv, the partial column), and re-derives each fall
under 1/3: a cell with partial >= 1 is a HOLD, so a fall recorded at
a 1/3-or-2/3 cell moves deeper to the first 0/3 cell; a climb whose
recorded fall cell now passes is a PASS CHAIN - the true fall is
above it and unmeasured (the early stop never wrote the cells
above), so its saved fall is DROPPED and the next --tournament run
re-runs the whole climb under 1/3 (the resume mechanism treats a
missing key as fresh). A 0/3 fall is unchanged under both criteria.
--rescore-apply writes the re-scored falls; the plain --rescore
never touches state (verified by test). MISSING cells below a
recorded fall abort that climb's re-score (keep the recorded fall)
- the CSVs are the authority only where they exist.

THE AUTHOR RUNS (her machine has the CSVs) - read-only report
first, then apply, then the usual --tournament resume for the
dropped climbs (fish, one line each):

    python3 full_benchmark.py --rescore Qwen/Qwen3.5-0.8B Qwen/Qwen3.5-2B AI21/AI21-Jamba2-3B meta-llama/Llama-3.2-1B-Instruct openbmb/MiniCPM5-2B openbmb/MiniCPM5-1B ai21labs/AI21-Jamba-Reasoning-3B RWKV/RWKV7-Goose-World3-2.9B-HF google/gemma-3-1b-it --state-file state/benchmark-state-tournament.json

    python3 full_benchmark.py --rescore --rescore-apply Qwen/Qwen3.5-0.8B Qwen/Qwen3.5-2B AI21/AI21-Jamba2-3B meta-llama/Llama-3.2-1B-Instruct openbmb/MiniCPM5-2B openbmb/MiniCPM5-1B ai21labs/AI21-Jamba-Reasoning-3B RWKV/RWKV7-Goose-World3-2.9B-HF google/gemma-3-1b-it --state-file state/benchmark-state-tournament.json

### Addendum 5 - the n=21 round graded (3/3 criterion - the run predated the 1/3 ruling)

The author's run: 5h03m, seeds 16-21 fresh via resume, all 9
families at n=21, the first reliable-depth w/s medians. Table and
the ten-question grade are in models.md (THE n=21 ROUND). HEADLINES:
(1) SOLE CHAMPION - Qwen3.5-0.8B at 262,144 (mode 2x, median-deep
tail, two full holds): the n=15 co-champion is alone at the top and
its reliable depth ROSE to 8,192. (2) The 2B keeps the mode 32,768
but its reliable depth DROPPED 16,384 -> 8,192 - seeds 16-21 were
4,096-heavy. (3) Jamba2 is the only family whose mode rose
(4,096 -> 16,384). (4) The certified map at n=21: 4k covered at
both sigma levels (0.8B, 2B), 8k reliable (0.8B, 2B), 16k+ EMPTY.
(5) Seven of nine families certify nothing - the minimal-roster
retrospective (session 36 addendum 51) is confirmed by the data.
CAVEAT: all of the above is the 3/3 picture; the addendum-4
re-score re-derives it under 1/3 and will move falls deeper
(every recorded fall was a partial).

### Addendum 6 - code_edit incidents (wow.md section 4)

Reported and fixed per the standing rule:
1. The multi-block search_replace tool failed twice on
   multi-line old_str that was unique in the file but rendered with
   wrapped lines (the tool's error message shows wrapped text, not
   the file's actual lines) - worked around with scripted replaces
   with asserts (the established pattern; the sandbox quirk list
   already recommends it).
2. My first re-score implementation had two real bugs caught by
   its own new test: the CSV filename was derived as depth-minus-
   headroom (the climb CSVs are named at the raw depth), and the
   dry-run mutated the in-memory state (violating the read-only
   contract). Both fixed; the test pins them.
3. The code_edit.py md auto-fixer itself is sound (blank lines
   around tables, trailing newline); the models.md MD058 that
   appeared mid-session came from my own scripted edit BYPASSING
   code_edit - caught by md_check before commit and fixed. LESSON
   (already in wow.md): scripted replaces bypass the editor's
   auto-fixes, so every scripted md edit must be followed by
   md_check before commit - done here.

### Addendum 7 - the re-score dry-run report (read-only; the 1/3 criterion vs the 3/3 falls)

The author ran the --rescore report (no --rescore-apply, so the
state is unchanged - the next step is the apply). RESULT: 110 of 189
climbs are PASS CHAINS (their 3/3 fall cell was a 1/3-or-2/3
partial), ZERO falls moved to a deeper 0/3 cell, ZERO missing CSVs -
the cell data is intact and every recorded fall was either a
partial (now a hold) or a 0/3 (unchanged). Per family (chains/21):

    Qwen3.5-2B        20  (only its climb-15 top is kept)
    gemma-3-1b-it     20
    Qwen3.5-0.8B      19
    AI21-Jamba2-3B    17
    MiniCPM5-2B        6
    Jamba-Reasoning    9
    Llama-3.2-1B       9
    RWKV7-2.9B         9
    MiniCPM5-1B         1  (20 of its 21 falls are TRUE 0/3 - the
                          zero-hold profile is real under 1/3 too)

FINDINGS: (1) the 3/3 criterion was hiding MOST of the field's
retrieval - 58% of all falls were partials; the n=21 3/3 table
(models.md addendum 5) is a deep lower bound. (2) The miss-shape
split is now measured: Qwen/gemma/Jamba2 fail by partial (find some
words, not all); MiniCPM5-1B fails by zero - a retrieval failure,
not an aggregation one. (3) COST WARNING: the apply drops 110 saved
falls, and the resume run re-runs all 110 climbs under 1/3 with
DEEPER early stops than before - at the n=15 pace (~5.5 min/climb
at 3/3 depths) this is well beyond the 5h overnight window; the
deeper the climbs go the more cells each costs. The sequential
doctrine (session 36 addendum 48) applies: the re-run's purpose is
the CERTIFIED MAP, not the full table - the contenders are the 0.8B,
the 2B and Jamba2 (the families with a reliable depth); the
floor-dead families' modes will not change the map. THE AUTHOR
DECIDES the roster for the re-run (all 9 for the record, or the 3
contenders first).

NEXT (the author runs, fish, one line each):

    python3 full_benchmark.py --rescore --rescore-apply Qwen/Qwen3.5-0.8B Qwen/Qwen3.5-2B AI21/AI21-Jamba2-3B meta-llama/Llama-3.2-1B-Instruct openbmb/MiniCPM5-2B openbmb/MiniCPM5-1B ai21labs/AI21-Jamba-Reasoning-3B RWKV/RWKV7-Goose-World3-2.9B-HF google/gemma-3-1b-it --state-file state/benchmark-state-tournament.json

    python3 full_benchmark.py --tournament <same 9 families> --state-file state/benchmark-state-tournament.json

### Addendum 8 - the practitioner takes the helm; the certify controller built

The author will play the practitioner from now on - the study's
requests come as a practitioner's sequence, and every experiment
must answer one. The first sequence, answered from current data:

Q1 (a list per step with at least one pass): ANSWERED from the
n=21 state - every rung 4k-262k has 3-8 models with >=1 hold
(models.md's n=21 passes/rung vectors). Caveat given: a single hold
is weak evidence (the Llama n=5 lesson).

Q2 (the same table with a RELIABLE model per step): PARTIALLY
ANSWERED - 4k and 8k are certified (0.8B both; 2B both at 1 sigma),
16k+ is EMPTY at the n=21 1-sigma bar; the 0.8B's 12/21 at 16,384
is one hold short. The 1/3 re-run is the cheap path to fill it
(most recorded falls were partials).

Q3 (the practitioner's spec, verbatim intent): "a smart benchmark
that per step picks the most promising candidates and tests them
until they pass reliably or fail enough times to never pass at the
fixed n; then the next candidate. A model cannot be re-measured in
a cell it already measured - the cell being (model, run, step)."

IMPLEMENTED (the addendum-50 --certify instrument, now specified):

    python3 full_benchmark.py --certify 16384 <families> --state-file state/benchmark-state-tournament.json

- THE CELL MODEL: a cell is (model, run number, step), never
  measured twice. Historical cells are INHERITED from
  tournament_falls: climb s measured every rung up to and including
  its fall - cell passed iff the fall is deeper (or topped out),
  failed iff the fall IS the rung, unmeasured iff the climb stopped
  below. Direct certify cells persist in fst["certify"][depth].
- THE CONTROLLER: candidates ordered by promise (existing passes at
  the rung, then reliable depth); each is tested cell by cell
  (seed = run number, the lowest unmeasured run) until EARLY ACCEPT
  (1-sigma Wilson lower bound >= 0.5 over measured cells, count >=
  11 = half of n=21) or EARLY REJECT (mathematically dead: even
  passing every remaining cell cannot reach the bar). On accept the
  rung's w/s is measured (n=5 median); the first accepted model
  ANSWERS the rung and the rest are SKIPPED (one model per rung).
- OBSERVATION from the tests: the early-accept bar can fire before
  21 cells (11/11 accepts, lo=0.917) - sequential testing pays;
  the dead check uses the FULL n=21 horizon (best possible k/n),
  not the measured subset.

Tests: cell inheritance, accept+skip, early-reject-dead (the
fall-at-rung vs fell-below distinction caught a fixture bug - the
suite now pins it). 133 pass.


### Addendum 9 - the configurable FWE threshold; measure once, grade later; the two quality metrics

The author's ruling: the FWE cost is per-cell regardless of k, so
INSTRUMENT: measure at k=3 with the per-word partial ALWAYS
recorded, GRADE at any threshold later - no separate benchmarks.

IMPLEMENTED:
- ruler_gate: FWE_PASS_MIN (default 1); score_fwe and run_fwe_depth
  take min_words; the CSV-cache re-grade reads the stored partials,
  so a cached cell re-grades at any threshold without a rerun;
  --fwe-pass-min CLI flag (3 = the original strict form).
- full_benchmark: fwe_pass takes min_words; the certify controller's
  DIRECT CELLS now persist the partial count (0..3) instead of a
  boolean, so certify data also re-grades later.
- --diagnose: reads every climb cell CSV and reports per family
  (a) which RANK of the 3 expected words the found-words are
  (the zeta law: rank-1 is ~4x/9x more frequent - a >=1/3 pass
  that only ever finds rank 1 is a weaker claim than the threshold
  suggests), (b) the pass rate at >=1/3, >=2/3, 3/3. Flag when
  found-words are >70% rank-1.

THE DIFFICULTY QUESTION (the author's k=3-at-1 vs k=1): NOT the
same. The three words are unequally findable (rank^-2 counts), and
>=1/3 is a union of three doors including the easiest one; k=1
(the single most frequent word) is strictly harder than the union.
The relaxation mostly rescues models that find the top word but
cannot complete the aggregation - exactly the partial-fallers the
re-score found.

THE TWO QUALITY METRICS (the author's question: which is
stronger?): (1) threshold quality - how many of the 3 words a cell
finds (graded 1/3, 2/3, 3/3); (2) repetition quality - how many
cells pass (the Wilson-certified count). ANSWER: they measure
DIFFERENT failure modes and are not interchangeable. Threshold
quality grades the MECHANISM (partial retrieval vs full
aggregation) on one draw; repetition quality grades the RELIABILITY
(the probability the mechanism fires at all). The stronger measure
FOR THE PRACTITIONER is repetition at a FIXED honest threshold -
p(pass) is what a user experiences, and it is what the Wilson
certification already prices. Threshold quality is the DIAGNOSTIC:
it explains WHY reliability collapses (rank-1-only retrieval) and
it is the free upgrade path - if the certified map fills at 1/3
but the practitioner wants the 3/3 claim, re-grade the same cells
at 3/3 and re-certify with zero new compute. RULE: report both;
certify on repetition at the stated threshold; state the threshold
in every recommendation.

## Addendum 10: the mode is RETIRED - sigma only (2026-10-03, during the 16k certify run)

AUTHOR'S RULING (while `--certify 16384` runs): retire the mode
measurement; n selection is based on sigma only.

IMPLEMENTED: `tournament_rank` no longer computes any central tendency
of the fall depths. The mode-with-median-fallback (session 36
addenda 15/20) and its `rank_depth`/`rank_mode`/`rank_statistic`
fields are deleted; the rank is the WILSON statistics alone - the
per-rung pass vector, reliable depth (1 sigma), conservative depth
(2 sigma), ceiling, and the per-rung 1-sigma Wilson bounds. The
tournament table ranks by reliable -> conservative -> pass vector ->
ceiling and reports no mode column. Rationale: the mode was a
ranking convenience from the 5-climb era; the Wilson bounds already
price reliability honestly, and a model is what it reliably holds,
not what it most often fell at.

A HONEST MATH NOTE from the rewritten tests: at 1 sigma, 4/5 holds
(lo ~ 0.58) clears the reliable bar - a one-flicker family is still
reliable at its top rung at small n. The mode would have called the
same family "rank 262144" too; the difference appears at n=21 where
the Wilson bar (11/21 early-accept, 13/21 reliable) is what the
certify controller already enforces. The mode's retirement changes
the TABLE, not the certification math - the controller was already
sigma-only by design.

State note: the historical `tournament` snapshot in
state/benchmark-state-tournament.json still carries the old
`rank_depth`/`rank_mode` fields from the 3/3-criterion run - they are
a record of what was printed then, not live data; new runs write
sigma-only entries.

Tests: `test_tournament_rank_mode` -> `test_tournament_rank_sigma_only`
(rewritten to the new semantics; two of my initial asserts were wrong
- the flicker 4/5 and distinct-falls 4/5-at-4096 shapes are both
reliable at 1 sigma, the suite taught the real bars), and the two
family tests assert reliable_depth instead of rank_depth. 134 pass.

## Addendum 11: the web pages updated for the practitioner (2026-10-03)

AUTHOR'S RULING: update the pickers with the practitioner-facing
information, written for readers who have NOT read the report ("CI in
sigmas always better" - the mode was a good size heuristic, but the
confidence interval is the recommendation).

IMPLEMENTED (cpu-picker.html + gpu-picker.html, both JS-checked):
- The pool is the three CERTIFIED families (n=21, 1/3 rule): Qwen3.5-
  0.8B (reliable 8,192 / conservative 4,096, 34.85 w/s at reliable),
  Qwen3.5-2B (8,192 / 4,096, 27.79 w/s), AI21-Jamba2-3B (8,192 / no
  2-sigma claim, 6.84 w/s). The six uncertified families are excluded
  with a plain-language "why only three models" note (they did not
  pass reliably at any rung - including some with large advertised
  windows) instead of stale rejection-log references.
- depth is now the RELIABLE depth (1 sigma, Wilson lo >= 0.5); a new
  conservative column (2 sigma) is in both the verdict and the table.
  "None at 1-sigma/2-sigma" replaces "counting floor" zero-handling.
- w/s values are the reliable-depth medians (n=5), not the old n=1
  worst turns; the reader-line scaling law is unchanged.
- All protocol v4.3 / addendum / "n=1 screen" jargon removed from the
  reader-facing prose; "How the recommendation is computed" now
  explains the 21-runs-per-rung ladder, the 1-of-3-words pass rule,
  and both sigma levels in plain language, with the caveats stated
  (16k+ certification in progress = "not yet certified", not
  "failed").
- cpu-picker's machine-list floor is recomputed from the new pool:
  the most bandwidth-forgiving certified model is now the 0.8B
  (34.85 w/s), so the list floor drops to ~14.7 GB/s.

## Addendum 12: code_edit gap FIXED - replace_verified (2026-10-03)

AUTHOR'S RULING (wow.md section 4): the incidents were reported but
not FIXED - always fix, and propose improvements.

ROOT CAUSE of the addendum-6 incident class: the session's
workaround pattern for wrapped-line old_str failures was a
hand-rolled `python3 open/write` script with asserts. That pattern
BYPASSES code_edit entirely - no md auto-fixer, no md-lint gate, no
delimiter check, no atomic synced write. The MD058 that escaped to
git mid-session came from exactly one of those scripts (reported in
addendum 6 item 3, but the FIX was only "run md_check after" - a
discipline rule, not a mechanism; discipline rules fail when
forgotten, and wow.md says we make procedures error-proof instead).

THE FIX (mechanism, not discipline): `code_edit.replace_verified(
path, [(old, new), ...], count=1)` - the scripted-replace pattern as
a first-class transaction. Each old must occur EXACTLY count times
(the scripted assert, now enforced by the tool); pairs apply in order
against the running buffer; on any assert failure the file is
untouched. The assembled result then runs the FULL edit() pipeline:
the md auto-fixer (blank lines around tables, trailing newline), the
md-lint no-new-violations gate (MD055/MD056/fences), and the
delimiter balance check. A scripted replace can no longer smuggle a
lint break into git, and there is no longer a reason to bypass the
editor. Plus `code_edit.src_count(path, text)` as the exposed assert
helper.

Tests: 4 new (unique pairs apply + lint-clean, exact-count assert
with the file untouched and count=2 -> replace_all, missing target
untouched, the md pipeline actually runs - a table insert gets
auto-blank-lined and a ragged MD056 is refused before the write).
138 pass.


## Addendum 13: safe_append upgraded - the notebook-append pattern is markdown-checked too (2026-10-03)

THE AUDIT (wow.md section 3: a class of bug becomes a tool
guarantee): every notebook addendum this session went in via a
shell heredoc append, bypassing the editor - the same bypass class
as addendum 12. And the tool built to own that pattern,
safe_append, only checked PYTHON syntax; a markdown append ran no
auto-fixer and no lint gate.

THE FIX: safe_append to a .md/.markdown target now runs the SAME
pipeline as edit() before the write - the md auto-fixer (blank
lines around any table the addition introduces, the single
trailing newline) and the no-new-violations lint gate (a ragged
MD056 row or an unclosed fence in the addition is refused with the
file untouched). The addendum-21 guarantees (idempotent,
non-corrupting, atomic, python-compiles-first) are unchanged.

DOGFOOD: this very addendum was appended through the upgraded
safe_append - the first notebook entry to pass the gate. 2 new
tests (the auto-fix on append, the MD056 refusal with the file
untouched; python compile path re-pinned). 140 pass.


## Addendum 14: medals replace sigma language; the runs-only table on the pages (2026-10-03)

AUTHOR'S RULINGS: (1) add the runs-only data to the web pages;
(2) sigma language is academic - quality is communicated in MEDALS:
bronze = at least a pass, silver = reliable, gold = confident.

IMPLEMENTED (both pages, JS-checked and boot-smoke-tested):
- MEDALS replace sigma in all reader-facing prose: bronze = at least
  one pass out of 21 (it can work, expect misses); silver = reliable
  (>= 13/21, we are confident it usually works); gold = confident
  (>= 16/21, trust it on a bad day). The verdict reads e.g. "8,192
  tokens silver (reliable) - 4,096 tokens gold (confident) - 4,096+
  tokens bronze". Table columns: silver tok (reliable), gold tok
  (confident). Sigma survives only in code comments and the medal
  definitions in the how-paragraph (the 13/21 and 16/21 bars).
- THE RUNS-ONLY TABLE: a new section "All measured models - the runs
  behind the medals" on both pages - all NINE families x SEVEN
  rungs (4k..256k) with the raw passes/21 per cell and the medal the
  rung earned (e.g. Qwen3.5-0.8B: 17/21 gold at 4k, 14/21 silver at
  8k, 12/21 bronze at 16k, ... 2/21 bronze at 256k). "Nothing
  hidden" - the recommendation derives from this data.
- ERROR FIXED (mine, addendum 11): I had written Jamba2's reliable
  depth as 8,192 on both pages; the n=21 table says 4,096 (15/21 at
  the floor, 12/21 at 8k is short of 13). Corrected on both pages.
- BUG FOUND BY THE NEW SMOKE TEST (live on the GPU page, predates
  the medal edit): the no-eligible-model "closest fit" branch
  referenced r.m while the variable in scope is best.m - a
  ReferenceError that would have broken that branch in the browser.
  Fixed; the smoke test now exercises the full boot path.

A TOOL LESSON (addendum 12 upheld): all page edits went through
code_edit.replace_verified; the exact-count assert caught a
non-unique anchor mid-patch (the transaction rolled back cleanly,
no partial state) - the tool working as designed.


## Addendum 15: w/s measurement REMOVED from the benchmark (2026-10-03)

AUTHOR'S RULING (interrupting the certify run): we agreed NOT to
measure w/s as a disqualifier; counting w/s in the benchmark is a
waste of time. The assumption in place: a configuration selected
under the RAM ceiling has enough bandwidth to achieve 5 w/s.

IMPLEMENTED: both w/s measurement paths removed from
full_benchmark.py -
1. The CERTIFY accept path (addendum 8): on accept the controller
   no longer runs the n=5 speed trials; an accepted candidate
   answers the rung immediately.
2. The TOURNAMENT recommendation path (addendum 42): the
   reliable-depth n=5 w/s block is retired; the RAM-ceiling
   assumption replaces it. The historical wps medians in state and
   models.md stay as records of what was measured under the old
   protocol - the 34.85/27.79/6.84 numbers on the web pages remain
   valid historical measurements.
The speed falsification stays available as a separate probe for
later if a recommendation is ever doubted (the session-36 doctrine:
assume the speed gate passes, falsify when needed - now it is not
even measured in the benchmark loop).
The certify summary print keeps reading a historical wps_median
from state (compat with old runs); new runs produce none.

COST SAVED: on the 16k certify run, ~5 speed conversations per
accepted candidate; on tournaments, 5 per family with a reliable
depth (up to 45 conversations per full run).

INCIDENT (code_edit, reported per wow.md section 4): my first
help-text replacement inserted a literal newline INSIDE a python
string literal -> SyntaxError at import; caught by the test run
before commit and fixed. The editor cannot catch this class (the
string was legally edited, just semantically broken) - the ast.parse
gate in safe_append has the same class for appends. NOTE: edit()
does NOT compile .py targets after replace; PROPOSAL: extend the
post-write verify to ast-parse .py results. Flagged for the author.
140 tests pass.


## Addendum 16: the ast gate - python edits are syntax-checked before the write (2026-10-03)

BUILT (the addendum-15 proposal, the author: "build it! we always
improve, no need to ask for permission"):

`_check_python_syntax(src, out, path)`: for .py targets, if the
source parsed and the edit's result does not, the edit is REFUSED
with the SyntaxError's line and message - the file untouched.
Philosophy identical to _check_markdown: only NEW problems fail; an
edit to an already-broken file is a legal repair and goes through.
Wired into edit(), edit_many(), and the check() preflight - the
same gate a pre-flight caller sees.

THE ADDENDUM-15 INCIDENT CLASS IS CLOSED: a replace that inserts a
literal newline inside a string literal (the exact bug that broke
full_benchmark.py's import last addendum) is now refused at edit
time with the line number. The gate also catches the general class:
truncated literals, orphaned brackets, mangled f-strings - any
edit that leaves the module unparseable.

INCIDENT (reported per wow.md section 4, with relish): while
BUILDING the syntax gate, my first insertion broke code_edit.py's
own syntax (a one-quote docstring terminator) - and the module
could not load to fix itself. Fixed with a standalone
verify-before-write script (the same atomic pattern). The irony is
registered: the gate's first catch could not be the gate.

Tests: 4 new (the addendum-15 reproduction refused with the line
number and the file untouched; repair-of-broken-python allowed;
clean python unaffected; the check() preflight runs the same gate).
144 pass.


## Addendum 17 (2026-10-03, grading) - the 16,384 rung is answered

The author: "results are in." The --certify 16384 run (commits 82c81be,
f1e69eb) is graded.

THE ANSWER: the 16,384 rung goes to AI21-Jamba2-3B (Q8_0, f16, f16) at
SILVER - accepted at 11/11 fresh cells, 1-sigma Wilson lo = 0.917.
3 historical top-out cells inherited (the cell controller never
re-measures); runs 9-21 never measured (early accept). The other 8
families were skipped - ~95% compute saved vs the 189-cell worst case.

COST: the first run measured 8 fresh cells then the author
interrupted during the w/s trials (KeyboardInterrupt in results.txt) -
w/s is no longer a certification input (addendum 15), so nothing was
lost. One w/s trial had already recorded 7.2 w/s at 16,384 (PASS) -
kept as a bonus record, not a certification input. The rerun after
the interruption took 1 minute: everything inherited, 0 fresh cells,
8 families skipped.

GRADED INTO THE ARTIFACTS:
- models.md: the practitioner table (session 37) - 4,096 -> Qwen3.5-0.8B
  gold (17/21 at 1s); 8,192 -> 0.8B silver (14/21); 16,384 -> Jamba2
  silver (accept 11/11, lo 0.917); 32,768+ -> EMPTY (in progress).
- Both web pages: Jamba2 depth 16,384 with depthSource "certified 11/11
  by the sequential controller (2026-10-03)"; conservative corrected to
  0 (15/21 at 4k is short of the 16/21 gold bar); caveats now "32k and
  deeper in progress". node --check and boot smoke test pass on both.

NEXT RUNG (cheapest-first): --certify 32768 on the same 9 families,
state/benchmark-state-tournament.json. All 9 stay candidates - early
stop never measured most deep cells.


## Addendum 18 (2026-10-03, tooling) - certify becomes a TYPE + a RANGE

The author's two rulings, and the design that fell out:

1. "certify should be a range." A JSON spec file was considered and
   REJECTED by the author's own observation: the output of the previous
   rung can change the predictions, so a static spec is stale the
   moment rung k is answered. The simpler design: --rungs DEPTH
   [DEPTH ...], processed cheapest-first (sorted ascending), state
   saved after EACH rung - so a range is just multiple commands
   concatenated, and each rung's answers feed the next rung's
   candidate ordering live. No JSON needed.

2. Three certification TYPES, chosen per invocation:
   --certify at_least_one - the practitioner's question 1: the first
   candidate with >= 1 pass at the rung answers it (bronze).
   --certify 1_sigma - reliable: 1-sigma Wilson lower bound >= 0.5,
   count >= half of n=21 (silver; the previous fixed bar).
   --certify 2_sigma - conservative: the same bar at 2 sigma (gold).

   The accept/dead math is parameterized by (floor, z) derived from
   the level; at_least_one uses floor=1, z=0 and declares DEAD only
   when every cell is measured with zero passes. Early reject still
   applies at the sigma levels (best-case Wilson lo < 0.5 = dead).

   CLI: --certify LEVEL + --rungs DEPTH [...]; the old single-depth
   --certify DEPTH form is retired.

Tests: 3 new (at_least_one accepts from a historical top-out cell
with zero fresh cells and skips the rest; at_least_one with 21
measured fails is DEAD; 2_sigma early-reject with the 2s bound in
the message). 147 pass.
