#!/usr/bin/env python3
"""session_replicate.py -- replay the gate's worst conversation live,
streaming, for the author's felt-experience calibration (prediction 5).

The one measurement the instrument cannot replace: the author reads the
exact conversation that produced the worst turn, at her own pace, and
grades her own experience. This instrument makes the session faithful
to the gate instead of hand-assembled:

  - same server launch flags as the gate (no_thinking template kwarg)
  - same depth_budget() blob for conv 1 (the gate's own arithmetic)
  - same conversation, verbatim from live-corpus.json
  - every turn replayed non-streaming exactly as the gate ran it
    (so the timing record matches the dump), and then
  - the conversation runs a SECOND time, STREAMING to the terminal:
    the author watches tokens arrive at true pace and reads them as
    they come. Per-token arrival times are recorded - TTFT and the
    inter-token gap distribution, the Andes view the non-streaming
    gate cannot see.

Usage (repo root, the author's machine):
    python3 session_replicate.py --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf
    python3 session_replicate.py --model <file> --conv 3   # any conversation
    python3 session_replicate.py --model <file> --stream-only  # skip the
        non-streaming replay, go straight to the live part

Writes <model>.session.json next to the model file (both passes' turn
records plus the streamed arrival-time telemetry).
"""
import argparse
import json
import os
import sys
import time

import llama_server
from speed_gate import (CTX_DEFAULT, READER_WPS_DEFAULT,
                        THINK_ALLOWANCE, build_blob, depth_budget)

CORPUS_DEFAULT = "./live-corpus.json"
PORT_DEFAULT = 8079


def replay_turn(port, history, cap_tokens, thinking, no_thinking):
    """One gate-faithful non-streaming turn (the gate's own request)."""
    payload = {"messages": list(history),
               "max_tokens": (cap_tokens + THINK_ALLOWANCE)
                             if thinking else cap_tokens,
               "temperature": 0, "stream": False}
    if no_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    t0 = time.time()
    data = llama_server.post_json(port, "/v1/chat/completions", payload)
    wall = time.time() - t0
    message = data["choices"][0]["message"]
    answer = message.get("content") or ""
    t = data.get("timings", {})
    return answer, {"server_tps": t.get("predicted_per_second"),
                    "server_wps": None,
                    "prompt_n": t.get("prompt_n"),
                    "prompt_ms": t.get("prompt_ms"),
                    "wall_s": round(wall, 3),
                    "n_gen": t.get("predicted_n",
                                   data.get("usage", {})
                                   .get("completion_tokens"))}


def stream_turn(port, history, cap_tokens, thinking, no_thinking):
    """The live pass: stream the answer to the terminal as it arrives,
    recording per-delta arrival times. Returns (answer, telemetry)."""
    payload = {"messages": list(history),
               "max_tokens": (cap_tokens + THINK_ALLOWANCE)
                             if thinking else cap_tokens,
               "temperature": 0, "stream": True}
    if no_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    pieces, times, t_first = [], [], None
    t0 = time.time()
    for text, t_arr in llama_server.stream_completion(port, payload):
        if t_first is None:
            t_first = t_arr - t0
        pieces.append(text)
        times.append(t_arr)
        print(text, end="", flush=True)
    print()
    answer = "".join(pieces)
    gaps = [times[i] - times[i - 1] for i in range(1, len(times))]
    n_words = len(answer.split())
    span = (times[-1] - times[0]) if len(times) > 1 else 0.0
    wps = n_words / span if span > 0 else None
    return answer, {"ttft_s": round(t_first, 3) if t_first is not None
                    else None,
                    "n_deltas": len(times),
                    "n_words": n_words,
                    "gen_span_s": round(span, 3),
                    "mean_gap_ms": round(1000 * sum(gaps) / len(gaps), 1)
                    if gaps else None,
                    "max_gap_ms": round(1000 * max(gaps), 1)
                    if gaps else None,
                    "streamed_wps": round(wps, 2) if wps else None}


