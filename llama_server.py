#!/usr/bin/env python3
"""llama_server.py -- the llama-server interface (bottom layer).

Every script that needs a running llama-server goes through this
module; none of them launches or kills the server process itself:

  - speed_gate.py   the worst-turn speed gate (live conversations)
  - arc_eval.py     the strict ARC-Challenge evaluation

It owns: binary resolution (repo-relative first, pre-reorg HOME
fallback, llama-server.exe on Windows), server launch with a custom
argument vector, health polling, HTTP helpers, and the hardened
teardown - a lingering server silently redirects the next run at the
WRONG model, so the port is verified free before returning (Session
13's zombie lesson, applied repo-wide). Not a CLI - the phase scripts
import it.

Merged in from the former live-bench.py (its server-management half)
when live-bench was absorbed into speed_gate.py.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request


def find_server():
    """llama-server binary: repo-relative first, pre-reorg HOME fallback.
    Windows builds ship llama-server.exe - pick the right name."""
    home = os.path.expanduser("~")
    exe = "llama-server.exe" if os.name == "nt" else "llama-server"
    for d in (os.path.join(".", "llama-b10964-gpu"),
              os.path.join(home, "technical_reports", "llama-b10964-gpu")):
        p = os.path.join(d, exe)
        if os.path.isfile(p):
            return p
    return os.path.join(".", "llama-b10964-gpu", exe)


def wait_healthy(port, timeout=300, proc=None):
    """Poll /health until 200. Returns True on healthy; if proc dies,
    or the timeout passes, returns False."""
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except OSError:
            pass
        if proc is not None and proc.poll() is not None:
            return False
        time.sleep(0.5)
    return False


def start_server(model_path, port, extra_args=None, server_bin=None,
                 health_timeout=1800):
    """Launch llama-server on a model. Returns (proc, healthy_bool)."""
    cmd = [server_bin or find_server(), "-m", model_path,
           "--port", str(port)]
    if extra_args:
        cmd += list(extra_args)
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    healthy = wait_healthy(port, health_timeout, proc)
    return proc, healthy


def stop_server(proc, port, warn_after=60):
    """Kill the server and verify the port is free (a lingering server
    silently redirects the next run at the WRONG model)."""
    if proc.poll() is None:
        proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            # Windows: kill the whole tree (children may hold the port).
            subprocess.run(["taskkill", "/PID", str(proc.pid),
                            "/T", "/F"], capture_output=True)
        else:
            proc.kill()
    deadline = time.time() + warn_after
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/health", timeout=2):
                pass
        except OSError:
            return True
        time.sleep(2)
    print(f"    WARNING: port {port} still busy after {warn_after}s - "
          "results may be invalid!", file=sys.stderr)
    return False


def post_json(port, endpoint, payload, timeout=1800):
    """POST JSON to the server and return the decoded response.
    Supports both chat (/v1/chat/completions) and completion
    (/v1/completions) endpoints - the two request shapes the study
    makes."""
    url = f"http://127.0.0.1:{port}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def tokenize(port, content, timeout=300):
    """POST /tokenize: the server's own token count for a text.
    The depth-prefill gate budgets its blob with this (exact per
    model - tokenizers differ), and the words-per-token protocol
    rides it too."""
    data = post_json(port, "/tokenize", {"content": content}, timeout)
    toks = data.get("tokens")
    if toks is None:
        raise ValueError("no tokens field in /tokenize response")
    return toks


def trim_to_tokens(port, text, target, tolerance=8, max_iter=24):
    """Trim text down to a token budget: returns (text, n_tokens)
    with n_tokens <= target, within tolerance when possible.
    Converges by bisection on character count (tokenizers are
    near-linear in chars). Never returns over budget - the depth
    arithmetic depends on that."""
    n = len(tokenize(port, text))
    if n <= target:
        return text, n
    lo, hi = 0, len(text)
    best = None
    for _ in range(max_iter):
        mid = (lo + hi) // 2
        cand = text[:mid]
        n = len(tokenize(port, cand))
        if n > target:
            hi = mid
        else:
            if target - n <= tolerance:
                return cand, n
            if best is None or n > best[1]:
                best = (cand, n)
            lo = mid + 1
        if hi - lo <= 1:
            break
    if best is None:
        raise ValueError(f"cannot trim text under {target} tokens")
    return best


def stream_completion(port, payload, timeout=1800):
    """POST a streaming /v1/chat/completions request and yield content
    deltas as they arrive, with per-delta wall arrival times (the
    felt-experience view the non-streaming gate cannot see: TTFT and
    the inter-token gap distribution). Yields (delta_text, t_arrival)
    pairs; the caller assembles the full answer and its timing."""
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    data = json.dumps({**payload, "stream": True}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        buf = b""
        for chunk in resp:
            buf += chunk
            while b"\n\n" in buf:
                raw, buf = buf.split(b"\n\n", 1)
                for line in raw.decode("utf-8", "replace").splitlines():
                    if not line.startswith("data: "):
                        continue
                    body = line[len("data: "):].strip()
                    if body == "":
                        return
                    try:
                        obj = json.loads(body)
                    except ValueError:
                        continue
                    choice = (obj.get("choices") or [{}])[0]
                    delta = choice.get("delta") or {}
                    text = delta.get("content")
                    if text:
                        yield text, time.time()
