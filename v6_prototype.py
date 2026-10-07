#!/usr/bin/env python3
"""v6.0 prototype (session 41, addendum 91) - the structure test.

The author's spec: strict k=1 tasks (fwe = 1 word, vt = 1 name,
arc = 1 question), n=1 cell per gate per rung, NO speed gate (it is
assumed to pass; the bandwidth law predicts where it would bite).
One model climbs the rungs until the training window or a fwe/vt
death. Every cell records its wall seconds; the server log's
prefill/decode split is kept per rung so the bandwidth fit
(1/t = B_eff / [weights + KV(R)]) can later predict the speed-gate
rung. Reference v5 state is untouched: results go to
v6-results/v6-state.json.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

import infra.hf_download as hf_download
import infra.llama_server as llama_server
import ruler_gate

PORT = 8017
RESULTS_DIR = "v6-results"
STATE_PATH = os.path.join(RESULTS_DIR, "v6-state.json")

TOURNAMENT_DEPTHS = [4096, 8192, 16384, 32768, 65536, 131072, 262144]


def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"model": None, "rungs": {}, "arc": None, "params": None, "window": None}


def save_state(state: dict) -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1, sort_keys=True)
    os.replace(tmp, STATE_PATH)


def log_tail(log_path: str, n: int = 12) -> str:
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            return "\n".join(f.read().splitlines()[-n:])
    except OSError:
        return ""


def timing_from_log(log_path: str) -> dict | None:
    """llama-server's per-request verbose lines: prompt eval time and
    eval time (tokens, t/s). Last request in the log wins - the cell
    we just ran."""
    prompt_ts = eval_ts = None
    prompt_tok = eval_tok = None
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.search(r"prompt eval time .*?(\d+) tokens.*?([\d.]+) tokens/s", line)
                if m:
                    prompt_tok, prompt_ts = int(m.group(1)), float(m.group(2))
                m = re.search(r"eval time .*?(\d+) tokens.*?([\d.]+) tokens/s", line)
                if m and "prompt" not in line:
                    eval_tok, eval_ts = int(m.group(1)), float(m.group(2))
    except OSError:
        return None
    if eval_ts is None and prompt_ts is None:
        return None
    return {
        "prompt_tokens": prompt_tok,
        "prompt_tokens_per_s": prompt_ts,
        "gen_tokens": eval_tok,
        "gen_tokens_per_s": eval_ts,
    }


def window_from_log(log_path: str) -> int | None:
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            log = f.read()
    except OSError:
        return None
    m = re.search(r"training context of the model \((\d+)\)", log)
    if not m:
        m = re.search(r"n_ctx_train\s*=\s*(\d+)", log)
    return int(m.group(1)) if m else None


def fwe_cell_k1(port: int, depth: int, seed: int) -> tuple[bool, dict]:
    """Strict k=1 fwe: ONE word hidden, pass = the word recalled."""
    prompt, top_words = ruler_gate.build_fwe_task(port, depth, seed=seed, top_k=1)
    t0 = time.time()
    try:
        answer = ruler_gate.ask(port, prompt, max_tokens=ruler_gate.FWE_GEN_TOKENS)
    except ValueError as e:
        return False, {"error": str(e), "s": time.time() - t0}
    secs = time.time() - t0
    ok, partial = ruler_gate.score_fwe(answer, top_words, min_words=1)
    return ok, {
        "v": 1 if ok else 0,
        "partial": partial,
        "k": 1,
        "s": round(secs, 1),
        "answer": answer.strip()[:120],
        "word": top_words[0],
    }


def vt_cell_k1(port: int, depth: int, seed: int) -> tuple[bool, dict]:
    """Strict k=1 vt: ONE name (num_hops=0), pass = the name recalled."""
    prompt, names = ruler_gate.build_vt_task(port, depth, seed=seed, num_chains=1, num_hops=0)
    t0 = time.time()
    try:
        answer = ruler_gate.ask(port, prompt, max_tokens=ruler_gate.VT_GEN_TOKENS)
    except ValueError as e:
        return False, {"error": str(e), "s": time.time() - t0}
    secs = time.time() - t0
    ok, found = ruler_gate.score_vt(answer, names)
    return ok, {
        "v": 1 if ok else 0,
        "found": found,
        "k": 1,
        "s": round(secs, 1),
        "answer": answer.strip()[:120],
        "name": names[0],
    }


def assign_medals(state: dict) -> dict:
    """v6 medal rule (addendum 92): gold at a rung iff fwe & vt & arc all
    passed. Simple by design - the structure test's medal. Recomputed
    from stored cells each call, so a late arc cell backfills medals
    for rungs that passed while arc was still unmeasured."""
    arc_ok = (state.get("arc") or {}).get("v") == 1
    for _key, rec in state.get("rungs", {}).items():
        cells = rec.get("cells") or {}
        fwe_pass = cells.get("fwe", {}).get("v") == 1
        vt_pass = cells.get("vt", {}).get("v") == 1
        rec["medal"] = "gold" if (fwe_pass and vt_pass and arc_ok) else None
    return state


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, help="path to the f16 gguf")
    ap.add_argument("--depths", default=",".join(str(d) for d in TOURNAMENT_DEPTHS))
    ap.add_argument("--dry", action="store_true", help="print the plan, measure nothing")
    args = ap.parse_args()

    label = os.path.splitext(os.path.basename(args.model))[0]
    depths = [int(d) for d in args.depths.split(",")]
    print(f"v6.0 prototype: {label}, rungs {depths}")
    print("  strict k=1 (fwe 1 word, vt 1 name, arc 1 question), n=1, no speed gate")
    if args.dry:
        print("  (dry run: nothing measured)")
        return 0

    state = load_state()
    state["model"] = label
    os.makedirs(RESULTS_DIR, exist_ok=True)
    fam_dir = os.path.join(RESULTS_DIR, label)
    os.makedirs(fam_dir, exist_ok=True)

    # arc once per benchmark, at the first rung's context (k=1)
    arc_done = state.get("arc") is not None

    for depth in depths:
        key = str(depth)
        if key in state["rungs"] and state["rungs"][key].get("verdict"):
            print(f"  {depth}: already answered ({state['rungs'][key]['verdict']}) - skip")
            continue
        print(f"\n=== rung {depth} ===")
        rung_rec: dict = {"depth": depth, "cells": {}, "verdict": None}

        # one server launch per rung, shared by fwe and vt (same shape)
        log_path = os.path.join(fam_dir, f"{label}-rung{depth}-server.log")
        proc, healthy = llama_server.start_server(
            args.model,
            PORT,
            ["-c", str(depth), "--parallel", "1", "-fa", "on"],
            log_path=log_path,
        )
        try:
            if not healthy or not llama_server.wait_healthy(PORT, proc=proc):
                print("  server did not come up; log tail:")
                print(log_tail(log_path))
                rung_rec["verdict"] = "infeasible"
                rung_rec["window"] = window_from_log(log_path)
                state["rungs"][key] = rung_rec
                save_state(state)
                break
            window = window_from_log(log_path)
            state["window"] = window
            if window is not None and window < depth:
                print(f"  training window {window} < rung {depth} - terminal")
                rung_rec["verdict"] = "window"
                state["rungs"][key] = rung_rec
                save_state(state)
                break
            print(f"  window: {window}")

            # fwe k=1
            ok, rec = fwe_cell_k1(PORT, depth, seed=depth)
            rec["timing"] = timing_from_log(log_path)
            rung_rec["cells"]["fwe"] = rec
            print(f"  fwe: {'PASS' if ok else 'FAIL'} ({rec.get('s', 0)}s) word={rec.get('word')}")
            # vt k=1
            ok2, rec2 = vt_cell_k1(PORT, depth, seed=depth + 1)
            rec2["timing"] = timing_from_log(log_path)
            rung_rec["cells"]["vt"] = rec2
            vt_line = f"  vt: {'PASS' if ok2 else 'FAIL'} ({rec2.get('s', 0)}s)"
            print(vt_line + f" name={rec2.get('name')}")
        finally:
            llama_server.stop_server(proc, PORT)

        verdict = "pass" if (ok and ok2) else "dead"
        rung_rec["verdict"] = verdict
        state["rungs"][key] = rung_rec
        # v6 medal rule (addendum 92): fwe & vt & arc all pass = gold at
        # the rung; arc runs once per benchmark, so the medal is assigned
        # after the arc cell lands - re-decided over the stored rungs.
        state = assign_medals(state)
        save_state(state)
        print(f"  rung {depth} verdict: {verdict}")
        if verdict != "pass":
            break

    # arc once (k=1), after the ladder - shallow context, any rung's server is fine
    if not arc_done:
        print("\n=== arc (once, k=1) ===")
        q_ok = None
        try:
            questions = hf_download.load_questions("ARC-Challenge", hf_download.ARC_NUM_DEFAULT)
            import random as _random

            rng = _random.Random(20260923)
            rng.shuffle(questions)
            q = questions[0]
            log_path = os.path.join(fam_dir, f"{label}-arc.log")
            proc, healthy = llama_server.start_server(
                args.model, PORT, ["-t", "8", "-c", "4096", "-ngl", "99"], log_path=log_path
            )
            try:
                if healthy and llama_server.wait_healthy(PORT, proc=proc):
                    prompt = f"Question: {q['q']}\n"
                    for lbl, text in q["choices"]:
                        prompt += f"{lbl}) {text}\n"
                    prompt += "\nThe answer is"
                    t0 = time.time()
                    r = llama_server.post_json(
                        PORT,
                        "/v1/completions",
                        {"prompt": prompt, "max_tokens": 1, "temperature": 0, "logprobs": 20},
                        timeout=120,
                    )
                    secs = round(time.time() - t0, 2)
                    labels = {lb for lb, _ in q["choices"]}
                    logps: dict = {}
                    try:
                        top = r["choices"][0]["logprobs"]["content"][0]["top_logprobs"]
                        for entry in top:
                            tok = entry["token"].strip().rstrip(").,")
                            if tok in labels:
                                logps[tok] = max(logps.get(tok, -999), entry["logprob"])
                    except (KeyError, IndexError, TypeError):
                        pass
                    if logps:
                        q_ok = max(logps, key=lambda k: logps[k]) == q["ans"]
                    else:
                        gen = r["choices"][0]["text"].strip()
                        q_ok = len(gen) > 0 and gen[0] in labels and gen[0] == q["ans"]
                    state["arc"] = {"v": 1 if q_ok else 0, "k": 1, "s": secs, "answer": q["ans"]}
                    assign_medals(state)
                    save_state(state)
                    print(f"  arc: {'PASS' if q_ok else 'FAIL'} ({secs}s) ans={q['ans']}")
            finally:
                llama_server.stop_server(proc, PORT)
        except Exception as e:  # noqa: BLE001 - the prototype reports and continues
            print(f"  arc failed: {e}")

    print("\n=== medals ===")
    golds = [
        k
        for k, r in sorted(state.get("rungs", {}).items(), key=lambda kv: int(kv[0]))
        if r.get("medal") == "gold"
    ]
    print("  " + (", ".join(f"gold@{k}" for k in golds) if golds else "none"))

    # the bandwidth summary: per-rung decode t/s from the cells' timing splits
    print("\n=== bandwidth series (decode t/s per rung) ===")
    for key in sorted(state["rungs"], key=int):
        rec = state["rungs"][key]
        for gate in ("fwe", "vt"):
            cell = rec.get("cells", {}).get(gate)
            if cell and cell.get("timing") and cell["timing"].get("gen_tokens_per_s"):
                print(f"  {key} {gate}: {cell['timing']['gen_tokens_per_s']:.1f} t/s decode")
    print("\nstate:", STATE_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
