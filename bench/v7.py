"""bench.v7 -- the fixed-budget reach benchmark (session 42's reframe).

The design (addendum 98): one fixed VT corpus at 256k tokens serves
every contender; questions are graded by (span, hops) - span is the
REACH axis (a window W < span is a structural fail), hops is the
REASONING axis (degrades gracefully). Model selection is the greedy
(q, k, v) climb from (2,2,2) toward the fixed memory budget
(session 43's ruling; K-encoding below q8, top at 16 bits). The
deliverable: the argmax cell - one model, one ctx, one
recommendation - with the speed gate as the certification step.

This module carries the v7 pieces that live in the full_benchmark
world: the allocation ladders, the greedy climb, the corpus builder,
the graded scorer, and the per-cell controller (acquire via the
certify phase-1/2 path, launch in the bench.cells shape, state in
the families/<name> tree of full_benchmark's state file).
READING A SCORE (session 44, addendum 131 - the author kept the
scoring; it needs explanation because it is counter-intuitive):

  credit   found / (h+1) per question - how far down the chain
           the answer got; 1.0 = the full chain. A grade's rate is
           its mean credit (one question per grade: the grade credit).
  score    SUM of grade credits over the REACHABLE grades. Each
           reachable grade contributes at most 1.0, so
           max_score (the grade count) is the natural ceiling.
  max_score  how many (span, hops) grades fit the window - the
           reachable breadth. Reach is monotone: a bigger ctx
           window contains every grade a smaller one has, plus more.

Consequences (all intended, none a bug):

  - raw score never decreases with ctx: extra context can only
    ADD grades, never remove them. Comparing raw sums across ctx
    ranks reachable breadth, not quality.
  - score / max_score is the per-grade completion RATE - the
    quality view. It can fall as ctx grows: the added grades are
    harder spans and dilute the average (MiniCPM4-0.5B live:
    0.098 -> 0.064 -> 0.043 across 8k/16k/32k while the raw sum
    rose 0.488 -> 0.638 -> 0.638 - the added grades earned ~0).
  - the same grade key at different ctx rungs is the same question
    on the same config: identical credits expected; drift = noise.
  - the argmax rides the raw score (R-19): it favors the biggest
    reachable ctx, ties by quality. The memory-price of a rung is
    read from the DELTA the added grades earned.

The deliverable's one-line answer: the argmax cell; the ranking is
trustworthy only in the normalized + per-grade views above.
"""

from __future__ import annotations

import json
import os
import random
import os
import random
import re
import string
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# addendum 183: the acquire path, moved from bench/certify.py (the v5
# controllers retired; v7 is the only consumer)
from typing import cast  # noqa: E402

import infra.convert_quant as convert_quant
import infra.hf_download as hf_download
import infra.llama_server as llama_server
import ruler_gate


def _acquire_missing_model(
    spec: str,
    fam: str,
    famdir: str,
    rung: str | None,
    state: dict[str, Any],
    dry_run: bool,
) -> str | None:
    """The certify controllers acquire their own entry files (addendum 16,
    refinement: the same phase-1 path the tournament uses - the author runs
    one command, not a download step per model). Returns the local path or
    None (in dry-run the plan is only reported)."""
    if not rung:
        return None
    model_repo, _, source_repo = spec.partition("=")
    hf_download.require_hub()
    list_repo_files = cast("Any", hf_download.list_repo_files)
    try:
        model_files = list_repo_files(model_repo)
        source_repo_eff = source_repo or model_repo
        source_files = (
            model_files if source_repo_eff == model_repo else list_repo_files(source_repo_eff)
        )
        path, plan = hf_download.acquire(
            fam,
            famdir,
            rung,
            model_repo,
            model_files,
            source_repo_eff,
            source_files,
            dry_run,
        )
    except SystemExit as e:
        if e.code == 130:
            raise
        return None
    if path:
        state["families"].setdefault(fam, {})["tournament_entry"] = {
            "rung": rung,
            "file": path,
        }
        return path
    if dry_run:
        return None
    # acquire returned a plan but no file (session 40, addendum 20): the
    # safetensors/bin download branches end in "convert + quantize" - the
    # same phase 2 the tournament path runs (full_benchmark phase 2). The
    # certify controllers previously stopped at phase 1 and errored
    # model-file-not-found for every family whose model must be built, not
    # downloaded - the whole 11:12 run died on it.
    built = convert_quant.create(fam, famdir, rung, plan, dry_run)
    if built:
        state["families"].setdefault(fam, {})["tournament_entry"] = {
            "rung": rung,
            "file": built,
        }
    return built



from bench.state_store import save_state  # noqa: E402
from etc import registry_data  # noqa: E402

S_MAX = 262144
SPANS = [4096, 8192, 16384, 32768, 65536, 131072, 262144]
HOPS = [2, 4, 8, 16, 32]
# Addendum 143: K removed - the per-grade repetition mechanism is
# dead (addendum 139: it grew the deep prefill). Stability across
# runs comes from RE-RUNNING with corpus n+1: the nth corpus has
# seed n (CORPUS_SEED). This run is n=1.
CORPUS_SEED = 1
# addendum 150: the random climb's rng seed - registered so the
# policy is reproducible. Seeded per (family, ctx) via params.
ALLOC_RANDOM_SEED = 7
# addendum 150: the random climb's rng seed - registered so the
# policy is reproducible. Seeded per (family, ctx) via params.
ALLOC_RANDOM_SEED = 7

# addendum 196/197: the axis probe's repeat corpora - three DIFFERENT
# corpora (one per seed), so a probe score is the mean over n=3 and
# the luck factor is eliminated (the author's ruling: no re-measures
# - seed 1, the field corpus, is EXCLUDED so every probe number comes
# from chains never measured before; the base config is measured on
# the new corpora as the baseline, not re-measured on the old one).
# Registered constants, not run-time choices.
PROBE_CORPUS_SEEDS = [11, 12, 13]

# addendum 196: the probe's config set, derived per cell - the base
# (measured) config plus each axis stepped ONE rung down the ladder,
# plus the pairwise down-steps. For the champion @131k (base
# Q8_0/f16/f16) this yields exactly the pre-registered six:
# base, w-down, K-down, V-down, KV-down, w+KV-down.
def probe_configs(wq: str, kq: str, vq: str) -> list[tuple[str, str, str]]:
    wl = W_LADDER
    kl = KV_QUANT_LADDER
    wi = wl.index(wq)
    ki = kl.index(kq)
    vi = kl.index(vq)
    cfgs = [(wq, kq, vq)]
    w1 = wl[max(wi - 1, 0)]
    k1 = kl[max(ki - 1, 0)]
    v1 = kl[max(vi - 1, 0)]
    for c in ((w1, kq, vq), (wq, k1, vq), (wq, kq, v1), (wq, k1, v1), (w1, k1, v1)):
        if c not in cfgs:
            cfgs.append(c)
    return cfgs
# (upstream). Session 44 addenda 120/122/123/143: the author
# rulings - 10x easier (K 20 -> 2), prefill-matched counts, the
# 2k span dropped, then K removed outright. A cell is
# 7 spans x 5 hops = 35 questions, one per grade.
# Addendum 124: no wall-clock ceiling - the question count is the
# correct fix for runtime, and a budget stop would hide slow cells
# instead of pricing them honestly (wall_seconds records the price;
# the per-question elapsed_s in the answers JSONL keeps the
# calibration data).


BUDGET_GIB = 4.0
CTX_GRID = [8192, 16384, 32768, 65536, 131072, 262144]
PILOT_FAMILIES = 4

