"""bench.tournament -- the climb/fall machinery (session 38, addendum
15: the full_benchmark.py refactor). The 21 climbs per family, the
fall ranking, the re-score and the tournament table. Extracted
verbatim."""

from __future__ import annotations

import csv
import math
import os
import sys
from collections.abc import Sequence
from typing import Any, cast

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import glob  # noqa: F401  (used by the rescore csv walk)

import convert_quant
import hf_download
import ruler_gate
from bench import cells as bench_cells
from bench.certify import wilson_interval
from bench.constants import (
    CORPUS_DEFAULT,
    TOURNAMENT_CLIMBS,
    TOURNAMENT_DEPTHS,
)
from bench.state_store import save_state, stamp

local_rung = hf_download.local_rung


def fwe_flicker(rungs: list[dict[str, Any]]) -> tuple[int, int] | None:
    """The flicker rule (session 34, addendum 31, ruling b): FWE
    verdicts must be MONOTONE - depth only gets harder. Returns the
    (deep_pass, shallow_fail) rung pair when a run passes FWE at a
    deep rung but FAILS at a shallower one (an n=1 boundary
    coin-flip, the addendum-29 flicker), else None. Works on any
    ladder's rungs list - a live run_ladder result OR one re-read
    from a state file (cross-grid flicker: the Qwen3-4B shape, a
    2048 fail next to a 16384 pass)."""
    fwe_cells = [c for c in rungs if c.get("fwe_pass") is not None]
    for deep in fwe_cells:
        if deep["fwe_pass"] is not True:
            continue
        for shallow in fwe_cells:
            if shallow["rung"] < deep["rung"] and shallow["fwe_pass"] is False:
                return deep["rung"], shallow["rung"]
    return None


def tournament_rank(fall_depths: Sequence[int | None], depths: list[int]) -> dict[str, Any]:
    """The sigma-only rank (session 37, addendum 10: the mode is
    RETIRED - the author's ruling, n selection is based on sigma
    only): fall_depths is one entry per climb - the depth where that
    climb ended (the first non-perfect cell), or None for a climb
    that topped out at the highest step (full hold). The rank is the
    WILSON-basis statistics alone: the per-rung pass vector, the
    reliable depth (1 sigma), the conservative depth (2 sigma), the
    ceiling, and the per-rung 1-sigma Wilson bounds. No central
    tendency of the fall depths is computed; a model is what it
    reliably holds, not what it most often fell at."""
    passes: dict[int, int] = {}
    for d in depths:
        passes[d] = sum(
            1 for fall in fall_depths if fall is None or (fall is not None and fall > d)
        )
    return _rank_extra(
        {
            "passes": passes,
            "fall_depths": fall_depths,
            "full_holds": sum(1 for fall in fall_depths if fall is None),
        },
        depths,
    )


def _rank_extra(rank: dict[str, Any], depths: list[int]) -> dict[str, Any]:
    """The addendum-42/43 recommendation statistics: reliable depth
    (the deepest rung whose 1-sigma LOWER Wilson bound on the hold
    probability is >= 0.5 - the rung holds FWE on most seeds, with
    1-sigma confidence), conservative depth (the same at 2 sigma -
    the claim that survives skeptical review; addendum 43, n=21 puts
    the 2-sigma certify bar at 15/21 observed holds), ceiling (the
    deepest rung held EVER), and the per-rung 1-sigma Wilson bounds."""
    n = len(rank["fall_depths"])
    passes = rank["passes"]
    floor = math.ceil(0.5 * n) if n else 0
    reliable = 0
    conservative = 0
    bounds: dict[int, tuple[float, float]] = {}
    for d in depths:
        k = passes[d]
        lo, hi = wilson_interval(k, n)
        bounds[d] = (round(lo, 3), round(hi, 3))
        if k >= floor and lo >= 0.5:
            reliable = d
        if k >= floor and wilson_interval(k, n, 2.0)[0] >= 0.5:
            conservative = d
    rank["reliable_depth"] = reliable
    rank["conservative_depth"] = conservative
    rank["wilson_bounds"] = bounds
    climb_max = [depths[-1] if f is None else f for f in rank["fall_depths"]]
    rank["ceiling"] = max(climb_max) if climb_max else 0
    return rank


