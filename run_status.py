#!/usr/bin/env python3
"""run_status.py - the live f16 run's status page (live_status.html).

Session 41, addendum 42 (the author's ruling: "better not mess up with
the html. Create live_status.html for this info. Put also the difficulty
in each gate"). Standalone page - the picker pages stay untouched.
Reads the state file + results.txt the run is already committing (the
addendum-31 verdict pushes), derives the per-family verdict table for
the CURRENT pass, and rewrites live_status.html wholesale - idempotent.

The pass being visualized: the (f16,f16,f16) full-capacity first pass -
every family param-ascending at the 4,096 rung first, each cell's four
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
PAGE = os.path.join(ROOT, "live_status.html")

# the four gates, their difficulty (the pass bar), and what a cell does
GATES = {
    "speed": {
        "label": "streaming speed",
        "difficulty": "worst words/s >= 5 (a fast reader's line, 300 wpm); "
        "0 stalls per conversation",
        "measures": "can it stream an answer at reading pace at this depth?",
    },
    "fwe": {
        "label": "hidden-word retrieval (FWE)",
        "difficulty": ">= 2 of 3 hidden words found in a long coded text",
        "measures": "does it actually find things buried in its context?",
    },
    "vt": {
        "label": "variable tracking (VT)",
        "difficulty": "all 5 assigned values recalled across 4 chain hops",
        "measures": "does it track state through a long conversation?",
    },
    "arc": {
        "label": "ARC-Challenge answers",
        "difficulty": ">= 4 of 5 grade-school science questions correct",
        "measures": "can it reason at all? (rung-independent, asked once)",
    },
}

CERT = (
    "certification: 2 sigma - a family certifies a rung only when every "
    "gate's pass count clears the Wilson lower bound >= 0.50 at n=20 cells; "
    "a gate that cannot mathematically reach the bar kills the family at "
    "that rung (dead), and the medals (0.5/1/2 sigma) are derived from the "
    "stored evidence, never requested"
)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _pass_segment() -> str:
    """results.txt scoped to the CURRENT pass: everything after the
    pass's first --force-rung f16 header."""
    txt = open(RESULTS, encoding="utf-8", errors="replace").read()
    starts = [
        m.start()
        for m in re.finditer(r"===== \S+ \| full_benchmark\.py[^=]*=====", txt)
        if "--force-rung f16" in m.group(0)
    ]
    return txt[starts[0] :] if starts else txt


def infeasible_families(seg: str) -> dict[str, int]:
    """The families OUT of the benchmark (addendum 45): the trained
    window cannot run the rung, so no cell was ever measurable - the
    family's cells and kills never enter any statistic. Detected from
    the addendum-130e error lines (the state's 'infeasible' field is
    the live-run record; this covers families benched before the
    verdict existed). Returns {family: trained window}."""
    out: dict[str, int] = {}
    for m in re.finditer(
        r"===== \S+ \| full_benchmark\.py[^=]*=====(.*?)(?====== |\Z)",
        seg,
        re.S,
    ):
        block = m.group(0)
        fam = re.search(r"verdict: ([\w.\-/]+) (?:DEAD|INFEASIBLE)", block)
        capped = re.search(r"accepted -c \d+ but runs n_ctx (\d+)", block)
        if fam and capped:
            out[fam.group(1)] = int(capped.group(1))
    return out


