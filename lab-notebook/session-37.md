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