def tournament_family(
    spec: str,
    models_dir: str,
    state: dict[str, Any],
    state_path: str,
    port: int,
    dry_run: bool,
) -> dict[str, Any]:
    """One family's tournament turn (session 36, addenda 10/11): five
    climbs of the dyadic FWE ladder at upstream parameters, SEED =
    CLIMB NUMBER, early stop at the first non-perfect cell. Runs at
    the family's SELECTED rung - the PASS config - with its stored
    KV quants (the 2B's Q4_K_M carries q5_0, per the state). The
    speed gate is ASSUMED passed (author ruling: known at 256k for
    all participants, falsified after the tournament if a ranking
    step needs it)."""
    model_repo, _, source_repo = spec.partition("=")
    fam = os.path.basename(model_repo.rstrip("/"))
    fst = state["families"].get(fam, {})
    entry = fst.get("tournament_entry") or {}
    rung = fst.get("selected") or entry.get("rung")
    if not rung:
        return {"family": fam, "error": "no selected rung - not a PASS family"}
    run = fst.get("runs", {}).get(rung, {})
    famdir = os.path.join(models_dir, fam)
    model = run.get("file") or entry.get("file") or local_rung(famdir, rung)
    if (not model or not os.path.isfile(model)) and entry:
        # addendum 29: the tournament acquires its own entry files -
        # the same phase-1 path the main run uses (wow.md: the author
        # runs one command, not a download step per model)
        hf_download.require_hub()
        list_repo_files = cast("Any", hf_download.list_repo_files)
        try:
            model_files = list_repo_files(model_repo)
            source_repo_eff = source_repo or model_repo
            source_files = (
                model_files if source_repo_eff == model_repo else list_repo_files(source_repo_eff)
            )
            path, plan = hf_download.acquire(
                fam, famdir, rung, model_repo, model_files, source_repo_eff, source_files, dry_run
            )
            if dry_run:
                print(f"  entry file absent - dry run plan: {plan}")
            path = path or convert_quant.create(fam, famdir, rung, plan, dry_run)
            if path and os.path.isfile(path):
                model = path
                entry["file"] = path
                save_state(state_path, state)
        except Exception as e:
            return {"family": fam, "error": f"entry acquisition failed: {e}"}
    if not model or not os.path.isfile(model):
        return {"family": fam, "error": f"rung file not found ({model})"}
    kv_k = run.get("kv_quant_k") or entry.get("kv_quant_k") or state.get("kv_quant_k")
    kv_v = run.get("kv_quant_v") or entry.get("kv_quant_v") or state.get("kv_quant_v")
    depths = TOURNAMENT_DEPTHS
    print()
    print("=" * 60)
    stamp(f"tournament: {fam} ({rung})")
    print(f"  file: {model}")
    if entry and not fst.get("selected"):
        pred = entry.get("predicted_ram_gib")
        print(
            f"  ENTRY CONFIG (predicted, addendum 16): {rung} + K/V "
            f"{kv_k or 'f16'}/{kv_v or 'f16'}" + (f" - predicted RAM {pred} GiB" if pred else "")
        )
    if dry_run:
        for s in range(1, TOURNAMENT_CLIMBS + 1):
            print(
                f"  would climb {s}/{TOURNAMENT_CLIMBS}: depths "
                f"{' '.join(str(d) for d in depths)} (seed {s}, early stop)"
            )
        return {"family": fam, "rung": rung, "dry_run": True}
    results_dir = os.path.join(models_dir, "tournament-results", fam)
    os.makedirs(results_dir, exist_ok=True)
    # addendum 37: the tournament is RESUMABLE - each climb's fall is
    # persisted in the family state (seed = climb number), so adding
    # climbs (5 -> 7) runs only the new seeds, never the old ones
    state["families"].setdefault(fam, fst)
    saved: dict[str, int | None] = dict(fst.get("tournament_falls") or {})
    fall_depths: list[int | None] = []
    for s in range(1, TOURNAMENT_CLIMBS + 1):
        key = str(s)
        if key in saved:
            fall_depths.append(saved[key])
            print(
                f"  climb {s}/{TOURNAMENT_CLIMBS}: RESUMED - "
                f"{'topped out' if saved[key] is None else f'fell at {saved[key]:,} tok'}"
            )
            continue
        climb_dir = os.path.join(results_dir, f"climb{s}")
        os.makedirs(climb_dir, exist_ok=True)
        fall = None
        for d in depths:
            row = bench_cells.fwe_pass(
                model,
                d + 2 * ruler_gate.ANSWER_HEADROOM,
                climb_dir,
                seed=s,
                port=port,
                kv_quant_k=kv_k,
                kv_quant_v=kv_v,
            )
            ok, fv = row
            words = fv.get("words_found", [fv.get("correct", 0)])
            partial = words[0] if words else 0
            print(
                f"  climb {s}/{TOURNAMENT_CLIMBS} @ {d} tok: "
                f"{partial}/{ruler_gate.FWE_TOP_K} words -> "
                f"{'HOLD' if ok else 'FALL'}"
            )
            if not ok:
                fall = d
                print(f"  CLIMB OVER at {d} tok (climb {s})")
                break
        if fall is None:
            print(f"  climb {s}/{TOURNAMENT_CLIMBS}: TOPPED OUT at {depths[-1]} tok")
        fall_depths.append(fall)
        saved[key] = fall
        fst["tournament_falls"] = saved
        save_state(state_path, state)
    rank = tournament_rank(fall_depths, depths)
    print(
        f"  {fam}: sigma rank - reliable {rank['reliable_depth']:,} "
        f"(1 sigma) | conservative {rank['conservative_depth']:,} "
        f"(2 sigma) | ceiling {rank['ceiling']:,} tokens "
        f"(falls: {[f if f else 'top' for f in fall_depths]})"
    )
    print(
        f"  {fam}: reliable depth {rank['reliable_depth']:,} tokens "
        f"(P>=0.5 at 1 sigma) | conservative {rank['conservative_depth']:,} "
        f"(2 sigma) | ceiling {rank['ceiling']:,} tokens"
    )
    return {
        "family": fam,
        "rung": rung,
        "model": model,
        "kv_quant_k": kv_k,
        "kv_quant_v": kv_v,
        "corpus": CORPUS_DEFAULT,
        **rank,
    }


