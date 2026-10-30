"""bench.contracts -- design-by-contract, ERRORS.

The author's philosophy (the correction of the earlier warning-only
ruling): preconditions, postconditions and invariants ride the
code as EXPLICIT checks, and every violation RAISES - a broken
contract is an error, never a warning. The reasoning: a violated
contract means a bug in our code or a wrong assumption in our
logic; continuing past it produces wrong results SILENTLY, which
is strictly worse than a loud abort (the same ruling as the
schema gate: a wrong result silently produced is worse than a
loud failure). The crash rail catches the raise, commits the
artifacts, and stamps the traceback - the triage pattern.

The tags, stable for grepping (in the exception and the log):
  [contract:pre:NAME]    a precondition - what the caller must
                         guarantee at entry
  [contract:post:NAME]   a postcondition - what the function
                         promises at exit
  [contract:inv:NAME]     an invariant - what must hold throughout
                         (re-checked at every loop boundary)

Violations are also counted (CONTRACT_VIOLATIONS) before the
raise, so a partial session's contract health is inspectable.
"""

from __future__ import annotations

import sys

# the session's violation count, by tag
CONTRACT_VIOLATIONS: dict[str, int] = {}


class ContractViolationError(AssertionError):
    """a violated contract: an error (the author's philosophy) -
    carries the greppable tag and the detail."""


def warn_contract(kind: str, name: str, ok: bool, detail: str = "") -> bool:
    """Evaluate one contract: RAISE on violation (ContractViolationError).
    The name stays warn_contract for the call sites' stability. Returns
    True when ok (the caller may branch, but must not have to)."""
    if ok:
        return True
    tag = f"[contract:{kind}:{name}]"
    CONTRACT_VIOLATIONS[tag] = CONTRACT_VIOLATIONS.get(tag, 0) + 1
    raise ContractViolationError(f"{tag} VIOLATED: {detail or 'condition failed'}")


def contract_health() -> dict[str, int]:
    """the session's contract violation counts, for the status and
    the crash rail."""
    return dict(CONTRACT_VIOLATIONS)
