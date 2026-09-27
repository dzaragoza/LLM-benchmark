# Lineages — Q8_0 verdicts per machine class

One section per family lineage, the study's right-sizing view turned
into a table: every member of the line, at the fixed rung **Q8_0**,
with its predicted reader-wall verdict on both bandwidth classes
(51.2 and 102.4 GB/s). The working question per row: *does this
model serve a practitioner on this machine class, or is it wasting
their hardware?*

**Machinery (all registered constants):** w/s = law(size) × w/t
anchor. Law per class: 102.4 → `1/t = size/76.5 + 1/74` (fitted,
R² 0.9996); 51.2 → BW_eff 34 GiB/s (study-#1-era fit; the v3.0-form
law is not yet fitted there — its refit is the replication's phase
A, addendum 69's pre-registration). Qwen-class anchor: p05 0.412
(calibrated n=267, addendum 66; cross-member transfer VALIDATED at
gap 0.000, addendum 69 — one anchor serves the whole lineage).
Q8_0 size = params × 1.07 GiB/B (calibrated on the measured 4B file:
4.29 GiB / 4.0B, addendum 68); measured file sizes supersede
estimates where they exist.

**Verdicts (the trust band, addendum 62):**

- **PASS** — predicted ≥ 5.9 w/s (trusted PASS, ≥ 2σ above the 5.0
  reader line): the practitioner's model, no bench needed.
- **STRADDLER** — predicted in (4.1, 5.9): the bench decides.
- **FAIL** — predicted ≤ 4.1 w/s (trusted FAIL): exclude.
- **PASS\*** (sub-band) — predicted ≥ 10 w/s: it passes, but it
  also passes on the *lower* class — out of THIS class's scope (the
  author's band ruling: the class roster is the band [5, 10) w/s;
  running a sub-band model wastes the machine, addendum 69). It is
  the lower class's candidate.

**Provenance markers:** (M) = measured file size on the T14s;
(P) = bpw-derived estimate. The 51.2 column is prediction
throughout (its replication has not run); the 102.4 column carries
measured verdicts where a run exists.

---

## Qwen (the lineage that armed the study)

The line that calibrated the instrument: the 1.5B was study #1's
champion, the 3B study #2's, the 9B study #3's selection, and the
4B was the sentinel that validated Δ and went 5-for-5 through the
predictor (addenda 67–69).

| name | parameters | quant | Q8_0 size (GiB) | passes in class 51.2 | passes in class 102.4 |
|---|---|---|---|---|---|
| Qwen-110B (old series, line endpoint) | ~110B | Q8_0 | 117.7 (P) | FAIL (0.1 w/s) | FAIL (0.3 w/s) |
| Qwen2.5-72B (line endpoint) | ~72B | Q8_0 | 77.0 (P) | FAIL (0.2 w/s) | FAIL (0.4 w/s) |
| Qwen3-Coder-30B | ~30B | Q8_0 | 32.1 (P) | FAIL (0.4 w/s) | FAIL (1.0 w/s) |
| Qwen3.6-27B | ~27B | Q8_0 | 28.9 (P) | FAIL (0.5 w/s) | FAIL (1.1 w/s) |
| Qwen3.5-9B | ~8.7B | Q8_0 | 9.3 (P, from measured Q5 6.19) | FAIL (1.5 w/s) | FAIL (3.1 w/s) |
| Qwen2.5-7B-Instruct | 7.62B | Q8_0 | 8.2 (P) | FAIL (1.6 w/s) | FAIL (3.4 w/s) |
| Qwen3.5-4B | 4.0B | Q8_0 | 4.29 (M) | FAIL (3.0 w/s) | **predicted PASS (5.9 w/s) / measured FAIL at s=2** † |
| Qwen3-4B | 4.0B | Q8_0 | 4.3 (P) | FAIL (3.0 w/s) | PASS (5.9 w/s) |
| Qwen2.5-3B-Instruct | 3.1B | Q8_0 | 3.62 (M) | FAIL (3.4 w/s) | PASS (6.8 w/s) |
| Qwen3-1.7B | 1.7B | Q8_0 | 1.8 (P) | PASS (6.2 w/s) | PASS\* (11.1 w/s, sub-band) |
| Qwen2.5-1.5B-Instruct | 1.5B | Q8_0 | 1.6 (P) | PASS (6.8 w/s) | PASS\* (11.9 w/s, sub-band) |
| Qwen3.5-0.8B | 0.8B | Q8_0 | 0.9 (P) | PASS\* (10.7 w/s, sub-band) | PASS\* (16.7 w/s, sub-band) |
| Qwen2.5-0.5B | 0.5B | Q8_0 | 0.5 (P) | PASS\* (14.1 w/s, sub-band) | PASS\* (20.1 w/s, sub-band) |

† **The sentinel row, honestly stated (addendum 69):** the 4B is the
predicted trusted-PASS that sits 0.02 GiB under its class ceiling —
and the measured sentinel run FAILED the strict gate at s=2 (6
wall-failing turns of 267; quantile tier ε 1.29 vs 2σ 1.22, short by
0.07). The predictor's band was [5.1, 7.5] and the measurement
landed 6.4 — a HIT — but the *cone* did not issue. Consequence on
record: **the qwen-class Q8 roster on the 102.4 class is EMPTY**
(the 0.8B is sub-band, the 4B wall-fails). The family's value on
that machine lives at Q5_K_M (the 9B), not at Q8.

**The lineage's shape (the right-sizing read):** the passable
window per class is one family-grid cell wide. On 102.4 at Q8, the
in-band members are the 4B-class and the 3B (predicted PASS, the 3B
never reader-wall-benched at n=50); everything ≥ 7B fails, and
everything ≤ 1.7B belongs to the 51.2 class. On 51.2, the in-band
members are the 1.5–1.7B cells — exactly the study-#1 champion class,
predicted by the same machinery 5 years of model generations later.
The lineage's grids (0.5 / 1.5 / 3 / 4 / 7–9 / 27–30 / 72+) quantize
coarser than either machine's window: the right-size member is
never the flagship (addendum 58's pattern, now visible per class).

**Sub-band cascade (the class-exclusive structure, addendum 65):**
each model serves exactly one class — the smallest class on which
it is in-band. The 1.5B/1.7B cells are the 51.2 class's roster; the
3B/4B cells are the 102.4 class's; the 9B is a Q5_K_M model of the
102.4 class (its Q8 file fails); nothing above 9B serves either
class at any ladder rung (the 12–14B class needs ~2× 102.4's
bandwidth — the next machine up).

**Caveats on record:** every 51.2 verdict is prediction pending the
replication's law refit (phase A) — the halving factor 0.50, ceiling
ratio 2.25, and band disjointness [2.12, 5.27] vs [0.94, 2.34] GiB
are pre-registered (addendum 69). Sizes marked (P) are bpw-derived
estimates (±8% observed, addendum 68). The anchor 0.412 is
corpus-conditional (the w/t tail is substantially corpus-owned,
addendum 69) — these verdicts are for this reader and corpus class;
generation-side well-behavedness is assumed per the qwen line's
measured record.
