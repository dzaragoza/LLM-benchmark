"""picker_medals.py - the gold-medal panel on the picker pages
(session 41, addendum 72 - the author's ruling: "every time a new gold
medal is achieved, update the picker web pages. Remove the live status
page").

Reads state/benchmark-state.json, computes the exclusive gold per rung
(addendum 70: the fewest-parameter 2-sigma accept) via
bench.certify.gold_per_rung, and rewrites the GOLD_MEDALS block in
cpu-picker.html and gpu-picker.html in place - idempotent. The picker
pages stay hand-authored except for this one generated block, delimited
by BEGIN/END markers.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PAGES = ["cpu-picker.html", "gpu-picker.html"]
BEGIN = "      // BEGIN gold medals (generated - picker_medals.py)"
END = "      // END gold medals"

import bench.certify  # noqa: E402


def gold_medals(state: dict) -> list[dict]:
    """[{depth, model, params}] for every TOURNAMENT rung - None model
    where no gold stands. The alias-class params come with the winner."""
    from bench.constants import TOURNAMENT_DEPTHS

    rows = []
    for depth in TOURNAMENT_DEPTHS:
        winner = bench.certify.gold_per_rung(state, depth)
        params = bench.certify._registry_params(winner) if winner else None
        rows.append(
            {
                "depth": f"{depth // 1024}k",
                "model": winner,
                "params": f"{params:.2f}" if params is not None else "",
            }
        )
    return rows


def block(rows: list[dict]) -> str:
    lines = [BEGIN, "      var GOLD_MEDALS = ["]
    for r in rows:
        esc = r["model"].replace('"', '\\"') if r["model"] else ""
        params = r["params"].replace('"', '\\"')
        lines.append(f'        {{ depth: "{r["depth"]}", model: "{esc}", params: "{params}" }},')
    lines.append("      ];")
    lines.append(END)
    return "\n".join(lines)


def rewrite(page: str, rows: list[dict]) -> None:
    text = open(page).read()
    new = f"{block(rows)}\n"
    if BEGIN in text:
        head, rest = text.split(BEGIN, 1)
        _, tail = rest.split(END, 1)
        text = head + new + tail.lstrip("\n")
    else:
        anchor = "      var RUNGS = "
        assert anchor in text, f"{page}: no RUNGS anchor for the medals block"
        text = text.replace(anchor, new + anchor, 1)
    open(page, "w").write(text)


def main() -> None:
    state = json.load(open("state/benchmark-state.json"))
    rows = gold_medals(state)
    for page in PAGES:
        rewrite(page, rows)
        print(f"{page}: gold medals updated")
    for r in rows:
        print(f"  {r['depth']:>6}  {r['model'] or '-'} {r['params']}")


if __name__ == "__main__":
    main()
