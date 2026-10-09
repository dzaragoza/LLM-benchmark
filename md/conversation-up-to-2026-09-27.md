# Conversation record — up to 2026-09-27

*Full state of the conversation for the next chat. Companion artifacts: the lab
notebook (`lab-notebook-llms-on-102-4-gb-s-system-ram-machines.md`, addenda
55–66 cover this conversation) and `protocol.md` (the constants registry).
Repo: github.com/dzaragoza/LLM-benchmark, branch `main`, direct commits, no PRs.
HEAD at close: `4a5aad5` (all work pushed).*

## People & conventions (unchanged)

- **Daniela Zaragoza** = the **author** (never "owner"). Working style:
  pre-registered predictions, registry discipline, no guessed names,
  corrections acknowledged plainly.
- **Machine**: ThinkPad T14s Gen 4 AMD (Ryzen 7 7840U, 780M, LPDDR5-6400,
  102.4 GB/s, 32 GB RAM). The author runs all real benchmarks and pastes
  output; the sandbox verifies with synthetic-stream unit tests + ruff.
- **Every command list for the author begins with `git pull --ff-only`**
  (author commits directly too — explicit ruling).
- Ruff is workflow-blocking: `python3 -m ruff check .` must pass
  (pyproject line-length 100, E/F/W/I/B/UP).

## Protocol state (governing forms)

- **Protocol v3.0 (addendum 55)**: the gate streams every turn; the verdict
  is the **reader-wall test** — a simulated reader (5.0 w/s = 300 wpm
  Brysbaert 2019; 0.45 s reaction) on the per-word arrival stream. A turn
  FAILS iff ANY word arrives after the reader is ready for it (mid-stream
  included). "The reader is the final judge. If the reader hits the wall,
  they feel the model is slow, so it fails." Flat worst-turn w/s is a
  diagnostic only (addendum 54: tiny-answer spans are pipeline overhead).
- **Ladder (addendum 49)**: Q8_0 → Q6_K → Q5_K_M → Q4_K_M only
  (`LADDER_DEFAULT`). Q3/Q2 retired.
- **The law**: `1/t = size_GiB/76.5 + 1/74` (BW_eff 76.5 GiB/s, t_inf 74;
  ±15% band; PROTOCOL row 94; refits per bandwidth tier).
- **General predictor (addendum 57)**: (1) t/s_pred = 1/(size/76.5 + 1/74);
  (2) w/s_pred = t/s_pred × w/t anchor — family p05 if measured, else the
  pooled anchor; (3) PASS iff ≥ 5.0. Simplicity guard: at most ONE new term.
- **Trust band (addendum 62)**: predicted ≥ 5.9 trusted PASS (skip bench),
  ≤ 4.1 trusted FAIL (exclude), between → bench. "The predictor proposes,
  the walk disposes."
- **Calibrated anchors (addendum 66, registry-current)**: qwen p05 0.412
  (min 0.189), mistral 0.366 (0.250), phi 0.418 (0.304), llama 0.491
  (0.242); **pooled anchor 0.366** (p05-based; the min-based pooling rule
  is retired — the min slides with n).

## Study #3 (v3.0 run) — final state

**Selections + ARC (5-conv corpus, addendum 56):**

| family | rung | ARC-C | note |
|---|---|---|---|
| Qwen3.5-9B | Q5_K_M | 92.4% | 1083/1172; passed 5-conv gate |
| Phi-4-mini | Q8_0 | 81.1% | 950/1172 |
| Mistral-7B-v0.3 | Q5_K_M | 75.6% | 886/1172 |
| Llama-3.2-3B | Q8_0 | 72.6% | 851/1172 |

All three consecutive pairs SEPARATED (−11.35 pp p<0.0001; −5.46 pp
p<0.0001; −2.99 pp p=0.0296). The phases 5–6 roster-leak fix
(full_benchmark.py defaults the ranking to the current run's command-line
families; `--roster` overrides) is in and verified.

**The calibration's verdict flips at n=50 (addendum 66 — the open ruling):**
qwen Q5_K_M FAIL (9/267 turns, 30 catch-up events, worst wait 6.34 s) and
mistral Q5_K_M FAIL (17/267, 41 events, worst 6.59 s); phi and llama PASS
clean (0 events in 267 turns each). Per-turn failure rates 3.4% / 6.4% —
hidden at n=5 (~22 turns). No retroactive verdicts (pre-registered); the
5-conv PASS is on record as anti-conservative (addendum 23's warning made
concrete). **The author must rule**: (a) re-bench the four selected rungs
at n=50 (~30–40 min/family; the same run fixes the addendum-65 class
boundary — the boundary rungs ARE the selected rungs), or (b) publish the
5-conv verdicts with the calibration tail as the scope statement. The
n=50 verdicts are already readable from the cal-dumps on disk
(`*.cal-dump.nothink.json`) — no re-run needed to know them.

