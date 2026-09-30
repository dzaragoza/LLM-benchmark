#!/usr/bin/env python3
"""llama_server.py -- the llama-server interface (bottom layer).

Every script that needs a running llama-server goes through this
module; none of them launches or kills the server process itself:

  - speed_gate.py   the worst-turn speed gate (live conversations)
  - ruler_gate.py   the RULER depth tasks (fwe - the depth score)

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

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from typing import Any


def find_server() -> str | None:
    """llama-server binary: repo-relative first, pre-reorg HOME fallback.
    Windows builds ship llama-server.exe - pick the right name."""
    home = os.path.expanduser("~")
    exe = "llama-server.exe" if os.name == "nt" else "llama-server"
    for d in (
        os.path.join(".", "llama-b10964-gpu"),
        os.path.join(home, "technical_reports", "llama-b10964-gpu"),
    ):
        p = os.path.join(d, exe)
        if os.path.isfile(p):
            return p
    return os.path.join(".", "llama-b10964-gpu", exe)


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
    cmd = [server, "-m", model_path, "--port", str(port)]
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


def peak_rss_gib(proc: Any) -> float | None:
    """Peak resident set size (VmHWM) of the server process, in GiB.
    DIAGNOSTIC ONLY (session 34, addendum 23): llama.cpp mmaps the
    weights, and mmap'd file-backed pages are shared with the page
    cache - the kernel may evict and re-fault them during the run, so
    the per-process peak UNDERCOUNTS the whole stack at deep ctx
    (registered pattern: peak RSS 0.27 GiB < a 0.63 GiB file). The
    authoritative number is mapped_memory_gib(). Linux only
    (/proc); returns None elsewhere or after the process is gone.
    MUST be called before stop_server terminates the process."""
    try:
        with open(f"/proc/{proc.pid}/status") as f:
            for line in f:
                if line.startswith("VmHWM:"):
                    return int(line.split()[1]) / (1024 * 1024)
    except Exception:
        return None
    return None


def mapped_memory_gib(proc: Any) -> dict[str, float | None] | None:
    """The server's mapped-memory census from /proc/<pid>/smaps
    (session 34, addendum 23 - the VmHWM undercount fix).

    Sums the VMA size of every mapping and the RSS (pages actually
    resident) split by backing:
      mapped_gib    total address-space mapped (the launch's claim)
      resident_gib  pages resident RIGHT NOW (sum of VMA Rss)
      file_gib      resident pages of file-backed VMAs (the weights,
                    via mmap - immune to the VmHWM peak-eviction quirk:
                    a resident page counts, whether or not the peak
                    caught it)
      anon_gib      resident pages of anonymous VMAs (KV cache,
                    compute buffers, runtime heap)
    resident_gib is the honest "can it run here" number: the pages
    the machine must actually hold with the model in use, counted
    from the memory map rather than a single high-water mark. Best
    read LATE in the run (deep turns faulted the whole blob in);
    MUST be called before stop_server terminates the process.
    Linux-exclusive (/proc/<pid>/smaps with per-VMA Rss, kernel 2.6.32+):
    returns None elsewhere or after the process is gone."""
    pid = getattr(proc, "pid", None)
    if pid is None:
        return None
    mapped = 0.0
    file_rss = 0.0
    anon_rss = 0.0
    cur_file = False
    try:
        with open(f"/proc/{pid}/smaps", errors="replace") as f:
            for line in f:
                first = line.split()[0] if line.strip() else ""
                if (
                    len(first) >= 3
                    and first[0] in "0123456789abcdef"
                    and "-" in first
                    and ":" not in first
                ):
                    # VMA header: "addr-addr perms offset dev inode [path]" -
                    # exactly 5 fields before the optional path; a path
                    # (6+ fields) means file-backed, "[vso]"-style or none
                    # means anonymous
                    cur_file = len(line.split()) >= 6
                    continue
                key, _, val = line.partition(":")
                val = val.strip()
                if key == "Size":
                    mapped += int(val.split()[0])
                elif key == "Rss":
                    kb = int(val.split()[0])
                    if cur_file:
                        file_rss += kb
                    else:
                        anon_rss += kb
    except Exception:
        return None
    gib = 1 / (1024 * 1024)
    resident = file_rss + anon_rss
    return {
        "mapped_gib": mapped * gib,
        "resident_gib": resident * gib,
        "file_gib": file_rss * gib,
        "anon_gib": anon_rss * gib,
    }


def system_memavailable_gib() -> float | None:
    """System-wide MemAvailable in GiB (Linux /proc/meminfo). The
    before/after difference across a server launch is the launch's
    cost to the MACHINE - immune to the accounting quirks that make
    per-process VmHWM undercount (mmap'd weights shared with page
    cache, wrapper scripts, child processes)."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / (1024 * 1024)
    except Exception:
        pass
    return None


def memory_cost_gib(before: float | None, after: float | None) -> float | None:
    """The launch's memory cost from two system_memavailable_gib()
    readings: before minus after. Positive = the launch consumed
    MemAvailable. Guarded against interference (other processes
    grabbing memory during the run read as a LARGER cost - the
    honest direction for a 'can it run here' number)."""
    if before is None or after is None:
        return None
    return before - after


def drop_file_cache(path: str) -> bool:
    """Evict the file's clean pages from the page cache (addendum 137m):
    os.posix_fadvise POSIX_FADV_DONTNEED on the whole file. This makes
    the next launch's MemAvailable delta an honest cold-cache machine
    cost - the mmap'd weights pages must be faulted in again, so the
    delta prices the whole stack (weights + KV + buffers), not the
    warm-cache marginal cost the ladder's back-to-back relaunches
    would otherwise read (the 137k artifact). No root needed (unlike
    /proc/sys/vm/drop_caches); returns True if the fadvise call
    succeeded, False if unavailable (costs stay caveated).
    """
    fd = None
    try:
        import ctypes

        libc = ctypes.CDLL(None, use_errno=True)
        fd = os.open(path, os.O_RDONLY)
        rc = libc.posix_fadvise(fd, 0, 0, 4)  # POSIX_FADV_DONTNEED = 4 on Linux
        return rc == 0
    except Exception:
        return False
    finally:
        if fd is not None:
            os.close(fd)


def parse_memory_log(log_path: str) -> dict[str, Any] | None:
    """Best-effort parse of llama.cpp's own memory accounting from the
    captured server log (addendum 36). The banner format moves between
    builds, so this extracts structured keys where the wording is
    recognizable AND keeps the raw memory-bearing lines verbatim;
    the peak RSS (VmHWM) remains the authoritative total. Returns a
    dict: {keys...: GiB, 'banner_lines': [raw lines with sizes]}."""
    out = {"banner_lines": []}
    pat = re.compile(
        r"([A-Za-z_0-9 .]*?)[:=]\s*([0-9]+(?:\.[0-9]+)?)"
        r"\s*(KiB|MiB|GiB)"
    )
    to_gib = {"KiB": 1 / (1024 * 1024), "MiB": 1 / 1024, "GiB": 1.0}
    try:
        with open(log_path, errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return out
    for ln in lines:
        low = ln.lower()
        if "mib" not in low and "gib" not in low and "kib" not in low:
            continue
        out["banner_lines"].append(ln.rstrip())
        for label, val, unit in pat.findall(ln):
            key = label.strip().lower().rstrip(" :=")
            gib = float(val) * to_gib[unit]
            if "kv" in key and "kv_cache_gib" not in out:
                out["kv_cache_gib"] = round(gib, 3)
            elif "cpu" in key and "cpu_buffers_gib" not in out:
                out["cpu_buffers_gib"] = round(gib, 3)
            elif "graph" in key and "graph_overhead_gib" not in out:
                out["graph_overhead_gib"] = round(gib, 3)
    out["banner_lines"] = out["banner_lines"][-40:]
    return out


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


def trim_to_tokens(
    port: int, text: str, target: int, tolerance: int = 8, max_iter: int = 24
) -> tuple[str, int]:
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


def stream_completion(
    port: int,
    payload: dict[str, Any],
    timeout: float = 1800,
    meta: dict[str, Any] | None = None,
) -> Any:
    """POST a streaming /v1/chat/completions request and yield content
    deltas as they arrive, with per-delta wall arrival times (the
    felt-experience view the non-streaming gate cannot see: TTFT and
    the inter-token gap distribution). Yields (delta_text, t_arrival)
    pairs; the caller assembles the full answer and its timing.
    meta (protocol v3.0): an optional dict the caller passes in; the
    server's final-chunk "timings"/"usage" objects are written into
    it before the generator ends, so a streaming caller keeps the
    law's server-side t/s and the exact token counts."""
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    data = json.dumps({**payload, "stream": True}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        buf = b""
        for chunk in resp:
            buf += chunk
            while b"\n\n" in buf:
                raw, buf = buf.split(b"\n\n", 1)
                for line in raw.decode("utf-8", "replace").splitlines():
                    if not line.startswith("data: "):
                        continue
                    body = line[len("data: ") :].strip()
                    if body == "":
                        return
                    try:
                        obj = json.loads(body)
                    except ValueError:
                        continue
                    if meta is not None:
                        if obj.get("timings"):
                            meta["timings"] = obj["timings"]
                        if obj.get("usage"):
                            meta["usage"] = obj["usage"]
                    choice = (obj.get("choices") or [{}])[0]
                    delta = choice.get("delta") or {}
                    text = delta.get("content")
                    rtext = delta.get("reasoning_content")
                    if meta is not None and rtext:
                        meta["reasoning"] = meta.get("reasoning", "") + rtext
                    if text:
                        yield text, time.time()
