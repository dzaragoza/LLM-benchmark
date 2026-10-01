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

| RWKV7-World-2.9B | Q8_0 | n/a | n/a | 3.03 | 4.13 GiB | ~8 | THE RECURRENT FAMILY (addendum 23): constant-size state - no KV growth at all, context bounded only by the machine; conversational chat tune, first-party RWKV org weights, Goose paper (arXiv 2504.03289, verified), community GGUF verified (mradermacher Q8_0 3.03 GiB); risks: llama.cpp rwkv7 support level, FWE-through-recurrent-state unproven, community GGUF not first-party quant |
| RWKV7-World-2.9B | Q6_K | n/a | n/a | 2.39 | 3.49 GiB | ~9 | the same model at Q6_K (multi-config exception): 70% of ceiling, headroom config under the Jamba Q8_0 |

## REJECTED

Strict reason list (author ruling, addendum 21, extended addendum 23):
no research paper | no model small enough (q2, q4, q4) > ceiling |
training window < 256k | thinking cannot be disabled | other. A model
is rejected on the FIRST reason that binds in the fair-chance order:
if even the floor config (Q2_K + K/V q4_0/q4_0) predicts RAM above the
4.96 GiB ceiling, the size binds; if the RAM fits but the trained
window is under 262,144 (no rope scaling), the window binds; thinking
tunes whose reasoning cannot be turned off close as thinking cannot
be disabled; everything else is other. BASE variants of an
already-instruct model are not recorded (author ruling, addendum 23):
the type rule implies their rejection - the instruct tune is the
family's one entry.

