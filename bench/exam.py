"""bench.exam -- the randomizer's exam machinery.

The exam papers (chain follow + elevator, both parts per level),
the prompts, the two bells (TOKEN: max_tokens = the window;
TIME: the caller's deadline), the grader (ordered-subsequence),
plus the paper-size and gate helpers the randomizer needs:
bell_window and _size_too_large.

Everything is IDEMPOTENT and RESUMABLE; every attempt is logged with
its full prompt and answer for debugging.
"""

from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import infra.llama_server as llama_server
from bench.roster import WINDOW_DEFAULT, roster_from_models_md, window

# protocol.md:179 - Determinism: temperature 0, seed 1024
SAMPLER_SEED = 1024


TRIGRAMS = re.compile(r"\b[a-z]{3}\b")
# the relaxed-final-line grading tolerates these English stop-words as
# prose around the chain ("the chain is", "final answer is", ...) - a
# trigram outside the chain that is NOT a stop-word is a wrong token
RELAX_STOPWORDS = frozenset(
    "the and was for not but all can has its are one two six ten end so "
    "top new now out per via yet yes who why how what when "
    "chain final answer therefore order comma separated tokens "
    "pairs pair start next last item first second third position".split()
)
ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def _gen_tokens(rng: random.Random, n: int) -> list[str]:
    """n distinct random 3-letter lowercase trigrams (random on purpose:
    no alphabetical shortcut, no letter-order confusions by design)."""
    seen: set[str] = set()
    out: list[str] = []
    while len(out) < n:
        t = "".join(rng.choice(ALPHABET) for _ in range(3))
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def build_chain(seed: int, level: int) -> dict[str, Any]:
    """Part 1 - the identity-matching chain (variant 1). level d = d+1
    pairs, d+1 links; the chain t0 -> t1 -> ... -> t(d+1) has a
    dangling end that never heads a pair. The start token is given; the
    model matches second-items to first-items until the dangling end.
    Verified single chain by construction (one unbroken path, no
    forks, no loops)."""
    rng = random.Random(f"exam-chain-{seed}-{level}")
    n_pairs = max(1, level + 1)
    tokens = _gen_tokens(rng, n_pairs + 1)
    pairs = [(tokens[i], tokens[i + 1]) for i in range(n_pairs)]
    order = list(range(n_pairs))
    rng.shuffle(order)
    rows = [pairs[i] for i in order]
    return {
        "part": "chain",
        "level": level,
        "seed": seed,
        "rows": rows,
        "start": tokens[0],
        "path": tokens,
    }


def build_elevator(seed: int, level: int) -> dict[str, Any]:
    """Part 2 - the numbered elevator (variant 4c). level d = d+1
    printed pairs, d hops: add the signed number to the pair's
    position to find the next pair; 0 = end marker. A Hamiltonian path
    over the printed positions by construction - the path IS the
    chain, the jumps are the position differences along it."""
    rng = random.Random(f"exam-elevator-{seed}-{level}")
    n_pairs = max(1, level + 1)
    tokens = _gen_tokens(rng, n_pairs)
    printed = list(range(n_pairs))
    rng.shuffle(printed)
    rows = []
    for chain_index, printed_index in enumerate(printed):
        last = chain_index == n_pairs - 1
        jump = 0 if last else printed[chain_index + 1] - printed_index
        rows.append((printed_index + 1, tokens[chain_index], jump))
    return {
        "part": "elevator",
        "level": level,
        "seed": seed,
        "rows": rows,
        "start": tokens[0],
        "path": list(tokens),
    }


CHAIN_DEMO = """Worked example (dummy tokens, not part of the task):
  (bbb, ccc)
  (aaa, bbb)
  (ddd, ccc)
Chain rule: after a pair (A, B), the next pair in the chain is the one whose FIRST item is B. Start at aaa: the pair (aaa, bbb) comes first; its second item is bbb, so the next pair is the one whose first item is bbb: (bbb, ccc). Its second item is ccc, but ccc never appears as a first item - so ccc is the dangling end of the chain.
ANSWER: aaa, bbb, ccc, ddd"""

