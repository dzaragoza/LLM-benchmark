#!/usr/bin/env python3
"""bench/sweet.py -- the mechanical-sweet-spot task (the session's new mode).

For one class of hardware, walk each model DOWN the measured tok/s
ladder and find where it stops being able to fill its own window:

  per family (param-ascending):
    per quant (the Qwen3.5-2B discovered tok/s order, fastest first):
      build the quant, bench it (llama-bench -p 0 -n 128)
      in-window = tg/s * concurrency > training window
      in-window -> the next quant down the ladder (same model)
      beyond    -> THE SWEET SPOT: the last in-window quant is where
                   the model still saturates its window at this
                   concurrency; next family
      every rung in-window -> the LAST quant (F16) is the sweet spot

No global stop: every model gets its own walk; unavailable rungs
(unbuildable types, load failures) are skipped, not verdicts.

State is saved after every measurement - reruns skip measured rungs.
"""

from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
from typing import Any, cast

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import infra.convert_quant as convert_quant
import infra.hf_download as hf_download
from bench import state_store as _state_store

# disk retention (the walk's own ruling): a rung file is dead weight once
# its measurement is stored - only the f16 master (the quant source), the
# imatrix, and the CURRENT sweet-spot candidate need to stay on disk.
# Each newly measured rung deletes the previous one.
KEEP_FILES = {"imatrix-calib.txt", "imatrix-overrides.txt", "config.json"}


def _prune_rung(famdir: str, path: str) -> None:
    """Delete a measured rung file (never the f16 master or the imatrix)."""
    base = os.path.basename(path)
    if not base.endswith(".gguf"):
        return
    if base.endswith("-f16.gguf") or ".imatrix" in base:
        return
    try:
        os.remove(path)
        print(f"  [disk] pruned {base}")
    except OSError:
        pass


def _prune_previous(famdir: str, rec: dict[str, Any], current: str) -> None:
    """After CURRENT measured in-window, the rung before it (the previous
    sweet-spot candidate) is no longer needed."""
    prev = rec.get("last_kept_file")
    if prev and prev != current and os.path.isfile(prev):
        _prune_rung(famdir, prev)
    rec["last_kept_file"] = current

# the Qwen3.5-2B measured tok/s order (the T14s/780M sweep), fastest
# first - the walk goes DOWN this list; the sweet spot is the last
# quant that still clears the bar before the first failure
SWEET_LADDER = [
    "IQ1_S",
    "IQ1_M",
    "Q2_0",
    "IQ2_XXS",
    "IQ2_XS",
    "Q1_0",
    "IQ2_S",
    "Q2_K_S",
    "IQ2_M",
    "IQ3_XXS",
    "TQ2_0",
    "Q2_K",
    "Q3_K_S",
    "IQ3_XS",
    "IQ3_S",
    "IQ3_M",
    "Q3_K_M",
    "IQ4_XS",
    "Q4_0",
    "Q4_K_S",
    "Q3_K_L",
    "Q4_1",
    "IQ4_NL",
    "Q4_K_M",
    "TQ1_0",
    "Q5_K_S",
    "Q5_0",
    "Q5_K_M",
    "Q5_1",
    "Q6_K",
    "Q8_0",
    "BF16",
    "F16",
]

# the window boundary: a rung is in-window while tg/s * concurrency > window
WINDOW_DEFAULT = 262144  # every Qwen3.5 trains at 2**18

BENCH_BIN = os.path.join(
    ".", "llama-b11669", "llama-bench.exe" if os.name == "nt" else "llama-bench"
)


def find_bench() -> str | None:
    return BENCH_BIN if os.path.isfile(BENCH_BIN) else None


def _window(repo: str, famdir: str) -> int:
    """The model's training window (text_config.max_position_embeddings;
    Qwen3.5 configs nest it - registry_data.unwrap's shape)."""
    try:
        cfg_path = os.path.join(famdir, "config.json")
        if not os.path.isfile(cfg_path):
            hub_get = cast("Any", hf_download.hf_hub_download)
            cfg_path = hub_get(repo, "config.json", local_dir=famdir)
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        c = cfg
        while isinstance(c, dict):
            if c.get("max_position_embeddings") is not None:
                return int(c["max_position_embeddings"])
            c = c.get("text_config") or c.get("language_model")
            if not isinstance(c, dict):
                break
    except Exception:
        pass
    return WINDOW_DEFAULT


def _build(fam: str, repo: str, famdir: str, rung: str) -> str | None:
    """Phase 1 + 2 for one rung (the certify path, simplified). None =
    the rung cannot exist on this machine (RAM-infeasible, a tensor
    shape the quantizer cannot express - e.g. Q1_0 on a 960-col
    tensor - or a tool failure): SKIP, not a model verdict."""
    hf_download.require_hub()
    list_repo_files = cast("Any", hf_download.list_repo_files)
    files = list_repo_files(repo)
    path, plan = hf_download.acquire(fam, famdir, rung, repo, files, repo, files, False)
    if path:
        return path
    if plan.startswith("infeasible"):
        return None
    try:
        return convert_quant.create(fam, famdir, rung, plan, False)
    except SystemExit as e:
        if e.code == 130:  # SIGINT must still kill the run
            raise
        return None


def _bench(path: str, repeat: int) -> float | None:
    """llama-bench -p 0 -n 128: the generation rate (tg tok/s)."""
    r = subprocess.run(
        [BENCH_BIN, "-m", path, "-p", "0", "-n", "128", "-r", str(repeat), "-o", "csv"],
        capture_output=True,
        text=True,
        timeout=3600,
    )
    if r.returncode != 0:
        return None
    tg = None
    for row in csv.DictReader(io.StringIO(r.stdout)):
        if row.get("model_filename") == path and row.get("avg_ts"):
            try:
                tg = float(row["avg_ts"])
            except ValueError:
                pass
    return tg


