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

  --interactive: the live pass waits for the author to press Enter
  before each user turn is sent - the conversation is felt as a real
  chat (send, wait, read), not read as a transcript. The history is
  still verbatim (gate-faithful); only the pacing is human. Each
  turn's send-to-first-token wait is recorded: the FIRST send carries
  the whole blob prefill (~2600 tokens, seconds); follow-up sends
  prefill only the new tail (cache_prompt), so their TTFT should be
  near-instant - the cold-start/warm-follow-up structure a real chat
  with a deep context has, which the gate's per-turn dump never
  separated. Telemetry is suppressed during the chat (perception
  matters); a per-turn summary prints at the end.

Usage (repo root, the author's machine):
    python3 session_replicate.py --model ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf
    python3 session_replicate.py --model <file> --conv 3   # any conversation
    python3 session_replicate.py --model <file> --stream-only  # skip the
        non-streaming replay, go straight to the live part
    python3 session_replicate.py --model <file> --interactive  # press
        Enter to send each turn yourself - the real-chat feel

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
    recording per-delta arrival times. Returns (answer, telemetry).
    Per-delta word positions are recorded ("deltas": cumulative word
    count at each arrival) - the raw input of the reader-collision
    simulation, kept in the dump so the true measurement can be
    re-run at any reader speed, reaction time, post-hoc."""
    payload = {"messages": list(history),
               "max_tokens": (cap_tokens + THINK_ALLOWANCE)
                             if thinking else cap_tokens,
               "temperature": 0, "stream": True}
    if no_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    pieces, times, words = [], [], []
    t_first = None
    t0 = time.time()
    for text, t_arr in llama_server.stream_completion(port, payload):
        if t_first is None:
            t_first = t_arr - t0
        pieces.append(text)
        times.append(t_arr)
        words.append(len("".join(pieces).split()))
        print(text, end="", flush=True)
    print()
    answer = "".join(pieces)
    gaps = [times[i] - times[i - 1] for i in range(1, len(times))]
    n_words = len(answer.split())
    span = (times[-1] - times[0]) if len(times) > 1 else 0.0
    wps = n_words / span if span > 0 else None
    deltas = [{"t": round(t - t0, 4), "w": w}
              for t, w in zip(times, words)]
    return answer, {"ttft_s": round(t_first, 3) if t_first is not None
                    else None,
                    "n_deltas": len(times),
                    "n_words": n_words,
                    "gen_span_s": round(span, 3),
                    "mean_gap_ms": round(1000 * sum(gaps) / len(gaps), 1)
                    if gaps else None,
                    "max_gap_ms": round(1000 * max(gaps), 1)
                    if gaps else None,
                    "streamed_wps": round(wps, 2) if wps else None,
                    "deltas": deltas}


def reader_collision(deltas, n_words, reader_wps, reaction_s):
    """The true felt-lag measurement (author ruling, addendum 30):
    simulate WHERE THE READER IS at every moment vs where printing
    has reached. The reader starts reading reaction_s after the
    first word appears and reads at reader_wps; a lag is FELT only
    when the reader's position collides with the printed position
    (the reader has consumed everything printed and waits) - a
    stall inside an already-accumulated buffer is invisible.
    reader_pos(t) = min(printed_pos(t), reader_wps * (t - t_read)):
    waiting = intervals where the reader line has crossed the
    printed staircase while the answer is incomplete. Returns
    collision metrics; deltas = [{"t": arrival, "w": cumulative
    words}] from stream_turn."""
    if not deltas or n_words == 0:
        return {"catchup_events": 0, "catchup_s": 0.0,
                "first_catchup_word_frac": None}
    t_read = deltas[0]["t"] + reaction_s
    pos = 0.0            # words the reader has consumed
    events, total, first_frac = 0, 0.0, None
    waiting_prev = False
    for i in range(len(deltas) - 1):
        t_i, p = deltas[i]["t"], deltas[i]["w"]
        t_next = deltas[i + 1]["t"]
        s = max(t_i, t_read)      # the reader does not exist before t_read
        if t_next <= s:
            continue
        if pos >= p - 1e-9:
            # pinned at the printed frontier: the reader has consumed
            # everything printed and waits for the next delta
            total += t_next - s
            if not waiting_prev:
                events += 1
                if first_frac is None:
                    first_frac = p / n_words
            waiting_prev = True
        else:
            advance = reader_wps * (t_next - s)
            if pos + advance >= p:
                # the reader catches the frontier mid-interval, then
                # waits for the remainder
                t_reach = s + (p - pos) / reader_wps
                total += t_next - t_reach
                if not waiting_prev:
                    events += 1
                    if first_frac is None:
                        first_frac = p / n_words
                waiting_prev = True
            else:
                waiting_prev = False   # behind and reading: no wait
            pos = min(p, pos + advance)
    return {"catchup_events": events,
            "catchup_s": round(total, 2),
            "first_catchup_word_frac": round(first_frac, 3)
            if first_frac is not None else None}
def resim_mode(session_path, reader_wps, reaction_s):
    """Post-hoc re-simulation (no server): read a .session.json and
    re-run the reader-collision simulation at a new reader speed /
    reaction time. The author's reading speed is variable run-to-run;
    the deltas are the measurement, the simulation parameters are not.
    Sweeps reader speed as a BAND (multiplicative steps around the
    given value) and reports the collision table per turn, so the
    variable-reader question is answered as a sensitivity, not a
    constant."""
    with open(session_path) as f:
        session = json.load(f)
    streams = [t for t in session["turns"] if t.get("pass") == "stream"]
    band = [reader_wps * m for m in (0.6, 0.8, 1.0, 1.2, 1.5)]
    print(f"=== re-simulation: {os.path.basename(session_path)} ===")
    print(f"    reaction {reaction_s} s; reader-speed band "
          f"{band[0]:.1f}-{band[-1]:.1f} w/s "
          f"(your reading speed is variable - the band is the honest "
          "reader)")
    for w in band:
        worst_ev, worst_s = 0, 0.0
        rows = []
        for t in streams:
            r = reader_collision(t["deltas"], t["n_words"], w,
                                 reaction_s)
            rows.append(r)
            worst_ev = max(worst_ev, r["catchup_events"])
            worst_s = max(worst_s, r["catchup_s"])
        cells = "  ".join(f"t{t['turn']}:{r['catchup_events']}"
                           f"/{r['catchup_s']}s"
                           for t, r in zip(streams, rows))
        print(f"    {w:4.1f} w/s: {cells}")
    print("    (events/waiting per turn; first catch-up position in "
          "the .session.json per-turn records)")


def main():
    ap = argparse.ArgumentParser(
        description="replay the gate's conversation live, streaming")
    ap.add_argument("--resim", metavar="SESSION_JSON",
                    help="post-hoc mode: re-simulate reader collisions "
                         "at a band of reader speeds from an existing "
                         ".session.json (no server needed)")
    ap.add_argument("--model")
    ap.add_argument("--corpus", default=CORPUS_DEFAULT)
    ap.add_argument("--conv", type=int, default=1,
                    help="conversation number in the corpus (1-based)")
    ap.add_argument("--port", type=int, default=PORT_DEFAULT)
    ap.add_argument("--ctx", type=int, default=CTX_DEFAULT)
    ap.add_argument("--no-thinking", action="store_true")
    ap.add_argument("--thinking", action="store_true")
    ap.add_argument("--stream-only", action="store_true",
                    help="skip the non-streaming replay pass")
    ap.add_argument("--interactive", action="store_true",
                    help="press Enter to send each user turn yourself "
                         "(real-chat feel; implies the live pass only; "
                         "per-turn TTFT recorded)")


    ap.add_argument("--reader-wps", type=float,
                    default=READER_WPS_DEFAULT,
                    help="reader speed (w/s) for the collision simulation")
    ap.add_argument("--reaction-s", type=float, default=0.45,
                    help="notice-and-start delay: seconds from first "
                         "word printed to reading start. Anchored "
                         "(addendum 31): simple visual RT ~0.25 s + "
                         "saccade latency to the text ~0.20 s (Carpenter "
                         "1988; PubMed 6227700 for the reading case). "
                         "Anticipated attention (already watching the "
                         "output) pushes toward ~0.35 s.")
    ap.add_argument("--keep-server", action="store_true",
                    help="leave the server running for further sessions")
    args = ap.parse_args()
    if args.resim:
        resim_mode(args.resim, args.reader_wps, args.reaction_s)
        return
    if not args.model:
        sys.exit("--model is required unless --resim is used")
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
        if args.interactive:
            print("  interactive mode: press Enter to send each turn "
                  "yourself.")
        if not args.stream_only and not args.interactive:
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
        if args.interactive:
            print("    the conversation is yours: each turn is shown, you "
                  "press Enter to send it,")
            print("    then read the answer as it streams. The first "
                  "send carries the context prefill;")
            print("    the follow-ups should start near-instantly.\n")
        else:
            print("    reading pace calibration: the answer streams at the "
                  "model's true pace; read it as it arrives.\n")
        history = [{"role": "user", "content": blob},
                   {"role": "assistant", "content": "Understood."}]
        for i, question in enumerate(user_turns, 1):
            history.append({"role": "user", "content": question})
            if args.interactive:
                print(f"[you] {question}")
                input("(press Enter to send) ")
                print("[model] ", end="", flush=True)
            else:
                print(f"  [you] {question}")
                print("  [model] ", end="", flush=True)
            answer, tel = stream_turn(args.port, history, cap_tokens,
                                      args.thinking, args.no_thinking)
            history.append({"role": "assistant", "content": answer})
            tel.update({"turn": i})
            tel.update(reader_collision(tel["deltas"], tel["n_words"],
                                        args.reader_wps, args.reaction_s))
            records.append({"turn": i, "pass": "stream",
                            "interactive": args.interactive, **tel})
            if not args.interactive:
                print(f"    (ttft {tel['ttft_s']}s, {tel['streamed_wps']} w/s "
                      f"streamed, mean gap {tel['mean_gap_ms']} ms, "
                      f"max gap {tel['max_gap_ms']} ms)")
                print()
        if args.interactive:
            print("\n--- session summary (send-to-first-token per turn) "
                  "---")
            for r in (t for t in records if t.get("pass") == "stream"):
                print(f"    turn {r['turn']}: TTFT {r['ttft_s']}s, "
                      f"{r['streamed_wps']} w/s streamed, "
                      f"mean gap {r['mean_gap_ms']} ms")
            print("\n--- reader-collision simulation (the true felt-lag "
                  "measurement, addendum 30) ---")
            print(f"    reader {args.reader_wps} w/s, reaction "
                  f"{args.reaction_s} s: where the reader actually hits "
                  "the stream.")
            for r in (t for t in records if t.get("pass") == "stream"):
                print(f"    turn {r['turn']}: catch-up events "
                      f"{r['catchup_events']}, waiting "
                      f"{r['catchup_s']}s, first at word "
                      f"{r['first_catchup_word_frac']}")
            print()

        dump = os.path.join(os.path.dirname(args.model),
                            label + ".session.json")
        with open(dump, "w") as f:
            json.dump({"model": label, "conv": args.conv,
                       "reader_wps": args.reader_wps,
                       "turns": records}, f, indent=1)
        print(f"session telemetry written to {dump}")

        if not args.keep_server:
            print("\nPre-registered feel predictions (notebook addenda "
                  "26 and 28):")
            print("  1. streaming at ~15 t/s feels smooth; no mid-answer "
                  "waiting for a 300-wpm reader;")
            print("  2. the wait that IS felt is the FIRST send "
                  "(context prefill, ~seconds); follow-up sends are "
                  "near-instant (cache_prompt);")
            print("  3. streamed w/s stays above the 5.0 w/s reader line "
                  "on every turn;")
            print("  4. the verdict (PASS at the 5.0 w/s line) matches the "
                  "felt experience.")
    finally:
        if args.keep_server:
            print(f"server left running on port {args.port}")
        else:
            llama_server.stop_server(proc, args.port)


if __name__ == "__main__":
    main()
