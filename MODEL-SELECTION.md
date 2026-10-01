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

1. **Machine ceiling first (author ruling, session 35 addendum 12 —
   supersedes the lineage-density criterion).** The machine's ceiling is
   determined FIRST, by measurement — the gallop search of the protocol
   ladder on the champion config (currently the champion Qwen3.5-0.8B @
   Q8_0, f16 KV, 262,144 deep, cold cost 4.96 GiB; rule 17). THEN, and
   only then, candidate models are screened: a candidate is any model
   whose predicted RAM at 262,144, in its best configuration (smallest
   weights/K/V combination that can run), is UNDER that measured
   ceiling. Lineage data density, cell counts, and popularity are
   RETIRED as selection criteria (the historical Ollama walk-down and
   the addendum-77/78/79 lineage counting stand for the study-#1/#2/#3
   rosters as measured).

2. **RETIRED (author ruling, session 35 addendum 12).** The
   distinct-families (publisher-identity) rule is obsolete: the 256k
   screen admits any model that passes both gates under the ceiling,
   publisher notwithstanding (both current survivors are Qwen3.5). The
   rule stands as history for the study-#1/#2/#3 rosters as measured.

3. **Non-thinking category: models must run in non-thinking mode
   (rationale updated, author ruling, session 35 addendum 12).**
   Pure-reasoning models (no off switch) are excluded — NOT for the
   strict letter-answer ARC protocol (ARC is no longer the study's
   instrument), but for the gates that now define the study: the speed
   gate (the 300-wpm reader line) and the FWE count at depth. Hybrid
   models (toggleable reasoning) ARE allowed, run with thinking
   disabled.

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

7. **RETIRED (author ruling, session 35 addendum 12).** The
   prefer-latest-generation rule is obsolete under the 256k screen: a
   candidate is screened by window, RAM, and gates, not by generation.

8. **RETIRED (author ruling, session 35 addendum 12).** The
   two-category hybrid allowance is obsolete with the category
   structure it served; hybrids still run with thinking disabled per
   rule 3.

9. **RETIRED (author ruling, session 35 addendum 12).** The
   class-exclusive (bandwidth-class) rule is obsolete: the roster
   question is the 256k goal under the measured ceiling (rule 17), not
   the class-exclusive set.

11. **Data hygiene: v3.1-instrument measurements only (addendum 79).**
    Avoid using any data collected before protocol v3.1 in study
    arithmetic — the protocol was not as mature (the v3.0-era records
    stand as history; the picker's pool cut, addendum 76, is the
    precedent — now a standing rule, not a one-off). Pre-v3.1 numbers
    may be quoted as history, never consumed as inputs.

12. **The way of working: dry-run pre-flight, always (addendum 79).**
    Every `full_benchmark.py` invocation is issued TWICE: first with
    `--dry-run` (the READ-ONLY pre-flight — verifies tooling, lists
    every repo, runs the RAM/disk feasibility checks, reports each
    family's acquisition plan, and never touches the state file), read
    the report, then the SAME command without the flag. The pre-flight
    is the risk mitigation: a bad repo, a missing converter or an
    infeasible size is caught in minutes, not mid-sweep.
13. **The way of working: git pull first; commands given verbatim
    (addendum 82).** Every session on the author's machine starts with
    `git pull` (the sandbox and the T14s both write to main — a stale
    checkout silently runs old tooling or old specs; the addendum-81
    .bin branch is exactly the kind of change a stale checkout would
    miss). And every command handed to the author is given DIRECT and
    COMPLETE — full arguments, copy-paste runnable, never "issue the
    same command with X changed": hand-editing arguments is a recipe
    for non-reproducibility. The notebook's registered sequences carry
    the full literal text of every command.
14. **RETIRED (author ruling, session 35 addendum 12).** The fixed
   Q8_0-rung rule is obsolete: the 256k screen benches the candidate's
   best configuration (weights quant under the Q8_0 cap, K/V quant as
   fit), and the FWE rules are the protocol's latest (the 3/3
   word-count HIT at depth, protocol v4.3 — see PROTOCOL.md and rule
   17), not the addendum-86 fixed-rung regime.

15. **RETIRED (author ruling, session 35 addendum 12).** The
   ARC-runs-always rule is obsolete: ARC is retired as the study's
   instrument; the speed gate and FWE (rule 3, rule 17) are the
   measures.

16. **The way of working: tests before any sweep (addendum 87).**
    `python3 -m pytest tests/ -q` runs before any benchmark command
    (seconds, no network/models/GPU). The suite pins the four
    contracts the study depends on: the registered-constants
    arithmetic (PROTOCOL.md-derived ceiling/law/band), the state-file
    contract (the addendum-79 dry-run never-writes guard), the
    addendum-83 plan classifier (f16-before-download order), and the
    addendum-86 ARC-jobs filter (PASS and FAIL both ARC; infeasible
    and unbenched skip). Any edit to full_benchmark.py that breaks a
    contract fails here first.

17. **The 256k goal and the RAM ceiling (session 35, addendum 10).**
    The study's roster question is now: which models pass BOTH gates
    (speed at the 300-wpm line, FWE 3/3) at a context of exactly
    **262,144 tokens** — the champion's (Qwen3.5-0.8B) trained window,
    the only depth with a measured pass-both existence proof in this
    RAM class. Contexts above 256k are out of scope (time budget).
    Selection screens:
    - **Window ≥ 262,144 trained** (no rope scaling — standing rule).
    - **Predicted RAM at 262,144 ≤ the champion's ceiling** in the
      model's best configuration (smallest weights/K/V combination
      that can run): currently **4.96 GiB** (0.8B @ Q8_0, f16 KV,
      measured). The champion sets the ceiling; a new survivor
      raises it only if its own measured cost is higher (the 2B
      survivor at 3.48 GiB does not).
    - **Weights quant cap: Q8_0** (author ruling, session 35 — F16
      runs too long to wait for).
    The **single-rung probe** (`--min-rung 262144 --max-rung 262144`)
    is the test — the full ladder is not run for new candidates.
    Every tested model is logged in the notebook's rejection log
    (session 35, addendum 10): candidate, config, predicted RAM,
    verdict, and the disqualifier (window / KV geometry / quality).


**Future work (addendum 86):** the 51.2 GB/s-class replication run is
OUT of this study's execution plan — the v3.1 benchmark methodology
is too time-consuming to replicate at a second machine class. The
halving factor 0.50 (band↔class mapping) and the BW_eff refit
question (addendum 75) stay pre-registered-unvalidated, with their
caveats stated in lineages.md; the replication is the first candidate
for a follow-up study.

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

10. **The sentinel certificate (addendum 67; protocol references updated to v4.3, author ruling, session 35 addendum 12).** For a
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
