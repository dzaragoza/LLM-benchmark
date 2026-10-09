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
    the anchor reader - 5.0 w/s = 300 wpm (k=1, Brysbaert 2019;
    addenda 2-6, restated in words/s by protocol v2.1) - so even a
    fast reader is never made to wait. (The k=3 floor-20 headroom
    line is deleted, addendum 50.)
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
  - The reader-wall collision simulation (addendum 55) is recorded
    per turn as DIAGNOSTIC DATA (stall rate, catch-up seconds).
    Verdict (protocol v4.x, addendum 37): strictly worst wps >= the
    reader line; the stall rate is data, never a gate.
    first PASS = selected - which, at the reader line, walks the
    ladder to the TOP rung that still guarantees the reader (the old
    floor-20 gate was a headroom judgment and rejected rungs the
    guarantee admits).

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
    python3 speed_gate.py --model ./models/A/A-Q6_K.gguf
    python3 speed_gate.py --model <file> --thinking
    python3 speed_gate.py --model <file> --no-thinking
    python3 speed_gate.py --make-sample     # step 0 (once)
    python3 speed_gate.py --make-corpus     # step 1 (once)

Imported by full_benchmark.py (bench, analyze, live_dump_name).
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import random
import sys
import time
import urllib.error
from typing import Any, NoReturn

import infra.llama_server as llama_server
from ruler_gate import report_server_ctx

CORPUS_DEFAULT = "./data/live-corpus-cal50.json"
READER_WPS_DEFAULT = 5.0  # k=1 guarantee line, WORDS/s: 300 wpm fast
# reader (Brysbaert 2019). Protocol v2.1:
# the anchor is words, not tokens.

READER_REACTION_S = 0.45  # reader reaction time, s: 0.25 s simple visual RT
# + 0.20 s saccade latency (Carpenter 1988;
# addendum 31). Protocol v3.0: part of the
# guarantee's verdict (the reader-wall test),
# single-sourced here - session_replicate
# imports it.
PORT_DEFAULT = 8077
CTX_DEFAULT = 4096
DEPTH_HEADROOM = 64
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
        "if the bench was interrupted, delete the dump and rerun (phase 3 will redo it)",
    ],
}


def fail(phase: int, rung: str, what: str, causes: list[str]) -> NoReturn:
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


def make_english_sample(n_sample: int = 5000) -> None:
    import pyarrow.parquet as pq

    files = sorted(glob.glob(os.path.join(ARENA_DIR, "**", "*.parquet"), recursive=True))
    if not files:
        sys.exit(
            f"No parquet found under {ARENA_DIR}. Download the "
            "lmsys-chat-1m dataset first (see README)."
        )
    english = []
    for f in files:
        table = pq.read_table(f)
        for row in table.to_pylist():
            # lmsys-chat-1m schema: conversation_id, model, language, turn,
            # conversation: [{"role": "user"/"assistant", "content": ...}]
            if (row.get("language") or "").lower().startswith("english"):
                english.append(
                    {
                        "conversation": row["conversation"],
                        "turn": row.get("turn"),
                    }
                )
    random.seed(SEED)
    random.shuffle(english)
    sample = english[:n_sample]
    with open(SAMPLE_OUT, "w") as f:
        json.dump(sample, f)
    print(f"{len(english)} English conversations; wrote {len(sample)}-conv sample -> {SAMPLE_OUT}")