def main():
    ap = argparse.ArgumentParser(
        description="replay the gate's conversation live, streaming")
    ap.add_argument("--model", required=True)
    ap.add_argument("--corpus", default=CORPUS_DEFAULT)
    ap.add_argument("--conv", type=int, default=1,
                    help="conversation number in the corpus (1-based)")
    ap.add_argument("--port", type=int, default=PORT_DEFAULT)
    ap.add_argument("--ctx", type=int, default=CTX_DEFAULT)
    ap.add_argument("--no-thinking", action="store_true")
    ap.add_argument("--thinking", action="store_true")
    ap.add_argument("--stream-only", action="store_true",
                    help="skip the non-streaming replay pass")
    ap.add_argument("--reader-wps", type=float,
                    default=READER_WPS_DEFAULT)
    ap.add_argument("--keep-server", action="store_true",
                    help="leave the server running for further sessions")
    args = ap.parse_args()
    if args.thinking and args.no_thinking:
        sys.exit("--thinking and --no-thinking are mutually exclusive")

    with open(args.corpus) as f:
        corpus = json.load(f)
    conv = corpus["conversations"][args.conv - 1]
    cap_tokens = corpus["answer_cap_tokens"]
    user_turns = conv["user_turns"]
    label = os.path.basename(args.model)

    print(f"=== session replicate: {label} / conv {args.conv} ===")
    print(f"    worst-turn conversation from the gate's dump; "
          f"reader line {args.reader_wps} w/s")
    extra = ["-ngl", "99", "-c", str(args.ctx)]
    if args.thinking:
        extra += ["--reasoning-format", "deepseek"]
    if args.no_thinking:
        extra += ["--chat-template-kwargs", '{"enable_thinking": false}']
    proc, healthy = llama_server.start_server(args.model, args.port, extra)
    if not healthy:
        sys.exit("server did not become healthy")
    try:
        budget = depth_budget(user_turns, cap_tokens, args.ctx,
                              args.thinking)
        pool = "\n\n".join(t for c in corpus["conversations"]
                           for t in c["user_turns"])
        blob, blob_tokens = build_blob(args.port, pool, budget)
        if blob is None:
            sys.exit("no blob budget for this conversation")

        # pass 1: gate-faithful non-streaming replay (matches the dump)
        records = []
        if not args.stream_only:
            print(f"\n--- pass 1: gate replay (non-streaming) ---")
            print(f"    blob: {blob_tokens} tokens (budget {budget})")
            history = [{"role": "user", "content": blob},
                       {"role": "assistant", "content": "Understood."}]
            for i, question in enumerate(user_turns, 1):
                history.append({"role": "user", "content": question})
                answer, rec = replay_turn(args.port, history, cap_tokens,
                                          args.thinking, args.no_thinking)
                history.append({"role": "assistant", "content": answer})
                rec.update({"turn": i, "question": question})
                records.append(rec)
                print(f"    turn {i}: {rec['server_tps']:.2f} t/s "
                      f"(prompt_n {rec['prompt_n']}, "
                      f"wall {rec['wall_s']:.1f}s)")

        # pass 2: the live streaming session
        print(f"\n--- pass 2: LIVE session (streaming) ---")
        print("    reading pace calibration: the answer streams at the "
              "model's true pace; read it as it arrives.\n")
        history = [{"role": "user", "content": blob},
                   {"role": "assistant", "content": "Understood."}]
        for i, question in enumerate(user_turns, 1):
            history.append({"role": "user", "content": question})
            print(f"  [you] {question}")
            print("  [model] ", end="", flush=True)
            answer, tel = stream_turn(args.port, history, cap_tokens,
                                      args.thinking, args.no_thinking)
            history.append({"role": "assistant", "content": answer})
            tel.update({"turn": i})
            records.append({"turn": i, "pass": "stream", **tel})
            print(f"    (ttft {tel['ttft_s']}s, {tel['streamed_wps']} w/s "
                  f"streamed, mean gap {tel['mean_gap_ms']} ms, "
                  f"max gap {tel['max_gap_ms']} ms)")
            print()

        dump = os.path.join(os.path.dirname(args.model),
                            label + ".session.json")
        with open(dump, "w") as f:
            json.dump({"model": label, "conv": args.conv,
                       "reader_wps": args.reader_wps,
                       "turns": records}, f, indent=1)
        print(f"session telemetry written to {dump}")

        if not args.keep_server:
            print("\nPre-registered feel-prediction bands (addendum 26):")
            print("  1. Q8_0 at ~15 t/s feels smooth WHILE STREAMING "
                  "(no waiting mid-answer);")
            print("  2. the wait that IS felt is the prefill "
                  "(TTFT ~8-10 s at 4k depth) before each answer;")
            print("  3. streamed w/s at reading pace ~ 10-13 w/s "
                  "(min 8) stays above your 300-wpm line;")
            print("  4. the verdict (PASS at 5.0 w/s) matches the felt "
                  "experience for a fast reader.")
    finally:
        if args.keep_server:
            print(f"server left running on port {args.port}")
        else:
            llama_server.stop_server(proc, args.port)


if __name__ == "__main__":
    main()