## Selection rules (now in model-selection.md, addendum 64/65)

Nine pre-registered rules, single-sourced in **model-selection.md**;
README points there. Key rulings this conversation:

1. **Family = publisher/author** (rule 2, sharpened addendum 64). Lineage
   (inherited architecture/tokenizer from a distinct publisher, e.g.
   Falcon3's `LlamaForCausalLM`, deepseek-r1's Qwen base) = a *genetic
   caveat*, logged not gated. This rule FALSIFIED both addendum-63 picks:
   Qwen2.5-7B (same publisher as the roster's Qwen3.5-9B) and
   Ministral-8B-2410 (Mistral AI first-party, same MistralForCausalLM +
   tekken lineage as Mistral-7B-v0.3 — same lineage under any sharpening).
2. **Class-exclusive rule (rule 9, addendum 65)**: a bandwidth class C's
   roster is the set of sizes that FAIL on every lower class and PASS on C.
   Below-class models are pointless — the practitioner would switch
   machines. 51.2 GB/s is the floor tier (whole passable window is
   exclusive); the 102.4 boundary is fixed once the 51.2 law is fitted.
   Study #3's four selections get graded exclusive-or-shared then; qwen 9B
   (6.19 GiB) is the predicted boundary case — sharpened by the
   calibration: qwen 9B is now predicted to fail its own class ceiling
   (calibrated qwen ceiling 5.27 GiB ≈ 7.9B params).
3. **Structural finding (addendum 64)**: the 4–9B window's only
   trusted-pass tokenizer class (qwen-class w/t ~0.49) is family-blocked
   by rule 2 — rule-compliant candidates in that window are straddlers
   the bench decides.
4. **Parameter window (addendum 58, at Q5_K_M with calibrated anchors)**:
   size ≤ BW_eff × (w/t/5.0 − 1/t_inf); pooled 0.366 → ~6.9B params;
   qwen class 0.412 → ~7.9B; llama class 0.491 → ~9.8B.

## Study #4 (pre-registered, addendum 64, pending probe + bench)

**Picks** (both straddlers under the calibrated pooled anchor 0.366):
- **ibm-granite/granite-3.3-8b-instruct** — 8.17B, apache-2.0, ungated,
  69k downloads, `GraniteForCausalLM` (llama-class vocab = genetic
  caveat). Q5_K_M 5.42 GiB → law 11.9 t/s → **4.36 w/s** (recomputed
  addendum 66) — FAIL-leaning straddler. Family paper: Granite 3.0
  technical report (LFM2-precedent lineage coverage). ARC expectation
  ~60–70%.
- **allenai/OLMo-2-1124-7B-Instruct** — 7.30B, apache-2.0, ungated,
  35k downloads, `Olmo2ForCausalLM`, OLMo 2 paper arXiv 2501.00656.
  Q5_K_M 4.85 GiB → law 12.7 t/s → **4.65 w/s** — straddler. ARC
  expectation ~55–65%.

Rejected/logged: gemma-2-9b-it (0.24B over window edge, gated, uncertain
class), Falcon3-7B (first reserve; 4.22 w/s; weakest popularity 11k),
InternLM3-8B (trusted FAIL 3.7, custom_code converter risk), Yi-1.5-9B
(HF metadata fetch failed — logged for a future scan).

**Run commands (probe FIRST per addendum 59):**

```
git pull --ff-only
python3 tokenizer_probe.py --repo ibm-granite/granite-3.3-8b-instruct
python3 tokenizer_probe.py --repo allenai/OLMo-2-1124-7B-Instruct
python3 full_benchmark.py --no-thinking --roster "Llama-3.2-3B-Instruct,Qwen3.5-9B,Phi-4-mini-instruct,Mistral-7B-Instruct-v0.3,granite-3.3-8b-instruct,OLMo-2-1124-7B-Instruct" "ibm-granite/granite-3.3-8b-instruct" "allenai/OLMo-2-1124-7B-Instruct"
```

(No `--force` — the existing four skip; granite's tokenizer class is the
one genuine unknown; if either probes above the pooled class the
prediction recomputes mechanically.)

## Instruments (all pushed, ruff-clean)

- `speed_gate.py`: streaming reader-wall verdict; `--conversations N`
  (corpus prefix slice), `--no-early-fail` (record walls without aborting;
  verdict recomputed from deltas at analyze), `w/t calibration` line
  (n, min, p05 at ceil(0.05n)−1, mean). READER_WPS_DEFAULT 5.0,
  READER_REACTION_S 0.45 (single-sourced; session_replicate imports).
- `tokenizer_probe.py`: `--repo` tokenizer-only download; pre-shortlist
  role (addendum 59); measures corpus-prompt w/t at zero model cost.
- `full_benchmark.py`: leak-free phases 5–6 (roster defaults to this
  run's families); stale-state guard (addendum 43); --force re-bench.
- `arc_eval.py` (ARC_CTX = speed_gate.CTX_DEFAULT = 4096), `mcnemar`
  (exact), `law_fit`, `lag_analyze`, `depth_probe`, `session_replicate`,
  `hf_download.py` (RUNG_BITS: Q8_0 8.5, Q6_K 6.6, Q5_K_M 5.7, Q4_K_M 4.8).

## Files added this conversation

- **protocol.md** — the constants registry (created addendum 39 era; rows
  updated through addendum 66; change-log entries per addendum).
- **model-selection.md** (addendum 64/65) — the nine roster rules with
  provenance pointers and worked examples.
- **practitioner-goals.md** (addendum 65) — nine goals from the author's
  rulings: the MY-hardware question; reader as final judge; within-model
  q4–q8 ladder; right-sizing over flagships; class-exclusive benchmarking;
  tokenizer aim; general cheap predictor + trust band; pre-registration /
  registry / simplicity; same rules for everyone.

## Conversation timeline (this chat, addenda 56–66)

1. **Addendum 56**: v3.0 run graded — llama Q8_0 PASS 18.6 t/s; qwen Q8_0
   FAIL (1 mid-stream event, 0.06 s), Q6_K FAIL (2 events), Q5_K_M PASS
   12.1 t/s; phi Q8_0 PASS 16.0; mistral Q8_0/Q6_K FAIL (1.53/1.61 s
   waits), Q5_K_M PASS 13.5. Phases 5–6 roster leak found and fixed.
   Corrected ranking: all three pairs separated.
2. **Addendum 57**: general predictor stated; llama-3.1-8B and Phi-4
   14B FAIL at every anchor (no larger family member passes Q5_K_M).
3. **Addendum 58**: calibration unblocked (`--conversations`,
   `--no-early-fail`, w/t calibration line); parameter-window answer
   (~1–9.7B at Q5_K_M, tokenizer-shaped).
4. **Addenda 59–62**: tokenizer-aim ruling ("the key is the
   tokenizer"); n settled at 50 convs (±0.9 w/s trust band at 12 t/s;
   decision rule ≥5.9 / ≤4.1 / bench); the addendum-61 n* table retired
   as answering a question nobody asked (author's correction).
5. **Addendum 63**: study-#4 candidates pre-registered (Qwen2.5-7B,
   Ministral-8B) — later falsified by the family rule (addendum 64);
   stands as written.
6. **Addendum 64**: family/lineage ruling (family = publisher/author;
   lineage = genetic caveat); picks revised to granite-3.3-8b and
   OLMo-2-7B; structural finding (trusted-pass class family-blocked).
7. **Addendum 65**: class-exclusive rule (rule 9); model-selection.md +
   practitioner-goals.md created.
8. **Addendum 66**: calibration graded — anchors (qwen UPDATE 0.412,
   mistral VALIDATED 0.366, llama grows 0.491 superseding the 0.144
   joke-turn row, phi hold 0.418); pooled 0.366; HEADLINE: qwen and
   mistral Q5_K_M FAIL at n=50; open ruling (re-bench vs scope
   statement).

## Open items (in priority order)

1. **Author ruling**: study-#3 verdicts at n=50 — re-bench the four
   selected rungs (also fixes the class boundary) vs publish 5-conv
   verdicts with the calibration tail as scope statement.
2. **Study #4**: probe granite + OLMo tokenizers, then the bench (commands
   above; predictions 4.36 / 4.65 w/s, both straddle → bench decides).
3. **51.2 GB/s class replication** (v3.0, calibrated anchors from the
   start) — fixes the 102.4-class exclusive boundary (addendum 65).
4. **Study #3 report** (registry-referenced; ceiling table as the
   right-sizing spine; tokenizer-aim paragraph; n-justification methods
   paragraph; the n=50 flip finding whichever way the ruling goes).
5. Housekeeping: author's `pre-commit install` on T14s; llama.cpp
   `--chat-template-kwargs` bug (#20409) flagged; disk-space watch during
   quantization (12.1 GiB free warning during qwen Q5_K_M).
