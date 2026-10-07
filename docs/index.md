# Results — LLMs on 102.4 GB/s system-RAM machines

The f16 context-depth tournament: which small models actually work at which
context depth, certified to 2 sigma. This page is the study's results
dashboard; the [lab notebook](../md/protocol.md) holds the full protocol
and the [picker pages](cpu-picker.html) turn the results into
recommendations.

## Gold medals per context depth

Gold is exclusive per rung: among the models certified at 2 sigma at a
depth, only the one with the **fewest parameters** holds gold.

| Context depth | Gold medal model | Parameters |
|---|---|---|
| 4k | granite-4.0-h-1b | 1.46B |
| 8k | Qwen2.5-1.5B-Instruct | 1.54B |
| 16k | Qwen2.5-1.5B-Instruct | 1.54B |
| 32k | — no gold yet | — |
| 64k | — no gold yet | — |
| 128k | — no gold yet | — |
| 256k | — no gold yet | — |

**Study headline so far:** the certified 2-sigma ceiling on this hardware
class is **16,384 tokens at f16** (Qwen2.5-1.5B-Instruct). 32,768 is
measured but unconquered: the deepest challenger died to the fwe gate at
10/16 (lower bound 0.477 — one hair under the certification bar).

## Gate difficulty (per-cell kill rate)

Cell kill rates under the calibration window (each rung counted up to its
gold medal, addendum 71):

| Gate | Pass bar | Cells | Kill rate |
|---|---|---|---|
| speed | strictly ≥ 5 w/s, 0 stalls | 187 | 3.7% |
| fwe | 2/3 hidden words | 187 | 39.6% |
| vt | 4/5 values traced | 186 | 38.7% |
| arc | 3/5 questions | 168 | 28.0% |

The quality gates sit in a healthy 28–40% kill band: arc easiest, fwe and
vt clustered just under 40%. No difficulty adjustment warranted.

## Verdicts so far

Across the rungs measured to date (4k–32k): 37 dead verdicts, 4 accepts,
2 infeasible (trained window below the first rung — out of the benchmark).
Every family is measured at (f16, f16, f16) to establish maximum quality
before any compression is considered.

## How to read this

- **2 sigma certification**: a model is accepted at a depth only if the
  Wilson 2-sigma lower bound on its per-gate pass rate is ≥ 0.50, with at
  least 10 measured cells per gate at that depth.
- **Gold (addendum 70)**: exclusive per depth — the fewest-parameter
  certified model wins it. Larger certified models keep their confidence
  tier but not gold.
- **The run is live**: verdicts commit and push as they happen; this page
  and the picker gold panel update with every new gold medal.
