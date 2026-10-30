Tokens are very expensive, so focus on coding tasks only.
Do not create or run tests, they are expensive.
Commit directly to main and push, no PR or reviews needed.
Be concise. Tokens are expensive.
STATE-FILE PROTOCOL (the two-writer rule, adopted after the rebase collision of 2026-10-29):
- state/trek-state.json (and any state/*.json the runner writes) has TWO writers: the machine's auto-commit and this repo's agent.
- NEVER push changes to a state file while the benchmark may be running. Code and docs push freely; state changes are handed to the operator as a patch or a script (fish-native) the operator runs while the run is stopped.
- If a change MUST touch the state (a cleanup, a repair), write it as a script in the repo (like recover.fish), commit only the script, and let the operator execute it on the machine. The machine's own auto-commit then carries the state forward - one writer at a time, always the machine's.
- The rebase guard (infra/git_ops.in_rebase) stops the auto-commit from compounding a conflicted git; this rule removes the collision source itself.
For editing code use code_edit.py in AI_tools. Read its USAGE docstring first - it covers plain edits (replace/insert/delete/lines/region), markdown table sorting (sort_table), and structured JSON edits (edit_json).
Before writing any ad-hoc script (open/write, json surgery, table re-sorting), check whether code_edit.py already does it; if it does not, ADD the capability to code_edit.py and use it - never bypass the tool with raw file scripts.
Immediately fix any issue encountered in code_edit.py
DESIGN BY CONTRACT (the author's philosophy): development uses design by contract; ALL contract assertions are ERRORS - they raise, they never warn. A precondition/postcondition/invariant check that fails aborts the run (the crash rail catches it). Add contracts freely at points of truth; a violated contract is a bug in the code or the logic - never something to continue past. The preflight's assertions are contracts too: update them when the truth they assert changes.
Propose any needed improvements in code_edit.py and implement them immediately
Prepend all the commands you give me with git pull
All the shell commands should be for fish instead of bash
Do not run linters, formatters or tests.
