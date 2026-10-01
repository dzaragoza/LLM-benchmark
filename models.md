# models.md — The Model Registry

Every model the 256k screen has touched, in one place: the passes,
the fails, and the candidates with predicted values. Updated with
every probe; the lab notebook carries the full narrative.

RAM = cold whole-stack machine cost (MemAvailable delta) at depth
262,144. w/s = the scored-rung worst turn. Predictions use the
registered ceiling predictor (MODEL-SELECTION.md rule 2):
`cost = file(rung) + KV_eff(262144) x kvquant + 1.10 GiB`.

---

## PASS (both gates at 262,144)

| model name | model quant | k quant | v quant | model size GiB | RAM | w/s | notes |
|---|---|---|---|---|---|---|---|
| Qwen3.5-0.8B | Q8_0 | f16 | f16 | 0.86 | 4.96 GiB | 9.3 | THE CHAMPION; sets the 4.96 GiB ceiling; trained window 262,144; speed PASS zero stalls, FWE 3/3 at 261,888 |
| Qwen3.5-2B | Q4_K_M | q5_0 | q5_0 | 1.22 | 3.48 GiB | 9.5 | the RAM champion (half the champion's cost); speed PASS 15.2 t/s worst turn, FWE 3/3; quant-raise candidate |

## FAIL

| model name | model quant | k quant | v quant | model size GiB | RAM | w/s | reason for failure |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## CANDIDATES (predicted values)

| model name | model quant (predicted) | k quant (predicted) | v quant (predicted) | model size GiB (predicted) | RAM (predicted) | w/s (predicted) | prediction notes |
|---|---|---|---|---|---|---|---|
| Qwen3.5-2B | Q8_0 | q8_0 | q8_0 | 2.09 | 4.78 GiB | ~8 | 96% of ceiling; the 2B quant raise to the best-under-ceiling config; RAM PASS, speed PASS expected (9.5 w/s at Q4_K_M leaves margin) |
| Qwen3.5-0.8B-Base | Q8_0 | f16 | f16 | 0.81 | 4.91 GiB | ~9.3 | SUPERSEDED (author ruling): identical config to the champion 0.8B already measured (4.96 GiB, 9.3 w/s) — only the tuning differs; not re-run |
| Qwen3.5-2B-Base | Q8_0 | q8_0 | q8_0 | 2.09 | 4.78 GiB | ~8 | 96% of ceiling; base model — FWE at depth unproven, that risk is the experiment |
| Qwen3.5-4B | Q2_K | q4_0 | q4_0 | 1.60 | 4.95 GiB | ~5 | THE EDGE: 100% of ceiling, RAM PASS by 0.01 GiB; speed straddler (the 4B wall was 6.07 w/s at 131k with f16 KV); Q2_K quality the wild card |
| Qwen3.5-4B-Base | Q2_K | q4_0 | q4_0 | 1.60 | 4.95 GiB | ~5 | same floor config on the base weights; the addendum-10 hypothesis test (match the 0.8 footprint, does the 4B pass?) |
| Qwen3.5-9B | Q2_K | q4_0 | q4_0 | 3.72 | 7.05 GiB | ~3 | OVER CEILING — listed to close the family: no 9B config fits under 4.96 GiB |
| gemma-4-e2b-it | Q4_K_M | q4_0 | q4_0 | ~0.9 | ~3.5 GiB | ~9 | WINDOW-DISQUALIFIED: max_position_embeddings 131,072 < 262,144 (verified from config.json); no rope scaling by standing rule |
