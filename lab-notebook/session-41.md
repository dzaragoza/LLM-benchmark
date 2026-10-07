# Session 41 - 2026-10-07

Opened 2026-10-07 (no session was open for today - session 40 was
opened 2026-10-06 and its tail addenda were working-day continuations;
per the notebook's one-session-per-day convention this session is
new). The day's first work landed at 07:42 (addendum 59, protocol
v5.0). The day was a requirements-engineering day plus a live-run
support day: the protocol became v5.x (requirements as a test-linked
contract), the window tax was ruled away (ctx = depth), the 4k-window
trio was revived and re-opened, and two restart-path crashes were
caught and fixed (the answered-rung skip that barred terminal
families; the state name that went to the hub as a repo).

## Addenda 58-63 (moved from session 40 per the one-session-per-day rule)

These addenda were registered and committed 2026-10-07 but sat in
session 40 (opened 2026-10-06); they belong to today. Numbers
preserved verbatim as registered.

### Addendum 58 - the registry pre-flight: the window was known before the download (2026-10-07, the author's ruling)

THE RULING: "So we measured and downloaded every model at 4k for nothing. They should have never been even evaluated." Correct - the registry store already carries every family's trained window (the hub config.json extract, max_position_embeddings, fetched at registry time), so the addendum-45 families (phi-1 window 2,048; MiniCPM sft pair 4,096; Phi-3-mini-4k 4,096) were downloaded, converted and launched to discover what the store said all along.

