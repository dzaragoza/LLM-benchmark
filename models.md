# models.md — The Model Registry

Every model the 256k screen has touched, in one place: the passes,
the fails, and the candidates with predicted values. Updated with
every probe; the lab notebook carries the full narrative.

RAM = cold whole-stack machine cost (MemAvailable delta) at depth
262,144. w/s = the scored-rung worst turn. Predictions use the
registered ceiling predictor (MODEL-SELECTION.md rule 2):
`cost = file(rung) + KV_eff(262144) x kvquant + 1.10 GiB`.

TYPE RULE (author ruling, session 35 addendum 18): only INSTRUCT
models are suited to this benchmark - both gates are
instruction-shaped (the speed gate is a live conversation with a
following reader; FWE is an instruction-following extraction task).
One type per model in the whole document: the instruct tune; base
(pretrained) variants are rejected on type, not re-evaluated.

ONE-MODEL-ONE-TABLE, with the author's exception (addendum 20): a
model appears at most once per table, in exactly one table - EXCEPT
the CANDIDATES table, where a model may appear MULTIPLE TIMES, once
per settings configuration (a candidate is a model+configuration
pair, not a model).

---

## PASS (both gates at 262,144)

| model name | model quant | k quant | v quant | model size GiB | RAM | w/s | notes |
|---|---|---|---|---|---|---|---|
| Qwen3.5-0.8B | Q8_0 | f16 | f16 | 0.86 | 4.96 GiB | 9.3 | THE CHAMPION; sets the 4.96 GiB ceiling; trained window 262,144; speed PASS zero stalls, FWE 3/3 at 261,888 |
| Qwen3.5-2B | Q4_K_M | q5_0 | q5_0 | 1.22 | 3.48 GiB | 9.5 | the RAM champion (half the champion's cost); speed PASS 15.2 t/s worst turn, FWE 3/3; pending its quant-raise re-probe (Q8_0 + q8_0/q8_0, predicted 4.78 GiB — 96% of ceiling) |

## FAIL

| model name | model quant | k quant | v quant | model size GiB | RAM | w/s | reason for failure |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## CANDIDATES (predicted values)

| model name | model quant (predicted) | k quant (predicted) | v quant (predicted) | model size GiB (predicted) | RAM (predicted) | w/s (predicted) | prediction notes |
|---|---|---|---|---|---|---|---|
| Qwen3.5-4B | Q2_K | q4_0 | q4_0 | 1.60 | 4.95 GiB | ~5 | THE EDGE: 100% of ceiling, RAM PASS by 0.01 GiB; speed straddler (the 4B wall was 6.07 w/s at 131k with f16 KV); Q2_K quality the wild card |
| AI21-Jamba2-3B | Q8_0 | f16 | f16 | 3.17 | 4.52 GiB | ~7 | THE NEW FAMILY (addendum 20): window 262,144; hybrid mamba-attention, only 2 full-attention layers x 1 KV head x 128 head_dim -> ~1 KiB/token f16 (0.25 GiB at 262k), the thinnest KV ever screened - the mamba state is constant-size; Q8_0 at 91% of ceiling; non-thinking instruct, Apache-2.0, GGUF tooling verified (bartowski 3.17 GiB); risks: llama.cpp jamba-arch support level, FWE at depth unproven |
| AI21-Jamba2-3B | Q6_K | f16 | f16 | 2.46 | 3.81 GiB | ~8 | the same model at Q6_K (the addendum-20 multi-config exception): 77% of ceiling, headroom if the Q8_0 run grazes the ceiling; probe only if the Q8_0 config passes or the ceiling measurement surprises |

## REJECTED

| model name | reason for rejection |
|---|---|
| Qwen3.5-0.8B-Base | identical RAM geometry to the champion 0.8B already measured (Q8_0 + f16, 4.96 GiB); only the tuning differs - not worth an hour (addendum 14) |
| Qwen3.5-9B | no configuration fits under the 4.96 GiB ceiling (best: Q2_K + q4_0/q4_0 = 7.05 GiB predicted) - the family closes at 9B |
| gemma-4-e2b-it | trained window 131,072 < 262,144 (verified from config.json); no rope scaling by standing rule |
| Ministral 3B | gated repo (HTTP 401) and 128k-class window |
| Qwen3.5-2B-Base | BASE type, not instruct (addendum 18): the benchmark is conversation- and instruction-shaped (the speed gate is a live conversation, FWE is an instruction-following task); the instruct 2B is already PASS - only one type per model |
| Qwen3.5-4B-Base | BASE type, not instruct (addendum 18): same reason; the instruct 4B is the candidate the study probes |
| MiniCPM5-2B-Base | BASE type, not instruct (addendum 18); the addendum-20 sweep found its config declares a 524,288 window - the only sub-ceiling-RAM window > 262,144 in the whole hub sweep - but the type rule closes it: the instruct MiniCPM5-2B (window 131,072) is the family's one type and it is already rejected on window |
| AI21-Jamba-Reasoning-3B | THINKING model (rule 3: the study carries non-thinking only); same 262,144 window and thin KV as Jamba2-3B but the reasoning tune is the wrong shape for the gates |
| AI21-Jamba2-Mini | 12B MoE (16 experts, 2 active): Q2_K weights alone ~4.75 GiB, over the ceiling before KV; window 262,144 and non-thinking, but no configuration fits |
| Qwen2.5-1.5B-Instruct | retro-analysis (addendum 19): trained window 32,768 < 262,144, no rope scaling; v4.3 score 20,992 @ Q8_0 - the RAM would fit (1.97 GiB q4_0 KV at 262k), the window is the wall |
| Qwen3-1.7B | retro-analysis (addendum 19): KV geometry 112 KiB/token f16 -> q4_0 KV alone ~7.9 GiB > 4.96 ceiling (plus window 40,960 and FWE broken at 40,704) |
| Qwen3-4B | retro-analysis (addendum 19): KV 144 KiB/token -> q4_0 KV ~10.1 GiB, triple the ceiling; window 40,960 besides |
| phi-4-mini-instruct | retro-analysis (addendum 19): KV 128 KiB/token -> q4_0 KV ~9.0 GiB > ceiling; window 131,072 (the deepest non-Qwen3.5 score, 44,032 @ Q4_K_M, is 6x short of the goal) |
| Phi-3.5-mini-instruct | retro-analysis (addendum 19): KV 384 KiB/token -> q4_0 KV ~27 GiB, 5x the ceiling; window 131,072; also FWE zero at Q4_K_M |
| Phi-3-mini-4k-instruct | retro-analysis (addendum 19): window 4,096; KV 384 KiB/token -> ~27 GiB q4_0 KV at 262k |
| phi-1 | retro-analysis (addendum 19): window 2,048; base/code model (type rule); far under the 16k screen |
| phi-2 | retro-analysis (addendum 19): window 2,048; KV 320 KiB/token -> ~22.5 GiB q4_0 KV at 262k |
| granite-3.0-2b-instruct | retro-analysis (addendum 19): window 4,096; KV 80 KiB/token -> ~5.6 GiB q4_0 KV; 4,096-class score |
| granite-3.1-2b-instruct | retro-analysis (addendum 19): window 131,072 < 262,144; KV 80 KiB/token -> ~5.6 GiB q4_0 KV > ceiling; Q4 counting fell off the cliff (12,288 -> 6,144) |
| granite-3.2-2b-instruct | retro-analysis (addendum 19): window 131,072; KV 80 KiB/token -> ~5.6 GiB q4_0 KV > ceiling; score 15,360 |
| granite-3.3-2b-instruct | retro-analysis (addendum 19): window 131,072; KV 80 KiB/token -> ~5.6 GiB q4_0 KV > ceiling; score 26,624 |
| granite-4.0-350m | retro-analysis (addendum 19): window 32,768; never passed the 16k screen on the f4k grid (quality) |
| granite-4.0-h-350m | retro-analysis (addendum 19): window 32,768; never passed the 16k screen on the f4k grid (quality) |
| granite-4.0-1b | retro-analysis (addendum 19): window 131,072; KV 80 KiB/token -> ~5.6 GiB q4_0 KV > ceiling |
| granite-4.0-micro | retro-analysis (addendum 19): window 131,072; KV 80 KiB/token -> ~5.6 GiB q4_0 KV > ceiling; MoE hybrid |
| granite-4.0-h-micro | retro-analysis (addendum 19): window 131,072; KV 80 KiB/token -> ~5.6 GiB q4_0 KV > ceiling; MoE hybrid |
| granite-4.0-h-1b | retro-analysis (addendum 19): window 131,072; KV 80 KiB/token -> ~5.6 GiB q4_0 KV > ceiling; MoE hybrid |
| granite-4.1-3b | retro-analysis (addendum 19): window 131,072; KV 80 KiB/token -> ~5.6 GiB q4_0 KV > ceiling; score 18,432 |
| granite-4.2-3b | retro-analysis (addendum 19): window 131,072; KV 80 KiB/token -> ~5.6 GiB q4_0 KV > ceiling; also corrupted f16 file in the Q4 resume, out of that sweep |
| MiniCPM-1B-sft | retro-analysis (addendum 19): window 4,096; sft = instruct-tuned (type OK) but KV 104 KiB/token -> ~7.3 GiB q4_0 KV > ceiling; 4,096-class score |
| MiniCPM-2B-sft | retro-analysis (addendum 19): window 4,096; KV 360 KiB/token -> ~25.3 GiB q4_0 KV; 4,096-class score |
| MiniCPM3-4B | retro-analysis (addendum 19): window 32,768 (no usable rope scaling); KV 620 KiB/token -> ~43.6 GiB q4_0 KV |
| MiniCPM4-0.5B | retro-analysis (addendum 19): window 32,768; KV 12 KiB/token (RAM would fit) but never passed the 16k screen on the f4k grid (quality) |
| MiniCPM5-1B | retro-analysis (addendum 19): window 131,072 < 262,144; RAM would fit (1.69 GiB q4_0 KV) but the window is the wall (no rope scaling by rule) |
| MiniCPM5-2B | retro-analysis (addendum 19): window 131,072; KV 42 KiB/token -> 2.95 GiB q4_0 KV, weights+KV+overhead ~4.2 GiB - would fit, but the window is the wall; also FWE zero at Q4_K_M |
