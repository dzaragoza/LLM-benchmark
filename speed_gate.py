#!/usr/bin/env python3
"""speed_gate.py -- the worst-turn speed gate (middle layer).

Measures live generation speed through the real serving stack, the way
a reader actually experiences it: multi-turn conversations with growing
history (real KV depth), prefills between turns (real chat shape), all
serving overhead included (tokenize/detokenize/HTTP). Merged from the
former live-bench.py (its measurement half) when the pipeline was
split into layers - the gate IS the live benchmark.

Conversations come from a fixed corpus file (LMSYS Chatbot Arena,
English sample, seed 1024), so the workload is standardized and
citable - the same philosophy as the cached ARC-Challenge question
set. This script owns corpus/sample building too (the --make-sample /
--make-corpus steps of the former live-bench.py).

Protocol v2 (author ruling, Session 27 - the depth-prefill gate):
  - The guarantee, restated: the WORST turn AT THE REFERENCE DEPTH
    (the 4096 protocol constant, addendum 9) must never fall below
    the anchor reader - 6.5 t/s = 300 wpm at 0.75 words/token (k=1,
    Brysbaert 2019; addenda 2-6) - so even a fast reader is never
    made to wait. Floor 20 (k=3) is reported as headroom, not gated.
  - Each conversation runs ON TOP of a depth prefill: a blob of
    corpus text (content irrelevant - the KV cost is
    content-independent, addendum 11) as a prepended user turn,
    sized per conversation via /tokenize so the deepest turn lands
    just under the reference depth. The blob rides inside the
    history, so the chat template wraps it and the prompt cache
    retains it turn-to-turn (cache_prompt, on by default).
  - After each conversation: same-depth noise samples (identical
    tiny follow-ups on the slot the conversation left) - worst/mean
    across them is the machine's noise at depth, cleanly separated
    from the KV trend (the addendum-10 attribution).
  - Never exceeds ctx (context shift would silently discard the
    blob; gemma-3 hard-errors on shift) - the blob budget is
    ctx - headroom - the conversation's own worst-case accumulation.
  - N conversations from the corpus, played verbatim on top of the
    blob (user turns sent; the model generates its own answers)
  - Each answer capped at the corpus's own reply-length p75 (measured,
    not guessed)
  - Temperature 0 (greedy): deterministic, repeatable
  - The server's own timing (timings.predicted_per_second) is the
    authoritative metric; an external wall-clock cross-check (generation
    span = wall time minus prompt processing) is computed per turn
  - THE RESULT IS THE WORST TURN across all depth-conditioned turns;
    verdict: PASS if worst >= reader line - 2*sigma (the lenient
    2-sigma ruling, now applied to the guarantee line); first PASS =
    selected - which, at the reader line, walks the ladder to the
    TOP rung that still guarantees the reader (the old floor-20 gate
    was a headroom judgment and rejected rungs the guarantee admits).
  - Qualifying tier: 1 rep (default). Final/podium numbers: --repeats 3.

Thinking-model category (author ruling 2026-09-24): the SAME worst-turn
gate applies (thinking tokens are generated at the same t/s); latency
spent thinking is the user's informed choice and is NOT gated. Thinking
is returned separately (reasoning_content) and measured (tokens +
estimated time share). Unrestricted thinking: max_tokens = answer cap +
THINK_ALLOWANCE; turns whose thinking consumes the whole allowance are
flagged (answer_empty).

Hybrid non-thinking mode (--no-thinking): sends chat_template_kwargs
{"enable_thinking": false} with every request and launches the server
with --chat-template-kwargs; for hybrid models run in the non-thinking
category. Verify with the first-turn dump: no reasoning, no inline
think tags must appear.

Mode rule (rule 8): hybrid models are allowed in BOTH categories and
must run in the category's mode. Dumps are name-separated per mode - a
thinking-mode dump must NEVER be reused by a non-thinking run (or vice
versa) because the resume check compares timestamps only (Session 25
bug: a --no-thinking run inherited thinking-mode dumps and reported
the thinking gate numbers as its own).

The server itself is managed by llama_server.py (the bottom-layer
interface); nothing here touches the process directly.

CLI (standalone use, from the repo root):
    python3 speed_gate.py --model ./models/A/A-Q6_K.gguf --floor 20
    python3 speed_gate.py --model <file> --thinking
    python3 speed_gate.py --model <file> --no-thinking
    python3 speed_gate.py --make-sample     # step 0 (once)
    python3 speed_gate.py --make-corpus     # step 1 (once)

Imported by full_benchmark.py (bench, analyze, live_dump_name).
"""

