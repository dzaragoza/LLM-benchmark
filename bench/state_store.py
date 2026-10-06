"""bench.state_store -- the never-re-measure store (session 38,
addendum 15: the full_benchmark.py refactor). The four task
namespaces (certify = fwe, certify_vt, certify_speed, certify_arc)
and their loaders; a cell is stored once and only once. Extracted
verbatim -- addendum citations stay."""

from __future__ import annotations

import json
import os
import random
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import infra.hf_download as hf_download
import infra.llama_server as llama_server
import ruler_gate
from bench import cells as bench_cells
from bench.constants import CORPUS_DEFAULT, RUNG_DEFAULT
from bench.tournament_helpers import _climb_csv_partial

COMBINED_TASKS = ("speed", "fwe", "vt", "arc")
ARC_CELL_K = 5  # questions per cell (the author's ruling: k=5, like VT's 5 names)
ARC_RUN_CTX = 4096  # ARC ignores context depth - one measurement, verdict applies to every rung


def _task_load(
    fst: dict[str, Any],
    depth: int,
    task: str,
    min_words: int,
    models_dir: str,
    fam: str,
    want: dict[str, Any] | None = None,
) -> dict[int, bool]:
    """The pass/fail cell map for one task at one rung, from whatever
    evidence already exists (combined mode: a cell's task measurement
    is loaded if present, measured later only if missing). `want` is
    the variant being certified (session 40, addendum 26): a stored
    cell measured under another variant does NOT load."""
    legacy = stored_variant(fst)
    if task == "vt":
        return {r: p >= 5 for r, p in vt_cells(fst, depth, want, legacy).items()}
    if task == "speed":
        return {r: p == 0 for r, p in speed_cells(fst, depth, want, legacy).items()}
    if task == "arc":
        return {r: p >= ARC_CELL_K for r, p in arc_cells(fst, want, legacy).items()}
    return certify_cells(fst, depth, min_words, models_dir, fam, want, legacy)


def arc_cell_questions(run: int) -> list[dict[str, Any]]:
    """Cell `run`'s k=5 ARC questions, deterministic: the full ARC-
    Challenge test split is shuffled with the fixed study seed, then
    cell r takes questions 5*(r-1)..5*r - the rung-independent
    analogue of FWE/VT's seed=run (ARC questions are a fixed pool;
    there is nothing to seed per rung)."""
    questions = hf_download.load_questions("ARC-Challenge", hf_download.ARC_NUM_DEFAULT)
    rng = random.Random(20260923)  # the study seed (author ruling 2026-09-23)
    rng.shuffle(questions)
    start = (run - 1) * ARC_CELL_K
    return questions[start : start + ARC_CELL_K]


def variant_of(
    fst: dict[str, Any],
    rung: str | None,
    default_k: str | None = None,
    default_v: str | None = None,
) -> dict[str, Any] | None:
    """The variant actually configured for a family at a rung
    (session 40, addendum 26): rung + KV quants, resolved the same
    way the certify controllers resolve them - the run's stored
    quants, then the tournament entry's, then the state default."""
    if not rung:
        return None
    run = (fst.get("runs") or {}).get(rung, {})
    entry = fst.get("tournament_entry") or {}
    return {
        "rung": rung,
        "kv_k": run.get("kv_quant_k") or entry.get("kv_quant_k") or default_k,
        "kv_v": run.get("kv_quant_v") or entry.get("kv_quant_v") or default_v,
    }


def stored_variant(
    fst: dict[str, Any],
    default_k: str | None = None,
    default_v: str | None = None,
) -> dict[str, Any] | None:
    """The variant the family's STORED selection resolves to - the
    variant every pre-override (legacy int) cell was measured under,
    by construction: before --force-rung the controllers always ran
    the stored selection."""
    rung = fst.get("selected") or (fst.get("tournament_entry") or {}).get("rung") or RUNG_DEFAULT
    return variant_of(fst, rung, default_k, default_v)


