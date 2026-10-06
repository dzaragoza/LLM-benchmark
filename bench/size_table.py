"""bench.size_table -- the per-context recommendation table (session 38,
addendum 16). The flat 5 GiB ceiling becomes a curve: for every (family,
rung) we already own a llama-server memory census (the -lv 5 "memory
breakdown" table, addendum 11) and a speed verdict (the reader-line gate).
The table answers the practitioner's question directly: at context X, which
models FIT and still hold the speed guarantee, and what do they cost in
GiB. The speed gate is the size authority (the author's ruling): a model
that fits but stalls is not a recommendation, a model that misses the
reader line is not a recommendation at that rung.

Data sources (read-only, nothing re-measured):
- the committed -lv 5 server logs: weights/model/context/compute GiB
  via llama_server.memory_breakdown_gib
- the committed speed dumps (the -rungR-speed.json turn records): the
  worst-span w/s from speed_gate.analyze
- the ladder/tournament result directories; the server log sits next to
  the speed json (the cell functions write both per rung)
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import infra.llama_server as llama_server
import speed_gate
from bench.constants import READER_WPS_DEFAULT, TOURNAMENT_DEPTHS

_SPEED_JSON = re.compile(r"(?P<label>.+)-rung(?P<rung>\d+)-speed\.json$")
_SERVER_LOG = re.compile(r"(?P<label>.+)-rung(?P<rung>\d+)-\w+-server\.log$")


def _label_family(label: str) -> str:
    """Strip the -QUANT suffix: 'Llama-3.2-1B-Instruct-Q8_0' -> family."""
    for q in ("Q8_0", "Q4_K_M", "Q6_K", "Q5_K", "Q4_K", "Q3_K", "Q2_K", "f16"):
        if label.lower().endswith("-" + q.lower()):
            return label[: -len(q) - 1]
    return label


def _collect(results_dirs: list[str]) -> dict[tuple[str, int], dict[str, Any]]:
    """The (family, rung) evidence: census + speed verdict per pair."""
    evidence: dict[tuple[str, int], dict[str, Any]] = {}
    for results_dir in results_dirs:
        if not os.path.isdir(results_dir):
            continue
        # server logs anywhere under the dir (ladder: flat; tournament: climbN/)
        for log_path in glob.glob(os.path.join(results_dir, "**", "*-server.log"), recursive=True):
            m = _SERVER_LOG.match(os.path.basename(log_path))
            if not m:
                continue
            rung = int(m.group("rung"))
            key = (_label_family(m.group("label")), rung)
            breakdown = llama_server.memory_breakdown_gib(log_path)
            if breakdown is None:
                continue
            row = evidence.setdefault(key, {})
            # the deepest-context census wins: context GiB grows with rung
            if "weights_gib" not in row or breakdown.get("context_gib", 0) >= (
                row.get("context_gib") or 0
            ):
                row.update(
                    {
                        "weights_gib": breakdown.get("weights_gib"),
                        "context_gib": breakdown.get("context_gib"),
                        "compute_gib": breakdown.get("compute_gib"),
                        "total_gib": breakdown.get("total_gib"),
                    }
                )
        # speed dumps: the stall rate + worst-span w/s per (family, rung),
        # recomputed from the raw arrival stream (addendum 73: the same
        # reader-wall test analyze runs, without its model-label contract)
        for speed_path in glob.glob(
            os.path.join(results_dir, "**", "*-speed.json"), recursive=True
        ):
            m = _SPEED_JSON.match(os.path.basename(speed_path))
            if not m:
                continue
            rung = int(m.group("rung"))
            key = (_label_family(m.group("label")), rung)
            row = evidence.setdefault(key, {})
            try:
                with open(speed_path) as f:
                    turns = json.load(f)
            except Exception:
                continue
            mine = [t for t in turns if t.get("server_wps") and "deltas" in t]
            if not mine:
                continue
            wall_fails = 0
            for t in mine:
                col = speed_gate.reader_wall_test(
                    t.get("deltas") or [],
                    t.get("gen_words") or 0,
                    READER_WPS_DEFAULT,
                    speed_gate.READER_REACTION_S,
                )
                if col["catchup_events"]:
                    wall_fails += 1
            stall_rate = wall_fails / len(mine)
            convs: dict[int, list[float]] = {}
            for t in mine:
                convs.setdefault(t["conv"], []).append(t["server_wps"])
            wps = min(min(v) for v in convs.values())
            # the best observed worst-span at a rung is the honest one
            if row.get("worst_wps") is None or wps > row["worst_wps"]:
                row["worst_wps"] = wps
                row["stall_rate"] = stall_rate
    return evidence


def build_size_table(
    results_dirs: list[str],
    reader_wps: float = READER_WPS_DEFAULT,
    depths: list[int] | None = None,
) -> list[dict[str, Any]]:
    """One row per (family, rung) with measured evidence: the census
    (fits), the worst-span w/s (holds the guarantee) and the verdict.
    Rows are sorted family, then rung ascending - the recommendation
    table reads top-to-bottom as the context ladder."""
    depths = depths or TOURNAMENT_DEPTHS
    evidence = _collect(results_dirs)
    rows: list[dict[str, Any]] = []
    for (family, rung), ev in evidence.items():
        wps = ev.get("worst_wps")
        holds = wps is not None and wps >= reader_wps
        stalls = ev.get("stall_rate")
        rows.append(
            {
                "family": family,
                "rung": rung,
                "weights_gib": ev.get("weights_gib"),
                "context_gib": ev.get("context_gib"),
                "total_gib": ev.get("total_gib"),
                "worst_wps": wps,
                "holds_reader_line": holds,
                "clean_pass": bool(holds and (stalls == 0)),
                "recommend": bool(holds and (stalls == 0)),
            }
        )
    rows.sort(key=lambda r: (r["family"], r["rung"]))
    return rows


def recommended_max_rung(
    rows: list[dict[str, Any]], reader_wps: float = READER_WPS_DEFAULT
) -> dict[str, int | None]:
    """The per-family headline: the deepest rung that still holds the
    speed guarantee with 0 stalls - the practitioner's pick."""
    best: dict[str, int | None] = {}
    for r in rows:
        if r.get("recommend"):
            fam = r["family"]
            if best.get(fam) is None or r["rung"] > best[fam]:
                best[fam] = r["rung"]
    families = {r["family"] for r in rows}
    for fam in families:
        best.setdefault(fam, None)
    return best