| model name | rejection reason | notes |
|---|---|---|
| Qwen3.5-9B | no model small enough (q2, q4, q4) > ceiling | best config Q2_K + q4_0/q4_0 = 7.05 GiB predicted; the family closes at 9B |
| gemma-4-e2b-it | training window < 256k | trained window 131,072 (verified from config.json); no rope scaling by standing rule |
| Ministral 3B | other | the repo does not exist on the hub (author-authenticated pull: RepositoryNotFoundError; the agent's unauthenticated 401 masked it); no first-party Ministral-3B weights to screen |
| Qwen2.5-1.5B-Instruct | training window < 256k | window 32,768; the RAM would fit (1.97 GiB q4_0 KV at 262k) - the window is the wall; v4.3 score 20,992 @ Q8_0 |
| Qwen3-1.7B | no model small enough (q2, q4, q4) > ceiling | KV 112 KiB/token -> q4_0 KV alone ~7.9 GiB > 4.96; window 40,960 and FWE broken at 40,704 besides |
| Qwen3-4B | no model small enough (q2, q4, q4) > ceiling | KV 144 KiB/token -> ~10.1 GiB q4_0 KV; window 40,960 besides |
| phi-4-mini-instruct | no model small enough (q2, q4, q4) > ceiling | KV 128 KiB/token -> ~9.0 GiB q4_0 KV; window 131,072; the deepest non-Qwen3.5 score (44,032 @ Q4_K_M) is 6x short |
| Phi-3.5-mini-instruct | no model small enough (q2, q4, q4) > ceiling | KV 384 KiB/token -> ~27 GiB q4_0 KV; FWE zero at Q4_K_M |
| Phi-3-mini-4k-instruct | no model small enough (q2, q4, q4) > ceiling | KV 384 KiB/token -> ~27 GiB q4_0 KV; window 4,096 |
| phi-1 | training window < 256k | window 2,048; base/code model (type rule) - far under the 16k screen |
| phi-2 | no model small enough (q2, q4, q4) > ceiling | KV 320 KiB/token -> ~22.5 GiB q4_0 KV; window 2,048 besides |
| granite-3.0-2b-instruct | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 4,096; 4,096-class score |
| granite-3.1-2b-instruct | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; Q4 counting fell off the cliff (12,288 -> 6,144) |
| granite-3.2-2b-instruct | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; score 15,360 |
| granite-3.3-2b-instruct | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; score 26,624 |
| granite-4.0-350m | training window < 256k | window 32,768; RAM would fit (1.97 GiB q4_0 KV); never passed the 16k screen on the f4k grid (quality) |
| granite-4.0-h-350m | training window < 256k | window 32,768; RAM would fit (2.25 GiB q4_0 KV); never passed the 16k screen (quality) |
| granite-4.0-1b | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072 |
| granite-4.0-micro | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; MoE hybrid |
| granite-4.0-h-micro | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; MoE hybrid |
| granite-4.0-h-1b | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; MoE hybrid |
| granite-4.1-3b | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; score 18,432 |
| granite-4.2-3b | no model small enough (q2, q4, q4) > ceiling | KV 80 KiB/token -> ~5.6 GiB q4_0 KV; window 131,072; also corrupted f16 file in the Q4 resume |
| MiniCPM-1B-sft | no model small enough (q2, q4, q4) > ceiling | KV 104 KiB/token -> ~7.3 GiB q4_0 KV; window 4,096; 4,096-class score |
| MiniCPM-2B-sft | no model small enough (q2, q4, q4) > ceiling | KV 360 KiB/token -> ~25.3 GiB q4_0 KV; window 4,096 |
| MiniCPM3-4B | no model small enough (q2, q4, q4) > ceiling | KV 620 KiB/token -> ~43.6 GiB q4_0 KV; window 32,768 |
| MiniCPM4-0.5B | training window < 256k | window 32,768; RAM would fit (0.84 GiB q4_0 KV); never passed the 16k screen (quality) |
| MiniCPM5-1B | training window < 256k | window 131,072; RAM would fit (1.69 GiB q4_0 KV) - the window is the wall |
| MiniCPM5-2B | training window < 256k | window 131,072; RAM would fit (~4.2 GiB whole config at q4_0 KV) - the window is the wall; also FWE zero at Q4_K_M |
| AI21-Jamba-Reasoning-3B | thinking cannot be disabled | the reasoning tune has no non-thinking mode; same 262,144 window and thin KV as Jamba2-3B but the wrong shape for the gates |
| AI21-Jamba2-Mini | no model small enough (q2, q4, q4) > ceiling | 12B MoE (16 experts, 2 active): Q2_K weights alone ~4.75 GiB, over the ceiling before KV; window 262,144 |
| openai/gpt-oss-20b | training window < 256k | window 131,072; KV 48 KiB/token (3.38 GiB q4_0 KV at 262k) - window binds first (addendum-20 sweep) |
| HuggingFaceTB/SmolLM3-3B | training window < 256k | window 65,536; KV 72 KiB/token -> ~5.1 GiB q4_0 KV would also exceed the ceiling |
| tencent/Hunyuan-A13B-Instruct | training window < 256k | window 32,768; MoE |
| LGAI-EXAONE/EXAONE-4.0-32B | training window < 256k | window 131,072; KV 256 KiB/token (~18 GiB q4_0 KV) would also exceed the ceiling |
| inclusionAI/Ling-lite-1.5B | training window < 256k | window 32,768 (addendum-20 sweep) |
| zai-org/GLM-4.5-Air | training window < 256k | window 131,072 |
| meta-llama/Llama-3.2-1B-Instruct | training window < 256k | window 131,072 (author-verified from the gated repo); RAM would fit - KV 32 KiB/token f16 (16 layers x 8 kv heads x 64 head_dim) -> ~2.25 GiB q4_0 KV, whole config ~3.75 GiB - the window is the wall |
| meta-llama/Llama-3.1-8B-Instruct | other | gated (HTTP 401); 128k-class window |
| google/gemma-3-1b-it | training window < 256k | window 32,768 (author-verified); 1 kv head - thin KV, but the window binds hard |
| google/gemma-3-4b-it | training window < 256k | window 131,072 class (the author's pull shows the config nests it in text_config - the gemma-3 wrapper; text models are 128k per the model card) |
| Qwen3-30B-A3B-Instruct-2507 | no model small enough (q2, q4, q4) > ceiling | window 262,144 but MoE: Q2_K weights alone far over the ceiling; KV 96 KiB/token -> 6.75 GiB q4_0 KV besides |
| Qwen3-4B-Instruct-2507 | no model small enough (q2, q4, q4) > ceiling | window 262,144 but KV 144 KiB/token -> ~10.1 GiB q4_0 KV (the 2507 refresh dropped the hybrid interval) |
| DSpark/EAGLE3 draft heads (RadixArk, z-lab, incoai, lightseekorg, Inferact, skt repos) | other | speculative-decoding DRAFT MODELS, not instruct models - sweep false positives, never candidates |
| community finetunes (NeoHorse-1-4B, JevK5, test tinies, reformer) | other | rule 5 (first-party weights) / not instruct models - sweep false positives |
