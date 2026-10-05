"""bench.constants -- the study's shared design parameters (session
38, addendum 15). The rungs, the 21 climbs, the quant menus and the
reader line; single-sourced so the bench modules and the
orchestrator agree."""

from __future__ import annotations

import speed_gate

COMBINED_TASKS = ("speed", "fwe", "vt", "arc")
ARC_CELL_K = 5  # questions per cell (the author's ruling: k=5, like VT's 5 names)
ARC_RUN_CTX = 4096  # ARC ignores context depth - one measurement, verdict applies to every rung
CERTIFY_LEVELS = ["at_least_one", "1_sigma", "2_sigma"]
TASK_PASS_BARS = {"speed": 0, "fwe": 2, "vt": 4, "arc": 4}
TOURNAMENT_DEPTHS = [4096, 8192, 16384, 32768, 65536, 131072, 262144]
TOURNAMENT_CLIMBS = 21
TOURNAMENT_MODEL_QUANTS = ["Q2_K", "Q3_K", "Q4_K", "Q5_K", "Q6_K", "Q8_0"]
TOURNAMENT_KV_QUANTS = ["q4_0", "q5_0", "q6_K", "q8_0", "f16"]
READER_WPS_DEFAULT = speed_gate.READER_WPS_DEFAULT
CORPUS_DEFAULT = speed_gate.CORPUS_DEFAULT
RUNG_DEFAULT = "Q8_0"