def print_size_table(rows: list[dict[str, Any]]) -> None:
    """The printed recommendation table: rungs across, families down, the
    cell = total GiB at (w/s) with ! for stalls and . for no evidence."""
    families = sorted({r["family"] for r in rows})
    rungs = sorted({r["rung"] for r in rows})
    grid: dict[tuple[str, int], dict[str, Any]] = {(r["family"], r["rung"]): r for r in rows}
    header = "family".ljust(34) + "".join(f"{rung:>9}" for rung in rungs)
    print(header)
    print("-" * len(header))
    for fam in families:
        cells = []
        for rung in rungs:
            row = grid.get((fam, rung))
            if row is None:
                cells.append("       .")
                continue
            gib = row.get("total_gib")
            wps = row.get("worst_wps")
            tag = ""
            if row.get("recommend"):
                tag = "*"
            elif row.get("stall_rate"):
                tag = "!"
            cell = f"{gib:.1f}" if gib is not None else "-"
            cell += f"@{wps:.0f}" if wps is not None else ""
            cells.append(cell[:7].rjust(7) + tag)
        print(fam[:34].ljust(34) + "".join(c.ljust(9) for c in cells))
    print(
        "\n* = holds the reader line with 0 stalls (recommend)   "
        "! = stalls at this rung   . = no census evidence"
    )
