#!/usr/bin/env bash
# The addendum-71 lineage sweep (pre-registered in the lab notebook).
# Run from the repo root:  nohup bash overnight-lineage.sh > overnight-lineage.log 2>&1 &
# Shell-agnostic to launch: this file itself runs under bash (shebang),
# so fish/zsh users only need the nohup line.
set -u

python3 full_benchmark.py --ladder Q8_0 --corpus ./live-corpus-cal50.json \
  --no-thinking --force \
  --state-file benchmark-state-lineage.json \
  --results-file benchmark-results-lineage.json \
  --arc-results-dir arc-results-lineage \
  "Qwen/Qwen2.5-0.5B-Instruct-GGUF" "Qwen/Qwen3.5-0.8B" \
  "Qwen/Qwen2.5-1.5B-Instruct-GGUF" "Qwen/Qwen3-1.7B-GGUF" \
  "Qwen/Qwen2.5-3B-Instruct-GGUF" "Qwen/Qwen3-4B-GGUF" \
  "Qwen/Qwen3.5-4B"

# ARC always (addendum 71): phases 5-6 ARC'd the selections above;
# this pass ARCs every family WITHOUT a selection (the wall-fails).
FAILED=$(python3 -c "
import json
s = json.load(open('benchmark-state-lineage.json'))
files = [r['file'] for f in s['families'].values() if not f.get('selected')
         for r in [f['runs'].get('Q8_0', {})] if r.get('file')]
print(','.join(files))")
if [ -n "$FAILED" ]; then
  python3 arc_eval.py --arc-num 1172 --arc-results-dir arc-results-lineage \
    --models "$FAILED"
fi
