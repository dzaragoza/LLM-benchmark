#!/usr/bin/env python3
"""v6.0 prototype (session 41, addenda 91-95) - the structure test.

The author's spec: strict k=1 tasks (fwe = 1 word, vt = 1 name,
arc = 1 question), n=1 cell per gate per rung, NO speed gate (the
bandwidth law predicts where it would bite). ARC RUNS FIRST per
family: if the arc cell dies, the model is dead by definition and no
rung is measured. The ladder then climbs ALL rungs to 256k - a
death at one rung does not stop the climb. Each rung's result is
gold (fwe & vt & arc all passed) or dead. Families run in the
registry's PARAM-ASCENDING order (the first 32 of the roster);
weights are acquired on demand (the certify controllers' own
phase-1/2 path). STATE IS THE FULL_BENCHMARK SHAPE (families/
<name>/{tournament_entry, verdicts, certify_*}) in its own file,
state/v6-benchmark-state.json - v5's state is untouched, and the v6
state reads with the same tooling (kill rates, golds). Results
upload to git at the end of every family; every cell records wall
seconds plus the server log's prefill/decode split, feeding the
bandwidth fit.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time

import infra.hf_download as hf_download
import infra.llama_server as llama_server
import ruler_gate
from bench.certify import _acquire_missing_model
from etc import registry_data

PORT = 8017
MODELS_DIR = "./models"
STATE_PATH = "state/v6-benchmark-state.json"
FAMILIES_LIMIT = 32

TOURNAMENT_DEPTHS = [4096, 8192, 16384, 32768, 65536, 131072, 262144]


def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"families": {}}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1, sort_keys=True)
    os.replace(tmp, STATE_PATH)


def roster_param_ascending(limit: int) -> list[tuple[str, str]]:
    """The registry roster, param-ascending, first `limit` families:
    (name, repo) pairs."""
    rows = sorted(
        ((registry_data.params_b(n) or 1e12, n, r) for n, r in registry_data.ROSTER.items())
    )
    return [(n, r) for _p, n, r in rows[:limit]]


def log_tail(log_path: str, n: int = 12) -> str:
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            return "\n".join(f.read().splitlines()[-n:])
    except OSError:
        return ""


def timing_from_log(log_path: str) -> dict | None:
    """llama-server's per-request verbose lines: prompt eval time and
    eval time (tokens, t/s). Last request in the log wins."""
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


def cell_record(passed: bool, seconds: float, **extra: object) -> dict:
    rec: dict = {"v": 1 if passed else 0, "t": round(seconds, 1)}
    rec.update(extra)
    return rec


def fwe_cell_k1(port: int, depth: int, seed: int) -> tuple[bool, dict]:
    """Strict k=1 fwe: ONE word hidden, pass = the word recalled."""
    prompt, top_words = ruler_gate.build_fwe_task(port, depth, seed=seed, top_k=1)
    t0 = time.time()
    try:
        answer = ruler_gate.ask(port, prompt, max_tokens=ruler_gate.FWE_GEN_TOKENS)
    except ValueError as e:
        return False, cell_record(False, time.time() - t0, error=str(e))
    secs = time.time() - t0
    ok, partial = ruler_gate.score_fwe(answer, top_words, min_words=1)
    return ok, cell_record(
        ok, secs, partial=partial, answer=answer.strip()[:120], word=top_words[0]
    )


def vt_cell_k1(port: int, depth: int, seed: int) -> tuple[bool, dict]:
    """Strict k=1 vt: ONE name (num_hops=0), pass = the name recalled."""
    prompt, names = ruler_gate.build_vt_task(port, depth, seed=seed, num_chains=1, num_hops=0)
    t0 = time.time()
    try:
        answer = ruler_gate.ask(port, prompt, max_tokens=ruler_gate.VT_GEN_TOKENS)
    except ValueError as e:
        return False, cell_record(False, time.time() - t0, error=str(e))
    secs = time.time() - t0
    ok, found = ruler_gate.score_vt(answer, names)
    return ok, cell_record(ok, secs, found=found, answer=answer.strip()[:120], name=names[0])


def arc_cell_k1(model: str, fam_dir: str, label: str) -> tuple[bool, dict]:
    """Strict k=1 arc: one question from the deterministic shuffled
    pool, the letter-logprob protocol. Runs FIRST per family - a dead
    arc cell means the model is dead by definition."""
    questions = hf_download.load_questions("ARC-Challenge", hf_download.ARC_NUM_DEFAULT)
    rng = random.Random(20260923)
    rng.shuffle(questions)
    q = questions[0]
    log_path = os.path.join(fam_dir, f"{label}-arc.log")
    proc, healthy = llama_server.start_server(
        model, PORT, ["-t", "8", "-c", "4096", "-ngl", "99"], log_path=log_path
    )
    try:
        if not healthy or not llama_server.wait_healthy(PORT, proc=proc):
            print("  arc server did not come up; log tail:")
            print(log_tail(log_path))
            return False, {"v": 0, "error": "server did not come up"}
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
            ok = max(logps, key=lambda k: logps[k]) == q["ans"]
        else:
            gen = r["choices"][0]["text"].strip()
            ok = len(gen) > 0 and gen[0] in labels and gen[0] == q["ans"]
        return ok, {"v": 1 if ok else 0, "t": secs, "answer": q["ans"]}
    finally:
        llama_server.stop_server(proc, PORT)


def assign_medals(state: dict, fam: str) -> None:
    """v6 medal rule (addendum 92): gold at a rung iff fwe & vt & arc
    all passed. Recomputed from stored cells - order-independent."""
    fst = state["families"][fam]
    arc_ok = (fst.get("certify_arc") or {}).get("1", {}).get("v") == 1
    for _depth, run in (fst.get("runs") or {}).items():
        fwe_ok = (fst.get("certify") or {}).get(_depth, {}).get("1", {}).get("v") == 1
        vt_ok = (fst.get("certify_vt") or {}).get(_depth, {}).get("1", {}).get("v") == 1
        run["medal"] = "gold" if (fwe_ok and vt_ok and arc_ok) else None


def family_verdict(fst: dict, depth: str) -> str | None:
    """The v6 rung verdict from stored cells: gold/dead (or None when
    unmeasured)."""
    fwe_ok = (fst.get("certify") or {}).get(depth, {}).get("1", {}).get("v") == 1
    vt_ok = (fst.get("certify_vt") or {}).get(depth, {}).get("1", {}).get("v") == 1
    arc_ok = (fst.get("certify_arc") or {}).get("1", {}).get("v") == 1
    if fwe_ok and vt_ok and arc_ok:
        return "gold"
    return "dead"


def upload(label: str, what: str) -> None:
    """Commit and push the artifacts (addendum 94); never fatal."""
    try:
        import git_push

        sha = git_push.push_working_tree(
            f"v6 prototype artifacts {time.strftime('%Y-%m-%d %H:%M')}: {label} {what}"
        )
        print(f"  pushed -> {sha}")
    except Exception as e:  # noqa: BLE001 - the upload never stops the prototype
        print(f"  upload failed (results stay local): {e}")


def run_family(name: str, repo: str, state: dict, depths: list[int]) -> None:
    print(f"\n########## {name} ({repo}) ##########")
    famdir = os.path.join(MODELS_DIR, name)
    os.makedirs(famdir, exist_ok=True)
    fst = state["families"].setdefault(name, {})

    # acquire on demand (the certify controllers' own path)
    spec = repo
    gguf = _acquire_missing_model(spec, name, famdir, "f16", state, False)
    if not gguf:
        print("  could not acquire the f16 rung - skipping family")
        return
    print(f"  entry: {gguf}")
    label = os.path.splitext(os.path.basename(gguf))[0]

    # arc FIRST (addendum 93): dead arc = dead by definition
    if not (fst.get("certify_arc") or {}):
        print("  === arc (first, k=1) ===")
        ok, arc_rec = arc_cell_k1(gguf, famdir, label)
        fst["certify_arc"] = {"1": arc_rec}
        save_state(state)
        print(f"  arc: {'PASS' if ok else 'FAIL'} ({arc_rec.get('t', 0)}s)")
    arc_ok = (fst.get("certify_arc") or {}).get("1", {}).get("v") == 1
    if not arc_ok:
        print("  arc dead -> model dead by definition; no rung measured")
        upload(name, "arc-dead shortcut")
        return

    for depth in depths:
        dkey = str(depth)
        have_fwe = (fst.get("certify") or {}).get(dkey, {}).get("1")
        have_vt = (fst.get("certify_vt") or {}).get(dkey, {}).get("1")
        if have_fwe and have_vt:
            print(f"  rung {depth}: already measured - skip")
            continue
        print(f"  === rung {depth} ===")
        log_path = os.path.join(famdir, f"{label}-rung{depth}-server.log")
        proc, healthy = llama_server.start_server(
            gguf, PORT, ["-c", str(depth), "--parallel", "1", "-fa", "on"], log_path=log_path
        )
        try:
            if not healthy or not llama_server.wait_healthy(PORT, proc=proc):
                print("  server did not come up; log tail:")
                print(log_tail(log_path))
                window = window_from_log(log_path)
                if window is not None and window < depth:
                    print(f"  training window {window} < rung {depth} - terminal")
                else:
                    print(f"  rung {depth} infeasible on this machine - skipped")
                continue
            window = window_from_log(log_path)
            if window is not None and window < depth:
                print(f"  training window {window} < rung {depth} - terminal")
                continue
            if not have_fwe:
                ok, rec = fwe_cell_k1(PORT, depth, seed=depth)
                rec["timing"] = timing_from_log(log_path)
                fst.setdefault("certify", {})[dkey] = {"1": rec}
                save_state(state)
                print(f"  fwe: {'PASS' if ok else 'FAIL'} ({rec.get('t', 0)}s)")
            if not have_vt:
                ok2, rec2 = vt_cell_k1(PORT, depth, seed=depth + 1)
                rec2["timing"] = timing_from_log(log_path)
                fst.setdefault("certify_vt", {})[dkey] = {"1": rec2}
                save_state(state)
                vt_line = f"  vt: {'PASS' if ok2 else 'FAIL'} ({rec2.get('t', 0)}s)"
                print(vt_line + f" name={rec2.get('name')}")
        finally:
            llama_server.stop_server(proc, PORT)
        verdict = family_verdict(fst, dkey)
        fst.setdefault("runs", {})[dkey] = {"medal": "gold" if verdict == "gold" else None}
        assign_medals(state, name)
        save_state(state)
        print(f"  rung {depth} verdict: {verdict}")
        # addendum 93: a death does NOT stop the climb

    assign_medals(state, name)
    save_state(state)
    golds = [
        int(d)
        for d, r in sorted((fst.get("runs") or {}).items(), key=lambda kv: int(kv[0]))
        if r.get("medal") == "gold"
    ]
    print("  medals: " + (", ".join(f"gold@{g}" for g in golds) if golds else "none"))
    upload(name, "ladder complete")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--families",
        default=None,
        help="comma-separated family names (default: first 32 of the roster)",
    )
    ap.add_argument("--depths", default=",".join(str(d) for d in TOURNAMENT_DEPTHS))
    ap.add_argument("--dry", action="store_true", help="print the plan, measure nothing")
    args = ap.parse_args()

    depths = [int(d) for d in args.depths.split(",")]
    if args.families:
        fams = [(n, registry_data.ROSTER.get(n, n)) for n in args.families.split(",")]
    else:
        fams = roster_param_ascending(FAMILIES_LIMIT)
    print(f"v6.0 prototype: {len(fams)} families, rungs {depths}")
    print("  strict k=1, n=1, no speed gate, arc first, climb never stops")
    if args.dry:
        for name, repo in fams:
            print(f"  plan: {name} ({repo})")
        return 0

    state = load_state()
    for name, repo in fams:
        run_family(name, repo, state, depths)

    # the summary across families: per-gate per-cell wall time + medals
    print("\n=== v6 summary ===")
    for name in sorted(state["families"]):
        fst = state["families"][name]
        golds = [
            int(d)
            for d, r in sorted((fst.get("runs") or {}).items(), key=lambda kv: int(kv[0]))
            if r.get("medal") == "gold"
        ]
        print(f"  {name}: " + (", ".join(f"gold@{g:,}" for g in golds) if golds else "no gold"))
        for gate, ns in (("fwe", "certify"), ("vt", "certify_vt")):
            cells = fst.get(ns) or {}
            ts = [
                (int(d), c["1"]["t"])
                for d, c in sorted(cells.items(), key=lambda kv: int(kv[0]))
                if c.get("1", {}).get("t") is not None
            ]
            if ts:
                print(f"    {gate}: " + ", ".join(f"{d // 1024}k={s:.0f}s" for d, s in ts))
        arc = (fst.get("certify_arc") or {}).get("1", {})
        if arc.get("t") is not None:
            print(f"    arc: {arc['t']:.1f}s")
    print("\nstate:", STATE_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
