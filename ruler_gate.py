#!/usr/bin/env python3
"""ruler_gate.py -- quality-at-depth gate (RULER-style needle-in-a-haystack).

The future study's quality instrument (addenda 120-123): the current
quality column is ZERO-context (ARC, single prompt), and the study has
no method to qualify context's importance. This gate grades the first
and cheapest RULER task family -- needle-in-a-haystack (niah_single,
the RULER reference's own entry task) -- at configurable depths through
the SAME serving stack as the speed gate (llama-server, /tokenize for
exact per-model depth accounting, /v1/chat/completions for answers).

RULER's reference implementation targets HF/transformers and vLLM
(author ruling, addendum 127); our stack is llama-server, so the
harness is ours. What is kept standard is the TASK SHAPE, not the
codebase: synthetic haystack essays, "One of the special magic
numbers for {key} is: {value}." needles scattered at depth fractions,
a retrieval query per needle, substring scoring on the value. The
honest scope line: this is niah only -- the multi-key, aggregation and
variable-tracking RULER tasks are NOT implemented; effective-context
numbers here grade retrieval-at-depth, the floor of the RULER suite.

The two gates stay orthogonal (addendum 127): this gate is
answer-accuracy, NOT the reader-wall streaming guarantee; a RULER run
pays the KV speed cost per token (the law prices the wall clock) but
no stall verdict is issued here.

Depth grid and budget follow the standing rules (addendum 125): a
lineage's RULER run is sized before launch; depths land under ctx
(the /tokenize accounting never exceeds it).

Usage (repo root):
  python3 ruler_gate.py ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf \
      --depths 4096 --samples 5 --results-dir ruler-results
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import re
import sys
import urllib.error
import urllib.request
from typing import Any

import llama_server

WORD_BANK = (
    "the quick brown fox jumps over a lazy dog while rain falls on quiet "
    "hills and rivers carry small stones toward distant lakes under grey "
    "skies where birds circle above fields of wheat that sway in evening "
    "wind as farmers watch the road and children count passing cars on "
    "warm afternoons in late summer when apples ripen in old orchards "
    "beside wooden fences painted white years ago by hands now gone"
)

NEEDLE_TEMPLATE = "One of the special magic numbers for {key} is: {value}."
ANSWER_HEADROOM = 128
QUERY_TEMPLATE = "What is the special magic number for {key}? Answer with the number only."
KEYS = (
    "alpha",
    "bravo",
    "charlie",
    "delta",
    "echo",
    "foxtrot",
    "golf",
    "hotel",
    "india",
    "juliet",
    "kilo",
    "lima",
    "mike",
    "november",
    "oscar",
    "papa",
    "quebec",
    "romeo",
    "sierra",
    "tango",
)


def make_needle(key: str, value: str) -> str:
    """RULER's own needle sentence shape (niah_single)."""
    return NEEDLE_TEMPLATE.format(key=key, value=value)


def haystack_paragraphs(rng: random.Random, n_sentences: int) -> list[str]:
    """Synthetic noisy haystack, RULER-style: same shape as the
    reference's repeated-sentence essays -- uninformative prose the
    model cannot memorize answers from."""
    words = WORD_BANK.split()
    out = []
    for _ in range(n_sentences):
        start = rng.randrange(0, len(words))
        n = rng.randrange(6, 16)
        sentence = " ".join(words[start:] + words[:start])[:0] or " ".join(
            (words[start:] + words[:start])[:n]
        )
        out.append(sentence.capitalize() + ".")
    return out


