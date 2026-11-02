#!/usr/bin/env python3
"""serve_candidate.py -- serve ONE candidate exactly as the exhaustive
benchmark would: download the model, build the rung's quant, launch
llama-server on port 9000 with the benchmark's parameters and the
command line's k/v cache quants.

Usage:
    python serve_candidate.py "granite-4.0-350m Q6_K k=f16 v=iq4_nl"

The string is "<model> <rung> k=<k-quant> v=<v-quant>". Ctrl-C stops
the server cleanly. The quant file stays in models/ (no file rule
here - this is a manual session, the gc owns cleanup).
"""

from __future__ import annotations

import argparse
import os
import re
import signal
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import infra.llama_server as llama_server
import trek_run as R
from bench.exam import bell_window
from bench.roster import roster_from_models_md

PORT_DEFAULT = 9000

_SPEC_RE = re.compile(
    r"^(?P<fam>\S+)\s+(?P<rung>\S+)\s+k=(?P<k>\S+)\s+v=(?P<v>\S+)\s*$"
)


def parse_spec(spec: str) -> tuple[str, str, str, str]:
    m = _SPEC_RE.match(spec.strip())
    if not m:
        raise SystemExit(
            f"cannot parse {spec!r} - expected: \"<model> <rung> k=<k> v=<v>\" "
            'e.g. "granite-4.0-350m Q6_K k=f16 v=iq4_nl"'
        )
    return m.group("fam"), m.group("rung"), m.group("k"), m.group("v")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="serve one benchmark candidate on port 9000: "
        '"<model> <rung> k=<k-quant> v=<v-quant>"'
    )
    ap.add_argument("spec", help='e.g. "granite-4.0-350m Q6_K k=f16 v=iq4_nl"')
    ap.add_argument("--models-dir", default="models")
    ap.add_argument("--port", type=int, default=PORT_DEFAULT)
    args = ap.parse_args()

    fam, rung, k_quant, v_quant = parse_spec(args.spec)
    repos = dict(roster_from_models_md())
    if fam not in repos:
        raise SystemExit(f"{fam!r} is not in md/models.md's roster")
    print(f"[serve] {fam} {rung} k={k_quant} v={v_quant} on port {args.port}")

    llama_server.kill_stale_server()
    gguf = R._acquire(fam, rung, args.models_dir)
    if not gguf:
        raise SystemExit(
            f"acquire failed: {R._last_acquire_error.get('result', 'unknown')} "
            f"- {R._last_acquire_error.get('detail', '')}"
        )
    print(f"[serve] the model file: {gguf}")

    ctx = bell_window({}, fam, args.models_dir) or 262144
    print(f"[serve] the training window (the paper): {ctx}")

    kv_args: list[str] = []
    if k_quant != "f16":
        kv_args += ["--cache-type-k", k_quant]
    if v_quant != "f16":
        kv_args += ["--cache-type-v", v_quant]
    log_path = os.path.join(args.models_dir, fam, f"serve-{rung}-k{k_quant}-v{v_quant}.log")
    proc, healthy = llama_server.start_server(
        gguf,
        port=args.port,
        extra_args=[
            "--n-gpu-layers",
            "999",
            "--parallel",
            "1",
            "--reasoning",
            "off",
            "--reasoning-budget",
            "0",
        ]
        + kv_args,
        log_path=log_path,
    )
    if not healthy or not llama_server.wait_healthy(args.port, proc=proc):
        llama_server.stop_server(proc, args.port)
        raise SystemExit(f"the server did not become healthy - see {log_path}")
    print(f"[serve] healthy at http://127.0.0.1:{args.port} (log: {log_path})")
    print("[serve] Ctrl-C to stop")

    def _stop(_signum: object, _frame: object) -> None:
        llama_server.stop_server(proc, args.port)
        print("[serve] stopped")
        sys.stdout.flush()
        os._exit(130)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    proc.wait()


if __name__ == "__main__":
    main()
