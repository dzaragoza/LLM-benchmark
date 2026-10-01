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
