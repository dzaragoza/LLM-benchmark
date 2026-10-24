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
LADDER = [
    "IQ1_S",
    "Q2_0",
    "Q1_0",
    "IQ2_XXS",
    "Q2_K_S",
    "TQ2_0",
    "IQ1_M",
    "IQ2_XS",
    "IQ2_S",
    "Q2_K",
    "IQ3_XXS",
    "IQ2_M",
    "IQ3_XS",
    "IQ4_XS",
    "IQ3_S",
    "IQ3_M",
    "Q3_K_S",
    "Q4_0",
    "IQ4_NL",
    "Q3_K_M",
    "Q4_K_S",
    "Q4_1",
    "Q4_K_M",
    "Q3_K_L",
    "Q5_K_S",
    "TQ1_0",
    "Q5_0",
    "Q5_K_M",
    "Q5_1",
    "Q6_K",
    "Q8_0",
    "F16",
]
# BF16 is cut (the author's ruling: f16 is basically the same thing)

# the fallback training window when a config.json cannot be read
WINDOW_DEFAULT = 262144  # every Qwen3.5 trains at 2**18


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
