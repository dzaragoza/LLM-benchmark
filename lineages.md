# Lineages — the wps bands (T14s predictions)

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

**Machinery (all registered constants):** w/s = law(size) × w/t
anchor. Law (102.4 tier): `1/t = size/76.5 + 1/74` (fitted, R²
0.9996). Qwen-class anchor: p05 0.412 (calibrated n=267, addendum
66; cross-member transfer VALIDATED at gap 0.000, addendum 69 —
one anchor serves the whole lineage). Q8_0 size = params × 1.07
GiB/B (calibrated on the measured 4B file: 4.29 GiB / 4.0B,
addendum 68); measured file sizes supersede estimates where they
exist. The class assignment below the band column derives from the
halving factor 0.50 (pre-registered, addendum 69; its validation
is the 51.2 replication's phase A — until then the band↔class
mapping carries that one unvalidated constant).

**In-band confidence (the trust band, addendum 62):** inside
[5–10], ≥ 5.9 is a trusted PASS and 5.0–5.9 is the marginal zone
where the instrument decides — the two 4B cells sit exactly there,
and the sentinel measured FAIL at s=2 (the honest row below).
Bands above 10 carry no wall risk at n=50 by prediction (their
corpus-min turns sit ≥ 5.07 w/s).

**Provenance markers:** (M) = measured file size on the T14s;
(P) = bpw-derived estimate.

---

## Qwen (the lineage that armed the study)

The line that calibrated the instrument: the 1.5B was study #1's
champion, the 3B study #2's, the 9B study #3's selection, and the
4B was the sentinel that validated Δ and went 5-for-5 through the
predictor (addenda 67–69). The overnight validation run
(addendum 71, pre-registered) benches every predicted-pass cell —
the seven members at or above 5 w/s.

| name | parameters | quant | Q8_0 size (GiB) | [10–20) wps | [5–10] wps | [20–40) wps |
|---|---|---|---|---|---|---|
| Qwen-110B (old series, line endpoint) | ~110B | Q8_0 | 117.7 (P) | — | FAIL (0.3) | — |
| Qwen2.5-72B (line endpoint) | ~72B | Q8_0 | 77.0 (P) | — | FAIL (0.4) | — |
| Qwen3-Coder-30B | ~30B | Q8_0 | 32.1 (P) | — | FAIL (1.0) | — |
| Qwen3.6-27B | ~27B | Q8_0 | 28.9 (P) | — | FAIL (1.1) | — |
| Qwen3.5-9B | ~8.7B | Q8_0 | 9.3 (P, from measured Q5 6.19) | — | FAIL (3.1) | — |
| Qwen2.5-7B-Instruct | 7.62B | Q8_0 | 8.2 (P) | — | FAIL (3.4) | — |
| Qwen3.5-4B | 4.0B | Q8_0 | 4.29 (M) | — | **5.92 — measured FAIL at s=2** † | — |
| Qwen3-4B | 4.0B | Q8_0 | 4.3 (P) | — | 5.93 | — |
| Qwen2.5-3B-Instruct | 3.1B | Q8_0 | 3.62 (M) | — | 6.77 | — |
| Qwen3-1.7B | 1.7B | Q8_0 | 1.8 (P) | 11.05 | — | — |
| Qwen2.5-1.5B-Instruct | 1.5B | Q8_0 | 1.6 (P) | 11.94 | — | — |
| Qwen3.5-0.8B | 0.8B | Q8_0 | 0.9 (P) | 16.68 | — | — |
| Qwen2.5-0.5B-Instruct | 0.5B | Q8_0 | 0.5 (P) | — | — | 20.09 |

† **The sentinel row, honestly stated (addendum 69):** the 4B is the
predicted in-band member (5.92, dead in [5–10]) whose measured
sentinel run FAILED the wall at s=2 — 6 wall-failing turns of 267,
quantile tier ε 1.29 vs 2σ 1.22, short by 0.07. The predictor's
w/s band [5.1, 7.5] was HIT (measured 6.4); the *cone* did not
issue. The verdict-stability finding (addendum 69: deterministic
is verdict-stable, not magnitude-stable) predicts the replicate
FAILS again. Consequence on record: **the qwen-class Q8 roster on
the 102.4 class is EMPTY** — no shipped member both lands in
[5–10] and passes.

**The lineage's shape (the right-sizing read):** each band holds
one family-grid cell of this line. [5–10]: the 3B/4B cells (the
4B measured-fail, the 3B predicted 6.77, never reader-wall-benched
at n=50 — the overnight run measures it). [10–20): the 1.5–1.7B
cells (study #1's champion class) plus the 0.8B. [20–40): the
0.5B alone — the only member that serves the 25.6 class. Below 5:
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
mapping) is pre-registered, not yet validated (addendum 69; the
51.2 replication's phase A). Sizes marked (P) are bpw-derived
estimates (±8% observed, addendum 68). The anchor 0.412 is
corpus-conditional (the w/t tail is substantially corpus-owned,
addendum 69) — these bands are for this reader and corpus class;
generation-side well-behavedness is assumed per the qwen line's
measured record. The overnight run (addendum 71) tests that
assumption across generations: the 2.5 / 3 / 3.5 members' measured
w/t p05s vs the 0.412 anchor is the cross-generation Δ test.
