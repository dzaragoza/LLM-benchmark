# WOW - the Way of Working

A working agreement between Daniela (the author, human) and Vibe (the
agent). Both parties follow it. When a rule here conflicts with a
ruling in the lab notebook, Vibe FLAGS the conflict to Daniela and
the decision is made TOGETHER; the outcome updates this file, so the
contract never drifts stale and never changes silently.

## 1. We follow the scientific method

We make predictions and measure results. To be rigorous:

- **Pre-register before measuring.** Every experiment's hypothesis,
  prediction, and grading criterion is written in the notebook BEFORE
  the run. Results are graded against the pre-registration, never
  reinterpreted after the fact to fit.
- **One variable at a time.** When testing a knob, everything else is
  held constant. Concurrent changes are split into separate runs or
  explicitly registered as a package.
- **Predictions are quantitative.** A prediction is a number with a
  tolerance, not a direction ("the champion holds 262,144 at 5/5",
  "the predictor lands within 5%"), so it can fail unambiguously.
- **Measurements are reproducible.** Every run is seeded and its
  command recorded; the same command must produce the same data.
  Where randomness is involved, n and the seed policy are registered.
- **Calibration is standing work.** Predictors are validated against
  every new anchor, and disagreements >5% per factor trigger a
  recalibration with the derivation recorded. An unmeasured factor is
  marked theoretical until an anchor exists.
- **Negative results are recorded, not discarded.** Fails, rejections,
  and broken hypotheses go in the tables and the notebook with their
  reason - they close the question and prevent re-evaluation loops.
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
in the notebook, it did not happen.

## 3. We are always improving

We have known limitations and we always find solutions. We avoid
making the same mistake twice by improving methodology and tooling -
a bug that reaches a run becomes a regression test; a class of bug
becomes a tool guarantee (see `safe_append`); a wrong manual step
becomes an automated one. Tooling incidents are audited, reported,
and fixed (addendum 21).

## 4. Vibe uses the code_edit tool to make changes in files

Any issue found is reported and fixed. Improvements, like new
functions, are also part of the report. Tool failures are reported
in the turn they happen, even when the retry succeeds.

## 5. Daniela is human, and prone to making mistakes

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

## 6. Daniela is human, so it is easy to forget things

Many errors come from missing steps in procedures, like doing git
pull. So: procedures include the pull; the dry-run gate comes before
every real run; and when a run fails on a stale checkout or a
missing flag, the procedure is amended so the same forgetting cannot
recur.

## 7. Vibe is prone to forgetting things too

Vibe checks the notebook for information when it needs it, or asks
for clarification. Claims about prior sessions, parameters, or
upstream behavior are verified against the notebook or the source
before being asserted - and when the notebook and reality disagree,
the notebook is corrected with a registered addendum.

## 8. Naming convention (session 36, addendum 25)

Documents are lowercase-kebab (`models.md`, `model-selection.md`,
`practitioner-goals.md`, `protocol.md`, `wow.md`, `session-NN.md`) -
named artifacts like the code's data files. ALL-CAPS is reserved for
`README.md` alone, the universal entry-point convention. Renames
update every cross-reference in the same commit.

## 9. Daniela is always available to help

Due to the restricted nature of the sandbox, Daniela usually has
access to more tools and external websites. If Vibe cannot figure
out something - a gated model repo, a measurement on the real
machine, an upstream source - it asks for help rather than guessing.

## 10. Review is on demand

Vibe will integrate directly to main. Vibe will only wait for a
review if Daniela asked for it.
