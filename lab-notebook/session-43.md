# Session 43 - 2026-10-08

Opened 2026-10-08. The day's arc: PR #10 (the v7 pilot) merged to
main; the greedy allocation ruled in and shipped (PR #11, merged);
the pilot merged INTO full_benchmark as bench/v7.py + `--task v7`
(the author: "this is failing too much... it is substantially more
mature"); two live-run bugs found and fixed (the 0/0 score, the
HTTP-400 full-corpus prompt); and the session's cleanup - ARC and
FWE retired, the crash rail, the corpus artifact, R-16..R-19.

## Addendum 100 - model selection re-ruled: the greedy climb

The author's ruling (superseding the pilot's closest-to-50% rule):
"For each model config (q, k, v) for context size c start at the
lowest Quant (2,2,2). Using the greedy algorithm, find the largest
config such that (q,k,v) <= 4 GiB." Pick always the single-axis
one-notch upgrade that lands closest without exceeding; >= 50% of
budget is fine. Rungs: Q2_K -> Q3_K -> Q4_K -> Q5_K -> Q6_K ->
Q8_0 -> F16 (the author: "q in the config can also be f16");
cache q2_K -> q4_K -> q8_0 -> f16. F32/FP64 ruled out (F32
pointless - no quality gain over F16 for the memory; FP64
unsupported by llama.cpp for weights or cache). The K-encoding
ruling: "keep the top at 16 bits. Use the k encoding for anything
below q8, both for model Quant and cache." Shipped in bench/v7.py
greedy_allocations; pinned by R-18.

## Addendum 101 - the pilot scope ruling

"This is the pilot! Choose the first 4 models by number of
parameters, ascending" - granite-4.0-h-350m, granite-4.0-350m,
MiniCPM4-0.5B, Qwen3.5-0.8B; 23 cells. The full-roster answer
(183 cells, 32-family cap question) was registered before the
narrowing; three families remain unplaceable pending registry
extracts (Llama-3.2-1B-Instruct, gemma-3-1b-it, gemma-3-4b-it -
`python3 etc/registry_data.py fetch` needs a networked machine).
The 512k question: nothing in the registry is trained beyond
262k, so the grid tops at 262,144.

## Addendum 102 - the pilot's two live crashes

The author ran `--task v7` on the T14s. Crash 1: SPANS started at
4096 while the smallest cells launch at ctx 2048 - every small-ctx
cell scored 0/0 with nothing measurable. Fix: the 2048 span grade
added (b53b464). Crash 2: HTTP 400 - question_prompt sent the FULL
~357k-token corpus to a 2k-window server. Fix: per-span prefix
cuts - a span-s question presents only the corpus prefix for its
grade (a9c8ad0). Both fixes folded into R-19.

## Addendum 103 - ARC and FWE RETIRED (R-05)

The author's session-43 ruling: "We don't need arc nor fwe anymore.
We can get rid of them." v7 sharpened the focus to reach vs
reasoning; the fixed corpus carries both axes, so the three-task
combined controller (speed + fwe + vt) becomes TWO tasks (speed +
vt). Removed: arc_pass / arc_cells / arc_cell_questions /
ARC_CELL_K / ARC_RUN_CTX / fwe_pass / arc_kill_rate_cells, the
certify_rung fwe path (default task now "vt"), the fwe/arc branches
of combined_medal, kill_rate_cells' fwe gate. Kept: the historical
certify / certify_arc cells in the state file (readable history -
never deleted, just never extended); ruler_gate.py's standalone
fwe CLI (a separate tool, not the task machinery). requirements_check
now exempts RETIRED requirements from the pin contract.

## Addendum 104 - the crash rail (R-17)

"Add a mechanism for reporting if a crash is detected. Basically
make sure that the git rail runs always." full_benchmark.main() is
now the crash-safe entry: _run(args) carries the old main body;
any BaseException (SystemExit passes through) prints and stamps
the traceback, appends a `===== CRASH =====` block to results.txt,
kills the stale server, uninstalls the tee, runs git_tail, and
RE-RAISES - the crash is reported, not dropped. SIGINT keeps its
own handler (addendum 8). Pinned by R-17 and
test_crash_tail_always_runs.

## Addendum 105 - the corpus as a repo artifact (R-16)

