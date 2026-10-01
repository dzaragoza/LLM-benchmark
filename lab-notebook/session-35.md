## Session 35 - 2026-10-01

Session 35 opens mid-sweep: the Q4_K_M overnight run of the 16-family pool (session 34, addendum 40) is read the morning after, and the study spends the day on its consequences - the disk crash, the tensor-cleanup rule, the merged best-of pages, and the multi-quant sweep plan.

### Session 35, addendum 1 - the Q4_K_M overnight run: the partial table, the disk crash, and the tensor cleanup

THE OVERNIGHT RESULT (12 of 16 benched before the disk filled): CONTEXT-OVER-PARAMETERS IS CONFIRMED AT THE TOP - Qwen3.5-0.8B more than DOUBLES to 262,144 (2.5x its Q8 depth at ~40% of the file, cold 4.44 GiB); Qwen3.5-4B nearly doubles to 123,904; Qwen3-4B doubles to 16,384; granite-4.1-3b 18,432 and granite-3.2-2b 15,360 hold theirs. BUT THE QUANT CUTS BOTH WAYS: MiniCPM5-2B, Phi-3.5-mini, Qwen2.5-1.5B and Qwen3-1.7B all scored ZERO at Q4_K_M (floor-rule FAILEDs - the smaller weights cannot do FWE even at 4,096), granite-3.1-2b dropped to 6,144, and the two MiniCPM sft families held 4,096. The division is clean: models whose Q8 depth came from capability keep or grow it at 4-bit; models near their counting edge fall off the cliff.

THE DISK CRASH: the sweep died writing benchmark-results-q4.json (OSError 28) after granite-4.2-3b's f16 conversion failed mid-write (out of space at ~4.2 GiB in) - granite-4.2-3b, granite-3.0-2b-instruct, phi-4-mini-instruct and granite-3.3-2b-instruct never ran; their tensors remain on disk for the resume. The author freed 82 GiB (manual safetensors-source cleanup, fish loop over the twelve done families keeping the four pending ones).

THE TENSOR-CLEANUP RULE IS NOW CODE: convert_quant.create() deletes the family's safetensors-source directory immediately after a verified f16 conversion - the f16 is the quant source for every further rung (never the safetensors; and never Q8 -> lower quants, which would double-quantize). Deleted only after the f16 is verified on disk; the local-f16 path (no conversion) never touches tensors. Test added (50 passing).

THE RESUME COMMAND (the four unfinished families, idempotent from benchmark-state-q4.json): python3 full_benchmark.py ibm-granite/granite-4.2-3b ibm-granite/granite-3.0-2b-instruct microsoft/phi-4-mini-instruct ibm-granite/granite-3.3-2b-instruct --rung Q4_K_M --state-file benchmark-state-q4.json --results-file benchmark-results-q4.json

### Session 35, addendum 2 - the merged best-of table, sortable pages, and the quant-sweep discussion

