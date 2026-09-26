#!/usr/bin/env python3
"""depth_probe.py -- decode speed at context depth, via prefill blobs.

The addendum-11 instrument (Session 26, item a of the pre-registered
experiment list): measures decode speed AT a chosen context depth
without authoring a conversation. Mechanism: decode reads the whole KV
cache once per token, so the depth tax depends on the cache SIZE
(tokens cached), not its content - any D-token prompt produces the
same depth tax. One D-token blob (corpus text repeated, exact token
budget, just under n_ctx - no context-shift risk, no 400), then
several identical follow-up generations on the same slot: the prompt
cache (cache_prompt, on by default) makes every prefill after the
first a ~0-ms cache hit, so each response's
timings.predicted_per_second is a decode sample AT DEPTH D - cleanly
separating noise-at-depth (worst/mean across same-depth samples, the
addendum-10 attribution question) from the KV trend.

ignore_eos keeps decode running for the full sample length whatever
the blob elicits (content-independence caveat on record: timing is
content-independent, answers are not).

Mode-blind by design: it measures decode physics, not a category -
thinking vs non-thinking changes which tokens generate, not tokens
per second. No mode flags, no chat template.

Verdict lines (Session 26 ruling): the guarantee is "decode speed at
reference depth >= the reader line" - the worst sample at depth vs
the anchor reader (6.5 t/s = 300 wpm at 0.75 words/token, k=1). The
floor-20 line is reported as the headroom check, not the pass line.

Two-depth check (addendum 11 prediction 4): pass --depth twice
(e.g. 2048 and 4000); with --kv architecture constants the depth
pair implies the effective bandwidth of the law's third term
(T_token(D) = (size + KV(D)) x ms/GiB + overhead) - the linearity
grade without any fit machinery.

Usage (from the repo root, on the target machine):

    python3 depth_probe.py --model ./models/qwen3.5-4b-q5_k_m.gguf
    python3 depth_probe.py --model <file> --depth 2048 --depth 4000
    python3 depth_probe.py --model <file> --kv 36,8,128 --json p.json

Writes <model>.depth-probe.json next to the model file. Reruns always
re-measure (fresh noise samples, no dump reuse): unlike the pipeline
phases this is a one-shot experiment instrument, minutes per model.
"""

import argparse
import json
import os
import sys

import llama_server
from law_fit import kv_gib

CORPUS_DEFAULT = "./live-corpus.json"
PORT_DEFAULT = 8078
CTX_DEFAULT = 4096
DEPTH_DEFAULT = 4000
SAMPLES_DEFAULT = 5
GEN_TOKENS_DEFAULT = 64
READER_TPS_DEFAULT = 6.5
FLOOR_DEFAULT = 20.0
DEPTH_TOLERANCE = 8
DEPTH_HEADROOM = 32

GUIDE = {
    "tokenize": [
        "llama-server build predates the /tokenize endpoint - use the",
        "pinned b10964 build (the study server), same as every other",
        "phase",
    ],
    "completion": [
        "llama-server build predates the /completion endpoint or rejects",
        "a field - use the pinned b10964 build; the payload is the",
        "native completion shape (n_predict / ignore_eos / cache_prompt)",
    ],
    "blob": [
        "corpus missing: python3 speed_gate.py --make-corpus (or pass",
        "--text <file> with any plain-text source)",
    ],
}


def fail(step, what, causes):
    print()
    print("=" * 60)
    print(f"DEPTH PROBE FAILED at {step}: {what}")
    print("Possible causes and fixes:")
    for c in causes:
        print(f"  - {c}")
    print("=" * 60)
    sys.exit(1)


def load_pool(corpus_file, text_file):
    if text_file:
        with open(text_file) as f:
            return f.read()
    if not os.path.isfile(corpus_file):
        fail("blob", f"corpus not found: {corpus_file}", GUIDE["blob"])
    with open(corpus_file) as f:
        corpus = json.load(f)
    turns = [t for c in corpus["conversations"] for t in c["user_turns"]]
    return "\n\n".join(turns)


def tokenize(port, content):
    try:
        data = llama_server.post_json(port, "/tokenize",
                                      {"content": content})
    except Exception as e:
        fail("tokenize", f"/tokenize request failed: {e}", GUIDE["tokenize"])
    toks = data.get("tokens")
    if toks is None:
        fail("tokenize", "response has no tokens field", GUIDE["tokenize"])
    return toks


