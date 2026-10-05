# Session 39 - 2026-10-05

Opened 2026-10-05 (no session was open for today - session 38 was
opened 2026-10-03 and its tail addenda were working-day continuations;
per the notebook's one-session-per-day convention this session is
new). Carrying over from session 38 (addendum 16 was its last): the
12-family run's census coverage grows as logs commit; the blocking
gates at the current bars are arc 60% and vt 61%.

The day's work was registry hygiene, not measurement: two documents
had drifted behind the code and were brought current.

## Addendum 1 - wow.md section 10: review is on demand (2026-10-05)

The author's ruling, registered verbatim: "Vibe will integrate
directly to main. Vibe will only wait for a review if Daniela asked
for it."

Recorded as section 10 of wow.md ("Review is on demand"). This
supersedes the default draft-PR flow: delivery is a direct push to
main, and a review gate is opened ONLY on explicit request. First
application of the rule in the same day: PR #9 (addendum 2 below)
was merged to main without review.

## Addendum 2 - protocol.md catch-up registered (addendum 107 of the registry change log, 2026-10-05)

The registry had fallen three notebook sessions behind (36-38): the
certification framework, the quality instruments and the memory
witness all shipped as code with no registry rows. The catch-up
(protocol.md change log, addendum 107) adds:

- [A] rows: certify bars (speed 0, fwe 2/3, vt 4/5, arc 4/5 -
  the >= 50% floor rule), medals (gold/silver/bronze), the
  21-conversation speed corpus (per-cell stall counts, k = 5 the
  median turns per conversation), n per task (FWE 3 / VT 5 /
  speed 5 / ARC 5).
- [P] rows: the tournament depth grid (4096..262144 dyadic,
  21 climbs, seed = climb number), the combined cell, the depth
  budget (probe-and-trim, ANSWER_HEADROOM 128), the two-gate
  orthogonality (addendum 127 of session 37).
- [D] rows: the memory witness (llama's own -lv 5 accounting
  supersedes the smaps census - session 38 addendum 11), the
  hybrid architecture finding (5 of 9 families SSM/recurrent;
  the law exception is architectural, not vendor), size_table
  (the per-context recommendation curve; the speed gate is the
  size authority).
- [M] rows: FWE and VT instrument constants (NVIDIA/RULER
  upstream verbatim - exit: none, upstream fidelity IS the point).
- SUPERSEDED: the addendum-86 Q8_0-only ruling - the tournament
  re-opened the quant axis (TOURNAMENT_MODEL_QUANTS Q2_K..Q8_0,
  KV q4_0..f16); the certify path standardizes on (q8, f16, f16).
- The anchor-chain section now separates the two consumers of the
  unchanged per-turn collision test: the ladder grades by stall
  rate (v3.1), the certify path grades by per-cell stall count
  (session 38 addendum 2). The binary per-turn event itself is
  untouched.

Verified: md_check.py clean on protocol.md; 162 tests pass.
Delivered as PR #9, merged to main under the addendum-1 rule
(no review requested).

NOTE (numbering): the catch-up entry is numbered 107 as the next
in protocol.md's own change-log series (which ended at 106). If a
future notebook addendum claims that number for other content, the
registry's series takes precedence for registry entries - the two
series are separate (notebook addenda per session; registry change
log global).