# weight-quant bytes per parameter; the dict's order is the climb
# ladder. Below Q8_0 the K-encoding (block-scaled K-quants) is the
# ruling; the top is F16 (32/64-bit ruled out - F32 doubles F16 for
# no inference gain, FP64 has no kernels).
# addendum 172 (the author's ruling: "k encodings are a risk for our
# size limit. use _0 encodings for everything except f16"): the
# weights ladder is the _0 legacy formats ONLY below f16 - exact
# structural sizes, no K-quant bookkeeping risk (Q4_K's measured
# 0.625-0.646 bpB vs the naive 0.56 was the addendum-170/171 lesson:
# the super-block scales are a size-limit hazard at the budget line).
# q4_0: 18 bytes / 32 weights = 0.5625 (exact); q8_0: 34/32 = 1.0625
# (exact, census-confirmed). Q8_0 -> F16 is the climb; nothing between
# exists on the ladder. R-18's "k encoding below q8" clause is retired.
W_QUANT_BPB = {
    "Q4_0": 0.5625,  # 18 bytes / 32 weights (4-bit payload + fp16 scale)
    "Q8_0": 1.0625,  # 34 bytes: 8-bit payload + scale (census-confirmed)
    "F16": 2.0,
}
W_LADDER = list(W_QUANT_BPB)
# kv-quant factor vs f16 bytes; K and V caches carry the same
# geometry. Addendum 132: the ladder is ONLY llama-server-supported
# --cache-type-k/v values (q2_K/q4_K crashed the live run at the
# 131072/262144 cells - "Unsupported cache type"); the set matches
# full_benchmark's _KV_CHOICES. Top is f16.
# addendum 173: the ladders are EQUAL - the same _0 family for weights
# and KV cache (the author's ruling, corrected: _0 ONLY, no _1 variants);
# every size is the exact structural constant, no K-quant bookkeeping (R-40).
KV_QUANT_LADDER = ["q4_0", "q8_0", "f16"]  # addendum 188: q5_0 retired (R-41)
KV_QUANT_FACTOR = {
    "q4_0": 0.28125,
    "q8_0": 0.53125,
    "f16": 1.0,
}


# addendum 136 (the author's scope ruling): the estimator prices
# the GPU FOOTPRINT ONLY - what lands on the accelerator. Host/
# system RAM (llama.cpp always parks a fixed chunk there) is out
# of scope. GPU census anchors: weights land at ~1.00x
# params x bpB (MiniCPM4 1.000, granite-4.0 0.999, granite-h
# 1.000; Qwen 0.86 - part of the embedding stays host-side, a
# small UNDER-count we accept rather than model per-family
# offload splits), so NO weights overhead on GPU.
# GPU compute buffer: floor + ~1 KiB/token (census slope
# 9.6e-7 GiB/token across the pilot families; the old 2 KiB
# figure was the system-wide one).
COMPUTE_FLOOR_GIB = 0.075  # addendum 187: SmolLM3 census intercept 0.074
COMPUTE_KIB_PER_TOKEN = 1.0


def weights_gib(params_b: float, wq: str) -> float:
    return params_b * 1e9 * W_QUANT_BPB[wq] / (1 << 30)


def _store() -> dict[str, Any]:
    return json.loads(registry_data.STORE.read_text())


def family_geometry(name: str) -> dict | None:
    return (_store().get(name) or {}).get("geometry")


def family_window(name: str) -> int:
    ex = (_store().get(name) or {}).get("extract") or {}
    return ex.get("max_position_embeddings") or 0


def is_recurrent(name: str) -> bool:
    ex = (_store().get(name) or {}).get("extract") or {}
    return str(ex.get("model_type") or "").lower().startswith("rwkv")


def kv_per_token_f16(name: str, geom: dict | None) -> float | None:
    """f16 KV bytes per token, or None when unknowable. Recurrent
    families return 0.0 (weights-only); the geometry column wins;
    MHA configs with null kv_heads fall back to hidden_size//heads.

    Addendum 133: hybrid-attention families divide by
    full_attention_interval - only every Nth layer keeps a
    full-window cache (the rest are linear/sliding, a small fixed
    cost the census attributes to compute). The addendum-132 run
    over-estimated Qwen3.5-0.8B 4x at 262144 (3.2 GiB predicted vs
    0.86 measured) because all 24 layers were charged at full
    window; with the interval the anchors fit within 5% at every
    ctx >= 32k. The greedy climb climbs HIGHER without it - wrong
    quants hurt scores, and wrong VRAM numbers hurt the
    recommendation, so the estimator calibrates against every
    census anchor (wow.md rule 1).
    """
    if is_recurrent(name):
        return 0.0
    ex = (_store().get(name) or {}).get("extract") or {}
    interval = (geom or {}).get("full_attention_interval") or ex.get("full_attention_interval") or 1
    if geom and geom.get("kv_bytes_per_token_f16"):
        return float(geom["kv_bytes_per_token_f16"]) / interval
    layers = ex.get("num_hidden_layers")
    heads = ex.get("num_attention_heads")
    kvh = ex.get("num_key_value_heads") or heads
    hd = ex.get("head_dim")
    if not hd and heads and ex.get("hidden_size"):
        hd = ex["hidden_size"] // heads
    if not (layers and kvh and hd):
        return None
    return layers * 2 * kvh * hd * 2 / interval


def _alloc_total(
    name: str, p: float, geom: dict | None, wq: str, kq: str, vq: str, ctx: int
) -> float | None:
    per_token = kv_per_token_f16(name, geom)
    if per_token is None:
        return None
    base = per_token / 2.0
    kv = base * (KV_QUANT_FACTOR[kq] + KV_QUANT_FACTOR[vq]) * ctx
    compute = COMPUTE_FLOOR_GIB + COMPUTE_KIB_PER_TOKEN * ctx / (1 << 20)
    return weights_gib(p, wq) + kv / (1 << 30) + compute


def climb_allocations(
    budget_gib: float,
    roster_limit: int = PILOT_FAMILIES,
    policy: str = "greedy",
    report_unplaceable: bool = False,
) -> list[dict]:
    """For each (family, ctx): start at the (W_LADDER[0], q4_0, q4_0) floor and
    climb by single-axis one-notch upgrades that land under the budget
    without exceeding it, until no upgrade fits (the maximal config).
    Policy (addendum 144): "greedy" takes the LARGEST-fitting upgrade
    each step (R-18); "stingy" takes the SMALLEST - the paths diverge,
    the maximality contract is identical. "random" (addendum 150) takes
    a RANDOM fitting upgrade, seeded for reproducibility - the truly
    assumption-free climb: no ordering over the axes, no step
    preference, maximality still guaranteed by the no-upgrade-fits
    stop. Output: the maximal config
    <= budget per (family, ctx), param-ascending.

    SELECTION (addendum 154, the author's ruling): the candidates are
    ALL roster families, sorted by parameter count ascending; the
    limit takes the FIRST N of that sorted list. A family that cannot
    earn a cell (missing registry extract / window below the grid /
    floor config over budget) is a FINDING, not a silent drop: with
    report_unplaceable=True the unplaceable are returned in the
    plan's findings list (family, params, reason) so the run reports
    them - the count of MEASURED families is then honest by
    construction."""
    if policy not in ("greedy", "stingy", "random"):
        raise ValueError(f"unknown allocation policy: {policy!r}")
    rows = sorted((registry_data.params_b(n) or 1e12, n) for n in registry_data.ROSTER)
    out = []
    for p, name in rows[:roster_limit]:
        geom = family_geometry(name)
        window = family_window(name)
        findings: list[dict] = []
        if kv_per_token_f16(name, geom) is None:
            findings.append(
                {
                    "family": name,
                    "params_b": p,
                    "reason": "unplaceable: missing registry extract (KV geometry "
                    "unknowable) - run etc/registry_data.py fetch",
                }
            )
            if report_unplaceable:
                out.append(findings[0])
            continue
        ctxs = [c for c in CTX_GRID if not (window and c > window)]
        if not ctxs:
            findings.append(
                {
                    "family": name,
                    "params_b": p,
                    "reason": (
                        f"unplaceable: trained window {window} below the "
                        f"grid's smallest ctx rung {CTX_GRID[0]} (addendum 123)"
                    ),
                }
            )
            if report_unplaceable:
                out.append(findings[0])
            continue
        feasible = any(
            (
                t := _alloc_total(
                    name, p, geom, W_LADDER[0], KV_QUANT_LADDER[0], KV_QUANT_LADDER[0], c
                )
            )
            is not None
            and t <= budget_gib
            for c in ctxs
        )
        if not feasible:
            findings.append(
                {
                    "family": name,
                    "params_b": p,
                    "reason": (
                        f"unplaceable: floor config ({W_LADDER[0]}, q4_0, q4_0) exceeds "
                        f"the {budget_gib} GiB budget at every reachable ctx"
                    ),
                }
            )
            if report_unplaceable:
                out.append(findings[0])
            continue
        for ctx in ctxs:
            # the floor: (W_LADDER[0], q4_0, q4_0) = (Q4_0, q4_0, q4_0) after
            # addendum 172
            wi, ki, vi = 0, 0, 0
            total = _alloc_total(
                name, p, geom, W_LADDER[wi], KV_QUANT_LADDER[ki], KV_QUANT_LADDER[vi], ctx
            )
            if total is None or total > budget_gib:
                continue
            rng = (
                random.Random(ALLOC_RANDOM_SEED) if policy == "random" else None
            )  # addendum 167: ONE fixed seed, the same for every cell -
            # a fresh rng per (family, ctx) from the registered constant;
            # no params-dependence, no cross-cell stream coupling
            while True:
                if rng is not None:
                    options = []
                    for axis in range(3):
                        cand = (
                            (min(wi + 1, len(W_LADDER) - 1), ki, vi)
                            if axis == 0
                            else (wi, min(ki + 1, len(KV_QUANT_LADDER) - 1), vi)
                            if axis == 1
                            else (wi, ki, min(vi + 1, len(KV_QUANT_LADDER) - 1))
                        )
                        if cand == (wi, ki, vi):
                            continue
                        t = _alloc_total(
                            name,
                            p,
                            geom,
                            W_LADDER[cand[0]],
                            KV_QUANT_LADDER[cand[1]],
                            KV_QUANT_LADDER[cand[2]],
                            ctx,
                        )
                        if t is not None and t <= budget_gib:
                            options.append((t, cand))
                    if not options:
                        break
                    total, (wi, ki, vi) = rng.choice(options)
                    continue
                best = None
                for axis in range(3):
                    cand = (
                        (min(wi + 1, len(W_LADDER) - 1), ki, vi)
                        if axis == 0
                        else (wi, min(ki + 1, len(KV_QUANT_LADDER) - 1), vi)
                        if axis == 1
                        else (wi, ki, min(vi + 1, len(KV_QUANT_LADDER) - 1))
                    )
                    if cand == (wi, ki, vi):
                        continue
                    t = _alloc_total(
                        name,
                        p,
                        geom,
                        W_LADDER[cand[0]],
                        KV_QUANT_LADDER[cand[1]],
                        KV_QUANT_LADDER[cand[2]],
                        ctx,
                    )
                    if t is None or t > budget_gib:
                        continue
                    if best is None or (t > best[0] if policy == "greedy" else t < best[0]):
                        best = (t, cand)
                if best is None:
                    break
                total, (wi, ki, vi) = best
            final = _alloc_total(
                name, p, geom, W_LADDER[wi], KV_QUANT_LADDER[ki], KV_QUANT_LADDER[vi], ctx
            )
            assert final is not None
            out.append(
                {
                    "family": name,
                    "params_b": p,
                    "ctx": ctx,
                    "wq": W_LADDER[wi],
                    "kq": KV_QUANT_LADDER[ki],
                    "vq": KV_QUANT_LADDER[vi],
                    "est_gib": round(final, 2),
                }
            )
    return out


