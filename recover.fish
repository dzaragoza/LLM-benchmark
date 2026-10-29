#!/usr/bin/env fish
# recover.fish - the incident cleanup, fish-native (NO heredocs)
# Run from the repo root. Idempotent: every step checks its state.

# --- 1. resolve any stuck rebase (your data wins - it is the newest) ---
if test -d .git/rebase-merge; or test -d .git/rebase-apply
    echo "==> a rebase is in progress - resolving with your (newest) data"
    git checkout --theirs state/trek-state.json
    git add -A
    GIT_EDITOR=true git rebase --continue
    git push origin main
else
    echo "==> no rebase in progress - skipping the resolution"
end

# --- 2. make sure main is where we think it is ---
git checkout main; or exit 1
git pull --rebase --autostash; or exit 1

# --- 3. re-apply the Qwen cleanup (the rebase took YOUR state, which
#        still carries the 49 false _launch markers from the corrupt
#        file - the failure was the pipeline's, not the candidates') ---
echo "==> removing the false _launch markers (the corrupt-file incident)"
python3 -c '
import sys
sys.path.insert(0, ".")
from bench import trek
st = trek.load_state()
removed = 0
for key in list(st["candidates"]):
    h = st["candidates"][key]
    if key.startswith("Qwen2.5-1.5B-Instruct|IQ3_XXS|") and set(h.keys()) == {"_launch"}:
        del st["candidates"][key]
        removed += 1
print(f"removed {removed} false _launch markers")
trek.save_state(st)
'

# --- 4. delete the corrupt quant file (the acquire's magic check would
#        catch it too, but the file is garbage - no reason to keep it) ---
if test -f models/Qwen2.5-1.5B-Instruct/Qwen2.5-1.5B-Instruct-IQ3_XXS.gguf
    echo "==> deleting the corrupt IQ3_XXS file"
    rm models/Qwen2.5-1.5B-Instruct/Qwen2.5-1.5B-Instruct-IQ3_XXS.gguf
end

# --- 5. commit + push the cleanup ---
git add -A
and git commit -m "cleanup: the corrupt-file incident's false markers (post-rebase)"
and git push origin main

echo "==> done. git log --oneline -3 shows the cleanup commit on top."
