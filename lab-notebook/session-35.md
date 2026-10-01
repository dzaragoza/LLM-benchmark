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
