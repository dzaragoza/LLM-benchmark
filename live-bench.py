#!/usr/bin/env python3
"""live-bench.py — scripted interactive-session benchmark.

Measures live generation speed through the real serving stack (llama-server),
the way a reader actually experiences it: multi-turn conversations with
growing history (real KV depth), prefills between turns (real chat shape),
all serving overhead included (tokenize/detokenize/HTTP).

Conversations come from a fixed corpus file (LMSYS Chatbot Arena, English
sample, seed 1024), so the workload is standardized and citable — the same
philosophy as the cached ARC-Challenge question set.

Companion script: arena_filter.py (English extraction + sampling) — see
report Data availability; both scripts published in the companion repo.

Protocol (fixed, pre-registered):
  - N conversations from the corpus, played verbatim (user turns sent;
    the model generates its own answers turn by turn)
  - Each answer capped at the corpus's own reply-length p75 (measured,
    not guessed)
  - History accumulates turn-to-turn (KV depth grows, like real chat)
  - Temperature 0 (greedy): deterministic, repeatable — same discipline
    as strict-ARC
  - The server's own timing (timings.predicted_per_second) is the
    authoritative metric; wall-clock printed as sanity check
  - Repeats (--repeats, default 3); report conversation mean + spread
"""

import argparse
import glob
import json
import random
import subprocess
import sys
import time
import urllib.request
import urllib.error

SERVER_BIN = "/home/daniela/technical_reports/llama-b10964-gpu/llama-server"
ARENA_DIR = "/home/daniela/technical_reports/arena/data"
SAMPLE_OUT = "/home/daniela/technical_reports/arena/english_sample.json"
SEED = 1024  # pre-registered; part of the protocol


# ---------------------------------------------------------------------------
# Step 0 — English extraction from the Arena parquet shards (run once)
# ---------------------------------------------------------------------------

def make_english_sample(n_sample=5000):
    import pyarrow.parquet as pq

    files = sorted(glob.glob(ARENA_DIR + "/**/*.parquet", recursive=True))
    if not files:
        sys.exit(f"No parquet found under {ARENA_DIR}")
    english = []
    for f in files:
        table = pq.read_table(f)
        for row in table.to_pylist():
            # lmsys-chat-1m schema: conversation_id, model, language, turn,
            # conversation: [{"role": "user"/"assistant", "content": ...}]
            if (row.get("language") or "").lower().startswith("english"):
                english.append({
                    "conversation": row["conversation"],
                    "turn": row.get("turn"),
                })
    random.seed(SEED)
    random.shuffle(english)
    sample = english[:n_sample]
    with open(SAMPLE_OUT, "w") as f:
        json.dump(sample, f)
    print(f"{len(english)} English conversations; wrote {len(sample)}-conv sample "
          f"-> {SAMPLE_OUT}")


# ---------------------------------------------------------------------------
# Corpus build (run once)
# ---------------------------------------------------------------------------

def make_corpus(arena_file, out_file, n_conversations, min_turns, max_turns,
                max_cap_tokens):
    with open(arena_file) as f:
        items = json.load(f)

    selected = []
    reply_chars = []
    for conv in items:
        msgs = conv["conversation"]
        user_msgs = [m["content"] for m in msgs if m.get("role") == "user"]
        asst_chars = [len(m["content"]) for m in msgs if m.get("role") == "assistant"]
        if not (min_turns <= len(user_msgs) <= max_turns):
            continue
        joined = " ".join(user_msgs)
        # ASCII-ish English check
        if sum(1 for c in joined if ord(c) < 128) < 0.95 * len(joined):
            continue
        if "http" in joined:
            continue
        # Skip turns that are absurdly long (paste dumps) or empty
        if any(len(u) > 4000 or not u.strip() for u in user_msgs):
            continue
        selected.append({"user_turns": user_msgs})
        reply_chars.extend(asst_chars)

    if not selected:
        sys.exit("No conversations matched the filters.")

    # Deterministic order: stable sort by content hash, take N
    selected.sort(key=lambda c: __import__("hashlib").sha256(
        json.dumps(c["user_turns"]).encode()).hexdigest())
    corpus = selected[:n_conversations]

    reply_chars.sort()
    p75 = reply_chars[int(0.75 * (len(reply_chars) - 1))] if reply_chars else 1200
    cap_tokens = min(max_cap_tokens, max(64, int(p75 / 4)))

    out = {
        "source": "LMSYS Chatbot Arena (lmsys-chat-1m), English sample, seed 1024",
        "selection": (f"{len(corpus)} conversations, {min_turns}-{max_turns} user "
                      "turns, English, no URLs, turns 1-4000 chars, deterministic "
                      "sha256 order"),
        "reply_length_p75_chars": p75,
        "answer_cap_tokens": cap_tokens,
        "temperature": 0,
        "seed": SEED,
        "conversations": corpus,
    }
    with open(out_file, "w") as f:
        json.dump(out, f, indent=1)

    total_turns = sum(len(c["user_turns"]) for c in corpus)
    print(f"Corpus written: {out_file}")
    print(f"  conversations: {len(corpus)}   total turns: {total_turns}")
    print(f"  reply p75: {p75} chars -> answer cap: {cap_tokens} tokens")


