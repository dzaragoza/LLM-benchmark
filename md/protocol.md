# protocol.md - The Constants Registry

Every number the study uses, with its provenance. The registry is the
single source of truth for the report: it appears in (or is referenced
by) the final paper, and no number enters the code without a row here.

Provenance categories:

- **[A] Author choice** - ruled by the study author, on record in the
  lab notebook with the ruling's rationale.
- **[P] Practical limit** - a wall of the world (hardware, tooling,
  safety margin), not a scientific claim; tuned, not derived.
- **[D] Derived** - computed from other registered constants, or
  measured by this study's own instruments.
- **[M] Magic** - inherited or assumed without derivation. Each row
  states its exit plan; a magic number that gains a derivation is
  re-registered as [D].

Governance rule (standing): a constant may appear in exactly one
place in the code (single-sourced); other files import it. Changing a
constant is a protocol change - it requires a notebook addendum, not
a silent edit.

---

## The anchor

The study has ONE anchor. Everything else derives from it or is
independent of it:

```
[A]  reader line 5.0 w/s  <-  300 wpm (Brysbaert 2019, silent English
                               non-fiction adults) / 60 s
```

Chain of derivation from the anchor:

```
5.0 w/s  --/w/t_min-->  t/s needed per model/rung  --law-->  size*(rung)
    |                                        (per-family w/t_min, [D])
```
The guarantee (protocol v3.1, addendum 73): **the reader stalls on
at most 5% of turns** - simulating the registered reader (5.0 w/s,
0.45 s reaction) on each turn's per-word arrival stream, a turn
stalls iff ANY word arrives after the reader is ready for it (the
addendum-30 collision simulation, exact form, unchanged per-turn).
The per-turn test is UNCHANGED and load-bearing in both instruments
that consume it; what changed across v3.x is only the aggregation
(addendum 140, registry catch-up):

- The LADDER still grades by the STALL RATE (speed_pass,
  bench/cells.py): PASS iff wall-failing turns / total turns <=
  0.05 - the author's distributional ruling ("a fast reader will
  only catch up to 5% of the turns"); early-fail is deleted (a rate
  verdict needs its denominator; the addendum-68 aborted run would
  have scored a false 1.1% PASS).
- The CERTIFY path (session 38, addendum 2) no longer uses the
  rate: a speed cell is ONE conversation of the 21-conversation
  corpus with a 0..k stall-count record (gold = 0 stalls), the
  exact FWE/VT cell shape. Everything protocol-v3.x (stall rate,
  n=50, threshold = reader_wps - 2*sigma budget) is RETIRED from
  the certification path; the per-turn binary event is not.

The old flat worst-turn w/s test stays a diagnostic - it manufactured
fails on tiny answers (the addendum-54 degeneracy: the span of a
5-token answer is pipeline overhead, not reading experience).

---

## Taxonomy - the study's model vocabulary (session 40, addendum 18)

Literature-compatible terms, each with the study's EXPLICIT
extension (what the word covers HERE - the literature sometimes uses
them wider or narrower; the ruling is what the study means):

| Term | The study means | Example | Literature note |
|---|---|---|---|
| release | one versioned generation of a vendor's model | Qwen3.5 (all sizes); Llama-3.2 (1B, 3B, 11B, 90B) | The literature says release / version / generation. The study previously used "lineage" informally; in the literature "lineage" means PROVENANCE (what a model derives from), so the study avoids it for the version axis. |
| family | the size range of ONE release - same version, different parameter counts | Qwen3.5-0.8B and Qwen3.5-2B are ONE family; Qwen3.5-2B and Qwen2.5-3B are NOT | The literature's "model family" is WIDER (sizes AND variants of one release, sometimes across releases); the study NARROWS it to the size axis of a single release. The state key (e.g. `Qwen3.5-0.8B`) names a family entry. |
| variant | one specific configuration: family x weights quant x KV quants (k, v) | Qwen3.5-2B (Q8_0, f16, f16); Qwen3.5-2B (Q4_K_M, q8_0, q4_0) | The literature says model instance / checkpoint / variant; the GGUF community says quant. The study's variant is the (family, rung, kv_k, kv_v) tuple - the unit that gets a model file, a server launch, and cells. |

Three levels, top to bottom: release > family > variant. The
benchmark's experimental unit is the variant; the certification
medals are per (family, rung) - the selected variant carries the
family's flag (the Q8_0-default rule; a family competes as one
variant per study, addendum 86).

