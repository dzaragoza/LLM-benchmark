"""bench.contracts -- design-by-contract, warning-only.

A cheap way to raise code quality (the author's ruling): the
preconditions, postconditions and invariants ride the code as
EXPLICIT checks - but they WARN, never raise. A violated contract
in a multi-hour experiment is a triage question (a bug in our
code, or a wrong assumption in our logic?), not a reason to kill
the run: the warning is loud, tagged and greppable, and the
decision is ours.

The tags, stable for grepping:
  [contract:pre:NAME]    a precondition - what the caller must
                         guarantee at entry
  [contract:post:NAME]   a postcondition - what the function
                         promises at exit
  [contract:inv:NAME]     an invariant - what must hold throughout
                         (re-checked at every loop boundary)

Every violation is counted (CONTRACT_VIOLATIONS), so the crash
rail and the status can report the session's contract health.
"""

from __future__ import annotations

import sys
from typing import Any

# the session's violation count, by tag
CONTRACT_VIOLATIONS: dict[str, int] = {}


def warn_contract(kind: str, name: str, ok: bool, detail: str = "") -> bool:
    """Evaluate one contract: WARN on violation, never raise.
    Returns ok (the caller may branch on it, but must not have to)."""
    if ok:
        return True
    tag = f"[contract:{kind}:{name}]"
    CONTRACT_VIOLATIONS[tag] = CONTRACT_VIOLATIONS.get(tag, 0) + 1
    n = CONTRACT_VIOLATIONS[tag]
    print(
        f"{tag} VIOLATED ({n}x): {detail or 'condition failed'}",
        file=sys.stderr,
        flush=True,
    )
    return False


def contract_health() -> dict[str, int]:
    """the session's contract violation counts, for the status and
    the crash rail."""
    return dict(CONTRACT_VIOLATIONS)