def make_corpus(
    arena_file: str,
    out_file: str,
    n_conversations: int,
    min_turns: int,
    max_turns: int,
    max_cap_tokens: int,
) -> None:
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
    import hashlib

    selected.sort(key=lambda c: hashlib.sha256(json.dumps(c["user_turns"]).encode()).hexdigest())
    corpus = selected[:n_conversations]

    reply_chars.sort()
    p75 = reply_chars[int(0.75 * (len(reply_chars) - 1))] if reply_chars else 1200
    cap_tokens = min(max_cap_tokens, max(64, int(p75 / 4)))

    out = {
        "source": "LMSYS Chatbot Arena (lmsys-chat-1m), English sample, seed 1024",
        "selection": (
            f"{len(corpus)} conversations, {min_turns}-{max_turns} "
            "user turns, English, no URLs, turns 1-4000 chars, "
            "deterministic sha256 order"
        ),
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


def depth_budget(user_turns: list[str], cap_tokens: int, ctx: int, thinking: bool = False) -> int:
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
        conv_side += (cap_tokens + THINK_ALLOWANCE) if thinking else cap_tokens
    # the noise measurement is protocol, not an afterthought: its
    # request (message + template wrappers + decode span) rides the
    # SAME worst-case-full history as the last turn, so its room is
    # reserved in the blob budget - not hoped for afterward (conv 3
    # of the addendum-22 run: max-length conversation, 64-token
    # headroom, noise needs ~224 -> 400 twice, fence held, samples
    # lost). Reserved = the full noise request's rendered size.
    reserve = NOISE_OVERHEAD + NOISE_TOKENS
    budget = ctx - DEPTH_HEADROOM - reserve - conv_side
    return max(0, budget)


def build_blob(port: int, pool: str, budget: int) -> tuple[str | None, int]:
    """Depth-prefill blob for one conversation: repeated corpus text
    trimmed to the exact per-model token budget via /tokenize."""
    if budget <= 0:
        return None, 0
    reps = budget * 8 // max(1, len(pool)) + 2
    text = "\n\n".join([pool] * reps)
    return llama_server.trim_to_tokens(port, text, budget)


def reader_wall_test(
    deltas: list[dict[str, Any]],
    n_words: int,
    reader_wps: float = READER_WPS_DEFAULT,
    reaction_s: float = READER_REACTION_S,
) -> dict[str, Any]:
    """The guarantee's verdict, protocol v3.0 (author ruling, addendum
    55): simulate the reader on the per-word arrival stream - the
    registered addendum-30 collision model, exact form. The reader
    starts reading reaction_s after the first word arrives and reads
    at reader_wps; the turn FAILS iff the reader EVER hits the wall
    (catches up with printing mid-answer - any word arrives after
    the reader is ready for it, not just the last). A stream the
    reader finishes inside his reaction window can never fail: it
    is read like a static message. deltas = [{"t": absolute arrival
    time, "w": cumulative words}] - one entry per stream delta,
    final entry = stream end. Returns the collision record
    (catchup_events > 0 = FAIL)."""
    if not deltas or n_words == 0:
        return {"catchup_events": 0, "catchup_s": 0.0, "first_catchup_word_frac": None}
    t_first = deltas[0]["t"]
    t_read = t_first + reaction_s
    pos = 0.0
    events, total, first_frac = 0, 0.0, None
    waiting_prev = False
    for i in range(len(deltas) - 1):
        t_i, p = deltas[i]["t"], deltas[i]["w"]
        t_next = deltas[i + 1]["t"]
        s = max(t_i, t_read)
        if t_next <= s:
            continue
        if pos >= p - 1e-9:
            total += t_next - s
            if not waiting_prev:
                events += 1
                if first_frac is None:
                    first_frac = p / n_words
            waiting_prev = True
        else:
            advance = reader_wps * (t_next - s)
            if pos + advance >= p:
                t_reach = s + (p - pos) / reader_wps
                total += t_next - t_reach
                if not waiting_prev:
                    events += 1
                    if first_frac is None:
                        first_frac = p / n_words
                waiting_prev = True
            else:
                waiting_prev = False
            pos = min(p, pos + advance)
    return {
        "catchup_events": events,
        "catchup_s": round(total, 2),
        "first_catchup_word_frac": round(first_frac, 3) if first_frac is not None else None,
    }


def run_conversation(
    port: int,
    user_turns: list[str],
    cap_tokens: int,
    ctx_tokens: int,
    thinking: bool = False,
    no_thinking: bool = False,
    blob: str | None = None,
    blob_tokens: int = 0,
    reader_wps: float | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Protocol v2: the conversation runs ON TOP of the depth prefill.
    The blob is a prepended user turn, so the chat template wraps it,
    cache_prompt retains it turn-to-turn, and every generated turn is
    depth-conditioned at the reference depth. Timing (like KV cost) is
    content-independent; only the depth matters.
    Returns (turn records, final history) - the history feeds the
    same-depth noise samples, which must ride it: the slot cache
    reuses only the longest common token prefix.
    Protocol v3.1 (addendum 73): turns run STREAMING; a turn
    stalls the reader iff the reader EVER hits the wall (any word
    late, not just the last - the registered addendum-30 collision
    simulation on the per-word arrival stream). Stalling turns are
    flagged `reader_wall_fail` and carry their collision record in
    the dump; the conversation ALWAYS runs to completion (the
    verdict is the stall rate - aborting at the first stall would
    truncate the denominator and bias the rate downward). The old
    span-based w/s stays a diagnostic (the addendum-54 tiny-answer
    degeneracy: a 5-token answer's span is overhead, not reading
    experience)."""
    history = []
    results = []
    if blob:
        history.append({"role": "user", "content": blob})
        history.append({"role": "assistant", "content": "Understood."})
    for i, question in enumerate(user_turns):
        history.append({"role": "user", "content": question})
        payload: dict[str, Any] = {
            "messages": list(history),
            "max_tokens": (cap_tokens + THINK_ALLOWANCE) if thinking else cap_tokens,
            "temperature": 0,
            "stream": True,
        }
        if no_thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": False}

        # Protocol v3.0: stream the answer, recording per-word
        # arrivals - the raw input of the reader-wall test (the
        # non-streaming span could not see a mid-stream wall at all)
        meta = {}
        pieces, times, words = [], [], []
        wall_start = time.time()
        for text, t_arr in llama_server.stream_completion(port, payload, meta=meta):
            pieces.append(text)
            times.append(t_arr)
            words.append(len("".join(pieces).split()))
        wall_s = time.time() - wall_start
        answer = "".join(pieces)
        history.append({"role": "assistant", "content": answer})

        t = meta.get("timings", {})
        server_tps = t.get("predicted_per_second")
        n_pred = t.get("predicted_n", meta.get("usage", {}).get("completion_tokens"))
        prompt_ms = t.get("prompt_ms")
        prompt_n = t.get("prompt_n")

        # External cross-check: generation span = wall time minus prefill
        ext_gen_s = wall_s - (prompt_ms / 1000.0) if prompt_ms else wall_s
        ext_tps = (n_pred / ext_gen_s) if (n_pred and ext_gen_s > 0) else None

        # depth estimate: the blob is already inside the history, so
        # count its chars once (as the exact tokenized blob_tokens)
        blob_chars = len(blob) if blob else 0
        history_chars = sum(len(m["content"]) for m in history[:-1])
        depth_tokens = blob_tokens + (history_chars - blob_chars) // 4

        # Diagnostics (v2.1 fields, kept): words = whitespace tokens
        # of the answer; span w/s = words / generation span. NOT the
        # verdict since v3.0 - see the addendum-54 degeneracy note.
        answer_words = len(answer.split()) if answer.strip() else 0
        gen_span_s = ext_gen_s if (ext_gen_s and ext_gen_s > 0) else None
        words_per_sec = answer_words / gen_span_s if (answer_words and gen_span_s) else None

        # The verdict (protocol v3.0): simulate the reader on the
        # arrival stream - the registered addendum-30 collision
        # model. deltas carry cumulative words at each word-arrival
        # (token deltas that complete no word are collapsed); waits
        # count only BETWEEN arrivals: once the last word has
        # landed the reader finishes from the buffer, so a reader
        # still behind at stream end is NOT a fail (the answer is
        # complete - this is exactly session_replicate's model). A
        # late LAST word still fails: its lateness is a wait in the
        # interval before it lands, which the loop sees.
        if times:
            deltas = [{"t": 0.0, "w": words[0]}]
            for t_arr, w in zip(times[1:], words[1:], strict=True):
                if w != deltas[-1]["w"]:
                    deltas.append({"t": round(t_arr - times[0], 4), "w": w})
            collision = reader_wall_test(
                deltas, answer_words, reader_wps or READER_WPS_DEFAULT, READER_REACTION_S
            )
        else:
            deltas = []
            collision = {"catchup_events": 0, "catchup_s": 0.0, "first_catchup_word_frac": None}

        reasoning = meta.get("reasoning") or ""
        rec = {
            "turn": i + 1,
            "depth_tokens_est": depth_tokens,
            "prompt_n": prompt_n,
            "blob_tokens": blob_tokens,
            "gen_tokens": n_pred,
            "gen_words": answer_words,
            "server_tps": server_tps,
            "server_wps": words_per_sec,
            "words_per_token": ((answer_words / n_pred) if (answer_words and n_pred) else None),
            "ext_tps": ext_tps,
            "wall_tps": (n_pred / wall_s) if (n_pred and wall_s) else None,
            "prompt_ms": prompt_ms,
            "wall_s": wall_s,
            "reasoning_chars": len(reasoning),
            "thinking_tokens_est": len(reasoning) // 4,
            "answer_empty": 1 if not answer.strip() else 0,
            "ttft_s": ((times[0] - wall_start) if times else None),
            "catchup_events": collision["catchup_events"],
            "catchup_s": collision["catchup_s"],
            "first_catchup_word_frac": collision["first_catchup_word_frac"],
            "reader_wall_fail": (1 if collision["catchup_events"] else 0),
            "deltas": deltas,
        }
        results.append(rec)
        if reader_wps is not None and rec["reader_wall_fail"]:
            print(
                f"      turn {i + 1} FAILED THE READER WALL - the reader "
                f"hit the stream {collision['catchup_events']}x "
                f"(waited {collision['catchup_s']:.2f}s) - continuing "
                "(the verdict is the stall rate, protocol v3.1 - the "
                "conversation always runs to completion; early-fail is "
                "deleted, addendum 73)",
                flush=True,
            )
    return results, history


NOISE_PROMPT = "Reply with a single paragraph about the weather (roughly sixty words)."
NOISE_TOKENS = 128  # decode span per noise sample; small enough
# to fit the worst-case-full history
NOISE_MIN_ROOM = 24  # below this remaining budget, skip: the
# history fills the context (Session 27,
# addendum 16: 299 cap on a full history
# -> prompt + n_predict over ctx -> 400,
# which killed the whole run)
NOISE_OVERHEAD = 96  # rendered noise message + template wrappers
# + generation header, server-measured
# prompt_n + this = the exact next-prompt size
# (32 was too tight: qwen3.5's template adds
# ~60+ rendered tokens of wrappers; conv 3 of
# the addendum-21 run 400'd both samples)


def noise_sample(
    port: int,
    history: list[dict[str, str]],
    cap_tokens: int,
    ctx_tokens: int,
    blob_tokens: int = 0,
    thinking: bool = False,
    no_thinking: bool = False,
    samples: int = 2,
    last_prompt_n: int | None = None,
    last_gen_tokens: int | None = None,
) -> list[dict[str, Any]]:
    """Same-depth noise samples: a short follow-up appended to the
    conversation's own history. The follow-up MUST ride the history:
    llama-server's slot cache reuses only the longest common token
    PREFIX of the incoming prompt, so a bare tiny message shares only
    the template prefix, re-prefills at ~zero depth, and measures
    shallow decode - not noise at depth (caught on the first real
    v2.1 run: the "noise" sat consistently ABOVE the conversation
    turns, the fingerprint of a shallower decode). With the full
    history + a final turn, the common prefix covers the whole cached
    conversation, only the tail prefills, and decode runs at the
    conversation's depth. Worst/mean across these is the machine's
    noise at depth - cleanly separated from the KV trend (addendum 10).

    Room guard (exact): the next request's prompt is the last turn's
    rendered prompt + its generated answer + the noise message and
    template wrappers - all measured server-side, so the room is
    known exactly from the last turn's own timings.prompt_n (the
    chars/4 fallback estimate is kept only for dumps/servers that
    report no prompt_n; it over-counted qwen3.5 by ~500 tokens and
    skipped noise samples whose turns ran fine at the cap). A failed
    request is recorded, never raised; the noise measurement must
    not kill the run (the addendum-16 crash lost three
    conversations of collected turns)."""
    blob_chars = len(history[0]["content"]) if (blob_tokens and history) else 0
    hist_chars = sum(len(m["content"]) for m in history)
    if last_prompt_n is not None:
        est = last_prompt_n + (last_gen_tokens or 0) + NOISE_OVERHEAD
    else:
        # conservative fallback: max of the two readings (the blob
        # normally IS history[0]; if it is not, the plain chars/4
        # sum is the honest depth estimate)
        est = max(blob_tokens + (hist_chars - blob_chars) // 4, hist_chars // 4)
    room = ctx_tokens - est
    if room < NOISE_MIN_ROOM:
        print(
            f"      noise at depth: skipped (history fills the "
            f"context: ~{est} of {ctx_tokens} tokens, room {room})"
        )
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
        data = None
        for attempt in (1, 2, 3):
            try:
                data = llama_server.post_json(port, "/v1/chat/completions", payload)
                break
            except Exception as e:
                if attempt < 3 and noise_cap > 8:
                    # 400 with room to spare means the overhead
                    # estimate was tight - halve and retry
                    noise_cap = max(8, noise_cap // 2)
                    payload["max_tokens"] = noise_cap
                    print(f"      noise sample {i}: retrying with max_tokens {noise_cap} ({e})")
                    continue
                print(f"      noise sample {i} failed: {e}")
                recs.append({"sample": i, "error": str(e)})
                break
        if data is None:
            continue
        t = data.get("timings", {})
        tps = t.get("predicted_per_second")
        pm = t.get("prompt_ms")
        msg = data["choices"][0]["message"]
        ans = (msg.get("content") or "").strip()
        ans_words = len(ans.split()) if ans else 0
        n_pred = t.get("predicted_n")
        gen_span = (data.get("timings", {}).get("predicted_ms") or 0) / 1000.0
        wps = ans_words / gen_span if (ans_words and gen_span > 0) else None
        recs.append(
            {
                "sample": i,
                "prompt_n": t.get("prompt_n"),
                "prompt_ms": pm,
                "gen_tokens": n_pred,
                "gen_words": ans_words,
                "tps": tps,
                "wps": wps,
                "words_per_token": ((ans_words / n_pred) if (ans_words and n_pred) else None),
            }
        )
    return recs


def _dump_log_tail(log_path: str, lines: int = 15) -> None:
    """session 35, addendum 5: a server that never becomes healthy died
    at argument parsing or model load - the reason is in its log, and
    the log stays local unless we print it (the addendum-33 lesson:
    never leave the diagnosis on the author's disk)."""
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            tail = f.read().splitlines()[-lines:]
    except OSError:
        return
    if tail:
        print(f"  --- server log tail ({log_path}) ---")
        for ln in tail:
            print(f"  [server] {ln}")


def bench_model(
    model: str,
    corpus_file: str,
    port: int,
    ctx: int,
    thinking: bool = False,
    no_thinking: bool = False,
    server_bin: str | None = None,
    label: str | None = None,
    reader_wps: float | None = None,
    n_conversations: int | None = None,
    conversation_start: int = 0,
    kv_quant_k: str | None = None,
    kv_quant_v: str | None = None,
    log_dir: str | None = None,
) -> tuple[list[dict[str, Any]], tuple[str, float, float] | None, list[dict[str, Any]]]:
    """Live-bench one model end to end (server launch included).
    Protocol v2: per-conversation depth prefill to the reference
    depth, worst turn across all depth-conditioned turns, plus the
    same-depth noise samples. Returns (all_turns, summary).
    Protocol v4.x (addendum 37): the verdict is strictly worst
    wps >= the reader line; the collision simulation is recorded
    per turn as diagnostic data. Every conversation always runs to
    completion (early-fail would truncate the record)."""
    with open(corpus_file) as f:
        corpus = json.load(f)
    conversations = corpus["conversations"]
    if n_conversations is not None or conversation_start:
        end = conversation_start + (n_conversations or len(conversations))
        conversations = conversations[conversation_start:end]
    cap_tokens = corpus["answer_cap_tokens"]
    label = label or model.split("/")[-1]

    print(f"\n=== {label} ===")
    all_turns = []
    noise_records = []
    mem_reports = []
    # addendum 60: the server log lives in log_dir (the results tree)
    # when given - deleting a models/<family> directory then touches
    # only regenerable data; the model dir stays weights-only.
    log_dir = log_dir or (os.path.dirname(model) or ".")
    log_path = os.path.join(log_dir, os.path.basename(model) + ".server.log")
    print("  starting server...", flush=True)
    extra = ["-ngl", "99", "-c", str(ctx), "--parallel", "1"]
    # session 35, addendum 8: K and V quantize SEPARATELY (the
    # combined option is GONE - author ruling); a None leaves that
    # cache at the default f16. Quantized caches need the FA kernels,
    # and this build's -fa TAKES A VALUE (on|off|auto) - "-fa on"
    # (the crashed witness runs passed bare "-fa" and the server ate
    # --cache-type-k as its value).
    if kv_quant_k or kv_quant_v:
        extra += ["-fa", "on"]
        if kv_quant_k:
            extra += ["--cache-type-k", kv_quant_k]
        if kv_quant_v:
            extra += ["--cache-type-v", kv_quant_v]
    if thinking:
        extra += ["--reasoning-format", "deepseek"]
    if no_thinking:
        extra += ["--chat-template-kwargs", '{"enable_thinking": false}']
    proc, healthy = llama_server.start_server(model, port, extra, server_bin, log_path=log_path)
    try:
        if not healthy:
            print("  ERROR: server did not become healthy; skipping")
            _dump_log_tail(log_path)
            return all_turns, None, mem_reports
        actual_ctx = report_server_ctx(log_path, ctx)
        if actual_ctx is None:
            print(
                "  ERROR: could not read n_ctx from the server banner - "
                "the gate refuses to bench blind (addendum 130e); "
                f"see {log_path}"
            )
            return all_turns, None, mem_reports
        if actual_ctx < ctx:
            print(
                f"  ERROR: server accepted -c {ctx} but runs n_ctx "
                f"{actual_ctx} (slots/cap silently reduced it, "
                "addendum 130e/130f) - the depth budget would "
                "overflow and every deep turn would 400; see "
                f"{log_path}"
            )
            return all_turns, None, mem_reports
        pool = "\n\n".join(t for c in conversations for t in c["user_turns"])
        conv_worsts = []
        for ci, conv in enumerate(conversations, 1 + conversation_start):
            budget = depth_budget(conv["user_turns"], cap_tokens, ctx, thinking)
            blob, blob_tokens = build_blob(port, pool, budget)
            if blob is None:
                print(
                    f"    conv {ci}: no blob budget left "
                    f"(conversation alone fills the context - run "
                    "at the shallower reference depth as-is)"
                )
            try:
                res, conv_history = run_conversation(
                    port,
                    conv["user_turns"],
                    cap_tokens,
                    ctx,
                    thinking,
                    no_thinking,
                    blob,
                    blob_tokens,
                    reader_wps=reader_wps,
                )
            except urllib.error.HTTPError as e:
                # session 34 (addendum 31): the rung is below the
                # conversation's floor - the conversation alone (plus
                # template + answer room) exceeds ctx and llama-server
                # rejects the whole prompt with 400. This is STRUCTURAL,
                # not a model verdict: the family must not die on it
                # (the addendum-29 acquisition deaths: granite-4.0-350m
                # and phi-1_5 died on the FIRST turn's 400).
                if e.code == 400 and blob is None:
                    print(
                        f"    conv {ci}: HTTP 400 with no blob budget - "
                        f"the rung ({ctx}) is below the conversation "
                        "floor (structural, not a model verdict)"
                    )
                    return (
                        [
                            {
                                "turn": 0,
                                "ctx": ctx,
                                "error": "rung below conversation floor",
                                "http_error": 400,
                            }
                        ],
                        None,
                        mem_reports,
                    )
                raise
            for r in res:
                all_turns.append({"model": label, "conv": ci, "ctx": ctx, **r})
            tps = [r["server_tps"] for r in res if r["server_tps"]]
            wps = [r["server_wps"] for r in res if r["server_wps"]]
            evts = [r.get("catchup_events") or 0 for r in res]
            cwait = [r.get("catchup_s") or 0.0 for r in res]
            cworst = min(tps) if tps else None
            cmean = sum(tps) / len(tps) if tps else None
            conv_worsts.append(cworst)
            print(
                f"    conv {ci} (blob {blob_tokens} tok): turns t/s: "
                + ", ".join(f"{x:.1f}" for x in tps)
                + (f"   worst {cworst:.1f} (mean {cmean:.1f})" if cworst else "")
            )
            print(
                "      reader wall (catch-up events): "
                + ", ".join(str(e) for e in evts)
                + (
                    f"   [reader waited {max(cwait):.2f}s on the worst turn]"
                    if max(cwait) > 0
                    else "   [reader never waited]"
                )
            )
            if wps:
                line = reader_wps if reader_wps is not None else READER_WPS_DEFAULT
                print(
                    "      words/s (diagnostic): "
                    + ", ".join(f"{x:.1f}" for x in wps)
                    + f"   (reader line {line:g} w/s)"
                )
            if thinking:
                tk = [r["thinking_tokens_est"] for r in res]
                empt = sum(r["answer_empty"] for r in res)
                print(
                    "      thinking tokens: "
                    + ", ".join(str(x) for x in tk)
                    + (f"   ({empt} empty answer(s))" if empt else "")
                )
            if not thinking and res and not any(r.get("gen_words") for r in res):
                print(
                    "      WARNING: every answer this conversation "
                    "was EMPTY - words/s cannot be measured. A "
                    "hybrid model in default mode thinks first; "
                    "pass --no-thinking (non-thinking) or "
                    "--thinking (thinking, with the 2048 allowance)"
                )
            try:
                noise = noise_sample(
                    port,
                    conv_history,
                    cap_tokens,
                    ctx,
                    blob_tokens,
                    thinking,
                    no_thinking,
                    last_prompt_n=res[-1].get("prompt_n"),
                    last_gen_tokens=res[-1].get("gen_tokens"),
                )
            except Exception as e:
                print(
                    f"      noise collection failed for conv {ci}: "
                    f"{e} (recorded, conversation kept)"
                )
                noise = [{"sample": 0, "error": str(e)}]
            for r in noise:
                noise_records.append({"model": label, "conv": ci, "ctx": ctx, **r})
            ntps = [r["tps"] for r in noise if r.get("tps")]
            if ntps:
                print("      noise at depth: " + ", ".join(f"{x:.1f}" for x in ntps))

    finally:
        breakdown = llama_server.memory_breakdown_gib(log_path)
        llama_server.stop_server(proc, port)
        if breakdown is not None:
            mem_reports.append(
                {
                    "rep": 1,
                    **breakdown,
                }
            )
            print(
                f"    memory (llama): weights {breakdown['weights_gib']:.2f} GiB, "
                f"context {breakdown['context_gib']:.2f} GiB, "
                f"compute {breakdown['compute_gib']:.2f} GiB"
                f" -> total {breakdown['total_gib']:.2f} GiB (addendum 11)",
                flush=True,
            )
    wall_hits = sum(1 for t in all_turns if t.get("reader_wall_fail"))
    if wall_hits:
        print(
            f"  note: {wall_hits} wall-failing turn(s) recorded - "
            "the verdict is the stall rate (protocol v3.1, "
            "addendum 73; recomputed from deltas at analyze time)",
            flush=True,
        )
    valid = [w for w in conv_worsts if w]
    summary = None
    if valid:
        worst = min(valid)
        avg_worsts = sum(valid) / len(valid)
        print(
            f"\n  {label}: WORST TURN = {worst:.1f} t/s "
            f"(worst turn; avg-of-worsts {avg_worsts:.1f})"
        )
        summary = (label, worst, avg_worsts)
    if noise_records:
        ntps = [float(r["tps"]) for r in noise_records if r.get("tps")]
        if ntps:
            nw = min(ntps)
            nm = sum(ntps) / len(ntps)
            print(
                f"  {label}: NOISE AT DEPTH: worst {nw:.2f}  mean {nm:.2f}"
                f"  worst/mean {nw / nm:.3f}  (n={len(ntps)})"
            )
    if mem_reports:
        totals = [
            float(v) for m in mem_reports if isinstance(v := m.get("weights_gib"), (int, float))
        ]
        if totals:
            print(
                f"  {label}: MEMORY (llama): weights {max(totals):.2f} GiB "
                f"- file {os.path.getsize(model) / (1024**3):.2f} GiB (addendum 11)"
            )
    return all_turns, summary, mem_reports


# =========================================================== dump + verdict


def live_dump_name(path: str, thinking: bool = False, no_thinking: bool = False) -> str:
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


def analyze(
    path: str,
    thinking: bool = False,
    no_thinking: bool = False,
    dump_override: str | None = None,
    reader_wps: float = READER_WPS_DEFAULT,
) -> dict[str, Any]:
    """Phase 4: the guarantee verdict from the dump.

    Protocol v2.1 (author catch, Session 27): t/s is not w/s. The
    guarantee's anchor is a READER: 300 wpm = 5.0 words per second
    (Brysbaert 2019) - words, not tokens. The verdict is computed in
    WORDS per second, measured from the generated text itself
    (whitespace words / generation span). The token-side view
    (worst t/s, mean words/token) is printed for continuity, but it
    is a derivative: a tokenizer with a lower words/token ratio
    fails the READER while passing a t/s line, and the honest
    instrument must not let that pass.
    Addendum 44 (author ruling): a dump with turns lacking measured
    w/s (protocol-v1 data, pre-v2.1) can no longer be verdicted via
    the 0.75 words/token rule of thumb - the fallback is DELETED;
    analyze fails loudly so the rung is re-benched (--force) and every
    verdict comes from measured words.

    Floor 20 t/s (k=3) stays a HEADROOM column, never the verdict.
    """
    dump = dump_override or live_dump_name(path, thinking, no_thinking)
    label = os.path.basename(path)
    try:
        with open(dump) as f:
            turns = json.load(f)
    except Exception as e:
        fail(4, label, f"cannot read dump: {e}", GUIDE[4])
    mine = [t for t in turns if t.get("model") == label and t.get("server_tps")]
    if not mine:
        fail(4, label, "dump has no turns for this model", GUIDE[4])

    # measured words/token across the dump (v2.1 turns carry it)
    ratios = [t["words_per_token"] for t in mine if t.get("words_per_token")]
    wpt = (sum(ratios) / len(ratios)) if ratios else None
    wpt_measured = bool(ratios)
    # the w/t calibration view (addendum 58): per-turn w/t sorted,
    # the min and the 5th percentile are the family anchor candidates
    sorted_ratios = sorted(ratios)
    if sorted_ratios:
        k = max(0, math.ceil(0.05 * len(sorted_ratios)) - 1)
        wpt_p05 = sorted_ratios[k]
    else:
        wpt_p05 = None

    # addendum 44: the 0.75 fallback is deleted; a v1 dump (turns
    # without measured w/s) cannot be verdicted - re-bench instead.
    legacy = [t for t in mine if t.get("server_wps") is None]
    if legacy:
        fail(
            4,
            label,
            f"dump has {len(legacy)} turn(s) without measured w/s "
            "(protocol-v1 data; the 0.75 words/token fallback is "
            "deleted, addendum 44) - re-bench with --force to "
            "measure words per second with the v2.1 instrument",
            GUIDE[4],
        )
    # Protocol v3.0 (addendum 55): the verdict is the reader-wall
    # test, which needs the per-word arrival stream - a dump whose
    # turns carry no deltas (pre-v3.0) cannot be verdicted; re-bench.
    no_stream = [t for t in mine if "deltas" not in t]
    if no_stream:
        fail(
            4,
            label,
            f"dump has {len(no_stream)} turn(s) without per-word "
            "arrival deltas (pre-v3.0 data; the verdict needs the "
            "arrival stream, addenda 55/73) - re-bench with "
            "--force to record the arrival stream",
            GUIDE[4],
        )

    # Protocol v3.1 (addendum 73): the verdict is the STALL RATE -
    # the registered addendum-30 collision simulation on each
    # turn's arrival stream, RECOMPUTED HERE from the dump's raw
    # deltas (so a dump can be re-graded post-hoc at any reader
    # speed, like session_replicate's resim mode; the bench-time
    # flags were computed with the same defaults). A turn stalls
    # iff the reader EVER hit the wall (any catch-up event); the
    # stall rate kept as data, not a gate (v4.x, addendum 37). The
    # flat w/s comparison stays a diagnostic only: it manufactured
    # fails on tiny answers (the addendum-54 degeneracy - the span
    # of a 5-token answer is pipeline overhead, not reading
    # experience).
    wall_fails = []
    total_catchup_events = 0
    worst_catchup_s = 0.0
    for t in mine:
        col = reader_wall_test(
            t.get("deltas") or [], t.get("gen_words") or 0, reader_wps, READER_REACTION_S
        )
        t["catchup_events"], t["catchup_s"] = (col["catchup_events"], col["catchup_s"])
        t["first_catchup_word_frac"] = col["first_catchup_word_frac"]
        t["reader_wall_fail"] = 1 if col["catchup_events"] else 0
        if col["catchup_events"]:
            wall_fails.append(t)
        total_catchup_events += col["catchup_events"]
        worst_catchup_s = max(worst_catchup_s, col["catchup_s"] or 0.0)
    # Protocol v3.1 (addendum 73): the guarantee is the STALL RATE -
    # stall rate is recorded per turn as diagnostic data.
    stall_rate = round(len(wall_fails) / len(mine), 4) if mine else 0.0

    def turn_wps(t: dict[str, Any]) -> float:
        return t["server_wps"]

    convs = {}
    for t in mine:
        convs.setdefault(t["conv"], []).append(turn_wps(t))
    conv_worsts = [min(v) for v in convs.values()]
    worst_wps = min(conv_worsts)
    # Protocol v4.x (session 41, addendum 37): the verdict is STRICTLY
    # wps >= the reader line - the stall rate is data, not a gate.
    verdict = "PASS (confident)" if worst_wps >= reader_wps else "FAIL"
    mean_wps = sum(turn_wps(t) for t in mine) / len(mine)
    if len(conv_worsts) > 1:
        mu = sum(conv_worsts) / len(conv_worsts)
        sd = math.sqrt(sum((w - mu) ** 2 for w in conv_worsts) / (len(conv_worsts) - 1))
        sigma = sd / math.sqrt(len(conv_worsts))
    else:
        sigma = 0.0
    threshold = reader_wps - 2 * sigma
    # Protocol v3.0: the flat-w/s numbers below stay DIAGNOSTICS
    # (the spread of conversation worsts; sigma as before). The
    # verdict is settled above by the reader-wall test.
    worst_tps = min(t["server_tps"] for t in mine)
    mean_tps = sum(t["server_tps"] for t in mine) / len(mine)
    return {
        "worst": worst_wps,
        "mean": mean_wps,
        "sigma": sigma,
        "threshold": threshold,
        "verdict": verdict,
        "stall_rate": stall_rate,
        "wall_fail_turns": len(wall_fails),
        "catchup_events": total_catchup_events,
        "worst_catchup_s": worst_catchup_s,
        "reader_wps": reader_wps,
        "words_per_token": wpt,
        "words_per_token_measured": wpt_measured,
        "worst_tps": worst_tps,
        "mean_tps": mean_tps,
        "words_per_token_min": (min(ratios) if ratios else None),
        "words_per_token_p05": wpt_p05,
        "n_turns": len(mine),
        "n_convs": len(conv_worsts),
        "dump": dump,
    }


# =========================================================== CLI


def main() -> None:
    """The corpus-building CLI (protocol v4.x, session 41 addendum 37:
    the bench path is the CELLS' library - bench_model/analyze are
    called by bench/cells.py inside the certify controllers, never a
    standalone sweep. The CLI stays for the one thing that may be
    needed again: building a LARGER corpus."""
    ap = argparse.ArgumentParser(
        description="speed_gate: the measurement library + the corpus "
        "builder (the bench path is bench/cells.py's library)"
    )
    ap.add_argument(
        "--make-sample",
        action="store_true",
        help="step 0 (once): English extraction from Arena parquet shards",
    )
    ap.add_argument(
        "--make-corpus",
        action="store_true",
        help="step 1 (once): build the fixed corpus from english_sample.json",
    )
    ap.add_argument("--corpus-out", default=CORPUS_DEFAULT)
    # addendum 185: the winner's certification defaults - 20 conversations,
    # PASS at >= 15/20 stall-free (the author's 2-sigma ruling)
    ap.add_argument("--n-conversations", type=int, default=20)
    ap.add_argument("--min-turns", type=int, default=4)
    ap.add_argument("--max-turns", type=int, default=8)
    ap.add_argument("--max-cap-tokens", type=int, default=300)
    args = ap.parse_args()
    if args.make_sample:
        make_english_sample()
        return
    if args.make_corpus:
        make_corpus(
            SAMPLE_OUT,
            args.corpus_out,
            args.n_conversations,
            args.min_turns,
            args.max_turns,
            args.max_cap_tokens,
        )
        return
    ap.error("nothing to do - use --make-sample or --make-corpus")


if __name__ == "__main__":
    main()