def gen_name(rng: random.Random) -> str:
    return "".join(rng.choices(string.ascii_uppercase, k=ruler_gate.VT_NAME_LEN))


def build_corpus_v72(port: int, s_max: int = S_MAX, seed: int = CORPUS_SEED) -> dict:
    """The chain-arith corpus (addenda 202/203): identical structure to
    build_corpus - the same noise sentences, the same span/hops grid,
    the same seeded placement - except every link after the root
    carries an independent signed delta: VAR B = VAR A + <delta>,
    deltas 3-4 digits both signs (the author's magnitude ruling: large
    enough that a q4_0 rounding error moves a value past exact match,
    small enough to stay integer-exact). Every variable holds a
    DISTINCT value; each question records the names AND the exact
    per-link values (the scorer's ground truth)."""
    rng = random.Random(seed)
    budget = s_max - ruler_gate.ANSWER_HEADROOM
    probe = ruler_gate.VT_HAYSTACK * 20
    probe_n = len(llama_server.tokenize(port, probe))
    tokens_per_sent = max(1.0, probe_n / 20.0)
    num_noises = int(budget / tokens_per_sent)
    sentences: list[str] = [ruler_gate.VT_HAYSTACK] * num_noises
    questions: list[dict] = []
    for s in SPANS:
        for h in HOPS:
            questions.append({"span": s, "hops": h})
    cuts: dict[int, int] = {s: 0 for s in SPANS}
    for qi, q in enumerate(questions):
        s = q["span"]
        limit = max(ruler_gate.VT_NAME_LEN, int(s / tokens_per_sent))
        sub = min(limit, len(sentences))
        chain_len = q["hops"] + 1
        names: list[str] = []
        while len(names) < chain_len:
            n = gen_name(rng)
            if n not in names:
                names.append(n)
        value = rng.randint(10000, 99999)
        values = [value]
        chain = [f"VAR {names[0]} = {value}"]
        for j in range(q["hops"]):
            delta = rng.randint(100, 9999) * rng.choice((1, -1))
            values.append(values[-1] + delta)
            chain.append(f"VAR {names[j + 1]} = VAR {names[j]} + {delta}")
        positions = sorted(rng.sample(range(sub), chain_len))
        for pi, j in zip(positions, range(chain_len), strict=True):
            sentences.insert(pi + j, chain[j])
        cuts[s] = max(cuts[s], positions[-1] + 2 * chain_len)
        questions[qi] = {
            **q,
            "names": names,
            "value": str(value),
            "values": [str(v) for v in values],
            "deltas": [0] + [int(v) - int(u) for u, v in zip(values, values[1:])],
        }
    for s in SPANS:
        cuts[s] = min(cuts[s] + 8, len(sentences))
    return {
        "sentences": sentences,
        "questions": questions,
        "cuts": cuts,
        "s_max": s_max,
        "grammar": "chainarith",
    }


def question_prompt_v72(corpus: dict, q: dict) -> str:
    cut = corpus["cuts"][q["span"]]
    context = "\n".join(corpus["sentences"][:cut]).replace(". \n", ".\n")
    return CHAINARITH_TEMPLATE.format(
        context=context,
        root=q["names"][0],
        rootval=q["values"][0],
        num_v=q["hops"] + 1,
    )