def _rec_variant(p: Any) -> tuple[Any, Any, Any] | None:
    if not isinstance(p, dict):
        return None
    return (p.get("rung"), p.get("kv_k"), p.get("kv_v"))


def _variant_key(v: dict[str, Any] | None) -> tuple[Any, Any, Any]:
    return (v or {}).get("rung"), (v or {}).get("kv_k"), (v or {}).get("kv_v")


def _int_cells(
    direct: Any,
    want: dict[str, Any] | None = None,
    legacy: dict[str, Any] | None = None,
) -> dict[int, int]:
    """{run: value} from a stored namespace, guarded (session 40,
    addendum 23, found by crosshair): a state file is loaded JSON -
    a corrupt non-numeric key once crashed int() and took the whole
    certify run down with it. Corrupt entries are skipped, not
    fatal; the re-grade never sees them.
    Variant filtering (session 40, addendum 26): a cell record may
    carry the variant that measured it ({v, rung, kv_k, kv_v}). When
    `want` is given, only matching-variant records load - a cell
    measured under another variant is UNMEASURED for this run, not
    silently trusted. Plain legacy records predate variant tracking
    and match only the family's STORED selection (`legacy`) - by
    construction that is the variant they were measured under."""
    cells: dict[int, int] = {}
    if not isinstance(direct, dict):
        return cells
    for r, p in direct.items():
        try:
            if isinstance(p, dict):
                value = int(p.get("v"))
            else:
                value = int(p)
            if want is not None:
                rec = _rec_variant(p)
                if rec is not None:
                    if rec != _variant_key(want):
                        continue
                elif _variant_key(legacy) != _variant_key(want):
                    continue
            cells[int(r)] = value
        except (TypeError, ValueError):
            continue
    return cells


def arc_cells(
    fst: dict[str, Any],
    want: dict[str, Any] | None = None,
    legacy: dict[str, Any] | None = None,
) -> dict[int, int]:
    """The ARC cell model: a cell is (family, run) with a 0..k graded
    record (correct answers of 5), stored in certify_arc ONCE per
    family - rung-independent (ARC ignores context depth). Pass at
    gold = 5/5."""
    return _int_cells(fst.get("certify_arc"), want, legacy)


def arc_pass(
    model: str,
    run: int,
    port: int,
) -> tuple[bool, dict[str, Any]]:
    """One ARC cell (session 38, addendum 6): k=5 deterministic
    questions, one server launch at ARC_RUN_CTX (rung-independent),
    strict-ARC protocol (logprob letter scoring, raw completions,
    max_tokens=1, temperature=0 - the retired arc_eval.py protocol,
    recovered). Returns (passed_at_gold, record)."""
    questions = arc_cell_questions(run)
    ctx = ARC_RUN_CTX
    log_path = os.path.join(
        os.path.dirname(model) or ".", os.path.basename(model) + f".arc-cell{run}.log"
    )
    proc, healthy = llama_server.start_server(
        model, port, ["-t", "8", "-c", str(ctx), "-ngl", "99"], log_path=log_path
    )
    try:
        if not healthy or not llama_server.wait_healthy(port, proc=proc):
            return False, {"error": "arc server did not come up"}
        correct = 0
        for q in questions:
            prompt = f"Question: {q['q']}\n"
            for lbl, text in q["choices"]:
                prompt += f"{lbl}) {text}\n"
            prompt += "\nThe answer is"
            r = llama_server.post_json(
                port,
                "/v1/completions",
                {"prompt": prompt, "max_tokens": 1, "temperature": 0, "logprobs": 20},
                timeout=120,
            )
            labels = {lb for lb, _ in q["choices"]}
            logps = {}
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
            correct += 1 if ok else 0
        return correct == len(questions), {"correct": correct, "k": len(questions)}
    finally:
        llama_server.stop_server(proc, port)