import argparse
import glob
import json
import math
import os
import random
import sys
import time

import llama_server

CORPUS_DEFAULT = "./live-corpus.json"
FLOOR_DEFAULT = 20.0
READER_WPS_DEFAULT = 5.0  # k=1 guarantee line, WORDS/s: 300 wpm fast
                          # reader (Brysbaert 2019). Protocol v2.1:
                          # the anchor is words, not tokens.
WORDS_PER_TOKEN_DEFAULT = 0.75  # unanchored rule of thumb; replaced per
                                # dump by the measured ratio (v2.1)
PORT_DEFAULT = 8077
CTX_DEFAULT = 4096
DEPTH_HEADROOM = 64
REPEATS_DEFAULT = 1
ARENA_DIR = "./arena/data"
SAMPLE_OUT = "./arena/english_sample.json"
SEED = 1024  # pre-registered; part of the protocol
THINK_ALLOWANCE = 2048  # thinking category: generation room on top
                 # (raised 1024->2048 by author ruling 2026-09-24: Qwen3.5-4B
                 #  measured 790-1440 natural thinking tokens/turn; at 1024 the
                 #  allowance, 82% of turns ran out mid-thinking (answer_empty)
                 #  - Session 25. Unrestricted-thinking ruling preserved: we never
                 #  tell the model to stop, we just don't cut it off mid-sentence.)

GUIDE = {
    3: [
        "llama-server missing: ./llama-b10964-gpu/llama-server must exist",
        "corpus missing: python3 speed_gate.py --make-corpus",
        "port conflict: stop other llama-server instances (or pass --port)",
        "GPU stack: the server startup log names the GPU - it must "
        "be the real one via the vendor driver, never a software "
        "rasterizer (llvmpipe on Linux)",
    ],
    4: [
        "dump unreadable: the .live-dump.json is malformed or empty",
        "if the bench was interrupted, delete the dump and rerun "
        "(phase 3 will redo it)",
    ],
}


def fail(phase, rung, what, causes):
    """Abort loudly for one phase, with reader guidance."""
    print()
    print("=" * 60)
    print(f"PHASE {phase} FAILED at {rung}: {what}")
    print("Possible causes and fixes:")
    for c in causes:
        print(f"  - {c}")
    print("Fix the cause, then RERUN THE SAME COMMAND: the script is")
    print("idempotent and will resume from this phase.")
    print("=" * 60)
    sys.exit(1)


# =========================================================== corpus build
# (from the former live-bench.py, verbatim protocol)

def make_english_sample(n_sample=5000):
    import pyarrow.parquet as pq

    files = sorted(glob.glob(os.path.join(ARENA_DIR, "**", "*.parquet"),
                             recursive=True))
    if not files:
        sys.exit(f"No parquet found under {ARENA_DIR}. Download the "
                 "lmsys-chat-1m dataset first (see README).")
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
    print(f"{len(english)} English conversations; wrote {len(sample)}-conv "
          f"sample -> {SAMPLE_OUT}")


