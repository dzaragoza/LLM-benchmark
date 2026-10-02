# model-selection.md — The Roster Selection Rules (pre-registered)

Every rule the study uses to pick which models enter a benchmark
roster, in one place. These rules are **fixed in advance** of any
measurement; each carries its provenance (notebook addendum or
session ruling) and its governing constants (protocol.md registry,
single-sourced).

**Governance:** changing or adding a rule is a protocol change — it
requires a notebook addendum and a commit, not a silent edit. The
README's "Roster selection" section is a summary that points here.

Retired rules are DELETED, not struck through (session 35, addendum
13, author ruling: "delete the retired rules, they just pollute").
Their history lives in the lab notebook (session 35, addenda 10-12).

---

## The rules

1. **Machine ceiling first (author ruling, session 35, addendum 12).**
   The machine's ceiling is determined FIRST, by measurement — the
   gallop search of the protocol ladder on the champion config
   (rule 10). THEN, and only then, candidate models are screened: a
   candidate is any model whose predicted RAM at 262,144, in its
   best configuration (the highest-fidelity weights/K/V combination
   that fits under the ceiling), is UNDER that measured ceiling.
   The registered predictor (rule 2) picks the config that gets as
   close to the ceiling as possible while staying under it.

2. **The ceiling predictor (registered, session 35, addendum 13).**
   Predicted machine cost at 262,144 tokens:
   `cost = file(rung) + KV_eff(262144) × kvquant + overhead`,
   where
   - `file(rung) = file_Q8_0 × bpw(rung)/8.5` (bpw from the
     registered RUNG_BITS table, hf_download.py, single-sourced);
   - `KV_eff = 262144 × L × 2 × kv_heads × head_dim / full_attention_interval`
     (KiB/token × depth; the interval divides because only
     full-attention layers hold the whole window — Qwen3.5 interval
     4);
   - `kvquant`: f16 = 1.0, q8_0 = 0.665, q5_0 = 0.34375,
     q4_0 = 0.400 (session 36, addendum 3 recalibration: f16 stays
     1.0 — measured near-exact (Jamba2 4.40 vs 4.42, +0.5%); the
     quantized factors are CALIBRATED on the overnight anchors, not
     the theoretical bytes-per-element (q8_0 0.53125, q4_0 0.28125),
     which underestimated 9–15%: 2B q8_0 4.78 vs 5.22 and 4B q4_0
     4.95 vs 5.81 back out to 0.665 and 0.400 — the quantized cache
     costs ~25% (q8_0) to ~42% (q4_0) more than raw bytes, book-
     keeping the quantization blocks and fragmentation; one anchor
     each, refine as more quantized-KV probes land);
   - `overhead = 1.10 GiB` ([P] practical, fitted on the two
     measured anchors: champion 0.8B @ Q8_0/f16 → predicted 4.96 vs
     measured 4.96; 2B @ Q4_K_M/q5_0 → predicted 3.31 vs measured
     3.48, −5% conservative — the predictor never over-predicts
     RAM on the anchors, which is the safe direction for a screen).
   Validation status (session 36 addendum 3): five anchors — f16-KV
   near-exact (0.8B: 4.96 vs 4.96; Jamba2: 4.40 vs 4.42, +0.5%);
   quantized-KV underestimated under the old theoretical factors
   (2B q8_0: 4.78 vs 5.22; 4B q4_0: 4.95 vs 5.81) and the factors
   are now calibrated on those anchors; RWKV overhead conservative
   (4.13 vs 3.58, −13%). Every probe grades the predictor when its
   measured cost lands (the standing pre-registration discipline).

