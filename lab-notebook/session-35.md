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
