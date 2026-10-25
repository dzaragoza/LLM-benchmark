# Randomizer recommendations — draft (data: 774 draws, 537 measured candidates)

The randomizer's one-chance-per-candidate protocol on the 2048 pool
(roster × LADDER) has produced a uniformly-sampled map of the
(model, quant) space under the exam protocol (128 s per level, both
parts). This is a DRAFT built from the current ledger; the run
continues and every number below is regenerable from
`state/randomizer-state.json`.

The machine context: AMD Radeon 780M iGPU (Vulkan, shared memory),
~120 GB/s theoretical memory bandwidth. The prior study
(`reports/small-models-big-claims-markdown-edition.md`) validated
**throughput ≈ effective memory bandwidth ÷ model file size** with a
family-dependent error of ±10–15% on this class of hardware. That
formula is the bridge between "file size" and "machine" used below.

## For practitioners: the top candidate per speed class

Rank: highest exam score, tiebreak by time. Speed class = the
candidate's whole run (fast ≤ 32 s, medium ≤ 64 s, slow ≤ 128 s).

| speed class | model | quant | score | file (GiB) | time |
|---|---|---|---|---|---|
| fast | gemma-2-2b-it | Q4_K_M | 6 | ~1.5 | 19 s |
| medium | granite-4.1-3b | Q5_0 | 7 | ~2.2 | 36 s |
| slow | gemma-3-4b-it | Q4_K_S | 4 | ~2.3 | 128 s |

Reading of the table:

- **The medium class carries the best candidate found so far**
  (granite-4.1-3b Q5_0, score 7). If you can tolerate ~35 s to first
  answer, that is the pick.
- **Fast does not mean weak**: gemma-2-2b-it Q4_K_M reached 6 in
  under 20 s — the best quality-per-second measured.
- **Slow adds nothing**: the slow-class leader scores 4, below both
  faster picks. On this machine class, waiting longer than ~64 s
  bought no quality in the current data; candidates that need the
  full 128 s mostly time out at the next level anyway.
- The sweet spot is consistent: every named candidate sits in the
  **1.5–2.5 GiB** size band (2.5–3.4 B params at Q4–Q5).

## For researchers: the search bias

### What the data says (n = 537 measured candidates)

| signal | vs score | note |
|---|---|---|
| file size (GiB), pooled | r = +0.24, ρ = +0.29 | significant but confounded |
| quant bits-per-weight | ρ = +0.35 | stronger than params! |
| params (B), pooled | ρ = +0.10 | nearly nothing pooled |
| file size within-family | median r = +0.23, 25/34 positive | the quant gradient is real |
| file size given no-timeout | mean +1.52 (>2 GiB) vs −0.59 (≤1 GiB) | the capability leg is strong |

Score probability by estimated file size:

| size band | n | P(score ≥ 0) | P(score ≥ 2) | timeout rate |
|---|---|---|---|---|
| ≤ 0.5 GiB | 139 | 0.13 | 0.01 | 0.42 |
| 0.5–1 GiB | 169 | 0.21 | 0.04 | 0.53 |
| 1–1.5 GiB | 110 | 0.36 | 0.07 | 0.54 |
| 1.5–2 GiB | 68 | 0.34 | 0.13 | 0.44 |
| 2–2.5 GiB | 30 | **0.60** | **0.33** | 0.43 |
| > 2.5 GiB | 21 | 0.38 | 0.14 | **0.62** |

The two mechanisms separate cleanly:

1. **A capability floor** — below ~1 GiB the model/quant combination
   is usually *unable* to follow the chain at all (95%+ fail), even
   when it finishes in time. This is where quants destroy small
   models and tiny params never learned the task.
2. **A bandwidth ceiling** — above ~2.5 GiB on THIS machine the
   timeout rate climbs (0.62) and scores fall: the candidate cannot
   generate fast enough for the bell. This ceiling is a machine
   property, not a model property: it moves with memory bandwidth.

### The bias: size-banded sampling with a bandwidth-derived ceiling

Do NOT weight by model (lineage is a strong prior but it freezes the
search to today's winners). Weight by the ONE variable that encodes
both parameters and quant AND interacts with the machine: the file
size in GiB, computed as `params × bpw / 16` from the roster before
any download.

Given the machine's effective memory bandwidth `BW` (GB/s) and the
minimum tokens/second `t_min` the task needs to finish inside its
deadline, the size ceiling is:

```
S_max = BW / t_min          (e.g. ~120 / 30 ≈ 4 GiB on this class)
```

Then sample candidates with weights by size band:

```
w(S) = 0        if S > S_max              (cannot beat the clock)
w(S) = S        if 0.5 GiB <= S <= S_max  (probability scales with size)
w(S) = 0        if S < 0.5 GiB            (capability floor)
```

Rationale from the table: P(score ≥ 2) grows monotonically with size
up to the bandwidth ceiling (1% → 4% → 7% → 13% → 33%), then
collapses (14%) as the timeout rate takes over. A linear-in-size
weight approximates that gradient. For this machine the expected
sweet band is 1.5–S_max GiB; the empirical optimum so far is 2–2.5
GiB with the ceiling biting above ~2.5 GiB.

### The recommended search algorithm (biased randomizer)

Keep the one-chance-per-candidate randomizer — it is unbiased,
resumable, and self-documenting — and change only the draw:

1. Precompute every candidate's file size from
   `params × bpw / 16` (no downloads).
2. Zero-weight candidates outside `[0.5 GiB, S_max]`.
3. Draw with probability proportional to `min(S, 2.5) /
   sum(weights)` — linear up to the empirically-best band, flat
   beyond it, so the ceiling region is still explored but not
   oversampled.
4. Rebuild the weights from the ledger every K draws: whenever a
   band's realized hit rate (score ≥ 2) diverges from its weight by
   more than 2σ, adjust the weight toward the realized rate. This
   makes the bias self-correcting per machine instead of hardcoded.
5. Optional family prior as a multiplier, capped (e.g. ×2 max) so a
   dominant lineage (granite-4.x, gemma-2/3 today) steers the search
   without ever excluding newcomers.

### Why this minimizes search time

Under uniform sampling, 537 draws produced 38 candidates (7%) with
score ≥ 2. The size-band table implies that restricting draws to the
1.5–2.5 GiB band alone (n = 99 in the current data) would have
raised the hit rate to ~19% — roughly 2.7× fewer wasted draws — and
adding the family prior pushes it further (granite-4.1-3b alone hit
7/13 at score ≥ 2). The bandwidth input costs one number per
machine, and the formula's ±10–15% error is small next to the
orders-of-magnitude gradient in the size table.

## Caveats

- Single machine class (iGPU, shared memory); the ceiling is
  bandwidth-relative and must be re-derived per machine via `S_max`.
- One exam protocol (chain-following, 128 s/level); the capability
  floor could sit elsewhere for other task families.
- The > 2.5 GiB band is thin (n = 21) because of the 8 GiB f16
  gate; the ceiling estimate will sharpen as the pool fills.
- Params and bpw are currently estimated from the roster table, not
  measured per file; measurement would tighten the band edges.
