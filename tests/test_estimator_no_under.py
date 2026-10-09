"""Pins: addendum 171 - the GPU estimator never under-estimates: every
census record in the committed state replays with est >= measured GPU
(the author's ruling: an under-estimate is an error; overall usage is
irrelevant, only GPU counts). The calibration: Q4_K 0.56 -> 0.65 (the
census measured 0.625-0.646 bpB), Q8_0 1.06 -> 1.0625 (the scale byte),
COMPUTE_FLOOR_GIB 0.03 -> 0.06 (the measured ~0.055 floor).
"""

import json
from pathlib import Path

import bench.v7 as v7

ROOT = Path(__file__).resolve().parent.parent


def test_no_under_estimate_in_any_census_record():
    state = json.loads((ROOT / "state" / "benchmark-state.json").read_text(encoding="utf-8"))
    rows = 0
    under = []
    for name, fst in state.get("families", {}).items():
        for ctx, c in (fst.get("v7") or {}).items():
            if not isinstance(c, dict):
                continue
            for suf, r in [("", c)] + [(f".{p}", a) for p, a in (c.get("arms") or {}).items()]:
                cen = r.get("mem_census") or {}
                v = (cen.get("devices") or {}).get("Vulkan0") or {}
                if not v:
                    continue
                p = r.get("params_b") or c.get("params_b")
                if p is None:
                    continue
                est = v7._alloc_total(
                    name, p, v7.family_geometry(name),
                    r.get("wq") or c.get("wq"), r.get("kq") or c.get("kq"),
                    r.get("vq") or c.get("vq"), int(ctx),
                )
                gpu = (
                    (v.get("model_gib") or 0)
                    + (v.get("context_gib") or 0)
                    + (v.get("compute_gib") or 0)
                )
                if est is None:
                    continue
                rows += 1
                if est + 1e-9 < gpu:
                    under.append(f"{name}@{ctx}{suf}: est {est:.3f} < gpu {gpu:.3f}")
    assert rows > 40, f"expected the full census record set, got {rows}"
    assert under == [], f"under-estimates remain: {under}"


def test_the_calibrated_constants():
    assert v7.W_QUANT_BPB["Q4_K"] == 0.65
    assert v7.W_QUANT_BPB["Q8_0"] == 1.0625
    assert v7.COMPUTE_FLOOR_GIB == 0.06
