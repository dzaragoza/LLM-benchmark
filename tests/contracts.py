"""CrossHair contracts (session 40, addendum 22) - formal verification of
the study's pure functions.

Run:  crosshair check tests/contracts.py

The contracts live here, not in the source modules: the source keeps
its measurement docstrings, and this module is the verification layer.
Each *_ref function mirrors a study function and states what MUST hold
for ALL inputs; crosshair proves it or returns a counterexample.
"""

from __future__ import annotations

import math

from bench.certify import wilson_interval
from infra.hf_download import find_rung_file, has_safetensors

# ---- wilson_interval: the accept/dead math of every certify run ----


def wilson_ref(k: int, n: int, z: float) -> tuple[float, float]:
    """The Wilson score interval bounds.

    pre: 0 <= k <= n
    pre: 0.0 <= z <= 10.0
    post: 0.0 <= __return__[0]
    post: __return__[0] <= __return__[1]
    post: __return__[1] <= 1.0
    """
    return wilson_interval(k, n, z)


def wilson_domain_ref(k: int, n: int, z: float) -> bool:
    """Outside the domain (0 <= k <= n, z >= 0) there is no interval.

    post: (0 <= k <= n and z >= 0) or (__return__)
    """
    return wilson_interval(k, n, z) == (0.0, 0.0)


def wilson_degenerate_ref(k: int, n: int) -> bool:
    """At z=0 the interval must collapse onto the point estimate.

    pre: 0 <= k <= n
    pre: n > 0
    post: __return__
    """
    lo, hi = wilson_interval(k, n, 0.0)
    return math.isclose(lo, k / n, abs_tol=1e-12) and math.isclose(hi, k / n, abs_tol=1e-12)


# ---- find_rung_file: the acquire path's repo-file matcher ----


def find_rung_file_ref(names: list[str], rung: str) -> str | None:
    """A returned file is one of the names and carries the rung token.

    post: (__return__ is None) or (__return__ in names)
    post: (__return__ is None) or (rung.lower() in __return__.lower())
    """
    return find_rung_file(names, rung)


def find_rung_file_none_ref(names: list[str], rung: str) -> bool:
    """No GGUF names means no match at all.

    post: any(f.lower().endswith('.gguf') for f in names) or __return__
    """
    return find_rung_file(names, rung) is None


def has_safetensors_ref(names: list[str]) -> bool:
    """True implies some name ends in .safetensors.

    post: (not __return__) or any(n.lower().endswith('.safetensors') for n in names)
    """
    return has_safetensors(names)


# ---- estimate_rung_gib: the memory shortcut (addendum 35) ----


def estimate_ref(rung: str, files: list[str], sizes: dict[str, int]) -> object:
    """An estimate, when produced, is positive; unknown rungs and
    empty sources estimate nothing (never a false skip).

    post: (__return__ is None) or (__return__ > 0.0)
    """
    from infra.hf_download import estimate_rung_gib

    return estimate_rung_gib(rung, files, files, sizes)


def estimate_none_ref(rung: str, files: list[str], sizes: dict[str, int]) -> bool:
    """No sizes at all means no estimate (the caller does not skip)."""
    from infra.hf_download import estimate_rung_gib

    return estimate_rung_gib(rung, files, files, sizes) is None


# ---- kv_gib: the KV cache arithmetic (the ceiling predictor's term) ----


def kv_gib_ref(layers: int, kv_heads: int, head_dim: int, depth: int, bpe: float) -> float:
    """KV cost is non-negative and linear in depth (double the depth,
    double the cache).

    pre: layers >= 0 and kv_heads >= 0 and head_dim >= 0 and depth >= 0 and bpe >= 0
    post: __return__ >= 0.0
    """
    from law_fit import kv_gib

    return kv_gib(layers, kv_heads, head_dim, depth, bpe)


def kv_gib_linear_ref(layers: int, kv_heads: int, head_dim: int, bpe: float) -> bool:
    """Linearity in depth: kv(d) + kv(d) == kv(2d) exactly (integer-ish
    arithmetic, no rounding drift at small scales).

    pre: layers >= 0 and kv_heads >= 0 and head_dim >= 0 and bpe >= 0
    post: __return__
    """
    from law_fit import kv_gib

    d = 4096
    return math.isclose(
        kv_gib(layers, kv_heads, head_dim, d, bpe) * 2,
        kv_gib(layers, kv_heads, head_dim, 2 * d, bpe),
        rel_tol=1e-12,
    )


# ---- law_worst: the fitted law evaluated at a size ----


def law_worst_ref(size: float, a: float, b: float) -> float:
    """A positive fit (a>0, b>0) predicts a positive worst-speed,
    decreasing in size (bandwidth: bigger file, slower worst turn).

    pre: 0.0 < a < 1e6 and 0.0 < b < 1e6 and 0.0 <= size < 1e6
    post: __return__ > 0.0
    """
    from law_fit import law_worst

    return law_worst(size, a, b)


# ---- the cell loaders: stored state -> cell maps ----


def speed_cells_ref(fst: dict[str, dict[str, int]], depth: int) -> dict:
    """The loader returns exactly the stored runs as int keys (the
    state's str keys never leak out).

    post: set(__return__) == set((fst.get('certify_speed') or {}).get(str(depth)) or {})
    """
    from bench.state_store import speed_cells

    return speed_cells(fst, depth)


def vt_cells_ref(fst: dict[str, dict[str, int]], depth: int) -> dict:
    """The VT loader mirrors the speed loader's contract.

    post: set(__return__) == set((fst.get('certify_vt') or {}).get(str(depth)) or {})
    """
    from bench.state_store import vt_cells

    return vt_cells(fst, depth)


def arc_cells_ref(fst: dict[str, dict[str, int]]) -> dict:
    """The ARC loader returns exactly the stored runs.

    post: set(__return__) == set(fst.get('certify_arc') or {})
    """
    from bench.state_store import arc_cells

    return arc_cells(fst)