ELEVATOR_DEMO = """Worked example (dummy tokens, not part of the task):
  1. bbb  +2
  2. aaa  -1
  3. ccc  +1
  4. ddd   0
Start at aaa, which sits at position 2. aaa's number is -1: 2 + (-1) = 1, so the next pair is the one at position 1: bbb. bbb's number is +2: 1 + 2 = 3, so the next pair is the one at position 3: ccc. ccc's number is +1: 3 + 1 = 4, so the next pair is the one at position 4: ddd. ddd's number is 0: end of chain.
ANSWER: aaa, bbb, ccc, ddd"""


def _shared_prompt(exam: dict[str, Any], demo: str, task_lines: list[str]) -> str:
    lines = [f"You are solving PART {exam['part'].upper()} of a CHAIN-FOLLOWING task.", ""]
    lines.append(
        "The input is WELL-FORMED: no loops, no typos, exactly one valid chain "
        "exists, and it visits every pair exactly once. Do not spend time "
        "checking this - it is guaranteed."
    )
    lines.append("")
    lines.append(demo)
    lines.append("")
    lines.extend(task_lines)
    lines.append("")
    lines.append(
        "You may work freely - show your steps, there is no penalty for "
        "working out loud and no penalty for being wrong along the way. But "
        "you must finish with a final line of exactly this form:"
    )
    lines.append("ANSWER: <the tokens of the chain in order, comma-separated>")
    return "\n".join(lines)


def chain_prompt(exam: dict[str, Any]) -> str:
    task = [f"The task (the chain starts at {exam['start']}):"]
    for a, b in exam["rows"]:
        task.append(f"  ({a}, {b})")
    return _shared_prompt(exam, CHAIN_DEMO, task)


def elevator_prompt(exam: dict[str, Any]) -> str:
    task = [f"The task (the chain starts at {exam['start']}):"]
    for p, t, j in exam["rows"]:
        task.append(f"  {p}. {t}  {j:+d}")
    return _shared_prompt(exam, ELEVATOR_DEMO, task)


def ask_exam(
    port: int,
    messages: list[dict[str, str]],
    bell_tokens: int,
    no_thinking: bool = True,
    deadline: float | None = None,
) -> tuple[str, int, str]:
    """One completion under BOTH bells, streamed (v9.2):

    - the TOKEN bell: max_tokens = the paper's remaining generation
      tokens (finish_reason 'length' = the paper is full)    - the TIME bell: the attempt expires at the caller's deadline;
      the streamed read is cut and the socket closed, cancelling
      the server-side generation (finish_reason 'time_limit'). The
      attempt is graded on what the model produced by the bell.

    Streaming: chunks arrive as the model writes and the deadline is
    checked per chunk - the cut is clean. Returns (text,
    completion_tokens, finish_reason)."""
    import urllib.request

    payload: dict[str, Any] = {
        "messages": messages,
        "max_tokens": bell_tokens,
        "temperature": 0,
        "seed": SAMPLER_SEED,
        "stream": True,
    }
    if no_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    # the socket timeout is the remaining wall time: a read
    # blocking that long means nothing arrived (dead connection) -
    # and it doubles as the time-bell's last-resort cut
    sock_to = max(30.0, deadline - time.monotonic()) if deadline else 1800.0
    text_parts: list[str] = []
    finish = ""
    usage_tokens = 0
    resp = urllib.request.urlopen(req, timeout=sock_to)
    try:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data: "):
                continue
            body = line[6:]
            if body == "[DONE]":
                break
            try:
                chunk = json.loads(body)
            except ValueError:
                continue
            choices = chunk.get("choices") or []
            if choices:
                choice = choices[0]
                delta = choice.get("delta") or {}
                text_parts.append(delta.get("content") or "")
                if choice.get("finish_reason"):
                    finish = choice["finish_reason"]
            u = chunk.get("usage") or {}
            if u.get("completion_tokens"):
                usage_tokens = int(u["completion_tokens"])
            if deadline is not None and time.monotonic() >= deadline:
                finish = "time_limit"
                break
    except TimeoutError:
        finish = "time_limit"
    finally:
        # closing the socket cancels the server's generation
        # (llama-server aborts the slot task on client disconnect)
        resp.close()
    text = "".join(text_parts)
    if not usage_tokens and text:
        try:
            usage_tokens = len(llama_server.tokenize(port, text))
        except Exception:
            usage_tokens = 0
    return text, usage_tokens, finish