"Add the corpus as an artifact in the repo." state/v7-corpus.json:
built once, carries its grid constants (spans, hops, k, s_max) and
the corpus; a run loads it when the constants match and only
rebuilds (and rewrites) when they change. The corpus is citable
and byte-identical for every contender and every machine. Pinned
by R-16 and test_corpus_artifact_roundtrip.

## Addendum 106 - requirements review: R-16..R-19

The author: "Let's review the requirements. We have sharpened the
focus quite a lot in v7." R-05 rewritten as RETIRED (addendum
103); R-14's ARC fragment retired; R-16 (corpus artifact),
R-17 (crash rail), R-18 (greedy climb + ladders), R-19 (prefix
prompts + reach exclusion) added. requirements_check passes:
19 requirements, all pinned.

SESSION STATE at close: the cleanup suite green (195 passed,
test_properties.py excluded in the sandbox - hypothesis absent
there, it runs on the author's machine). PENDING on the author:
fresh `git pull`, clear the stale v7 cells, rerun
`python3 full_benchmark.py --task v7` on the T14s.

## Addendum 107 - R-20: the hooks run for real, and are never omitted

The author's ruling: "All the dependencies for the commit hook shall
be installed. The commit hook shall not be omitted." The sandbox gap
(ty, hypothesis, then huggingface_hub/pyarrow/transformers for ty's
import resolution, ruff as a binary) is CLOSED - every hook entry
runs green in this environment, and the addendum-21 ruling ("no
--no-verify exceptions") is now ENFORCED, not just intended:

- R-20 added to md/protocol.md: hook dependencies installed; no
  bypass; a failing hook is fixed, never skipped.
- tests/test_precommit_env.py pins it: binaries on PATH (ruff,
  pre-commit), modules importable (ty, pytest, hypothesis,
  huggingface_hub, pyarrow, transformers), ty_check.py exits 0,
  the .pre-commit-config.yaml hook list stays complete, and no
  repo source carries a quoted --no-verify literal.
- The bypass is REMOVED from the machinery: infra/git_ops.py's
  pull_rebase drops its no_verify parameter; full_benchmark's
  git_pull_head pulls WITH hooks.

## Addendum 108 - the test-strategy and formal-verification audit

The author's ask: "Check our test strategy for weaknesses and improve.
Same for formal verification." The audit (coverage map + crosshair
run + a read of every test file):

WEAKNESSES FOUND (tests):
1. run_cell - the v7 SCORER, the number the whole benchmark argues
   from - had ZERO direct tests. The suite tested the planner, never
   the score.
2. build_corpus untested: determinism, chain-inside-prefix, cut
   monotonicity all unpinned.
3. corpus_from_artifact's mismatch-rebuild path untested.

WEAKNESSES FOUND (formal verification):
4. contracts.py covered only pre-v7 functions; the quant-ladder
   arithmetic (the budget discipline) was proved nowhere.

BUGS THE NEW TESTS CAUGHT IMMEDIATELY (the audit paid for itself):
- corpus_from_artifact checked the grid at the TOP level of the
  artifact JSON while the writer nests it under art["grid"] - the
  artifact NEVER loaded; every run silently rebuilt the corpus,
  violating R-16's citable-bytes promise.
- once loading worked, JSON's str-int key coercion broke the cuts
  map: question_prompt KeyErrored on every artifact-loaded run.
  Fixed by normalizing cut keys on load.

LANDED:
- tests/test_v7_run_cell.py (12 tests): corpus determinism and
  structure, chains-embedded-before-cut, cut monotonicity, prompt
  rendering, exclusion-not-failure, score-is-mean-pass-mass,
  all-pass-earns-max, score-bounded, window reported, artifact
  mismatch-rebuild and matching-load (the load path now actually
  exercised - it never was).
- tests/test_properties.py +5: alloc monotone in every ladder axis
  and ctx, weights ladder ordered, score_vt partial-never-passes,
  score_vt order/debris-tolerant.
- tests/contracts.py +7 proved contracts (crosshair exit 0):
  weights positive/linear, both ladders strictly ordered, alloc
  total positive, KV monotone in ctx and in rung. score_vt stays in
  the hypothesis layer - crosshair cannot prove string membership
  through symbolic list elements (a tool limit, registered).
- v7.py coverage 65% -> 74%; the remainder is the live-server
  launch loop (needs the GPU binary, the author's machine owns it).
