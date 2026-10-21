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
    # point (they are all sweet spots - the downstream measurements).
    # Case-insensitive: rung names cross the pipeline in both cases
    # (F16 vs f16 master vs a repo's lowercase artifacts) - a case
    # mismatch pruned live sweet-spot files as leftovers (the v8
    # run's lesson: the exam found every boundary file missing)
    keep = {f"{fam}-f16.gguf", f"{fam}-{spot}.gguf"}
    for rung, m in rec.get("rungs", {}).items():
        if m.get("in_window") is False:
            keep.add(f"{fam}-{rung}.gguf")
    keep_lower = {k.lower() for k in keep}
    freed = 0
    for f in os.listdir(famdir):
        p = os.path.join(famdir, f)
        if f.endswith(".gguf") and f.lower() not in keep_lower:
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
        # case-insensitive presence check (the pipeline's rung names
        # cross in both cases); regenerate only when no file of the
        # keep-set name exists in either case
        candidates = (
            [os.path.join(famdir, f"{fam_spot}-f16.gguf"), os.path.join(famdir, f"{fam_spot}-F16.gguf")]
            if rung.upper() == "F16"
            else [_rung_file(famdir, fam_spot, rung)]
        )
        path = next((c for c in candidates if os.path.isfile(c)), None)
        if path:
            continue
        path = candidates[0]
        print(f"  {rung}: sweet-spot file was pruned earlier - regenerating (no re-bench)")
        files = cast("Any", hf_download.list_repo_files)(repo)
        # the full acquire path (not bare create): when the F16 rung's
        # own master is gone there is no local source to convert from,
        # so the safetensors must come back from the hub first - the
        # same phase-1 path a fresh walk uses (measurements stand)
        try:
            got, plan = hf_download.acquire(fam, famdir, rung, repo, files, repo, files, False)
            if got:
                built = got
            elif not plan.startswith("infeasible"):
                built = convert_quant.create(fam, famdir, rung, plan, False)
            else:
                built = None
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
    low = base.lower()
    if low.endswith("-f16.gguf") or ".imatrix" in base:
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


def _unquantizable(log: str) -> str | None:
    """The permanent-unquantizable signature from a failed llama-quantize
    log (the b11669 hard requirements: a column count the quant type's
    blocking cannot express, or no defined fallback for the type) - a
    property of the ARCHITECTURE, not of the machine's disk or tools.
    Returns the matched quantize error line, or None for transient
    failures (disk-full, missing tools, OOM) that a rerun can fix."""
    try:
        with open(log, encoding="utf-8") as f:
            for line in f:
                if "not divisible by" in line and "required for type" in line:
                    return line.strip()
                if "no tensor type fallback is defined" in line:
                    return line.strip()
    except OSError:
        pass
    return None


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