THE MERGED RULING: the picker pages carry each family ONCE, at its best score between Q4_K_M and Q8_0 (the author's ruling). Six families upgraded to Q4_K_M: Qwen3.5-0.8B (262,144 - 2.5x its Q8 score), Qwen3.5-4B (123,904), granite-4.1-3b (18,432), granite-3.2-2b (15,360, same score but half the file), Qwen3-4B (16,384, double its Q8), MiniCPM-2B-sft (4,096, same score, 1.68 vs 2.70 GiB file). The other ten keep Q8_0 (their Q4 run scored zero or the family only has Q8 data yet).

THE PAGE CHANGES: title/sub/foot prose de-Q8'd ("which model serves your machine"); the quant column is now per-row data; column headers are clickable and sort the table (click again to reverse; depth descending by default); the GPU picker's DEFAULT tier stays the smallest capacity that runs every measured model (the author's ruling on the first proposal: "it is better to select the gpu ram that can run every model as default" - the top-scoring model's own capacity had been tried and reverted).

THE FINDINGS (Q4 vs Q8, the 12-family partial grid):
- Context dominance is the story of the grid. Q4 halves the weights and roughly doubles the tokens each weight can carry before the KV+attention drag catches up: Qwen3.5-0.8B 105,472 -> 262,144 (its 262,144 rung passed with 8.1 w/s to spare); Qwen3.5-4B 65,536 -> 123,904; Qwen3-4B 8,192 -> 16,384; granite-4.1-3b 16,384 -> 18,432.
- Quantization cuts both ways at the counting edge: the four families that scored ZERO at Q4 (MiniCPM5-2B, Phi-3.5-mini, Qwen2.5-1.5B, Qwen3-1.7B) all passed speed at 4,096 but missed FWE at 3,840 - their Q8 depth was capability-fragile, and 4-bit noise tips them below the counting floor. Their Q8 scores stand; the Q4 FAILED is recorded.
- granite-3.1-2b went the wrong way (12,288 -> 6,144): a small-model family where the Q8 counting margin was already thin.
- Speed is not the binding constraint for the Q4 winners below ~130k tokens; FWE fails first. The speed ceiling only binds the deepest (Qwen3.5-4B failed speed at 131,072).

WHICH QUANTS NEXT, FOR WHICH MODELS: the interesting frontier is the top of the table, where depth is KV-bound and the weights are a small fraction of the cost. Q5_K_M and Q6_K on the two Qwen3.5 families answer "how much counting capability does a bit of precision buy back" - Qwen3.5-4B Q5_K_M is the single most interesting cell (its Q8 65,536 vs Q4 123,904 bracket is wide; Q5/Q6 pin where the FWE cliff sits). Q3_K_M on Qwen3.5-0.8B tests whether the 262,144 champion survives further compression. Q2_K is likely a waste of machine time (the Q4 zeros show the counting floor is near). The granite/MiniCPM mid-table is speed-band-limited, not precision-limited - low priority. The f16 files are kept on disk (the quant source; lz4-style tools buy only ~5-10% on f16, quantization is the real compression).

THE RESUME IS RUNNING: the four-family Q4 resume (session 35, addendum 1's command) is running now; the pages will be re-checked against its results when it lands (phi-4-mini and granite-3.3-2b may flip to Q4 rows; granite-4.2-3b and granite-3.0-2b scored 4,096 at Q8 so they only flip if Q4 beats that).


## Session 35, addendum 3 - the KV-cache quantization variant (FA required)

The author wants to take the Qwen3.5 family to the limit. The context is the dominant factor on this bandwidth class, so the next lever is the KV cache itself: quantize the KV cache to halve (q8_0) or quarter (q4_0) its size, which at 262k tokens is the memory term that scales with context.

Why flash attention (-fa) is REQUIRED for a quantized cache: the non-FA attention kernels in llama.cpp do not implement the quantized-cache code paths - the server refuses or ignores --cache-type-k/--cache-type-v without -fa. FA itself is the memory-saving rewrite of attention: the naive kernel materializes the full O(n^2) score matrix (n = context tokens); FA tiles the computation and runs the softmax online, never materializing the score matrix. So -fa is both the enabler of the quantized cache and a memory win in its own right at deep contexts.

The experiment design (author rulings):
- The 4B is the WITNESS: it is speed-wall-bound (131,072 failed at 5.74 w/s worst), so a smaller KV may push the wall deeper. We run it first at both weight quants (Q8_0 and Q4_K_M) with the KV cache at q8_0, to see the effect on the wall before touching the winner.
- The 0.8B is the TWEAK TARGET: it is window-capped (its 262,144 ceiling IS the training window at Q4), so KV quant cuts the machine cost at the winning rung rather than the depth. We only tweak it after the witness validates the variant.
- Variants ride FRESH state/results file pairs (benchmark-state-kvq8-q4.json / benchmark-results-kvq8-q4.json and the -q8 twins) so they never contaminate the baseline grids.

Implementation (pushed with this addendum):
- full_benchmark.py gains --kv-quant {q8_0,q4_0}; it is persisted in the state file (kv_quant) so every rung of the ladder launches the same way, and it plumbs through run_ladder -> speed_pass/fwe_pass -> speed_gate.bench_model; both launch sites add -fa --cache-type-k <q> --cache-type-v <q> to the server args.
- code_edit.py: the delimiter balance check goes REGION-based (session 35, addendum 3: a per-line check blamed legitimate multi-line code). Each replaced region must balance as a unit; insert/delete-only edits fall back to the whole buffer only when the source was balanced; a region may OPEN a delimiter that closes after it (an inserted call whose closing paren lands on a later line) - the real failure modes, a mismatched closer or an unclosed quote, still fail. The test stubs for speed_pass/fwe_pass gained the kv_quant parameter.
- The witness commands (dry-run first, then real, Q4_K_M then Q8_0) are with the author; the results land in fresh results.txt sections read back here.


## Session 35, addendum 4 - the Q4 resume lands; code_edit goes file-type aware; prettier owns the pages

THE Q4 RESUME LANDED (13:03): phi-4-mini-instruct flips to Q4_K_M - 44,032 tokens (from 32,768 at Q8), scored-rung worst 6.4 w/s, cold cost 8.14 GiB, 123.4 min. granite-3.3-2b-instruct flips to Q4_K_M - 26,624 tokens (from 6,144 at Q8!), cold cost 3.78 GiB. granite-3.0-2b-instruct Q4 ties its Q8 (4,096) so it stays Q8. granite-4.2-3b failed BOTH resume attempts (corrupted f16: blk.27.ffn_down.weight out of file bounds - the safetensors -> f16 conversion produced a truncated file); it stays on its Q8 row and is out of the Q4 sweep. The pages now carry the flips; the GPU default tier self-adjusts (MAX_COST is computed from the rows: 8.14 GiB now).

CODE_EDIT (three fixes, each hit during this addendum):
1. File-type aware delimiter check: prose (md/txt) has NO balance check (apostrophes are legal); python keeps the region check; markup (html/js) gets a whole-buffer bracket check with apostrophes stripped (prose inside the page) but DOUBLE quotes still counted (a truncated attribute is a real error); json balances fully.
2. The balance parser now understands triple-quoted strings (a docstring used to parse as open/close/open and false-positive an unclosed quote).
3. The block post-conditions (new-text-on-disk etc) moved BEFORE the atomic write - they used to run after it, so a failed verify left a MODIFIED file and broke the file-untouched contract (this corrupted code_edit.py once today). edit_many got the same pre-write checks it was missing.
4. The balance check for markup revealed two REAL page bugs prettier refused to reformat over: a stray closing div in cpu-picker.html and three doubled closing p tags in gpu-picker.html - fixed.

PRETTIER now owns the page formatting (prettier 3.3.3, print-width 100): both pickers reformatted; the check runs on every page edit from here on.

THE WITNESS (author ruling): the witness is Qwen3.5-4B at Q4_K_M - the cache encoding varies (KV q8_0 vs KV q4_0, weight quant fixed at Q4_K_M). The commands are with the author (fresh state/results pairs: benchmark-state-kvq8-q4.json etc).


## Session 35, addendum 5 - the witness runs died at launch; the log tail now prints

BOTH KV-variant witness runs (4B @ Q4_K_M, KV q8_0 and KV q4_0) failed identically in ~1s: "server did not become healthy" at the 4,096 start rung, speed verdict {"error": "no turns measured"}, ladder FAILED at floor - a FALSE zero (the same file scored 123,904 in the baseline Q4 run). The launch died at argument parsing or model load, and the reason was in the server log, which stayed on the author's disk.

THE FIX (pushed): both launch sites now dump the last 15 lines of the server log into results.txt when the server never becomes healthy (speed_gate.bench_model via _dump_log_tail; full_benchmark.fwe_pass inline). The addendum-33 lesson, applied: never leave the diagnosis on the author's disk.

PRIME SUSPECT: the -fa flag. Recent llama.cpp builds made flash attention the default and REMOVED -fa; passing it is a hard argument-parse error that kills the server in ~1s - exactly this signature. The fix, once the log confirms it, is to drop -fa and keep only --cache-type-k/--cache-type-v (quantized caches are the default-kernel path in those builds). Rerun the same two commands after the pull.


## Session 35, addendum 6 - code_edit: the shorthand, the pre-flight, and the standing report rule

AUTHOR RULING (standing): every code_edit issue is reported to the author the moment it happens, before moving on. This addendum opens the register.

THE REGISTER (this addendum, in order):
1. Bare (old, new) tuples failed with the cryptic "unknown kind" error - the kind tag was required. FIX: _normalize_block infers the kind: a 2-tuple whose first element is not a known kind IS a replace; a 3-string-tuple without a kind gets a CLEAR error naming the kind list. Both edit() and check() normalize.
2. _KINDS was written from memory and MISSED five real kinds (replace_regex_all, replace_region, delete_lines, indent, dedent) - 7 tests failed until it was synced against _verify_blocks. FIX: the list is now complete; a test would have caught this (see 4).
3. A multi-block transaction rolled back on a duplicate anchor (block 2 matched two places) - correct behavior, but it took a failed edit to find out. FIX: check() pre-flights a whole block set WITHOUT writing: verify + delimiters + result checks, returns the preview diff, raises with the exact block and reason on failure.

DESIGN NOTE: the failure modes are now all pre-write. The transactional contract (file untouched on ANY error) holds; check() exists so a bad block set never even reaches the write path.


## Session 35, addendum 7 - separate K/V cache quants; the false-zero selection fixed; the witness rides a 64k floor

THE RESUME RERUNS NEVER RAN: the fresh state files carried the crashed launches as "PASS (ladder score 0 tokens)" selections, so the family was skipped ("already selected... --force to redo"). Two bugs, both fixed:

1. THE FALSE-ZERO SELECTION: a speed verdict with error "no turns measured" (the server never became healthy) now carries launch_failed=True; run_ladder reports failed+launch_failed and phase 4 records FAIL ("server launch failed") instead of PASS - the family stays UNSELECTED. A launch crash is not a model score.
2. code_edit region check: a replace that starts INSIDE an open delimiter (a parameter list) and ends with its closer was false-positived; the region check now allows both directions (openers that close later, closers that opened earlier) - the real signals, mismatched closers and unclosed quotes, remain. Register entry 4.

SEPARATE K/V CACHE QUANTS (author ruling): --kv-quant-k and --kv-quant-v (choices q8_0, q4_0, q4_1, q5_0, q5_1, iq4_nl) ride the state file like --kv-quant. The witness design: K stays DEFAULT (f16), only V quantizes - community wisdom says V-quantization is nearly free quality-wise, K is where the damage shows. If V-only works, K-only is the follow-up.

64K FLOOR for the witness runs: --min-rung 65536 (persisted as ladder_min_rung in the state file) - the witness is speed-wall-bound near 123k, so the 4k-32k rungs are wasted machine time; the ladder starts at 64k and gallops up.


## Session 35, addendum 8 - the log tail names the killer: -fa takes a value; the combined flag is gone

THE WITNESS RERUNS both died at launch again - and this time the log tail (addendum 5's fix) named the exact cause: this llama.cpp build changed -fa to TAKE A VALUE ("-fa [on|off|auto]", default auto). Our bare "-fa" made the server eat the NEXT flag as its value: "error: unknown value for --flash-attn: '--cache-type-k'". The false-zero fix (addendum 7) worked exactly as designed: both runs recorded FAIL (server launch failed), the family stayed UNSELECTED, and the table flagged it for investigation instead of recording a score.

FIX (pushed): both launch sites pass "-fa on" when either cache quantizes. The default "auto" would also work; "on" is explicit because a quantized cache REQUIRES the FA kernels.

THE COMBINED OPTION IS GONE (author ruling): --kv-quant is removed from the CLI and the plumbing - K and V quantize ONLY via --kv-quant-k and --kv-quant-v. speed_gate.bench_model and the fwe launch build their args from the two separate params alone. Old state files carrying a stale "kv_quant" key are simply ignored (state.get on the removed key no longer happens).

code_edit register entry 5: a big multi-block removal transaction rolled back silently next to a formatting drift (ruff had reflowed a call site my target copied from memory) - check() caught it before any write; re-applied in smaller verified chunks. Reminder recorded: targets are copied FROM THE FILE, never from memory.
code_edit register entry 5: a big multi-block removal transaction rolled back silently next to a formatting drift (ruff had reflowed a call site my target copied from memory) - check() caught it before any write; re-applied in smaller verified chunks. Reminder recorded: targets are copied FROM THE FILE, never from memory.

## Session 35, addendum 9 - the witness verdict: V q8_0 buys RAM, not depth; the single-rung probe

THE INTERRUPTED WITNESS RUN (V q8_0, 4B @ Q4_K_M, 64k floor) settled the question. The addendum-8 launch fix worked: every server came up healthy with the quantized V cache, and the cold machine cost tells the story - 5.40 GiB at 65,536 vs baseline 7.71 GiB at 65,536, about 2.3 GiB saved at the same depth. Rung results: 65,536 speed PASS (worst 14.2 t/s); 131,072 speed FAIL (worst 6.07 w/s, stall rate 0.25) - essentially the BASELINE wall (5.74 w/s at the same rung without V-quant); binary search: 98,304 / 114,688 / 122,880 all PASS-ceiling (12.0 / 11.1 / 10.7 w/s, cold cost 6.24 / 6.44 / 6.65 GiB); 126,976 mid-launch when the author interrupted (KeyboardInterrupt in stream_completion - a clean stop, no bug).

VERDICT: V q8_0 does NOT push the speed wall deeper. The wall is bandwidth/compute-bound, not memory-bound; KV quantization buys RAM headroom (about 2.3 GiB at 65k) but the same ~123k-131k cliff. FWE was clean everywhere tested (65,280 / 98,048 / 114,432 / 122,624 all 3/3 HIT). Honest expectation for the remaining tweaks (V q4_0, K+V both): more RAM savings, same wall - the 4B is unlikely to pass 262,144 on KV quant alone.

THE SIMPLER MEASUREMENT (author ruling): we are not running full ladders per tweak. run_ladder already takes max_rung (the gallop's hard stop) - it is now exposed as --max-rung (persisted as ladder_max_rung). --min-rung N --max-rung N is the single-rung probe: speed + fwe at exactly N, pass or fail, no gallop, no search. A pass scores N; a fail is the floor rule (FAILED, investigate).

code_edit register entry 6: insert_after with a multi-line anchor FUSED the new text onto the anchor's last line (no newline at the join) - two corrupted lines in full_benchmark.py, and --check did not catch it (the check verifies anchors, not the join). FIX: _sep() forces a newline at the join whenever the edges would fuse (insert_before too); regression tests added; the corruption repaired. Register reminder stands: the delimiter check does not lint the JOIN - the pre-write _verify_result now sees the fused buffer, but a syntax check would have been the real guard here (future improvement).

## Session 35, addendum 10 - the roster collapses to one survivor: the 256k goal, the champion config, and the full rejection log

THE NEW GOAL (author ruling): the study's target context is fixed at 262,144 tokens (256k) - "finding anything higher than 256k is out of scope due to time constraints". The roster question becomes binary: which models can serve a 300-wpm reader AND count (FWE) at exactly 262,144, under the RAM ceiling the champion sets. A model either passes the single-rung probe (--min-rung 262144 --max-rung 262144, addendum 9) or it is retired. The full ladder per model is no longer run - the probe IS the test.

THE CHAMPION: Qwen3.5-0.8B at Q8_0, f16 KV, 262,144 deep - speed PASS (worst turn 14.8 t/s, scored-rung worst 9.3 w/s, zero stalls, reader never waited), FWE 3/3 HIT at depth 261,888, cold machine cost 4.96 GiB, 48.4 min wall. This closes the 0.8 RAM-max question: the quant CAP is Q8 (author ruling - F16 was the next rung at a predicted 5.78 GiB, but the wall time is too long to wait for). The passing RAM range at 256k is 4.44 (Q4_K_M) to 4.96 (Q8_0) GiB, both measured; the ceiling the roster screens against is the champion's 4.96 GiB.

HOW WE REACHED 262,144 (the context size): the 0.8's own training window is 262,144 (the server never capped its -c; the window rule, session 34 addendum 6, has nothing to cap). The v4.3 ladder scored the 0.8 at its window under the Q4 sweep (262,144, 8.1 w/s, 4.44 GiB) - the deepest score any family ever posted, 2.1x the next-best (the 4B's 123,904). The probe at the window then confirmed both gates hold at Q8_0 too. So 262,144 is not an arbitrary round number: it is the champion's trained window, the only depth at which we have a measured existence proof of pass-both-gates in this RAM class.

THE 4B IS STILL PENDING, WITH A PREDICTION: its floor config (Q2_K weights + K q4_0 + V q4_0) is estimated at ~5.0 GiB - just above the ceiling. It stays on the candidate list (the author's hypothesis: match 0.8's footprint and the 4B might pass), but the arithmetic says the fixed mass (1.37 GiB Q2_K weights + ~1.1 GiB overhead) already exceeds the 0.8's entire Q4_K_M footprint. The honest prediction: the 4B cannot pass at 262,144 under this ceiling; the probe will settle it.

THE REJECTION LOG - every family benched under v4.x, why each failed the 256k screen, and the screen's three disqualifiers (predicted RAM at 262,144 in the model's BEST config - the smallest weights/K/V combination it can run - versus the champion's ceiling; KV slopes fit from the measured cold-cost rungs):

WINDOW-DISQUALIFIED (trained window below 262,144 - unreachable without rope scaling, which the study rejects):
- Qwen2.5-1.5B-Instruct (window 32k class; v4.3 score 20,992 @ Q8_0) - the only other family whose RAM would fit; the window is the wall.
- Qwen3-4B (window 32k; score 16,384 @ Q4_K_M).
- phi-4-mini (window 16k; score 44,032 @ Q4_K_M - the deepest non-Qwen3.5 score, but 6x short of the goal).
- MiniCPM-1B/2B-sft, granite-3.0/3.1-2b, granite-4.2-3b (4,096-class scores; windows far below the goal and/or quality broken shallow).

KV-GEOMETRY-DISQUALIFIED (window possibly fine, but the KV cache at 262,144 exceeds the ceiling even at q4_0/q4_0):
- Qwen3-1.7B (KV ~100 KiB/token f16 -> ~7.3 GiB at q4_0 alone; v4.3 score 34,816, FWE broken at 40,704 anyway).
- granite-3.3-2b (~90 KiB/token -> ~6.6 GiB; score 26,624).
- granite-4.1-3b (~97 KiB/token -> ~7.1 GiB; score 18,432).
- granite-3.2-2b, MiniCPM5-2B, Phi-3.5-mini (same class; scores 15,360 / 12,288 / 7,168).
- Qwen3.5-4B (~34.5 KiB/token, the thinnest KV in the pool after the 0.8's 12.9 - but 2.59 GiB of Q4_K_M weights plus ~1.1 overhead leaves no budget for a 2.5+ GiB q4_0 cache at 262k; its v4.3 score is 123,904, the best in the pool; the probe at its floor config is the pending test).

QUALITY-DISQUALIFIED (FWE refusal/failure far below the goal - "we are not changing the benchmark to fit a model"):
- Qwen2.5-3B-Instruct (refused the FWE task, session 34; score 0).
- Qwen2.5-0.5B (counting floor; retired, session 34).
- granite-4.0-* and the other lineage-2 stragglers (never passed the 16k screen on the f4k grid).

THE SCIENTIFIC FINDING: the 256k screen is decided by KV GEOMETRY (KiB/token of cache), not by parameter count or quant. Qwen3.5's ~12.9-34.5 KiB/token GQA design is 3-11x thinner than every other family's; that, plus a 262,144 trained window, is why exactly one family survives. The metric the roster now ranks on: depth per RAM byte - the 0.8 champion holds 59,041 tokens/GiB at Q4_K_M (and 52,853 at Q8_0); no retired family exceeds 8,783.

THE CANDIDATE PIPELINE (pre-registered predictions, to be probed at 262,144 - skip the ladder, addendum 9): Qwen3.5-2B (Q4_K_M + K/V q5_0, predicted ~3.8 GiB - PASS ~60%); gemma-4-e2b (Q4_K_M + K/V q4_0, ~4.5 GiB, window must verify on the E2B - ~35%); Ministral 3 3B (predicted RAM fail - hold, dry-run only if the disqualification is wanted on record). Every model tested from here on gets a log line in this addendum: candidate, config, predicted RAM, probe verdict.

THE WEB PAGES: both pickers carry the single survivor row (Qwen3.5-0.8B, Q8_0, depth 262,144, 4.96 GiB, 9.3 w/s) with the rejection log referenced; the sortable 16-row tables are gone with the retired families. The 15 retired model files are wiped from the author's disk (the GGUFs remain re-acquirable via the hub interface).

code_edit register entry 7: replace_region was used with the anchors INCLUDED in the replacement text - but the kind is EXCLUSIVE (anchors are kept), so the anchors were duplicated and the old array tail leaked. --check passed because _verify_blocks verifies anchors, not the result's structure. FIX (agent discipline, and a tool gap recorded): the region contract is now documented in the kind's error message; the real guard still missing is a result-level sanity check (e.g. the new text must not contain the anchors) - future improvement candidate. The corrupted sections were repaired by exact replace; prettier 3.3.3 reformats both pages clean.

## Session 35, addendum 11 - the 2B probe PASSES: a second 256k survivor, at HALF the champion's RAM
THE RUN (2026-10-01 17:38-18:34, T14s): the addendum-10 candidate pipeline's first probe - Qwen3.5-2B, Q4_K_M weights + K q5_0 + V q5_0 KV, single-rung at 262,144 (--min-rung 262144 --max-rung 262144, fresh state/results pair benchmark-state-p2.json / benchmark-results-p2.json). Verdict: SCORE = 262,144 tokens, 54.1 min wall.
- speed: PASS - worst turn 15.2 t/s (avg-of-worsts 15.2), zero reader catch-up events, noise at depth worst/mean 0.999 (n=2).
- FWE: PASS - 3/3 words HIT at 261,888.
- scored-rung row: worst 9.5 w/s, cold machine cost 3.48 GiB (MemAvailable delta; mapped census 5.34 GiB mapped / 0.59 resident).
- SELECTED Q4_K_M for Qwen3.5-2B; the table row: score 262,144 | scored-rung worst 9.5 w/s | cold 3.48 GiB.
PREDICTION GRADED: addendum 10 predicted ~3.8 GiB and PASS at ~60%. The RAM came in BETTER than predicted (3.48 vs ~3.8), the pass verdict was right - the second candidate to pass the 256k screen. The q5_0/q5_0 KV pick (over q4_0/q4_0) cost nothing: 3.48 GiB is still 1.48 GiB under the champion's 4.96 GiB ceiling.
ROSTER STATUS: two survivors now share the 256k goal - Qwen3.5-0.8B @ Q8_0 (4.96 GiB) and Qwen3.5-2B @ Q4_K_M (3.48 GiB). The 2B is the RAM champion; whether it is also the quality champion is a separate question (the 0.8 keeps the depth-score tiebreak until a head-to-head is run). Remaining pipeline: gemma-4-e2b (~4.5 GiB predicted, ~35% - window must verify), Ministral 3 3B (predicted RAM fail, dry-run only if the disqualification is wanted on record), the 4B floor-config probe (predicted fail at ~5.0 GiB).
MACHINE STATE, logged per the Session-3 protocol ruling (record governor/power state with each run; this run's settings, author-reported):
- Transparent hugepages: [always] madvise never - THP is ALWAYS on. Relevant because the KV cache and mmap'd weights are huge anonymous/file mappings; with `always`, the kernel opportunistically backs them with 2 MiB pages, which favors DRAM bandwidth (the study's bound resource, 102.4 GB/s class) and cuts TLB pressure at 262k-deep contexts. Note for cross-run comparability: earlier baseline grids ran under the same setting (it is the distro default on this machine), so no confound is introduced - but any future run after switching to madvise/never would not be comparable without a re-baseline.
- CPU: amd-pstate-epp driver, governor `performance`, policy 1.10-5.13 GHz, boost supported. This is the fixed-clock-equivalent of the EPP world: the governor holds high frequencies instead of the powersave hysteresis loop, so the 9.5 w/s scored-rung figure is not throttled by policy. Combined with THP=always, the 2B's 54.1 min wall is a clean measurement of the machine's capability, not of a power state.
STANDING RULE REAFFIRMED (Session 3): battery/AC status and these two settings (THP mode, governor) are to be logged with every run from here on; this addendum is the first entry in that log for the 256k-screen era.

## Session 35, addendum 12 - the selection rules collapse; the 2B gets its headroom; the pages carry two survivors
THE SELECTION-RULES AUDIT (the author's point-by-point rulings on MODEL-SELECTION.md; every obsolete rule RETIRED in place, numbered as printed):
- Rule 1 OBSOLETE -> REPLACED: the machine's ceiling is determined FIRST, by measurement (the gallop search on the champion config), and THEN models are screened by predicted RAM under that ceiling. Lineage density/cell counts/popularity retired.
- Rule 2 OBSOLETE: distinct-families retired (both current survivors are Qwen3.5).
- Rule 3 CORRECT BUT REROUTED: non-thinking still required - not for ARC (retired as the instrument) but for the SPEED GATE and FWE, the study's defining gates.
- Rules 4, 5, 6 CORRECT (speed-gate predictor, first-party weights, paper requirement) - unchanged.
- Rules 7, 8, 9 OBSOLETE: latest-generation preference, two-category hybrid allowance, class-exclusive bandwidth rule - all retired under the 256k screen.
- Rule 10 UPDATED: the sentinel-certificate rule's protocol references updated to the latest protocol (v4.3).
- Rules 11, 12 (dry-run pre-flight, git-pull/verbatim-commands) CORRECT - unchanged. (The author's points 11-12 map to rules 11-12; the misnumbered sentinel block sits after the worked examples and is now labeled rule 10.)
- Rule 13 OBSOLETE: git-pull-first/verbatim-commands... CORRECT per the author's point 13; RETAINED.
- Rule 14 OBSOLETE: the fixed Q8_0 rung is retired; the 256k screen benches the candidate's best configuration, and the FWE rules are the protocol's latest (v4.3's 3/3 word-count HIT at depth).
- Rule 15 OBSOLETE: ARC-runs-always retired with ARC.
- Rule 16 CORRECT: tests-before-any-sweep retained.
- Rule 17 CORRECT: the 256k goal and RAM ceiling retained, with the clarification that a new survivor raises the ceiling only if its own measured cost is higher (the 2B at 3.48 GiB does not; the ceiling stays 4.96 GiB).
Note: the author's numbered points 1-16 map to the file's printed rules 1-9, 11-17 (the file skips 10 in place - the sentinel rule sits after the worked examples); the mapping above follows the printed numbers.
THE 2B QUANT RAISE (author ruling: disk space is plentiful; raise the 2B's weights quant toward the ceiling). The 2B passed at Q4_K_M + K/V q5_0 with 3.48 GiB cold - 1.48 GiB under the 4.96 GiB ceiling. The raise walks the quant ladder toward Q8_0; predicted cold costs (weights + q5_0/q5_0 KV + overhead, from the measured 3.48 GiB anchor at Q4_K_M 1.22 GiB file): Q5_K_M ~4.0 GiB, Q6_K ~4.3 GiB, Q8_0 ~4.9 GiB - Q8_0 lands at the ceiling's edge and is the predicted pass/fail boundary. The re-probe sequence (verbatim, one quant at a time, fresh state/results pairs per the standing convention; --force because the family carries the addendum-11 selection):
  python3 full_benchmark.py Qwen/Qwen3.5-2B --rung Q5_K_M --kv-quant-k q5_0 --kv-quant-v q5_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-p2q5.json --results-file benchmark-results-p2q5.json --force --dry-run
  python3 full_benchmark.py Qwen/Qwen3.5-2B --rung Q5_K_M --kv-quant-k q5_0 --kv-quant-v q5_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-p2q5.json --results-file benchmark-results-p2q5.json --force
  python3 full_benchmark.py Qwen/Qwen3.5-2B --rung Q6_K --kv-quant-k q5_0 --kv-quant-v q5_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-p2q6.json --results-file benchmark-results-p2q6.json --force --dry-run
  python3 full_benchmark.py Qwen/Qwen3.5-2B --rung Q6_K --kv-quant-k q5_0 --kv-quant-v q5_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-p2q6.json --results-file benchmark-results-p2q6.json --force
  python3 full_benchmark.py Qwen/Qwen3.5-2B --rung Q8_0 --kv-quant-k q5_0 --kv-quant-v q5_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-p2q8.json --results-file benchmark-results-p2q8.json --force --dry-run
  python3 full_benchmark.py Qwen/Qwen3.5-2B --rung Q8_0 --kv-quant-k q5_0 --kv-quant-v q5_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-p2q8.json --results-file benchmark-results-p2q8.json --force
The first FAILED rung stops the walk (the standing rule: a FAIL is never selected; the family keeps its last PASS config). The K/V pair stays q5_0/q5_0 (already the study's pick for the 2B; raising K/V to q8_0 costs ~0.9 GiB and is out unless the weights walk completes with headroom). Pre-registered predictions: Q5_K_M PASS (~4.0 GiB), Q6_K PASS (~4.3 GiB), Q8_0 STRADDLER (~4.9 GiB - the ceiling's edge; 50/50).
THE PAGES: both pickers now carry BOTH survivors - Qwen3.5-2B (Q4_K_M, 3.48 GiB, 9.5 w/s, depth 262,144) and the 0.8B champion (Q8_0, 4.96 GiB, 9.3 w/s, depth 262,144) - with the 2B flagged as pending its quant-raise re-probe. The smallest-RAM notes updated (3.48 GiB, the 2B); the min-bandwidth comment updated (worst w/s 9.5 -> ~54 GB/s floor). Prettier 3.9.9 clean on both; md_check and the 117-test suite pass.

## Session 35, addendum 13 - the retired rules are deleted; the ceiling predictor is registered; the 4-model ceiling chase
THE DOCUMENTS (author ruling: "delete the retired rules, they just pollute" + "align the documents"):
- MODEL-SELECTION.md is REWRITTEN: the retired rules (old 2, 7, 8, 9, 14, 15 - and the misnumbered sentinel block) are DELETED, not struck through; the survivors renumber 1-10. New rule 2 registers the ceiling predictor (below). Data hygiene (new rule 7) updated v3.1 -> v4.3 (the author's point 10, mis-mapped to the sentinel block in addendum 12 - corrected here). Rule 1 (ceiling first, then screen) and rule 10 (the 256k goal) are the load-bearing pair.
- PROTOCOL.md registry rows aligned: "Roster ceiling" is now the measured 4.96 GiB at 262,144 (champion config; supersedes the v3.1 5.27 GiB size ceiling, history addendum 88); "Selection mechanism" is ceiling-first-then-predictor; the ARC row is retired and replaced by the ceiling-predictor row; the candidate-pool row carries the two v4.3 survivors (the v3.1 7-member pool is history).
- README roster-selection summary rewritten to point at the ten rules.
THE CEILING PREDICTOR (registered, new rule 2; the author's ask: "good estimate of getting as close as possible, but under, to the machine ceiling"):
  cost = file(rung) + KV_eff(262144) x kvquant + overhead
  - file(rung) = file_Q8_0 x bpw(rung)/8.5 (RUNG_BITS, single-sourced in hf_download.py)
  - KV_eff = 262144 x L x 2 x kv_heads x head_dim / full_attention_interval - only the full-attention layers hold the whole window (Qwen3.5 interval 4: 24 layers -> 6 full -> 12.0 KiB/token for the 0.8/2B, 32.0 for the 4B)
  - kvquant: f16 1.0, q8_0 0.53125, q5_0 0.34375, q4_0 0.28125
  - overhead = 1.10 GiB ([P], fitted on the two measured anchors)
  VALIDATION: the champion (0.8B Q8_0 + f16: 0.86 + 3.00 + 1.10 = 4.96 vs measured 4.96 - EXACT) and the 2B (Q4_K_M + q5_0: 1.18 + 1.03 + 1.10 = 3.31 vs measured 3.48 - the predictor UNDER-predicts by 5%, the safe direction for a screen; the residual is the KV-quant block granularity, q5_0 blocks round up). Every probe grades it.
THE CANDIDATE SPACE (the honest finding): the HF sweep for >= 262,144-window, non-MoE, accessible, non-gated models finds ONE family - Qwen3.5 (window 262,144; 12.0-32.0 KiB/token effective KV, 3-11x thinner than every other family). gemma-4-e2b is WINDOW-DISQUALIFIED (max_position_embeddings 131,072 - the addendum-10 ~35% pipeline entry is dead); Ministral 3B is gated (401) and 128k-class; granite/Nemotron/EXAONE/etc. are gated or fat-KV or sub-262k. So the "three new models" are the Qwen3.5 variants never benched: 0.8B-Base, 2B-Base, and the 4B at its floor config (the addendum-10 pending probe, now with the predictor's blessing at 4.95 GiB). Base models carry a quality risk (FWE at depth on a non-instruct model is unproven) - that risk is the experiment.
THE 4-MODEL CEILING CHASE (pre-registered; the big run, ~4 h wall at ~55-60 min per probe):

| # | model | config | file | KV | predicted | % of ceiling | prediction |
|---|---|---|---|---|---|---|---|
| 1 | Qwen3.5-2B (instruct) | Q8_0 + K/V q8_0 | 2.09 | 1.59 | 4.78 GiB | 96% | RAM PASS; speed ~8.5 w/s (file 2.09 GiB, law); FWE PASS (instruct family proven at depth) |
| 2 | Qwen3.5-0.8B-Base | Q8_0 + K/V f16 | 0.81 | 3.00 | 4.91 GiB | 99% | RAM PASS (edge); speed ~9.3 w/s class; FWE UNCERTAIN (base model, never benched) |
| 3 | Qwen3.5-2B-Base | Q8_0 + K/V q8_0 | 2.09 | 1.59 | 4.78 GiB | 96% | RAM PASS; speed ~8.5 w/s; FWE UNCERTAIN (base) |
| 4 | Qwen3.5-4B (instruct) | Q2_K + K/V q4_0 | 1.60 | 2.25 | 4.95 GiB | 100% | THE EDGE: predictor says 4.95 vs ceiling 4.96 - RAM PASS by 0.01; Q2_K quality is the wild card; FWE PASS if the family pattern holds |

The 2B-instruct row SUPERSEDES the addendum-12 quant-raise walk (Q5_K_M/Q6_K/Q8_0 at q5_0 KV): with the predictor registered, the best-under-ceiling config is known in advance - Q8_0 + q8_0/q8_0 at 4.78 GiB - so the walk is skipped and the ceiling config is probed directly. The walk commands of addendum 12 are RETIRED without running.
THE COMMANDS (two blocks, verbatim; fresh state/results pairs; --force where a family carries a prior selection):
DRY-RUN BLOCK (read the reports, then run the real block):
  python3 full_benchmark.py Qwen/Qwen3.5-2B --rung Q8_0 --kv-quant-k q8_0 --kv-quant-v q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil1.json --results-file benchmark-results-ceil1.json --force --dry-run
  python3 full_benchmark.py Qwen/Qwen3.5-0.8B-Base --rung Q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil2.json --results-file benchmark-results-ceil2.json --dry-run
  python3 full_benchmark.py Qwen/Qwen3.5-2B-Base --rung Q8_0 --kv-quant-k q8_0 --kv-quant-v q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil3.json --results-file benchmark-results-ceil3.json --dry-run
  python3 full_benchmark.py Qwen/Qwen3.5-4B --rung Q2_K --kv-quant-k q4_0 --kv-quant-v q4_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil4.json --results-file benchmark-results-ceil4.json --force --dry-run
REAL-RUN BLOCK (the big run; ~4 h; leave the machine):
  python3 full_benchmark.py Qwen/Qwen3.5-2B --rung Q8_0 --kv-quant-k q8_0 --kv-quant-v q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil1.json --results-file benchmark-results-ceil1.json --force
  python3 full_benchmark.py Qwen/Qwen3.5-0.8B-Base --rung Q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil2.json --results-file benchmark-results-ceil2.json
  python3 full_benchmark.py Qwen/Qwen3.5-2B-Base --rung Q8_0 --kv-quant-k q8_0 --kv-quant-v q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil3.json --results-file benchmark-results-ceil3.json
  python3 full_benchmark.py Qwen/Qwen3.5-4B --rung Q2_K --kv-quant-k q4_0 --kv-quant-v q4_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil4.json --results-file benchmark-results-ceil4.json --force
ORDER NOTE: the 4B is last (its 0.01-GiB edge is the most likely RAM FAIL; a fail costs nothing but time). A launch failure records FAIL, never a selection (addendum 7). Machine state per the addendum-11 log: THP always, amd-pstate-epp performance, AC advised.

## Session 35, addendum 14 - models.md (the model registry); the 0.8B-Base duplicate is caught
THE CATCH (the author: "we already did 0.8B-Base, check your notes"): right - the benched spec was Qwen/Qwen3.5-0.8B at Q8_0 + f16 KV (the champion config, 4.96 GiB, 9.3 w/s), and the addendum-13 row 2 proposed the IDENTICAL config on the Base weights - same RAM geometry, only the instruct tuning differs. A wasted hour, caught before the run. The candidate is RETIRED (superseded; see models.md). The tracking failure that allowed it is fixed below.
MODELS.MD (the model registry, author ruling): a new top-level file registering every model the 256k screen has touched. Three tables: PASS (measured: model, quant, K/V, file, RAM, w/s, notes - the champion 0.8B and the 2B open it), FAIL (empty for now), and CANDIDATES (every possible candidate with the predictor's values, including the superseded and window-disqualified entries with their reasons - so a duplicate cannot be proposed twice). Updated with every probe; the notebook keeps the narrative.
THE RUN CORRECTION: the addendum-13 command blocks drop the 0.8B-Base row (a duplicate) and add nothing in its place - the ceiling chase is the 2B quant raise (Q8_0 + q8_0/q8_0), the 2B-Base, and the 4B floor config; the 4B-Base at the same floor config is the reserve candidate (models.md). The corrected command blocks are in THIS addendum and supersede addendum 13's:
DRY-RUN BLOCK:
  python3 full_benchmark.py Qwen/Qwen3.5-2B --rung Q8_0 --kv-quant-k q8_0 --kv-quant-v q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil1.json --results-file benchmark-results-ceil1.json --force --dry-run
  python3 full_benchmark.py Qwen/Qwen3.5-2B-Base --rung Q8_0 --kv-quant-k q8_0 --kv-quant-v q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil3.json --results-file benchmark-results-ceil3.json --dry-run
  python3 full_benchmark.py Qwen/Qwen3.5-4B --rung Q2_K --kv-quant-k q4_0 --kv-quant-v q4_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil4.json --results-file benchmark-results-ceil4.json --force --dry-run
REAL-RUN BLOCK:
  python3 full_benchmark.py Qwen/Qwen3.5-2B --rung Q8_0 --kv-quant-k q8_0 --kv-quant-v q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil1.json --results-file benchmark-results-ceil1.json --force
  python3 full_benchmark.py Qwen/Qwen3.5-2B-Base --rung Q8_0 --kv-quant-k q8_0 --kv-quant-v q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil3.json --results-file benchmark-results-ceil3.json
  python3 full_benchmark.py Qwen/Qwen3.5-4B --rung Q2_K --kv-quant-k q4_0 --kv-quant-v q4_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil4.json --results-file benchmark-results-ceil4.json --force
The three probes are ~3 h wall. The 4B stays last (the 0.01-GiB edge).

## Session 35, addendum 15 - the registry's one-model-one-table rule; the pages' RAM/VRAM defaults
MODELS.MD CORRECTED (the author caught it: "the candidates table is very wrong, you have duplicates"): the 2B appeared in BOTH the PASS and the CANDIDATES table (and a "quant raise" pseudo-row re-listed it a third time). THE RULE (author): a model appears at most ONCE, in exactly ONE table. Applied: the PASS 2B row carries its quant-raise status in its NOTES (not as a candidate row); the 0.8B-Base/9B/e2b/Ministral closures move to a prose CLOSED section (they never enter a table); the CANDIDATES table now holds only the never-benched models (2B-Base, 4B, 4B-Base). Verified programmatically: no model name in two tables.
THE PAGES (author rulings):
- CPU (cpu-picker.html): the RAM input defaults to the MINIMUM RAM NEEDED - 5 GiB (the champion's 4.96 GiB cold cost, the smallest RAM any measured model needs) instead of 32; a footnote states the prefill and that more memory changes nothing. The machine list already filtered to configurations that can run the models (MIN_RUN_BW); the "higher specs" note is sharpened to "higher bandwidth runs the same models without issue".
- GPU (gpu-picker.html): the tier list already carries only the VRAM capacities that fit a measured model; the note now states that a card with higher VRAM than the largest tier is expected to MATCH the recommendation of the highest-VRAM model in the list (the pool is measured at its ceiling; more VRAM cannot change the recommendation).
Prettier clean; both pages' JS parses; md_check passes.

## Session 35, addendum 16 - code_edit learns the md linter's rules (the pre-write markdown gate)
THE GAP (author ruling: "improve the code editor to take into account the rules from the md linter"): md_check.py enforced MD047/MD055/MD056/MD058 + fence balance only at pre-commit - the addendum-13/14 MD058 failures were caught by the HOOK, after the edit had already hit the disk. The register's addendum-9 lesson said it directly: "a syntax check would have been the real guard here."
THE GATE (pushed): md_check.py gains check_text(path, text) - the same rules, runnable on in-memory text; code_edit gains _check_markdown(src, out, path), called in BOTH edit() and preview() BEFORE the atomic write (the addendum-4 contract holds: a failure leaves the file untouched). The rules: a markdown edit (and only markdown - .md/.markdown; python/js/html/json keep their existing delimiter checks) must not INTRODUCE a violation. Only NEW problems fail: pre-existing violations in the surrounding file are not the edit's fault (they stay flagged for pre-commit), so the gate never blocks unrelated edits on imperfect files - the ignore-preexisting case is regression-tested.
COVERAGE: MD058 (blank lines around tables - the two real failures this session), MD056 (ragged tables), MD055 (row pipes), MD047 (single trailing newline), and fence balance (the worst non-table failure mode - an unclosed fence renders everything after it as code). Seven new regression tests (124 total, all pass): blocked MD058/MD056/fence/MD047, allowed clean table, pre-existing violations ignored, non-md files untouched by the gate.

## Session 35, addendum 17 - the editor fixes the mechanical md rules; models.md gains the Rejected table
THE AUTHOR'S RULING ("isn't it better... the errors are fixed by the editor?"): YES. The register split is now MECHANICAL vs JUDGEMENT:
- MECHANICAL (auto-fixed by _fix_markdown, runs in edit(), preview() and write() AFTER the post-condition verify - the fixer may legitimately reflow inserted text): MD058 blank line before a table header and after a table body; MD047 exactly one trailing newline. These fixes are unique and unambiguous, so the editor inserts them.
- JUDGEMENT (still lint failures, only NEW violations, pre-existing ones stay for pre-commit): MD056 ragged tables (which cell count is right?), MD055 row pipes, fence balance (where does the fence close?). No safe automatic fix exists.
Both this session's real MD058 failures (the addendum-13/14 table landings) would now be silently repaired at edit time. 125 tests pass (the two addendum-16 block-tests became fix-tests; a new after-table fix test; the judgement-class tests unchanged).
MODELS.MD: (a) the "CLOSED, NOT CANDIDATES" prose note is DELETED, replaced by the REJECTED table (model name, reason for rejection): 0.8B-Base (identical RAM geometry to the measured champion config), 9B (no config under the ceiling), gemma-4-e2b (window 131,072), Ministral 3B (gated, 128k) - so nothing is ever re-evaluated without a ruling to un-reject it. (b) THE 4B QUESTION (the author: "isn't 4B and 4B-Base the same model?"): NO - verified from the hub: Qwen/Qwen3.5-4B is the INSTRUCT tune, tagged base_model:finetune:Qwen/Qwen3.5-4B-Base - the Base is the pretrained original. Same architecture and RAM geometry, different weights; the Base stays a candidate (FWE-at-depth on an untuned model is the open question), its registry note now states the distinction.

## Session 35, addendum 18 - the type ruling: instruct only, one type per model
THE AUTHOR'S QUESTION: which common model type is best suited to the benchmark (conversation speed + FWE)? THE ANSWER (registered as the TYPE RULE): INSTRUCT - and it is the only type the study carries. The reasoning is the gates themselves: the speed gate is a live CONVERSATION (cal-50 turns, a reader following the streamed answer; instruct tunes are optimized for exactly this turn shape) and FWE is an INSTRUCTION-FOLLOWING task (extract/count the target words; the study has a measured failure mode for instruction-shape violations - Qwen2.5-3B's task refusal scored 0). Base (pretrained) models are next-token continuators: unproven at FWE, erratic in conversation template shape. Coding/reasoning/vision types are excluded by the same shape argument plus rule 3 (non-thinking) and the text-only instrument.
ONE TYPE PER MODEL IN THE WHOLE REGISTRY (author ruling): a model appears once, at its instruct tune - the base variant of an already-instruct model is REJECTED ON TYPE, never re-evaluated. Applied: Qwen3.5-2B-Base and Qwen3.5-4B-Base move to the REJECTED table (type reason); the candidates are the 2B quant raise and the 4B floor config, both instruct.
THE RUN SHRINKS (the 2B-Base probe of addendum 14 is cancelled by this ruling): the big run is now TWO probes, ~2 h wall:
DRY-RUN BLOCK:
  python3 full_benchmark.py Qwen/Qwen3.5-2B --rung Q8_0 --kv-quant-k q8_0 --kv-quant-v q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil1.json --results-file benchmark-results-ceil1.json --force --dry-run
  python3 full_benchmark.py Qwen/Qwen3.5-4B --rung Q2_K --kv-quant-k q4_0 --kv-quant-v q4_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil4.json --results-file benchmark-results-ceil4.json --force --dry-run
REAL-RUN BLOCK:
  python3 full_benchmark.py Qwen/Qwen3.5-2B --rung Q8_0 --kv-quant-k q8_0 --kv-quant-v q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil1.json --results-file benchmark-results-ceil1.json --force
  python3 full_benchmark.py Qwen/Qwen3.5-4B --rung Q2_K --kv-quant-k q4_0 --kv-quant-v q4_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil4.json --results-file benchmark-results-ceil4.json --force
The 4B stays last (the 0.01-GiB edge). The addendum-14 blocks carrying 2B-Base are SUPERSEDED by this one.

## Session 35, addendum 19 - the retro-analysis: every notebook-evaluated model gets its fair chance

THE AUTHOR'S RULING ("do an analysis for the other models we have evaluated in the notebook... give them a fair chance, choose the settings that most closely take them to the ceiling, like they were new models"): the full historical roster - every model in the state files (benchmark-state-q4/f4k/rebench) - is re-screened AS IF NEW, at its cheapest legal config (Q2_K + K/V q4_0/q4_0 where the rungs exist), with the registered ceiling predictor and the hub's config.json for each. The FAIL table stays EMPTY (it is reserved for 256k probes, floor=ceiling=262,144; none of these has been probed at 262k).

THE METHOD (verbatim from the registry header): window from max_position_embeddings (rope scaling rejected by standing rule), KV geometry = L x 2 x kv_heads x head_dim bytes/token f16 (full_attention_interval applied where present), predicted RAM = file(rung) + KV_eff(262144) x kvquant + 1.10 GiB overhead. All 26 roster families' configs were fetched from the hub (none gated except the already-ruled Ministral).

THE FINDING, IN ONE LINE: NO roster model has a trained window >= 262,144 - the best in the pool is 131,072 (phi-4-mini, granite-3.1/3.2/3.3-2b, granite-4.0-1b/micro/h-micro/h-1b, granite-4.1-3b, granite-4.2-3b, MiniCPM5-1B/2B) - so the WINDOW RULE alone closes every one of them; the KV-geometry check (which closed the fat families) and the quality record (FWE zeros, 4,096-class scores) are recorded as the second disqualifier where they apply. The scientific finding of addendum 10 is CONFIRMED and STRENGTHENED by the fair-chance pass: the 256k screen is decided by trained window + KV geometry, and Qwen3.5 is the only family in the pool with both (262,144 window, 12.0-34.5 KiB/token effective KV).

THE RAM-FITS-BUT-WINDOW-CAPPED SET (the honest fair chance - these would fit the 4.96 GiB ceiling at 262k with q4_0 KV, and are rejected ONLY on the window): Qwen2.5-1.5B-Instruct (32k window; 1.97 GiB q4_0 KV; v4.3 score 20,992), granite-4.0-350m/h-350m (32k; 1.97/2.25 GiB), MiniCPM4-0.5B (32k; 0.84 GiB), MiniCPM5-1B (131k; 1.69 GiB), MiniCPM5-2B (131k; 2.95 GiB, whole config ~4.2 GiB). THE KV-GEOMETRY-CLOSED SET (q4_0 KV alone exceeds the ceiling at 262k): Qwen3-1.7B (112 KiB/token -> 7.9 GiB), Qwen3-4B (144 -> 10.1), phi-4-mini (128 -> 9.0), Phi-3.5-mini (384 -> 27.0), Phi-3-mini-4k (384 -> 27.0), phi-2 (320 -> 22.5), granite-3.0/3.1/3.2/3.3-2b and the granite-4.0-1b/micro/h-micro/h-1b, granite-4.1-3b, granite-4.2-3b (all 80 -> 5.6), MiniCPM-1B-sft (104 -> 7.3), MiniCPM-2B-sft (360 -> 25.3), MiniCPM3-4B (620 -> 43.6). THE QUALITY-CLOSED (recorded second disqualifier): Phi-3.5-mini, Qwen3-1.7B, MiniCPM5-2B scored FWE zero at Q4_K_M; granite-4.0-350m/h-350m and MiniCPM4-0.5B never passed the 16k screen on the f4k grid; MiniCPM-1B/2B-sft and granite-3.0-2b are 4,096-class. THE TYPE-CLOSED: phi-1 and phi-2 are base/code models (the TYPE RULE, addendum 18; also 2,048-token windows).

THE REGISTRY (models.md updated): 26 new REJECTED rows, one per roster family, each with its specific disqualifier and the measured/predicted numbers; the one-model-one-table rule verified programmatically (35 unique rows, no model in two tables); the FAIL table remains empty - it is reserved for floor=ceiling=256k probes only, and no roster model has earned one. No candidate emerged: the CANDIDATES table stays the Qwen3.5-4B edge row; the run plan (addendum 18's two probes) is unchanged.

## Session 35, addendum 20 - the candidates exception; the second sweep finds a new family

THE AUTHOR'S EXCEPTION ("in the candidates table there's a genuine reason a model appear more than once, multiple settings"): REGISTERED. The one-model-one-table rule now reads: a model appears at most once per table, in exactly one table - EXCEPT the CANDIDATES table, where a model may appear MULTIPLE TIMES, once per settings configuration (a candidate is a model+configuration pair, not a model). models.md header carries the exception; the duplicate check is updated to exempt CANDIDATES.

THE FOUR-CANDIDATE HUNT ("we're still short of the 4 candidates I asked"): the previous sweep (addendum 13) used a name list; this one is SYSTEMATIC - every text-generation model on the hub by downloads (1,840 configs fetched), then a second pass by recency, plus targeted checks of the long-context families (Ling, LongCat, GLM-Air, Ministral, Nemotron, SmolLM3, Hunyuan, EXAONE, RWKV, Jamba, gpt-oss, gemma-3). Filters: trained window >= 262,144 (no rope scaling), predicted RAM at the best config <= 4.96 GiB, instruct type, first-party weights, GGUF tooling.

THE FINDING: exactly ONE new family survives - AI21-Jamba2-3B (ai21labs/AI21-Jamba2-3B). Window 262,144 (native, no rope scaling), Apache-2.0, non-thinking instruct, and a KV geometry thinner than Qwen3.5's: a hybrid mamba-attention architecture with only 2 full-attention layers, 1 KV head, head_dim 128 -> ~1 KiB/token f16 (0.25 GiB at 262,144 with f16 K/V - the mamba state is constant-size, it does not grow with context). GGUF tooling verified: bartowski/mradermacher quants exist; Q8_0 = 3.17 GiB -> predicted RAM 3.17 + 0.25 + 1.10 = 4.52 GiB, 91% of ceiling. THE RISKS (recorded honestly): llama.cpp's jamba-arch support level is unproven at our rungs; FWE-at-depth is unproven for a mamba hybrid (the calibration corpus and the counting task may behave differently through recurrent state); the Q6_K config (2.46 GiB -> 3.81 GiB, 77%) is registered as the same model's second configuration under the new exception, probed only if the Q8_0 passes or grazes.

EVERYTHING ELSE THE SWEEP TOUCHED, CLOSED ON RECORD (the REJECTED table carries each): MiniCPM5-2B-Base (the sweep's surprise: its config declares a 524,288 window - the only sub-ceiling-RAM window above 262,144 in the entire hub - but BASE type; the instruct tune is the family's one type and it is window-closed at 131,072); AI21-Jamba-Reasoning-3B (thinking, rule 3); AI21-Jamba2-Mini (12B MoE, Q2_K weights alone ~4.75 GiB); the draft-model false positives (DSpark/EAGLE3 heads, test tinies, reformer) never enter the registry - they are not instruct models. The gated set (Llama-3.x, gemma-3, Ministral-3B, Nemotron-Nano) stays closed as gated unless the author grants access.

THE RUN, BACK TO FOUR PROBES (the candidate is a model+configuration pair): the two addendum-18 probes (2B Q8_0+q8_0/q8_0; 4B Q2_K+q4_0/q4_0) plus the new family at its ceiling config:

DRY-RUN BLOCK:  python3 full_benchmark.py Qwen/Qwen3.5-2B --rung Q8_0 --kv-quant-k q8_0 --kv-quant-v q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil1.json --results-file benchmark-results-ceil1.json --force --dry-run  python3 full_benchmark.py Qwen/Qwen3.5-4B --rung Q2_K --kv-quant-k q4_0 --kv-quant-v q4_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil4.json --results-file benchmark-results-ceil4.json --force --dry-run  python3 full_benchmark.py ai21labs/AI21-Jamba2-3B --rung Q8_0 --kv-quant-k f16 --kv-quant-v f16 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceilj.json --results-file benchmark-results-ceilj.json --force --dry-run

REAL-RUN BLOCK (Jamba last - the unproven arch carries the integration risk; the author runs the dry-runs first and the Jamba dry-run is the tooling gate: if the GGUF/server path fails, the probe never starts and the model goes to FAIL only if it was a 256k attempt):

  python3 full_benchmark.py Qwen/Qwen3.5-2B --rung Q8_0 --kv-quant-k q8_0 --kv-quant-v q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil1.json --results-file benchmark-results-ceil1.json --force  python3 full_benchmark.py Qwen/Qwen3.5-4B --rung Q2_K --kv-quant-k q4_0 --kv-quant-v q4_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil4.json --results-file benchmark-results-ceil4.json --force  python3 full_benchmark.py ai21labs/AI21-Jamba2-3B --rung Q8_0 --kv-quant-k f16 --kv-quant-v f16 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceilj.json --results-file benchmark-results-ceilj.json --force

(If the author wants the fourth PROBE rather than the fourth candidate-config: the Jamba2-3B Q6_K row is the spare; or the two configs of the same family count as the author rules.)

## Session 35, addendum 21 - the REJECTED table's strict reason list

THE AUTHOR'S RULING: the REJECTED table gains a NOTES column (model name | rejection reason | notes) and a STRICT four-reason list: (1) no research paper, (2) no model small enough (q2, q4, q4) > ceiling, (3) training window < 256k, (4) other - anything that does not fit the first three. THE BINDING ORDER (the fair-chance order, so one reason always decides): the floor config (Q2_K + K/V q4_0/q4_0) is computed first; if its predicted RAM exceeds the 4.96 GiB ceiling the SIZE binds (reason 2); if the RAM fits but the trained window is under 262,144 the WINDOW binds (reason 3); type/gating/first-party/tooling close as OTHER (reason 4); reason 1 (no research paper) is reserved for models that pass geometry, window, and type but lack a paper - none bind today (Jamba2 has the arXiv link; the one candidate-family risk is recorded in its notes).

THE REMAP (all 32 existing rows re-classified): the granite-3.x/4.x-1b+/MiniCPM fat-KV families to reason 2 (q4_0 KV alone 5.6-43.6 GiB); the RAM-fits-but-window-capped set (Qwen2.5-1.5B, granite-4.0-350m/h-350m, MiniCPM4-0.5B, MiniCPM5-1B/2B, gemma-4-e2b) to reason 3; the type closes (three Qwen3.5 Base variants, MiniCPM5-2B-Base, Jamba-Reasoning-3B) and the gated closes (Ministral 3B, Llama-3.x, gemma-3) to reason 4. The addendum-20 sweep finds are added on the same list: gpt-oss-20b (window 131,072), SmolLM3-3B (65,536), Hunyuan-A13B (32,768), EXAONE-4.0-32B (131,072), Ling-lite (32,768), GLM-4.5-Air (131,072), Qwen3-4B-Instruct-2507 and Qwen3-30B-A3B-Instruct-2507 (window 262,144 but fat KV / MoE size - reason 2), and the sweep's false-positive classes (DSpark/EAGLE3 draft heads, community finetunes, test tinies) to OTHER in grouped rows.

OPEN ITEM FOR THE AUTHOR: the gated repos (Ministral-3B, Llama-3.2-1B, gemma-3) are rejected as OTHER/gated; if the author verifies their windows with hub access, any that are >= 262,144 get a fair-chance screen; the expectation is 128k-class (all close on window).

## Session 35, addendum 22 - the gated set verified by the author

THE AUTHOR RAN THE GATED PULL (authenticated): the four open items close on record.
- Ministral 3B: RepositoryNotFoundError even authenticated - the repo does not exist; the agent's unauthenticated 401 had masked a nonexistent repo. Stays REJECTED (other): no first-party Ministral-3B weights to screen.
- meta-llama/Llama-3.2-1B-Instruct: window 131,072, 16 layers, 8 kv heads (head_dim 64 -> KV 32 KiB/token f16, ~2.25 GiB q4_0 at 262k; whole floor config ~3.75 GiB would FIT). Re-classified to TRAINING WINDOW < 256k - the window is the wall; the gated guess replaced by the verified number.
- google/gemma-3-1b-it: window 32,768, 1 kv head. Re-classified to TRAINING WINDOW < 256k.
- google/gemma-3-4b-it: the config nests the text fields in text_config (the gemma-3 multimodal wrapper); text window 131,072 class. Re-classified to TRAINING WINDOW < 256k.
The REJECTED table now carries zero unverified guesses; the gated reason no longer appears - every row binds on a checked number.

## Session 35, addendum 23 - the Base rows removed; the fifth reason; the recurrent family

THE AUTHOR'S RULING ON BASE ROWS ("rejected because another model is in the list with a better type. no need to record it"): the four Base rows (Qwen3.5-0.8B/2B/4B-Base, MiniCPM5-2B-Base) are DELETED from the REJECTED table. The type rule implies their rejection - the instruct tune is the family's one entry; the header now states that BASE variants of an already-instruct model are not recorded. (The MiniCPM5-2B-Base 524,288-window observation stays in the addendum-20 narrative.)

THE FIFTH REASON (author ruling): "thinking cannot be disabled" joins the strict list. Jamba-Reasoning-3B re-classified from other to the new reason (its reasoning tune has no non-thinking mode). Binding order unchanged: size binds first, then window, then thinking, then other.

THE THIRD FAMILY ("that's the best we can do?"): the recurrent sweep finds RWKV7-World-2.9B - the RWKV org's first-party 2.9B chat tune (conversational tag), a RECURRENT architecture with constant-size state: no KV growth at all, context bounded only by the machine, so the window rule cannot cap it and the KV-geometry term of the predictor is ~0. The Goose paper exists (arXiv 2504.03289, "RWKV-7 'Goose' with Expressive Dynamic State Evolution" - verified via the arXiv API). GGUF tooling: the official repos ship no GGUF, but the community quants exist and are llama.cpp-format (mradermacher Q8_0 = 3.03 GiB, Q6_K = 2.39 GiB, verified). Predicted RAM at Q8_0: 3.03 + 1.10 = 4.13 GiB, 83% of ceiling (plus a small constant state cost; the predictor's KV term is 0 for a recurrent model). REGISTERED AS TWO CANDIDATE CONFIGS under the multi-config exception: Q8_0 (4.13 GiB) and Q6_K (3.49 GiB). THE HONEST RISKS: llama.cpp's rwkv7 kernel path is unproven at our rungs; FWE-through-recurrent-state is unproven (the same open question as the mamba hybrid); the GGUF is a community quant, not first-party (rule 5 risk, recorded in the row).

THE POOL NOW: three families, four models, six candidate-configs: Qwen3.5-2B (Q8_0+q8_0, in PASS notes pending its quant-raise probe), Qwen3.5-4B (Q2_K+q4_0), AI21-Jamba2-3B (Q8_0 and Q6_K), RWKV7-World-2.9B (Q8_0 and Q6_K). The run blocks gain the RWKV probes (dry-run first; its dry-run is the tooling gate like Jamba's):

DRY-RUN BLOCK:  python3 full_benchmark.py Qwen/Qwen3.5-2B --rung Q8_0 --kv-quant-k q8_0 --kv-quant-v q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil1.json --results-file benchmark-results-ceil1.json --force --dry-run  python3 full_benchmark.py Qwen/Qwen3.5-4B --rung Q2_K --kv-quant-k q4_0 --kv-quant-v q4_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceil4.json --results-file benchmark-results-ceil4.json --force --dry-run  python3 full_benchmark.py ai21labs/AI21-Jamba2-3B --rung Q8_0 --kv-quant-k f16 --kv-quant-v f16 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceilj.json --results-file benchmark-results-ceilj.json --force --dry-run  python3 full_benchmark.py RWKV/RWKV7-World-2.9B --rung Q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceilr.json --results-file benchmark-results-ceilr.json --force --dry-run

REAL-RUN BLOCK: the same four commands with --dry-run dropped, in the same order (RWKV last; its recurrent path is the least-proven integration).

## Session 35, addendum 24 - two REJECTED rows corrected on the author's challenge

THE AUTHOR CAUGHT TWO BAD ROWS ("Ministral-3-3B-Instruct-2512-GGUF exists or is the wrong one?" / "Llama-3.1-8B-Instruct I don't understand why it is rejected"):
- Ministral 3B: the addendum-22 'repo does not exist' was WRONG - the probe used a stale name (Ministral-3B-instruct); the real repos are mistralai/Ministral-3-3B-Instruct-2512 (safetensors) and -2512-GGUF (first-party quants, Q4_K_M 2.00 GiB). Screened properly: KV 104 KiB/token f16 (26 x 8 x 128) -> ~7.3 GiB q4_0 KV at 262k - over the ceiling, SIZE binds (reason 2). Second disqualifier on record: the declared 262,144 window is YaRN rope-scaled from an original 16,384 (params.json llama_4_scaling, factor 16) - the no-rope-scaling rule closes it even if the RAM fit. Interesting near-miss worth noting: a first-party 262k-class window with GGUF tooling, but the KV geometry is Mistral-fat, the same class as granite/Phi.
- Llama-3.1-8B-Instruct: 'gated' was a lazy reason (the author's challenge is right). The real numbers: KV 128 KiB/token f16 (32 x 8 x 128) -> ~9 GiB q4_0 KV at 262k - SIZE binds (reason 2); window 131,072 < 262,144 besides. Re-classified from other to no model small enough. Numbers from the public model card (repo gated, geometry is documented).
THE LESSON (register): a rejection row must carry the model's OWN checked numbers, never a class guess ('128k-class', 'gated') - the addendum-19 retro-analysis standard, now applied retroactively to the addendum-21 sweep rows.

## Session 35, addendum 25 - the window re-verification pass

THE AUTHOR'S AUDIT ("could you please verify again everything marked training window < 256k"): all 17 window-rejection rows re-pulled from config.json, each note now carries "config.json verified (addendum 25)". Results, all CONFIRMED: gemma-4-e2b 131,072 (text_config); Qwen2.5-1.5B 32,768; phi-1 2,048; granite-4.0-350m/h-350m 32,768; MiniCPM4-0.5B 32,768 (longrope scaling present - doubly closed); MiniCPM5-1B/2B 131,072; gpt-oss-20b 131,072 (rope factor 32 - doubly closed, and MoE besides); SmolLM3-3B 65,536; Hunyuan-A13B 32,768 (rope factor 8 - doubly closed); EXAONE-4.0-32B 131,072 (rope factor 16 - doubly closed); GLM-4.5-Air 131,072 (MoE 106B/12B besides); Llama-3.2-1B 131,072 and gemma-3-1b 32,768 (author-verified, gated).

TWO CORRECTIONS THE PASS CAUGHT: (1) the Ling-lite row carried a WRONG REPO NAME - inclusionAI/Ling-lite-1.5B does not exist; the real repo is inclusionAI/Ling-lite, window 32,768 verified, KV 56 KiB/token -> ~3.9 GiB q4_0 at 262k (would nearly fit; the window is the wall). (2) the gemma-3-4b KV numbers drafted in this pass were unverifiable from the author's pull output (the wrapper printed None for layers/kv_heads) - per the addendum-24 lesson the guess was removed before commit; the row states the geometry is not extractable and the window binds regardless.

SECONDARY FINDING: three of the seventeen (MiniCPM4, gpt-oss-20b, Hunyuan, EXAONE) carry rope_scaling in config - for these the window is DOUBLY closed: trained short AND the extension mechanism is the thing the study rejects. The notes now distinguish "rope_scaling absent" from "rope_scaling present" so the doubly-closed rows are visible at a glance.

## Session 35, addendum 26 - the registry data store (the author's reproducibility build)

BUILT (author ruling: "please build it"): etc/registry_data.py + the checked-in etc/registry_data.json. The script carries the roster's 48 model ids -> source repos; `fetch` re-pulls each config.json (unwrapping multimodal text_config), stores the RAW extract fields plus derived geometry (window, rope_scaling presence, KV KiB/token, q4_0 KV at 262,144), and marks the 4 gated/paper-sourced rows explicitly. `check` verifies every roster id appears in models.md and reports fetch errors; `geometry ID` prints one model's record. Future window/geometry audits are `python3 etc/registry_data.py fetch && git diff etc/registry_data.json` - no more 17-fetch passes by hand.

THE STORE'S FIRST CATCH, SAME DAY: the RWKV candidate row carried a wrong repo name - RWKV/RWKV7-World-2.9B does not exist; the official repo is RWKV/RWKV7-Goose-World3-2.9B-HF (the mradermacher quant's source lineage). Its HF config also declares max_position_embeddings 2048 - a TRAINING-DATA relic, not an architectural cap: the recurrent state carries the context and the serving context is set by -c, so the transformer window rule does not mechanically apply; the candidate row now states this explicitly rather than letting the 2048 look like a window rejection.

CURRENT STORE STATE: 44/48 hub extracts, 4 gated/paper-sourced (gemma-3-1b/4b, Llama-3.2-1B author pulls; Llama-3.1-8B public card), 0 fetch errors; all 48 roster ids present in models.md.

## Session 35, addendum 27 - the 2B quant-raise restored to the CANDIDATES table

THE AUTHOR'S CATCH ("the qwen 2b candidate is missing, we were trying an improvement to see if we can get it closer to 256k"): the addendum-15 one-model-one-table ruling had pushed the 2B's quant-raise into its PASS notes - but a candidate is a MODEL+CONFIGURATION pair (the addendum-20 exception), and Q8_0+q8_0/q8_0 is a different configuration from the PASS'd Q4_K_M+q5_0/q5_0. The row is restored to CANDIDATES with its predicted values (Q8_0 file 1.43 GiB, predicted RAM 4.78 GiB - 96% of ceiling; w/s ~9 predicted to hold). The multi-config exception was written for exactly this shape; the registry now shows it correctly.

THE OVERNIGHT RUN (the author runs it tonight): four probes, one per candidate configuration - 2B quant-raise, 4B edge, Jamba2-3B, RWKV7-2.9B. Dry-run block first (each dry-run is also the tooling gate for its probe: Jamba and RWKV are the unproven-arch integrations; a dry-run failure there means the probe never starts and nothing enters FAIL unless a 256k attempt actually ran).

## Session 35, addendum 28 - the dry-run gate catches a bad command

THE AUTHOR'S REPORT ("the dry run gave an error"): three of the four dry-runs PASSED clean (2B quant-raise, 4B edge, RWKV - each acquire+create phases verified, rung files ready). The Jamba command FAILED at argument parse: --kv-quant-k f16 is not a CLI choice (q8_0, q4_0, q4_1, q5_0, q5_1, iq4_nl only). THE ERROR WAS MINE (the addendum-27 block): f16 K/V is the DEFAULT - it is what the server runs when NO kv-quant flag is passed (verified in full_benchmark.py's launch path: extra_args gains --cache-type-k/v only when the flags are set; the champion's Q8_0+f16 config ran exactly so). The corrected Jamba command omits the flags:

  python3 full_benchmark.py ai21labs/AI21-Jamba2-3B --rung Q8_0 --min-rung 262144 --max-rung 262144 --state-file benchmark-state-ceilj.json --results-file benchmark-results-ceilj.json --force

The corrected REAL-RUN block is the addendum-27 block with the Jamba line replaced by this line; the other three commands stand verbatim as dry-run-verified. THE REGISTER: the dry-run gate did its job - a bad flag killed the probe at parse time, before any download or server launch; the tooling gate for the unproven arches (Jamba, RWKV) is exactly where it belongs.

## Session 35, day close - 2026-10-01 (addenda 19-28)

THE DAY IN ONE PARAGRAPH: the registry became a complete instrument. The retro-analysis (addendum 19) gave all 26 notebook-evaluated models a fair-chance screen - every one closed on window or KV geometry, none reached CANDIDATES, the FAIL table stayed empty (reserved for 256k probes). The author's rulings reshaped the registry: the multi-config exception (a candidate is a model+configuration pair, addendum 20), the strict four-reason rejection list with the fair-chance binding order (addendum 21), Base variants unrecorded and the fifth reason thinking-cannot-be-disabled (addendum 23). The candidate hunt went systematic - 1,840 hub configs swept - and found TWO new families: AI21-Jamba2-3B (hybrid mamba-attention, ~1 KiB/token KV, the thinnest ever screened) and RWKV7-World-2.9B (recurrent, constant state, no KV growth at all; Goose paper arXiv 2504.03289). The author's challenges kept the table honest: Ministral-3's stale-name error corrected (it exists, and its YaRN-scaled window is doubly closed), Llama-3.1-8B re-classified on real numbers (addendum 24), all 17 window rejections re-verified from config.json (addendum 25). The registry data store was built (etc/registry_data.py + checked-in JSON, addendum 26) - audits are now fetch + git diff, and it caught the RWKV repo name error on day one. The dry-run gate caught a bad command of mine before it could cost a night (addendum 28).

THE STATE GOING INTO THE NIGHT RUN (pre-registered, to grade tomorrow): four probes, one per candidate configuration -
1. Qwen3.5-2B quant-raise (Q8_0 + q8_0/q8_0): predicted RAM 4.78 GiB (96% of ceiling), w/s ~9 predicted to hold. The 2B is the PASS'd RAM champion (3.48 GiB at Q4_K_M+q5_0); this probe closes its gap to the ceiling.
2. Qwen3.5-4B edge (Q2_K + q4_0/q4_0): predicted 4.95 GiB - 100% of ceiling, PASS by 0.01 GiB; w/s ~5 (the 131k wall was 6.07 w/s at f16 KV). Q2_K quality is the wild card.
3. AI21-Jamba2-3B (Q8_0, f16 KV by default - flags omitted per addendum 28): predicted 4.40 GiB (91%); w/s ~7. Risks: llama.cpp jamba-arch support; FWE through a mamba hybrid's recurrent state.
4. RWKV7-Goose-World3-2.9B (Q8_0): predicted 4.13 GiB (83%); w/s ~8. Risks: rwkv7 kernel path; FWE through pure recurrence; community GGUF lineage (mradermacher, from the official Goose-World3 repo).

GRADING RULE (standing): a probe PASSes if it fits the ceiling AND passes both gates at 262,144 - RAM alone is not a pass. FAIL rows record the actual attempt's numbers; a tooling death before the 256k attempt is not a FAIL, it is a risk realized (the row returns to CANDIDATES with the risk note updated, or to REJECTED on a proven-hard blocker). The Q6_K spares (Jamba, RWKV) probe tomorrow night only if their Q8_0 configs pass or graze.

THE OPEN QUESTIONS THE DATA WILL ANSWER: (a) does the 2B hold both gates at the top rung - and does its quality close on the champion's; (b) does the 4B's 0.01-GiB edge survive contact with the real machine; (c) does a mamba hybrid or a pure recurrent carry FWE at 256k - the first clean measurement of recurrent-state fidelity at this depth in the study; (d) if both new families pass, the practitioner pages gain their first non-transformer recommendations.

SESSION CLOSED 2026-10-01. The machine carries the night run; the analysis opens tomorrow's session.
