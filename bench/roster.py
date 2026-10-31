"""bench.roster -- the roster and the candidate machinery v9 needs,
extracted from the retired bench/sweet.py (the sweet walk is gone;
its ladder, window lookup, roster reader and build path survive
here as the exam's acquisition layer)."""

from __future__ import annotations

import json
import os
import sys
from typing import Any, cast

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import infra.convert_quant as convert_quant
import infra.hf_download as hf_download

# the quant acquisition ladder, sorted by tg/s (fastest first) - the
# EXAMINATION order within each family, and the order in which
# candidates surface. F16 last: the f16 master is the quantization
# source for every quant of its family, so it is examined (and
# deleted by the gc) last.
# THE SAFE LADDER (the author's safety ruling): every imatrix-
# dependent rung is cut - the imatrix computation is the sole source
# of the vulkan device-lost crashes (20 of the 22 recorded events,
# the RADV command-buffer OOM), and no quant is worth a kernel panic.
# The classic K-quant rungs (Q2_K .. F16) need no importance matrix.
# The grid reshapes accordingly: 64 models x 15 rungs = 960 pairs.
# BF16 is cut (the author's ruling: f16 is basically the same thing)
# THE SMALL GRID (the author's ruling: the grid is too large for the
# machine - no algorithm change, just a smaller state space):
# - the models: one per DYADIC billion-parameter tier (0.5, 1, 2, 4,
#   8B), the closest with no more than +/-5% difference from the
#   dyadic (the 16B and 32B tiers have no model within 5% - cut)
# - the model_quants: q4_0, q8_0, f16
# - the kv quants: q4_0, q8_0, f16
# The grid: 5 models x 3 model_quants = 15 pairs x 9 kv = 135
# candidates (was 64 x 15 x 49 = 47,040).
LADDER = [
    "Q4_0",
    "Q8_0",
    "F16",
]

# the fallback training window when a config.json cannot be read
WINDOW_DEFAULT = 262144  # every Qwen3.5 trains at 2**18


def dyadic_picks(
    tiers: list[float] | None = None,
    tolerance: float = 0.05,
) -> list[tuple[str, str]]:
    """THE DYADIC PICKS (the author's small-grid ruling): one model
    per billion-parameter tier (the dyadic ladder 0.5, 1, 2, 4, 8...),
    the closest with no more than +/-tolerance difference from the
    tier; tiers with no model inside the tolerance are cut. Returns
    (fam, repo) pairs, param-ascending."""
    if tiers is None:
        tiers = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0]
    full = roster_from_models_md()
    repos = dict(full)
    params: dict[str, float] = {}
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "md", "models.md"
    )
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) >= 5 and cells[0] in repos and cells[1] not in ("params", "", "unknown"):
                try:
                    params[cells[0]] = float(cells[1])
                except ValueError:
                    pass
    picks = []
    for t in tiers:
        cands = [
            (abs(p - t) / t, fam)
            for fam, p in params.items()
            if abs(p - t) / t <= tolerance
        ]
        if cands:
            cands.sort()
            fam = cands[0][1]
            picks.append((fam, repos[fam]))
    return picks


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
            if len(parts) >= 5 and parts[0] and parts[0] != "model name" and set(parts[0]) != {"-"}:
                # the table: name | params | f16 (GiB) | window | repo -
                # the repo is column 5 (the f16 column shifted it right)
                rows.append((parts[0], parts[4]))
    return rows


def window(repo: str, famdir: str) -> int:
    """The model's training window (text_config.max_position_embeddings;
    Qwen3.5 configs nest it)."""
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


def build(fam: str, repo: str, famdir: str, rung: str) -> str | None:
    """Acquire one rung file: download or quantize on demand. None =
    the rung cannot exist on this machine (RAM-infeasible, a tensor
    shape the quantizer cannot express, a tool failure) - recorded,
    skipped, never a model verdict."""
    hf_download.require_hub()
    list_repo_files = cast("Any", hf_download.list_repo_files)
    print(f"  [hub] listing files for {repo} ...")
    files = hf_download._with_timeout(lambda: list_repo_files(repo), f"list_repo_files {repo}")
    print(f"  [hub] {len(files)} files listed")
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
