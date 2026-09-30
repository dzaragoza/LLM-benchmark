#!/usr/bin/env python3
"""Push commits to GitHub through the REST API.

The sandbox's direct git transport is proxy-blocked (403 CONNECT), but the
GitHub REST API works through the proxy with the sandbox CA and GITHUB_TOKEN.
This module encapsulates the proven Git Data API push recipe:

    GET  parent commit -> create blobs (base64) -> create tree (base_tree)
    -> create commit -> PATCH the ref

Usage:
    import git_push; git_push.push_files(files, message)
    or:  python3 git_push.py "commit message"   (commits ALL tracked+untracked changes)

Environment: GITHUB_TOKEN, SANDBOX_PROXY_GITHUB_PROXY, SANDBOX_PROXY_CA_CERT.
"""

from __future__ import annotations

import base64
import json
import os
import ssl
import sys
import urllib.request

REPO = "dzaragoza/LLM-benchmark"
BRANCH = "main"
API = "https://api.github.com"


class PushError(RuntimeError):
    pass


def _ca_path() -> str:
    path = "/tmp/proxy-ca.pem"
    if not os.path.exists(path):
        pem = os.environ.get("SANDBOX_PROXY_CA_CERT", "")
        if not pem:
            raise PushError(
                "no CA available: /tmp/proxy-ca.pem missing "
                "and SANDBOX_PROXY_CA_CERT unset"
            )
        with open(path, "w") as fh:
            fh.write(pem)
    return path


def _opener() -> urllib.request.OpenerDirector:
    proxy = os.environ.get("SANDBOX_PROXY_GITHUB_PROXY")
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"https": proxy, "http": proxy}))
    ctx = ssl.create_default_context(cafile=_ca_path())
    handlers.append(urllib.request.HTTPSHandler(context=ctx))
    return urllib.request.build_opener(*handlers)


def api_request(method: str, path: str, body: dict | None = None) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise PushError("GITHUB_TOKEN not set")
    url = f"{API}/repos/{REPO}/{path}" if path else f"{API}/repos/{REPO}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with _opener().open(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:500]
        raise PushError(f"{method} {path} -> HTTP {exc.code}: {detail}") from exc


def remote_head() -> str:
    ref = api_request("GET", f"git/ref/heads/{BRANCH}")
    return ref["object"]["sha"]


def head_is_ancestor_of_remote(local_sha: str) -> bool:
    try:
        remote = api_request("GET", f"commits/{local_sha}")
        return remote.get("sha") == local_sha
    except PushError:
        return False


def push_files(
    files: list[tuple[str, str | None]], message: str, parent_sha: str | None = None
) -> str:
    """files: list of (repo_path, local_path). To delete a file, use
    (repo_path, None). The parent is remote HEAD unless parent_sha is given.
    Returns the new commit SHA.
    """
    if parent_sha is None:
        parent_sha = remote_head()
    tree_items = []
    for repo_path, local_path in files:
        if local_path is None:
            tree_items.append({"path": repo_path, "mode": "100644", "type": "blob", "sha": None})
            continue
        with open(local_path, "rb") as fh:
            blob_body = {"content": base64.b64encode(fh.read()).decode(), "encoding": "base64"}
        blob = api_request("POST", "git/blobs", blob_body)
        tree_items.append({"path": repo_path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    tree = api_request("POST", "git/trees", {"base_tree": None, "tree": tree_items})
    commit = api_request(
        "POST",
        "git/commits",
        {"message": message, "tree": tree["sha"], "parents": [parent_sha]},
    )
    api_request("PATCH", f"git/refs/heads/{BRANCH}", {"sha": commit["sha"], "force": False})
    return commit["sha"]


def push_working_tree(message: str) -> str:
    """Collect every changed/untracked file (vs the local HEAD) and push it."""
    import subprocess

    def git(*args: str) -> str:
        out = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
        return out.stdout

    files: list[tuple[str, str | None]] = []
    for line in git("status", "--porcelain").splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"')
        if line[0] in "MDRAU" or line[1] in "MDRAU":
            files.append((path, path if os.path.exists(path) else None))
    if not files:
        raise PushError("nothing to push: working tree clean")
    return push_files(files, message)


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "update"
    sha = push_working_tree(msg)
    print(f"pushed -> {sha}")
    print(f"https://github.com/{REPO}/commit/{sha}")