THE MIGRATION NOTE: the CODE KEEPS "families" as its key name (the
state's `families` dict, `--families` CLI, `families` positional) -
the key matches the literature term and the study's extension of
it, so nothing renames. "Lineage" was never a code term (only old
study artifacts named lineage.json - the lineage STUDIES compared
releases); the artifacts were already moved to state/ in addendum
16 and need no further action.

## Requirements (v5.0 - the test-linked contract)

Protocol v5.0 (addendum 59): the study's rulings are first-class
REQUIREMENTS, and every requirement is pinned by at least one test.
A requirement is a testable statement of a ruling that lives
somewhere better than memory - each row cites its provenance
addendum, and each pinning test carries a `Pins: R-xx` docstring
marker. `python3 requirements_check.py` (every commit, via the
pre-commit hook) fails if a requirement has no pin, or a pin
references a requirement that does not exist - the traceability
that keeps the table from going stale. Adding or changing a
requirement is a protocol change: it requires a notebook addendum,
not a silent edit.

| Req | The requirement (testable statement) | Provenance |
|---|---|---|
| R-01 | A cell measured by a controller is present in the state file after save; a fresh family's cells persist, and a second pass measures nothing. | addendum 55 (the orphaned-fst bug) |
| R-02 | A verdict (accept / dead / infeasible) persists per (family, rung); a restart honors it - stored dead skips that family at that rung only, stored accept answers the rung. | addendum 57 |
| R-03 | Every grading predicate grades at `TASK_PASS_BARS` (bench/constants.py, the single source); no predicate hardcodes a bar. | addenda 52-54 (the 5/5 gate regression) |
| R-04 | An accept answers the rung and the ladder climbs: quality-dead families re-measure at deeper rungs; only infeasible and speed-dead are permanent outs. | addendum 56 ("everyone climbs") |
| R-05 | RETIRED (session 43): ARC and FWE are retired from the benchmark - v7 sharpened the focus to reach vs reasoning (the fixed corpus carries both axes); historical arc/fwe cells stay in state, no new ones are measured. The combined controller is speed + vt. | session 43 (the v7 focus ruling) |
| R-06 | A family whose trained window is below the rung's DEPTH is infeasible before any download, conversion or launch, and is skipped at every rung (pre-flight + runtime catch agree on the state record). The rung launches at ctx = depth - the answer headroom is paid from the measured content, not from the model's window (addendum 61) - so a window == rung model IS a candidate at its own rung. | addenda 45, 58, 61 |
| R-07 | Families evaluate in param-ascending order; the sort resolves both repo-carried and name-carried specs identically. | addendum 57 |
| R-08 | A speed-gate death at rung k ends that family's climb at every deeper rung (the speed gate only hardens with depth). | addendum 13, session 40 |
| R-09 | A study constant appears in exactly one place in the code; other files import it (the standing governance rule, now a requirement). | the registry's governance rule |
| R-10 | Every cell artifact (dumps, csv, server and arc cell logs, mem sidecars) lives in the results tree; `models/<family>/` is weights-only, so deleting a model directory loses only regenerable data. | addendum 60 (the deleted arc logs) |
| R-11 | An answered rung still measures a never-evaluated family whose trained window makes that rung its terminal one (no stored verdict at the depth, no cells anywhere, window <= depth) - the answered-rung skip never becomes a permanent bar. | addendum 62 (the revival that did not bite) |
| R-12 | A name-only spec (a state-carried family name with no stored spec) resolves to its roster repo before any hub access; an unknown name is never sent to the hub. | addendum 63 (the 404 crash) |

## [A] Author choices (ruled, on record)

| Constant | Value | Where | Ruling / derivation |
|---|---|---|---|
| Reader line (k=1 guarantee) | 5.0 w/s | `speed_gate.py` READER_WPS_DEFAULT | THE anchor. 5.0 w/s = 300 wpm / 60 (Brysbaert 2019 meta-analysis, silent reading, English non-fiction, adult mean). Single-sourced here; every other reader constant derives from it. |
| Stall-rate max (v3.1 guarantee) | 0.05 (5%) | `speed_gate.py` STALL_RATE_MAX | Author ruling (addendum 73): the guarantee is distributional - PASS iff at most 5% of turns have a catch-up event; "a fast reader will only catch up to 5% of the turns". At n=50 convs (267 turns) the pass edge is <= 13 stalls. Adjustable by the author as a parameter, not a derivation. |
| Reader reaction time | 0.45 s | `speed_gate.py` READER_REACTION_S | Part of the guarantee since protocol v3.0 (addendum 55): the simulated reader starts reading 0.45 s after the first word arrives. Derived (addendum 31): 0.25 s simple visual RT + 0.20 s saccade latency (Carpenter 1988). Single-sourced here (session_replicate imports it). |
| Instrument corpus | cal-50: 50 conversations / 267 turns | `data/live-corpus-cal50.json` | The v3.1 instrument corpus (every registered sweep command passes it). The old 5-conversation `live-corpus.json` is retired from protocol use - its verdicts were anti-conservative (addendum 23's warning, made concrete by addendum 66); the notebook keeps that history. |
| Repeats | 1 | `speed_gate.py` REPEATS_DEFAULT | Author ruling: "simplify, accept the worst with confidence". One rep per model; the verdict is the stall rate over the full cal-50 corpus (267 turns), not a rep-min. |
| Thinking allowance | 2048 tokens | `speed_gate.py` THINK_ALLOWANCE | Author ruling after 82% answer_empty at 1024 - thinking tokens are the user's informed choice, measured descriptively, never gated. |
| Determinism | temperature 0, seed 1024 | corpus + every payload | Pre-registered; seed is part of the protocol. |
| Reader band (re-sim) | 0.6-1.5x reader speed | `session_replicate.py` | Author ruling: reading speed is variable run-to-run; the band sweep is post-hoc, no server. |
| Roster ceiling (256k screen) | 4.96 GiB at 262,144 tokens | model-selection.md rule 10 | [D] Measured: the champion Qwen3.5-0.8B @ Q8_0, f16 KV, cold machine cost 4.96 GiB at 262,144 (MemAvailable delta). Supersedes the v3.1 5.27 GiB size ceiling (history: addendum 88). A new survivor raises it only if its own measured cost is higher. |
| Selection mechanism | ceiling first, then predictor screen | model-selection.md rules 1-2 | [A] Author ruling (session 35, addendum 12): the machine's ceiling is measured first (gallop search on the champion config), then candidates screen by predicted RAM at 262,144 under it (the registered ceiling predictor, rule 2). The lineage-counting mechanism is retired (history: addendum 77-79). |
| n=50 conversations | 50 convs / 267 turns | corpus + instrument | [A] The qualifying n, re-ruled at the v3.1 rebench (addendum ~71): n=5 was too little; at n=50 the stall-rate denominator is 267 turns (pass edge <= 13 stalls). The cal-50 corpus is the registered instrument corpus. |
| Ceiling predictor | cost = file(rung) + KV_eff x kvquant + 1.10 GiB | model-selection.md rule 2 | [D] Registered (session 35, addendum 13): file(rung) = file_Q8_0 x bpw/8.5 (RUNG_BITS); KV_eff = 262144 x L x 2 x kv_heads x head_dim / full_attention_interval. Validated on two anchors (exact on the champion, -5% conservative on the 2B). |
| Rung (ladder cut) | Q8_0 ladder; the tournament walks Q2_K-Q8_0 | `bench/constants.py` RUNG_DEFAULT / TOURNAMENT_MODEL_QUANTS | SUPERSEDED (addendum 140, catch-up): the addendum-86 Q8_0-only cut held through the v3.x era, but the session-36 tournament (addendum 10) re-opened the quant axis - TOURNAMENT_MODEL_QUANTS = [Q2_K, Q3_K, Q4_K, Q5_K, Q6_K, Q8_0] and TOURNAMENT_KV_QUANTS = [q4_0, q5_0, q6_K, q8_0, f16] (bench/constants.py, single source). The certify/bench path standardizes on (Q8_0 weights, f16 K, f16 V) (session 38, addendum 14). History: the Q8-only ruling is addendum 86/~74; the ladder-walk removal is addendum 86. RUNG_BITS retains all rungs in hf_download (size arithmetic only). |
| Certify bars (the difficulty knob) | speed 0, fwe 2/3, vt 4/5, arc 3/5 | `bench/constants.py` / `bench/certify.py` TASK_PASS_BARS | [A] Calibrated (session 38, addenda 12-13) under the author's floor rule (aggregate pass rate >= 50%, "if k needs to become zero to do so, we have a problem"): VT 5/5 was the most blocking gate at 31%; at 4/5 the stored records re-grade to 61%. FWE 3/3 -> 2/3: 47% -> 68%, the big jump (a 2/3 cell is "found the list, missed one word", not a fluke). Bars never move retroactively mid-run; records are stored per cell (x/k) so any bar re-grades free without re-measuring. ARC recalibrated 4/5 -> 3/5 (addendum 68, session 41): the stored f16 evidence graded 36% at 4/5 - below the >= 50% floor; 3/5 gives 52%, on target. |
| Medals (the confidence tiers) | gold / silver / bronze | `bench/certify.py` combined_medal | [A] Pure confidence tiers (session 37, addenda 14/22-24; the sigma language retired, addendum 10): gold = all tasks at their gold bars (speed 0 stalls, FWE 3/3, VT 5/5); silver = at least silver in all three (speed <= 1 stall, FWE 2/3, VT 4/5); bronze = any task at its silver bar or better. Re-graded from stored records, never re-measured. |
| Speed corpus (certify path) | 21 conversations (107 turns) | `bench/cells.py` speed_cell | [A] Session 38, addendum 2 (the redesign): the corpus is DEFINED as its first 21 conversations (the 50 was an arbitrary cut from a larger pool); cell = (model, rung, conversation r), r = 1..21 deterministic corpus order, seed = r. k = 5 (the MEDIAN turns per conversation) is a property of the corpus, like FWE's 3 words and VT's 5 names. Record = stall count 0..len per cell, re-gradable at any bar. |
| n per task (the certification ladder) | FWE 3, VT 5, speed 5, ARC 5 | `bench/constants.py` COMBINED_TASKS / ARC_CELL_K | [A] ARC_CELL_K = 5 (the author's ruling: k=5, like VT's 5 names), cell = (family, run), 0..5 graded record. ARC_RUN_CTX = 4096: ARC ignores context depth - one measurement, verdict applies to every rung. FWE k=3 and VT 5 names are upstream RULER shapes (session 36, addenda 7/10; VT num_chains 1, num_hops 4). |

## [P] Practical limits

| Constant | Value | Where | Nature |
|---|---|---|---|
| RAM reserve | 4.0 GiB | `infra/hf_download.py` RAM_RESERVE_GIB | OS + KV reserve for the memory shortcut (addendum 35); being validated rung-by-rung by the addendum-36 peak-RSS report. |
| Server ports | 8077 / 8078 / 8079 / 8081 | speed_gate / depth_probe / session_replicate / arc_eval | Collision avoidance only; no protocol meaning. |
| Health / post timeouts | 1800 s wall | `infra/llama_server.py` | Generous walls for 12B-class cold loads; retry ladders on HTTP errors. |
| Noise-sample guards | NOISE_MIN_ROOM 24, NOISE_TOKENS 128 | `speed_gate.py` | Shakeout-tuned: skip noise when the history nearly fills ctx; decode span small enough to fit the worst case. |
| Depth guards | DEPTH_HEADROOM 64 (gate) / 32 (probe), DEPTH_TOLERANCE 8 | `speed_gate.py`, `depth_probe.py` | Blob-budget safety margins. The 64/32 difference: the gate's conversations ride the blob AND reserve noise room; the probe's single prompt does not. Registered here so the pair is intentional. |
| Noise template overhead | 96 tokens | `speed_gate.py` NOISE_OVERHEAD | Measured-in-shakeout: 32 was too tight (qwen's template adds ~60+ rendered tokens); exact guard, retry ladder on 400. |
| Snapshot scope | safetensors + configs only | `infra/hf_download.py` allow_patterns | Scoped after the Meta 32 GB crash (addendum 35): the conversion path needs no `original/*.pth`. |
| Conversion tooling pins | llama.cpp b10964 build; converter checkout b29c606e2 | `infra/convert_quant.py` | Pinned builds - reproducibility of the quantization path itself. |
| Tournament depth grid | 4096 .. 262144 (dyadic) | `bench/constants.py` TOURNAMENT_DEPTHS | [P] The dyadic ladder: 4096, 8192, 16384, 32768, 65536, 131072, 262144 - each depth an n-cell; the climb ends at the first non-perfect depth (early stop is the cost bound). TOURNAMENT_CLIMBS = 21 (seed = climb number, session 36, addendum 11). |
| Combined cell | speed + FWE + VT (+ ARC) in one controller | `bench/certify.py` certify_rung_combined | [P] Session 38, addendum 3: one cell carries the three (ARC fourth) independent measurements, each measured only if missing; a candidate certifies when ALL tasks accept and dies when ANY is dead. Single-task namespaces (certify, certify_vt, certify_speed) remain available. |
| Two-gate orthogonality | speed gate = streaming guarantee; ruler gate = answer accuracy | `speed_gate.py` / `ruler_gate.py` | [P] Session 33, addendum 127's standing ruling: the quality gate is answer-accuracy, NOT the reader-wall guarantee; the two never grade each other's axis. History: the original niah_single task is REMOVED (session 37, addendum 3) - FWE superseded it; every quality verdict since addendum 136b is FWE. |
| Depth budget / headroom | ANSWER_HEADROOM 128; probe-and-trim to depth | `ruler_gate.py` | [P] The RULER-style sizing: the prompt is trimmed to the token budget via llama-server /tokenize accounting, never exceeding ctx (session 37, addendum 25's standing rules). |
| Vibe's editor | code_edit.py for every program-file edit | `code_edit.py` | [P] Session 40, addendum 6: Vibe owns code_edit.py and edits program files THROUGH it (verify-before-write, transactional, gated); the raw search/replace tool is not to be picked when code_edit can do the job. code_edit's goal (the author's ruling): good enough that there is no reason to pick anything else - the whitespace-flexible replace rescue and the not-found diagnostics (session 40, addendum 6) exist so an edit written against drifted formatting is rescued or re-aimed, not blind-failed. |

## [D] Derived / measured by this study

| Constant | Value | Where | Derivation |
|---|---|---|---|
| Answer cap | 299 tokens | `data/live-corpus-cal50.json` answer_cap_tokens | Arena reply p75 = 1197 chars, measured at corpus construction; carried into the instrument corpus (the retired `live-corpus.json` holds the same value). |
| Bandwidth class + law parameters | 102.4 GB/s; BW_eff 76.5 GiB/s, t_inf 74 t/s | study frame + law fit (Session 26) | The study's single machine class (the T14s), where the law lives: 1/t = size/BW_eff + 1/t_inf, R2 0.9996 in-family; cross-family error band +-15%. The 51.2-class replication is FUTURE WORK (addendum ~85) - the halving factor 0.50 stays pre-registered and unvalidated. |
| Bits-per-weight table | Q8_0 8.5 ... Q2_K 3.4 | `infra/hf_download.py` RUNG_BITS | llama.cpp average bits-per-weight; used for size estimates before download. Single-sourced: law_fit imports RUNG_BITS (the BPW_APPROX copy was deleted, addendum 44). |
| w/t anchor, qwen family | p05 0.412 (min 0.189) | cal-50 pass (addendum 66) | n=267 turns. LOAD-BEARING: the roster ceiling derivation (76.5 x (0.412/5.0 - 1/74) = 5.27 GiB) uses this p05. The Q5_K_M ceiling history lives in the notebook (addendum 66). |
| w/t anchor, llama family | p05 0.491 (min 0.242) | cal-50 pass (addendum 66) | n=267 turns. Supersedes the 0.144 joke-turn row (corpus-degenerate, addendum 54; the cal-50 min is 0.242 — no joke turn sampled at n=50). Ceiling grows to 6.48 GiB ≈ 9.8B params. |
| w/t anchor, mistral family | p05 0.366 (min 0.250) | cal-50 pass (addendum 66) | n=267 turns. p05 −0.004 vs the 0.37 anchor → VALIDATED (hold). The closest prediction of the four. |
| w/t anchor, phi family | p05 0.418 (min 0.304) | cal-50 pass (addendum 66) | n=267 turns. p05 −0.027 vs the probe min 0.445 → hold (within the ±0.05 grading band). |
| words/token band (unmeasured families) | (deleted, addendum 50) | - | Retired: every roster family is now measured or content-evidenced (llama 0.144, mistral 0.37, qwen 0.49, gemma sparse), and phi-4-mini was selected by threshold (passes iff w/t_min >= 0.245), not by band. No code references it; per the addendum-44 ruling, unused constants are deleted. The notebook keeps the history. |
| Candidate pool (256k survivors) | v4.3-measured survivors only | cpu-picker.html + gpu-picker.html CANDIDATES | [D] Measured under v4.3 (the 256k screen): Qwen3.5-0.8B @ Q8_0 (4.96 GiB) and Qwen3.5-2B @ Q4_K_M (3.48 GiB), both depth 262,144. The ONLY models the practitioner pages recommend. KNOWN DEBT: the pool is duplicated verbatim in both pages - a sync hazard; single-sourcing across static pages needs the registry row as the reference (see Practitioner-facing claims). History: the v3.1 7-member pool (session 35, addendum 10's retirement). |
| Pool values (cost / wps / ARC) | e.g. Qwen3.5-4B 12.99 / 6.32 / 90.4 | cpu-picker.html + gpu-picker.html | [D] Measured: cost = whole-stack machine cost (MemAvailable delta, addendum 36/40); wps = corpus p05 at 102.4 GB/s; ARC = full split n=1172. Any change re-measures, never hand-edits. |
| Memory witness (current) | llama-server's own -lv 5 accounting | `infra/llama_server.py` memory_breakdown_gib() | [D] Session 38, addendum 11: the smaps census is RETIRED - the -lv 5 memory-breakdown table is parsed into per-device model/context/compute plus weights_gib (summed over ALL model-buffer-size lines; hybrid builds print 0.00 placeholders). All three census sites (fwe_cell, vt_cell, speed mem report) record mem_census = {source, weights_gib, model_gib, context_gib, compute_gib, total_gib, devices}. mem_cost_gib (MemAvailable) stays the machine-level witness. History: the smaps + amdgpu-carveout machinery (addendum 4) was deleted at session 39, addendum 23 (the author's ruling: llama-server report only; the old records keep their keys, the code is gone). |
| Hybrid architecture finding | 5 of 9 families SSM/recurrent hybrids | session 38 addendum 10 | [D] The -lv 5 logs reveal llama_memory_recurrent layers in Qwen3.5-0.8B, Qwen3.5-2B (qwen35 arch, full_attention_interval 4) and RWKV7 alongside the Jambas. The size x t/s law does not apply to hybrids (SSM layers read a bounded recurrent state per token): attention models cluster at 70-76% of theoretical BW, hybrids at 34-61%. Corrects the Jamba-only claim - the law exception is a property of the architecture, not of one vendor. |
| Per-context recommendation table | recommend = fits AND 0 stalls | `bench/size_table.py` | [D] Session 38, addendum 16: for every (family, rung), the table reads the committed -lv 5 logs and the committed speed dumps (recomputed stall rate + worst-span w/s, the same reader-wall test), then rules per cell. The speed gate is the size authority (the author's ruling); the flat 5 GiB ceiling becomes a curve. Census coverage grows as the 12-family run commits logs. |

## [M] Magic - inherited or assumed, each with an exit plan

| Constant | Value | Where | Status / exit plan |
|---|---|---|---|
| Context depth | 4096 | `speed_gate.py` CTX_DEFAULT | llama-server's own default, inherited (addendum 9) - PROMOTED to protocol constant: the guarantee is honestly stated AT the tool's depth. Overflow behavior documented (context shift; gemma hard-errors). Exit: none needed - the promotion IS the fix; a practitioner menu (k_min as a function of D) is the report's extension. |
| ARC context | (unified with ctx 4096) | `arc_eval.py` ARC_CTX = speed_gate.CTX_DEFAULT | Addendum 45 (author ruling): ARC needs no smaller context - it uses the study's promoted depth constant 4096 (llama-server's own default), single-sourced from speed_gate. The strict-arc-era 2048 is deleted. The addendum-44 precondition (every rendered prompt checked against ctx before any run) still holds. |
| ARC server flags | threads 8, ngl 99, max_tokens 1, top-20 logprobs | `arc_eval.py` | llama.cpp conventions; 99 = "all layers offloaded". Exit: none - register as [P] conventions of the pinned build. |
| Depth-probe defaults | depth 4000, 5 samples x 64 tokens | `depth_probe.py` | Chosen in Session 27 for the KV-term measurement; 64 tokens is a short decode span, 5 samples the noise set. Exit: register as [P] instrument settings; the depth sweep (2048 vs 4000) already validated linearity. |
| Linear bandwidth law | w/s(BW) = w/s@102.4 x BW/102.4 | both practitioner pages | [M] Pre-registered form (decode is bandwidth-dominated at these sizes); VALIDATED ONLY AT THE REFERENCE POINT (all measurements at 102.4). Exit plan: the 51.2-class replication (halving factor check) or the first GPU-side calibration run. Used by both pages for every non-102.4 estimate - the most load-bearing unvalidated number in the practitioner artifacts. |
| Halving factor | 0.50 | notebook (pre-registered predictions) | [M] Half the bandwidth = half the w/s (efficiency cancellation at the same model size). Pre-registered, UNVALIDATED - the 51.2-class replication is deferred to future work (addendum ~85). Exit plan: the replication run; if the measured factor differs, both picker pages' estimates re-derive. |
| GPU tier bandwidths | 177.4 (GTX 480) ... 2039 GB/s (A100 80GB) | gpu-picker.html VRAM_TIERS | [P] Hardware facts (the lowest-bandwidth real card found at each capacity, 30 years of cards); the estimate per tier is conservative for anything faster at that capacity. |
| GPU cost carryover | CPU-side whole-stack cost reused as VRAM criterion | gpu-picker.html | [M] Conservative by design (the GPU stack is expected to need less; a fit is a lower bound). Exit plan: the first GPU-side calibration run re-measures cost on GPU and replaces the carryover. |
| FWE instrument constants | coded_wordlen 6, alpha 2.0, k=3, vocab depth/50, gen 128 | `ruler_gate.py` FWE_* | [M] Upstream verbatim: NVIDIA/RULER scripts/data/synthetic/freq_words_extraction.py @ main (checked from source, session 36, addenda 7/8 - the grid IS upstream's). Counts from the Zeta law count(w_rank) = num_words x rank^-alpha / zeta(alpha); rank 0 the '...' noise word, ranks 1-3 the answer. Exit: none - upstream fidelity IS the point; the task's own pass bar lives in TASK_PASS_BARS. |
| VT instrument constants | 5-letter names, 1 chain, 4 hops, haystack 'noise' | `ruler_gate.py` VT_* | [M] Upstream verbatim: NVIDIA/RULER variable_tracking.py @ main. The chain's sentences are inserted into the noise at random positions (upstream's noise path verbatim - the heap interleave belongs to the essay haystack branch; session 40, addendum 2 corrected the earlier heap claim); the pass is ALL expected names (a partial trace is a broken trace, unlike FWE's graded partial). Exit: same as FWE - upstream fidelity. |

---

## Practitioner-facing claims (the pages are the report - addendum 96)

The two static pages are the study's main artifact; every number they display
is a published claim. This section maps each claim to its registry row so the
pages stay auditable against the registry:

| On-page claim | Page(s) | Registry source |
|---|---|---|
| 5.0 w/s reader line, 95% confidence, 300-wpm reader | both | [A] reader line; [A] stall-rate max 0.05 |
| Recommended model per machine/VRAM | both | [D] v3.1 candidate pool (measured) |
| file GiB / stack cost GiB per model | both | [D] pool values (cost, MemAvailable-delta instrument) |
| w/s at bandwidth BW (est. w/s column) | both | [M] linear bandwidth law (unvalidated off 102.4) |
| min BW floor ~19.8 GB/s (list filter) | CPU | [D] derived: READER x 102.4 / max(pool wps) |
| min stack cost 1.06 GiB (list filter) | GPU | [D] derived: min(pool cost) |
| "higher specs run the same models as the default" (over 102.4) | CPU | follows from the pool's max cost 12.99 GiB + the law being an estimate, not a gate |
| VRAM tiers 1.5-80 GiB and their bandwidths | GPU | [P] GPU tier bandwidths |
| ARC scores | both | [D] pool values (ARC, full split n=1172) |

The CANDIDATES pool is duplicated in both pages (no build step by design);
when the roster changes, BOTH pages update from the same measurement record
(benchmark-results-*.json) - this row is the contract that they must agree.

## Deferred validations (future-work tracker)

| Open item | Registered as | Exit plan | Status |
|---|---|---|---|
| 51.2-class replication | halving factor 0.50 [M] | re-run one model on a 51.2 GB/s machine; factor re-derives if off | deferred (addendum ~85; run after the roster settles) |
| Linear law off 102.4 | linear bandwidth law [M] | same run - the replication validates both | deferred (same run) |
| GPU-side cost calibration | GPU cost carryover [M] | first GPU benchmark re-measures whole-stack cost on GPU | waits on the next system (204.8-class shopping) |
| GPU-side bandwidth law | linear law [M] (GPU use) | same calibration run | same |
| gemma debug | out of scope (addendum ~70) | debug logged open, low priority | closed as out-of-scope; reopening is a new ruling |

---

## Change log

| Date | Entry | Addendum |
|---|---|---|
| 2026-09-26 | Registry created from the full-code sweep; anchor chain stated; categories A/P/D/M assigned; exit plans registered for every [M]. | 39 |
| 2026-09-27 | Deprecation executed per the author's ruling (used-in-code stays a parameter; removable-and-unused deleted): BPW_APPROX deleted (single-sourced to RUNG_BITS); the 0.75 w/t fallback deleted from the verdict path (fail-verbose on v1 dumps); the 6.5 t/s line deleted (lag_analyze re-anchored to measured w/s at 5.0; depth_probe --reader-tp explicit); ARC_CTX promoted to [P] via an enforced in-code precondition. | 44 |
| 2026-09-27 | ARC_CTX unified with the study's depth constant: 2048 deleted, ARC uses ctx 4096 (llama-server's own default, addendum 9) - one depth for the whole study, single-sourced from speed_gate.CTX_DEFAULT. | 45 |
| 2026-09-28 | Protocol v3.0 (addendum 55): the verdict is the reader-wall test - the addendum-30 collision simulation on each turn's per-word arrival stream (fail = ANY catch-up event; flat worst-turn w/s retired to diagnostic after the addendum-54 tiny-answer degeneracy). The gate streams; dumps carry per-word deltas. Reaction time 0.45 s promoted to a guarantee constant (READER_REACTION_S, single-sourced in speed_gate). Pre-v3.0 dumps fail-verbose (no deltas). | 55 |
| 2026-09-28 | w/t anchors calibrated at n=50 convs / 267 turns per family (addendum 66): qwen p05 0.412 (UPDATE, −0.078), mistral 0.366 (validated), phi 0.418 (hold), llama 0.491 (grows; supersedes the 0.144 joke-turn row). Pooled anchor 0.33 → 0.366 (p05-based; the min-based rule retired — the min slides with n). HEADLINE on record: qwen Q5_K_M and mistral Q5_K_M FAIL the reader-wall test at n=50 (9 / 17 wall-failing turns, worst waits 6.34 / 6.59 s) — verdicts that PASSED on the 5-conv study corpus; no retroactive verdicts (pre-registered), the 5-conv verdict is on record as anti-conservative (addendum 23's warning made concrete). | 66 |
| 2026-09-28 | The sentinel certificate pre-registered (addendum 67): the certificate form (one-sided tolerance bound, author-ruled s=2; cone issues iff W - 2sigma >= 5.0 AND eps <= 2sigma; existence iff eps <= W - 5.0), S = tokenizer class x size cone (probe-assigned; strong form tokenizer identity, weak form probe w/t within Delta/2 of a class center). Delta = 0.05 w/t registered [M] (borrowed from the addendum-59 grading band; exit plan = the qwen sentinel run, the study's first cross-member transfer measurement). Q8_0-only ruling for the certificate study: parameters self-select (bpw fixes size<->params; class ceiling intersected with the family grid picks the sentinel). Cones issued from cal-pass data: llama-class (0/267 events) and phi-class (0/267, thin margin); mistral-class NEGATIVE (no member passes at any shipped size); qwen-class pending the sentinel run (pre-registered: w/s p05 6.3 band [5.1, 7.5]; Delta graded by the 4B's p05 vs the 9B's 0.412). Gemma ruled out of scope for the machinery (excluded by measurement; debug logged open, low priority). | 67 |
| 2026-09-28 | The qwen Q8 sentinel tail graded (addendum 69): Delta VALIDATED (4B p05 0.412 vs 0.412, gap 0.000 - the [M] exit plan fired; the band stays 0.05). Predictor 5-for-5 on its pre-registered bands (t/s [14.5,16.1] -> 14.6; events 0-12/267 -> 6; worst wait 1-5 s -> 3.36; w/s p05 [5.1,7.5] -> 6.4; w/t p05 0.412 -> 0.412). Cone verdict FAIL at s=2 on both tiers (event tier 6 wall-failing turns/267; quantile tier budget +0.21 PASSES, eps 1.29 vs 2sigma 1.22 fails by 0.07; the s-window [2.11, 2.34] exists but the author ruled s=2). The qwen-class Q8 roster on the 102.4 class is EMPTY (0.8B sub-band >= 10 w/s, 4B wall-FAIL) - the class-exclusive rule applied at Q8, measured. Unplanned: the w/t tail is substantially corpus-owned (4B min 0.189 = 9B min 0.189, same corpus, temp 0); "deterministic" is verdict-stable, not magnitude-stable (llama.cpp/Vulkan launch noise +-10-30% on single-turn magnitudes). The class band [5, 10) w/s (the author's upper-bound ruling; 10 asymptotic - the strict edge sits above 10 by the t_inf term) pre-registered with the 51.2-class replication predictions: halving factor 0.50 at 4.29 GiB (efficiency cancellation), ceiling ratio 2.25, band disjointness [2.12,5.27] vs [0.94,2.34] GiB. | 69 |
| 2026-09-28 | Redundancy pass (addendum 105): ms per GiB 13.07 DELETED (a unit restatement of BW_eff - 1000/76.5); the fast-reader anchor 300 wpm DELETED as a separate row (5.0 w/s x 60 - the ONE-anchor rule enforced, the citation folded into the reader-line row); the reader profiles 238/340 wpm DELETED (law_fit-era settings; that instrument's duty moved to session_replicate's band sweep); the bandwidth-class and law-parameters rows MERGED (the class is where the law lives). [D] now 10 rows, each an independent measurement or an operative value. | 105 |
| 2026-09-28 | Addendum 106: the historical Floor deletion-marker row removed from [A] (the addendum-103 convention - current values only - applied to the last remaining marker; history lives in the notebook). All seven registry tables fixed for GitHub rendering: every table header was missing the required blank line before it, so GitHub showed raw pipe text (the README tables rendered because they had the blank line). The anchor-chain floor aside removed with the row. | 106 |
| 2026-09-28 | Full-table audit (addendum 104): every row in all four tables verified against the code. [P] clean. [D]: answer-cap Where corrected to the instrument corpus; BPW row's exit plan marked fired (single-sourced since addendum 44); the pooled w/t anchor and the selection estimator DELETED (dead machinery - every roster model is benched and measured now, nothing consumes the predictions); the qwen family anchor flagged LOAD-BEARING (the roster ceiling derivation uses it). [M]: the three deletion-marker rows (0.75 w/t, 6.5 t/s, BPW duplicate) removed outright and the Transfer band (Delta) row deleted - its exit plan fired (addendum 69), the cone/certificate machinery was superseded by v3.1, and its tokenizer_probe.py membership-radius citation was stale (no such code). The anchor-chain diagram's stray code fence fixed. | 104 |
| 2026-09-28 | Obsolete [A] rows deleted per the author's ruling ("the protocol is current values only; for older proposals of the study, one can read the notebook"): the quant-5 inclusion filter (the Q5_K_M estimator era - dead since the Q8-only cut), the 5-conversation corpus shape (superseded by cal-50 as the instrument corpus; the old live-corpus.json is retired from protocol use), the repeats podium ("3 podium" was rung-walk-era). ARC sample + ARC always merged into one row; quant scope merged into the rung row. live-corpus-cal50.json committed at data/ (the registered commands are reproducible from a fresh clone). | 103 |
| 2026-09-28 | Catch-up registration (addendum 102): the registry is brought current with addenda 74-101. New [A] rows: roster ceiling (4.92B params / 5.27 GiB), the lineage selection mechanism (data availability, ALL matching models, no cherry-picking), quant scope (Q8_0 only), n=50 conversations, ARC always. New [D] rows: the v3.1 candidate pool (7 qwen members, all PASS, stall rates 0.0-2.6%) and its measured values. New [M] rows: the linear bandwidth law (the pages' most load-bearing unvalidated number), the halving factor 0.50, GPU tier bandwidths [P], the GPU cost carryover. Fixed: the ladder row (the rung walk is REMOVED, RUNG = "Q8_0", addendum 86), the bandwidth tiers row (51.2 is future work, 102.4 is the single class), the duplicate reaction-time row merged. New sections: Practitioner-facing claims (the pages are the report, addendum 96) and Deferred validations (the future-work tracker). Known debt on record: the CANDIDATES pool is duplicated across both pages (no-build-step tradeoff; the registry row is the sync contract). | 102 |
| 2026-10-05 | Catch-up registration (addendum 140): the registry is brought current with notebook sessions 36-38, which had shipped code without registry rows. New [A] rows: certify bars (speed 0, fwe 2/3, vt 4/5, arc 4/5 - calibrated under the author's >=50% floor rule), medals (gold/silver/bronze confidence tiers), the speed corpus (21 conversations, per-cell stall counts - session 38 addendum 2's redesign), n per task (FWE 3 / VT 5 / speed 5 / ARC 5). New [P] rows: tournament depth grid + 21 climbs, combined cell, depth budget, two-gate orthogonality. New [D] rows: memory witness (llama's own -lv 5 accounting supersedes the smaps census, session 38 addendum 11), the hybrid architecture finding (5 of 9 families SSM/recurrent - the law exception is architectural), size_table (the per-context recommendation curve). New [M] rows: FWE and VT upstream constants (NVIDIA/RULER verbatim). SUPERSEDED: the addendum-86 Q8_0-only ruling - the tournament re-opened the quant axis (TOURNAMENT_MODEL_QUANTS Q2_K-Q8_0, KV q4_0-f16); the certify path standardizes on (q8, f16, f16). The anchor-chain section now separates the two consumers of the per-turn collision test: the ladder still grades by stall rate (v3.1), the certify path grades by per-cell stall count - both use the unchanged binary per-turn event. | 140 |
| 2026-09-28 | Protocol v3.1 (addendum 73, author ruling, pre-run): the guarantee is the STALL RATE - PASS iff wall-failing turns / total turns <= 0.05 ("a fast reader will only catch up to 5% of the turns"); the per-turn collision test unchanged inside it. STALL_RATE_MAX = 0.05 registered [A] (speed_gate, single-sourced); at n=50 convs (267 turns) the pass edge is <= 13 stalls. Early-fail DELETED (a rate verdict needs its denominator - the aborted addendum-68 run would have scored a false 1.1% PASS; speed_gate loses --no-early-fail; full tails are now the only protocol, and full_benchmark inherits them by default). Recorded v3.0 verdicts stand as v3.0 verdicts; prospective v3.1 grades on record: the 4B sentinel (2.2%) and qwen Q5 9B (3.4%) would PASS v3.1, mistral Q5 (6.4%) stays FAIL. The addendum-71 overnight grading set updated prospectively (both 4B cells now predict PASS; no cell predicts v3.1 FAIL). | 73 |
| 2026-10-06 | Taxonomy section added (session 40, addendum 18): release > family > variant defined with explicit study extensions - literature-compatible terms, the study narrower family and the (family, rung, kv_k, kv_v) variant registered; lineage retired from the version sense (provenance is its literature meaning). Code keeps `families` as the key name - it matches. | 18 |
| 2026-10-06 | Certify path phase 2 (session 40, addendum 20): _acquire_missing_model runs convert_quant.create when acquire returns a convert+quantize plan - the certify controllers build the model, not just download it; convert_quant.create guards on a phase-1 source before building (no crash on a missing family dir). | 20 |
| 2026-10-06 | docs/ directory (session 40, addendum 21): all root-level study .md files moved to docs/ (git mv, history preserved); README.md stays at the root; lab-notebook/ unchanged; etc/registry_data.py reads docs/models.md; README links re-anchored. | 21 |
| 2026-10-06 | Formal methods join the toolbox (session 40, addendum 22): crosshair-tool (contract proofs over the pure functions - wilson_interval domain guard found and fixed) and hypothesis (property-based falsification - the [0,1] clamp found and fixed). tests/contracts.py proved; tests/test_properties.py in pytest. Once-in-a-while class, not a hook. | 22 |
| 2026-10-06 | Verification spread (session 40, addendum 23): eleven contracts proved (estimate_rung_gib, kv_gib, law_worst, the cell loaders); crosshair crashed arc_cells on a corrupt state key - the shared _int_cells guard now skips corrupt entries instead of killing the run. Fourteen properties. | 23 |
| 2026-10-06 | Weekly quality run (session 40, addendum 24): .github/workflows/weekly-quality.yml lands - cron 00:00 UTC Monday + manual dispatch; coverage, crosshair contracts, vulture, pre-commit hook drift report. mutmut stays out (too expensive). Crosshair: once-in-a-while class, not a hook; hypothesis rides free via pytest. | 24 |
| 2026-10-06 | Full-capacity run (session 40, addendum 25): --force-rung certifies every family at --rung (the study default Q8_0, f16 K, f16 V), ahead of the stored selections - the compression decision waits for the speed gate's verdict. | 25 |
| R-13 | Gold is exclusive per rung: among the families accepted (2-sigma) at a rung, only the one with the fewest parameters is gold; every other accept keeps its confidence tier but is not the rung's gold. Parameter counts come from the registry (never guessed); an accepted family without a count can never win gold. | addendum 70 (the exclusive gold) |
| R-14 | Pass/kill calibration counts only the cells of each rung up to the gold medal: families in param-ascending order, stopping after the fewest-parameter accepted family (the gold winner). Post-gold measurements (revivals, terminal-rung runs) never enter the stats. | addendum 71 (the calibration window); ARC fragment retired session 43 |
| R-15 | The practitioner page (docs/index.md, the GitHub Pages site) lists every rung with a gold medal: the winner (fewest-parameter 2-sigma accept), its measured whole-stack RAM cost, and the minimum memory bandwidth for the 5 w/s reader line - sorted deepest-first. HTML pickers and the live-status page are retired; the page is static Markdown updated with every new gold medal. | addendum 74 (the static page) |
| R-16 | The v7 corpus is a repo artifact (`state/v7-corpus.json`): built once, byte-identical for every contender and every machine, citable; a run loads the artifact and only rebuilds (and rewrites the artifact) when the grid constants change. | session 43 (the corpus-artifact ruling) |
| R-17 | The git tail runs ALWAYS: on a clean finish, on any crash (the traceback is appended to results.txt and committed as a CRASH artifact before re-raising), and on SIGINT. A crashed run still uploads state and results. | session 43 (the crash-reporting ruling) |
| R-18 | v7 model selection is the greedy (q, k, v) climb from (Q2_K, q2_K, q2_K) toward the fixed budget, taking the single-axis one-notch upgrade that lands closest to the budget without exceeding it; the result is maximal (no upgrade fits). The ladders use the K-encoding below q8 and top out at 16 bits. | session 43 (the author's rulings) |
| R-19 | A v7 question presents only the corpus prefix for its span grade (~s tokens), never the full corpus; a cell is graded only on the questions whose WHOLE REQUEST fits its window (span + prompt overhead + generation headroom <= window - session 44 honesty fix after the span-2048-at-ctx-2048 HTTP-400 crash), and unreachable grades are excluded, not failed. | session 43 (the prefix-cut and exclusion rulings), refined session 44 |
| R-20 | Every pre-commit hook dependency shall be installed in the working environment (ruff, ruff-format, pre-commit, ty, pytest, hypothesis, and the imports the suite resolves: huggingface_hub, pyarrow, transformers), so the full hook suite runs for real. The commit/push hooks shall not be omitted: no `--no-verify` bypass - if a hook fails, the environment or the code is fixed, never skipped. | session 43 (the author's no-bypass ruling) |
| R-21 | No backward compatibility: retired machinery (tasks, namespaces, prototype scripts, path fallbacks) is removed from the codebase, not maintained behind compatibility shims. Nothing in this repo reads or adapts to superseded formats except by explicit requirement. | session 44 (the author's no-compat ruling) |
| R-22 | The state file carries a schema, validated at load: a corrupt or mistyped entry raises `StateSchemaError` naming the exact path (e.g. `families.<name>.certify_vt.8192.3`), routed through the crash rail - never a silent start-fresh that discards measured cells, never an unguarded loader. Structured data stays JSON (git-diffable, stdlib); databases only when a real need appears. | session 44 (the author's schemas-are-helpful ruling) |
| R-23 | Every model answer is logged, one JSON line per question (grade, expected names, found count, raw answer), appended to the family's results dir - answers are always important for debugging, and reruns append rather than overwrite. Suppressing a hybrid model's thinking (enable_thinking False) is the default and is the model designer's supported mode: a model that fails under it is a design finding, not a harness bug. | session 44 (the author's answers-always ruling) |
| R-24 | Every evaluated v7 (family, ctx) cell commits and pushes immediately through the git rail (state, answers JSONL, server log, results) - the run is watchable cell by cell. A git failure never stops the run; the commit is skipped under --no-git/dry-run; skipped cells do not fire it. | session 44 (the author's push-per-cell ruling) |
| R-25 | The commit hook stays <= 5s: ruff, ruff-format, ty, markdown check, requirements check - no pytest per commit. The FULL pytest suite (deterministic pins + hypothesis properties) and the crosshair proofs run in GitHub Actions on EVERY push (push-regression.yml); the workflow's verdict is checked before the next push - a red run blocks the next delivery, not the commit. | session 44 (the author's 5s-hook + push-CI ruling) |
| R-26 | All agent code/text edits go through AI_tools/code_edit.py (edit, write, edit_many, safe_append, replace_verified) - the transactional editor built for this purpose (session 34, addendum 20). Hand-rolled string replacement (heredocs, sed, python -c open/replace/write) is PROHIBITED for repo files: it is not a transaction, and its silent partial-application failures have cost real debugging time (session 44). The session notebook is the one exception (chronological append is the sanctioned pattern there when code_edit is impractical). | session 44 (the author's use-the-tool ruling) |
