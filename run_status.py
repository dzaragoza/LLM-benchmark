#!/usr/bin/env python3
"""run_status.py - the live f16 run's status, injected into the picker page.

Session 41, addendum 41 (the author's ruling: "start updating the web
pages with this info - it helps me visualize"). Reads the state file +
results.txt the run is already committing (the addendum-31 verdict
pushes), derives the per-family verdict table for the CURRENT pass, and
rewrites the <div id="runStatus"> block in cpu-picker.html in place.
Idempotent: the div's content is regenerated wholesale each run.

The pass being visualized: the (f16,f16,f16) full-capacity first pass -
every family at the 4,096 rung first, param-ascending, each cell's four
tasks (speed/fwe/vt/arc) at the 2-sigma bar, medals derived from the
stored evidence. Statuses: DEAD (which task killed it, at which rung,
with which tally), or the live cell tallies when still climbing.
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(ROOT, "state", "benchmark-state.json")
RESULTS = os.path.join(ROOT, "results.txt")
PAGE = os.path.join(ROOT, "cpu-picker.html")

MARK = '<div id="runStatus"'

TASK_LABELS = {
    "speed": "streaming speed (the 5 w/s reader line)",
    "fwe": "hidden-word retrieval (FWE)",
    "vt": "variable tracking (VT)",
    "arc": "ARC-Challenge answers",
}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def family_rows() -> list[dict]:
    """One row per family in the state file, enriched from results.txt."""
    with open(STATE, encoding="utf-8") as f:
        st = json.load(f)
    txt = open(RESULTS, encoding="utf-8", errors="replace").read()

    rows = []
    for name in st.get("families", {}):
        verdict = re.findall(rf"verdict: {re.escape(name)} (\w+) at rung ([\d,]+)", txt)
        row = {
            "name": name,
            "verdict": verdict[-1][0] if verdict else "climbing",
            "rung": verdict[-1][1] if verdict else "",
            "kill": "",
            "tally": "",
        }
        if row["verdict"] == "DEAD":
            idx = txt.rfind(f"verdict: {name}")
            seg = txt[max(0, idx - 800) : idx]
            d = re.findall(r"DEAD - (\w+) cannot reach the bar at ([\d,]+) \(([\d/]+)", seg)
            if d:
                row["kill"], row["rung"], row["tally"] = d[-1]
        else:
            # live tallies: the last cell lines for this family
            idx = txt.rfind(f"{name} speed:")
            seg = txt[idx : idx + 4000] if idx >= 0 else ""
            tally = re.findall(r"-> (\w+) (\d+)/(\d+) ", seg)
            if tally:
                row["tally"] = ", ".join(f"{t} {k}/{n}" for t, k, n in tally[-4:])
        rows.append(row)
    return rows


def render(rows: list[dict]) -> str:
    out = ['<div id="runStatus" class="panel">']
    out.append(
        "<h2>Live: the f16 full-capacity pass (all models, (f16,f16,f16), param-ascending)</h2>"
    )
    out.append(
        '<p style="font-size: 0.9rem">Every registered family, measured at its '
        "full capacity &mdash; no quantization &mdash; starting at the 4,096 "
        "rung. Each cell runs the four tasks; a family dies when any one "
        "cannot reach the 2-sigma bar. Updated as verdicts are committed.</p>"
    )
    out.append("<table>")
    out.append("<tr><th>family</th><th>status</th><th>killed by</th><th>tally</th></tr>")
    for r in rows:
        status = "climbing" if r["verdict"] == "climbing" else esc(r["verdict"].lower())
        kill = esc(r["kill"]) if r["kill"] else "&mdash;"
        kill_full = f"{kill} ({TASK_LABELS[r['kill']]})" if r["kill"] in TASK_LABELS else kill
        tally = esc(r["tally"]) if r["tally"] else "&mdash;"
        rung = f" @ {esc(r['rung'])} ctx" if r["rung"] and r["verdict"] == "DEAD" else ""
        out.append(
            f"<tr><td>{esc(r['name'])}</td><td>{status}{rung}</td>"
            f"<td>{kill_full}</td><td>{tally}</td></tr>"
        )
    out.append("</table>")
    out.append(
        '<p style="font-size: 0.8rem; color: #666">Source: the run\'s own commits '
        "(addendum 31: every verdict is pushed immediately). Regenerate with "
        "<code>python3 run_status.py</code>.</p>"
    )
    out.append("</div>")
    return "\n".join(out)


def main() -> None:
    rows = family_rows()
    block = render(rows)
    with open(PAGE, encoding="utf-8") as f:
        page = f.read()
    if MARK in page:
        pre, post = page.split(MARK, 1)
        post = post.split("</div>", 1)[1] if "</div>" in post else ""
        page = pre + block + post
    else:
        anchor = "<h2>All measured models"
        pre, post = page.split(anchor, 1)
        page = pre + block + "\n    " + anchor + post
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"runStatus updated: {len(rows)} families")


if __name__ == "__main__":
    sys.exit(main())
