Tokens are very expensive, so focus on coding tasks only.
Do not create or run tests, they are expensive.
Commit directly to main and push, no PR or reviews needed.
Be concise. Tokens are expensive.
For editing code use code_edit.py in AI_tools. Read its USAGE docstring first - it covers plain edits (replace/insert/delete/lines/region), markdown table sorting (sort_table), and structured JSON edits (edit_json).
Before writing any ad-hoc script (open/write, json surgery, table re-sorting), check whether code_edit.py already does it; if it does not, ADD the capability to code_edit.py and use it - never bypass the tool with raw file scripts.
Immediately fix any issue encountered in code_edit.py
Propose any needed improvements in code_edit.py and implement them immediately
Prepend all the commands you give me with git pull
All the shell commands should be for fish instead of bash
Do not run linters, formatters or tests.
