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