THE FIX: a REGISTRY PRE-FLIGHT in both certify controllers, before any download, conversion or launch: _registry_window(fam) reads the store (geometry.window, else the extract's max_position_embeddings); a window below the rung's ctx (depth + 2x128 answer headroom) declares the family INFEASIBLE immediately - same state record as the runtime catch (fst["infeasible"] = {window_cap, depth}, addendum 45), so every existing skip/statistic applies - and prints "nothing downloaded, converted or launched". An UNKNOWN window (no extract, e.g. a gated repo) leaves the gate silent: the launch banner remains the authority and addendum 45 catches it at runtime. The pre-flight fires per rung, so it also answers the mid-ladder case: as the ladder climbs, each family whose window falls below the new rung's ctx exits before its download would ever start.

Tests: test_registry_preflight_declares_infeasible_before_download (a 2,048-window family at 4,096 goes infeasible with ZERO hub touches - the acquire is never called; the state record and the printed reason match the runtime catch). 195 tests.

### Addendum 59 - protocol v5.0: requirements as first-class, test-linked contract (2026-10-07, the author's ruling)

THE RULING: "Regarding the many bugs we have hit with this protocol. I would call it v5.x. Will requirements engineering help? So tests are not only tied to code but also to requirements?" Yes - the lightweight kind. The bug taxonomy from addenda 52-58 splits into three classes: requirement-code drift (the 5/5 arc/vt gates - the ruling lived only in an old addendum and the refactor re-invented it; the ladder break - addendum 11's STOP semantics surviving verbatim into v4.x), unstated state invariants (the orphaned fst - "every measured cell lands in the state file" was implicit; volatile verdicts - "a verdict survives a restart" was never written), and plain code bugs (the name-vs-repo sort). Classes 1-2 are exactly what RE addresses; class 3 is what the existing toolbox covers.

THE DESIGN (all four pieces shipped):
1. docs/protocol.md gains a Requirements section (v5.0): nine numbered, testable statements R-01..R-09, each citing its provenance addendum - R-01 cells persist (55), R-02 verdicts persist per rung (57), R-03 gate = bar via TASK_PASS_BARS (52-54), R-04 everyone climbs (56), R-05 arc rung-independent, measured once at ARC_RUN_CTX (the design verified live on 2026-10-07 after the author's "16k arc doesn't make sense" challenge - the 16k/32k arc tallies are LOADED records, the fresh measurements live at rung 4,096), R-06 window-below-rung families never evaluate (45, 58), R-07 param-ascending order resolves names and repos (57), R-08 speed-dead ends the climb (13), R-09 single-sourced constants (the standing governance rule).
2. Pinning markers: every requirement has at least one test carrying `Pins: R-xx` in its docstring; the addendum-52/54/55/56/57/58 regression tests were retrofitted (10 markers across test_verdict_path.py, test_speed_gate.py), and two new pins landed: test_param_sort_resolves_family_names_identically (R-07's name-carried shape, unpinned until now) and test_registered_constants_single_source (R-09, source-level: no consumer module redefines TASK_PASS_BARS).
3. requirements_check.py: the traceability gate - fails if a requirement has no pin, or a pin references a nonexistent requirement (the RE staleness failure mode, closed). Runs EVERY COMMIT (the author's ruling: "3 should be checked in every commit") via .pre-commit-config.yaml's requirements-check hook; also runnable standalone.
4. Governance: adding or changing a requirement is a protocol change requiring a notebook addendum - that is what makes "v5.0" a version, not a rename.

THE LIMIT, ON RECORD: RE prevents ruling-loss in refactors (the arc-gate and ladder-break class); it does not prevent novel code bugs (the wrong-model-first sort was caught by the author's eye). The arc question that opened this was the proof of value: 30 minutes of archaeology that a pin would have answered in seconds.

197 tests. requirements_check: 9 requirements, all pinned.

### Addendum 60 - every log lives in the results tree: models/<family> is weights-only (2026-10-07, the author's ruling)

THE CATCH: deleting the infeasible families' model directories (the disk-recovery ruling) took the arc cell logs with them - the arc log was written next to the gguf (os.path.dirname(model)), so rm -rf models/<family> destroyed diagnostics. The author's ruling: "Put every log in tournament results, so deleting a directory in models affects only data that can be easily regenerated."

THE FIX (three writers moved; the fwe/vt cells already lived in the results tree):
1. speed_gate.bench_model gains log_dir (default: the model's own dir, so every existing caller keeps working); the server log becomes <log_dir>/<model>.server.log.
2. bench/cells.speed_pass and speed_cell pass results_dir as log_dir, and their _banner_window reads move to the results-tree path - the window cap check rides the same log it always did, just in a different directory.
3. bench/state_store.arc_pass gains results_dir (same default); _task_measure passes it through. The arc log becomes <results_dir>/<model>.arc-cell{run}.log.
4. full_benchmark.git_tail's artifact globs: the tournament-results recursive glob (already present) picks up the new locations; the old models/*/ globs stay for the pre-60 logs already committed, and go stale naturally as model dirs get deleted.

The layout after: models/<family>/ holds the gguf (and the pre-60 logs until their dirs are deleted); models/tournament-results/<family>/ holds EVERYTHING a cell run produces - per-turn dumps, csv, per-cell server logs, arc cell logs, mem sidecars. Deleting a models/<family> directory now touches only the weights; every verdict is in the state file and every log is in the results tree.

Test: test_cell_logs_live_in_the_results_tree (a faked launch per task writes its log under tournament-results, nothing lands next to the model). 198 tests.

### Addendum 61 - the window tax: ctx = depth, the headroom is paid from the content (2026-10-07, the author's ruling)

THE CATCH: "The way we are setting context is affecting good model candidates. We are setting the context a bit higher than the clean power of 2 number for context. That's potentially disqualified some good models." Exact - the rung at depth D launched at ctx = D + 2x128 (ANSWER_HEADROOM), so a model whose trained window equals D (the power-of-two coincidence: windows and rungs share the same grid) had its -c silently capped, the addendum-130e guard fired, and the family went infeasible AT ITS OWN NOMINAL RUNG. The live casualties: Qwen2.5-1.5B-Instruct and gemma-3-1b-it (both 32,768-window, both killed at the 32,768 rung by 256 tokens of arithmetic, not by measurement). The registry pre-flight enforced the same rule, so the disqualification was pre-download too.

THE RULING (the author chose option A of the three presented): the rung at depth D requires window >= D - EXACTLY. The headroom does not disappear (a model must have room to answer inside its window); it moves from the QUALIFICATION side to the MEASUREMENT side: ctx = D, and every task's content budget pays for the answer room out of the measured depth - fwe/vt already budget depth - ANSWER_HEADROOM inside ruler_gate (the haystack leaves the query tail room), and the speed cell's depth_budget reserves DEPTH_HEADROOM (645) + noise + answer room out of ctx. The rung's depth label becomes nominal by those same tokens - the price of not disqualifying the window==rung tier.

THE CHANGES: every depth + 2*ANSWER_HEADROOM in the launch path becomes depth (both certify controllers' task launches, _task_measure, the pre-flight threshold and its reason string, and ruler_gate's standalone CLI wanted_ctx/guard); bench/cells fwe/vt internal depth = rung (the csv label now equals the rung - the -2xheadroom offset is gone); the unused ruler_gate imports fall away.

THE MIGRATION: the state's two window==rung casualties (Qwen2.5-1.5B-Instruct, gemma-3-1b-it) have their infeasible record and 32,768 verdict CLEARED - they get their 32,768 rung measured under the new rule; the medalist's final record (2sigma at 4k/8k/16k, ceiling 32k pending its own measurement) is decided by measurement, not by 256 tokens. The other infeasible families (window strictly below every rung) are untouched - their disqualification holds under both rules.

Test: test_window_equal_to_rung_is_a_candidate (a 4,096-window family at the 4,096 rung is acquired and measured, never pre-declared infeasible; the pre-flight stays silent). R-06 re-worded: the requirement is window >= rung DEPTH, ctx = depth. 199 tests.

### Addendum 61b - the 4k-window trio revived (2026-10-07, the author's ruling)

THE RULING: "Can we revive the 4k window candidates the same way?" Yes - same disease, same cure. The 4,096-window trio (MiniCPM-1B-sft-bf16, MiniCPM-2B-sft-bf16, Phi-3-mini-4k-instruct) was disqualified at the FIRST rung by the old ctx = depth + 256 rule: 4,096 < 4,352. Under addendum 61 (window >= depth, ctx = depth) they are candidates at the 4,096 rung. All three state records cleared (infeasible = None, no stored verdicts - they went out before any cell was measured, so the re-entry is clean: nothing to re-derive, they measure from scratch).

phi-1 STAYS OUT: trained window 2,048 is strictly below the first rung under both the old and the new rule - its disqualification is a measurement of the world, not of the rule. The roster's sub-4k-window class has no rung to run; that is the study's floor, unchanged.

Migration class closed: every family whose infeasible record was window == depth is revived; the surviving infeasible set is exactly the strictly-below families (phi-1 alone at present). The addendum-45 machinery catches anything the registry missed at runtime, unchanged.

### Addendum 61c - the 4,096 rung re-opened (2026-10-07, the author's ruling)

THE RULING: "Yes. Then I will update the benchmark and restart." The rung's answered state derives entirely from the stored verdicts (addendum 57: a stored accept ANSWERS its rung) - so reviving the 4,096-window trio (61b) required re-opening the 4,096 rung, else the trio would be skipped there ("rung already answered") and, their window being 4k, go infeasible at the very next rung - never measured at all.

THE MIGRATION: Qwen2.5-1.5B-Instruct's stored 4096 accept verdict is REMOVED (the 8,192 and 16,384 accepts stand). The medal is untouched - it is computed from the stored cells (14 at 4,096 across speed/fwe/vt + 14 arc), which remain; only the rung-answering verdict is gone. On the restart the 4,096 rung measures: the revived trio (from scratch - they have no cells), every quality-dead family whose stored 4096 verdict was "dead" STILL SKIPS (their kills were measured - addendum 57's stored-dead skip is per family, not per rung), and the medalist itself re-derives its 4,096 accept free from the store (cells load, verdict re-stamps - the never-re-measure promise holds).

Note the asymmetry, on record: re-opening a rung costs nothing for stored-dead families (their skip is their own verdict, not the rung's) and nothing for accept families (their cells re-answer); it only re-admits families with NO stored verdict at that depth - exactly the revived trio.

### Addendum 62 - the answered rung must still measure its terminal families (2026-10-07, the author's catch)

THE CATCH: "check the results it did not work." The 61b/61c revival did not bite: the restart's first 4,096 pass re-derived the medalist's accept (free, from the store) - which ANSWERED the rung - and the revived trio was then SKIPPED with "rung already answered", never measured. Two compounding causes: (1) the answered-rung skip (addendum 57) is unconditional, and for a 4k-window family the 4,096 rung is TERMINAL - there is no deeper rung to climb to, so the skip means never measuring it at all; (2) the param sort still placed the sft pair after the medalist anyway, because the parked name-mismatch lived on: the state carries "MiniCPM-1B-sft-bf16", the roster's repo basename IS "MiniCPM-1B-sft-bf16" but _registry_params only matched the full repo string or the roster NAME - so both sft families resolved params None and sorted "unknowns last".

THE FIX (two parts):
1. The answered-rung skip now checks the terminal case (both controllers): a family with NO stored verdict at this depth, NO cells anywhere, and registry window <= depth is MEASURED anyway, with the printed reason "rung answered, but <fam>'s window (N) makes this its terminal rung - measuring it (addendum 62)". Families that CAN climb (window > depth) or have already been evaluated (stored verdict or cells) still skip - the skip's economics are untouched.
2. _registry_params resolves the repo BASENAME too (and strips the -bf16/-f16/-f32/-instruct suffix aliases): "MiniCPM-1B-sft-bf16" now resolves to 1.3603B via the repo openbmb/MiniCPM-1B-sft-bf16, and the sft pair sorts param-ascending with everyone else. The parked registry/state name-mismatch issue (addendum 57's note) is closed for the suffix class.

Tests: test_answered_rung_still_measures_the_terminal_family (a stored-accept champion answers the rung; a never-evaluated 4,096-window family measures anyway, the skip line never fires for it). 200 tests.

### Addendum 63 - a state-carried family name is not a hub repo (2026-10-07, the author's crash report)

THE CATCH: "crash." The restart with addendum 62 went down in flames: `huggingface_hub.errors.RepositoryNotFoundError: 404 ... https://huggingface.co/api/models/MiniCPM-1B-sft-bf16/tree/main` - the traceback runs through certify_rung_combined -> _acquire_missing_model(spec, ...) -> list_repo_files(model_repo). The state carries the family NAME "MiniCPM-1B-sft-bf16" (no stored spec - the family predates spec storage), and resolve_families used `(fst or {}).get("spec") or fam`, so the NAME went to the hub as a repo and the hub 404'd. The addendum-62 fix resolved names for the param SORT; the spec itself still went out raw.

THE FIX: `_resolve_spec_repo(spec)` in full_benchmark.py - a name-only spec resolves to its roster REPO before it ever reaches the hub. It matches the repo string, its basename, or the roster name; the addendum-62 suffix alias class (-bf16/-f16/-f32/-instruct) applies to specs too. Repos with a variant ("=" present) pass through unchanged; unknown names return None (no guess - same stance as the param sort). resolve_families maps every saved spec through it: `[_resolve_spec_repo(s) or s for s in saved if s]`.

Verified: "MiniCPM-1B-sft-bf16" -> openbmb/MiniCPM-1B-sft-bf16, "MiniCPM-2B-sft-bf16" -> openbmb/MiniCPM-2B-sft-bf16, and the parked mismatch "RWKV7-World-2.9B" -> RWKV/RWKV7-Goose-World3-2.9B-HF. The remaining unresolved names should be none - a None here means a genuinely unknown family.

Test: test_state_names_resolve_to_repos_before_the_hub (the trio names, the RWKV mismatch, repo passthrough, unknown -> None). 201 tests.


### Addendum 64 - the session split, and the day's failures become requirements (2026-10-07, the author's request)

THE SESSION: "I forgot to start the session today." The day's first work landed at 07:42 (addendum 59, protocol v5.0) but sat in session 40 (opened 2026-10-06) - the same drift the session-39 audit fixed for session 38's tail. Per the one-session-per-day rule, addenda 58-63 moved verbatim to this session (41), and session 40 closes with a pointer.

THE REQUIREMENTS: "from the failures today due to requirements, make sure there is a requirement for them." Audited against the day's bug taxonomy: three failures were requirement gaps, not covered by R-01..R-09 - (1) the deleted model dirs took the arc cell logs with them (addendum 60), (2) the answered-rung skip permanently barred the revived 4k-window trio (addendum 62), (3) the state-carried family name went to the hub as a repo and 404'd (addendum 63). Each becomes a numbered, testable statement; each regression test re-pins to it:

- R-10: every cell artifact lives in the results tree; models/<family>/ is weights-only. Pin: test_cell_logs_live_in_the_results_tree.
- R-11: an answered rung still measures a never-evaluated terminal-window family. Pin: test_answered_rung_still_measures_the_terminal_family.
- R-12: a name-only spec resolves to its roster repo before any hub access; unknown names never reach the hub. Pin: test_state_names_resolve_to_repos_before_the_hub.

The addendum-61 window-tax fix needed no new requirement: R-06 already carries ctx = depth (re-worded in addendum 61). The traceability gate (requirements_check.py) enforces the new pins on every commit, as ruled.
