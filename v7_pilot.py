#!/usr/bin/env python3
"""v7 pilot - the fixed-memory-budget benchmark (session 42).

The design flip (the author's ruling): the benchmark no longer sizes
its noise to the model's window (v5/v6 asked "how much context do you
NEED"). It is HARD at low context and EASIER the larger the context,
so a large window is an asset. VT alone carries both axes:

  span s  - the token span the chain links are spread across.
            A window W < s is a STRUCTURAL fail (links unreachable).
  hops h  - the chain length (reasoning load per question).
            Degrades gracefully - small models get some hops right.

ONE FIXED CORPUS at S_MAX tokens serves every model: same bytes for
all contenders (fair cross-model comparison, unlike the per-model
depth budgeting of v5/v6). The question grid is (s, h) pairs; a cell
asks for the chain whose links live in the first s tokens with h hops.
Score(model, W) = pass mass over the grid, restricted to questions
the window can structurally reach (W >= s) - unreachable grades are
'excluded', not failed, so small-window cells keep a defined score.

The experiment: fix the memory budget M (default 4 GiB, to be refined
by measuring w/s later), enumerate the feasible allocations
(family, weight-quant, kv-quant, ctx) with llama.cpp -lv 5 total
<= M, and report the argmax - the best smarts/reach balance at M.

Reuses the serving stack (infra/llama_server), VT building blocks and
scoring semantics (ruler_gate, upstream fidelity), and the registry
roster/geometry (etc/registry_data) unchanged.
"""

from __future__ import annotations

import argparse
import json
import random
import string
import sys

import infra.llama_server as llama_server
import ruler_gate
from etc import registry_data

PORT = 8019
CORPUS_PATH = "state/v7-corpus.json"
STATE_PATH = "state/v7-pilot-state.json"
S_MAX = 262144
SPANS = [4096, 8192, 16384, 32768, 65536, 131072, 262144]
HOPS = [2, 4, 8, 16, 32]
K = 20  # questions per (span, hops) grade; pass = all h+1 names (upstream)
BUDGET_GIB = 4.0
CTX_GRID = [2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144]

# weight-quant bytes per parameter (the tournament's axis, addendum
# 140); the dict's order is the climb ladder, coarse to fine
W_QUANT_BPB = {
    "Q2_K": 0.40,
    "Q3_K": 0.48,
    "Q4_0": 0.59,
    "Q5_K": 0.72,
    "Q6_K": 0.82,
    "Q8_0": 1.06,
    "F16": 2.0,
}
W_LADDER = list(W_QUANT_BPB)
# kv-quant factor vs f16 bytes (the KV axes q4_0..f16; K and V
# caches carry the same geometry, so the factor applies per cache)
KV_QUANT_LADDER = ["q2_0", "q4_0", "q8_0", "f16"]
KV_QUANT_FACTOR = {"q2_0": 0.28125, "q4_0": 0.5625, "q8_0": 0.8125, "f16": 1.0}


def gen_name(rng: random.Random) -> str:
    return "".join(rng.choices(string.ascii_uppercase, k=ruler_gate.VT_NAME_LEN))


def build_corpus(port: int, s_max: int = S_MAX, seed: int = 7) -> dict:
    """One fixed VT corpus at ~s_max tokens, identical bytes every run.

    Structure: the shared context (noise haystack + every question's
    chain embedded) is built ONCE. A chain for span grade s has its
    links inserted among the sentences of the first ~s tokens - the
    span grade is the position, not a regenerated prompt. The query
    tail is per-question (the chain's base value + num_v = h+1), so a
    model's prefill is shared across questions via llama-server's
    prompt cache - the reach axis is measured, not re-paid 700x.
    Span boundaries are sentence-unit approximations, verified once
    against the live tokenizer; K chains per grade share the region.
    """
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
            for _ in range(K):
                questions.append({"span": s, "hops": h})
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
        questions[qi] = {**q, "names": names, "value": value}
    context = "\n".join(sentences).replace(". \n", ".\n")
    return {"context": context, "questions": questions, "s_max": s_max}


