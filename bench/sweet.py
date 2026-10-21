#!/usr/bin/env python3
"""bench/sweet.py -- the mechanical-sweet-spot task (the session's new mode).

For one class of hardware, walk each model DOWN the measured tok/s
ladder and find where it stops being able to fill its own window:

  per family (param-ascending):
    per quant (the Qwen3.5-2B discovered tok/s order, fastest first):
      build the quant, bench it (llama-bench -p 0 -n 128)
      in-window = tg/s * concurrency > training window
      the in-window side contributes its BOUNDARY: the slowest in-window
      quant (the last one before the first beyond) - the only in-window
      file kept on disk
      the beyond side (tg/s * concurrency <= window) is MEASURED IN
      FULL: every rung from the first beyond one to the ladder's end
      gets its tg/s recorded - the model's sweet CURVE is the boundary
      quant plus every beyond-quant's tg/s

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


def _reconcile_disk(famdir: str, rec: dict[str, Any]) -> None:
    """The keep-set reconciliation, run when a family's walk is (re)entered:
    from the STORED verdicts, the f16 master and the current sweet-spot
    rung's file are the keep-set; every other *.gguf in the family dir is
    a superseded leftover (walks that ran before the retention landed,
    or re-judged records whose files were never pruned) - delete them.
    No state mutation: this only enforces what the state already says."""
    spot = rec.get("sweet_spot")
    if not spot or not os.path.isdir(famdir):
        return
    fam = os.path.basename(famdir)
    # keep the f16 master, the boundary, and EVERY beyond-window curve
    # point (they are all sweet spots - the downstream measurements)
    keep = {f"{fam}-f16.gguf", f"{fam}-{spot}.gguf"}
    for rung, m in rec.get("rungs", {}).items():
        if m.get("in_window") is False:
            keep.add(f"{fam}-{rung}.gguf")
    freed = 0
    for f in os.listdir(famdir):
        p = os.path.join(famdir, f)
        if f.endswith(".gguf") and f not in keep:
            try:
                freed += os.path.getsize(p)
                os.remove(p)
            except OSError:
                pass
    if freed:
        print(f"  [disk] reconciled: {freed / 2**30:.2f} GiB of superseded rungs pruned")


def _regenerate_missing(
    fam: str, repo: str, famdir: str, rec: dict[str, Any], dry_run: bool = False
) -> None:
    """The era bridge: the pre-curve retention pruned files the curve
    semantics now needs - any rung with a STORED measurement that is a
    keep-set member (the boundary or a beyond-window sweet spot) but
    whose file is absent gets rebuilt from the f16 master (no re-bench:
    the measurement stands; only the file was lost). The F16 rung's
    file IS the f16 master itself."""
    spot = rec.get("sweet_spot")
    if not spot or dry_run:
        return
    fam_spot = os.path.basename(famdir)
    for rung, m in rec.get("rungs", {}).items():
        keep = rung == spot or m.get("in_window") is False
        if not keep or m.get("tg") is None:
            continue
        path = (
            os.path.join(famdir, f"{fam_spot}-f16.gguf")
            if rung.upper() == "F16"
            else _rung_file(famdir, fam_spot, rung)
        )
        if os.path.isfile(path):
            continue
        print(f"  {rung}: sweet-spot file was pruned earlier - regenerating (no re-bench)")
        files = cast("Any", hf_download.list_repo_files)(repo)
        try:
            built = convert_quant.create(fam, famdir, rung, "", False)
        except SystemExit as e:
            if e.code == 130:
                raise
            built = None
        if not built or not os.path.isfile(path):
            print(f"  {rung}: could not regenerate ({path} still missing) - skipped")


def _rung_file(famdir: str, fam: str, rung: str) -> str:
    """The rung's expected on-disk name (the pipeline's own convention)."""
    return os.path.join(famdir, f"{fam}-{rung}.gguf")


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
    """Disk retention with the sweet-spot KEEP rule: the f16 master and
    the LATEST in-window rung (the sweet-spot candidate the walk will
    hand to the downstream measurements) always stay. Only when the
    walk moves PAST a rung (the new one measured in-window too) does the
    superseded candidate get pruned."""
    prev = rec.get("sweet_spot_file")
    if prev and prev != current:
        _prune_rung(famdir, prev)
    rec["sweet_spot_file"] = current


# the Qwen3.5-2B measured tok/s order (the T14s/780M sweep), fastest
# first - the walk goes DOWN this list; the sweet spot is the last
# quant that still clears the bar before the first failure
SWEET_LADDER = [
    "IQ1_S", "Q2_0", "Q1_0", "IQ2_XXS", "Q2_K_S", "TQ2_0", "IQ1_M",
    "IQ2_XS", "IQ2_S", "Q2_K", "IQ3_XXS", "IQ2_M", "IQ3_XS", "IQ4_XS",
    "IQ3_S", "IQ3_M", "Q3_K_S", "Q4_0", "IQ4_NL", "Q3_K_M", "Q4_K_S",
    "Q4_1", "Q4_K_M", "Q3_K_L", "Q5_K_S", "TQ1_0", "Q5_0", "Q5_K_M",
    "Q5_1", "Q6_K", "Q8_0", "F16",
]
# BF16 is cut from the walk (the author's ruling: f16 is basically the
# same thing) - one fewer full-size build+bench per model

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
        _reconcile_disk(famdir, rec)
        print(
            f"\n{'=' * 60}\n{fam} (window {window:,}, in-window while tg/s*{concurrency} > {window:,})"
        )
        _regenerate_missing(fam, repo, famdir, rec, dry_run)
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
                    prev_spot = rec.get("prev_sweet")
                    if prev_spot and prev_spot != rung:
                        prev_file = rec.get("sweet_spot_file")
                        if prev_file and os.path.isfile(prev_file):
                            _prune_rung(famdir, prev_file)
                    rec["prev_sweet"] = rung
                    rec["sweet_spot_file"] = _rung_file(famdir, fam, rung)
                else:
                    rec["beyond"] = True
                _state_store.save_state(state_file, state)
                print(
                    f"  {rung}: {m['tg']:.2f} tok/s (measured) "
                    f"x {concurrency} = {m['tg'] * concurrency:,.0f} "
                    f"-> {'in-window' if ok else 'BEYOND (curve point)'}"
                )
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
                        prev_spot = rec.get("sweet_spot")
                        rec["sweet_spot"] = rung
                        # prune the superseded candidate only now that the
                        # walk has a NEWER in-window rung to hand over
                        if prev_spot and prev_spot != rung:
                            _prune_previous(famdir, rec, path)
                        else:
                            rec["sweet_spot_file"] = path
        else:
            if dry_run:
                rec["ceiling"] = False
                continue
            # every MEASURED rung stayed in-window: the ladder's last
            # measured quant is the sweet spot (the walk never went beyond)
            n_beyond = sum(1 for m in rec["rungs"].values() if m.get("in_window") is False)
            _state_store.save_state(state_file, state)
            print(
                f"  {fam}: curve complete - boundary {rec.get('sweet_spot')}, "
                f"{n_beyond} beyond points"
            )
    return sweet
