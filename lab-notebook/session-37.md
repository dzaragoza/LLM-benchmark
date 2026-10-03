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
