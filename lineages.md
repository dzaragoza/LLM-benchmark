# Lineages — the wps bands (T14s, predicted and measured)

**Scope note (author ruling, addendum 75): quant is OUT OF SCOPE for
this study.** The lineages view is **Q8_0-only** — the one fixed rung
— and the planned multi-quant extension is deferred to a later study.
The quant column is removed; the rung stays stated here once. Size
stays a column: params do not determine size well enough (the
measured spread is 1.00–1.26 GiB/B across the seven benched
members; the 0.5B packs 1.26 — embedding-heavy small models — and
that +18% size error alone flipped its band call, addendum 74), and
size is the law's input: the through-origin fit size ≈ 1.05 ×
params (R² 0.99) carries ±17% residuals at the small end (addendum
75).

One section per family lineage, the study's right-sizing view turned
into a table: every member of the line, at the fixed rung **Q8_0**,
with its predicted T14s words-per-second and the **band** it lands
in. The bands are the serving classes: a model belongs to exactly
one machine class — the smallest class on which it clears the
reader wall — and the band is that assignment, stated as one
T14s-predicted number per member. The working question per row:
*which machine class does this model serve, and is it wasting the
hardware of every class above that?*

**The bands (T14s-predicted w/s; the author's ruling, addendum 69):**

- **[5–10] wps** — serves the **102.4 GB/s class**: predicted to
  pass the reader wall on the T14s, and halving the bandwidth
  (the 51.2 class, factor 0.50 pre-registered) drops it below the
  5.0 reader line. The class's own roster. The strict edge sits a
  hair above 10 (the t_inf term makes the doubling asymptotic) —
  above ~10 w/s the model is wasting this machine.
- **[10–20) wps** — serves the **51.2 GB/s class**: sub-band on
  the T14s (it passes with 2× margin to spare), in-band after the
  halving. The study-#1 champion class.
- **[20–40) wps** — serves the **25.6 GB/s class** (the next class
  down, not yet studied): twice-sub-band on the T14s.
- **below 5 wps** — clears no band: FAIL on both studied classes
  (marked FAIL with the predicted value, in the [5–10] column as
  the lowest band).

**The roster window (addendum 78, the author's ruling):** the
parameter ceiling is NOT an ad-hoc number — it is **the largest size
predicted to pass**, derived from the registered constants: the law
inverted at the reader line gives size_max = BW_eff × (w/t/5.0 −
1/t_inf) = 76.5 × (0.412/5.0 − 1/74) = **5.27 GiB ≈ 4.92B params at
Q8_0 (×1.07 GiB/B)** under the qwen-class anchor (addendum 88 relabel: the old text read 4.92 GiB - 4.92 was the params number mislabeled as a size). Every lineage
member at or below that ceiling enters the roster (the whole lineage
matching the rules — no picking and choosing); everything above it is
a line-endpoint FAIL row. The v3.1 T14s results (addendum 74) are the
ceiling's calibration data.

**Machinery (all registered constants):** w/s = law(size) × w/t
anchor. Law (102.4 tier): `1/t = size/76.5 + 1/74` (fitted, R²
0.9996). Qwen-class anchor: p05 0.412 (calibrated n=267, addendum
66; cross-member transfer VALIDATED at gap 0.000, addendum 69 —
one anchor serves the whole lineage). Q8_0 size = params × 1.07
GiB/B (calibrated on the measured 4B file: 4.29 GiB / 4.0B,
addendum 68); measured file sizes supersede estimates where they
exist. Prediction band (corrected, addendum 74): pred ± (2σ_w/t ×
t/s) = pred ± 0.156·t/s. The class assignment below the band column derives from the
halving factor 0.50 (pre-registered, addendum 69; its validation
instrument, the 51.2 replication, is FUTURE WORK — out of this
study's execution plan per addendum 86 — so the band↔class mapping
carries that one unvalidated constant indefinitely).

**In-band confidence:** the trust band (≥ 5.9 / ≤ 4.1, addendum 62)
is the internal BENCH FILTER only (demoted, addendum 72). The
practitioner guarantee is protocol v3.1 (addendum 73): **PASS iff
at most 5% of turns stall the reader** — "a fast reader will only
catch up to 5% of the turns" (at n=50 convs / 267 turns, the pass
edge is ≤ 13 stalls). Under v3.1 the sentinel's measured 6/267
(2.2%) is a PASS; the recorded v3.0 FAIL stands as the v3.0-verdict
history, and the report will state both semantics.
Bands above 10 carry no wall risk at n=50 by prediction (their
corpus-min turns sit ≥ 5.07 w/s).

**Provenance markers:** (M) = measured file size on the T14s;
(P) = params x 1.07 GiB/B (the addendum-68 calibrated rate;
NOT the raw 8.5-bpw arithmetic - the converter keeps the output
tensor at F16, so measured files run 1.006-1.26 GiB/B, and the
calibrated rate beats the naive arithmetic on the measured set);
(C) = config.json arithmetic (size_predict.py, addendum 110 - exact
per-tensor params, body @ 8.5 bpw + output tensor @ F16; -2.7% to
+3.1% on the measured set). The granite/Phi/MiniCPM (P) rows
upgrade to (C) or (M) once tonight's run lands their configs/files.
**ARC column:** ARC-Challenge test,
n=1172, measured at Q8_0 on the T14s (the overnight run, addendum
74); higher is better. The cross-family Q8_0 records for comparison:
Phi-4-mini 81.1% and Llama-3.2-3B 72.6% (both 0/267 stalls at n=50,
addendum 66) — mistral has no passing Q8_0 member (measured FAIL).

**ARC vs parameters (addendum 117, the qwen fit):** on the v3.1 qwen set the score is log-linear in parameters - score = 61.5 + 41.0*log10(P), R2 0.920, rmse 3.9 points. Read it as hardness: 25% is random chance (4-way choice), 50% is reachable below 1B, but a constant slope in log10(P) means every equal step up the ARC scale costs a constant MULTIPLICATIVE factor in parameters (~2.3x per 10 ARC points). Within a lineage, ARC-per-parameters is a fixed exchange rate - buying ARC with size is exponential in parameters, which is why the bandwidth-bound regime is a plateau where you pick the family intercept, not a scale race. Descriptive until the cross-family cells grade the slope.

---

## Qwen (the lineage that armed the study)

The line that calibrated the instrument: the 1.5B was study #1's
champion, the 3B study #2's, the 9B study #3's selection, and the
4B was the sentinel that validated Δ and went 5-for-5 through the
predictor (addenda 67–69). The overnight validation run
(addendum 71, pre-registered) benches every predicted-pass cell —
the seven members at or above 5 w/s.

| name | parameters | Q8_0 size (GiB) | ARC (n=1172) | [10–20) wps | [5–10] wps | [20–40) wps | v4 depth (tok) |
|---|---|---|---|---|---|---|---|
| Qwen-110B (old series, line endpoint) | ~110B | 117.7 (P) | — | — | FAIL (0.3) | — | — |
| Qwen2.5-72B (line endpoint) | 72.7B | 73.0 (C) | — | — | FAIL (0.4) | — | — |
| Qwen3-Coder-30B | ~30B | 32.1 (P) | — | — | FAIL (1.0) | — | — |
| Qwen3.6-27B | ~27B | 28.9 (P) | — | — | FAIL (1.1) | — | — |
| Qwen3.5-9B | ~8.7B | 9.3 (P, from measured Q5 6.19) | 92.4 (at Q5_K_M, quant out of scope) | — | FAIL (3.1) | — | — |
| Qwen2.5-7B-Instruct | 7.62B | 8.01 (C) | — | — | FAIL (3.4) | — | — |
| Qwen3.5-4B | 4.0B | 4.29 (M) | **90.4** | — | **predicted 5.92 → measured 6.32 (2.6% stalls, v3.1 PASS)** † | — | **32,768** |
| Qwen3-4B | 4.0B | 3.99 (M) | **85.0** | — | predicted 5.93 → **measured 7.10** (1.1% stalls, v3.1 PASS) | — | **16,384** |
| Qwen2.5-3B-Instruct | 3.1B | 3.37 (M) | **76.1** | — | predicted 6.77 → **measured 9.72** (0.4% stalls, v3.1 PASS) | — | **OUT** (task refusal — session 34 add. 8) |
| Qwen3-1.7B | 1.7B | 1.71 (M) | **68.0** | predicted 11.05 → **measured 10.66** (0.0% stalls, v3.1 PASS; Δ gap 0.081 MISS) | — | — | **32,768** (trained window 40,960) |
| Qwen2.5-1.5B-Instruct | 1.5B | 1.76 (M) | **73.5** | predicted 11.94 → **measured 14.86** (0.0% stalls, v3.1 PASS) | — | — | **16,384** |
| Qwen3.5-0.8B | 0.8B | 0.86 (M) | **61.3** | predicted 16.68 (flipped) | — | **measured 25.86** (0.0% stalls, v3.1 PASS — the band flip, addendum 74) | **65,536** |
| Qwen2.5-0.5B-Instruct | 0.5B | 0.63 (M) | **45.8** | — | — | predicted 20.09 → **measured 25.03** (0.0% stalls, v3.1 PASS; Δ gap 0.162 MISS — the study's first Δ miss, the generation-split question) | **OUT** (counting floor — 136f) | 0 (counting floor, 136f) |

† **The sentinel row, honestly stated (addenda 69/73):** the 4B is
the predicted in-band member (5.92, dead in [5–10]) whose measured
sentinel run recorded 6 wall-failing turns of 267 (2.2%) — a FAIL
under protocol v3.0 (the never-guarantee; also the cone's
quantile tier: ε 1.29 vs 2σ 1.22, short by 0.07, so the
certificate did not issue) and a **PASS under protocol v3.1** (the
stall-rate guarantee). The predictor's w/s band [5.1, 7.5] was HIT
(measured 6.4). The overnight replicate (addendum 74) CONFIRMED the
verdict-stability finding: 7/267 stalls (2.6%), the same stalling
conversations (19/33/39), magnitudes drifted ±30–75% — a v3.1 PASS
both times, and the qwen-class Q8 roster on the 102.4 class now
holds all three [5,10] cells by measurement.

**The lineage's shape (the right-sizing read, measured):** each
band holds one family-grid cell of this line. [5–10]: the 3B/4B
cells — all three measured v3.1 PASS at 0.4–2.6% stalls, the
sweep's headline. [10–20): the 1.5–1.7B cells (study #1's
champion class), measured 10.66–14.86. [20–40): the 0.8B and
0.5B — BOTH measured above 25 w/s (the 0.8B flipped from its
predicted band by the law's small-end miss, addendum 74; the 0.5B
confirmed its superseded prediction). Below 5:
everything ≥ 7B at Q8 (the 9B's value lives at Q5_K_M, not Q8).
The lineage's grids (0.5 / 1.5 / 3 / 4 / 7–9 / 27–30 / 72+)
quantize coarser than any class window: the right-size member is
never the flagship (addendum 58's pattern, now visible per band).

**The band cascade (the class-exclusive structure, addendum 65):**
each model serves exactly one class — the smallest class on which
it is in-band — so the class rosters are disjoint by construction:
the 0.5B is the 25.6 class's; the 0.8B–1.7B cells are the 51.2
class's; the 3B/4B cells are the 102.4 class's (empty at Q8 by
measurement); the 9B is a Q5_K_M model of the 102.4 class; nothing
above 9B serves any studied class at any rung (the 12–14B class
needs ~2× 102.4's bandwidth — the next machine up).

**Caveats on record:** the halving factor 0.50 (band↔class
mapping) is pre-registered, not yet validated (addendum 69; its
validation instrument, the 51.2 replication, is FUTURE WORK — out of
this study's execution plan per addendum 86 — so the caveat stands
indefinitely). Sizes marked (P) are params x 1.07 GiB/B
estimates (the addendum-68 calibrated rate); sizes marked (C)
are config.json arithmetic (size_predict.py, addendum 110:
exact per-tensor params, body @ 8.5 bpw + output tensor F16,
±3% on the measured set). The anchor 0.412 is
corpus-conditional (the w/t tail is substantially corpus-owned,
addendum 69) — these bands are for this reader and corpus class;
generation-side well-behavedness is assumed per the qwen line's
measured record. The overnight run (addenda 71/74) TESTED that
assumption across generations: the cross-generation Δ test came back
5/7 — the two Qwen3.5 members and the 2.5-1.5B/3B/4B inside the band,
the 2.5-0.5B (gap 0.162) and Qwen3-1.7B (gap 0.081) outside. The
generation-split question (is the qwen class one class or two?) is
logged open in addendum 74's completion.

---

## Phi (Microsoft — the measured-anchor lineage, six cells)

The lineage with a second measured class anchor: the phi-class p05 0.418
is registry-calibrated [D] (addendum 66), so this is the only new
lineage whose predictions do not lean on the pooled anchor. The 3.8B
trio is also the study's first within-lineage tokenizer-class boundary
(phi-3/3.5 vocab 32,064 vs phi-4-mini vocab 200K). All rows
non-thinking; phi-1/1.5/2 benched as base models (no instruct shipped).
All values PRE-REGISTERED (addendum 76) — none measured yet.

| name | parameters | Q8_0 size (GiB) | ARC (n=1172) | [10–20) wps | [5–10] wps | [20–40) wps |
|---|---|---|---|---|---|---|
| phi-4-mini | 3.8B | 4.07 (P) | pending | — | predicted 6.27 (measured cone W 6.7; anchor 0.418) | — |
| phi-3.5-mini | 3.8B | 4.07 (P) | pending | — | predicted 6.27 | — |
| phi-3-mini | 3.8B | 4.07 (P) | pending | — | predicted 6.27 | — |
| phi-2 | 2.7B | 2.89 (P) | pending | — | predicted 8.15 | — |
| phi-1.5 | 1.3B | 1.39 (P) | pending | predicted 13.19 | — | — |
| phi-1 | 1.3B | 1.39 (P) | pending | predicted 13.19 | — | — |
| phi-3-medium (14B, line endpoint) | 14B | 15.0 (P) | — | — | FAIL (1.7) | — |

**The pre-registered questions this lineage answers:** (1) does the
phi-class anchor 0.418 hold ACROSS GENERATIONS (the exact question the
qwen Δ misses raised) — the 3.8B trio's per-generation p05s vs 0.418 is
the within-lineage Δ test; (2) the strong-form class boundary: phi-4's
200K vocab vs the 32K trio — if the 4-mini's p05 departs the trio's by
more than Δ, the tokenizer class split INSIDE one lineage is measured;
(3) base-vs-instruct: phi-1/1.5/2 are base models — their rows test
whether content sparseness (the w/t bottom) is instruct-owned or
tokenizer-owned.

---

## Granite (IBM — the size-fixed quartet, twelve cells)

The H1-vs-H2 discriminator: FOUR models at IDENTICAL size (2B, four
generations — 3.0, 3.1, 3.2, 3.3). With size held fixed, any p05
scatter across the quartet is generation-owned by construction — the
sharpest test of the generation-split hypothesis the study can run.
granite-4.2-3b and granite-4.1-3b carry thinking toggles (run
non-thinking, rule 8); granite-4.0-h-micro is a hybrid Mamba-2/transformer
(llama.cpp support to be verified before acquisition; the dense
granite-4.0-micro is the same-size fallback, and the hybrid-vs-dense
pair is its own datum). The 4.0-1b pair (1b / h-1b — ADDENDUM 81
CORRECTION: the addendum-78 "nano tier" never existed on the hub, a
phantom from bad web facts; the real ~1B tier is 4.0-1b (dense) and
4.0-h-1b (hybrid-H), both with official Q8_0 GGUF repos, both
GraniteMoeHybridForCausalLM — llama.cpp b10964 support VERIFIED at the
source: the converter registers the arch and the runtime carries
LLM_ARCH_GRANITE_HYBRID) enters under the addendum-78 ceiling —
the whole-lineage rule, no picking and choosing. All values
PRE-REGISTERED (addenda 76/78) under the pooled anchor 0.366 — none
measured yet; the probe-first step may re-anchor per family before
any weights download.

| name | parameters | Q8_0 size (GiB) | ARC (n=1172) | [10–20) wps | [5–10] wps | [20–40) wps |
|---|---|---|---|---|---|---|
| granite-4.2-3b | 3B | 3.21 (P) | pending | — | predicted 6.60 | — |
| granite-4.1-3b | 3.2B | 3.42 (P) | pending | — | predicted 6.28 | — |
| granite-4.0-h-micro | 3B | 3.21 (P) | pending | — | predicted 6.60 | — |
| granite-4.0-micro (the dense fallback; same-size hybrid-vs-dense datum) | 3B | 3.21 (P) | pending | — | predicted 6.60 | — |
| granite-3.3-2b | 2B | 2.14 (P) | pending | — | predicted 8.82 | — |
| granite-3.2-2b | 2B | 2.14 (P) | pending | — | predicted 8.82 | — |
| granite-3.1-2b | 2B | 2.14 (P) | pending | — | predicted 8.82 | — |
| granite-3.0-2b | 2B | 2.14 (P) | pending | — | predicted 8.82 | — |
| granite-4.0-1b (dense ~1B; ADDENDUM 81: replaces the phantom granite-4.0-nano; official Q8_0 1.62 GiB) | 1B | 1.62 (P) | pending | predicted 10.55 | — | — |
| granite-4.0-h-1b (hybrid-H ~1B; ADDENDUM 81: replaces the phantom granite-4.0-h-nano; official Q8_0 1.45 GiB) | 1B | 1.45 (P) | pending | predicted 11.27 | — | — |
| granite-4.0-h-350m | 0.35B | 0.37 (P) | pending | predicted 19.88 — small-end law caveat (the qwen 0.5B measured +25% over prediction) | — | — |
| granite-4.0-350m (the dense 350M twin) | 0.35B | 0.37 (P) | pending | predicted 19.88 — small-end law caveat | — | — |
| granite-4.0-h-small (32B/A9B, line endpoint) | 32B | 34.2 (P) | — | — | FAIL (0.9) | — |

**The pre-registered question this lineage answers:** the four 2B
p05s. If their scatter exceeds Δ = 0.05, generation-owned w/t bottoms
are MEASURED (H1 confirmed on a second lineage, size-fixed); if they
agree within Δ, the class is one and the qwen Δ misses were
family-specific structure. Either result closes an open question.

---

## MiniCPM (OpenBMB — the unmeasured-family ladder, six cells)

The best size spread of the new lineages: a 0.5 → 4B ladder spanning
all three bands in one family — the qwen shape, in a family with NO
measured anchor. This is the pooled anchor 0.366's first multi-size
test: if the family's p05s land far from 0.366, the pooled anchor
needs the per-family calibration the four study-3 families got.
MiniCPM5-2B and MiniCPM5-1B (the newest generation, hybrid
reasoning — run with thinking disabled, rule 8; first-party GGUF
repos) enter under the addendum-78 whole-lineage rule alongside the
measured-paper members; their near-size overlap with MiniCPM-2B-sft /
MiniCPM-1B-sft is a generation-pair datum, not a duplicate (same
size, different generation — the granite quartet's question at half
the cost). All non-thinking or hybrid-run-non-thinking. All values
PRE-REGISTERED (addenda 76/78) — none measured yet. ADDENDUM 81 SPEC
CORRECTIONS (the addendum-78 specs failed the pre-flight): MiniCPM3-4B
ships bin-only in its source repo but has an official
MiniCPM3-4B-GGUF repo with an f16 GGUF (download f16 → pinned
llama-quantize → Q8_0 at 4.03 GiB, provenance preserved); the sft
models' repos are -bf16-suffixed and bin-only (openbmb/MiniCPM-2B-sft-bf16
at 5.45 GB, openbmb/MiniCPM-1B-sft-bf16 at 2.72 GB — the pinned b10964
converter loads pytorch_model.bin natively; the tool's phase-1 .bin
branch is the addendum-81 extension); MiniCPM5-2B/1B are plain
LlamaForCausalLM. Predictions re-derived from the registered constants.

| name | parameters | Q8_0 size (GiB) | ARC (n=1172) | [10–20) wps | [5–10] wps | [20–40) wps |
|---|---|---|---|---|---|---|
| MiniCPM3-4B | 4B | 4.03 (P) | pending | — | predicted 5.52 — SHARP EDGE (band [3.4, 7.7]) | — |
| MiniCPM5-2B | 2.5B | 2.68 (P) | pending | — | predicted 7.55 | — |
| MiniCPM-2B-sft (2.4B non-embedding; ADDENDUM 81: repo is MiniCPM-2B-sft-bf16, pytorch_model.bin) | 2.4B | 2.70 (P) | pending | — | predicted 7.50 | — |
| MiniCPM5-1B | 1.1B | 1.18 (P) | pending | predicted 12.66 | — | — |
| MiniCPM-1B-sft (1.2B non-embedding; ADDENDUM 81: repo is MiniCPM-1B-sft-bf16, pytorch_model.bin) | 1.2B | 1.35 (P) | pending | predicted 11.78 | — | — |
| MiniCPM4-0.5B | 0.5B | 0.54 (P) | pending | predicted 17.85 — small-end law caveat (the qwen 0.5B measured +25% over prediction) | — | — |
| MiniCPM4-8B (line endpoint) | 8B | 8.6 (P) | — | — | FAIL (2.9) | — |

**The pre-registered questions this lineage answers:** (1) the pooled
anchor's first real test across a size ladder — the per-size p05s vs
0.366 grade whether the min-of-calibrated-p05s pooling rule survives
contact with an unmeasured family; (2) the law's cross-family ±15%
band at a fourth family; (3) the small-end t_inf caveat on a second
0.5B model.

---

## Gemma (Google — back in scope, the word-sparse probe)

Ruled back in scope by the author (addendum 77, superseding the
addendum-47 "no debugging" ruling — the re-scope is prospective; the
recorded v3.0-era verdicts stand as history). The family's measured
record is unique in the study: a HEALTHY tokenizer (probes 0.55–0.70)
with WORD-SPARSE content failure (worst turns w/t 0.03–0.29, addendum
46) that is rung-independent — and never yet graded under v3.1. The
right-sized probe is the 1B: predicted comfortably in-band, cheap to
bench, and the answer to the question no other lineage can address —
is the word-sparse failure a 3B-and-up artifact or a family-wide
content property?

| name | parameters | Q8_0 size (GiB) | ARC (n=1172) | [10–20) wps | [5–10] wps | [20–40) wps |
|---|---|---|---|---|---|---|
| gemma-3-4b-it | 4.3B | 4.60 (P) | 73.3 (v3.0-era Q6_K; superseded record) | — | predicted 4.97 (pooled anchor — SHARP EDGE: below the 5.0 line at the corrected 4.3B params, the band's only predicted-FAIL cell; the word-sparse-risk caveat also applies: the family's measured content failure is NOT in any anchor) | — |
| gemma-2-2b (third generation datum) | 2.6B | 2.78 (P) | pending | — | predicted 7.34 (pooled) | — |
| **gemma-3-1b-it (the word-sparse probe)** | 1.0B | 1.07 (P) | pending | predicted 13.31 (pooled) | — | — |

**The question this family would answer (open, unscheduled):** the
1B's v3.1 stall rate and its per-turn w/t distribution. If it stalls
on word-sparse turns at the same corpus points, the family failure is
content-owned and size-independent; if it runs clean, the 3B/4B
failures were size-linked and the family's anchor is rescuable at
small sizes. One cell answers it — the cost/benefit call is the
author's, at probe-first time.
**Caveat on every gemma prediction:** the pooled anchor 0.366 is a
well-behaved-family floor; the gemma family's failure mode (word-sparse
content) is by construction NOT in any anchor — the prediction band
here does not carry the family's known risk, and the bench is the
only instrument that can.