def gate_kill_rates() -> dict[str, dict[str, int]]:
    """Per gate, over the CURRENT pass (everything after the pass's
    first run header): families killed, and the pass fraction of all
    measured cells - the raw difficulty of the bar (addendum 43:
    'difficulty' = kill rate, the author's ruling). INFEASIBLE families
    (addendum 45) are OUT of the benchmark - their blocks are cut from
    the segment before any count, so neither their kills nor their
    cells (all FAIL-by-400) enter the statistics."""
    seg = _pass_segment()
    infeasible = infeasible_families(seg)
    for fam in infeasible:
        block = (
            rf"===== \S+ \| full_benchmark\.py[^=]*=====(?:(?!===== ).)*?"
            rf"verdict: {re.escape(fam)} (?:DEAD|INFEASIBLE)[^\n]*\n"
        )
        seg = re.sub(block, "", seg, flags=re.S)
    kills: dict[str, int] = {}
    for task, _ in re.findall(r"DEAD - (\w+) cannot reach the bar at [\d,]+ \(([\d/]+)", seg):
        kills[task] = kills.get(task, 0) + 1
    # per-CELL outcomes (the k/n in the cell lines is a RUNNING tally -
    # summing it double-counts; the PASS/FAIL verdict is per cell)
    tal: dict[str, list[int]] = {}
    for task, outcome in re.findall(r"cell \d+ \(rung [\d,]+\) (\w+): .*?-> (PASS|FAIL)", seg):
        a = tal.setdefault(task, [0, 0])
        a[0] += 1 if outcome == "PASS" else 0
        a[1] += 1
    return {
        task: {
            "kills": kills.get(task, 0),
            "passes": tal.get(task, [0, 0])[0],
            "measured": tal.get(task, [0, 0])[1],
        }
        for task in GATES
    }


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
        if name in infeasible_families(txt):
            # the family's own block shows the trained-window cap - no
            # cell was ever measurable (addendum 45): out of the benchmark
            row["verdict"] = "INFEASIBLE"
        if row["verdict"] == "DEAD":
            idx = txt.rfind(f"verdict: {name}")
            seg = txt[max(0, idx - 800) : idx]
            d = re.findall(r"DEAD - (\w+) cannot reach the bar at ([\d,]+) \(([\d/]+)", seg)
            if d:
                row["kill"], row["rung"], row["tally"] = d[-1]
        else:
            idx = txt.rfind(f"{name} speed:")
            seg = txt[idx : idx + 4000] if idx >= 0 else ""
            tally = re.findall(r"-> (\w+) (\d+)/(\d+) ", seg)
            if tally:
                row["tally"] = ", ".join(f"{t} {k}/{n}" for t, k, n in tally[-4:])
        rows.append(row)
    return rows