def build_corpus_v73(port: int, s_max: int = S_MAX, seed: int = CORPUS_SEED) -> dict:
    """The gated-chain corpus (addendum 212): chainarith's structure
    with each link's delta replaced by a REFERENCE - VAR B = VAR A +
    <mul> x D<i> - where D<i> is defined by ONE easy seeded riddle
    sentence planted elsewhere in the same span region, and each
    chain gets a near-miss decoy chain (edit-distance-1 names)
    planted adjacent to the real links. The model must select the
    right chain among decoys (K), find and resolve each gate
    (K + weights), then compute (weights) - the cascade amplifies
    whichever stage breaks."""
    rng = random.Random(seed)
    budget = s_max - ruler_gate.ANSWER_HEADROOM
    probe = ruler_gate.VT_HAYSTACK * 20
    probe_n = len(llama_server.tokenize(port, probe))
    tokens_per_sent = max(1.0, probe_n / 20.0)
    num_noises = int(budget / tokens_per_sent)
    sentences: list[str] = [ruler_gate.VT_HAYSTACK] * num_noises
    questions: list[dict] = []
    for s in SPANS:
        for h in HOPS:
            questions.append({"span": s, "hops": h})
    cuts: dict[int, int] = {s: 0 for s in SPANS}
    d_counter = 0
    for qi, q in enumerate(questions):
        s = q["span"]
        limit = max(ruler_gate.VT_NAME_LEN, int(s / tokens_per_sent))
        sub = min(limit, len(sentences))
        chain_len = q["hops"] + 1
        names: list[str] = []
        while len(names) < chain_len:
            n = gen_name(rng)
            if n not in names:
                names.append(n)
        value = rng.randint(10000, 99999)
        values = [value]
        chain = [f"VAR {names[0]} = {value}"]
        gate_specs = []
        for j in range(q["hops"]):
            d_counter += 1
            dname = f"D{d_counter}"
            riddle, fn = RIDDLE_TEMPLATES[rng.randrange(len(RIDDLE_TEMPLATES))]
            n_small = rng.randint(2, 9)
            gate_val = fn(n_small)
            mul = rng.randint(100, 999)
            delta = mul * gate_val * rng.choice((1, -1))
            values.append(values[-1] + delta)
            sign = "+" if delta >= 0 else "-"
            chain.append(
                f"VAR {names[j + 1]} = VAR {names[j]} {sign} {mul} x {dname}"
            )
            gate_specs.append(
                {
                    "dname": dname,
                    "riddle": riddle.format(n=n_small),
                    "gate_val": gate_val,
                    "mul": mul,
                    "sign": sign,
                }
            )
        positions = sorted(rng.sample(range(sub), chain_len))
        for pi, j in zip(positions, range(chain_len), strict=True):
            sentences.insert(pi + j, chain[j])
        # decoy chain: same-length, edit-distance-1 names, plausible
        # values, planted right AFTER the real chain's LAST link (adjacent
        # by construction - the near-miss K-stressor). Anchored at the
        # DEEPEST link so the decoy never lands beyond the region.
        decoy_names = [_edit_distance_one(n, rng) for n in names]
        dv = rng.randint(10000, 99999)
        decoy = [f"VAR {decoy_names[0]} = {dv}"]
        for j in range(q["hops"]):
            dmul = rng.randint(100, 999)
            decoy.append(
                f"VAR {decoy_names[j + 1]} = VAR {decoy_names[j]} + {dmul}"
            )
        base_pos = positions[-1] + chain_len
        for j in range(chain_len):
            sentences.insert(base_pos + j, decoy[j])
        # gates: one riddle sentence per link, scattered AFTER the decoy
        # but INSIDE the cut the question will present (found by position,
        # not adjacency - selection under distance)
        gate_end = base_pos + chain_len
        for gspec in gate_specs:
            gpos = gate_end + rng.randint(1, max(2, sub // 8))
            gpos = min(gpos, len(sentences))
            sentences.insert(
                gpos,
                f"{gspec['dname']} is {gspec['riddle']}, which is "
                f"{gspec['gate_val']}",
            )
            gate_end = gpos + 1
        # the cut must cover EVERYTHING this question planted: chain,
        # decoy, gates - the deepest insertion plus margin, or the
        # prefix would orphan the gates (the v7.2 question bug's
        # corpus-side twin, caught by the invariant check before burn)
        deepest = gate_end + 1
        cuts[s] = max(cuts[s], deepest + 4)
        questions[qi] = {
            **q,
            "names": names,
            "value": str(value),
            "values": [str(v) for v in values],
            "gates": gate_specs,
        }
    for s in SPANS:
        cuts[s] = min(cuts[s] + 16, len(sentences))
    return {
        "sentences": sentences,
        "questions": questions,
        "cuts": cuts,
        "s_max": s_max,
        "grammar": "gatedchain",
    }


def question_prompt_v73(corpus: dict, q: dict) -> str:
    cut = corpus["cuts"][q["span"]]
    context = "\n".join(corpus["sentences"][:cut]).replace(". \n", ".\n")
    return GATED_TEMPLATE.format(
        context=context,
        root=q["names"][0],
        rootval=q["values"][0],
        num_v=q["hops"] + 1,
    )


def build_corpus(port: int, s_max: int = S_MAX, seed: int = CORPUS_SEED) -> dict:
    """One fixed VT corpus, identical bytes every run. The corpus is a
    sentence list (noise + every question's chain embedded); a chain
    for span grade s has its links among the first ~s tokens. Per-span
    CUT indices record where each span's region ends (the deepest
    insertion position of that span's chains plus one hop of margin)
    - a span-s question presents only sentences[:cut_s], so its
    prompt is ~s tokens (the full-corpus prompt of the first live run
    was HTTP-400 dead on any small-window cell: 357k tokens vs a 2k
    ctx). Prefix fairness holds: every model sees the same bytes for
    a given grade; prefill cost is proportional to the span."""
    rng = random.Random(seed)
    budget = s_max - ruler_gate.ANSWER_HEADROOM
    probe = ruler_gate.VT_HAYSTACK * 20
    probe_n = len(llama_server.tokenize(port, probe))
    tokens_per_sent = max(1.0, probe_n / 20.0)
    num_noises = int(budget / tokens_per_sent)
    sentences: list[str] = [ruler_gate.VT_HAYSTACK] * num_noises
    questions: list[dict] = []
    for s in SPANS:
        for h in HOPS:
            questions.append({"span": s, "hops": h})
    cuts: dict[int, int] = {s: 0 for s in SPANS}
    for qi, q in enumerate(questions):
        s = q["span"]
        limit = max(ruler_gate.VT_NAME_LEN, int(s / tokens_per_sent))
        sub = min(limit, len(sentences))
        chain_len = q["hops"] + 1
        names: list[str] = []
        while len(names) < chain_len:
            n = gen_name(rng)
            if n not in names:
                names.append(n)
        value = str(rng.randint(10000, 99999))
        chain = [f"VAR {names[0]} = {value}"]
        for j in range(q["hops"]):
            chain.append(f"VAR {names[j + 1]} = VAR {names[j]} ")
        positions = sorted(rng.sample(range(sub), chain_len))
        for pi, j in zip(positions, range(chain_len), strict=True):
            sentences.insert(pi + j, chain[j])
        cuts[s] = max(cuts[s], positions[-1] + 2 * chain_len)
        questions[qi] = {**q, "names": names, "value": value}
    for s in SPANS:
        cuts[s] = min(cuts[s] + 8, len(sentences))
    return {
        "sentences": sentences,
        "questions": questions,
        "cuts": cuts,
        "s_max": s_max,
    }


def question_prompt(corpus: dict, q: dict) -> str:
    """The span-s question: the corpus PREFIX up to that span's cut,
    plus the query tail. ~s tokens of prefill, chain included."""
    cut = corpus["cuts"][q["span"]]
    context = "\n".join(corpus["sentences"][:cut]).replace(". \n", ".\n")
    return ruler_gate.VT_TEMPLATE.format(context=context, query=q["value"], num_v=q["hops"] + 1)


class BudgetExceeded(Exception):
    """Addendum 170: the MEASURED GPU census exceeded the budget - the
    estimate was wrong. The cell is an error, never a scored result."""


class PreflightError(Exception):
    """The measured prompt does not fit the window the arithmetic said
    it would (session 44, addendum 112) - the estimate-vs-server drift
    both live crashes shared. Reported per cell, never a crash."""


class TemplateMalfunction(Exception):
    """The model fails a template-sanity probe (addendum 140): asked
    to reply with a single word, it echoes chat-template fragments
    or the prompt text instead - the GGUF's embedded template (or
    the server's auto-parse of it) mangles the message, so the
    model never sees a well-formed question. The cell is LABELLED
    (template_malfunction), not scored: a measured 0 would lie
    about the model's reach (MiniCPM5-1B, session 45 - its
    prefill was an endless <|im_start|> assistant loop and the
    answers parroted haystack noise)."""


PROMPT_OVERHEAD_TOKENS = 128
GEN_HEADROOM_TOKENS = 192
TEMPLATE_PROBE_PROMPT = "Reply with the single word PINEAPPLE and nothing else."


def grade_reachable(span: int, hops: int, window: int) -> bool:
    """R-19's reachability with the server's own accounting (session 44:
    the span-2048 grade at a ctx=2048 cell HTTP-400'd - the prompt was
    2048 prefix + template + query, and the server also reserves room
    for max_tokens, which grows with hops). A grade is reachable only
    if the whole request fits: span + overhead + generation headroom
    <= window. Overhead and headroom are generous constants - the
    template is ~90 tokens, generation is at most VT_GEN_TOKENS."""
    gen = max(ruler_gate.VT_GEN_TOKENS, (hops + 1) * 12)
    return span + PROMPT_OVERHEAD_TOKENS + max(GEN_HEADROOM_TOKENS, gen) <= window


def preflight_reachable_grades(port: int, corpus: dict, window: int) -> dict[str, int] | None:
    """The measured-reality check (session 44, addendum 112): tokenize
    the SMALLEST and LARGEST reachable grade's actual rendered prompt
    and verify the whole request fits the window. The estimate in
    grade_reachable is arithmetic; this is measurement - both live
    crashes (357k prompt vs 2k; 2237 vs 2048) were estimate-vs-server
    drift that a preflight would have caught before any question was
    asked. Returns {grade_key: measured_prompt_tokens} on pass, or
    raises PreflightError naming the overflow."""
    probes = sorted(
        {
            (q["span"], q["hops"])
            for q in corpus["questions"]
            if grade_reachable(q["span"], q["hops"], window)
        }
    )
    if not probes:
        return {}
    seen: dict[tuple[int, int], int] = {}
    for span, hops in (probes[0], probes[-1]):
        q = next(x for x in corpus["questions"] if x["span"] == span and x["hops"] == hops)
        toks = len(llama_server.tokenize(port, question_prompt(corpus, q)))
        seen[(span, hops)] = toks
        gen = max(ruler_gate.VT_GEN_TOKENS, (hops + 1) * 12)
        if toks + gen > window:
            raise PreflightError(
                f"grade {span}x{hops}: rendered prompt is {toks} tokens + {gen} gen "
                f"= {toks + gen} > window {window} - the reachability estimate "
                f"drifted from this server's tokenizer"
            )
    return {f"{s}x{h}": t for (s, h), t in seen.items()}


def preflight_template_sanity(port: int) -> None:
    """Addendum 140: a one-question sanity probe BEFORE the cell runs.
    A healthy model asked to reply with the single word PINEAPPLE
    returns something short and echo-free; a template-mangled one
    parrots template fragments (<|im_start|>, [INST]) or the
    instruction text itself. Raises TemplateMalfunction so the
    cell is labelled, never scored-0."""
    reply = ruler_gate.ask(port, TEMPLATE_PROBE_PROMPT, max_tokens=32)
    r = (reply or "").strip()
    if not r:
        raise TemplateMalfunction("empty reply to the sanity probe")
    low = r.lower()
    if any(frag in low for frag in ("<|im_start|>", "<|im_end|>", "[inst]", "</s>", "<s>")):
        raise TemplateMalfunction(f"template fragment in sanity probe: {r[:120]!r}")
    # a model that parrots the instruction back ("reply with the word...")
    # is echoing, not answering
    if low.startswith("reply with") or low.startswith("respond with"):
        raise TemplateMalfunction(f"prompt echo in sanity probe: {r[:120]!r}")


def run_cell(
    port: int,
    corpus: dict,
    window: int,
    answers_path: str | None = None,
) -> dict:
    """Score one allocation: pass mass over the reachable (span, hops)
    grid. Questions with span > window are EXCLUDED (structurally
    unreachable), not failed. Pass = all h+1 names (upstream's rule).

    answers_path (R-23): EVERY answer is logged, one JSON line per
    question - grade, expected, found count, the raw answer. Answers
    are always important for debugging; the file is append-per-cell
    and lands in the family's results dir next to the server log."""
    per_grade: dict[tuple[int, int], dict] = {}
    samples: list[dict] = []
    answers_fh = open(answers_path, "a", encoding="utf-8") if answers_path else None
    started = time.monotonic()
    try:
        for q in corpus["questions"]:
            if not grade_reachable(q["span"], q["hops"], window):
                continue
            key = (q["span"], q["hops"])
            g = per_grade.setdefault(
                key, {"pass": 0, "asked": 0, "found": 0, "credit": 0.0, "format_ok": 0}
            )
            grammar = corpus.get("grammar")
            is_v72 = grammar in ("chainarith", "gatedchain")
            prompt = (
                question_prompt_v73(corpus, q)
                if grammar == "gatedchain"
                else question_prompt_v72(corpus, q)
                if is_v72
                else question_prompt(corpus, q)
            )
            per_q = (q["hops"] + 1) * (26 if is_v72 else 12)
            max_tokens = max(ruler_gate.VT_GEN_TOKENS, per_q)
            t0 = time.monotonic()
            answer = ruler_gate.ask(port, prompt, max_tokens=max_tokens)
            elapsed = round(time.monotonic() - t0, 3)
            if is_v72:
                ok, found = score_pairs(answer, q["names"], q["values"])
                fmt_ok = ok
            else:
                ok, found = ruler_gate.score_vt(answer, q["names"])
                fmt_ok = ruler_gate.format_ok_vt(answer)
            g["asked"] += 1
            g["format_ok"] += 1 if fmt_ok else 0
            g["pass"] += 1 if ok else 0
            g["found"] += found
            # addendum 125: partial credit - found/(h+1) per question.
            # The strict all-names rule left every pilot cell at 0 while
            # models traced parts of the chain (44/400 answers had >=1
            # name, 0/400 had all); credit prices the partial trace.
            g["credit"] += found / len(q["values"]) if is_v72 else found / len(q["names"])
            if answers_fh is not None:
                answers_fh.write(
                    json.dumps(
                        {
                            "window": window,
                            "grade": f"{q['span']}x{q['hops']}",
                            "expected": q["names"],
                            "value": q["value"],
                            "found": found,
                            "ok": ok,
                            "format_ok": fmt_ok,
                            "elapsed_s": elapsed,
                            "answer": answer,
                        },
                        ensure_ascii=True,
                    )
                    + "\n"
                )
                answers_fh.flush()
            # addendum 113: three sample answers per grade (one pass,
            # up to two fails) land in the cell record for quick reads.
            sample = {
                "grade": f"{q['span']}x{q['hops']}",
                "ok": ok,
                "found": found,
                "names": q["names"],
                "answer": (answer or "")[:200],
            }
            passes = sum(1 for x in samples if x["grade"] == sample["grade"] and x["ok"])
            fails = sum(1 for x in samples if x["grade"] == sample["grade"] and not x["ok"])
            if (ok and passes < 1) or (not ok and fails < 2):
                samples.append(sample)
    finally:
        if answers_fh is not None:
            answers_fh.close()
    score = 0.0
    asked_grades = 0
    for _key, g in sorted(per_grade.items()):
        if g["asked"]:
            score += g["credit"] / g["asked"]
            asked_grades += 1
    return {
        "window": window,
        "score": round(score, 3),
        "max_score": asked_grades,
        "wall_seconds": round(time.monotonic() - started, 1),
        "samples": samples,
        "format_ok": sum(g["format_ok"] for g in per_grade.values()),
        "format_ok_asked": sum(g["asked"] for g in per_grade.values()),
        "per_grade": {
            f"{s}x{h}": {
                "pass": g["pass"],
                "asked": g["asked"],
                "credit": round(g["credit"], 3),
                "format_ok": g["format_ok"],
            }
            for (s, h), g in sorted(per_grade.items())
        },
    }


CORPUS_ARTIFACT = "state/v7-corpus.json"
CORPUS_ARTIFACT_V72 = "state/v7-2-corpus.json"
CORPUS_ARTIFACT_V72 = "state/v7-2-corpus.json"

# addendum 212: the gated-chain grammar (v7.3) - each link's delta is a
# REFERENCE (VAR B = VAR A + 100 x D3), each D defined by an easy seeded
# riddle sentence planted elsewhere in the region; near-miss decoy chains
# (edit-distance-1 names) make the selection competitive.
GATED_TEMPLATE = (
    "[INST] Memorize and track the chain(s) of variable assignment "
    "hidden in the following text.\n\n{context}\nQuestion: One "
    "chain begins with the assignment VAR {root} = {rootval}. "
    "Follow that chain - and only that chain - link by link, resolving "
    "each D reference to its defined value, and report each variable "
    "in it and the value it holds, in chain order. [/INST] Answer ONLY "
    "with the {num_v} pairs as NAME = VALUE, comma-separated, and "
    "nothing else. "
)

# easy, closed-form riddle templates (addendum 209: near-100% at f16);
# (template, answer) - the riddle's ANSWER is the D value's small core
RIDDLE_TEMPLATES = [
    ("the number of legs on {n} spiders", lambda n: 8 * n),
    ("the number of wheels on {n} cars", lambda n: 4 * n),
    ("the number of sides on {n} hexagons", lambda n: 6 * n),
    ("the number of fingers on {n} hands", lambda n: 5 * n),
    ("the number of eggs in {n} dozen", lambda n: 12 * n),
    ("the number of minutes in {n} hours", lambda n: 60 * n),
    ("the number of days in {n} weeks", lambda n: 7 * n),
    ("the number of quarters in {n} dollars", lambda n: 4 * n),
]


def _edit_distance_one(name: str, rng: random.Random) -> str:
    """A decoy name differing from the real one by exactly one "
    "substituted character (edit distance 1) - the near-miss "
    "K-stressor (addendum 212)."""
    alphabet = [c for c in string.ascii_uppercase if c != name[0]]
    i = rng.randrange(len(name))
    c = rng.choice(alphabet)
    return name[:i] + c + name[i + 1 :]

# addendum 202/203: the chain-arith grammar (v7.2) - every link carries
# an independent signed delta (VAR B = VAR A + -1234), so every
# variable holds a DISTINCT value and the question asks for
# NAME = VALUE pairs. The v7.1 grammar (aliases, lookup question)
# stays the default; the frozen suite pins it.
CHAINARITH_TEMPLATE = (
    "[INST] Memorize and track the chain(s) of variable assignment "
    "hidden in the following text.\n\n{context}\nQuestion: One "
    "chain begins with the assignment VAR {root} = {rootval}. "
    "Follow that chain - and only that chain - link by link, and "
    "report each variable in it and the value it holds, in chain "
    "order. [/INST] Answer ONLY with the {num_v} pairs as "
    "NAME = VALUE, comma-separated, and nothing else. "
)
PAIR_RE = re.compile(
    r"([A-Z]{%d})\s*=\s*(-?\d+)(?:\s*\+\s*-?\d+\s*=\s*(-?\d+))?" % ruler_gate.VT_NAME_LEN
)


def score_pairs(answer: str, expected_names: list[str], expected_values: list[str]) -> tuple[bool, int]:
    """Addendum 203 partial credit per (name, value) pair, tolerant of
    work-shown: the pilot answers came back as NAME = base + delta =
    FINAL (the model computes in the answer), so the FINAL number is
    taken when present, the first number otherwise."""
    clean = ruler_gate.strip_template_debris(answer or "").upper()
    correct = 0
    for match in PAIR_RE.finditer(clean):
        name, first, final = match.group(1), match.group(2), match.group(3)
        val = final if final is not None else first
        if name in expected_names and val == expected_values[expected_names.index(name)]:
            correct += 1
    return correct == len(expected_names), correct


def corpus_from_artifact(port: int) -> dict:
    """The corpus as a repo artifact (the author's session-43 ruling):
    load state/v7-corpus.json when it matches the current grid
    constants; otherwise build once and write it. The artifact makes
    the corpus citable and byte-stable across machines - every
    contender runs on the exact same chains, and a rebuild is
    verifiable against the committed file."""
    # JSON stringifies int dict keys, so the artifact's k_per_span
    # comes back with str keys - compare on str or every load misses
    grid = {
        "spans": SPANS,
        "hops": HOPS,
        "seed": CORPUS_SEED,
        "s_max": S_MAX,
    }
    if os.path.exists(CORPUS_ARTIFACT):
        with open(CORPUS_ARTIFACT, encoding="utf-8") as f:
            art = json.load(f)
        stored = art.get("grid") or {}
        if all(stored.get(k_) == v for k_, v in grid.items()) and art.get("corpus"):
            corpus = art["corpus"]
            # JSON stringifies the int cut keys - restore them, or
            # question_prompt's corpus["cuts"][span] KeyErrors on every
            # artifact-loaded run (found by the roundtrip test once the
            # load path actually worked - session 43)
            corpus["cuts"] = {int(k_): v for k_, v in (corpus.get("cuts") or {}).items()}
            return corpus
    corpus = build_corpus(port)
    os.makedirs(os.path.dirname(CORPUS_ARTIFACT), exist_ok=True)
    with open(CORPUS_ARTIFACT, "w", encoding="utf-8") as f:
        json.dump({"grid": grid, "corpus": corpus}, f)
    return corpus


def probe_axes(
    models_dir: str,
    state: dict[str, Any],
    state_path: str,
    port: int,
    probe_cells: list[tuple[str, int]] | list[tuple[str, int, tuple[str, str, str]]],
    dry_run: bool = False,
    budget_gib: float = BUDGET_GIB,
    on_model_commit: Any = None,
    grammar: str = "v71",
) -> list[dict[str, Any]]:
    """Addendum 196: the axis probe - one family/cell measured across
    its config neighborhood: the base (measured) config plus each axis
    stepped one rung down, plus the pairwise down-steps, on n=3 repeat
    corpora (PROBE_CORPUS_SEEDS). Results land under
    families/<fam>/probe/<ctx>/<wq-kq-vq> - a NAMESPACE APART from v7,
    so the v7.1 table is never contaminated by probe records. The
    probe is the expensive experiment; it runs only on cells the
    author names (--v7-probe-axes family:ctx,...)."""
    from bench.state_store import save_state

    results: list[dict[str, Any]] = []
    corpora: dict[int, dict] = {}
    builder = (
        build_corpus_v73
        if grammar == "gatedchain"
        else build_corpus_v72
        if grammar == "chainarith"
        else build_corpus
    )
    for spec_cell in probe_cells:
        if len(spec_cell) == 3:
            fam, ctx, explicit_cfgs = spec_cell
        else:
            fam, ctx = spec_cell
            explicit_cfgs = None
        fst = state["families"].setdefault(fam, {})
        base = (fst.get("v7") or {}).get(str(ctx)) or {}
        if base.get("score") is None:
            print(f"probe: {fam} ctx={ctx}: no measured base cell - skipped")
            continue
        cfgs = (
            [tuple(explicit_cfgs)] if explicit_cfgs else probe_configs(base["wq"], base["kq"], base["vq"])
        )
        # addendum 205: the probe namespace is grammar-scoped - a chainarith
        # record is NOT the v7.1 record for the same config (the pilot run
        # silently skipped everything because the v7.1 means were on file)
        pdir = fst.setdefault("probe", {})
        if grammar != "v71":
            pdir = fst.setdefault(f"probe_{grammar}", {})
        print(
            f"=== probe {fam} ctx={ctx}: base {base['wq']}/{base['kq']}/"
            f"{base['vq']} (score {base['score']}), {len(cfgs)} configs x "
            f"n={len(PROBE_CORPUS_SEEDS)} corpora"
        )
        if dry_run:
            for wq, kq, vq in cfgs:
                print(f"  plan: probe {fam} ctx={ctx} {wq}/{kq}/{vq}")
            results.append({"family": fam, "ctx": ctx, "probe": [list(c) for c in cfgs]})
            continue
        repo = registry_data.ROSTER.get(fam, fam)
        famdir = os.path.join(models_dir, fam)
        results_dir = os.path.join(models_dir, "tournament-results", fam)
        os.makedirs(results_dir, exist_ok=True)
        for wq, kq, vq in cfgs:
            key = f"{wq}-{kq}-{vq}"
            stored = (pdir.get(str(ctx)) or {}).get(key)
            if stored is not None and stored.get("mean_score") is not None:
                print(f"  {key}: already probed (mean {stored['mean_score']})")
                results.append({"family": fam, "ctx": ctx, "cfg": key, **stored})
                continue
            gguf = _acquire_missing_model(repo, fam, famdir, wq, state, False)
            if not gguf:
                results.append({"family": fam, "ctx": ctx, "cfg": key, "error": "acquire"})
                continue
            log_path = os.path.join(
                results_dir, f"{fam}-ctx{ctx}-probe-{key}-server.log"
            )
            extra = ["-c", str(ctx), "--parallel", "1"]
            if kq != "f16" or vq != "f16":
                extra += ["-fa", "on", "--cache-type-k", kq, "--cache-type-v", vq]
            proc, healthy = llama_server.start_server(
                gguf, port=port, extra_args=extra, log_path=log_path
            )
            try:
                if not healthy or not llama_server.wait_healthy(port, proc=proc):
                    results.append(
                        {"family": fam, "ctx": ctx, "cfg": key, "error": "server"}
                    )
                    continue
                breakdown = llama_server.memory_breakdown_gib(log_path)
                scores = []
                per_seed = {}
                for seed in PROBE_CORPUS_SEEDS:
                    if seed not in corpora:
                        corpora[seed] = builder(port, seed=seed)
                    corpus = corpora[seed]
                    try:
                        preflight_template_sanity(port)
                    except TemplateMalfunction as e:
                        results.append(
                            {"family": fam, "ctx": ctx, "cfg": key,
                             "error": f"template_malfunction: {e}"}
                        )
                        break
                    g_suffix = "" if grammar == "v71" else f"-{grammar}"
                    answers_path = os.path.join(
                        results_dir,
                        f"{fam}-ctx{ctx}-probe-{key}{g_suffix}-seed{seed}-answers.jsonl",
                    )
                    try:
                        rec = run_cell(port, corpus, ctx, answers_path=answers_path)
                    except BudgetExceeded as e:
                        results.append(
                            {"family": fam, "ctx": ctx, "cfg": key, "error": f"budget: {e}"}
                        )
                        break
                    scores.append(rec["score"])
                    per_seed[seed] = rec
                if len(scores) < len(PROBE_CORPUS_SEEDS):
                    continue
                mean = round(sum(scores) / len(scores), 3)
                if breakdown is not None:
                    devs = breakdown.get("devices") or {}
                    v = devs.get("Vulkan0") or {}
                    gpu_gib = (
                        (v.get("model_gib") or 0)
                        + (v.get("context_gib") or 0)
                        + (v.get("compute_gib") or 0)
                    ) if v else breakdown.get("total_gib")
                    if gpu_gib is not None and gpu_gib > budget_gib:
                        results.append(
                            {"family": fam, "ctx": ctx, "cfg": key,
                             "error": f"budget: measured GPU {gpu_gib:.2f} GiB"}
                        )
                        continue
                rec_out = {
                    "wq": wq, "kq": kq, "vq": vq,
                    "mean_score": mean,
                    "scores": scores,
                    "est_gib": round(_alloc_total(
                        fam, registry_data.params_b(fam) or 0.0, family_geometry(fam),
                        wq, kq, vq, ctx
                    ) or 0.0, 2),
                }
                print(f"  {key}: mean {mean} (per-seed {scores})")
                pdir[str(ctx)] = {**(pdir.get(str(ctx)) or {}), key: rec_out}
                save_state(state_path, state)
                results.append({"family": fam, "ctx": ctx, "cfg": key, **rec_out})
            finally:
                llama_server.stop_server(proc, port)
        if on_model_commit is not None:
            try:
                on_model_commit(results)
            except Exception as e:
                print(f"  model-commit failed (ignored): {e}")
    return results


def certify_v7(
    models_dir: str,
    state: dict[str, Any],
    state_path: str,
    port: int,
    roster_limit: int,
    dry_run: bool = False,
    budget_gib: float = BUDGET_GIB,
    on_model_commit: Any = None,
    clean: bool = False,
    alloc_policy: str = "greedy",
    only_cells: list[tuple[str, int]] | None = None,
    multi_arm: bool = False,
) -> list[dict[str, Any]]:
    """Addendum 166: multi_arm mode - all three allocation policies
    measured TOGETHER, in one cell record: greedy goes first, then
    stingy IFF its config differs from greedy's, then random IFF its
    config differs from both. Every arm's config and score land in the
    SAME cell (state[...][ctx]["arms"] = {policy: {wq,kq,vq,score,
    ...}}), so all the data is in one file. Cells where all three
    agree measure once (the null arm needs no re-measure)."""
    """The v7 controller, in the certify shape: for each greedy cell,
    acquire the wq quant (the certify phase-1/2 path), launch in the
    bench.cells shape (ctx, -fa on, cache types), score the fixed
    corpus on the reachable grid, persist per cell under
    families/<name>/v7/<ctx>. An interrupted run resumes; measured
    cells are never re-measured."""
    if clean:
        # addendum 129: --clean wipes ALL v7 cells and answer logs
        # UP FRONT, before any measuring - per-cell cleaning (the
        # addendum-125 --force shape) left mixed-era records for
        # families not yet reached when a mid-flight run was stopped;
        # the author's rule is never leave mixed results in a table
        wiped = 0
        for fam in sorted(state.get("families", {})):
            fst = state["families"][fam]
            if fst.pop("v7", None) is not None:
                wiped += 1
            for f_ in (
                os.listdir(os.path.join(models_dir, "tournament-results", fam))
                if os.path.isdir(os.path.join(models_dir, "tournament-results", fam))
                else []
            ):
                if f_.endswith("-v7-answers.jsonl"):
                    os.remove(os.path.join(models_dir, "tournament-results", fam, f_))
        print(f"clean: wiped v7 blocks from {wiped} famil(y/ies) and all answer logs")
        save_state(state_path, state)
    cells = climb_allocations(budget_gib, roster_limit, alloc_policy, report_unplaceable=True)
    # addendum 166: the multi-arm plans - stingy/random configs per cell,
    # measured only where they diverge from the arms already measured
    alt_plans: dict[str, dict[tuple[str, int], dict]] = {}
    if multi_arm:
        for pol in ("stingy", "random"):
            plan = [
                r for r in climb_allocations(budget_gib, roster_limit, pol) if "reason" not in r
            ]
            alt_plans[pol] = {(r["family"], r["ctx"]): r for r in plan}
    # addendum 154: the unplaceable are FINDINGS, reported before the
    # run - the measured count is honest by construction
    findings = [c for c in cells if "reason" in c]
    cells = [c for c in cells if "reason" not in c]
    if findings:
        print(
            f"\n{len(findings)} of the first {roster_limit} candidates "
            f"cannot earn a cell (findings, addendum 154):"
        )
        for f in findings:
            print(f"  {f['family']}: {f['reason']}")
    results: list[dict[str, Any]] = []
    corpus = None
    # addendum 132: the commit hook fires once per family, after its
    # LAST cell - not per cell. Cells are ordered family-major (the
    # greedy output is param-ascending, ctx-ascending per family).
    pending: list[dict[str, Any]] = []
    pending_fam = None

    def _flush_model_commit() -> None:
        # addendum 147: the commit fires only when something RAN - a
        # fully-skipped family (resume, all cells already measured)
        # commits nothing; re-pushing evaluated artifacts is noise.
        # The batch still carries the whole family picture (the
        # skipped cells included) when at least one cell measured.
        ran = [e for e in pending if e.get("skipped") is None]
        if on_model_commit is not None and ran:
            try:
                on_model_commit(list(pending))
            except Exception as e:
                print(f"  model-commit failed (ignored): {e}")

    # addendum 181: the position print - the plan is param-ascending, so
    # the family's first cell marks its position: "model x of n"
    plan_fams = []
    for _c in cells:
        if _c["family"] not in plan_fams:
            plan_fams.append(_c["family"])
    fam_position = {f: i + 1 for i, f in enumerate(plan_fams)}
    n_models = len(plan_fams)

    for cell in cells:
        fam = cell["family"]
        if pending_fam is not None and fam != pending_fam:
            _flush_model_commit()
            pending.clear()
        pending_fam = fam
        fst = state["families"].setdefault(fam, {})
        key = str(cell["ctx"])
        v7 = fst.setdefault("v7", {})
        done = v7.get(key) or {}
        entry = {**cell, "family": fam}
        # addendum 162: the cell selector - measure ONLY the cells whose
        # (family, ctx) is listed; everything else is reported as skipped
        # (selector), never measured. Comparison arms re-measure only the
        # diverging cells - no sense re-measuring what cannot change.
        # (The check lives AFTER entry exists - the first delivery put it
        # before and crashed the author's run; the crash rail caught it.)
        if only_cells is not None and (fam, cell["ctx"]) not in only_cells:
            entry["skipped"] = "cell not selected (--v7-cells)"
            results.append(entry)
            continue
        # addendum 168: the multi-arm pre-launch check - decide BEFORE the
        # launch cycle (acquire, start, corpus, preflight) whether ANY arm
        # needs measuring. Greedy measured + every diverging arm already in
        # the cell's arms block => nothing to do; the launch cycle is pure
        # waste in that case (the author's compute-time catch).
        if (
            done.get("score") is not None
            and done.get("wq") == cell["wq"]
            and done.get("kq") == cell["kq"]
            and done.get("vq") == cell["vq"]
        ):
            if multi_arm:
                arms_record = done.get("arms") or {}
                stored_arms = arms_record.get
                arms_needed = []
                for pol in ("stingy", "random"):
                    alt = alt_plans.get(pol, {}).get((fam, cell["ctx"]))
                    if alt is None:
                        continue
                    if (alt["wq"], alt["kq"], alt["vq"]) == (
                        cell["wq"],
                        cell["kq"],
                        cell["vq"],
                    ):
                        continue  # agrees with greedy - already measured
                    stored = stored_arms(pol)
                    if stored is not None and stored.get("score") is not None:
                        continue  # that arm already measured
                    arms_needed.append(pol)
                if not arms_needed:
                    entry["skipped"] = f"already measured (score {done['score']})"
                    entry["arms"] = done.get("arms") or {}
                    results.append(entry)
                    pending.append(entry)
                    continue
                print(
                    f"  greedy measured; arms still needed: {arms_needed} - "
                    "launching only for them"
                )
                cell["_skip_greedy_rescore"] = True
            else:
                entry["skipped"] = f"already measured (score {done['score']})"
                results.append(entry)
                pending.append(entry)
                continue
        if done.get("score") is not None and not cell.get("_skip_greedy_rescore", False):
            # addendum 168: in the arms-only path the cell IS measured -
            # no drift re-measure; the flag is consumed here so the scoring
            # site sees a clean cell (the earlier delivery left the drift
            # check firing on identical configs in that path)
            print(
                f"  config drift: stored {done.get('wq')}/{done.get('kq')}/"
                f"{done.get('vq')} != planned {cell['wq']}/{cell['kq']}/"
                f"{cell['vq']} - re-measuring"
            )
            v7 = fst.setdefault("v7", {})
            v7.pop(key, None)
        if dry_run:
            print(
                f"plan: {fam} ctx={cell['ctx']} wq={cell['wq']} k={cell['kq']} "
                f"v={cell['vq']} est={cell['est_gib']} GiB"
            )
            results.append(entry)
            continue
        repo = registry_data.ROSTER.get(fam, fam)
        print(
            f"=== {fam} (model {fam_position[fam]} of {n_models}) "
            f"ctx={cell['ctx']} wq={cell['wq']} k={cell['kq']} v={cell['vq']}"
        )
        famdir = os.path.join(models_dir, fam)
        gguf = _acquire_missing_model(repo, fam, famdir, cell["wq"], state, False)
        if not gguf:
            entry["error"] = "could not acquire the quant"
            results.append(entry)
            continue
        results_dir = os.path.join(models_dir, "tournament-results", fam)
        os.makedirs(results_dir, exist_ok=True)
        log_path = os.path.join(results_dir, f"{fam}-ctx{cell['ctx']}-v7-server.log")
        extra = ["-c", str(cell["ctx"]), "--parallel", "1"]
        if cell["kq"] != "f16" or cell["vq"] != "f16":
            extra += ["-fa", "on", "--cache-type-k", cell["kq"], "--cache-type-v", cell["vq"]]
        proc, healthy = llama_server.start_server(
            gguf, port=port, extra_args=extra, log_path=log_path
        )
        try:
            if not healthy or not llama_server.wait_healthy(port, proc=proc):
                entry["error"] = "server did not come up"
                try:
                    with open(log_path, encoding="utf-8", errors="replace") as f:
                        for ln in f.read().splitlines()[-15:]:
                            print(f"    [server] {ln}")
                except OSError:
                    pass
                results.append(entry)
                continue
            breakdown = llama_server.memory_breakdown_gib(log_path)
            if corpus is None:
                corpus = corpus_from_artifact(port)
            try:
                preflight_template_sanity(port)
                probe_toks = preflight_reachable_grades(port, corpus, cell["ctx"])
                if probe_toks:
                    print(f"  preflight: {probe_toks}")
                suffix = "" if alloc_policy == "greedy" else f".{alloc_policy}"
                answers_path = os.path.join(
                    results_dir, f"{fam}-ctx{cell['ctx']}-v7{suffix}-answers.jsonl"
                )
                rec = run_cell(port, corpus, cell["ctx"], answers_path=answers_path)
            except TemplateMalfunction as e:
                entry["error"] = f"template_malfunction: {e}"
                results.append(entry)
                continue
            except PreflightError as e:
                entry["error"] = f"preflight: {e}"
                results.append(entry)
                continue
            except BudgetExceeded as e:
                entry["error"] = f"budget: {e}"
                results.append(entry)
                continue
            except Exception as e:
                entry["error"] = f"run_cell failed: {e}"
                results.append(entry)
                continue
            if breakdown is not None:
                rec["mem_census"] = breakdown
                devs = breakdown.get("devices") or {}
                v = devs.get("Vulkan0") or {}
                gpu_gib = (
                    (v.get("model_gib") or 0)
                    + (v.get("context_gib") or 0)
                    + (v.get("compute_gib") or 0)
                ) if v else breakdown.get("total_gib")
                # addendum 177: print the GPU footprint (the estimate's own
                # scope) - the whole-machine total was confusing to read next
                # to a GPU-scoped estimate (the author's ruling)
                if v:
                    print(
                        f"  census: GPU {gpu_gib:.2f} GiB (est {cell['est_gib']}) "
                        f"- weights {(v.get('model_gib') or 0):.2f}, "
                        f"context {(v.get('context_gib') or 0):.2f}, "
                        f"compute {(v.get('compute_gib') or 0):.2f}"
                    )
                else:
                    print(
                        f"  census: GPU {gpu_gib:.2f} GiB (est {cell['est_gib']}) "
                        f"- no device split; whole-machine fallback"
                    )
                # addendum 170: the MEASURED budget gate - the estimate is an
                # estimate; the verdict is llama-server's own GPU census. A cell
                # over the budget is an ERROR, never a scored result (the author's
                # ruling; the addendum-135 4.558 GiB cell was the precedent).
                if gpu_gib is not None and gpu_gib > budget_gib:
                    raise BudgetExceeded(
                        f"measured GPU {gpu_gib:.2f} GiB exceeds the {budget_gib} GiB "
                        f"budget (est was {cell['est_gib']}) - the cell is erased, "
                        f"never scored"
                    )
            skip_rescore = cell.pop("_skip_greedy_rescore", False)
            if skip_rescore:
                # addendum 168: greedy already measured - this launch exists
                # only for the arms; keep the stored record, no re-score
                rec = {k: done[k] for k in ("score", "max_score")}
                print(
                    f"  greedy kept (score {done['score']}/{done['max_score']})"
                    " - measuring arms only"
                )
            else:
                print(f"  score {rec['score']} / {rec['max_score']}")
            # addendum 166: the multi-arm cell record - every arm's config
            # and score in the SAME cell, one file; arms that agree with an
            # already-measured config need no re-measure (they ARE it)
            greedy_arm = {"wq": cell["wq"], "kq": cell["kq"], "vq": cell["vq"], **rec}
            if skip_rescore:
                greedy_arm = {**greedy_arm, "score": done["score"], "max_score": done["max_score"]}
            arms = {"greedy": greedy_arm}
            if multi_arm:
                measured_cfgs = {
                    (cell["wq"], cell["kq"], cell["vq"]),
                }
                for pol in ("stingy", "random"):
                    alt = alt_plans.get(pol, {}).get((fam, cell["ctx"]))
                    if alt is None:
                        continue
                    cfg = (alt["wq"], alt["kq"], alt["vq"])
                    if cfg in measured_cfgs:
                        print(f"  arm {pol}: same config as a measured arm - skipped")
                        continue
                    print(f"  arm {pol}: {cfg[0]}/{cfg[1]}/{cfg[2]} differs - measuring")
                    # the arm has its OWN launch cycle: a different weights
                    # quant is a different GGUF, different cache flags - the
                    # greedy server cannot serve it. Stop, relaunch, score.
                    llama_server.stop_server(proc, port)
                    try:
                        arm_gguf = _acquire_missing_model(
                            repo, fam, famdir, alt["wq"], state, False
                        )
                        if not arm_gguf:
                            arms[pol] = {
                                "wq": alt["wq"],
                                "kq": alt["kq"],
                                "vq": alt["vq"],
                                "error": "arm: could not acquire the quant",
                            }
                            continue
                        arm_extra = ["-c", str(cell["ctx"]), "--parallel", "1"]
                        if alt["kq"] != "f16" or alt["vq"] != "f16":
                            arm_extra += [
                                "-fa", "on", "--cache-type-k", alt["kq"],
                                "--cache-type-v", alt["vq"],
                            ]
                        proc, healthy = llama_server.start_server(
                            arm_gguf, port=port, extra_args=arm_extra,
                            log_path=log_path,
                        )
                        if not healthy or not llama_server.wait_healthy(port, proc=proc):
                            arms[pol] = {
                                "wq": alt["wq"], "kq": alt["kq"], "vq": alt["vq"],
                                "error": "arm: server did not come up",
                            }
                            continue
                        arm_rec = run_cell(port, corpus, cell["ctx"], answers_path=answers_path)
                        arms[pol] = {"wq": alt["wq"], "kq": alt["kq"], "vq": alt["vq"], **arm_rec}
                        measured_cfgs.add(cfg)
                    except Exception as e:
                        arms[pol] = {
                            "wq": alt["wq"], "kq": alt["kq"], "vq": alt["vq"],
                            "error": f"arm failed: {e}",
                        }
                for pol, a in arms.items():
                    if "score" in a:
                        print(
                            f"  arm {pol}: {a['wq']}/{a['kq']}/{a['vq']} "
                            f"-> {a['score']}/{a['max_score']}"
                        )
            if skip_rescore:
                # addendum 168: keep the stored record intact - only the
                # arms block updates (rec here is a stub; overwriting would
                # drop the stored per_grade/mem_census)
                stored = dict(done)
                stored["arms"] = arms
                v7[key] = stored
            else:
                v7[key] = {**cell, **rec, **({"arms": arms} if multi_arm else {})}
            entry.update(rec)
            if multi_arm:
                entry["arms"] = arms
        finally:
            llama_server.stop_server(proc, port)
            save_state(state_path, state)
        results.append(entry)
        pending.append(entry)
    _flush_model_commit()
    return results