def build_blob(port, pool, depth):
    """Repeat the pool past the depth budget, then trim characters until
    the token count lands in [depth - DEPTH_TOLERANCE, depth]."""
    n_pool = len(tokenize(port, pool))
    if not n_pool:
        fail("blob", "corpus text tokenizes to nothing", GUIDE["blob"])
    reps = (2 * depth) // n_pool + 1
    text = "\n\n".join([pool] * reps)
    n = len(tokenize(port, text))
    chars = int(len(text) * depth / n)
    best = None
    for _ in range(20):
        cand = text[:chars]
        n = len(tokenize(port, cand))
        if depth - DEPTH_TOLERANCE <= n <= depth:
            return cand, n
        if best is None or (n <= depth and n > best[1]):
            best = (cand, n)
        if n > depth:
            chars = max(1, chars * depth // n - 4)
        else:
            chars += max(64, (depth - n) * 32)
    if best is None:
        fail("blob", "could not trim the blob under the depth budget",
             GUIDE["blob"])
    return best


def probe_depth(port, blob, gen_tokens, samples):
    """Prime the slot with the blob, then take `samples` identical decode
    samples: after the first request every prefill is a cache hit, so
    each response is a decode sample at the same depth."""
    payload = {
        "prompt": blob,
        "n_predict": gen_tokens,
        "temperature": 0,
        "ignore_eos": True,
        "cache_prompt": True,
        "stream": False,
    }
    recs = []
    for i in range(1, samples + 1):
        try:
            data = llama_server.post_json(port, "/completion", payload)
        except Exception as e:
            fail("completion", f"/completion request failed: {e}",
                 GUIDE["completion"])
        t = data.get("timings", {})
        rec = {
            "sample": i,
            "prompt_n": t.get("prompt_n"),
            "prompt_ms": t.get("prompt_ms"),
            "gen_tokens": t.get("predicted_n"),
            "tps": t.get("predicted_per_second"),
        }
        recs.append(rec)
        if rec["tps"] is None or rec["prompt_ms"] is None:
            print(f"    sample {i}: no timings in response")
            continue
        pm = rec["prompt_ms"]
        cache = "cache hit" if pm < 50 else "PREFILL"
        print(f"    sample {i}: t/s {rec['tps']:.2f}  "
              f"(prompt_n {rec['prompt_n']}, prompt_ms {pm:.1f} - {cache})")
    return recs


def summarize(recs, depth_target, reader_tp, floor):
    tps = [r["tps"] for r in recs if r["tps"]]
    if not tps:
        fail("completion", "no predicted_per_second in any sample",
             GUIDE["completion"])
    worst = min(tps)
    mean = sum(tps) / len(tps)
    wm = worst / mean if mean else 0.0
    prompt_n = next((r["prompt_n"] for r in recs if r["prompt_n"]), None)
    print(f"  depth target {depth_target} (measured prompt_n {prompt_n})")
    print(f"  decode at depth: worst {worst:.2f}  mean {mean:.2f}  "
          f"worst/mean {wm:.3f}  (n={len(tps)} samples)")
    if worst >= reader_tp:
        print(f"  reader line {reader_tp:g} t/s: worst >= reader "
              f"-> guarantee HOLDS at depth")
    else:
        print(f"  reader line {reader_tp:g} t/s: worst < reader "
              f"-> guarantee BROKEN at depth")
    if worst >= floor:
        print(f"  floor {floor:g} t/s: headroom intact at depth")
    else:
        print(f"  floor {floor:g} t/s: BELOW floor at depth "
              f"(the headroom flag, addendum 10)")
    return {"depth_target": depth_target, "prompt_n": prompt_n,
            "samples": recs, "worst": worst, "mean": mean, "wm": wm}


def parse_kv(spec):
    parts = [p.strip() for p in spec.split(",")]
    if len(parts) < 3:
        sys.exit(f"bad --kv spec (need layers,kv_heads,head_dim): {spec}")
    layers, kvh, hd = int(parts[0]), int(parts[1]), int(parts[2])
    bpe = float(parts[3]) if len(parts) > 3 else 2.0
    return layers, kvh, hd, bpe


def main():
    ap = argparse.ArgumentParser(
        description="decode speed at context depth via prefill blobs "
                    "(the addendum-11 depth protocol)")
    ap.add_argument("--model", required=True, help=".gguf file to probe")
    ap.add_argument("--depth", action="append", type=int, default=[],
                    metavar="TOK",
                    help="prefill depth in tokens (repeatable for the "
                         "two-depth linearity check; default 4000, just "
                         "under the 4096 protocol constant)")
    ap.add_argument("--samples", type=int, default=SAMPLES_DEFAULT,
                    help="decode samples per depth (default 5: the "
                         "noise-at-depth measurement needs a handful)")
    ap.add_argument("--gen-tokens", type=int, default=GEN_TOKENS_DEFAULT,
                    help="tokens generated per sample (default 64; "
                         "ignore_eos guarantees the full length)")
    ap.add_argument("--port", type=int, default=PORT_DEFAULT)
    ap.add_argument("--ctx", type=int, default=CTX_DEFAULT,
                    help="server n_ctx (default 4096, the protocol "
                         "constant; depth + gen_tokens must fit)")
    ap.add_argument("--corpus", default=CORPUS_DEFAULT,
                    help="blob source: the study corpus (default) or --text")
    ap.add_argument("--text", default=None,
                    help="plain-text blob source, overrides --corpus")
    ap.add_argument("--reader-tp", type=float, default=READER_TPS_DEFAULT,
                    help="the guarantee line (default 6.5 t/s = 300 wpm "
                         "at 0.75 words/token, k=1)")
    ap.add_argument("--floor", type=float, default=FLOOR_DEFAULT,
                    help="the headroom line (default 20 t/s)")
    ap.add_argument("--kv", default=None,
                    metavar="'layers,kv_heads,head_dim[,bytes_per_elem]'",
                    help="architecture constants: enables the KV(D) tax "
                         "column and, with >= 2 depths, the implied "
                         "third-term bandwidth (linearity grade). "
                         "Sliding-window models: pass window-capped "
                         "constants yourself")
    ap.add_argument("--json", default=None,
                    help="dump path (default: <model>.depth-probe.json)")
    args = ap.parse_args()

    if not os.path.isfile(args.model):
        sys.exit(f"model file not found: {args.model}")
    depths = sorted(set(args.depth) or [DEPTH_DEFAULT])
    for d in depths:
        if d + args.gen_tokens > args.ctx - DEPTH_HEADROOM:
            sys.exit(f"depth {d} + {args.gen_tokens} gen tokens does not "
                     f"fit ctx {args.ctx} with {DEPTH_HEADROOM} headroom "
                     f"- lower --depth or raise --ctx (and note in the "
                     "notebook if you leave the 4096 protocol constant)")
    kv = parse_kv(args.kv) if args.kv else None
    size_gib = os.path.getsize(args.model) / (1 << 30)

    pool = load_pool(args.corpus, args.text)
    print(f"=== depth probe: {os.path.basename(args.model)} "
          f"({size_gib:.2f} GiB) ===")
    print(f"depths {depths}, {args.samples} samples x "
          f"{args.gen_tokens} tokens each, ctx {args.ctx}")

    extra = ["-ngl", "99", "-c", str(args.ctx)]
    results = []
    for d in depths:
        # fresh server per depth: the slot cache survives across depths
        # on one server, and consecutive blobs share the corpus pool's
        # opening text - the 2048-blob's tokens stay cached and the
        # 4000-blob prefills only its tail (measured prompt_n 1959 on
        # the first two-depth run: decode WAS at ~4000, but prompt_n
        # under-reported depth). A restart per depth gives every depth
        # a clean slot and an honest prompt_n (Session 27, addendum 18)
        print(f"\n--- depth {d} ---")
        proc, healthy = llama_server.start_server(args.model, args.port,
                                                  extra)
        try:
            if not healthy:
                sys.exit("server did not become healthy")
            blob, n_tok = build_blob(args.port, pool, d)
            print(f"  blob built: {n_tok} tokens "
                  f"(target {d}, tolerance {DEPTH_TOLERANCE})")
            recs = probe_depth(args.port, blob, args.gen_tokens,
                               args.samples)
            results.append(summarize(recs, d, args.reader_tp, args.floor))
        finally:
            llama_server.stop_server(proc, args.port)

    print("\n" + "=" * 72)
    print("DEPTH SUMMARY  (decode t/s at depth; the law's third term)")
    print("=" * 72)
    hdr = f"  {'depth':>6} {'prompt_n':>9} {'worst':>7} {'mean':>7}"
    if kv:
        hdr += f" {'KV(D) GiB':>10} {'+ms/tok':>8}"
    print(hdr)
    kv_gibs = {}
    for r in results:
        row = (f"  {r['depth_target']:>6} {str(r['prompt_n']):>9} "
               f"{r['worst']:>7.2f} {r['mean']:>7.2f}")
        if kv:
            d_eff = r["prompt_n"] or r["depth_target"]
            kvg = kv_gib(kv[0], kv[1], kv[2], d_eff, kv[3])
            kv_gibs[r["depth_target"]] = kvg
            tax_ms = ((1000.0 / r["mean"]) * kvg / (size_gib + kvg)
                      if r["mean"] else 0.0)
            row += f" {kvg:>10.3f} {tax_ms:>8.2f}"
        print(row)

    if kv and len(results) >= 2:
        pts = [(size_gib + kv_gibs[r["depth_target"]], 1.0 / r["mean"])
               for r in results]
        (x1, y1), (x2, y2) = pts[0], pts[-1]
        if y2 != y1:
            bw = (x2 - x1) / (y2 - y1)
            print(f"\n  third-term linearity: implied BW from the depth "
                  f"pair = {bw:.1f} GiB/s ({1000.0 / bw:.2f} ms/GiB)")
            print(f"  (the law's T14s constant is ~13.07 ms/GiB; a "
                  "matching number grades the KV-tax arithmetic and the "
                  "noise attribution together)")
        else:
            print("\n  third-term linearity: no speed change across "
                  "depths - nothing to imply (check the samples above)")

    dump = args.json or (args.model + ".depth-probe.json")
    out = {
        "model": args.model,
        "size_gib": size_gib,
        "ctx": args.ctx,
        "gen_tokens": args.gen_tokens,
        "kv_spec": args.kv,
        "reader_tp": args.reader_tp,
        "floor": args.floor,
        "depths": results,
    }
    with open(dump, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\ndepth-probe dump written to {dump}")


if __name__ == "__main__":
    main()
