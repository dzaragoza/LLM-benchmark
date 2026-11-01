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
# THE FULL SAFE LADDER (the exhaustive era): the 15 rungs,
# bits-per-weight ascending - the exhaustive collection sweeps them
# all (the author's ruling: collect the data, predict after).
LADDER = [
    "Q2_K",
    "Q3_K_S",
    "Q4_0",
    "Q3_K_M",
    "Q4_K_S",
    "Q4_1",
    "Q4_K_M",
    "Q3_K_L",
    "Q5_K_S",
    "Q5_0",
    "Q5_K_M",
    "Q5_1",
    "Q6_K",
    "Q8_0",
    "F16",
]

# the fallback training window when a config.json cannot be read
WINDOW_DEFAULT = 262144  # every Qwen3.5 trains at 2**18


def dyadic_picks(
    tiers: list[float] | None = None,
    per_tier: int = 3,
    tolerance: float = 0.28,
) -> list[tuple[str, str]]:
    """THE DYADIC PICKS (the author's rulings): per billion-parameter
    tier (the full dyadic ladder 0.5..32B), the `per_tier` CLOSEST
    models with no more than +/-tolerance difference from the tier
    (28%: the sparse tiers carry their thirds at 13-28% off - the
    0.5B tier's SmolLM2-360M at 27.6% - and the 16B/32B tiers enter
    at their 12.2B/27.4B models, 23-24%/14% off). Tiers contribute
    as many picks as the roster holds within the tolerance (the
    16B tier: 2; the 32B tier: 1). Returns (fam, repo) pairs,
    param-ascending - 18 picks on the current roster."""
    if tiers is None:
        tiers = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0]  # the full ladder
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
        cands.sort()
        for _off, fam in cands[:per_tier]:
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
