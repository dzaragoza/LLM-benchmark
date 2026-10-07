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

### Addendum 65 - live update: the page's history must never overrule the state (2026-10-07, the author's live update)

THE CATCH: the live refresh showed the medalist as "out of the benchmark" and the revived trio as out or dead - wrong on both counts. The page's classification read results.txt's HISTORICAL verdict lines: the medalist's superseded 32k infeasible (cleared by addendum 61) and the trio's pre-61 DEAD/INFEASIBLE lines (measured at the inflated ctx, cleared by 61/61b) were the most recent lines, so they won.

THE FIX (three authorities, in order - the state leads, the window decides, the marker revives):
1. STORED VERDICTS LEAD: a family with state verdicts renders from the store (the medalist: "accept", its stored 4096/8192/16384 accepts; a superseded INFEASIBLE line can no longer overrule them).
2. THE WINDOW DECIDES OUT-OF-BENCHMARK (R-06's own rule): disqualified_families checks every family against its trained window - state record's window_cap, else the registry store via the addendum-63 alias class, else the historical line - and disqualifies ONLY on window < first rung. The trio (4,096 == first rung) is in; phi-1, phi-2, RWKV7-Goose (2,048) stay out; the count went 8 -> 3.
3. THE REVIVAL MARKER: the 61/61b migration left the trio an explicit "infeasible": null - the migration's fingerprint. A family carrying it renders "climbing" (history never classifies it); a pre-verdict-storage family (granite-3.0-2b-instruct) keeps its measured history.

NOTE FOR THE RUN (the author's call): granite-3.0-2b-instruct's registry window IS 4,096 and its old speed kill was measured at ctx 4,352 - ABOVE its trained window. It has no stored verdict, so on the restart it re-measures from scratch at ctx 4,096 (the addendum-62 terminal rule); its "dead @ 4,096" row is its measured history until then. Same shape as the trio's, but without the revival marker - if the re-measure accepts it, the state will say so.

Test: test_revived_families_never_show_superseded_verdicts (revival marker -> climbing; no marker, no verdicts -> history stands; stored verdicts lead over superseded lines). 202 tests.

### Addendum 66 - the sft pair climbed above their window; phi-2 was "terminal-measured" below it (2026-10-07, the author's status check)

THE CATCH: the restart's fresh results showed MiniCPM-1B-sft-bf16 DEAD at 8,192/16,384/32,768 - a 4,096-window family evaluated three rungs above its ceiling - and phi-2 (window 2,048) "terminal-measured" at 4,096 per addendum 62. Two bugs, both in my addendum-62/61 machinery:

1. _registry_window did not resolve the state names: the store is keyed by roster name (MiniCPM-1B-sft), the state carries the repo basename (MiniCPM-1B-sft-bf16) - the addendum-63 alias class, but only the spec resolver had it. The pre-flight read None, stayed silent, and the family climbed; its arc cells load rung-independently, so the deaths needed no launch and nothing caught them.

2. The addendum-62 terminal condition used _w <= depth - window <= rung - which is also true when the window is BELOW the rung (phi-2, 2,048 at 4,096): a sub-rung family is R-06 infeasible, never a terminal measurement.

THE FIX: (1) _registry_window resolves the alias class (repo/base/roster-name + quant-suffix aliases), same as _resolve_spec_repo; (2) the terminal condition is _w >= depth in BOTH controllers - the family's window must REACH the rung. A sub-rung family at an answered rung falls through to the pre-flight, which declares it infeasible with zero hub touches.

THE MIGRATION: MiniCPM-1B-sft-bf16's above-window dead verdicts (8,192/16,384/32,768) cleared - its measured 4,096 arc death (2/8 cells) stands. MiniCPM-2B-sft-bf16 has no verdicts; it measures at 4,096 on the next restart via the terminal rule. phi-2 keeps its infeasible record (2,048 < 4,096, correctly out).

THE CLIMB NOTE: the fresh run itself is healthy - gemma-3-1b-it died to vt at 32,768 (0/6, its 4k/8k/16k deads stand as stored quality verdicts), the medalist's 32k measurement is queued, granite-3.0-2b-instruct was re-measured at 4,096 per the terminal rule.

Test: test_terminal_rung_never_measures_below_the_rung (the alias-resolved windows; the >= depth condition). 203 tests.

### Addendum 67 - the terminal condition was inverted: climbing families re-measured at answered rungs (2026-10-07, the author's restart catch)

THE CATCH: "I restarted with the latest version and it is re-measuring Qwen instead of the revived family." The fresh run "terminal-measured" Qwen3.5-2B (window 262,144!) at the answered 4,096 rung - my addendum-66 correction overrotated: _w <= depth (below-rung families measured) became _w >= depth (EVERY family that can run the rung measured, climbers included). Qwen3.5-2B can climb, so the answered rung must skip it; MiniCPM-2B-sft-bf16 (the actually-terminal family, window 4,096) never got its turn.

THE FIX: TERMINAL = can run THIS rung but cannot reach the NEXT one: depth <= window < next TOURNAMENT_DEPTHS entry. Below the rung: R-06 infeasible (pre-flight). Window >= the next rung: it climbs, the answered rung skips it. The both-controllers blocks now compute _next from TOURNAMENT_DEPTHS and use the three-way condition.

THE CONTEXT QUESTION ("something wrong with the context calculation"): checked - CORRECT, and it is addendum 61 visible at the 4k rung for the first time. The old first-pass 4k cells launched at ctx 4,352 (depth + 256); the fresh ones launch at exactly 4,096 (ctx = depth), so the speed blob shrank 2,825 -> 2,575 tokens. The budget math checks exactly: 4,096 - 64 (DEPTH_HEADROOM) - 224 (noise reserve) - 1,233 (conversation side: 4 user turns + 4x299 answer cap) = 2,575. The deepest turn still lands at the 4,096 reference depth - the headroom is paid from the content, per the ruling.

THE STATE: Qwen3.5-2B's two fresh 4,096 cells (speed PASS, fwe PASS, vt 4/5 FAIL, arc 5/5 PASS x2) are valid measurements - kept; its verdicts remain unstored, so the answered-rung skip correctly skips it on the next restart and it climbs. No migration needed.

Test: test_terminal_rung_never_measures_below_the_rung updated to pin the three-way condition (phi-2 below, the trio terminal, Qwen3.5-2B climbs). 203 tests.

### Addendum 68 - the arc bar recalibrated to 3/5 (2026-10-07, the author's ruling)

THE RULING: "I think arc is too hard... Yes let's go 3/5. It's fair." The evidence: the stored f16 arc cells (324) graded 36% at the 4/5 bar - well below the author's >= 50% pass-rate floor (the difficulty basis, session 38). At 3/5 the same evidence grades 52%, on target. The distribution: 0/5 8%, 1/5 12%, 2/5 28%, 3/5 16%, 4/5 16%, 5/5 16% - the bar sits exactly at the distribution's middle.

THE CHANGE: TASK_PASS_BARS["arc"] = 3 (bench/constants.py, R-03's single source). Protocol row updated. The three 4/5-encoded tests updated (the stored re-grade pair, the fresh-cell gate, the constants pin).

THE MIGRATION (per the protocol's promise - records re-grade free): every stored arc-caused dead verdict re-derived against its stored arc cells at the new bar, using the certify math (2-sigma Wilson lower bound >= 0.50, floor 10). Result: granite-4.0-h-1b REVIVED at all four rungs (29/30 arc cells at 3/5, lower bound 0.829 - its arc deaths were an artifact of the too-hard bar; it now re-enters and climbs). The other arc-dead families stay dead on their own evidence (their cells cannot reach the bar even at 3/5: the granite 350ms 0/12, MiniCPM4 1/14, Qwen3.5-0.8B 11/28, Llama-3.2 6/16, MiniCPM-1B-sft 5/16). Families whose stored deads were vt/fwe/speed-caused are untouched - this migration touches only arc-caused verdicts.

NOTE: rungs do not re-open wholesale - only granite-4.0-h-1b's verdicts cleared, so on the restart it measures at 4,096 (no stored verdict) while the answered-rung skip holds for everyone else. 203 tests.

### Addendum 69 - the majority bar: ceil(k/2)/k is the difficulty principle (2026-10-07, the author's ruling)

THE RULING: "Ceiling(k/2)/k seems like a sweet spot for difficulty - let's see if the tests difficulty agrees going forward." The bar for a k-item gate is the SMALLEST MAJORITY: ceil(k/2) of k. A pass means "right more often than not" - the natural difficulty anchor for a binomial gate, and it sits at the distribution's center rather than its tail.

THE AGREEMENT CHECK (current bars vs the rule):
- fwe: 2/3 = ceil(3/2). AGREES - calibrated session 38.
- arc: 3/5 = ceil(5/2). AGREES - addendum 68's recalibration landed exactly on the rule, empirically (36% -> 52%, on the >= 50% floor).
- vt: 4/5 - ONE NOTCH ABOVE the rule (ceil(5/2) = 3). vt is also the most lethal quality gate (53% cell fail rate, the biggest near-miss pile: the 4/5 patterns). This is the one bar to watch going forward - if vt keeps concentrating the kills, the rule says 3/5 is its calibration.
- speed: 0 stalls - not a k-of-k gate (a strict screen, the author's ruling), the rule does not apply.

GOVERNANCE: the rule is the DEFAULT for any future gate or recalibration; departing from it (as vt currently does) requires its own evidence and addendum. No change made now - the author's call is to observe.

## Addendum 70 - the exclusive gold

The author's ruling: gold is EXCLUSIVE per rung. Among the families
ACCEPTED (2-sigma) at a rung, only the one with the FEWEST parameters
is gold; every other accept keeps its confidence tier (0.5/1/2 sigma)
but is not the rung's gold. Parameter counts come from the registry
store (addendum 29 - never guessed); an accepted family without a
count can never win gold (the registry check flags it). No accepts ->
no gold.

`gold_per_rung(state, depth)` in bench/certify.py, with the
addendum-63/66 alias class in the params lookup (`_registry_params`).
Protocol R-13, pinned by
test_gold_per_rung_is_the_fewest_parameter_accept. 204 tests.

Effect on today's standings (live state): 4k gold moves from
Qwen2.5-1.5B-Instruct (1.5B) to granite-4.0-h-1b (the 1.0B accept);
8k/16k gold stays Qwen2.5-1.5B-Instruct (sole accept); 32k no gold.

## Addendum 71 - the calibration window

The author's rationale: evaluating beyond the gold medal is a
consequence of the difficulty changes - under the correct difficulty
the first gold IS the fewest-parameter model. Pass/kill calibration
therefore counts only the cells of each rung UP TO the gold medal:
families in param-ascending order, stopping after the gold winner (the
fewest-parameter accept, addendum 70). Post-gold measurements
(revivals, terminal-rung runs) never enter the stats. No gold at a
rung -> every measured family counts. ARC is the special case
(rung-independent, loaded at first launch): its cells count only up
to the LARGEST-parameter family with any speed/fwe/vt cell - a family
whose arc ran but that was never launched never enters.

`kill_rate_cells(state, depth)` + `arc_kill_rate_cells(state)` in
bench/certify.py. Protocol R-14, pinned by
test_kill_rate_window_stops_at_gold. 205 tests.

## Addendum 72 - the gold panel on the picker pages; the live page retires

The author's ruling: "every time a new gold medal is achieved, update
the picker web pages. Remove the live status page." The pickers now
carry a GOLD MEDALS section - one row per tournament rung with the
exclusive gold winner (addendum 70) and its param count, "-" where no
gold stands. picker_medals.py rewrites the delimited GOLD_MEDALS block
in cpu-picker.html and gpu-picker.html (idempotent; the pages stay
hand-authored except that one generated block); verdict_commit runs it
on every accept, so a new gold lands on the pages with the verdict's
own commit-and-push. live_status.html, run_status.py and
tests/test_run_status.py are removed - live updates are conversational
(addendum 67-era ruling). Protocol R-15, pinned by
test_picker_medals_panel; js_check guards the pages' boot. 200 tests.

## Addendum 73 - the site shape: md/ for the documents, docs/ for the web

The author's ruling: "create a directory md and put every md file in
there. Keep readme in the root. Then we use docs for the new picker."
GitHub Pages only offers root or /docs as the publishing source, so
the shape is now: md/ holds every study document (protocol.md, wow.md,
models.md, model-selection.md, practitioner-goals.md, the legacy
notebook.md and the conversation archives), README.md stays in the
root, and docs/ is the PAGES SITE: index.md (the results dashboard -
gold per rung, gate kill rates, verdict counts) plus the two picker
pages. All path references moved with the files:
requirements_check.py (md/protocol.md), etc/registry_data.py's models
check (md/models.md), js_check/picker_medals page lists
(docs/*.html), README links, .pre-commit-config.yaml's requirements
hook scope, and js_check's temp-file name (page paths now carry a
slash - basename only). js_check boots both pages at their new paths.
To publish: Settings -> Pages -> source main /docs - then
dzaragoza.github.io/LLM-benchmark/ serves index.md as the homepage,
the pickers at /cpu-picker and /gpu-picker.

## Addendum 74 - the static practitioner page; the HTML pickers retire

The author's ruling: "Remove the html. Let's make the page static in MD
with minimal information needed to choose a model." docs/index.md is
now the whole site: one table, deepest-first, with per gold rung the
winner, its measured whole-stack RAM (the same number serves the
CPU/iGPU and VRAM columns - the cost is the model's, not the host's),
and the minimum bandwidth for the 5 w/s reader line (the linear law:
102.4 x 5 / worst-turn t/s - 24.3 GB/s for the deepest winner), plus
the common DDR configurations that clear that minimum. The HTML
pickers, js_check.py, picker_medals.py and the js-check pre-commit
hook are removed; R-15 rewritten for the static page (pinned by
test_gold_per_rung_is_the_fewest_parameter_accept_docstring). The
page's numbers today: 16k Qwen2.5-1.5B-Instruct 3.6 GiB / 24.3 GB/s
(21.1 t/s), 8k Qwen2.5-1.5B-Instruct 3.4 GiB / 22.9 GB/s (22.4 t/s),
4k granite-4.0-h-1b 4.2 GiB / 22.5 GB/s (22.8 t/s). 200 tests.

## Addendum 75 - the page trims: integer RAM, no VRAM column

The author's ruling: "Round RAM up to int. Remove the gpu vram column
for the moment." The chooser table's Min RAM is now the measured
whole-stack cost rounded UP to the next whole GiB (16k/8k
Qwen2.5-1.5B-Instruct: 4 GiB; 4k granite-4.0-h-1b: 5 GiB) and the VRAM
column is gone - the GPU note keeps only that VRAM capacity is the
constraint; a GPU column returns when GPU-side measurements exist.

## Addendum 76 - the page goes per-model; the granite memory question

The author's rulings: one section per model (optimum settings, the
quant explained, the bandwidth configurations that clear the minimum),
drop the CPU reference (the study serves from the iGPU - system RAM),
and two questions. (1) Which parts of the llama memory report are GPU:
on the iGPU ALL of them - weights, KV context and compute buffers live
in system RAM (the GPU shares machine memory), which is exactly why
the MemAvailable-delta machine cost IS the right serving number; the
page now says so. (2) Is granite's memory correct? Yes - verified:
granite-4.0-h-1b f16 weighs 3.01 GiB vs Qwen's 3.31 GiB, but its
MEASURED machine cost runs ~0.8 GiB higher (4.2-4.4 vs 3.4-3.6 GiB)
across every rung - the weights are smaller, the hybrid-attention
runtime overhead is larger; the measurement stands and the page notes
it. Structure: Qwen2.5-1.5B-Instruct first (deepest, 16k gold),
granite-4.0-h-1b second (fewest params, 4k gold); the shared DDR table
follows.

## Addendum 77 - the UMA correction

The author's correction: "there is no separate GPU pool to account
for" is WRONG - the machine's system-RAM measurements show part of the
serving footprint resides in the UMA region the BIOS reserves for the
iGPU, memory the OS never allocates and MemAvailable never sees. The
page's memory note now states the measured machine cost is a LOWER
BOUND and the practitioner should budget the UMA carve-out (typically
512 MiB-2 GiB in BIOS settings) on top. This also sharpens the standing
question for the memory sidecar work: attribute the UMA-resident share
(llama-server's Vulkan backend reports its allocations; a future
sidecar can split the footprint into OS-visible vs UMA-resident).

## Addendum 78 - the memory authority is llama's own breakdown

The author's correction: the page's memory numbers come from
llama-server's MEMORY (llama) breakdown (weights + context + compute),
NOT the MemAvailable-delta machine cost. Rewritten accordingly - and
this resolves the addendum-76 granite paradox: under the llama
breakdown granite-4.0-h-1b @4k is weights 3.01 + context 0.09 +
compute 0.06 = 3.15 GiB (4 GiB rounded), SMALLER than Qwen
(3.85 GiB @16k, 4 GiB rounded) exactly as its smaller weights predict.
The ~0.8 GiB gap in the machine-cost numbers was the MemAvailable
delta's artifact (the UMA-resident share the OS counter cannot see),
not a granite runtime overhead - the addendum-76 note is superseded.
The UMA budgeting note stays (the carve-out rides on top of whatever
the breakdown totals).

## Addendum 79 - the device split from llama's own table; MemAvailable machinery finally deleted

The author asked why MemAvailable was still in use ("we deprecated it
many sessions ago") - honest answer: the deprecation was ruled but the
machinery was never removed; bench/cells.py (4 sites) and speed_gate.py
(2 sites) still took the reading and printed "machine cost ... GiB
(MemAvailable delta)" on every cell, which is why the number was in
front of me when the page was written. Now finished: every
system_memavailable_gib/memory_cost_gib call site deleted, the two
helpers removed from infra/llama_server.py, the "machine cost" log
line gone. The memory authority is memory_breakdown_gib - and it
already parses the per-DEVICE rows: the verbose log's
`memory breakdown [MiB]` table lists Vulkan0 (the iGPU - on this APU,
the UMA region: Qwen @16k 3.4 GiB = 2.88 w + 0.44 ctx + 0.07 comp;
granite @4k 2.9 GiB = 2.72 w + 0.09 ctx + 0.05 comp) and Host (plain
system RAM: 0.46 / 0.30 GiB). The page now shows the GPU(UMA) vs
system-RAM split per model and states the real constraint: the UMA
carve-out must be at least the Vulkan0 share or the model cannot
launch.

## Addendum 80 - the practitioner page, minimal

The author's ruling: far too much information for the practitioner.
The page is now: a two-sentence intro (pick the largest context size
that fits your machine; context size = how long a document the model
tracks reliably) and one section per certified context size, each
listing exactly: model + configuration, needed bandwidth with the
minimum single/dual/quad-channel systems that meet it, RAM for iGPU,
VRAM for a dedicated GPU. No methodology, no measurement notes, no
gates - the target audience wants the result, not the why. All the
removed detail lives in the protocol and this notebook. The RAM and
VRAM numbers are the rounded llama-breakdown totals (addendum 79's
device split sums to the same footprint whether it lands in UMA or a
dedicated card's VRAM).

## Addendum 81 - the page: the iGPU/dGPU split made visible, K/V quants, example commands

The author's rulings: (1) the GPU must read as OPTIONAL, very
visible - a blockquote at the top splits the two machine kinds:
system RAM + iGPU (use the RAM number) vs VRAM + dedicated GPU (use
the VRAM number), with "a dedicated GPU is optional" stated plainly;
each section's rows now read "System RAM needed (iGPU)" and "VRAM
needed (dedicated GPU, optional)". (2) The configuration line details
the K and V cache quants (f16 K, f16 V - the tournament's (f16,f16,f16)
variant, weights/K/V). (3) Each section carries an example llama-server
command line matching the exact configuration the benchmark measured:
-m <gguf> -c <depth> --cache-type-k f16 --cache-type-v f16 -fa on
--parallel 1 (the -fa/--parallel flags mirror the benchmark's own
launch flags for the f16 K/V variant).

## Addendum 82 - the bandwidth remark

The author's ruling: state that ANY dedicated GPU meets the bandwidth
requirement - the BW consideration is only for integrated GPUs. The
blockquote gains the remark, and each section's row retitled
"Memory bandwidth needed (iGPU only)".

## Addendum 83 - the bandwidth recommendations, exact matches only

The author's ruling: pick the LOWEST configuration that matches the
requirement, and list only the other channel configurations that
match that same bandwidth EXACTLY; if they don't match, don't list
them. 16k (25 GB/s): lowest is DDR4-3200 single channel = 25.6 GB/s,
and its only exact equal is DDR4-1600 dual (25.6); both listed, DDR5
and faster dropped (they exceed, not match). 8k and 4k (23 GB/s):
lowest is DDR4-2933 single channel = 23.5 GB/s, no other standard
configuration matches it exactly - listed alone. The "or faster"
wording and the generic channel-count list are gone.

## Addendum 84 - the layout: model + configuration, pick-one GPU note

The author's ruling: rename "Example" to "llama.cpp command line";
each entry laid out as model, configuration, then a very visible
"Pick ONE - you do not need both" block: the integrated-gpu entry
(system bandwidth with the exact-match minimum, minimum RAM) and the
dedicated-gpu entry (minimum VRAM, any GPU has high enough BW). The
most common reader complaint will be "do I need both?" - the intro
and every section state it: ONE, never both. Also caught while
rewriting: the command lines carried comma-formatted -c values
(16384, not 16,384) - fixed; and a first draft broke the nested
markdown lists (md_check + inspection caught it).

## Addendum 85 - the 32k section; kill rates join the update format

Qwen3-1.7B's 32k gold lands on the page: model + config, iGPU
bandwidth 55 GB/s (worst turn 9.4 t/s at 102.4; the lowest exact match
DDR5-7200 single channel, 57.6 GB/s - nothing slower meets it, the
linear law is now biting: deep context needs fast memory), 8 GiB
RAM/VRAM (Vulkan0 6,941 MiB + Host 633 MiB = 7.4 GiB rounded up),
command line at -c 32768. The update format gains a standing element:
every update now reports the per-gate per-cell pass/kill percentages
under the calibration window (addendum 71).

## Addendum 86 - the no-gold rungs count their dead; my 64k miscount corrected

The author's ruling: kills in a rung WITHOUT a gold medal count by
models declared dead - the param-ascending order guarantees the gold
will land on a HIGHER-parameter model (the R-14 window already encodes
this: no accept -> every measured family counts). My previous update
WRONGLY excluded the 64k cells ("they'll count once someone accepts")
- Qwen3.5-0.8B's 64k cells were always in the window; my totals missed
them. Corrected overall per-cell rates under the calibration window:
speed 196 cells 96.4/3.6, fwe 196 61.7/38.3, vt 195 62.6/37.4, arc 171
72.5/27.5 - the 64k cells were in fact included there (the helper
walks all rungs); the per-rung breakdown now shows 64k explicitly:
speed 6 cells 100% pass, fwe 6 83.3%, vt 6 83.3% - Qwen3.5-0.8B's
speed/fwe cells PASSED at 64k; only vt killed it (0/6, all 4/5
near-misses). Updates will report per-rung tables when a rung is
settled, and the no-gold rungs' dead always count.

## Addendum 87 - the exact-match bandwidth pool, multi-channel entries included

The author challenged the page's minimum-BW selections: valid
configurations closer to the target were being ignored. Re-derived the
selections using the old cpu-picker's machine table (DDR3-800..2133
single/dual/quad; DDR4-1600..3200 and DDR5-3200..6400
single/dual/quad/octa; per-channel GB/s = MT/s x 8 / 1000). No closer
match exists at any rung - 57.6 (32k), 25.6 (16k), 23.5 (8k/4k) remain
the tightest fits - but the exact-equal sets were incomplete. Page now
lists every exact equal: 32k adds DDR5-3600 dual channel; 16k adds
DDR5-3200 single, DDR3-1600 dual, DDR3-800 quad alongside the existing
two. LPDDR deliberately excluded - same bandwidth as the DDR of the
same MT/s, adds noise for the reader. 8k/4k unchanged (DDR4-2933
single stands alone).