def cell_record(
    value: int,
    variant: dict[str, Any] | None = None,
    seconds: float | None = None,
) -> Any:
    """A stored cell record: the graded value plus, when a variant is
    known, the variant that measured it (session 40, addendum 26).
    Addendum 32: carries the wall seconds ({t}) - the per-test cost.
    Legacy plain-int records remain readable - they predate variant
    tracking and are attributed to the family's stored selection."""
    if variant is None:
        return value
    return {
        "v": value,
        "rung": variant.get("rung"),
        "kv_k": variant.get("kv_k"),
        "kv_v": variant.get("kv_v"),
        "t": round(seconds, 1) if seconds is not None else None,
    }


def _task_store(
    fst: dict[str, Any],
    depth: int,
    task: str,
    run: int,
    value: int,
    variant: dict[str, Any] | None = None,
    seconds: float | None = None,
) -> None:
    """Persist one cell's graded record in its own namespace (the
    combined controller never re-measures a stored cell-task).
    Session 40, addendum 26: the record carries the VARIANT that
    measured it ({v, rung, kv_k, kv_v}) - the author will try
    several variants per model, so a score without its variant is
    unattributable. Addendum 32: the record carries the WALL SECONDS
    the test took ({t}) - the per-test cost, so the expensive tests
    are visible and the cheap ones are too."""
    ns = {
        "vt": "certify_vt",
        "speed": "certify_speed",
        "arc": "certify_arc",
    }.get(task, "certify")
    record: Any = value
    if variant is not None:
        record = {
            "v": value,
            "rung": variant.get("rung"),
            "kv_k": variant.get("kv_k"),
            "kv_v": variant.get("kv_v"),
            "t": round(seconds, 1) if seconds is not None else None,
        }
    if task == "arc":
        fst.setdefault(ns, {})[str(run)] = record
        return
    fst.setdefault(ns, {}).setdefault(str(depth), {})[str(run)] = record


def _task_measure(
    task: str,
    model: str,
    depth: int,
    results_dir: str,
    run: int,
    port: int,
    kv_k: str | None,
    kv_v: str | None,
    min_words: int,
) -> tuple[bool, int, str, float]:
    """Measure one cell's one task. Returns (passed_at_gold, graded
    record, human line, wall seconds - session 40, addendum 32: the
    per-test cost, so the expensive tests are visible). The graded
    record is the speed stall count, the FWE word count, the VT 5-name
    count - all re-gradable at any bar later without re-measuring."""
    t0 = time.time()
    if task == "speed":
        ok, fv = bench_cells.speed_cell(
            model,
            depth + 2 * ruler_gate.ANSWER_HEADROOM,
            CORPUS_DEFAULT,
            results_dir,
            run,
            port,
            kv_quant_k=kv_k,
            kv_quant_v=kv_v,
        )
        stalls = int(fv.get("stalls") or 0)
        n_turns = int(fv.get("turns") or 0)
        return (
            ok,
            stalls,
            (f"speed: {stalls} stall(s) in {n_turns} turns -> {'PASS' if ok else 'FAIL'}"),
            time.time() - t0,
        )
    if task == "arc":
        ok, fv = arc_pass(model, run, port)
        correct = int(fv.get("correct") or 0)
        k_q = int(fv.get("k") or ARC_CELL_K)
        return (
            ok,
            correct,
            f"arc: {correct}/{k_q} answers -> {'PASS' if ok else 'FAIL'}",
            time.time() - t0,
        )
    if task == "vt":
        ok, fv = bench_cells.vt_pass(
            model,
            depth + 2 * ruler_gate.ANSWER_HEADROOM,
            results_dir,
            seed=run,
            port=port,
            kv_quant_k=kv_k,
            kv_quant_v=kv_v,
        )
        partial = int((fv.get("words_found") or [0])[0] or 0)
        return (
            ok,
            partial,
            f"vt: {partial}/5 names -> {'PASS' if ok else 'FAIL'}",
            time.time() - t0,
        )
    ok, fv = bench_cells.fwe_pass(
        model,
        depth + 2 * ruler_gate.ANSWER_HEADROOM,
        results_dir,
        seed=run,
        port=port,
        kv_quant_k=kv_k,
        kv_quant_v=kv_v,
        min_words=min_words,
    )
    words = fv.get("words_found") or []
    count = words[0] if words else int(ok)
    return (
        ok,
        count,
        f"fwe: {count}/{max(1, min_words)} word(s) -> {'PASS' if ok else 'FAIL'}",
        time.time() - t0,
    )