def rescore_tournament(
    models_dir: str,
    state: dict[str, Any],
    state_path: str,
    dry_run: bool,
) -> None:
    """Session 37, addendum 4 (the author's re-score ruling): the saved
    tournament_falls were collected under the 3/3 criterion; under the
    relaxed 1/3 criterion (addendum 2) every recorded fall is a LOWER
    BOUND on the true one (all recorded falls were 1/3 or 2/3 partials,
    addendum 26 - a 0/3 fall would fall under both criteria). This
    re-derives each climb's fall from the raw per-cell CSVs the climbs
    wrote: a cell passes at partial >= 1; the re-scored fall is the
    first rung whose cell fails; a climb whose every recorded cell
    passes re-runs from just above its old fall (the early stop never
    wrote the cells above). Without --rescore-apply the state is only
    REPORTED, never written; with it, tournament_falls is rewritten
    under the new criterion and the family's remaining depths run
    the next --tournament as fresh seeds' resume."""
    depths = TOURNAMENT_DEPTHS
    for fam, fst in sorted(state.get("families", {}).items()):
        saved = fst.get("tournament_falls") or {}
        if not saved:
            print(f"  {fam}: no saved climbs - nothing to re-score")
            continue
        results_dir = os.path.join(models_dir, "tournament-results", fam)
        print(f"  {fam}: re-scoring {len(saved)} climbs under the 1/3 criterion")
        changed = 0
        if dry_run:
            saved = dict(saved)
        for key in sorted(saved, key=int):
            s = int(key)
            climb_dir = os.path.join(results_dir, f"climb{s}")
            old_fall = saved[key]
            new_fall = None
            for d in depths:
                csv_path = os.path.join(climb_dir, f"-{d}-fwe.csv")
                if not os.path.isfile(csv_path):
                    matches = sorted(glob.glob(os.path.join(climb_dir, f"*-{d}-fwe.csv")))
                    csv_path = matches[0] if matches else csv_path
                if not os.path.isfile(csv_path):
                    if old_fall is not None and d <= old_fall:
                        print(
                            f"    climb {s}: MISSING cell at {d:,} tok "
                            f"({csv_path}) - cannot re-score; keeping the "
                            f"recorded fall"
                        )
                        new_fall = old_fall
                        break
                    break
                with open(csv_path, encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
                partial = None
                for r in rows:
                    if r.get("partial") not in (None, ""):
                        partial = int(r["partial"])
                if partial is None:
                    print(
                        f"    climb {s}: cell at {d:,} tok has no partial "
                        f"count - cannot re-score; keeping the recorded fall"
                    )
                    new_fall = old_fall
                    break
                if partial < 1:
                    new_fall = d
                    break
            if new_fall is None and old_fall is not None:
                # every recorded cell passes under 1/3 - the true fall is
                # ABOVE the recorded one, and the cells above were never
                # written (early stop). The climb needs re-running from
                # just above its old fall; the rescore marks it UNKNOWN
                # by dropping the saved entry so the next --tournament
                # run resumes it as a fresh climb.
                print(
                    f"    climb {s}: old fall {old_fall:,} is now a PASS "
                    f"chain - the true fall is above it and unmeasured; "
                    f"the saved fall is DROPPED so the next tournament "
                    f"run re-runs the whole climb under 1/3"
                )
                del saved[key]
                changed += 1
                continue
            if new_fall != old_fall:
                changed += 1
                o = "None" if old_fall is None else format(old_fall, ",")
                n = "None" if new_fall is None else format(new_fall, ",")
                print(f"    climb {s}: fall {o} -> {n} tok")
                saved[key] = new_fall
        if dry_run:
            print(f"  {fam}: dry run - {changed} climbs would change (state NOT written)")
        else:
            fst["tournament_falls"] = saved
            save_state(state_path, state)
            print(f"  {fam}: {changed} climbs changed - state saved")


def print_tournament_table(tours: list[dict[str, Any]]) -> None:
    """The tournament ranking (session 37, addendum 10: the mode is
    retired - sigma only): ranked by reliable depth (1 sigma), ties on
    conservative depth (2 sigma), then the pass vector at the steps
    above, then the ceiling."""
    print()
    print("=" * 60)
    stamp("TOURNAMENT TABLE (sigma rank - session 37 addendum 10)")
    done = [t for t in tours if "passes" in t]
    errs = [t for t in tours if "error" in t]
    for t in errs:
        print(f"  {t['family']}: SKIPPED - {t['error']}")
    order = sorted(
        done,
        key=lambda t: (
            -t.get("reliable_depth", 0),
            -t.get("conservative_depth", 0),
            [-t["passes"][d] for d in sorted(t["passes"], reverse=True)],
            -t.get("ceiling", 0),
        ),
    )
    for i, t in enumerate(order, 1):
        pv = " ".join(f"{t['passes'][d]}" for d in TOURNAMENT_DEPTHS)
        print(
            f"  {i}. {t['family']:24s} reliable "
            f"{t.get('reliable_depth', 0):>7,} tok | conservative "
            f"{t.get('conservative_depth', 0):>7,} tok | ceiling "
            f"{t.get('ceiling', 0):>7,} tok | passes/rung [{pv}]"
        )