3. **Non-thinking mode required (rationale rerouted, session 35,
   addendum 12).** Pure-reasoning models (no off switch) are
   excluded — not for ARC (retired as the study's instrument), but
   for the gates that now define the study: the speed gate (the
   300-wpm reader line) and the FWE count at depth. Hybrid models
   (toggleable reasoning) are allowed, run with thinking disabled.

4. **The family must have a size class predicted to pass the speed
   gate** on the target machine — via the general predictor
   (addendum 57) under the trust band (addendum 62): predicted
   ≥ 5.9 w/s trusted PASS, ≤ 4.1 trusted FAIL, between → bench.
   The predictor: t/s = 1/(size_GiB/76.5 + 1/74) (the law, 102.4
   GB/s tier), then w/s = t/s × w/t_min (family anchor if measured,
   else the pooled 0.33).

5. **Weights are always first-party** — the model owner's official
   Hugging Face repos.

6. **At least one model in the family has a published research
   paper** (technical report or peer-reviewed). A technical report
   covering the *lineage* counts (LFM2 precedent, Session 28; the
   Granite 3.0 report covering the 3.3 line, addendum 64).

7. **Data hygiene: v4.3-instrument measurements only (session 35,
   addendum 13; supersedes the addendum-79 v3.1 rule).** Study
   arithmetic consumes only data collected under the protocol
   version in force (currently v4.3, the depth-scored ladder with
   the speed gate + FWE rungs and the single-rung probe). Earlier
   records stand as history; they may be quoted, never consumed as
   inputs.

8. **The way of working: dry-run pre-flight, always.** Every
   `full_benchmark.py` invocation is issued TWICE: first with
   `--dry-run` (the READ-ONLY pre-flight — verifies tooling, lists
   every repo, runs the RAM/disk feasibility checks, reports each
   family's acquisition plan, and never touches the state file),
   read the report, then the SAME command without the flag. The
   pre-flight is the risk mitigation: a bad repo, a missing
   converter or an infeasible size is caught in minutes, not
   mid-sweep.

9. **The way of working: git pull first; commands given verbatim.**
   Every session on the author's machine starts with `git pull`
   (the sandbox and the T14s both write to main — a stale checkout
   silently runs old tooling or old specs). And every command
   handed to the author is given DIRECT and COMPLETE — full
   arguments, copy-paste runnable, never "issue the same command
   with X changed": hand-editing arguments is a recipe for
   non-reproducibility. The notebook's registered sequences carry
   the full literal text of every command.

10. **The 256k goal and the RAM ceiling (session 35, addendum 10).**
    The study's roster question is: which models pass BOTH gates
    (speed at the 300-wpm line, FWE 3/3) at a context of exactly
    **262,144 tokens** — the champion's (Qwen3.5-0.8B) trained
    window, the only depth with a measured pass-both existence
    proof in this RAM class. Contexts above 256k are out of scope
    (time budget). Selection screens:
    - **Window ≥ 262,144 trained** (no rope scaling — standing
      rule).
    - **Predicted RAM at 262,144 ≤ the champion's ceiling** in the
      model's best configuration: currently **4.96 GiB** (0.8B @
      Q8_0, f16 KV, measured). The champion sets the ceiling; a new
      survivor raises it only if its own measured cost is higher
      (the 2B at 3.48 GiB does not).
    - **Weights quant cap: Q8_0** (author ruling, session 35 — F16
      runs too long to wait for).
    The **single-rung probe** (`--min-rung 262144 --max-rung
    262144`) is the test — the full ladder is not run for new
    candidates. Every tested model is logged in the notebook's
    rejection log: candidate, config, predicted RAM, verdict, and
    the disqualifier (window / KV geometry / quality).

---

## How the rules combine (the worked examples on record)

- **The addendum-63/64 correction** — Qwen2.5-7B and
  Ministral-8B-2410 both passed the old rule 4's window scan but
  violated the publisher-identity rule (since retired); the picks
  were replaced by granite-3.3-8b-instruct and OLMo-2-1124-7B-
  Instruct. Lesson recorded: the window scan never overrides the
  roster rules.

- **The parameter-window arithmetic** (the rule-4 input): a model
  passes iff size ≤ BW_eff × (w/t_min/5.0 − 1/t_inf); at Q5_K_M
  on the 102.4 GB/s tier: w/t 0.33 → 6.1B params, 0.37 → 7.0B,
  0.445 → 8.7B, 0.49 → 9.7B (addendum 58).

---

## Pre-registered selection predictions (current)

Per the pre-registration discipline, the active picks and their
predictions are recorded in the notebook before any bench. Current
pipeline (session 35, addendum 13): the 2B quant-raise walk and the
three-model ceiling chase (see the notebook for the full predicted
table and the verbatim commands).
