"""bench.constants -- the study's shared design parameters (session
38, addendum 15). The rungs, the 20 climbs, the quant menus and the
reader line; single-sourced so the bench modules and the
orchestrator agree."""

from __future__ import annotations

import speed_gate

# session 43: ARC and FWE are retired - v7 sharpened the focus to
# reach vs reasoning; the fixed corpus carries both axes.
# The v6/v5 arcs remain in state history; no new arc/fwe cells.
COMBINED_TASKS = ("speed", "vt")
TASK_PASS_BARS = {"speed": 0, "vt": 4}
TOURNAMENT_DEPTHS = [4096, 8192, 16384, 32768, 65536, 131072, 262144]
TOURNAMENT_CLIMBS = 20
READER_WPS_DEFAULT = speed_gate.READER_WPS_DEFAULT
CORPUS_DEFAULT = speed_gate.CORPUS_DEFAULT
RUNG_DEFAULT = "Q8_0"