def make_corpus(arena_file, out_file, n_conversations, min_turns, max_turns,
                max_cap_tokens):
    with open(arena_file) as f:
        items = json.load(f)

    selected = []
    reply_chars = []
    for conv in items:
        msgs = conv["conversation"]
        user_msgs = [m["content"] for m in msgs if m.get("role") == "user"]
        asst_chars = [len(m["content"]) for m in msgs
                      if m.get("role") == "assistant"]
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
    import hashlib
    selected.sort(key=lambda c: hashlib.sha256(
        json.dumps(c["user_turns"]).encode()).hexdigest())
    corpus = selected[:n_conversations]

    reply_chars.sort()
    p75 = reply_chars[int(0.75 * (len(reply_chars) - 1))] if reply_chars else 1200
    cap_tokens = min(max_cap_tokens, max(64, int(p75 / 4)))

    out = {
        "source": "LMSYS Chatbot Arena (lmsys-chat-1m), English sample, seed 1024",
        "selection": (f"{len(corpus)} conversations, {min_turns}-{max_turns} "
                      "user turns, English, no URLs, turns 1-4000 chars, "
                      "deterministic sha256 order"),
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


# =========================================================== measurement

def depth_budget(user_turns, cap_tokens, ctx, thinking=False):
    """Per-conversation blob budget: the deepest turn must land at the
    reference depth without ever exceeding ctx (context shift would
    silently discard the blob - and gemma-3 hard-errors on shift).
    Estimates conversation-side tokens at 4 chars/token (the blob is
    exact via /tokenize; the conversation estimate only sizes the blob,
    it never decides the measurement). Thinking mode: generation can
    reach cap + THINK_ALLOWANCE, and reasoning + answer both persist
    in the history - budgeted at 4 chars/token chars-side."""
    conv_side = 0
    for q in user_turns:
        conv_side += len(q) // 4
        conv_side += (cap_tokens + THINK_ALLOWANCE) \
            if thinking else cap_tokens
    budget = ctx - DEPTH_HEADROOM - conv_side
    return max(0, budget)


def build_blob(port, pool, budget):
    """Depth-prefill blob for one conversation: repeated corpus text
    trimmed to the exact per-model token budget via /tokenize."""
    if budget <= 0:
        return None, 0
    reps = budget * 8 // max(1, len(pool)) + 2
    text = "\n\n".join([pool] * reps)
    return llama_server.trim_to_tokens(port, text, budget)


def run_conversation(port, user_turns, cap_tokens, ctx_tokens,
                     thinking=False, no_thinking=False, blob=None,
                     blob_tokens=0):
    """Protocol v2: the conversation runs ON TOP of the depth prefill.
    The blob is a prepended user turn, so the chat template wraps it,
    cache_prompt retains it turn-to-turn, and every generated turn is
    depth-conditioned at the reference depth. Timing (like KV cost) is
    content-independent; only the depth matters.
    Returns (turn records, final history) - the history feeds the
    same-depth noise samples, which must ride it: the slot cache
    reuses only the longest common token prefix."""
    history = []
    results = []
    if blob:
        history.append({"role": "user", "content": blob})
        history.append({"role": "assistant", "content": "Understood."})
    for i, question in enumerate(user_turns):
        history.append({"role": "user", "content": question})
        payload = {
            "messages": list(history),
            "max_tokens": (cap_tokens + THINK_ALLOWANCE)
                           if thinking else cap_tokens,
            "temperature": 0,
            "stream": False,
        }
        if no_thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        wall_start = time.time()
        data = llama_server.post_json(port, "/v1/chat/completions", payload)
        wall_s = time.time() - wall_start

        message = data["choices"][0]["message"]
        answer = message.get("content") or ""
        reasoning = message.get("reasoning_content") or ""
        history.append({"role": "assistant", "content": answer})

        t = data.get("timings", {})
        server_tps = t.get("predicted_per_second")
        n_pred = t.get("predicted_n",
                       data.get("usage", {}).get("completion_tokens"))
        prompt_ms = t.get("prompt_ms")

        # External cross-check: generation span = wall time minus prefill
        ext_gen_s = wall_s - (prompt_ms / 1000.0) if prompt_ms else wall_s
        ext_tps = (n_pred / ext_gen_s) if (n_pred and ext_gen_s > 0) else None

        # depth estimate: the blob is already inside the history, so
        # count its chars once (as the exact tokenized blob_tokens)
        blob_chars = len(blob) if blob else 0
        history_chars = sum(len(m["content"]) for m in history[:-1])
        depth_tokens = blob_tokens + (history_chars - blob_chars) // 4

        # Protocol v2.1: the guarantee is anchored in WORDS per second
        # (300 wpm = 5.0 w/s, Brysbaert 2019). t/s was always a
        # derivative via the 0.75 words/token rule of thumb - the
        # honest instrument measures both, from the generated text
        # itself: words = whitespace tokens of the answer, w/s =
        # words / generation span (wall minus prefill - the same
        # span the external cross-check uses).
        answer_words = len(answer.split()) if answer.strip() else 0
        gen_span_s = ext_gen_s if (ext_gen_s and ext_gen_s > 0) else None
        words_per_sec = (answer_words / gen_span_s
                         if (answer_words and gen_span_s) else None)

        results.append({
            "turn": i + 1,
            "depth_tokens_est": depth_tokens,
            "blob_tokens": blob_tokens,
            "gen_tokens": n_pred,
            "gen_words": answer_words,
            "server_tps": server_tps,
            "server_wps": words_per_sec,
            "words_per_token": ((answer_words / n_pred)
                                if (answer_words and n_pred) else None),
            "ext_tps": ext_tps,
            "wall_tps": (n_pred / wall_s) if (n_pred and wall_s) else None,
            "prompt_ms": prompt_ms,
            "wall_s": wall_s,
            "reasoning_chars": len(reasoning),
            "thinking_tokens_est": len(reasoning) // 4,
            "answer_empty": 1 if not answer.strip() else 0,
        })
    return results, history


NOISE_PROMPT = ("Reply with a single paragraph about the weather "
                 "(roughly sixty words).")
NOISE_TOKENS = 128       # decode span per noise sample; small enough
                         # to fit the worst-case-full history
NOISE_MIN_ROOM = 24      # below this remaining budget, skip: the
                         # history fills the context (Session 27,
                         # addendum 16: 299 cap on a full history
                         # -> prompt + n_predict over ctx -> 400,
                         # which killed the whole run)


def noise_sample(port, history, cap_tokens, ctx_tokens, blob_tokens=0,
                 thinking=False, no_thinking=False, samples=2):
    """Same-depth noise samples: a short follow-up appended to the
    conversation's own history. The follow-up MUST ride the history:
    llama-server's slot cache reuses only the longest common token
    PREFIX of the incoming prompt, so a bare tiny message shares only
    the template prefix, re-prefills at ~zero depth, and measures
    shallow decode - not noise at depth (caught on the first real
    v2.1 run: the "noise" sat consistently ABOVE the conversation
    turns, the fingerprint of a shallower decode). With the full
    history + a final turn, the common prefix covers the whole
    cached conversation, only the tail prefills, and decode runs at
    the conversation's depth. Worst/mean across these is the
    machine's noise at depth - cleanly separated from the KV trend
    (addendum 10).

    Room guard: the blob budget is worst-case (every answer at the
    cap), so after the last turn the history is at the budget - a
    full-cap generation on top overflows ctx and the server rejects
    the request with 400. The noise generation is therefore capped
    small (NOISE_TOKENS) and skipped with a note when the remaining
    room is gone. A failed request is recorded, never raised: the
    noise measurement must not kill the run (the addendum-16 crash
    lost three conversations of collected turns)."""
    est = blob_tokens + sum(len(m["content"]) for m in history) // 4
    room = ctx_tokens - est
    if room < NOISE_MIN_ROOM:
        print(f"      noise at depth: skipped (history fills the "
              f"context: ~{est} of {ctx_tokens} tokens, room {room})")
        return []
    noise_cap = max(8, min(NOISE_TOKENS, room - 8))
    msgs = list(history) + [{"role": "user", "content": NOISE_PROMPT}]
    recs = []
    for i in range(1, samples + 1):
        payload = {
            "messages": msgs,
            "max_tokens": noise_cap,
            "temperature": 0,
            "stream": False,
        }
        if no_thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        try:
            data = llama_server.post_json(port, "/v1/chat/completions",
                                           payload)
        except Exception as e:
            print(f"      noise sample {i} failed: {e}")
            recs.append({"sample": i, "error": str(e)})
            continue
        t = data.get("timings", {})
        tps = t.get("predicted_per_second")
        pm = t.get("prompt_ms")
        msg = data["choices"][0]["message"]
        ans = (msg.get("content") or "").strip()
        ans_words = len(ans.split()) if ans else 0
        n_pred = t.get("predicted_n")
        gen_span = ((data.get("timings", {}).get("predicted_ms") or 0)
                    / 1000.0)
        wps = (ans_words / gen_span
               if (ans_words and gen_span > 0) else None)
        recs.append({
            "sample": i,
            "prompt_n": t.get("prompt_n"),
            "prompt_ms": pm,
            "gen_tokens": n_pred,
            "gen_words": ans_words,
            "tps": tps,
            "wps": wps,
            "words_per_token": ((ans_words / n_pred)
                                if (ans_words and n_pred) else None),
        })
    return recs


def bench_model(model, corpus_file, port, ctx, repeats,
               thinking=False, no_thinking=False, server_bin=None,
               label=None):
    """Live-bench one model end to end (server launch included).
    Protocol v2: per-conversation depth prefill to the reference
    depth, worst turn across all depth-conditioned turns, plus the
    same-depth noise samples. Returns (all_turns, summary)."""
    with open(corpus_file) as f:
        corpus = json.load(f)
    conversations = corpus["conversations"]
    cap_tokens = corpus["answer_cap_tokens"]
    label = label or model.split("/")[-1]

    print(f"\n=== {label} ===")
    all_turns = []
    noise_records = []
    repeat_worsts = []
    for rep in range(1, repeats + 1):
        print(f"  [rep {rep}/{repeats}] starting server...", flush=True)
        extra = ["-ngl", "99", "-c", str(ctx)]
        if thinking:
            extra += ["--reasoning-format", "deepseek"]
        if no_thinking:
            extra += ["--chat-template-kwargs",
                      '{"enable_thinking": false}']
        proc, healthy = llama_server.start_server(model, port, extra,
                                                  server_bin)
        try:
            if not healthy:
                print("  ERROR: server did not become healthy; skipping")
                continue
            pool = "\n\n".join(t for c in conversations for t in c["user_turns"])
            conv_worsts = []
            for ci, conv in enumerate(conversations, 1):
                budget = depth_budget(conv["user_turns"], cap_tokens, ctx,
                                      thinking)
                blob, blob_tokens = build_blob(port, pool, budget)
                if blob is None:
                    print(f"    conv {ci}: no blob budget left "
                          f"(conversation alone fills the context - run "
                          "at the shallower reference depth as-is)")
                res, conv_history = run_conversation(
                    port, conv["user_turns"], cap_tokens, ctx, thinking,
                    no_thinking, blob, blob_tokens)
                for r in res:
                    all_turns.append({"model": label, "conv": ci, **r})
                tps = [r["server_tps"] for r in res if r["server_tps"]]
                wps = [r["server_wps"] for r in res if r["server_wps"]]
                cworst = min(tps) if tps else None
                cmean = sum(tps) / len(tps) if tps else None
                conv_worsts.append(cworst)
                print(f"    conv {ci} (blob {blob_tokens} tok): turns t/s: "
                      + ", ".join(f"{x:.1f}" for x in tps)
                      + (f"   worst {cworst:.1f} (mean {cmean:.1f})"
                         if cworst else ""))
                if wps:
                    print(f"      words/s: "
                          + ", ".join(f"{x:.1f}" for x in wps)
                          + f"   (reader line {READER_WPS_DEFAULT:g} w/s)")
                if thinking:
                    tk = [r["thinking_tokens_est"] for r in res]
                    empt = sum(r["answer_empty"] for r in res)
                    print("      thinking tokens: "
                          + ", ".join(str(x) for x in tk)
                          + (f"   ({empt} empty answer(s))"
                             if empt else ""))
                if (not thinking and res
                        and not any(r.get("gen_words") for r in res)):
                    print("      WARNING: every answer this conversation "
                          "was EMPTY - words/s cannot be measured. A "
                          "hybrid model in default mode thinks first; "
                          "pass --no-thinking (non-thinking) or "
                          "--thinking (thinking, with the 2048 allowance)")
                noise = noise_sample(port, conv_history, cap_tokens,
                                     ctx, blob_tokens, thinking,
                                     no_thinking)
                for r in noise:
                    noise_records.append({"model": label, "conv": ci, **r})
                ntps = [r["tps"] for r in noise if r["tps"]]
                if ntps:
                    print(f"      noise at depth: "
                          + ", ".join(f"{x:.1f}" for x in ntps))
        finally:
            llama_server.stop_server(proc, port)
        valid = [w for w in conv_worsts if w]
        if valid:
            rep_worst = min(valid)
            repeat_worsts.append(rep_worst)
            rep_mean_of_worsts = sum(valid) / len(valid)
            print(f"  rep {rep}: conversation worsts -> "
                  + ", ".join(f"{x:.1f}" for x in valid)
                  + f"   [rep worst {rep_worst:.1f}, "
                    f"avg-of-worsts {rep_mean_of_worsts:.1f}]")

    summary = None
    if repeat_worsts:
        worst = min(repeat_worsts)
        avg_worsts = sum(repeat_worsts) / len(repeat_worsts)
        print(f"\n  {label}: WORST TURN = {worst:.1f} t/s "
              f"(min of {len(repeat_worsts)} reps; "
              f"avg-of-rep-worsts {avg_worsts:.1f})")
        summary = (label, worst, avg_worsts)
    if noise_records:
        ntps = [r["tps"] for r in noise_records if r.get("tps")]
        if ntps:
            nw = min(ntps)
            nm = sum(ntps) / len(ntps)
            print(f"  {label}: NOISE AT DEPTH: worst {nw:.2f}  mean {nm:.2f}"
                  f"  worst/mean {nw / nm:.3f}  (n={len(ntps)})")
    return all_turns, summary


# =========================================================== dump + verdict

def live_dump_name(path, thinking=False, no_thinking=False):
    """Mode-suffixed dump name: a thinking-mode dump must NEVER be reused
    by a non-thinking run (or vice versa) - the resume check compares
    timestamps only, so the mode must live in the filename (Session 25
    bug: --no-thinking run inherited thinking-mode dumps and reported
    the thinking gate numbers as its own)."""
    if thinking:
        return path + ".live-dump.think.json"
    if no_thinking:
        return path + ".live-dump.nothink.json"
    return path + ".live-dump.json"


def bench(path, corpus, dry_run, thinking=False, no_thinking=False,
          port=PORT_DEFAULT, ctx=CTX_DEFAULT, repeats=REPEATS_DEFAULT,
          dump_override=None):
    """Phase 3: live-bench the model file; returns the dump path."""
    dump = dump_override or live_dump_name(path, thinking, no_thinking)
    label = os.path.basename(path)

    def dump_valid():
        if not os.path.isfile(dump):
            return False
        try:
            with open(dump) as f:
                turns = json.load(f)
        except Exception:
            return False
        return any(t.get("model") == label and t.get("server_tps")
                   for t in turns)

    if dump_valid() and os.path.getmtime(dump) > os.path.getmtime(path):
        print("  [3] reusing existing dump (newer than model file)")
        return dump
    if dry_run:
        return dump
    turns, _ = bench_model(path, corpus, port, ctx, repeats,
                           thinking, no_thinking, label=label)
    with open(dump, "w") as f:
        json.dump(turns, f, indent=1)
    if not dump_valid():
        fail(3, label, "live bench produced no usable dump "
             "(see the output above)", GUIDE[3])
    return dump


def analyze(path, floor, thinking=False, no_thinking=False,
            dump_override=None,
            reader_wps=READER_WPS_DEFAULT,
            words_per_token_default=WORDS_PER_TOKEN_DEFAULT):
    """Phase 4: the guarantee verdict from the dump.

    Protocol v2.1 (author catch, Session 27): t/s is not w/s. The
    guarantee's anchor is a READER: 300 wpm = 5.0 words per second
    (Brysbaert 2019) - words, not tokens. The verdict is computed in
    WORDS per second, measured from the generated text itself
    (whitespace words / generation span). The token-side line
    (6.5 t/s = 5.0 w/s / 0.75 words-per-token) is printed for
    continuity, but it is a derivative: a tokenizer with a lower
    words/token ratio fails the READER while passing 6.5 t/s, and the
    honest instrument must not let that pass. For dumps without
    measured w/s (protocol-v1 data), the verdict converts via the
    dump's own words/token when present, else the 0.75 default -
    flagged as unanchored in the result.

    Floor 20 t/s (k=3) stays a HEADROOM column, never the verdict.
    """
    dump = dump_override or live_dump_name(path, thinking, no_thinking)
    label = os.path.basename(path)
    try:
        with open(dump) as f:
            turns = json.load(f)
    except Exception as e:
        fail(4, label, f"cannot read dump: {e}", GUIDE[4])
    mine = [t for t in turns
            if t.get("model") == label and t.get("server_tps")]
    if not mine:
        fail(4, label, "dump has no turns for this model", GUIDE[4])

    # measured words/token across the dump (v2.1 turns carry it)
    ratios = [t["words_per_token"] for t in mine
              if t.get("words_per_token")]
    wpt = (sum(ratios) / len(ratios)) if ratios else words_per_token_default
    wpt_measured = bool(ratios)

    def turn_wps(t):
        if t.get("server_wps") is not None:
            return t["server_wps"]
        return t["server_tps"] * wpt

    convs = {}
    for t in mine:
        convs.setdefault(t["conv"], []).append(turn_wps(t))
    conv_worsts = [min(v) for v in convs.values()]
    worst_wps = min(conv_worsts)
    mean_wps = sum(turn_wps(t) for t in mine) / len(mine)
    if len(conv_worsts) > 1:
        mu = sum(conv_worsts) / len(conv_worsts)
        sd = math.sqrt(sum((w - mu) ** 2 for w in conv_worsts)
                       / (len(conv_worsts) - 1))
        sigma = sd / math.sqrt(len(conv_worsts))
    else:
        sigma = 0.0
    threshold = reader_wps - 2 * sigma
    if worst_wps >= reader_wps:
        verdict = "PASS (confident)"
    elif worst_wps >= threshold:
        verdict = "PASS (within 2-sigma)"
    else:
        verdict = "FAIL"
    # token-side view: continuity + the law's currency + headroom
    worst_tps = min(t["server_tps"] for t in mine)
    mean_tps = sum(t["server_tps"] for t in mine) / len(mine)
    headroom = "intact" if worst_tps >= floor else "below floor (k=3)"
    return {"worst": worst_wps, "mean": mean_wps, "sigma": sigma,
            "threshold": threshold, "verdict": verdict,
            "reader_wps": reader_wps,
            "words_per_token": wpt,
            "words_per_token_measured": wpt_measured,
            "worst_tps": worst_tps, "mean_tps": mean_tps,
            "floor": floor, "headroom": headroom,
            "n_turns": len(mine), "n_convs": len(conv_worsts),
            "dump": dump}


# =========================================================== CLI

def main():
    ap = argparse.ArgumentParser(
        description="speed gate: live-bench a model and grade the worst "
                    "turn against the floor (absorbs the former "
                    "live-bench.py)")
    ap.add_argument("--model", help=".gguf file to bench")
    ap.add_argument("--corpus", default=CORPUS_DEFAULT)
    ap.add_argument("--floor", type=float, default=FLOOR_DEFAULT,
                    help="the k=3 headroom line (t/s), reported not "
                         "gated (protocol v2)")
    ap.add_argument("--reader-wps", type=float, default=READER_WPS_DEFAULT,
                    help=f"the k=1 guarantee line in WORDS per second "
                         f"(default {READER_WPS_DEFAULT} w/s = 300 wpm, "
                         f"Brysbaert 2019 - match the fast reader; the "
                         f"t/s line is this divided by words/token)")
    ap.add_argument("--dump", default=None,
                    help="live-dump path override (default: next to the "
                         "model file, mode-suffixed)")
    ap.add_argument("--port", type=int, default=PORT_DEFAULT)
    ap.add_argument("--ctx", type=int, default=CTX_DEFAULT)
    ap.add_argument("--repeats", type=int, default=REPEATS_DEFAULT,
                    help="qualifying tier default: 1 rep; use 3 for final "
                         "podium numbers")
    ap.add_argument("--thinking", action="store_true",
                    help="thinking mode (category protocol, rule 8)")
    ap.add_argument("--no-thinking", action="store_true",
                    help="hybrid model, non-thinking category (rule 8)")
    ap.add_argument("--dry-run", action="store_true")
    # corpus-building steps (from the former live-bench.py)
    ap.add_argument("--make-sample", action="store_true",
                    help="step 0 (once): English extraction from Arena "
                         "parquet shards")
    ap.add_argument("--make-corpus", action="store_true",
                    help="step 1 (once): build the fixed corpus from "
                         "english_sample.json")
    ap.add_argument("--corpus-out", default=CORPUS_DEFAULT)
    ap.add_argument("--n-conversations", type=int, default=5)
    ap.add_argument("--min-turns", type=int, default=4)
    ap.add_argument("--max-turns", type=int, default=8)
    ap.add_argument("--max-cap-tokens", type=int, default=300)
    args = ap.parse_args()

    if args.thinking and args.no_thinking:
        ap.error("--thinking and --no-thinking are mutually exclusive")

    if args.make_sample:
        make_english_sample()
        return
    if args.make_corpus:
        make_corpus(SAMPLE_OUT, args.corpus_out, args.n_conversations,
                    args.min_turns, args.max_turns, args.max_cap_tokens)
        return

    if not args.model:
        ap.error("--model is required (or use --make-sample/--make-corpus)")
    if not args.dry_run and not os.path.isfile(args.model):
        sys.exit(f"model file not found: {args.model}")
    if not args.dry_run and not os.path.isfile(args.corpus):
        sys.exit(f"corpus not found at {args.corpus} - build it: "
                 "python3 speed_gate.py --make-corpus")

    dump = bench(args.model, args.corpus, args.dry_run, args.thinking,
                 args.no_thinking, args.port, args.ctx, args.repeats,
                 args.dump)
    if args.dry_run:
        print(f"[4] would analyze (reader line {args.reader_wps:g} w/s "
              f"- 2*sigma; floor {args.floor:g} t/s as headroom)")
        return
    res = analyze(args.model, args.floor, args.thinking, args.no_thinking,
                  args.dump, args.reader_wps)
    print(f"\nper-turn results written to {dump}")
    print(f"[4] worst {res['worst']:.2f} w/s "
          f"(mean {res['mean']:.2f}, sigma {res['sigma']:.2f}, "
          f"guarantee threshold {res['threshold']:.2f} w/s) "
          f"-> {res['verdict']}")
    print(f"    token-side view: worst {res['worst_tps']:.1f} t/s "
          f"(mean {res['mean_tps']:.1f}); words/token "
          f"{res['words_per_token']:.3f}"
          + (" (measured)" if res["words_per_token_measured"]
             else " (0.75 default, unanchored)"))
    print(f"    headroom vs floor {args.floor:g} t/s: {res['headroom']}")


if __name__ == "__main__":
    main()