def question_prompt(corpus: dict, q: dict) -> str:
    """The per-question prompt: shared context + this chain's query tail."""
    return ruler_gate.VT_TEMPLATE.format(
        context=corpus["context"], query=q["value"], num_v=q["hops"] + 1
    )


def run_cell(port: int, corpus: dict, window: int) -> dict:
    """Score one allocation: pass mass over the (span, hops) grid.

    Questions with span > window are EXCLUDED (structurally
    unreachable), not failed - a small-window cell keeps a defined
    score over the reachable grid. Pass = all h+1 names (upstream's
    score_vt rule: a partial trace is a broken trace).
    """
    per_grade: dict[tuple[int, int], dict] = {}
    for q in corpus["questions"]:
        if q["span"] > window:
            continue
        key = (q["span"], q["hops"])
        g = per_grade.setdefault(key, {"pass": 0, "asked": 0})
        prompt = question_prompt(corpus, q)
        max_tokens = max(ruler_gate.VT_GEN_TOKENS, (q["hops"] + 1) * 12)
        answer = ruler_gate.ask(port, prompt, max_tokens=max_tokens)
        ok, _found = ruler_gate.score_vt(answer, q["names"])
        g["asked"] += 1
        g["pass"] += 1 if ok else 0
    score = 0.0
    asked_grades = 0
    for _key, g in sorted(per_grade.items()):
        if g["asked"]:
            score += g["pass"] / g["asked"]
            asked_grades += 1
    return {
        "window": window,
        "score": round(score, 3),
        "max_score": asked_grades,
        "per_grade": {
            f"{s}x{h}": {"pass": g["pass"], "asked": g["asked"]}
            for (s, h), g in sorted(per_grade.items())
        },
    }


PILOT_FAMILIES = 4  # the pilot scope: the first 4 families, param-ascending


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="v7 pilot corpus generation")
    ap.add_argument("--plan", action="store_true", help="print the allocation plan only")
    ap.add_argument("--budget-gib", type=float, default=BUDGET_GIB)
    ap.add_argument("--roster-limit", type=int, default=PILOT_FAMILIES)
    args = ap.parse_args(argv)
    if args.plan:
        print(json.dumps(greedy_allocations(args.budget_gib, args.roster_limit), indent=1))
        return 0
    return 0


def weights_gib(params_b: float, wq: str) -> float:
    return params_b * 1e9 * W_QUANT_BPB[wq] / (1 << 30)


def kv_gib(geom: dict, kvq: str, ctx: int) -> float:
    per_token = geom["kv_bytes_per_token_f16"] * KV_QUANT_FACTOR[kvq]
    return per_token * ctx / (1 << 30)


def kv_split_gib(geom: dict, kq: str, vq: str, ctx: int) -> float:
    """KV total with independent K and V quant rungs (each cache half of
    the f16 per-token bytes).
    """
    base = geom["kv_bytes_per_token_f16"] / 2.0
    per_token = base * (KV_QUANT_FACTOR[kq] + KV_QUANT_FACTOR[vq])
    return per_token * ctx / (1 << 30)


def family_geometry(name: str) -> dict | None:
    """The family's KV geometry from the registry store."""
    store = json.loads(registry_data.STORE.read_text())
    entry = store.get(name) or {}
    return entry.get("geometry")


def is_recurrent(name: str) -> bool:
    """Recurrent/SSM architectures carry no KV cache (RWKV7 et al.) -
    their memory is weights-only, so they are the CHEAPEST families at
    large ctx (session 42's architecture finding, applied to the reach
    race). Detected via the registry extract's model_type.
    """
    store = json.loads(registry_data.STORE.read_text())
    ex = (store.get(name) or {}).get("extract") or {}
    return str(ex.get("model_type") or "").lower().startswith("rwkv")