def render(rows: list[dict]) -> str:
    out = []
    out.append("<!doctype html>")
    out.append('<html lang="en">')
    out.append('<head><meta charset="utf-8" />')
    out.append('<meta name="viewport" content="width=device-width, initial-scale=1" />')
    out.append("<title>LLM benchmark &mdash; live run status</title>")
    out.append(
        """<style>
      :root { color-scheme: light dark; }
      * { box-sizing: border-box; }
      body {
        font-family: Georgia, "Times New Roman", serif;
        margin: 0 auto; max-width: 900px; padding: 1.5rem 1rem 4rem;
        line-height: 1.55;
      }
      h1 { font-size: 1.4rem; margin-bottom: 0.2rem; }
      .sub { color: #666; font-size: 0.95rem; font-style: italic;
             margin-bottom: 1.4rem; }
      h2 { font-size: 1.05rem; margin-top: 1.6rem; }
      table { border-collapse: collapse; width: 100%; margin: 0.6rem 0 1.2rem;
              font-size: 0.92rem; }
      th, td { border: 1px solid #bbb; padding: 0.35rem 0.55rem;
               text-align: left; vertical-align: top; }
      th { font-family: Verdana, Arial, sans-serif; font-size: 0.75rem; }
      .panel { border: 1px solid #bbb; border-radius: 8px;
               padding: 1rem 1.2rem; margin: 0.6rem 0 1.2rem;
               background: rgba(127, 127, 127, 0.06); }
      .footnote { font-size: 0.8rem; color: #666; }
      code { font-family: monospace; }
    </style>"""
    )
    out.append("</head><body>")
    out.append("<h1>Live run status &mdash; the f16 full-capacity pass</h1>")
    out.append(
        '<p class="sub">every registered family at (f16,f16,f16) - full '
        "quality, full size - param-ascending; updated as the run commits "
        "its verdicts</p>"
    )

    # the gates panel: difficulty per gate
    out.append('<div class="panel">')
    out.append("<h2>The four gates and their difficulty</h2>")
    out.append("<table>")
    out.append("<tr><th>gate</th><th>difficulty (the pass bar)</th><th>what it measures</th></tr>")
    for key, g in GATES.items():
        out.append(
            f"<tr><td><strong>{key}</strong><br>{esc(g['label'])}</td>"
            f"<td>{esc(g['difficulty'])}</td>"
            f"<td>{esc(g['measures'])}</td></tr>"
        )
    out.append("</table>")
    out.append(f"<p class='footnote'>{esc(CERT)}</p>")
    out.append("</div>")

    # the difficulty panel: kill rate per gate (this pass)
    kr = gate_kill_rates()
    total_kills = sum(v["kills"] for v in kr.values())
    out.append('<div class="panel">')
    out.append("<h2>Difficulty &mdash; the kill rate, this pass</h2>")
    out.append("<table>")
    out.append(
        "<tr><th>gate</th><th>families killed</th><th>cells passed</th><th>pass rate</th></tr>"
    )
    for key, v in kr.items():
        rate = (v["passes"] / v["measured"]) if v["measured"] else 0.0
        out.append(
            f"<tr><td><strong>{key}</strong></td><td>{v['kills']}</td>"
            f"<td>{v['passes']}/{v['measured']}</td>"
            f"<td>{rate:.0%}</td></tr>"
        )
    out.append(
        f"<tr><td><strong>any</strong></td><td>{total_kills}</td><td>&mdash;</td><td>&mdash;</td></tr>"
    )
    out.append("</table>")
    out.append(
        '<p class="footnote">families killed = the gate that mathematically '
        "could not reach the 2-sigma bar; pass rate = passed cells / measured "
        "cells across every family this pass &mdash; the raw lethality of "
        "each bar.</p>"
    )
    out.append("</div>")

    # the verdict table
    out.append("<h2>The families, in evaluation order</h2>")
    out.append("<table>")
    out.append("<tr><th>family</th><th>status</th><th>killed by</th><th>last tally</th></tr>")
    for r in rows:
        if r["verdict"] == "INFEASIBLE":
            out.append(
                f"<tr><td>{esc(r['name'])}</td>"
                "<td>out of the benchmark &mdash; trained window below the "
                "first rung (addendum 45)</td><td>&mdash;</td><td>&mdash;</td></tr>"
            )
            continue
        status = "climbing" if r["verdict"] == "climbing" else esc(r["verdict"].lower())
        rung = f" @ {esc(r['rung'])} ctx" if r["rung"] and r["verdict"] == "DEAD" else ""
        if r["kill"]:
            g = GATES.get(r["kill"], {})
            kill = f"<strong>{esc(r['kill'])}</strong>" + (
                f"<br>{esc(g.get('label', ''))}" if g else ""
            )
        else:
            kill = "&mdash;"
        tally = esc(r["tally"]) if r["tally"] else "&mdash;"
        out.append(
            f"<tr><td>{esc(r['name'])}</td><td>{status}{rung}</td>"
            f"<td>{kill}</td><td>{tally}</td></tr>"
        )
    out.append("</table>")
    out.append(
        '<p class="footnote">Source: the run\'s own commits (addendum 31: '
        "every verdict is pushed immediately). Regenerate with "
        "<code>python3 run_status.py</code>.</p>"
    )
    out.append("</body></html>")
    return "\n".join(out)


def main() -> None:
    rows = family_rows()
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(render(rows))
    print(f"live_status.html written: {len(rows)} families")


if __name__ == "__main__":
    sys.exit(main())
