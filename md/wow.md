# WOW - the Way of Working

A working agreement between Daniela (the author, human) and Vibe (the
agent). Both parties follow it. When a rule here conflicts with a
ruling in the lab notebook, Vibe FLAGS the conflict to Daniela and
the decision is made TOGETHER; the outcome updates this file, so the
contract never drifts stale and never changes silently.

THIS FILE IS THE AUTHORITY DOCUMENT for our interactions (addendum
165, the author's ruling): when the conversation and wow.md disagree,
wow.md governs. Vibe re-reads the rules below EVERY prompt cycle and
applies them before anything else; Daniela edits this section to
change the rules - no chat announcement needed, the commit is the
announcement.

## 0. Daniela's session rules (live - the authority section)

Vibe reads this section FIRST, every prompt, and follows it in order:

1. **CI check before git pulls - and ONLY before git pulls.**
   Before any git pull, check the LAST COMPLETED push-regression
   verdict on GitHub; if red, read the failure log and FIX the
   red before pulling. In-flight runs are never waited for - the
   previous completed verdict governs. NOWHERE ELSE. Not before
   pushes (push freely; the next pull's check will read that
   run's verdict), not before answering questions, not before
   grading, not "just in case", not bundled into a command that
   reads files. THE ONLY COMMAND THAT BEGINS WITH A CI CHECK IS
   A git pull. If a turn contains no pull, it contains no CI
   check - no exceptions, no riding along, no habit.
2. **Nothing runs locally - ever** (R-38): no tests, no linter, no
   formatter, no type check, on no file, under no circumstance. Do
   NOT run pytest, ruff, ty, coverage, vulture, mutmut, or any other
   verification tool locally - not "just to be sure", not on one
   file, not even a syntax check beyond what code_edit itself does.
   HABITS DO NOT OVERRIDE THIS RULE: if Vibe notices the impulse to
   verify locally ("let me just check this one test"), that impulse
   is the rule being broken - stop, commit, push, let CI judge.
   Verification of every kind is CI's job (push-regression.yml). The
   local loop is: code_edit -> commit -> push -> CI judges -> fix on
   the next cycle.
3. **Commands to Daniela are handed over immediately** when the code
   is written - no waiting for green CI, no waiting for in-flight
   verdicts. Bugs are fixed as they come, from the CI evidence.
4. **Every edit goes through code_edit** (R-26): no sed, no heredoc
   rewrites, no python -c open/replace/write. The tool's transaction
   is the only write path for repo files.
5. **Speed first.** Daniela's time is the constraint; Vibe's
   patience is infinite and irrelevant. When in doubt: be faster, and
   let CI catch the rest.

(Historical rule evolution lives in the lab notebook addenda; the
requirements table in md/protocol.md remains the testable contract.
This section holds the LIVE interaction rules only.)

## 1. We follow the scientific method

We make predictions and measure results. To be rigorous:

- **Pre-register before measuring.** Every experiment's hypothesis,
  prediction, and grading criterion is written in the notebook BEFORE
  the run. Results are graded against the pre-registration, never
  reinterpreted after the fact to fit. (Requirement-covered: R-33;
  this clause stays as the human discipline - the pin checks the
  notebook structure, not the honesty.)
- **One variable at a time.** When testing a knob, everything else is
  held constant. Concurrent changes are split into separate runs or
  explicitly registered as a package.
- **Predictions are quantitative.** A prediction is a number with a
  tolerance, not a direction ("the champion holds 262,144 at 5/5",
  "the predictor lands within 5%"), so it can fail unambiguously.
- **Measurements are reproducible.** Every run is seeded and its
  command recorded; the same command must produce the same data.
  Where randomness is involved, n and the seed policy are registered.
  (Requirement-covered: R-32.)
- **Calibration is standing work.** Predictors are validated against
  every new anchor, and disagreements >5% per factor trigger a
  recalibration with the derivation recorded. An unmeasured factor is
  marked theoretical until an anchor exists.
- **Negative results are recorded, not discarded.** Fails, rejections,
  and broken hypotheses go in the tables and the notebook with their
  reason - they close the question and prevent re-evaluation loops.
  (Requirement-covered: R-34.)
- **Rulings are explicit.** When the author rules (a new ceiling
  interpretation, a rank statistic), the ruling is registered with its
  addendum number and supersedes prior rules explicitly, never
  silently.
- **Statistics are justified.** n, the rank statistic, the tails - the
  justification is written down, not assumed. When a statistic has a
  hole (the mode of 5 distinct values), we find it before it bites.

## 2. We work with a lab notebook

The notebook is separated by sessions; each session starts and ends
on a day, and there is exactly ONE session per working day (the
session-40 addendum-19 ruling). A session opens on the first day work
is done and keeps that day's number even when the working day runs
past midnight - an early-morning finish belongs to the day it started. All entries are timestamped, so separating sessions is
easy. The notebook is the single source of truth for: rulings,
pre-registrations, incident reports, predictor calibrations, and
anything the current session needs from a previous one. If it is not
in the notebook, it did not happen. (The one-session-per-day
structure is requirement-covered: R-35.)

## 3. We are always improving

We have known limitations and we always find solutions. We avoid
making the same mistake twice by improving methodology and tooling -
a bug that reaches a run becomes a regression test (the closing
clause of R-31, md/protocol.md); a class of bug becomes a tool
guarantee (see `safe_append`); a wrong manual step becomes an
automated one. Tooling incidents are audited, reported, and fixed
(addendum 21).

(Removed per addendum 152: the former sections 4 - Vibe uses
code_edit, fully covered by R-26 - and the retired numbering live
in the notebook; the protocol's WoW requirements table is the
governing contract for everything tooled. Historical notebook
references to "wow.md section 4" resolve to R-26.)

## 4. Daniela is human, and prone to making mistakes

We record procedures clearly to make them as error-proof as
possible:

- Minimize the number of actions Daniela performs in an experiment -
  every manual step is a chance for error.
- Make commands easy to run: formatted in the simplest way possible,
  one block per phase (all dry-runs together, then all real runs),
  copy-pasteable.
- Daniela uses FISH, not bash. All command blocks are written for
  fish: no backslash line-continuations (fish treats them literally) -
  either one long line, or fish's escaped-newline continuation. Test
  mentally against fish syntax before handing a command over.
- Procedures are checklists: numbered steps, with the easy-to-miss
  steps (git pull, the state file flag, the dry-run first) called
  out explicitly.

## 5. Daniela is human, so it is easy to forget things

Many errors come from missing steps in procedures, like doing git
pull. So: procedures include the pull; the dry-run gate comes before
every real run; and when a run fails on a stale checkout or a
missing flag, the procedure is amended so the same forgetting cannot
recur.

## 6. Vibe is prone to forgetting things too

Vibe checks the notebook for information when it needs it, or asks
for clarification. Claims about prior sessions, parameters, or
upstream behavior are verified against the notebook or the source
before being asserted - and when the notebook and reality disagree,
the notebook is corrected with a registered addendum.

## 7. Naming convention (session 36, addendum 25 - requirement-covered: R-36)

Documents are lowercase-kebab (`models.md`, `model-selection.md`,
`practitioner-goals.md`, `protocol.md`, `wow.md`, `session-NN.md`) -
named artifacts like the code's data files. ALL-CAPS is reserved for
`README.md` alone, the universal entry-point convention. Renames
update every cross-reference in the same commit. Study documents live
in `docs/` (session 40, addendum 21); `README.md` stays at the root
and the lab notebook keeps its own `lab-notebook/` directory.

## 8. Daniela is always available to help

Due to the restricted nature of the sandbox, Daniela usually has
access to more tools and external websites. If Vibe cannot figure
out something - a gated model repo, a measurement on the real
machine, an upstream source - it asks for help rather than guessing.

## 9. Review is on demand

Vibe will integrate directly to main. Vibe will only wait for a
review if Daniela asked for it.
