# PROTOCOL.md - The Constants Registry

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
addendum-30 collision simulation, exact form, unchanged per-turn);
the verdict is the STALL RATE: PASS iff wall-failing turns / total
turns <= 0.05. The author's distributional ruling ("a fast reader
will only catch up to 5% of the turns"); early-fail is deleted (a
rate verdict needs its denominator - aborting at the first stall
would bias the rate downward; the addendum-68 aborted run would
have scored a false 1.1% PASS). At n=50 convs (267 turns) the pass
edge is <= 13 stalls. The old flat worst-turn w/s test stays a
diagnostic - it manufactured fails on tiny answers (the
addendum-54 degeneracy: the span of a 5-token answer is pipeline
overhead, not reading experience).

---

## [A] Author choices (ruled, on record)

| Constant | Value | Where | Ruling / derivation |
|---|---|---|---|
| Reader line (k=1 guarantee) | 5.0 w/s | `speed_gate.py` READER_WPS_DEFAULT | THE anchor. 5.0 w/s = 300 wpm / 60 (Brysbaert 2019 meta-analysis, silent reading, English non-fiction, adult mean). Single-sourced here; every other reader constant derives from it. |
| Stall-rate max (v3.1 guarantee) | 0.05 (5%) | `speed_gate.py` STALL_RATE_MAX | Author ruling (addendum 73): the guarantee is distributional - PASS iff at most 5% of turns have a catch-up event; "a fast reader will only catch up to 5% of the turns". At n=50 convs (267 turns) the pass edge is <= 13 stalls. Adjustable by the author as a parameter, not a derivation. |
| Reader reaction time | 0.45 s | `speed_gate.py` READER_REACTION_S | Part of the guarantee since protocol v3.0 (addendum 55): the simulated reader starts reading 0.45 s after the first word arrives. Derived (addendum 31): 0.25 s simple visual RT + 0.20 s saccade latency (Carpenter 1988). Single-sourced here (session_replicate imports it). |
| Instrument corpus | cal-50: 50 conversations / 267 turns | `live-corpus-cal50.json` | The v3.1 instrument corpus (every registered sweep command passes it). The old 5-conversation `live-corpus.json` is retired from protocol use - its verdicts were anti-conservative (addendum 23's warning, made concrete by addendum 66); the notebook keeps that history. |
| Repeats | 1 | `speed_gate.py` REPEATS_DEFAULT | Author ruling: "simplify, accept the worst with confidence". One rep per model; the verdict is the stall rate over the full cal-50 corpus (267 turns), not a rep-min. |
| Thinking allowance | 2048 tokens | `speed_gate.py` THINK_ALLOWANCE | Author ruling after 82% answer_empty at 1024 - thinking tokens are the user's informed choice, measured descriptively, never gated. |
| Determinism | temperature 0, seed 1024 | corpus + every payload | Pre-registered; seed is part of the protocol. |
| Reader band (re-sim) | 0.6-1.5x reader speed | `session_replicate.py` | Author ruling: reading speed is variable run-to-run; the band sweep is post-hoc, no server. |
| Roster ceiling | 4.92B params / 5.27 GiB at Q8_0 | MODEL-SELECTION.md + `full_benchmark.py` | [D] Derived: 76.5 x (0.412/5.0 - 1/74) = 5.27 GiB; ~1.07 GiB/B at Q8_0. The maximum model size/parameter count the study considers; relabeled in addendum 88 (params vs size). |
| Selection mechanism | lineages by # models <= ceiling; ALL matching models | MODEL-SELECTION.md | [A] Author ruling (addendum ~77, adopted permanently): lineages are chosen by the NUMBER of models under the parameter ceiling (data availability, not popularity), non-thinking/hybrid only, papers available; selection adds ALL matching models from a lineage - no cherry-picking. Registered from its first use; the roster is Qwen + granite + Phi + MiniCPM (31 families, 5 known-failing repos). |
| n=50 conversations | 50 convs / 267 turns | corpus + instrument | [A] The qualifying n, re-ruled at the v3.1 rebench (addendum ~71): n=5 was too little; at n=50 the stall-rate denominator is 267 turns (pass edge <= 13 stalls). The cal-50 corpus is the registered instrument corpus. |
| ARC | full test split, n=1172, every benched model | `arc_eval.py` ARC_NUM_DEFAULT + `full_benchmark.py` | No sampling (author ruling 2026-09-23: the whole split), and it runs on every benched model, always - the skip option removed from the orchestrator (addendum ~85). Cached results skip re-runs; no model is benched without its ARC score. |
| Rung (ladder cut) | Q8_0 only, quant out of scope | `full_benchmark.py` RUNG = "Q8_0" | The rung walk is REMOVED (addendum 86); the study is Q8_0-only, quant out of scope by author ruling (addendum ~74: "the rung ladder is cut to only q8" / "quant is out of scope for this study") - the tool and the report answer the Q8_0 question only. History: the ladder was Q8_0, Q6_K, Q5_K_M, Q4_K_M (Q7 dropped - no 7-bit rung exists in modern llama.cpp; Q4_0 dropped, addendum 37, redundant with Q4_K_M; Q3_K_M/Q2_K dropped, addendum 49, below ~4.5 bpw the quality penalty is too steep). RUNG_BITS retains all rungs in hf_download (size arithmetic only). |

## [P] Practical limits

| Constant | Value | Where | Nature |
|---|---|---|---|
| RAM reserve | 4.0 GiB | `hf_download.py` RAM_RESERVE_GIB | OS + KV reserve for the memory shortcut (addendum 35); being validated rung-by-rung by the addendum-36 peak-RSS report. |
| Server ports | 8077 / 8078 / 8079 / 8081 | speed_gate / depth_probe / session_replicate / arc_eval | Collision avoidance only; no protocol meaning. |
| Health / post timeouts | 1800 s wall | `llama_server.py` | Generous walls for 12B-class cold loads; retry ladders on HTTP errors. |
| Noise-sample guards | NOISE_MIN_ROOM 24, NOISE_TOKENS 128 | `speed_gate.py` | Shakeout-tuned: skip noise when the history nearly fills ctx; decode span small enough to fit the worst case. |
| Depth guards | DEPTH_HEADROOM 64 (gate) / 32 (probe), DEPTH_TOLERANCE 8 | `speed_gate.py`, `depth_probe.py` | Blob-budget safety margins. The 64/32 difference: the gate's conversations ride the blob AND reserve noise room; the probe's single prompt does not. Registered here so the pair is intentional. |
| Noise template overhead | 96 tokens | `speed_gate.py` NOISE_OVERHEAD | Measured-in-shakeout: 32 was too tight (qwen's template adds ~60+ rendered tokens); exact guard, retry ladder on 400. |
| Snapshot scope | safetensors + configs only | `hf_download.py` allow_patterns | Scoped after the Meta 32 GB crash (addendum 35): the conversion path needs no `original/*.pth`. |
| Conversion tooling pins | llama.cpp b10964 build; converter checkout b29c606e2 | `convert_quant.py` | Pinned builds - reproducibility of the quantization path itself. |

## [D] Derived / measured by this study

| Constant | Value | Where | Derivation |
|---|---|---|---|
| Answer cap | 299 tokens | `live-corpus-cal50.json` answer_cap_tokens | Arena reply p75 = 1197 chars, measured at corpus construction; carried into the instrument corpus (the retired `live-corpus.json` holds the same value). |
| Bandwidth class + law parameters | 102.4 GB/s; BW_eff 76.5 GiB/s, t_inf 74 t/s | study frame + law fit (Session 26) | The study's single machine class (the T14s), where the law lives: 1/t = size/BW_eff + 1/t_inf, R2 0.9996 in-family; cross-family error band +-15%. The 51.2-class replication is FUTURE WORK (addendum ~85) - the halving factor 0.50 stays pre-registered and unvalidated. |
| Bits-per-weight table | Q8_0 8.5 ... Q2_K 3.4 | `hf_download.py` RUNG_BITS | llama.cpp average bits-per-weight; used for size estimates before download. Single-sourced: law_fit imports RUNG_BITS (the BPW_APPROX copy was deleted, addendum 44). |
| w/t anchor, qwen family | p05 0.412 (min 0.189) | cal-50 pass (addendum 66) | n=267 turns. LOAD-BEARING: the roster ceiling derivation (76.5 x (0.412/5.0 - 1/74) = 5.27 GiB) uses this p05. The Q5_K_M ceiling history lives in the notebook (addendum 66). |
| w/t anchor, llama family | p05 0.491 (min 0.242) | cal-50 pass (addendum 66) | n=267 turns. Supersedes the 0.144 joke-turn row (corpus-degenerate, addendum 54; the cal-50 min is 0.242 — no joke turn sampled at n=50). Ceiling grows to 6.48 GiB ≈ 9.8B params. |
| w/t anchor, mistral family | p05 0.366 (min 0.250) | cal-50 pass (addendum 66) | n=267 turns. p05 −0.004 vs the 0.37 anchor → VALIDATED (hold). The closest prediction of the four. |
| w/t anchor, phi family | p05 0.418 (min 0.304) | cal-50 pass (addendum 66) | n=267 turns. p05 −0.027 vs the probe min 0.445 → hold (within the ±0.05 grading band). |
| words/token band (unmeasured families) | (deleted, addendum 50) | - | Retired: every roster family is now measured or content-evidenced (llama 0.144, mistral 0.37, qwen 0.49, gemma sparse), and phi-4-mini was selected by threshold (passes iff w/t_min >= 0.245), not by band. No code references it; per the addendum-44 ruling, unused constants are deleted. The notebook keeps the history. |
| v3.1 candidate pool | 7 qwen members, all PASS | cpu-picker.html + gpu-picker.html CANDIDATES | [D] Measured (v3.1 rebench, n=50): stall rates 0.0-2.6%, all PASS. The ONLY models the practitioner pages recommend. KNOWN DEBT: the pool is duplicated verbatim in both pages - a sync hazard; single-sourcing across static pages needs the registry row as the reference (see Practitioner-facing claims). |
| Pool values (cost / wps / ARC) | e.g. Qwen3.5-4B 12.99 / 6.32 / 90.4 | cpu-picker.html + gpu-picker.html | [D] Measured: cost = whole-stack machine cost (MemAvailable delta, addendum 36/40); wps = corpus p05 at 102.4 GB/s; ARC = full split n=1172. Any change re-measures, never hand-edits. |

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
| 2026-09-28 | Obsolete [A] rows deleted per the author's ruling ("the protocol is current values only; for older proposals of the study, one can read the notebook"): the quant-5 inclusion filter (the Q5_K_M estimator era - dead since the Q8-only cut), the 5-conversation corpus shape (superseded by cal-50 as the instrument corpus; the old live-corpus.json is retired from protocol use), the repeats podium ("3 podium" was rung-walk-era). ARC sample + ARC always merged into one row; quant scope merged into the rung row. live-corpus-cal50.json committed (the registered commands are reproducible from a fresh clone). | 103 |
| 2026-09-28 | Catch-up registration (addendum 102): the registry is brought current with addenda 74-101. New [A] rows: roster ceiling (4.92B params / 5.27 GiB), the lineage selection mechanism (data availability, ALL matching models, no cherry-picking), quant scope (Q8_0 only), n=50 conversations, ARC always. New [D] rows: the v3.1 candidate pool (7 qwen members, all PASS, stall rates 0.0-2.6%) and its measured values. New [M] rows: the linear bandwidth law (the pages' most load-bearing unvalidated number), the halving factor 0.50, GPU tier bandwidths [P], the GPU cost carryover. Fixed: the ladder row (the rung walk is REMOVED, RUNG = "Q8_0", addendum 86), the bandwidth tiers row (51.2 is future work, 102.4 is the single class), the duplicate reaction-time row merged. New sections: Practitioner-facing claims (the pages are the report, addendum 96) and Deferred validations (the future-work tracker). Known debt on record: the CANDIDATES pool is duplicated across both pages (no-build-step tradeoff; the registry row is the sync contract). | 102 |
| 2026-09-28 | Protocol v3.1 (addendum 73, author ruling, pre-run): the guarantee is the STALL RATE - PASS iff wall-failing turns / total turns <= 0.05 ("a fast reader will only catch up to 5% of the turns"); the per-turn collision test unchanged inside it. STALL_RATE_MAX = 0.05 registered [A] (speed_gate, single-sourced); at n=50 convs (267 turns) the pass edge is <= 13 stalls. Early-fail DELETED (a rate verdict needs its denominator - the aborted addendum-68 run would have scored a false 1.1% PASS; speed_gate loses --no-early-fail; full tails are now the only protocol, and full_benchmark inherits them by default). Recorded v3.0 verdicts stand as v3.0 verdicts; prospective v3.1 grades on record: the 4B sentinel (2.2%) and qwen Q5 9B (3.4%) would PASS v3.1, mistral Q5 (6.4%) stays FAIL. The addendum-71 overnight grading set updated prospectively (both 4B cells now predict PASS; no cell predicts v3.1 FAIL). | 73 |
