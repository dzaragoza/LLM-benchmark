"""bench.radio - trek v3 phase B: the per-tier end condition (the radio).

THE MODEL (the author's draft): every candidate (model, quant, k, v)
is a threat unit at every tier t in {1..128} where its checkpoint-t
score is not yet known:
- closed: the frontier is a fail - final at every tier, never a threat
- open: the frontier is a timeout at cap_u - known at t <= cap_u,
  a threat at t > cap_u: p_u(t) = P(s_u + d draws from D >= C_t + 1),
  d = log2(t / cap_u), s_u = the score at cap_u
- unknown: never probed - a threat at every tier:
  p_u(t) = P(-1 + g from G + log2(t) draws from D >= C_t + 1)
- infeasible (launch-failed only): excluded forever
- unfinished (an interrupted exam, transient): certification BLOCKED
  until its cell's next probe completes it - never modeled

THE POOLS (global, rebuilt from the log each evaluation):
- D (doubling gains): every probed curve's adjacent OBSERVED
  checkpoint pairs (t, 2t): gain = score(2t) - score(t), zeros incl.
- G (genesis): every probed curve: g = score(1) + 1

C_t = the champion at tier t = the max KNOWN checkpoint-t score (the
known part: the consecutive passes with time <= t - a lower bound on
the true score, so a live unit's s_u <= C_t always holds).

THE CERTIFICATION: tier t is CERTIFIED when Sum over live units of
p_u(t) < 0.01 (the union bound). The search STOPS when all 8 tiers
are certified. Pools empty -> the affected cells cannot be judged ->
keep searching. All computations are exact convolutions over the
pooled histograms (never sampling) in sorted order - the same state
gives bit-for-bit the same p's.
"""

from __future__ import annotations

import bisect
import math
from collections import Counter
from typing import Any

from bench.contracts import warn_contract

TIER_LADDER = [1, 2, 4, 8, 16, 32, 64, 128]
CERTIFY_EPS = 0.01
MAX_TIER = 128
MAX_D = 7  # log2(128/1)


def _curve(h: dict[int, Any]) -> tuple[str, float, int, list[float], float]:
    """classify one candidate's curve from its history: the kind, the
    cap (the frontier's timeout budget), the score (the highest level
    PASSED = the pass count - 1, per the unified convention - a wrong
    answer AT level k books score k-1), the pass times, and the run's
    final budget (the closing budget for a closed curve, the frontier
    budget for an open one - the attempted-bracket evidence)."""
    levels: dict[int, Any] = {}
    for k, rec in h.items():
        if isinstance(rec, dict):
            if isinstance(k, int):
                levels[k] = rec
            elif isinstance(k, str) and k.lstrip("-").isdigit():
                levels[int(k)] = rec
    if not levels:
        return ("infeasible", 0.0, -1, [], 0.0)
    times: list[float] = []
    while True:
        rec = levels.get(len(times))
        if rec is None:
            return ("unfinished", 0.0, len(times) - 1, times, 0.0)
        status = rec.get("status")
        if status == "pass":
            times.append(float(rec.get("time_s", 0.0)))
            continue
        if status == "timeout":
            return ("open", float(rec.get("timeout_s", 1.0)), len(times) - 1, times,
                    float(rec.get("timeout_s", 1.0)))
        return ("closed", float(rec.get("budget_s", 1.0)), len(times) - 1, times,
                float(rec.get("budget_s", 1.0)))


def _tier_score(times: list[float], t: int) -> int:
    """the known checkpoint-t score: the highest level PASSED with
    time <= t = the count of such levels - 1 (the unified convention:
    score = count - 1, never the count)."""
    n = 0
    for x in times:
        if x <= t:
            n += 1
        else:
            break
    return n - 1 if n else -1


def _conv(row: dict[int, float], dist: list[tuple[int, float]]) -> dict[int, float]:
    """one exact convolution step: row (*) dist, sorted order."""
    nxt: dict[int, float] = {}
    for g, p in sorted(row.items()):
        for gain, f in dist:
            k = g + gain
            nxt[k] = nxt.get(k, 0.0) + p * f
    return nxt


