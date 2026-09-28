# tests/ — the study tooling's regression suite (addendum 87)
#
# Scope: the pure logic and contracts the study depends on — the
# registered-constants arithmetic, the state-file contract (including
# the addendum-79 dry-run guard), the addendum-83 plan classifier,
# and the addendum-86 ARC-jobs filter. No network, no models, no GPU:
# the whole suite runs in seconds, so it can run before any sweep.
#
# Run:  python3 -m pytest tests/ -q
