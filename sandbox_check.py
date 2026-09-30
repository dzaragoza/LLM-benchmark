#!/usr/bin/env python3
"""Sandbox sanity check: run this at session start before any real work.

Checks, in order of how they have hurt us before:
  1. GitHub API reachability (distinguishes CA vs auth vs proxy failure)
  2. Tool availability + versions (git, python3, pytest, ruff, ty, gh, node)
  3. CA file presence (/tmp/proxy-ca.pem or SANDBOX_PROXY_CA_CERT)
  4. Remote HEAD of the repo (the only source of truth; local fetch is broken)
Exit code 0 = all critical checks pass; 1 = something needs fixing first.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

REPO = "dzaragoza/LLM-benchmark"
failures: list[str] = []
warnings: list[str] = []


def check(name: str, ok: bool, detail: str = "", critical: bool = True) -> None:
    line = f"  {'OK  ' if ok else 'FAIL'} {name}"
    if detail:
        line += f" ({detail})"
    print(line)
    if not ok:
        (failures if critical else warnings).append(f"{name}: {detail}")


print("== tools ==")
for tool, _min_ver in [
    ("git", "2"),
    ("python3", "3.10"),
    ("pytest", "7"),
    ("node", "18"),
    ("gh", "2"),
]:
    path = shutil.which(tool)
    if not path:
        check(tool, False, "not on PATH", critical=(tool in ("git", "python3")))
        continue
    try:
        out = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=15)
        ver = (out.stdout + out.stderr).split("\n")[0].strip()[:60]
        check(tool, out.returncode == 0, ver, critical=(tool in ("git", "python3")))
    except Exception as exc:  # noqa: BLE001 - report, do not crash the preflight
        check(tool, False, str(exc), critical=(tool in ("git", "python3")))

ruff = os.path.expanduser("~/.local/bin/ruff")
if os.path.exists(ruff):
    out = subprocess.run([ruff, "--version"], capture_output=True, text=True, timeout=15)
    check("ruff (~/.local/bin)", out.returncode == 0, out.stdout.strip()[:40])
else:
    check("ruff (~/.local/bin)", False, "missing (lint will be skipped)", critical=False)

ty = shutil.which("ty")
if ty:
    out = subprocess.run([ty, "--version"], capture_output=True, text=True, timeout=15)
    check("ty", out.returncode == 0, out.stdout.strip()[:40])
else:
    check("ty", False, "missing (typecheck will be skipped)", critical=False)

print("== CA / credentials ==")
ca = "/tmp/proxy-ca.pem"
if os.path.exists(ca):
    check("CA file /tmp/proxy-ca.pem", True, f"{os.path.getsize(ca)} bytes")
elif os.environ.get("SANDBOX_PROXY_CA_CERT"):
    check(
        "CA file /tmp/proxy-ca.pem",
        False,
        "missing but SANDBOX_PROXY_CA_CERT set - writable by git_push.py",
    )
else:
    check("CA file /tmp/proxy-ca.pem", False, "missing and no env fallback", critical=False)

for var in ("GITHUB_TOKEN", "SANDBOX_PROXY_GITHUB_PROXY"):
    check(f"env {var}", bool(os.environ.get(var)), "set" if os.environ.get(var) else "unset")

print("== GitHub API (the push path) ==")
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import git_push

    try:
        sha = git_push.remote_head()
        check("API reachability", True)
        check("remote HEAD fetch", True, f"main @ {sha[:10]}")
    except git_push.PushError as exc:
        msg = str(exc)
        if "401" in msg or "token" in msg.lower():
            check("API reachability", False, f"AUTH failure: {msg}")
        elif " CERT" in msg or "SSL" in msg or "certificate" in msg.lower():
            check("API reachability", False, f"CA failure: {msg}")
        elif "proxy" in msg.lower() or "tunnel" in msg.lower():
            check("API reachability", False, f"PROXY failure: {msg}")
        else:
            check("API reachability", False, msg)
except Exception as exc:  # noqa: BLE001 - report, do not crash the preflight
    check("git_push import", False, str(exc), critical=False)

print("== local repo ==")
try:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=15, check=True
    )
    print(f"  OK   local HEAD {out.stdout.strip()[:10]}")
except subprocess.CalledProcessError as exc:
    check("local git repo", False, str(exc))

print()
if warnings:
    for w in warnings:
        print(f"note: {w}")
if failures:
    print(f"SANITY CHECK: {len(failures)} failure(s) - fix before working:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("SANITY CHECK: all critical checks pass")
