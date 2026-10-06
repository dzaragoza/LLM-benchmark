"""git_ops.py -- the git interface (bottom layer).

Everything that shells out to the git binary lives here (session 40,
addendum 5: the three-layer audit found the orchestrator running git
via subprocess directly - a top-layer bypass of the bottom
interfaces). Import only.

Distinct from git_push.py, which is the sandbox's REST-API push
workaround (the direct git transport is proxy-blocked there); this
module is the plain-git seam for the orchestrator on the bench
machine.
"""

from __future__ import annotations

import subprocess


def _run(args: list[str], text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=text)


def inside_work_tree() -> bool:
    """True when the CWD is a git work tree."""
    r = _run(["git", "rev-parse", "--is-inside-work-tree"])
    return r.returncode == 0 and r.stdout.strip() == "true"


def pull_rebase(autostash: bool = True, no_verify: bool = False) -> tuple[int, str, str]:
    """git pull --rebase (autostash optional). Returns (rc, stdout, stderr)."""
    args = ["git", "pull", "--rebase"]
    if autostash:
        args.append("--autostash")
    if no_verify:
        args.append("--no-verify")
    r = _run(args)
    return r.returncode, r.stdout, r.stderr


def add(paths: list[str], force: bool = True) -> tuple[int, str]:
    """git add (force passes -f past ignores). Returns (rc, stderr)."""
    args = ["git", "add"] + (["-f"] if force else []) + ["--"] + paths
    r = _run(args)
    return r.returncode, r.stderr


def staged_changes_exist() -> bool:
    """True when the index differs from HEAD (rc 1 from diff --quiet)."""
    return _run(["git", "diff", "--cached", "--quiet"]).returncode != 0


def commit(message: str) -> tuple[int, str]:
    """git commit -m. Returns (rc, stdout)."""
    r = _run(["git", "commit", "-m", message])
    return r.returncode, r.stdout


def push() -> tuple[int, str]:
    """git push. Returns (rc, stderr)."""
    r = _run(["git", "push"])
    return r.returncode, r.stderr
