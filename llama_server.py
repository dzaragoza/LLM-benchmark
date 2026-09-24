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