def _in_window(tg: float, window: int, concurrency: int) -> bool:
    return tg * concurrency > window


def roster_from_models_md() -> list[tuple[str, str]]:
    """The roster AS WRITTEN in md/models.md (the source of truth): the
    table rows in file order (param-ascending), model name + repo. The
    'unknown'-param rows sort to their file position - the table's own
    order decides, no re-sorting here."""
    rows = []
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "md", "models.md"
    )
    in_table = False
    for line in open(path, encoding="utf-8"):
        if line.startswith("| model name"):
            in_table = True
            continue
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            if len(parts) >= 4 and parts[0] and parts[0] != "model name" and set(parts[0]) != {"-"}:
                rows.append((parts[0], parts[3]))
    return rows


def run(
    models_dir: str,
    state: dict[str, Any],
    state_file: str,
    families: list[str],
    repeat: int = 3,
    concurrency: int = 1024,
    dry_run: bool = False,
    bench_bin: str | None = None,
) -> dict[str, Any]:
    if not dry_run and not bench_bin:
        sys.exit(f"llama-bench not found at {BENCH_BIN} - place the b11669 build in the repo root")
    roster = dict(roster_from_models_md())
    if not roster:
        sys.exit("md/models.md carries no roster rows - regenerate the table first")

    sweet = state.setdefault("sweet", {})
    for fam in families:
        repo = roster.get(fam)
        if not repo:
            print(f"  {fam}: not in md/models.md - skipped")
            continue
        famdir = os.path.join(models_dir, fam)
        os.makedirs(famdir, exist_ok=True)
        rec = sweet.setdefault(fam, {"rungs": {}, "sweet_spot": None, "ceiling": False})
        window = rec.get("window") or _window(repo, famdir)
        rec["window"] = window
        rec["repo"] = repo
        print(
            f"\n{'=' * 60}\n{fam} (window {window:,}, in-window while tg/s*{concurrency} > {window:,})"
        )
        for rung in SWEET_LADDER:
            if rung in rec["rungs"] and rec["rungs"][rung].get("tg") is None:
                if rec["rungs"][rung].get("error"):
                    print(f"  {rung}: {rec['rungs'][rung]['error']} - skipped")
                    continue
            # old-era records (tg present but keyed by pass, not in_window):
            # fall through to the re-judge below which stamps in_window
            if rung in rec["rungs"] and rec["rungs"][rung].get("tg") is not None:
                m = rec["rungs"][rung]
                # RE-JUDGE with the run's concurrency (the stored verdict was
                # computed under whatever factor was live then): a stored
                # tg/s is a measurement - the pass bar is today's decision
                ok = _in_window(m["tg"], window, concurrency)
                m.pop("pass", None)
                m["in_window"] = ok
                m["concurrency"] = concurrency
                if ok:
                    rec["sweet_spot"] = rung
                else:
                    rec["ceiling"] = True
                _state_store.save_state(state_file, state)
                print(
                    f"  {rung}: {m['tg']:.2f} tok/s (measured) "
                    f"x {concurrency} = {m['tg'] * concurrency:,.0f} "
                    f"-> {'in-window' if ok else 'beyond the window'}"
                )
                if not ok:
                    break
                continue
            if dry_run:
                if rec.get("ceiling"):
                    break
                continue
            if dry_run:
                print(f"  {rung}: would build + bench")
                continue
            path = _build(fam, repo, famdir, rung)
            if not path:
                rec["rungs"][rung] = {
                    "tg": None,
                    "pass": None,
                    "error": "unavailable on this machine",
                }
                _state_store.save_state(state_file, state)
                print(f"  {rung}: unavailable on this machine - skipped")
                continue
            else:
                tg = _bench(path, repeat)
                if tg is None:
                    rec["rungs"][rung] = {"tg": None, "pass": None, "error": "bench failed"}
                    _state_store.save_state(state_file, state)
                    print(f"  {rung}: llama-bench failed - skipped")
                    continue
                else:
                    ok = _in_window(tg, window, concurrency)
                    rec["rungs"][rung] = {"tg": tg, "in_window": ok}
                    _state_store.save_state(state_file, state)
                    print(
                        f"  {rung}: {tg:.2f} tok/s x {concurrency} = "
                        f"{tg * concurrency:,.0f} -> {'in-window' if ok else 'beyond the window'}"
                    )
                    if ok:
                        rec["sweet_spot"] = rung
                        _prune_previous(famdir, rec, path)
            if not rec["rungs"][rung]["in_window"]:
                rec["ceiling"] = True
                _state_store.save_state(state_file, state)
                print(f"  {fam}: sweet spot: {rec.get('sweet_spot')} (beyond at {rung})")
                break
        else:
            if dry_run:
                rec["ceiling"] = False
                continue
            # every MEASURED rung stayed in-window: the ladder's last
            # measured quant is the sweet spot (the walk never went beyond)
            last = [
                r
                for r in SWEET_LADDER
                if r in rec["rungs"] and rec["rungs"][r].get("tg") is not None
            ]
            rec["sweet_spot"] = last[-1] if last else None
            _state_store.save_state(state_file, state)
            print(f"  {fam}: every rung in-window - sweet spot: {rec.get('sweet_spot')}")
    return sweet