def certify_cells(
    fst: dict[str, Any],
    depth: int,
    min_words: int = 1,
    models_dir: str | None = None,
    fam: str | None = None,
    want: dict[str, Any] | None = None,
    legacy: dict[str, Any] | None = None,
) -> dict[int, bool]:
    """Session 37, addendum 8: the CELL model - a cell is (model, run
    number, step) and is NEVER measured twice. The historical cells
    come from the saved tournament_falls: climb s measured every
    rung up to and including its fall (fall == first FAILING rung),
    so cell (s, depth) PASSED iff the fall is None (topped out) or
    deeper than the rung, FAILED iff the fall IS the rung, and is
    UNMEASURED iff the climb stopped below it. The direct cells
    (certify runs) live in fst["certify"][str(depth)] as {run: pass}
    (or {run: words_found} once cells record word counts).
    Returns {run: passed} for every MEASURED cell.

    Re-grading (session 37, the 2/3 tightening): a direct cell that
    stored an INTEGER word count is graded at >= min_words exactly;
    cells stored as booleans were graded under the old 1/3 rule and
    are dropped from the measured set at a stricter bar - they are
    re-run, never silently trusted. Inherited tournament-fall cells
    are re-graded from their committed climb CSV (the `partial`
    word count) when models_dir/fam are given: the fall only says
    pass/fail at 3/3, but the CSV holds the actual words found, so
    the cell is MEASURED, not guessed."""
    cells: dict[int, bool] = {}
    for key, fall in (fst.get("tournament_falls") or {}).items():
        if min_words > 1:
            csv_words = _climb_csv_partial(models_dir, fam, int(key), depth)
            if csv_words is not None:
                cells[int(key)] = csv_words >= min_words
            continue
        if fall is None or fall > depth:
            cells[int(key)] = True
        elif fall == depth:
            cells[int(key)] = False
    direct = _int_cells((fst.get("certify") or {}).get(str(depth)), want, legacy)
    for key, words in direct.items():
        cells[int(key)] = words >= min_words
    return cells


def speed_cells(
    fst: dict[str, Any],
    depth: int,
    want: dict[str, Any] | None = None,
    legacy: dict[str, Any] | None = None,
) -> dict[int, int]:
    """The redesigned speed gate's cell model (session 38, addendum 2):
    cell = (model, rung, conversation r), stored in certify_speed as
    {run: stall count}. Gold bar = 0 stalls; the counts re-grade at
    any 'at most x stalls' bar later without re-measuring."""
    return _int_cells((fst.get("certify_speed") or {}).get(str(depth)), want, legacy)


def vt_cells(
    fst: dict[str, Any],
    depth: int,
    want: dict[str, Any] | None = None,
    legacy: dict[str, Any] | None = None,
) -> dict[int, int]:
    """The VT cell model: a cell is (model, run, task) and is NEVER
    measured twice. VT inherits NOTHING from the tournament (the
    climbs were FWE) - every cell is fresh, stored in the separate
    certify_vt namespace as {run: partial 0..5} (the graded score,
    like the FWE x/3 word count; pass = 5, re-gradable at any bar
    later without re-measuring)."""
    return _int_cells((fst.get("certify_vt") or {}).get(str(depth)), want, legacy)


def stamp(msg: str) -> None:
    import time

    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_state(path: str) -> dict[str, Any]:
    """The state file loader (moved here in the addendum-15 refactor:
    the bench modules save state mid-controller and must not import
    the orchestrator)."""
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"state file corrupt ({e}); starting fresh")
    return {"families": {}}


def save_state(path: str, state: dict[str, Any]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, path)