class _Tail:
    """a row's tail probability P(value >= gap), binary-searched."""

    def __init__(self, row: dict[int, float]) -> None:
        items = sorted(row.items())
        self.vals = [v for v, _ in items]
        probs = [p for _, p in items]
        n = len(probs)
        suf = [0.0] * (n + 1)
        for i in range(n - 1, -1, -1):
            suf[i] = suf[i + 1] + probs[i]
        self.suf = suf
        # ACCEPTANCE 1: every convolution row sums to 1
        warn_contract(
            "inv", "radio.row_sums_1", abs(suf[0] - 1.0) < 1e-9,
            f"the convolution row sums to {suf[0]!r}, not 1",
        )

    def p(self, gap: int) -> float:
        i = bisect.bisect_left(self.vals, gap)
        return self.suf[i]


def certify(st: dict[str, Any], kv_ladder: list[str]) -> dict[str, Any]:
    """the per-tier certification, computed exactly from the state.
    Returns {'tiers': {t: {...}}, 'all_certified': bool, 'blocked': bool}."""
    from bench import trek

    grid = trek.Grid()
    cands = st.get("candidates", {})
    D: Counter[int] = Counter()
    G: Counter[int] = Counter()
    C = {t: -1 for t in TIER_LADDER}
    units: list[tuple[str, float, int]] = []
    blocked = False
    # RULING 1: the pools are ATTEMPTED BRACKETS ONLY. A checkpoint
    # pair (t, 2t) enters D iff the curve RAN AT budget >= 2t (the
    # doubling was actually attempted) - for an open curve that is
    # its cap; for a closed curve, its closing budget (now recorded
    # in the history). The bracket that closes a curve contributes
    # its realized gain; post-closure pairs are excluded (capability
    # facts, not pace facts). Pre-closure brackets of a closed curve
    # are genuine pace evidence and stay. THE TWO-CELL QUORUM: the
    # pools may support certification only after drawing from >= 2
    # distinct cells (one cell = clones of the champion; the union
    # bound is degenerate). THE SCOPE: the threat units are feasible
    # CELLS (~2048), not the 100k candidates - each unknown cell
    # appears once; kv curves feed the pools, never the count.
    cells_seen: set = set()
    for fam in grid.models:
        for rung in grid.rungs:
            prefix = f"{fam}|{rung}|"
            cell_kind = "unknown"
            cell_cap = 0.0
            cell_s = -1
            cell_has_hist = False
            cell_unfinished = False
            for k in kv_ladder:
                for v in kv_ladder:
                    h = cands.get(prefix + k + "|" + v)
                    if h is None:
                        continue
                    cell_has_hist = True
                    kind, cap, s, times, run_budget = _curve(h)
                    if kind == "infeasible":
                        continue
                    if kind == "unfinished":
                        cell_unfinished = True
                        continue
                    ts = [_tier_score(times, t) for t in TIER_LADDER]
                    for t, sc in zip(TIER_LADDER, ts, strict=True):
                        if sc > C[t]:
                            C[t] = sc
                    # THE ATTEMPTED BRACKETS: every pair (t, 2t) the
                    # curve's run covered (2t <= the run's budget)
                    if run_budget > 0:
                        for i in range(len(TIER_LADDER) - 1):
                            if TIER_LADDER[i + 1] <= run_budget:
                                D[ts[i + 1] - ts[i]] += 1
                    G[ts[0] + 1] += 1
                    if kind == "open":
                        cell_kind = "open"
                        if cell_cap == 0.0 or cap < cell_cap:
                            cell_cap = cap
                    elif kind == "closed" and cell_kind == "unknown":
                        cell_kind = "closed"
                    if s > cell_s:
                        cell_s = s
            if cell_unfinished:
                blocked = True
            if not cell_has_hist:
                units.append(("unknown", 0.0, -1))
                continue
            units.append((cell_kind, cell_cap, cell_s))
            cells_seen.add((fam, rung))

    d_total = sum(D.values())
    g_total = sum(G.values())
    quorum = len(cells_seen) >= 2  # THE TWO-CELL QUORUM (the clone-killer)
    D_dist = sorted((g, c / d_total) for g, c in D.items()) if d_total else None
    G_dist = sorted((g, c / g_total) for g, c in G.items()) if g_total else None

    # the precomputed rows: D_rows[d] = the distribution of the sum of
    # d D-draws; U_rows[d] = g from G + d D-draws. d = 0 needs no pool.
    D_tails: list[_Tail | None] = [ _Tail({0: 1.0}) ]
    if D_dist is not None:
        row = {0: 1.0}
        for _ in range(MAX_D):
            row = _conv(row, D_dist)
            D_tails.append(_Tail(row))
    else:
        D_tails += [None] * MAX_D
    U_tails: list[_Tail | None] = []
    if G_dist is not None:
        row = {g: f for g, f in G_dist}
        U_tails.append(_Tail(row))
        if D_dist is not None:
            for _ in range(MAX_D):
                row = _conv(row, D_dist)
                U_tails.append(_Tail(row))
        else:
            U_tails += [None] * MAX_D
    else:
        U_tails = [None] * (MAX_D + 1)

    tiers: dict[str, Any] = {}
    all_certified = not blocked
    for t in TIER_LADDER:
        groups: Counter = Counter()
        for kind, cap, s in units:
            if kind == "closed" or kind == "unfinished":
                continue
            if kind == "open":
                if t <= cap:
                    continue  # known at this tier
                d = max(1, int(round(math.log2(t / cap))))
                groups[("open", s, d)] += 1
            else:  # unknown
                groups[("unknown", -1, int(round(math.log2(t))))] += 1
        # EDGE: a live unit's known score cannot exceed the champion
        warn_contract(
            "inv", "radio.score_le_champion",
            all(s <= C[t] for (_kind, s, _d) in groups),
            f"a live unit's known score exceeds the champion C[{t}]={C[t]}",
        )
        total = 0.0
        modelable = True
        for (kind, s, d), count in sorted(groups.items()):
            gap = C[t] + 1 - s
            if kind == "open":
                tail = D_tails[d] if d < len(D_tails) else None
                if tail is None:
                    if d == 0:
                        p = 1.0 if gap <= 0 else 0.0
                    else:
                        modelable = False  # pool D empty: cannot judge
                        break
                else:
                    p = 1.0 if gap <= 0 else tail.p(gap)
            else:
                tail = U_tails[d] if d < len(U_tails) else None
                if tail is None:
                    modelable = False  # pool G (or D) empty: cannot judge
                    break
                p = 1.0 if gap <= 0 else tail.p(gap)
            total += count * p
        certified = modelable and quorum and total < CERTIFY_EPS
        tiers[str(t)] = {
            "champion": C[t],
            "live_units": sum(groups.values()),
            "sum_p": total if modelable else None,
            "certified": certified,
            "pool_D": d_total,
            "pool_G": g_total,
            "quorum": quorum,
            # RULING 2: tier 1's certification rests on the support-cap
            # assumption (G's max genesis is the champion's own) - the
            # flagged eager tier, logged in every radio_stop
            "eager_tier": t == 1,
        }
        all_certified = all_certified and certified
    return {
        "tiers": tiers,
        "all_certified": all_certified,
        "blocked": blocked,
        "quorum": quorum,
        "cells_pooled": len(cells_seen),
    }


def summary(radio: dict[str, Any]) -> str:
    """one console line: the per-tier sums and the certified count.
    Tier 1 carries the * flag (RULING 2: its certification rests on
    the support-cap assumption - G's max genesis is the champion's
    own, so unknowns are structurally 0 at any sample size; the eager
    tier, flagged in every radio line and the radio_stop record)."""
    parts = []
    n = 0
    for t in TIER_LADDER:
        rec = radio["tiers"].get(str(t), {})
        sp = rec.get("sum_p")
        flag = "*" if rec.get("eager_tier") and rec.get("certified") else ""
        parts.append(f"t{t}={'-' if sp is None else f'{sp:.3g}'}{flag}")
        if rec.get("certified"):
            n += 1
    if not radio.get("quorum"):
        parts.append("no-quorum(<2 cells)")
    if radio.get("blocked"):
        parts.append("blocked(an unfinished exam)")
    return f"[radio] {' '.join(parts)} - certified {n}/8"
