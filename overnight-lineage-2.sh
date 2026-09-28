#!/usr/bin/env bash
# The addendum-77 lineage sweep (pre-registered in the lab notebook):
# the three new lineages (phi 6, granite 7, minicpm 4) = 17 cells,
# plus gemma-3-1b (the in-scope-again probe of the word-sparse family).
# Run from the repo root:
#   nohup bash overnight-lineage-2.sh > overnight-lineage-2.log 2>&1 &
# Shell-agnostic to launch: this file itself runs under bash (shebang).
set -u

# Timestamped log header (addendum 77, item 5: the timing gap in run 1
# is closed at the source - every phase line below carries a duration).
SECONDS=0
echo "============================================================"
echo "sweep start: $(date -Is)"

# The sweep, one family per invocation so a family that dies (e.g. a
# conversion OOM) cannot take the rest down with it (addendum 77).
run_family () {
  echo "============================================================"
  echo "[$(date -Is)] family: $1  (elapsed ${SECONDS}s)"
  python3 full_benchmark.py --ladder Q8_0 --corpus ./live-corpus-cal50.json \
    --no-thinking --force \
    --state-file benchmark-state-lineage2.json \
    --results-file benchmark-results-lineage2.json \
    --arc-results-dir arc-results-lineage2 \
    "$1" || echo "FAMILY FAILED (recorded; the sweep continues - addendum 77)"
}

# --- phi (Microsoft; anchor 0.418 measured, phi-class) ---
run_family "microsoft/phi-4-mini-instruct"        # 3.8B, 3.8B trio member
run_family "microsoft/Phi-3.5-mini-instruct"      # 3.8B trio
run_family "microsoft/Phi-3-mini-4k-instruct"      # 3.8B trio
run_family "microsoft/phi-2"                      # 2.7B base
run_family "microsoft/phi-1_5"                    # 1.3B base
run_family "microsoft/phi-1"                      # 1.3B base

# --- granite (IBM; pooled anchor 0.366) ---
run_family "ibm-granite/granite-4.2-3b"           # 3B, thinking toggle -> non-thinking
run_family "ibm-granite/granite-4.0-h-micro"      # 3B HYBRID Mamba; llama.cpp support risk
run_family "ibm-granite/granite-3.3-2b-instruct" # 2B quartet
run_family "ibm-granite/granite-3.2-2b-instruct" # 2B quartet
run_family "ibm-granite/granite-3.1-2b-instruct" # 2B quartet
run_family "ibm-granite/granite-3.0-2b-instruct" # 2B quartet

# --- minicpm (OpenBMB; pooled anchor 0.366) ---
run_family "openbmb/MiniCPM3-4B"                  # 4B sharp edge
run_family "openbmb/MiniCPM-2B-sft"              # 2.4B (2.4B non-embedding)
run_family "openbmb/MiniCPM-1B-sft"               # 1.2B
run_family "openbmb/MiniCPM4-0.5B"                # 0.5B

# --- gemma (Google; back in scope, addendum 77) ---
run_family "google/gemma-3-1b-it"                # 1B; the word-sparse-family probe

# ARC always (addendum 71): the selections ARC'd above; this pass ARCs
# every family WITHOUT a selection (the wall-fails).
echo "============================================================"
echo "[$(date -Is)] ARC pass for unselected families (elapsed ${SECONDS}s)"
FAILED=$(python3 -c "
import json
s = json.load(open('benchmark-state-lineage2.json'))
files = [r['file'] for f in s['families'].values() if not f.get('selected')
         for r in [f['runs'].get('Q8_0', {})] if r.get('file')]
print(','.join(files))" 2>/dev/null || true)
if [ -n "$FAILED" ]; then
  python3 arc_eval.py --arc-num 1172 --arc-results-dir arc-results-lineage2 \
    --models "$FAILED" || echo "ARC pass failed (recorded; the sweep continues)"
fi

# The per-model p05 extraction (addendum 77, item 5 - the run-1 gap
# closed at the source: grading needs the per-model p05s the same
# evening, not a second extraction pass on the author machine).
echo "============================================================"
echo "[$(date -Is)] per-model p05 extraction (elapsed ${SECONDS}s)"
python3 - << 'PYEOF'
import glob, json, math, os
# The dump is a flat list of turn records (speed_gate.py line 845:
# json.dump(turns) - each turn carries words_per_token and conv).
for path in sorted(glob.glob('models/*/*.live-dump*.json') +
                   glob.glob('models/*/*.sentinel*.json')):
    try:
        d = json.load(open(path))
    except Exception as e:
        print(f"  unreadable dump {path}: {e}"); continue
    turns = d if isinstance(d, list) else (d.get('turns') or [])
    wt = [t['words_per_token'] for t in turns
          if isinstance(t, dict) and t.get('words_per_token')]
    if not wt:
        print(f"  {os.path.basename(os.path.dirname(path)):28s} no w/t records"); continue
    wt.sort()
    n = len(wt)
    k = max(0, math.ceil(0.05 * n) - 1)  # the gate's own p05 rule (line 899)
    print(f"  {os.path.basename(os.path.dirname(path)):28s} "
          f"n={n:4d} min={wt[0]:.3f} p05={wt[k]:.3f} mean={sum(wt)/n:.3f}")
PYEOF

# The git tail (addendum 77, item 4 - the author's standing order:
# the log, state, results and dumps land in git the same evening).
echo "============================================================"
echo "[$(date -Is)] committing artifacts to git (elapsed ${SECONDS}s)"
git add -f overnight-lineage-2.log \
           benchmark-state-lineage2.json \
           benchmark-results-lineage2.json 2>/dev/null \
  || echo "nothing new to commit"
# per-turn dumps: the grading instrument's raw data (p05, Delta,
# stall attribution). Small JSON, force-added past models/ ignore.
git add -f models/*/*.live-dump*.json models/*/*.sentinel*.json 2>/dev/null || true
git add arc-results-lineage2/ 2>/dev/null || true
if git diff --cached --quiet; then
  echo "no changes to commit"
else
  git commit -m "lineage sweep 2 results (addendum 77): phi/granite/minicpm/gemma-3-1b - log, state, results, per-turn dumps, ARC CSVs" \
    || echo "commit failed (recorded)"
  git push origin main || echo "push failed (recorded - run: git push origin main)"
fi
echo "============================================================"
echo "sweep end: $(date -Is)  (total ${SECONDS}s)"