def _bench(path: str, repeat: int, gen_len: int = 2048) -> float | None:
    """llama-bench -p 0 -n <gen_len>: the SUSTAINED generation rate
    (tg tok/s). The old -n 128 was a 2-second burst - blind to the
    thermal throttling (the 780M iGPU) and KV-growth slowdown that a
    1024-second fill actually suffers (the v8 lesson: Qwen3-1.7B
    benched ~50 tok/s at n=128 but filled its bell at ~1/3 of that).
    2048 tokens is long enough to see the decay, short enough to keep
    the walk affordable (~16x the old burst per rung)."""
    r = subprocess.run(
        [BENCH_BIN, "-m", path, "-p", "0", "-n", str(gen_len), "-r", str(repeat), "-o", "csv"],
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


def _era_ok(rec_rung: dict[str, Any], gen_len: int) -> bool:
    """A stored tg is reusable only within its measurement era: the
    -n it was measured at (burst n=128 vs sustained n=2048) changes
    the number materially (thermal decay, KV growth). A record
    without a gen_len stamp is the old burst era - stale under a
    sustained run."""
    return rec_rung.get("gen_len") == gen_len


def _in_window(tg: float, window: int, concurrency: int) -> bool:
    return tg * concurrency > window


def calibrated_gen_len(state: dict[str, Any]) -> int | None:
    """The author's calibration: llama-bench's -n (the GENERATION
    LENGTH the rate is measured at) is the MEDIAN length of every
    PASSING exam answer on record, rounded UP to a power of two.

    The rationale: the 1024s promise is 'a good answer within the
    budget', and passing answers are what a good answer costs -
    measuring tg/s at that length matches the measurement to the
    workload the promise is actually about (n=128 was the guess;
    the first era's median passing answer was 76 -> n=128 - the
    guess was right, now it is grounded).

    None until passing attempts exist in state (the flag/default
    binds). Expect the median to GROW with higher levels passed -
    recalibrate and re-measure when it moves a power of two."""
    import statistics

    toks = []
    for fam, fam_exam in (state.get("exam") or {}).items():
        if not isinstance(fam_exam, dict):
            continue
        recs = [
            rec
            for key, rec in fam_exam.items()
            if not str(key).startswith("_") and isinstance(rec, dict) and "levels" in rec
        ]
        if "levels" in fam_exam and fam_exam.get("levels"):
            recs.append(fam_exam)
        for rec in recs:
            for lv in (rec.get("levels") or {}).values():
                for a in lv.get("attempts") or []:
                    if a.get("ok") and a.get("answer_tokens"):
                        toks.append(a["answer_tokens"])
    if not toks:
        return None
    med = statistics.median(toks)
    n = 1
    while n < med:
        n *= 2
    return n


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
    gen_len: int = 2048,
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
            # fall through to the re-judge below which stamps in_window.
            # A tg measured in a DIFFERENT gen_len era is stale: drop
            # it and re-measure (the burst-era number predicted fills
            # the sustained era could not deliver - the v8 lesson)
            if (
                rung in rec["rungs"]
                and rec["rungs"][rung].get("tg") is not None
                and not _era_ok(rec["rungs"][rung], gen_len)
            ):
                print(f"  {rung}: stored tg is from the -n "
                      f"{rec['rungs'][rung].get('gen_len') or 128} era - re-measuring at -n {gen_len}")
                del rec["rungs"][rung]
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
                    # NO mid-walk prune here: prev_sweet is STALE on a
                    # resume (it names the previous run's boundary -
                    # often the very rung _regenerate_missing just
                    # rebuilt), so pruning on it deleted live boundary
                    # files mid-walk. Retention is _reconcile_disk's
                    # job at the next entry, over the FINAL verdicts.
                    rec["prev_sweet"] = rung
                    # the ACTUAL on-disk file, not the ladder spelling:
                    # the f16 master is lowercase ({fam}-f16.gguf, the
                    # converter's convention) while the ladder's rung
                    # name is uppercase - a stored uppercase path made
                    # the exam report the sweet spot missing
                    rec["sweet_spot_file"] = (
                        hf_download.local_rung(famdir, rung) or _rung_file(famdir, fam, rung)
                    )
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
                permanent = _unquantizable(os.path.join(famdir, f"quantize-{rung}.log"))
                error = (
                    f"quantization impossible for this architecture ({permanent})"
                    if permanent
                    else "unavailable on this machine"
                )
                rec["rungs"][rung] = {
                    "tg": None,
                    "pass": None,
                    "error": error,
                    "permanent": bool(permanent),
                }
                _state_store.save_state(state_file, state)
                print(f"  {rung}: {error} - skipped")
                continue
            else:
                tg = _bench(path, repeat, gen_len)
                if tg is None:
                    rec["rungs"][rung] = {"tg": None, "pass": None, "error": "bench failed"}
                    _state_store.save_state(state_file, state)
                    print(f"  {rung}: llama-bench failed - skipped")
                    continue
                else:
                    ok = _in_window(tg, window, concurrency)
                    rec["rungs"][rung] = {"tg": tg, "in_window": ok, "gen_len": gen_len}
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
            # the v8 rule pair, per rung: tg/s x time_factor >
            # window = UNDER (the boundary rung is THE sweet spot);
            # no rung meets it = OVER the window, and then EVERY
            # measured quant is a sweet spot - the exam roster derives
            # the candidates per rung, each with its own bell
            # (min(window, its own tg x time_factor)). The walk itself
            # records only the boundary; over-window models carry
            # the flag, the exam reads the whole ladder.
            if not rec.get("sweet_spot") and n_beyond:
                rec["over_window"] = True
                print(
                    f"  {fam}: no rung fills the window within the time "
                    "parameter (OVER) - every measured quant is a sweet spot"
                )
            _state_store.save_state(state_file, state)
            print(
                f"  {fam}: curve complete - boundary {rec.get('sweet_spot')}, "
                f"{n_beyond} beyond points"
            )
    return sweet
