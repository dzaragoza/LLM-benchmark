"""depth_gen -- the missing term-2 instrument (addendum 237).

llama-bench cannot measure generation at depth: its tg test generates
off a FIXED small prompt (-p sizes only the pp test; the author's run
showed tg128 = 34.52 +/- 0.00 t/s at every -p). The depth-scaled
generation term of the speed picture (addendum 220) therefore has no
off-the-shelf measurement - this script is it.

THE INSTRUMENT: one llama-server, /completion (NOT /v1/chat), with
prompt_n tokens of filler and n_predict tokens of generation. The
server's own timings block is the read:
  prompt_eval  (s)  -> prefill seconds at depth (the pp curve, again)
  eval         (s)  -> generation seconds for n_predict tokens
  t/s at depth = n_predict / eval
Both terms of the speed picture fall out of the SAME request, measured
by the server itself - no client stopwatch, no drift.

THE SWEEP: the addendum-226 depths (4k, 16k, 32k, 64k, 131k) x a few
generation lengths, one server launch per model config. The filler is
ruler_gate.VT_HAYSTACK sentences - the same text the benchmark corpus
uses, so the depth profile matches the benchmark's own traffic.

Usage (fish):
  python3 depth_gen.py --gguf models/FAM/FAM-Q8_0.gguf --ctx 131072
  python3 depth_gen.py --gguf ... --ctx 131072 --kv q4_0   # KV-quant arm
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import infra.llama_server as llama_server
import ruler_gate

DEPTHS = [4096, 16384, 32768, 65536, 131072]
GEN_TOKENS = [64, 128, 256]
PORT = 8290


def build_filler(port: int, depth_tokens: int) -> str:
    """VT_HAYSTACK sentences trimmed by /tokenize accounting to the depth
    budget (session 37, addendum 25 discipline: never exceed ctx)."""
    sent = ruler_gate.VT_HAYSTACK
    probe = len(llama_server.tokenize(port, sent))
    per_sent = max(1.0, probe)
    n = int(depth_tokens / per_sent)
    return " ".join([sent] * n)


def main() -> None:
    ap = argparse.ArgumentParser(description="generation-at-depth probe (addendum 237)")
    ap.add_argument("--gguf", required=True)
    ap.add_argument("--ctx", type=int, default=131072)
    ap.add_argument("--kv", default="f16", help="cache-type-k/v value (f16, q8_0, q4_0)")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--ngl", default="99")
    ap.add_argument(
        "--out", default=None, help="output json path (default state/depth-gen-<label>.json)"
    )
    args = ap.parse_args()

    extra = ["-c", str(args.ctx), "--parallel", "1", "-ngl", str(args.ngl)]
    if args.kv != "f16":
        extra += ["-fa", "on", "--cache-type-k", args.kv, "--cache-type-v", args.kv]

    label = os.path.basename(args.gguf).replace(".gguf", "") + f"-kv{args.kv}-ctx{args.ctx}"
    out_path = args.out or f"state/depth-gen-{label}.json"

    print(f"=== depth-gen: {args.gguf} kv={args.kv} ctx={args.ctx} ===")
    proc, healthy = llama_server.start_server(
        args.gguf,
        port=args.port,
        extra_args=extra,
        log_path=f"models/depth-gen-{label}-server.log",
    )
    rows = []
    try:
        if not healthy or not llama_server.wait_healthy(args.port, proc=proc):
            print("ERROR: server did not come up")
            return
        for depth in DEPTHS:
            if depth > args.ctx:
                continue
            filler = build_filler(args.port, depth)
            for n_gen in GEN_TOKENS:
                payload = {
                    "prompt": filler,
                    "n_predict": n_gen,
                    "temperature": 0,
                    "stream": False,
                    "cache_prompt": False,
                }
                data = llama_server.post_json(args.port, "/completion", payload)
                t = data.get("timings") or {}
                prompt_n = t.get("prompt_n")
                p_eval = t.get("prompt_eval")
                gen_n = t.get("eval_n") or t.get("tokens_evaluated") or n_gen
                g_eval = t.get("eval")
                pp_ts = (prompt_n / p_eval) if p_eval else None
                tg_ts = (gen_n / g_eval) if g_eval else None
                row = {
                    "depth": depth,
                    "n_gen": n_gen,
                    "prompt_n": prompt_n,
                    "prefill_s": round(p_eval, 3) if p_eval else None,
                    "gen_s": round(g_eval, 3) if g_eval else None,
                    "pp_t_s": round(pp_ts, 1) if pp_ts else None,
                    "tg_t_s": round(tg_ts, 2) if tg_ts else None,
                }
                rows.append(row)
                print(
                    f"  depth {depth:>6} gen {n_gen:>3}: "
                    f"prefill {row['prefill_s']:>7}s ({row['pp_t_s']} t/s)  "
                    f"gen {row['gen_s']:>6}s ({row['tg_t_s']} t/s)"
                )
    finally:
        llama_server.stop_server(proc, args.port)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"model": args.gguf, "kv": args.kv, "ctx": args.ctx, "rows": rows}, f, indent=1)
    print(f"=== {len(rows)} rows -> {out_path} ===")


if __name__ == "__main__":
    main()
