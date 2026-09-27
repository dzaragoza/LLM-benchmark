# MODEL-SELECTION.md — The Roster Selection Rules (pre-registered)

Every rule the study uses to pick which models enter a benchmark
roster, in one place. These rules are **fixed in advance** of any
measurement; each carries its provenance (notebook addendum or
session ruling) and its governing constants (PROTOCOL.md registry,
single-sourced).

**Governance:** changing or adding a rule is a protocol change — it
requires a notebook addendum and a commit, not a silent edit. The
README's "Roster selection" section is a summary that points here.

---

## The rules

1. **Popularity-sourced.** Start from the [Ollama library](https://ollama.com/library?sort=popular)
   ranked by pull count (snapshot: 2026-09-23), walking down the
   list. Popularity picks the *family*, never the weight file.
   (Session 22; README walk-down table.)

2. **Distinct families only — family = publisher/author.** No two
   roster models from the same model family, where family is the
   **publisher/author** (the organization that ships the weights).
   *Lineage* is sharper and is logged, not gated: when a distinct
   publisher ships a model that inherits another family's
   architecture or tokenizer (e.g. Falcon3's `LlamaForCausalLM`,
   deepseek-r1's Qwen-2.5 base, InternLM3's qwen-class tokenizer),
   the inheritance is a **genetic caveat** on record, not a
   conflict. The conflict test is publisher-identity only.
   (Session 22 revision; Session 24 deepseek precedent; addendum 64.)

3. **Non-thinking category: models must run in non-thinking mode.**
   Pure-reasoning models (no off switch) are excluded — the strict
   letter-answer ARC protocol requires plain answers. Hybrid models
   (toggleable reasoning) ARE allowed, run with thinking disabled.

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

7. **Prefer the latest generation** within a family: the newest
   model generation supersedes older ones of the same family
   (e.g. qwen3.5 > qwen3; phi4-mini > phi3).

8. **Hybrid models (toggleable reasoning) are allowed in BOTH
   categories**, always run in the mode that matches the category.
   Mode control is part of the protocol and is logged per run.

9. **Class-exclusive selection (bandwidth-class rule).** For a
   machine of bandwidth class C, benchmark only the model sizes
   that are *exclusive to C*: sizes that would NOT run (fail the
   reader-wall gate) on any lower class and DO run on C. Sizes
   that also pass on a lower class are out of scope for class C —
   a practitioner on that hardware would be served by the class-C
   roster; running a below-class model wastes the machine (they
   would simply switch to another machine). The real benefit for
   practitioners is the class-exclusive set: the models the
   machine unlocks. (Author ruling, addendum 65.)

---

## How the rules combine (the worked examples on record)

- **The addendum-63/64 correction** — Qwen2.5-7B and
  Ministral-8B-2410 both passed rule 4's window scan but violated
  rule 2 (publisher-identity with the roster's qwen / mistral
  slots); the picks were replaced by granite-3.3-8b-instruct and
  OLMo-2-1124-7B-Instruct. Lesson recorded: the window scan
  (rule 4) never overrides the roster rules (rules 1–3, 5–8).

- **The 4–9B structural finding** — the window's only trusted-pass
  tokenizer class (qwen-class w/t ≈ 0.49) is family-blocked
  (rule 2), so rule-compliant candidates in that window are
  straddlers the bench decides (addendum 64).

- **The parameter-window arithmetic** (the rule-4 input): a model
  passes iff size ≤ BW_eff × (w/t_min/5.0 − 1/t_inf); at Q5_K_M
  on the 102.4 GB/s tier: w/t 0.33 → 6.1B params, 0.37 → 7.0B,
  0.445 → 8.7B, 0.49 → 9.7B (addendum 58).

10. **The sentinel certificate (Q8_0-only study; addendum 67).** For a
tokenizer class and machine class, S = {models of the class at or
below the sentinel's size, well-behaved} at the fixed rung. The
sentinel self-selects: the largest class member under the predicted
trusted-PASS ceiling (rule 4's arithmetic at the fixed rung). A
sentinel measured at W with the n=50 instrument (2sigma) certifies
S iff W - 2sigma >= 5.0 AND eps <= 2sigma, where eps = Delta x
 t/s(sentinel) + law residual and Delta = 0.05 w/t (PROTOCOL [M]
row; exit plan = the qwen sentinel run). Class assignment: strong
form = tokenizer identity (hash); weak form = probe w/t within
Delta/2 = 0.025 of a measured class center (tokenizer_probe.py).
An empty cone is a valid negative certificate. Every certificate
carries the well-behaved conditional (gemma excluded by
measurement, addendum 46; ruled out of scope, addendum 67).

---

## Pre-registered selection predictions (current)

Per the pre-registration discipline, the active picks and their
predictions are recorded in the notebook before any bench:
addendum 64 — granite-3.3-8b-instruct (3.93 w/s, FAIL-leaning
straddler) and OLMo-2-1124-7B-Instruct (4.19 w/s, straddler),
both pending the probe-first check and the bench.