def score_exam(answer: str, exam: dict[str, Any], finish_reason: str) -> bool:
    """PASS/FAIL on completion: the ANSWER line must carry the full
    chain in order. Graded semantically - tokens matched
    case-insensitively in order; surrounding text and separators
    tolerated, the ORDER not.

    The bells: 'length' (the paper filled) FAILS even if a partial
    answer leaked - the paper was the budget and it is spent.
    'time_limit' (v9.2): the model is graded on what it produced by
    the 32s bell - a COMPLETE ANSWER line still passes (the model
    answered within the bell; the cut only ended the stream), an
    unfinished one fails. The paper bell is tokens-only budget."""
    if finish_reason == "length":
        return False
    text = (answer or "").lower()
    m = re.search(r"answer\s*:\s*(.+)", text)
    line = m.group(1) if m else ""
    if not m:
        # format-instruction drift is real (KNOWLEDGE.md, and the
        # author's relaxation ruling): the FINAL non-empty line is the
        # reply, whatever prefix it carries ("3. therefore, the chain
        # is ...", "final chain:", brackets) - a correct chain stated on
        # the last line is a correct answer, not a formatting fail. The
        # reply is the last line: answers inside the thinking are NOT
        # a reply and are never graded. The relaxed line must carry
        # EXACTLY the chain's tokens (multiset): with prefixes
        # tolerated, order alone cannot protect a single-token chain -
        # "(ffh), (ffg), (fha)" must not pass for expected ["ffh"]
        lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
        line = lines[-1] if lines else ""
    found = [t for t in TRIGRAMS.findall(line)]
    expected = [t.lower() for t in exam["path"]]
    if not m:
        # relaxed fallback: the line's trigrams are the chain plus at
        # most known English stop-words from the surrounding prose
        # ("3. therefore, the chain is ..."). A NON-stopword trigram
        # outside the chain is a wrong token - the prompt-echo case
        # ("<the tokens of the chain in order, comma-separated>")
        # carries "and", "for", "not"... all stop-words, but its chain
        # is absent, so the subsequence below rejects it. Stop-words
        # cannot rescue a single-token chain either: "(ffh), (ffg),
        # (fha)" has ffg/fha outside the chain - rejected here already
        extras = [t for t in found if t not in expected and t not in RELAX_STOPWORDS]
        if extras:
            return False
        if line.rstrip().endswith("?"):
            # a question mark is a hedge ("ffh, ?"), not an answer
            return False
    # FLEXIBLE GRADING (the trial era): the expected chain must appear
    # as an ORDERED SUBSEQUENCE of the ANSWER line - extra tokens,
    # padding (e.g. trailing end markers), and duplicates are
    # tolerated; only the order of the real links is enforced. The
    # strict era (exact match, no extras) returns once the benchmark
    # matures and the contestant field narrows
    it = iter(found)
    return all(tok in it for tok in expected)



def bell_window(state: dict[str, Any], fam: str, models_dir: str = "models") -> int | None:
    """The v9 bell: the FULL training window - the number of tokens
    the model was trained to hold, the whole paper. No tg/s leg, no
    in-window rule: the time bell (32s per attempt) is what makes
    the fill-rate problem the model's, not the benchmark's."""
    repo = dict(roster_from_models_md()).get(fam)
    if not repo:
        return None
    try:
        return window(repo, os.path.join(models_dir, fam))
    except Exception:
        return WINDOW_DEFAULT



def _size_too_large(path: str, limit_gib: float = 8.0) -> bool:
    """The SIZE gate helper: True when the file on DISK exceeds the
    limit (default the randomizer's 8 GiB f16 family gate - the
    v9.5 exam walk's own 16 GiB candidate cap is RETIRED, superseded
    by the f16 gate: a model whose f16 fits 8 GiB cannot produce a
    rung file anywhere near 16 GiB). No estimates - the measured
    file size is the only truth."""
    return os.path.getsize(path) / (1024**3) > limit_gib


