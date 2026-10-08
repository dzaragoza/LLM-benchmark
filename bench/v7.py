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
"""

from __future__ import annotations

import json
import os
import random
import string
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import infra.llama_server as llama_server
import ruler_gate
from bench.certify import _acquire_missing_model
from bench.state_store import save_state
from etc import registry_data

S_MAX = 262144
SPANS = [2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144]
HOPS = [2, 4, 8, 16, 32]
K = 20  # questions per (span, hops) grade; pass = all h+1 names (upstream)
BUDGET_GIB = 4.0
CTX_GRID = [2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144]
PILOT_FAMILIES = 4

# weight-quant bytes per parameter; the dict's order is the climb
# ladder. Below Q8_0 the K-encoding (block-scaled K-quants) is the
# ruling; the top is F16 (32/64-bit ruled out - F32 doubles F16 for
# no inference gain, FP64 has no kernels).
W_QUANT_BPB = {
    "Q2_K": 0.40,
    "Q3_K": 0.48,
    "Q4_K": 0.56,
    "Q5_K": 0.72,
    "Q6_K": 0.82,
    "Q8_0": 1.06,
    "F16": 2.0,
}
W_LADDER = list(W_QUANT_BPB)
# kv-quant factor vs f16 bytes; K and V caches carry the same
# geometry. Below q8_0 the K-encoding is the ruling; top is f16.
KV_QUANT_LADDER = ["q2_K", "q4_K", "q8_0", "f16"]
KV_QUANT_FACTOR = {
    "q2_K": 0.16,
    "q4_K": 0.28125,
    "q8_0": 0.8125,
    "f16": 1.0,
}


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
    """
    if is_recurrent(name):
        return 0.0
    if geom and geom.get("kv_bytes_per_token_f16"):
        return float(geom["kv_bytes_per_token_f16"])
    ex = (_store().get(name) or {}).get("extract") or {}
    layers = ex.get("num_hidden_layers")
    heads = ex.get("num_attention_heads")
    kvh = ex.get("num_key_value_heads") or heads
    hd = ex.get("head_dim")
    if not hd and heads and ex.get("hidden_size"):
        hd = ex["hidden_size"] // heads
    if not (layers and kvh and hd):
        return None
    return layers * 2 * kvh * hd * 2


def _alloc_total(
    name: str, p: float, geom: dict | None, wq: str, kq: str, vq: str, ctx: int
) -> float | None:
    per_token = kv_per_token_f16(name, geom)
    if per_token is None:
        return None
    base = per_token / 2.0
    kv = base * (KV_QUANT_FACTOR[kq] + KV_QUANT_FACTOR[vq]) * ctx
    return weights_gib(p, wq) + kv / (1 << 30)


def greedy_allocations(budget_gib: float, roster_limit: int = PILOT_FAMILIES) -> list[dict]:
    """For each (family, ctx): start at (Q2_K, q2_K, q2_K) and greedily
    climb, taking the single-axis one-notch upgrade that lands closest
    to the budget without exceeding it. Output: the maximal config
    <= budget per (family, ctx), param-ascending."""
    rows = sorted((registry_data.params_b(n) or 1e12, n) for n in registry_data.ROSTER)
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


def gen_name(rng: random.Random) -> str:
    return "".join(rng.choices(string.ascii_uppercase, k=ruler_gate.VT_NAME_LEN))


def build_corpus(port: int, s_max: int = S_MAX, seed: int = 7) -> dict:
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
            for _ in range(K):
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


def run_cell(port: int, corpus: dict, window: int) -> dict:
    """Score one allocation: pass mass over the reachable (span, hops)
    grid. Questions with span > window are EXCLUDED (structurally
    unreachable), not failed. Pass = all h+1 names (upstream's rule)."""
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


CORPUS_ARTIFACT = "state/v7-corpus.json"


def corpus_from_artifact(port: int) -> dict:
    """The corpus as a repo artifact (the author's session-43 ruling):
    load state/v7-corpus.json when it matches the current grid
    constants; otherwise build once and write it. The artifact makes
    the corpus citable and byte-stable across machines - every
    contender runs on the exact same chains, and a rebuild is
    verifiable against the committed file."""
    grid = {
        "spans": SPANS,
        "hops": HOPS,
        "k": K,
        "s_max": S_MAX,
    }
    if os.path.exists(CORPUS_ARTIFACT):
        with open(CORPUS_ARTIFACT, encoding="utf-8") as f:
            art = json.load(f)
        if all(art.get(k_) == v for k_, v in grid.items()) and art.get("corpus"):
            return art["corpus"]
    corpus = build_corpus(port)
    os.makedirs(os.path.dirname(CORPUS_ARTIFACT), exist_ok=True)
    with open(CORPUS_ARTIFACT, "w", encoding="utf-8") as f:
        json.dump({"grid": grid, "corpus": corpus}, f)
    return corpus


def certify_v7(
    models_dir: str,
    state: dict[str, Any],
    state_path: str,
    port: int,
    dry_run: bool = False,
    budget_gib: float = BUDGET_GIB,
    roster_limit: int = PILOT_FAMILIES,
) -> list[dict[str, Any]]:
    """The v7 controller, in the certify shape: for each greedy cell,
    acquire the wq quant (the certify phase-1/2 path), launch in the
    bench.cells shape (ctx, -fa on, cache types), score the fixed
    corpus on the reachable grid, persist per cell under
    families/<name>/v7/<ctx>. An interrupted run resumes; measured
    cells are never re-measured."""
    cells = greedy_allocations(budget_gib, roster_limit)
    results: list[dict[str, Any]] = []
    corpus = None
    for cell in cells:
        fam = cell["family"]
        fst = state["families"].setdefault(fam, {})
        key = str(cell["ctx"])
        v7 = fst.setdefault("v7", {})
        done = v7.get(key) or {}
        entry = {**cell, "family": fam}
        if done.get("score") is not None:
            entry["skipped"] = f"already measured (score {done['score']})"
            results.append(entry)
            continue
        if dry_run:
            results.append(entry)
            continue
        repo = registry_data.ROSTER.get(fam, fam)
        print(f"=== {fam} ctx={cell['ctx']} wq={cell['wq']} k={cell['kq']} v={cell['vq']}")
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
            rec = run_cell(port, corpus, cell["ctx"])
            if breakdown is not None:
                rec["mem_census"] = breakdown
                print(
                    f"  census: weights {breakdown['weights_gib']:.2f} GiB, "
                    f"context {breakdown['context_gib']:.2f} GiB "
                    f"-> total {breakdown['total_gib']:.2f} GiB (est {cell['est_gib']})"
                )
            print(f"  score {rec['score']} / {rec['max_score']}")
            v7[key] = {**cell, **rec}
            entry.update(rec)
        finally:
            llama_server.stop_server(proc, port)
            save_state(state_path, state)
        results.append(entry)
    return results
