"""bench.certify -- the sequential controller and the medals (session
38, addendum 15: the full_benchmark.py refactor). The Wilson
sequential accept/dead per task, the combined controller (one cell,
three-to-four tasks), TASK_PASS_BARS (the difficulty knob) and
combined_medal (the confidence tiers). Extracted verbatim."""

from __future__ import annotations

import math
import os
import sys
from typing import Any, cast

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import infra.hf_download as hf_download
import ruler_gate
from bench import cells as bench_cells
from bench import state_store as bench_state_store
from bench.constants import COMBINED_TASKS, CORPUS_DEFAULT, RUNG_DEFAULT, TOURNAMENT_CLIMBS
from bench.state_store import (
    _task_load,
    arc_cells,
    certify_cells,
    save_state,
    speed_cells,
    vt_cells,
)

local_rung = hf_download.local_rung


def wilson_interval(k: int, n: int, z: float = 1.0) -> tuple[float, float]:
    """The Wilson score interval at 1 sigma (addendum 42): the
    honest CI for a binomial hold fraction at tournament n. At n=15
    a 2-sigma interval is too wide to separate models - 1 sigma is
    the pre-registered choice."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return center - half, center + half


CERTIFY_LEVELS = ["at_least_one", "1_sigma", "2_sigma"]


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


def certify_rung(
    depth: int,
    level: str,
    specs: list[str],
    models_dir: str,
    state: dict[str, Any],
    state_path: str,
    port: int,
    dry_run: bool,
    min_words: int = 1,
    task: str = "fwe",
) -> list[dict[str, Any]]:
    """Session 37, addendum 8 (the practitioner-certified map): fill
    ONE rung - the sequential controller of session-36 addendum 50.
    Session 37, addendum 18: the certification TYPE is chosen per
    rung - at_least_one (the practitioner's question 1: any model
    with a pass at the step), 1_sigma (reliable: 1-sigma Wilson
    lower bound >= 0.5, count >= half of n=20) or 2_sigma
    (conservative: the same bar at 2 sigma). Candidates are the
    given families, ordered by promise (existing passes at the
    rung, then reliable depth). Each candidate is tested cell by
    cell (direct single-rung FWE at the rung, seed = the run
    number, cells already measured are NEVER re-run) until EARLY
    ACCEPT or EARLY REJECT (mathematically dead: even passing
    every remaining cell cannot reach the bar).
    The RAM-ceiling assumption replaces the w/s measurement
    (session 37, addendum 15): a config selected under the ceiling
    has enough bandwidth to clear the 5 w/s reader line - w/s is
    not measured in the benchmark (a waste of time; the author's
    ruling); a speed falsification probe stays available for later
    if a recommendation is ever doubted. The first accepted
    candidate ANSWERS the rung; the rest are skipped (the
    practitioner wants ONE model per rung)."""
    if level not in CERTIFY_LEVELS:
        raise ValueError(f"unknown certify level {level!r}")
    n_total = TOURNAMENT_CLIMBS
    floor = 1 if level == "at_least_one" else math.ceil(0.5 * n_total)
    z = 0.0 if level == "at_least_one" else float(level.split("_")[0])
    order: list[tuple[str, dict[str, Any], dict[int, bool], str]] = []
    for spec in specs:
        fam = os.path.basename(spec.partition("=")[0].rstrip("/"))
        fst = state["families"].get(fam, {})
        if task == "vt":
            cells = {r: p >= 5 for r, p in vt_cells(fst, depth).items()}
        elif task == "speed":
            cells = {r: p == 0 for r, p in speed_cells(fst, depth).items()}
        else:
            cells = certify_cells(fst, depth, min_words, models_dir, fam)
        order.append((fam, fst, cells, spec))

    def promise(item):
        fam, fst, cells, _spec = item
        k = sum(1 for ok in cells.values() if ok)
        saved_rank = state.get("tournament") or []
        rd = 0
        for tr in saved_rank:
            if tr.get("family") == fam:
                rd = tr.get("reliable_depth") or 0
        return (-k, -rd, fam)

    order.sort(key=promise)
    results: list[dict[str, Any]] = []
    answered = False
    for fam, fst, cells0, spec in order:
        cells = dict(cells0)
        measured = len(cells)
        k = sum(1 for ok in cells.values() if ok)
        entry = {
            "family": fam,
            "depth": depth,
            "level": level,
            "historical_passes": k,
            "historical_cells": measured,
        }
        print()
        print("-" * 60)
        print(f"  {fam}: {k}/{measured} cells measured, {n_total - measured} unmeasured")
        if answered:
            entry["skipped"] = "rung already answered"
            print("  SKIPPED - the rung is already answered")
            results.append(entry)
            continue
        famdir = os.path.join(models_dir, fam)
        rung = (
            fst.get("selected") or (fst.get("tournament_entry") or {}).get("rung") or RUNG_DEFAULT
        )
        run = (fst.get("runs") or {}).get(rung or "", {})
        model = (
            run.get("file")
            or (fst.get("tournament_entry") or {}).get("file")
            or (local_rung(famdir, rung) if rung else None)
        )
        if (not model or not os.path.isfile(model)) and spec:
            acquired = _acquire_missing_model(spec, fam, famdir, rung, state, dry_run)
            if acquired:
                model = acquired
        if not model or not os.path.isfile(model):
            entry["error"] = f"model file not found ({model})"
            print(f"  ERROR: {entry['error']}")
            results.append(entry)
            continue
        kv_k = (
            run.get("kv_quant_k")
            or (fst.get("tournament_entry") or {}).get("kv_quant_k")
            or state.get("kv_quant_k")
        )
        kv_v = (
            run.get("kv_quant_v")
            or (fst.get("tournament_entry") or {}).get("kv_quant_v")
            or state.get("kv_quant_v")
        )
        results_dir = os.path.join(models_dir, "tournament-results", fam)
        os.makedirs(results_dir, exist_ok=True)
        ns = {"vt": "certify_vt", "speed": "certify_speed", "arc": "certify_arc"}.get(
            task, "certify"
        )
        direct = dict((fst.get(ns) or {}).get(str(depth)) or {})
        ran = 0
        verdict = None
        while True:
            lo, _ = wilson_interval(k, measured, z) if measured else (0.0, 0.0)
            remaining = n_total - measured
            # the plan: how many consecutive passes certify, how many
            # consecutive fails kill - the author's addendum-20 request
            to_accept = None
            to_dead = None
            if level == "at_least_one":
                if k >= 1:
                    verdict = "accept"
                    break
                if remaining == 0:
                    verdict = "dead"
                    break
                to_accept = 1
            else:
                if measured >= floor and lo >= 0.5:
                    verdict = "accept"
                    break
                best_k = k + remaining
                best_lo, _ = wilson_interval(best_k, n_total, z)
                if best_lo < 0.5 or best_k < floor:
                    verdict = "dead"
                    break
                for j in range(1, remaining + 1):
                    lo_j, _ = wilson_interval(k + j, measured + j, z)
                    if measured + j >= floor and lo_j >= 0.5:
                        to_accept = j
                        break
                for j in range(1, remaining + 1):
                    bk = k + (remaining - j)
                    bl, _ = wilson_interval(bk, n_total, z)
                    if bl < 0.5 or bk < floor:
                        to_dead = j
                        break
            if ran == 0:
                plan = (
                    f"  PLAN @ {depth:,}: {measured}/{n_total} cells measured, {remaining} left - "
                )
                plan += (
                    f"{to_accept if to_accept else remaining} consecutive pass(es) certify; "
                    if to_accept is not None or level == "at_least_one"
                    else ""
                )
                plan += (
                    f"{to_dead if to_dead else remaining} consecutive fail(s) kill"
                    if to_dead is not None
                    else f"cannot die this rung ({remaining} cells left)"
                )
                print(plan)
            if dry_run:
                verdict = "would-run"
                break
            next_run = min(r for r in range(1, n_total + 1) if r not in cells)
            if task == "speed":
                ok, fv = bench_cells.speed_cell(
                    model,
                    depth + 2 * ruler_gate.ANSWER_HEADROOM,
                    CORPUS_DEFAULT,
                    results_dir,
                    next_run,
                    port,
                    kv_quant_k=kv_k,
                    kv_quant_v=kv_v,
                )
                ran += 1
                cells[next_run] = ok
                stalls = int(fv.get("stalls") or 0)
                n_turns = int(fv.get("turns") or 0)
                direct[str(next_run)] = stalls
                measured += 1
                k += 1 if ok else 0
                fst.setdefault("certify_speed", {})[str(depth)] = direct
                save_state(state_path, state)
                print(
                    f"  speed cell (conv {next_run}, {depth:,} tok): "
                    f"{stalls} stall(s) in {n_turns} turns -> "
                    f"{'PASS' if ok else 'FAIL'} -> {k}/{measured} "
                    f"(1s lower bound {wilson_interval(k, measured)[0]:.3f})"
                )
                continue
            if task == "vt":
                ok, fv = bench_cells.vt_pass(
                    model,
                    depth + 2 * ruler_gate.ANSWER_HEADROOM,
                    results_dir,
                    seed=next_run,
                    port=port,
                    kv_quant_k=kv_k,
                    kv_quant_v=kv_v,
                )
                ran += 1
                cells[next_run] = ok
                partial = int((fv.get("words_found") or [0])[0] or 0)
                direct[str(next_run)] = partial
                measured += 1
                k += 1 if ok else 0
                fst.setdefault("certify_vt", {})[str(depth)] = direct
                save_state(state_path, state)
                print(
                    f"  vt cell (run {next_run}, {depth:,} tok): "
                    f"{partial}/5 names -> {'PASS' if ok else 'FAIL'} -> "
                    f"{k}/{measured} "
                    f"(1s lower bound {wilson_interval(k, measured)[0]:.3f})"
                )
                continue
            ok, fv = bench_cells.fwe_pass(
                model,
                depth + 2 * ruler_gate.ANSWER_HEADROOM,
                results_dir,
                seed=next_run,
                port=port,
                kv_quant_k=kv_k,
                kv_quant_v=kv_v,
                min_words=min_words,
            )
            ran += 1
            cells[next_run] = ok
            words = fv.get("words_found") or []
            direct[str(next_run)] = words[0] if words else int(ok)
            measured += 1
            k += 1 if ok else 0
            fst.setdefault("certify", {})[str(depth)] = direct
            save_state(state_path, state)
            print(
                f"  cell (run {next_run}, {depth:,} tok): "
                f"{'PASS' if ok else 'FAIL'} -> {k}/{measured} "
                f"(1s lower bound {wilson_interval(k, measured)[0]:.3f})"
            )
        entry["cells_measured"] = measured
        entry["passes"] = k
        entry["ran_now"] = ran
        if verdict == "accept":
            entry["verdict"] = "accept"
            if level == "at_least_one":
                print(
                    f"  ACCEPT at {k}/{measured} - at least one pass at "
                    f"{depth:,} - {fam} answers the {depth:,} rung"
                )
            else:
                lo = wilson_interval(k, measured, z)[0]
                print(
                    f"  ACCEPT at {k}/{measured} - {level.replace('_', ' ')} "
                    f"lower bound {lo:.3f} >= 0.5 - {fam} answers the {depth:,} rung"
                )
            answered = True
        elif verdict == "dead":
            entry["verdict"] = "dead"
            if level == "at_least_one":
                print(f"  DEAD - every cell measured, no pass at {depth:,}; next candidate")
            else:
                print(
                    f"  DEAD - even {best_k}/{n_total} cannot reach the bar "
                    f"(best {int(z)}s lower bound {best_lo:.3f} < 0.5); next candidate"
                )
        elif verdict == "would-run":
            entry["verdict"] = "would-run"
            nxt = min(r for r in range(1, n_total + 1) if r not in cells)
            print(f"  dry run - would test {remaining} cell(s) from run {nxt}")
        results.append(entry)
    return results


def certify_rung_combined(
    depth: int,
    level: str,
    specs: list[str],
    models_dir: str,
    state: dict[str, Any],
    state_path: str,
    port: int,
    dry_run: bool,
    min_words: int = 1,
) -> list[dict[str, Any]]:
    """The combined controller (session 38, addendum 3 - the author's
    ruling): a cell is (model, rung, run) carrying THREE independent
    measurements - speed, FWE and VT. A cell's task is measured only
    if missing (never twice); the three tasks carry their own pass/fail
    tallies and their own accept/dead verdicts. The candidate certifies
    the rung when ALL THREE accept; it dies when ANY ONE is dead (the
    next candidate is picked up). Session 40, ruling B: the certify
    LEVEL maps to a MEDAL TIER - at_least_one = 0.5_sigma (0.5 sigma,
    0.20), 1_sigma = 1_sigma (1 sigma, 0.375), 2_sigma = 2_sigma
    (2 sigma, 0.50) - and the accept/dead math per task IS the tier's
    own bar, so the rung-stopping accept fires exactly when
    combined_medal returns the requested tier."""
    if level not in CERTIFY_LEVELS:
        raise ValueError(f"unknown certify level {level!r}")
    n_total = TOURNAMENT_CLIMBS
    tier_bars = {"at_least_one": (0.5, 0.20), "1_sigma": (1.0, 0.375), "2_sigma": (2.0, 0.50)}
    z, bar_lo = tier_bars[level]
    order: list[tuple[str, dict[str, Any], dict[str, dict[int, bool]], str]] = []
    for spec in specs:
        fam = os.path.basename(spec.partition("=")[0].rstrip("/"))
        fst = state["families"].get(fam, {})
        cells = {t: _task_load(fst, depth, t, min_words, models_dir, fam) for t in COMBINED_TASKS}
        order.append((fam, fst, cells, spec))

    def promise(item):
        fam, fst, cells, _spec = item
        k = sum(sum(1 for ok in t.values() if ok) for t in cells.values())
        saved_rank = state.get("tournament") or []
        rd = 0
        for tr in saved_rank:
            if tr.get("family") == fam:
                rd = tr.get("reliable_depth") or 0
        return (-k, -rd, fam)

    order.sort(key=promise)
    results: list[dict[str, Any]] = []
    answered = False
    for fam, fst, cells0, spec in order:
        cells = {t: dict(v) for t, v in cells0.items()}
        entry: dict[str, Any] = {
            "family": fam,
            "depth": depth,
            "level": level,
            "task": "all",
        }
        for t in COMBINED_TASKS:
            m = len(cells[t])
            kp = sum(1 for ok in cells[t].values() if ok)
            entry[f"{t}_historical_passes"] = kp
            entry[f"{t}_historical_cells"] = m
        print()
        print("-" * 60)
        for t in COMBINED_TASKS:
            print(
                f"  {fam} {t}: {entry[f'{t}_historical_passes']}/"
                f"{entry[f'{t}_historical_cells']} cells measured, "
                f"{n_total - entry[f'{t}_historical_cells']} unmeasured"
            )
        if answered:
            entry["skipped"] = "rung already answered"
            print("  SKIPPED - the rung is already answered")
            results.append(entry)
            continue
        speed_dead_at = fst.get("speed_dead_at")
        if speed_dead_at is not None and speed_dead_at <= depth:
            entry["skipped"] = f"speed gate died at {speed_dead_at:,}"
            print(f"  SKIPPED - speed gate died at {speed_dead_at:,} - not climbed")
            results.append(entry)
            continue
        famdir = os.path.join(models_dir, fam)
        rung = (
            fst.get("selected") or (fst.get("tournament_entry") or {}).get("rung") or RUNG_DEFAULT
        )
        run = (fst.get("runs") or {}).get(rung or "", {})
        model = (
            run.get("file")
            or (fst.get("tournament_entry") or {}).get("file")
            or (local_rung(famdir, rung) if rung else None)
        )
        if (not model or not os.path.isfile(model)) and spec:
            acquired = _acquire_missing_model(spec, fam, famdir, rung, state, dry_run)
            if acquired:
                model = acquired
        if not model or not os.path.isfile(model):
            entry["error"] = f"model file not found ({model})"
            print(f"  ERROR: {entry['error']}")
            results.append(entry)
            continue
        kv_k = (
            run.get("kv_quant_k")
            or (fst.get("tournament_entry") or {}).get("kv_quant_k")
            or state.get("kv_quant_k")
        )
        kv_v = (
            run.get("kv_quant_v")
            or (fst.get("tournament_entry") or {}).get("kv_quant_v")
            or state.get("kv_quant_v")
        )
        results_dir = os.path.join(models_dir, "tournament-results", fam)
        os.makedirs(results_dir, exist_ok=True)
        ran = 0
        verdict = None
        verdicts = {t: None for t in COMBINED_TASKS}
        tallies = {
            t: {
                "measured": len(cells[t]),
                "k": sum(1 for ok in cells[t].values() if ok),
            }
            for t in COMBINED_TASKS
        }

        def task_lo(t, _tallies=tallies):
            ta = _tallies[t]
            return wilson_interval(ta["k"], ta["measured"], z)[0] if ta["measured"] else 0.0

        while True:
            # verdicts: per task, independent accept / dead
            for t in COMBINED_TASKS:
                if verdicts[t] is not None:
                    continue
                ta = tallies[t]
                k, measured = ta["k"], ta["measured"]
                remaining = n_total - measured
                lo = task_lo(t)
                if lo >= bar_lo:
                    verdicts[t] = "accept"
                    continue
                best_k = k + remaining
                best_lo, _ = wilson_interval(best_k, n_total, z)
                if best_lo < bar_lo:
                    verdicts[t] = "dead"
            if all(v == "accept" for v in verdicts.values()):
                verdict = "accept"
                break
            if any(v == "dead" for v in verdicts.values()):
                verdict = "dead"
                dead_task = next(t for t in COMBINED_TASKS if verdicts[t] == "dead")
                break
            if dry_run:
                verdict = "would-run"
                break
            # pick the lowest unmeasured cell across the three tasks:
            # a cell run is shared, so measure the tasks the cell misses
            next_run = min(
                min(r for r in range(1, n_total + 1) if r not in cells[t])
                for t in COMBINED_TASKS
                if any(r not in cells[t] for r in range(1, n_total + 1))
            )
            for t in COMBINED_TASKS:
                if next_run in cells[t]:
                    continue
                ok, graded, line = bench_state_store._task_measure(
                    t, model, depth, results_dir, next_run, port, kv_k, kv_v, min_words
                )
                ran += 1
                cells[t][next_run] = ok
                tallies[t]["measured"] += 1
                tallies[t]["k"] += 1 if ok else 0
                bench_state_store._task_store(fst, depth, t, next_run, graded)
                save_state(state_path, state)
                print(
                    f"  cell {next_run} (rung {depth:,}) {line} -> {t} "
                    f"{tallies[t]['k']}/{tallies[t]['measured']} "
                    f"(1s lower bound {task_lo(t):.3f})"
                )
        entry["cells_measured"] = sum(tallies[t]["measured"] for t in COMBINED_TASKS)
        entry["ran_now"] = ran
        entry["passes"] = sum(tallies[t]["k"] for t in COMBINED_TASKS)
        entry["medal"] = combined_medal(fst, depth, level)
        for t in COMBINED_TASKS:
            entry[f"{t}_passes"] = tallies[t]["k"]
            entry[f"{t}_cells"] = tallies[t]["measured"]
            entry[f"{t}_verdict"] = verdicts[t]
        tally_line = ", ".join(
            f"{t} {tallies[t]['k']}/{tallies[t]['measured']}" for t in COMBINED_TASKS
        )
        if verdict == "accept":
            entry["verdict"] = "accept"
            print(
                f"  ACCEPT at {depth:,} - all three tasks clear "
                f"({tally_line}) "
                f"- {fam} answers the {depth:,} rung"
            )
            answered = True
        elif verdict == "dead":
            entry["verdict"] = "dead"
            if dead_task == "speed":
                prev = fst.get("speed_dead_at")
                if prev is None or depth < prev:
                    fst["speed_dead_at"] = depth
                    save_state(state_path, state)
            ta = tallies[dead_task]
            print(
                f"  DEAD - {dead_task} cannot reach the bar at {depth:,} "
                f"({ta['k']}/{ta['measured']}, best lower bound "
                f"{wilson_interval(ta['k'] + (n_total - ta['measured']), n_total, z)[0]:.3f}"
                f" < {bar_lo})"
                "; next candidate"
            )
        elif verdict == "would-run":
            entry["verdict"] = "would-run"
            print("  dry run - would measure the missing cell-tasks above")
        results.append(entry)
    return results


TASK_PASS_BARS = {"speed": 0, "fwe": 2, "vt": 4, "arc": 4}


def combined_medal(fst: dict[str, Any], depth: int, level: str) -> str | None:
    """The combined medal (session 38, addendum 7 - the author's
    refinement): the medals are PURE CONFIDENCE TIERS over each task's
    pass bar - 2_sigma = 2 sigma in EVERY test, 1_sigma = at least 1
    sigma in EVERY test, 0.5_sigma = 0.5 sigma in EVERY test (session
    40, the equidistant ruling: the thresholds land the tiers on
    round cell counts at n=20 - 0.5_sigma k=5, 1_sigma k=10,
    2_sigma k=15; the majority floor is dropped: it would forbid
    0.5_sigma; the tier names ARE the sigma names, the consistency
    ruling). The pass
    bars (the difficulty knob) live in TASK_PASS_BARS and never move
    the medals; tuning a test's difficulty changes what a pass means,
    not what the medals mean. A task with no measured cells has no
    medal contribution (None overall until every task has evidence)."""
    grades: dict[str, dict[str, bool]] = {}
    for t in COMBINED_TASKS:
        if t == "fwe":
            raw = (fst.get("certify") or {}).get(str(depth)) or {}
            records = {}
            for r, p in raw.items():
                if isinstance(p, bool):
                    records[int(r)] = 3 if p else 0
                else:
                    records[int(r)] = int(p)
        elif t == "vt":
            records = vt_cells(fst, depth)
        elif t == "arc":
            records = arc_cells(fst)
        else:
            records = speed_cells(fst, depth)
        if not records:
            return None
        bar = TASK_PASS_BARS[t]
        k = sum(1 for p in records.values() if p >= bar)
        lo_05s, _ = wilson_interval(k, len(records), 0.5)
        lo_1s, _ = wilson_interval(k, len(records), 1.0)
        lo_2s, _ = wilson_interval(k, len(records), 2.0)
        grades[t] = {
            "2_sigma": lo_2s >= 0.50,
            "1_sigma": lo_1s >= 0.375,
            "0.5_sigma": lo_05s >= 0.20,
        }
    if all(grades[t]["2_sigma"] for t in COMBINED_TASKS):
        return "2_sigma"
    if all(grades[t]["1_sigma"] for t in COMBINED_TASKS):
        return "1_sigma"
    if all(grades[t]["0.5_sigma"] for t in COMBINED_TASKS):
        return "0.5_sigma"
    return None
