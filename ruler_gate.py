#!/usr/bin/env python3
"""ruler_gate.py -- quality-at-depth gate (RULER-style FWE).

The study's quality instrument: RULER's frequent-words-extraction
(Challenge tier) graded at configurable depths through the SAME
serving stack as the speed gate (llama-server, /tokenize for exact
per-model depth accounting, /v1/chat/completions for answers).
The original niah_single task is REMOVED (session 37, addendum 3):
FWE superseded it - every quality verdict since addendum 136b is FWE.
A task passes at >= 1/3 expected words (session 37, addendum 2); the
per-word count is the graded 0..k diagnostic.

The two gates stay orthogonal (addendum 127): this gate is
answer-accuracy, NOT the reader-wall streaming guarantee.

Depth grid and budget follow the standing rules (addendum 125): a
lineage's run is sized before launch; depths land under ctx (the
/tokenize accounting never exceeds it).

Usage (repo root):
  python3 ruler_gate.py ./models/Qwen3.5-4B/Qwen3.5-4B-Q8_0.gguf \\
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
import tee_output

ANSWER_HEADROOM = 128
QUERY_TEMPLATE = "What is the special magic number for {key}? Answer with the number only."

# --- FWE (frequent-words extraction, RULER's aggregation Challenge tier,
# addendum 136b) --- upstream constants: NVIDIA/RULER
# scripts/data/synthetic/freq_words_extraction.py @ main, verbatim:
# coded_wordlen 6, vocab_size = depth/50 (when -1), alpha 2.0 (zeta),
# rank-0 word is the '...' noise word, answer = ranks 1-3, query asks for
# the THREE most frequent words, tokens_to_generate 50.
FWE_TEMPLATE = (
    "Read the following coded text and track the frequency of each coded "
    "word. Find the three most frequently appeared coded words. {context}\n"
    "Question: Do not provide any explanation. Please ignore the dots "
    "'....'. What are the three most frequently appeared words in the "
    "above coded text?"
)
FWE_CODED_WORDLEN = 6
FWE_ALPHA = 2.0
FWE_TOP_K = 3
FWE_GEN_TOKENS = 128
FWE_PASS_MIN = 1


def zeta(alpha: float, k: int) -> float:
    """Riemann zeta, the normalizer of the Zipf/Zeta count law (scipy's
    zeta is upstream's; stdlib-only here - k stays small so the tail
    cutoff loses nothing material)."""
    return sum(1.0 / (i**alpha) for i in range(1, k + 1))


def build_fwe_task(
    port: int,
    depth_tokens: int,
    seed: int,
    top_k: int = FWE_TOP_K,
) -> tuple[str, list[str]]:
    """One FWE task at ~depth_tokens: returns (prompt, top_k_words).

    Faithful to upstream's generate_input_output: a synthetic vocab of
    depth/50 six-letter words, counts drawn from the Zeta law
    count(w_rank) = num_words * rank^-alpha / zeta(alpha), rank 0 the
    '...' noise word, rank 1-3 the answer, the whole list shuffled and
    joined with spaces. The prompt is trimmed to the token budget the
    with llama_server.trim_to_tokens; trims slice from the
    END, preserving the head's instruction - and a trim never changes
    the answer, because counts scale with rank, not position.
    """
    import string

    rng = random.Random(seed)
    vocab_size = max(20, depth_tokens // 50)
    vocab: list[str] = []
    seen: set[str] = set()
    while len(vocab) < vocab_size:
        w = "".join(rng.choices(string.ascii_lowercase, k=FWE_CODED_WORDLEN))
        if w not in seen:
            seen.add(w)
            vocab.append(w)
    vocab[0] = "..."
    norm = zeta(FWE_ALPHA, len(vocab))
    budget = depth_tokens - ANSWER_HEADROOM
    # Token-budget by construction, not by character arithmetic (the
    # 136d bug: coded words are gibberish to the tokenizer - ~2-3
    # tokens per 6-letter word - so `depth // 6` words ran every cell
    # at ~40-50% of the requested depth and the whole feel run was
    # void). Probe with /tokenize and scale the word count like
    # upstream's incremental loop: measure a fixed sample, extrapolate
    # linearly, then trim-verify - one probe per task, not per guess.
    probe_words = 2000
    probe = " ".join(
        "".join(rng.choices(string.ascii_lowercase, k=FWE_CODED_WORDLEN))
        for _ in range(probe_words)
    )
    probe_n = len(llama_server.tokenize(port, probe))
    tokens_per_word = max(1.0, probe_n / probe_words)
    num_words = int(budget / tokens_per_word)
    while True:
        counts = [int(num_words * (r + 1) ** -FWE_ALPHA / norm) for r in range(len(vocab))]
        words: list[str] = []
        for w, c in zip(vocab, counts, strict=True):
            words.extend([w] * c)
        rng.shuffle(words)
        body = " ".join(words)
        prompt_full = FWE_TEMPLATE.format(context=body)
        prompt, n_tok = llama_server.trim_to_tokens(port, prompt_full, budget)
        if n_tok >= budget * 0.9:
            break
        # the trim came in short (probe noise) - grow the word list and retry
        num_words = int(num_words * budget / max(1, n_tok))
    return prompt, vocab[1 : 1 + top_k]


TEMPLATE_DEBRIS = re.compile(r"<\|[^|>]{1,32}\>|<\[/[^>]{1,32}\]>|\[INST\]|\[/INST\]")


def strip_template_debris(answer: str) -> str:
    """Remove chat-template special tokens the model emitted as literal
    text (session 34, addendum 29/30: granite-4.0-h-350m answered
    literally '<|im_end|>'; the author's ruling 1a - the reply is still
    correct, the token is launch noise, not part of the answer)."""
    return TEMPLATE_DEBRIS.sub("", answer)


def score_fwe(
    answer: str, top_k: list[str], min_words: int = FWE_PASS_MIN
) -> tuple[bool, int]:
    """Upstream scores FWE as the hit-count of expected words in the
    reply. The verdict threshold is CONFIGURABLE (session 37,
    addendum 9: measure once at k=3, grade at any threshold later):
    a task passes when >= min_words of the expected words are found
    (default 1, the addendum-2 relaxation; 3 is the original strict
    form). The per-word count remains the graded 0..k diagnostic.
    Template debris is stripped first (ruling 1a, addendum 30)."""
    clean = strip_template_debris(answer)
    found = [w for w in top_k if w in re.sub(r"\s+", "", clean)]
    return len(found) >= min_words, len(found)


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


def run_fwe_depth(
    port: int,
    label: str,
    depth: int,
    samples: int,
    csv_path: str,
    seed0: int = 1024,
    no_thinking: bool = True,
    show: bool = False,
    top_k: int = FWE_TOP_K,
    min_words: int = FWE_PASS_MIN,
) -> dict[str, Any]:
    """FWE cells: same shape as run_depth (CSV cache, per-task rows,
    ERROR rows continue the sweep), verdict >= 1/3 words per task
    (session 37, addendum 2) with the per-word partial credit as the
    diagnostic (registered 136b)."""
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if len(rows) >= samples and all(r.get("correct") is not None for r in rows):
            hits = sum(
                (int(r["partial"]) if r.get("partial") not in (None, "") else int(r["correct"]))
                >= min_words
                for r in rows[:samples]
            )
            partials = [
                int(r["partial"])
                for r in rows[:samples]
                if r.get("partial") not in (None, "")
            ]
            return {
                "label": label,
                "depth": depth,
                "n": len(rows[:samples]),
                "correct": hits,
                "acc": hits / samples,
                "words_found": partials,
            }
    hits = 0
    partial_list: list[int] = []
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["task", "depth", "top_k", "partial", "answer", "correct"])
        for i in range(samples):
            prompt, top_k = build_fwe_task(port, depth, seed=seed0 + i, top_k=top_k)
            if show:
                print(f"    --- task prompt head: {prompt[:160]!r}")
                print(f"    expected top-{FWE_TOP_K}: {top_k}")
            try:
                answer = ask(port, prompt, max_tokens=FWE_GEN_TOKENS, no_thinking=no_thinking)
            except ValueError as e:
                print(f"  task {i + 1}/{samples} @ {depth} tok: FAILED - {e}")
                w.writerow([i, depth, ";".join(top_k), "", f"ERROR: {e}", ""])
                continue
            ok, partial = score_fwe(answer, top_k, min_words)
            hits += ok
            partial_list.append(partial)
            w.writerow([i, depth, ";".join(top_k), partial, answer, int(ok)])
            print(
                f"  task {i + 1}/{samples} @ {depth} tok: {partial}/{len(top_k)} words "
                f"-> {'HIT' if ok else 'MISS'} ({answer.strip()[:48]!r})"
            )
    return {
        "label": label,
        "depth": depth,
        "n": samples,
        "correct": hits,
        "acc": hits / samples,
        "words_found": partial_list,
    }


def main() -> None:
    tee_output.install()
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
    p.add_argument("--port", type=int, default=8200)
    p.add_argument("--results-dir", default="ruler-results")
    p.add_argument("--seed", type=int, default=1024)
    p.add_argument(
        "--arch",
        default="qwen2",
        help="GGUF architecture key for --override-kv (llama-server caps the "
        "slot at the metadata context_length; overriding it IS the "
        "addendum-130 experiment - attention beyond trained context)",
    )
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
    _KV_CHOICES = ["q8_0", "q4_0", "q4_1", "q5_0", "q5_1", "iq4_nl"]
    p.add_argument(
        "--kv-quant-k",
        default=None,
        choices=_KV_CHOICES,
        help="quantize the K cache to this type (session 36, addendum 5: "
        "the standalone FWE diagnostic needs the same cache flags the "
        "ladder's fwe_pass launches with - both None = default f16)",
    )
    p.add_argument(
        "--stop-on-miss",
        action="store_true",
        help="session 36, addendum 10 (the tournament): stop the depth "
        "sweep at the first depth whose score is below perfect - a "
        "climb ends the moment it falls; the depths above are not run",
    )
    p.add_argument(
        "--fwe-top-k",
        type=int,
        default=None,
        help="session 36, addendum 6: the FWE difficulty knob 1 - the answer "
        "set size (default 3; upstream RULER asks for the 10 most frequent "
        "words; the score is >= 1/3 words per task (session 37, addendum 2), "
        "the per-word partial is the graded 0..k diagnostic)",
    )
    p.add_argument(
        "--fwe-pass-min",
        type=int,
        default=None,
        help="session 37, addendum 9: the pass threshold - a task passes "
        "at >= this many of the 3 expected words (default 1, the "
        "addendum-2 relaxation; 3 is the original strict form). The "
        "per-word partial is always recorded, so the same run grades "
        "at any threshold later",
    )
    p.add_argument(
        "--kv-quant-v",
        default=None,
        choices=_KV_CHOICES,
        help="quantize the V cache to this type (same as --kv-quant-k)",
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
    extra_args = [
        "-c",
        str(wanted_ctx),
        "--parallel",
        "1",
        "--override-kv",
        f"{args.arch}.context_length=int:{wanted_ctx}",
    ]
    if args.kv_quant_k or args.kv_quant_v:
        extra_args += ["-fa", "on"]
        if args.kv_quant_k:
            extra_args += ["--cache-type-k", args.kv_quant_k]
        if args.kv_quant_v:
            extra_args += ["--cache-type-v", args.kv_quant_v]
    proc, healthy = llama_server.start_server(
        args.model, port=args.port, extra_args=extra_args, log_path=log_path
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
        f"ruler gate: {label} (fwe, depths {args.depths}, "
        f"samples {args.samples})"
    )
    try:
        for depth in args.depths:
            csv_path = os.path.join(args.results_dir, f"{label}-{depth}-fwe.csv")
            row = run_fwe_depth(
                    args.port,
                    label,
                    depth,
                    args.samples,
                    csv_path,
                    seed0=args.seed,
                    no_thinking=not args.thinking,
                    show=args.show,
                    top_k=args.fwe_top_k or FWE_TOP_K,
                    min_words=args.fwe_pass_min or FWE_PASS_MIN,
                )
            print(
                f"  {label} @ {depth} tok: {row['correct']}/{row['n']} "
                f"correct (acc {row['acc']:.0%})"
            )
            if args.stop_on_miss and row["acc"] < 1.0:
                print(
                    f"  CLIMB OVER at {depth} tok - the score fell below "
                    f"perfect; depths above {depth} are not run"
                )
                break
    finally:
        llama_server.stop_server(proc, args.port)


if __name__ == "__main__":
    main()
