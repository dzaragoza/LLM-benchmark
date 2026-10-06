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
