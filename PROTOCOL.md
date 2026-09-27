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
    (the k=3 floor line is deleted, addendum 50 - an observation
     for the report, not a protocol constant)
```
The guarantee (protocol v3.0, addendum 55): **the reader never hits
the wall** - on every turn, simulating the registered reader (5.0 w/s,
0.45 s reaction) on the turn's per-word arrival stream, the reader
never catches up with printing while the answer is incomplete. The
verdict is the addendum-30 collision simulation, exact form: a turn
fails iff ANY word arrives after the reader is ready for it (any
catch-up event, not just the last word). The old flat worst-turn w/s
test is retired to a diagnostic - it manufactured fails on tiny
answers (the addendum-54 degeneracy: the span of a 5-token answer is
pipeline overhead, not reading experience).

---

## [A] Author choices (ruled, on record)

| Constant | Value | Where | Ruling / derivation |
|---|---|---|---|
| Reader line (k=1 guarantee) | 5.0 w/s | `speed_gate.py` READER_WPS_DEFAULT | Match the FAST reader: 300 wpm / 60. The canonical anchor. |
| Reader reaction time | 0.45 s | `speed_gate.py` READER_REACTION_S | Part of the guarantee since protocol v3.0 (addendum 55): the simulated reader starts reading 0.45 s after the first word arrives. Single-sourced here (session_replicate imports it); previously session_replicate's CLI default only. |
| Fast-reader anchor | 300 wpm | `law_fit.py` READER_PROFILES | Cited: Brysbaert 2019 meta-analysis, silent reading, English non-fiction, adult mean. |
| Floor (k=3 headroom) | (deleted, addendum 50) | - | Author ruling: "obsolete. We use w/s >= 5. Remove it if possible. It is an observation, not needed for the protocol. We can mention in the report, but it doesn't play any role in the benchmark." FLOOR_DEFAULT deleted from speed_gate/depth_probe; the --floor flags, the headroom verdict line, the stlD stall metric, and law_fit's floor-20 default all removed with it. The gate is the reader line alone. |
| Corpus shape | 5 conversations, 4-8 user turns | `live-corpus.json` | Corpus construction (Session 10); re-ruled vs n=1 in addendum 23: the verdict is a min, fewer samples = anti-conservative PASS. |
| Repeats | 1 qualifying / 3 podium | `speed_gate.py` REPEATS_DEFAULT | Author ruling: "simplify, accept the worst with confidence"; 3 reps only for final published numbers. |
| Thinking allowance | 2048 tokens | `speed_gate.py` THINK_ALLOWANCE | Author ruling after 82% answer_empty at 1024 - thinking tokens are the user's informed choice, measured descriptively, never gated. |
| Determinism | temperature 0, seed 1024 | corpus + every payload | Pre-registered; seed is part of the protocol. |
| Reaction time | 0.45 s | `session_replicate.py` | Derived (addendum 31): 0.25 s simple visual RT + 0.20 s saccade latency (Carpenter 1988). Flag-tunable; deltas allow post-hoc re-simulation. |
| Reader band (re-sim) | 0.6-1.5x reader speed | `session_replicate.py` | Author ruling: reading speed is variable run-to-run; the band sweep is post-hoc, no server. |
| ARC sample | full test split, n=1172 | `arc_eval.py` ARC_NUM_DEFAULT | Author ruling 2026-09-23: no sampling - the whole split. |
| Quant-5 inclusion filter | Q5_K_M predicted pass | study #3 selection | Author ruling (addendum 48, superseding the addendum-37 quant-6 filter): a pick must be estimated to pass the gate at quant 5 — "we are leaving brains on the table, for roughly the same performance". The estimate uses the corrected estimator (t/s × per-family w/t_min, measured or family-anchored; the 0.43–0.49 default band is retired for filter use per addendum 40/47). |
| Ladder | Q8_0, Q6_K, Q5_K_M, Q4_K_M | `full_benchmark.py` LADDER_DEFAULT | Ecosystem enumeration; Q7 dropped (no 7-bit rung exists in modern llama.cpp), Q4_0 dropped by author ruling (addendum 37: redundant with Q4_K_M); Q3_K_M and Q2_K dropped by author ruling (addendum 49: below ~4.5 bpw the quality penalty is too steep for a q4–q8 study - gemma's Q2_K selection collapsed ARC 73.3% → 53.3%; a user is better served by a smaller model in the q4–q8 band). RUNG_BITS retains all rungs (used for size arithmetic). |

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
| Answer cap | 299 tokens | `live-corpus.json` | Arena reply p75 = 1197 chars, measured at corpus construction. |
| Law parameters (102.4 tier) | BW_eff 76.5 GiB/s, t_inf 74 t/s | law fit (Session 26) | Fitted: 1/t = size/BW_eff + 1/t_inf, R2 0.9996 in-family; cross-family error band +-15%. |
| Bandwidth tiers | 102.4 / 51.2 GB/s | study frame | Hardware facts of the two machine classes; the law refits per tier. |
| Bits-per-weight table | Q8_0 8.5 ... Q2_K 3.4 | `hf_download.py` RUNG_BITS | llama.cpp average bits-per-weight; used for size estimates before download. Exit plan for [M]-status duplicate: law_fit's BPW_APPROX is the same table - single-source it (see [M] rows). |
| words/token minimum, qwen family | 0.49 | addendum 37 | Measured worst-turn words/token (three runs, 40+ turns, stable). |
| words/token minimum, llama family | 0.144 | addendum 37 | The joke-answer turn (30 words / 208 tokens). |
| words/token band (unmeasured families) | (deleted, addendum 50) | - | Retired: every roster family is now measured or content-evidenced (llama 0.144, mistral 0.37, qwen 0.49, gemma sparse), and phi-4-mini was selected by threshold (passes iff w/t_min >= 0.245), not by band. No code references it; per the addendum-44 ruling, unused constants are deleted. The notebook keeps the history. |
| ms per GiB | 13.07 | notebook | Inverse of the fitted effective bandwidth. |
| Reader profiles (mean / 2-sigma-fast) | 238 / 340 wpm | `law_fit.py` READER_PROFILES | Brysbaert 2019: mean adults; 2-sigma above the fast anchor. |
| Selection estimator | w/s_pass = t/s(rung) x w/t_min(family) | addendum 37 | Pre-registered after the llama miss; retro-predicts both measured families (7.5 pred vs 7.32-8.24 meas; 2.0 pred vs 2.09 meas). |

## [M] Magic - inherited or assumed, each with an exit plan

| Constant | Value | Where | Status / exit plan |
|---|---|---|---|
| Context depth | 4096 | `speed_gate.py` CTX_DEFAULT | llama-server's own default, inherited (addendum 9) - PROMOTED to protocol constant: the guarantee is honestly stated AT the tool's depth. Overflow behavior documented (context shift; gemma hard-errors). Exit: none needed - the promotion IS the fix; a practitioner menu (k_min as a function of D) is the report's extension. |
| words/token rule of thumb | 0.75 | (deleted, addendum 44) | DELETED from the code by the author's ruling ("if it is not used anywhere, delete it"): WORDS_PER_TOKEN_DEFAULT removed from speed_gate (the verdict fallback is now fail-verbose - a v1 dump cannot be verdicted, re-bench with --force), the law_fit --words-per-token default removed (required with --reader). Historical note only; the notebook keeps the history. |
| Reader line in t/s (lag/probe view) | 6.5 t/s | (deleted, addendum 44) | DELETED: lag_analyze re-anchored to the study's single anchor (5.0 w/s) computing stalls from each turn's MEASURED server_wps; depth_probe's --reader-tp has no default (pass 5.0 / w/t_min(family)). Historical note only. |
| ARC context | (unified with ctx 4096) | `arc_eval.py` ARC_CTX = speed_gate.CTX_DEFAULT | Addendum 45 (author ruling): ARC needs no smaller context - it uses the study's promoted depth constant 4096 (llama-server's own default), single-sourced from speed_gate. The strict-arc-era 2048 is deleted. The addendum-44 precondition (every rendered prompt checked against ctx before any run) still holds. |
| ARC server flags | threads 8, ngl 99, max_tokens 1, top-20 logprobs | `arc_eval.py` | llama.cpp conventions; 99 = "all layers offloaded". Exit: none - register as [P] conventions of the pinned build. |
| BPW duplicate | BPW_APPROX | (deleted, addendum 44) | Copy DELETED; law_fit imports RUNG_BITS from hf_download (single-sourced). |
| Depth-probe defaults | depth 4000, 5 samples x 64 tokens | `depth_probe.py` | Chosen in Session 27 for the KV-term measurement; 64 tokens is a short decode span, 5 samples the noise set. Exit: register as [P] instrument settings; the depth sweep (2048 vs 4000) already validated linearity. |

---

## Change log

| Date | Entry | Addendum |
|---|---|---|
| 2026-09-26 | Registry created from the full-code sweep; anchor chain stated; categories A/P/D/M assigned; exit plans registered for every [M]. | 39 |
| 2026-09-27 | Deprecation executed per the author's ruling (used-in-code stays a parameter; removable-and-unused deleted): BPW_APPROX deleted (single-sourced to RUNG_BITS); the 0.75 w/t fallback deleted from the verdict path (fail-verbose on v1 dumps); the 6.5 t/s line deleted (lag_analyze re-anchored to measured w/s at 5.0; depth_probe --reader-tp explicit); ARC_CTX promoted to [P] via an enforced in-code precondition. | 44 |
| 2026-09-27 | ARC_CTX unified with the study's depth constant: 2048 deleted, ARC uses ctx 4096 (llama-server's own default, addendum 9) - one depth for the whole study, single-sourced from speed_gate.CTX_DEFAULT. | 45 |
| 2026-09-28 | Protocol v3.0 (addendum 55): the verdict is the reader-wall test - the addendum-30 collision simulation on each turn's per-word arrival stream (fail = ANY catch-up event; flat worst-turn w/s retired to diagnostic after the addendum-54 tiny-answer degeneracy). The gate streams; dumps carry per-word deltas. Reaction time 0.45 s promoted to a guarantee constant (READER_REACTION_S, single-sourced in speed_gate). Pre-v3.0 dumps fail-verbose (no deltas). | 55 |
