# Pick your model — V7 reach benchmark

A **fixed memory budget of 4 GiB** (GPU footprint), one fixed benchmark corpus, every model competing on how much context it can *use*: how many facts it still finds when they live deep in the window. The score is credit — the fraction of variable-tracking names recovered, averaged per (span, hops) grade — so partial recall earns partial credit, and a bigger window only pays when the model converts it.

The deliverable: given the budget, the **best (model, context, quantization) allocation**.

## The winner — the argmax at 4 GiB

- **Model**: Qwen3.5-2B (Q8_0 weights, q8_0 K cache, q5_0 V cache)
- **Context**: 262,144 tokens — the full grid depth
- **Score**: 6.88 of 30 — the reach curve was still rising at the top
- **GPU memory**: 3.84 GiB estimated

```bash
llama-server -m Qwen3.5-2B-Q8_0.gguf -c 262144 --cache-type-k q8_0 --cache-type-v q5_0 -fa on --parallel 1
```

## The ranking (all scored families)

| rank | model | best context | score | the curve |
|---|---|---|---|---|
| 1 | Qwen3.5-2B | 256k | 6.88/30 | 8k → 16k → 32k → 64k → 128k → 256k |
| 2 | Qwen3.5-0.8B | 128k | 4.50/25 | 8k → 16k → 32k → 64k → 128k → 256k |
| 3 | Qwen3-1.7B | 32k | 2.45/15 | 8k → 16k → 32k |
| 4 | granite-3.1-2b-instruct | 32k | 2.27/15 | 8k → 16k → 32k → 64k → 128k |
| 5 | Qwen2.5-1.5B-Instruct | 32k | 1.70/15 | 8k → 16k → 32k |
| 6 | MiniCPM4-0.5B | 32k | 1.42/15 | 8k → 16k → 32k |
| 7 | MiniCPM5-2B | 128k | 1.19/25 | 8k → 16k → 32k → 64k → 128k |
| 8 | granite-4.0-350m | 16k | 0.09/10 | 8k → 16k → 32k |
| 9 | granite-4.0-h-350m | 8k | 0.09/5 | 8k → 16k → 32k |
| 10 | MiniCPM5-1B | 8k | 0.00/5 | 8k → 16k → 32k → 64k → 128k |
| 11 | granite-4.0-1b | 8k | 0.00/5 | 8k → 16k → 32k |

**How to read the curve column**: each cell lists the context rungs measured (8k → 262k where the trained window allows). Scores rise with context for every model that can afford it — *context buys more than quantization costs* — until the KV cache tax starves the weights; Qwen3.5-0.8B and granite-3.1 peak mid-grid and decline, Qwen3.5-2B does not peak yet.

## Findings — the families that cannot compete

The candidates are all roster families, the first 16 by parameter count. Four of them cannot earn a cell — findings, not failures of the run:

| family | why it cannot run |
|---|---|
| gemma-3-1b-it | missing registry extract — KV geometry unknowable (recoverable: refresh the registry) |
| Llama-3.2-1B-Instruct | missing registry extract (gated repo; recoverable) |
| MiniCPM-1B-sft | trained window 4,096 below the grid's smallest rung (8,192) |
| phi-1 | trained window 2,048 below the grid |

Two models measured zero with evidence recorded — the granite-4.0 hybrids answer the *value* instead of the variable names and template-mangled models echo instead of answering; both classes are **labelled, not scored 0** (their answer logs are in the results tree).

## What the numbers mean

- **Score** — credit: each question asks for the variable names in a chain hidden deep in the context; a grade's rate is the average of found/(hops+1) over its questions, summed over the grades that fit the model's window.
- **Unreachable grades are excluded, not failed** — a bigger window strictly raises the attainable maximum, so reach only pays when converted.
- **Reproducibility**: one fixed corpus (seed 1), temperature 0, per-question derived seeds; every answer is logged (one JSON line per question).