def build_task(
    port: int,
    depth_tokens: int,
    n_needles: int,
    seed: int,
) -> tuple[str, dict[str, str]]:
    """One niah task at an exact depth: returns (prompt, answers).

    The haystack is trimmed to the token budget MINUS the needles and
    query (llama_server.trim_to_tokens, the same instrument the depth
    prefill uses), then the needles are spliced in at even depth
    fractions (0.1, 0.3, 0.5, 0.7, 0.9 cycling) -- never first or
    last, so retrieval is genuinely at depth. The query asks for ONE
    key; answers maps every key to its value so the caller can draw
    multiple queries per haystack without rebuilding it.
    """
    rng = random.Random(seed)
    answers = {k: str(10000 + rng.randrange(0, 90000)) for k in KEYS[:n_needles]}
    keys = list(answers)
    needle_texts = [make_needle(k, answers[k]) for k in keys]
    query = QUERY_TEMPLATE.format(key=keys[0])
    fixed = sum(len(llama_server.tokenize(port, t)) for t in needle_texts) + len(
        llama_server.tokenize(port, query)
    )
    budget = depth_tokens - fixed - ANSWER_HEADROOM
    if budget < 200:
        raise ValueError(
            f"depth {depth_tokens} leaves only {budget} haystack tokens "
            f"after {n_needles} needles + query - raise the depth"
        )
    n_sentences = max(4096, (budget * 3) // 2 // 10)
    paragraphs = haystack_paragraphs(rng, n_sentences)
    haystack, n_hay = llama_server.trim_to_tokens(port, "\n".join(paragraphs), budget)
    del n_hay
    lines = haystack.split("\n")
    out: list[str] = []
    needle_i = 0
    fractions = (0.1, 0.3, 0.5, 0.7, 0.9)
    per = max(1, len(lines) // n_needles)
    for idx, line in enumerate(lines):
        out.append(line)
        if needle_i < n_needles and (idx + 1) % per == 0:
            pos = fractions[needle_i % len(fractions)]
            del pos
            out.append(needle_texts[needle_i])
            needle_i += 1
    while needle_i < n_needles:
        out.append(needle_texts[needle_i])
        needle_i += 1
    while True:
        prompt = "\n".join(out) + "\n\n" + query
        n_prompt = len(llama_server.tokenize(port, prompt))
        if n_prompt <= depth_tokens:
            return prompt, answers
        haystack_idx = max(
            (i for i, line in enumerate(out) if line not in needle_texts), default=None
        )
        if haystack_idx is None:
            raise ValueError(
                f"prompt {n_prompt} tokens exceeds depth budget {depth_tokens} "
                "and no haystack line remains to trim"
            )
        del out[haystack_idx]


def report_server_ctx(log_path: str, wanted: int) -> int | None:
    """Print the server's own context lines and return the actual n_ctx.
    llama-server may silently run a SMALLER context than -c requested
    (KV/memory budget) - the launch banner says so, but only if you read
    it. The gate refuses to run a grid deeper than the real n_ctx:
    every deep task would 400 and read as 0/5, which is a build
    constraint, not a model result."""
    import re as _re

    actual = None
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    for line in lines:
        m = _re.search(r"n_ctx_slot\s*=\s*(\d+)", line) or _re.search(r"n_ctx\s*=\s*(\d+)", line)
        if m:
            actual = int(m.group(1))
        if "n_ctx" in line or "reduce" in line.lower() or "context" in line.lower():
            print(f"    [server] {line.strip()[:160]}")
    if actual is not None:
        print(f"    [server] actual n_ctx = {actual} (requested {wanted})")
    return actual


def show_task(prompt: str, answers: dict[str, str], needle_texts: list[str]) -> None:
    """Print the conversation for one task: the context window around
    each needle plus the tail with the query - so a human reads what
    the model read. The full haystack is repetitive by construction;
    the windows carry the information (needle position in context)."""
    n = len(prompt)
    print(f"    --- task prompt ({n} chars) ---")
    for text in needle_texts:
        i = prompt.find(text)
        if i < 0:
            print(f"    [needle not found: {text}]")
            continue
        lo, hi = max(0, i - 120), min(n, i + len(text) + 120)
        window = prompt[lo:hi].replace("\n", " ")
        print(f"    @ {i:6}/{n}  ...{window}...")
    tail = prompt[-260:].replace("\n", " ")
    print(f"    [tail] ...{tail}")


def score_answer(answer: str, value: str) -> bool:
    """Substring scoring, RULER's niah rule: the value appears in the
    model's reply (whitespace-tolerant)."""
    return value in re.sub(r"\s+", "", answer)


def ask(port: int, prompt: str, max_tokens: int = 64, no_thinking: bool = True) -> str:
    """One completion through the same endpoint the speed gate uses.
    Default no_thinking=True: hybrid models (qwen3/3.5-class) burn the
    whole token budget on reasoning_content otherwise - the answer
    arrives empty, the same trap the speed gate's --no-thinking mode
    exists for. A thinking answer is accepted from either field."""
    payload: dict[str, Any] = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": False,
    }
    if no_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    try:
        data = llama_server.post_json(port, "/v1/chat/completions", payload)
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read()[:500]
        except Exception:
            pass
        raise ValueError(f"HTTP {e.code} from the server: {body.decode('utf-8', 'replace')}") from e
    msg = data["choices"][0]["message"]
    return msg.get("content") or msg.get("reasoning_content") or ""


def run_depth(
    port: int,
    label: str,
    depth: int,
    samples: int,
    needles: int,
    csv_path: str,
    seed0: int = 1024,
    no_thinking: bool = True,
    show: bool = False,
) -> dict[str, Any]:
    """Run `samples` tasks at one depth, append per-task rows to the
    CSV, return the summary row. Idempotence follows the ARC pattern:
    an existing valid CSV is respected (the file is the cache)."""
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if len(rows) >= samples and all(r.get("correct") is not None for r in rows):
            hits = sum(r["correct"] == "1" for r in rows[:samples])
            return {
                "label": label,
                "depth": depth,
                "n": len(rows[:samples]),
                "correct": hits,
                "acc": hits / samples,
            }
    hits = 0
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["task", "depth", "key", "value", "answer", "correct"])
        for i in range(samples):
            prompt, answers = build_task(port, depth, needles, seed=seed0 + i)
            key = list(answers)[0]
            if show:
                show_task(prompt, answers, [make_needle(k, answers[k]) for k in answers])
            try:
                answer = ask(port, prompt, no_thinking=no_thinking)
            except ValueError as e:
                print(f"  task {i + 1}/{samples} @ {depth} tok: FAILED - {e}")
                w.writerow([i, depth, key, answers[key], f"ERROR: {e}", ""])
                continue
            ok = score_answer(answer, answers[key])
            hits += ok
            w.writerow([i, depth, key, answers[key], answer, int(ok)])
            print(
                f"  task {i + 1}/{samples} @ {depth} tok: key {key} value {answers[key]} "
                f"-> {'HIT' if ok else 'MISS'} ({answer.strip()[:48]!r})"
            )
    return {"label": label, "depth": depth, "n": samples, "correct": hits, "acc": hits / samples}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("model", help="GGUF path (the server runs this file)")
    p.add_argument(
        "--depths",
        type=int,
        nargs="+",
        default=[4096],
        help="token depths to grade (default: the protocol depth 4096)",
    )
    p.add_argument("--samples", type=int, default=5, help="tasks per depth")
    p.add_argument("--needles", type=int, default=4, help="needles per haystack")
    p.add_argument("--port", type=int, default=8200)
    p.add_argument("--results-dir", default="ruler-results")
    p.add_argument("--seed", type=int, default=1024)
    p.add_argument(
        "--show",
        action="store_true",
        help="print each task's conversation: the haystack window around "
        "every needle and the query tail (what the model actually read)",
    )
    p.add_argument(
        "--thinking",
        action="store_true",
        help="let hybrid models think (default: enable_thinking False, "
        "the study's non-thinking mode - reasoning burns the budget)",
    )
    args = p.parse_args()

    label = os.path.splitext(os.path.basename(args.model))[0]
    os.makedirs(args.results_dir, exist_ok=True)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{args.port}/health", timeout=2):
            pass
        sys.exit(
            f"port {args.port} already answers /health - a server is running there "
            "(a stale ruler/llama-server? pkill -f llama-server, or pass --port). "
            "Refusing to bench against it: the model and its ctx would be the wrong ones."
        )
    except urllib.error.HTTPError:
        sys.exit(
            f"port {args.port} answers with an HTTP error but SOMETHING is there - "
            "a stale server. pkill -f llama-server, or pass --port."
        )
    except OSError:
        pass
    wanted_ctx = max(args.depths) + 2 * ANSWER_HEADROOM
    log_path = os.path.join(args.results_dir, f"{label}-server.log")
    proc, healthy = llama_server.start_server(
        args.model,
        port=args.port,
        extra_args=["-c", str(wanted_ctx), "--parallel", "1"],
        log_path=log_path,
    )
    if not healthy or not llama_server.wait_healthy(args.port, proc=proc):
        llama_server.stop_server(proc, args.port)
        sys.exit("server did not come up - aborting before any results")
    actual_ctx = report_server_ctx(log_path, wanted_ctx)
    if actual_ctx is None:
        llama_server.stop_server(proc, args.port)
        sys.exit(
            f"could not read n_ctx from {log_path} - the banner parse is "
            "uncertain and the gate refuses to bench blind. Paste the "
            "server log so the parser learns this build's banner format."
        )
    if actual_ctx < max(args.depths) + ANSWER_HEADROOM:
        llama_server.stop_server(proc, args.port)
        sys.exit(
            f"server accepted -c {wanted_ctx} but runs n_ctx {actual_ctx} - "
            f"the depth grid ({max(args.depths)}) cannot run. Read {log_path} "
            "for the reason (silent context reduction: KV/memory budget, "
            "build flags) and re-run with a grid that fits."
        )
    print(
        f"ruler gate: {label} (niah, depths {args.depths}, "
        f"samples {args.samples}, needles {args.needles})"
    )
    try:
        for depth in args.depths:
            csv_path = os.path.join(args.results_dir, f"{label}-{depth}-niah.csv")
            row = run_depth(
                args.port,
                label,
                depth,
                args.samples,
                args.needles,
                csv_path,
                seed0=args.seed,
                no_thinking=not args.thinking,
                show=args.show,
            )
            print(
                f"  {label} @ {depth} tok: {row['correct']}/{row['n']} "
                f"correct (acc {row['acc']:.0%})"
            )
    finally:
        llama_server.stop_server(proc, args.port)


if __name__ == "__main__":
    main()