def kv_per_token_f16(name: str, geom: dict | None) -> float | None:
    """f16 KV bytes per token, or None when unknowable. Recurrent
    families return 0.0 (weights-only); the geometry column wins when
    present; MHA configs with null kv_heads (phi-1's shape) fall back
    to the attention heads (the geometry() contract already does this
    for head-dim, but nulls in the extract can leave geometry absent).
    """
    if is_recurrent(name):
        return 0.0
    if geom and geom.get("kv_bytes_per_token_f16"):
        return float(geom["kv_bytes_per_token_f16"])
    store = json.loads(registry_data.STORE.read_text())
    ex = (store.get(name) or {}).get("extract") or {}
    layers = ex.get("num_hidden_layers")
    heads = ex.get("num_attention_heads")
    kvh = ex.get("num_key_value_heads") or heads
    hd = ex.get("head_dim")
    if not hd and heads and ex.get("hidden_size"):
        hd = ex["hidden_size"] // heads  # MHA fallback (phi-1's shape)
    if not (layers and kvh and hd):
        return None
    return layers * 2 * kvh * hd * 2


def family_window(name: str) -> int:
    """The family's mechanical window (max_position_embeddings), if the
    registry knows it; unlimited otherwise (the pilot flags these)."""
    store = json.loads(registry_data.STORE.read_text())
    entry = store.get(name) or {}
    ex = entry.get("extract") or {}
    return ex.get("max_position_embeddings") or 0


def _alloc_total(name: str, p: float, geom: dict | None, wq: str, kq: str, vq: str, ctx: int) -> float | None:
    """Estimated total GiB for one config, or None when the family's
    memory cannot be estimated (no geometry and not recurrent)."""
    per_token = kv_per_token_f16(name, geom)
    if per_token is None:
        return None
    base = per_token / 2.0
    kv = base * (KV_QUANT_FACTOR[kq] + KV_QUANT_FACTOR[vq]) * ctx
    return weights_gib(p, wq) + kv / (1 << 30)


def greedy_allocations(budget_gib: float, roster_limit: int = 12) -> list[dict]:
    """The author's model-selection ruling (session 43): for each
    (family, ctx), start at the LOWEST quant everywhere - weights q=Q2_K,
    K=q2_0, V=q2_0 - and greedily climb: at each step try every
    single-axis one-notch upgrade (q, k, v), keep the one whose result
    lands CLOSEST to the budget without exceeding it, stop when no
    upgrade fits. The output is the largest config <= budget per
    (family, ctx) - the allocation the benchmark then scores.
    """
    rows = sorted(
        (registry_data.params_b(n) or 1e12, n) for n in registry_data.ROSTER
    )
    out = []
    for p, name in rows[:roster_limit]:
        geom = family_geometry(name)
        window = family_window(name)
        if kv_per_token_f16(name, geom) is None:
            continue
        for ctx in CTX_GRID:
            if window and ctx > window:
                continue
            wi, ki, vi = 0, 0, 0
            total = _alloc_total(
                name, p, geom, W_LADDER[wi], KV_QUANT_LADDER[ki], KV_QUANT_LADDER[vi], ctx
            )
            if total is None or total > budget_gib:
                continue
            while True:
                best = None
                for axis in range(3):
                    cand = (wi, ki, vi)
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
                    if t is not None and t <= budget_gib and (best is None or t > best[0]):
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


def plan_allocations(budget_gib: float, roster_limit: int = 12) -> list[dict]:
    """Enumerate feasible (family, wq, kvq, ctx) allocations under budget.

    The menu the budget sphere offers: biggest params per ctx and best
    quant per params. Returns param-ascending rows with est_gib (the
    estimate; the launch's -lv 5 accounting is the measured witness).
    """
    rows = sorted(
        (registry_data.params_b(n) or 1e12, n, r) for n, r in registry_data.ROSTER.items()
    )
    out = []
    for p, name, _repo in rows[:roster_limit]:
        geom = family_geometry(name)
        window = family_window(name)
        per_token = kv_per_token_f16(name, geom)
        if per_token is None:
            continue
        for wq in W_QUANT_BPB:
            for kvq in KV_QUANT_FACTOR:
                for ctx in CTX_GRID:
                    if window and ctx > window:
                        continue
                    kv = per_token * KV_QUANT_FACTOR[kvq] * ctx / (1 << 30)
                    total = weights_gib(p, wq) + kv
                    if total <= budget_gib:
                        out.append(
                            {
                                "family": name,
                                "params_b": p,
                                "wq": wq,
                                "kvq": kvq,
                                "ctx": ctx,
                                "est_gib": round(total, 2),
                            }
                        )
    return out


if __name__ == "__main__":
    sys.exit(main())
