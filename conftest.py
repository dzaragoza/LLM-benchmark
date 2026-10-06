"""pytest path setup: the AI session tools (code_edit, code_search) live in
AI_tools/, not the repo root (session 41, addendum 38 ruling 3)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "AI_tools"))
