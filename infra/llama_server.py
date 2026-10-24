#!/usr/bin/env python3
"""llama_server.py -- the llama-server interface (bottom layer).

Every script that needs a running llama-server goes through this
module; none of them launches or kills the server process itself:

  - speed_gate.py   the worst-turn speed gate (live conversations)
  - ruler_gate.py   the RULER depth tasks (fwe - the depth score)

It owns: binary resolution (repo-relative,
llama-server.exe on Windows), server launch with a custom
argument vector, health polling, HTTP helpers, and the hardened
teardown - a lingering server silently redirects the next run at the
WRONG model, so the port is verified free before returning (Session
13's zombie lesson, applied repo-wide). Not a CLI - the phase scripts
import it.

Merged in from the former live-bench.py (its server-management half)
when live-bench was absorbed into speed_gate.py.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any

# session 38, addendum 5: llama's own memory accounting must land in the
# server log (the sole per-process memory witness - session 38, addendum
# 11 retired the smaps census; addendum 23 deletes the machinery).
# v9.4: level 5 (the per-token debug stream - 100MB+ per run) is RETIRED.
# Measured on the pinned build (the author's lv0..5 sweep): the memory
# breakdown table - the only thing the benchmark reads - first appears
# at level 4 (16KB per launch; level 5 was 440KB).
# Single-sourced HERE - every launch site gets it,
# no triplicated flags to drift apart.
LOG_VERBOSITY_ARGS = ["-lv", "4"]


def kill_stale_server() -> bool:
    """Session 34 (addendum 19, refinement 1): pkill any llama-server
    holding a port or RAM - the sweep's own launches replace whatever
    was there. Session 40 (addendum 5): moved here from bench/cells.py
    - process control of llama-server is bottom-layer contact, and the
    middle layer does not shell out directly. Returns True when
    something was killed."""
    r = subprocess.run(
        ["pkill", "-f", "llama-server"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return r.returncode == 0


def find_server() -> str | None:
    """llama-server binary: repo-relative only. None when absent -
    the caller (check_tooling) fails loudly with install guidance.
    Windows builds ship llama-server.exe - pick the right name."""
    exe = "llama-server.exe" if os.name == "nt" else "llama-server"
    p = os.path.join(".", "llama-b11669", exe)
    return p if os.path.isfile(p) else None


def wait_healthy(port: int, timeout: float = 300, proc: Any = None) -> bool:
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


def start_server(
    model_path: str,
    port: int,
    extra_args: list[str] | None = None,
    server_bin: str | None = None,
    health_timeout: float = 1800,
    log_path: str | None = None,
) -> tuple[Any, bool]:
    """Launch llama-server on a model. Returns (proc, healthy_bool).
    log_path (addendum 36): capture the server's stdout/stderr instead
    of discarding them - llama.cpp's startup banner carries its own
    memory accounting (model size, KV cache, compute buffers), which
    the memory report parses. The log is truncated per launch (the
    last launch's banner is the reported one)."""
    server = server_bin or find_server()
    assert server is not None  # the caller (check_tooling) verified the binary exists
    cmd = [server, "-m", model_path, "--port", str(port)] + list(LOG_VERBOSITY_ARGS)
    if extra_args:
        cmd += list(extra_args)
    if log_path:
        log_fh = open(log_path, "wb")
        try:
            proc = subprocess.Popen(cmd, stdout=log_fh, stderr=subprocess.STDOUT)
        finally:
            log_fh.close()
    else:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    healthy = wait_healthy(port, health_timeout, proc)
    return proc, healthy


def memory_breakdown_gib(log_path: str) -> dict[str, Any] | None:
    """llama.cpp's own memory accounting from the -lv 5 server log
    (session 39, addendum 11 - the smaps census retired: it can't see
    the UMA carveout, so it undercounted offload by 3-8x - addendum 23
    deletes the machinery outright). Parses the
    `memory breakdown [MiB]` table rows:
      | - Vulkan0 (780M ...) | 16383 = 15181 + (1140 = 1013 + 71 + 55) + 61 |
      | - Host               |   317 =   306 +   0 + 11                  |
    into per-device model/context/compute and the totals the GPU table
    wants. Sums ALL model-buffer-size lines (the first occurrence in
    hybrid builds is a 0.00 placeholder before the real split)."""
    devices: dict[str, dict[str, float]] = {}
    weights_mib = 0.0
    try:
        with open(log_path, errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return None
    for ln in lines:
        m = re.search(r"model buffer size\s*=\s*([0-9.]+)\s*MiB", ln)
        if m:
            weights_mib += float(m.group(1))
    for ln in lines:
        m = MEMORY_BREAKDOWN_ROW.search(ln) or MEMORY_BREAKDOWN_ROW_FLAT.search(ln)
        if not m:
            continue
        dev = m.group(1).split("(")[0].strip()
        model, context, compute = (int(m.group(i)) for i in (3, 4, 5))
        row = {
            "self_gib": round(int(m.group(2)) / 1024, 3),
            "model_gib": round(model / 1024, 3),
            "context_gib": round(context / 1024, 3),
            "compute_gib": round(compute / 1024, 3),
        }
        if dev not in devices:
            devices[dev] = row
    if not devices and weights_mib == 0.0:
        return None
    model_gib = round(sum(d["model_gib"] for d in devices.values()), 3)
    context_gib = round(sum(d["context_gib"] for d in devices.values()), 3)
    compute_gib = round(sum(d["compute_gib"] for d in devices.values()), 3)
    return {
        "source": "llama-server (memory breakdown)",
        "weights_gib": round(max(weights_mib, model_gib * 1024) / 1024, 3),
        "model_gib": model_gib,
        "context_gib": context_gib,
        "compute_gib": compute_gib,
        "total_gib": round(model_gib + context_gib + compute_gib, 3),
        "devices": devices,
    }


def stop_server(proc: Any, port: int, warn_after: float = 60) -> bool:
    """Kill the server and verify the port is free (a lingering server
    silently redirects the next run at the WRONG model)."""
    if proc.poll() is None:
        proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            # Windows: kill the whole tree (children may hold the port).
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        else:
            proc.kill()
    deadline = time.time() + warn_after
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2):
                pass
        except OSError:
            return True
        time.sleep(2)
    print(
        f"    WARNING: port {port} still busy after {warn_after}s - results may be invalid!",
        file=sys.stderr,
    )
    return False


def post_json(port: int, endpoint: str, payload: dict[str, Any], timeout: float = 1800) -> Any:
    """POST JSON to the server and return the decoded response.
    Supports both chat (/v1/chat/completions) and completion
    (/v1/completions) endpoints - the two request shapes the study
    makes."""
    url = f"http://127.0.0.1:{port}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def tokenize(port: int, content: str, timeout: float = 300) -> list[Any]:
    """POST /tokenize: the server's own token count for a text.
    The depth-prefill gate budgets its blob with this (exact per
    model - tokenizers differ), and the words-per-token protocol
    rides it too."""
    data = post_json(port, "/tokenize", {"content": content}, timeout)
    toks = data.get("tokens")
    if toks is None:
        raise ValueError("no tokens field in /tokenize response")
    return toks