# ---------------------------------------------------------------------------
# Server management
# ---------------------------------------------------------------------------

def wait_for_server(port, timeout=300):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)
    return False


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


# ---------------------------------------------------------------------------
# The benchmark
# ---------------------------------------------------------------------------

def run_conversation(port, user_turns, cap_tokens, ctx_tokens):
    history = []
    results = []
    for i, question in enumerate(user_turns):
        history.append({"role": "user", "content": question})
        payload = {
            "messages": list(history),
            "max_tokens": cap_tokens,
            "temperature": 0,
            "stream": False,
        }
        req = urllib.request.Request(
            f"http://localhost:{port}/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        wall_start = time.time()
        with urllib.request.urlopen(req, timeout=1800) as r:
            data = json.loads(r.read())
        wall_s = time.time() - wall_start

        answer = data["choices"][0]["message"]["content"]
        history.append({"role": "assistant", "content": answer})

        t = data.get("timings", {})
        server_tps = t.get("predicted_per_second")
        n_pred = t.get("predicted_n", data.get("usage", {}).get("completion_tokens"))

        history_chars = sum(len(m["content"]) for m in history[:-1])
        depth_tokens = history_chars // 4

        results.append({
            "turn": i + 1,
            "depth_tokens_est": depth_tokens,
            "gen_tokens": n_pred,
            "server_tps": server_tps,
            "wall_tps": (n_pred / wall_s) if n_pred and wall_s else None,
        })
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus")
    ap.add_argument("--models", nargs="+")
    ap.add_argument("--port", type=int, default=8077)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--ctx", type=int, default=4096)
    ap.add_argument("--make-sample", action="store_true",
                    help="step 0: English extraction from Arena parquet")
    ap.add_argument("--make-corpus", action="store_true",
                    help="step 1: build fixed corpus from english_sample.json")
    ap.add_argument("--corpus-out", default="/home/daniela/technical_reports/live-corpus.json")
    ap.add_argument("--n-conversations", type=int, default=5)
    ap.add_argument("--min-turns", type=int, default=4)
    ap.add_argument("--max-turns", type=int,default=8)
    ap.add_argument("--max-cap-tokens", type=int, default=300)
    args = ap.parse_args()

    if args.make_sample:
        make_english_sample()
        return
    if args.make_corpus:
        make_corpus(SAMPLE_OUT, args.corpus_out, args.n_conversations,
                    args.min_turns, args.max_turns, args.max_cap_tokens)
        return

    if not args.corpus:
        ap.error("--corpus is required for benchmarking (or use --make-sample/--make-corpus)")
    with open(args.corpus) as f:
        corpus = json.load(f)
    conversations = corpus["conversations"]
    cap_tokens = corpus["answer_cap_tokens"]

    all_summary = []
    for model in args.models or []:
        label = model.split("/")[-1]
        print(f"\n=== {label} ===")
        repeat_means = []
        for rep in range(1, args.repeats + 1):
            print(f"  [rep {rep}/{args.repeats}] starting server...", flush=True)
            proc = subprocess.Popen(
                [SERVER_BIN, "-m", model, "-ngl", "99", "-c", str(args.ctx),
                 "--port", str(args.port)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            try:
                if not wait_for_server(args.port):
                    print("  ERROR: server did not become healthy; skipping")
                    stop_server(proc)
                    continue
                conv_means = []
                for ci, conv in enumerate(conversations, 1):
                    res = run_conversation(args.port, conv["user_turns"],
                                           cap_tokens, args.ctx)
                    tps = [r["server_tps"] for r in res if r["server_tps"]]
                    cmean = sum(tps) / len(tps) if tps else None
                    conv_means.append(cmean)
                    print(f"    conv {ci}: turns t/s: "
                          + ", ".join(f"{x:.1f}" for x in tps)
                          + (f"   mean {cmean:.1f}" if cmean else ""))
            finally:
                stop_server(proc)
            valid = [m for m in conv_means if m]
            if valid:
                rep_mean = sum(valid) / len(valid)
                repeat_means.append(rep_mean)
                print(f"  rep {rep}: conversation means -> "
                      + ", ".join(f"{x:.1f}" for x in valid)
                      + f"   [rep mean {rep_mean:.1f}]")

        if repeat_means:
            conv_mean = sum(repeat_means) / len(repeat_means)
            spread = (max(repeat_means) - min(repeat_means)) if len(repeat_means) > 1 else 0.0
            print(f"\n  {label}: LIVE = {conv_mean:.1f} t/s "
                  f"(mean of {len(repeat_means)} reps, spread {spread:.1f})")
            all_summary.append((label, conv_mean, spread))

    print("\n" + "=" * 60)
    print("FINAL LIVE SCORES (conversation means, server-timed)")
    for label, mean, spread in sorted(all_summary, key=lambda x: -x[1]):
        print(f"  {label}: {mean:.1f} t/s  (spread {spread:.1f})")
    print("=" * 60)


if __name__ == "__main__":
    main()
