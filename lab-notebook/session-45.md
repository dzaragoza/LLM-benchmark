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
