"""bench.exam -- THE benchmark (v9.1): the exam is the only phase.

Daniela's v9.1 ruling: keep the v9 machinery, sharpen the search -
comprehensiveness yielded to efficiency.

  candidates  ONE per model: (model, F16), roster order
              (param-ascending, per md/models.md). The F16
              candidate's max score IS the model's max score.
  the paper    the full training window, as the generation budget.
  the bell     TOKEN and TIME: max_tokens = the window (finish_reason
              'length' = the paper filled); one attempt may run at
              most 32s (finish_reason 'time_limit' = the bell).
  recovery    v9.4 - the EXHAUSTIVE quant walk: a sweep that
              ends at the bell is retried quant number by quant
              number (f16, q8, q6, q5, q4, q3, q2, q1), EVERY
              variation of a number (roster LADDER order) before
              the next, until a verdict lands. A clean sweep
              PASSES the walk; a quant number whose every
              testable variation answered and was wrong FAILS it;
              only bells move the walk on. Quants exhausted with no
              verdict anywhere = 'out of time', itself an exam
              fail - recovery was exhaustive.
  grading     PASS/FAIL, both parts (chain follow + elevator) per
              level, ordered-subsequence (the flexible trial era).
  self-clean  MODEL granularity: a model whose deciding rung
              scored strictly below the global best is eliminated
              once its walk reached a terminal verdict (pass,
              fail, or out of time - an exam fail: recovery was
              exhaustive). A PENDING model (walk unfinished) is
              never touched. Tied leaders are NEVER eliminated;
              TIME ranks them (elapsed per attempt) but decides
              nothing - the human breaks ties.

Run data is v9-compatible: the same state shape (exam.<fam>.<rung>),
the same answers files, the same ledger - a v9.1 run resumes a v9
run's F16 records directly.

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
from bench import state_store as _state_store
from bench.roster import WINDOW_DEFAULT, roster_from_models_md, window

# protocol.md:179 - Determinism: temperature 0, seed 1024
SAMPLER_SEED = 1024

# the TIME bell (v9.4, the author's ruling): one exam attempt may
# run at most 32 seconds - with recovery re-running the whole exam
# per quant, a long bell multiplies against the quant ladder. The
# streamed read is cut at the wall and the socket closed, cancelling
# the server-side generation; the attempt is graded on whatever the
# model produced ('time_limit'). Time ALSO ranks tied leaders
# (recorded per attempt) - but the human breaks ties.
TIME_BELL_SECONDS = 32

# v9.4 recovery: the quant walk, by quant NUMBER quality-descending
# (each step down trades precision for speed - the clock is what the
# candidate lost to, so the walk buys tok/s with bits until a
# verdict lands)
QUANT_NUMBERS = ("F16", "Q8", "Q6", "Q5", "Q4", "Q3", "Q2", "Q1")

# v9.4 SIZE recovery (the author's ruling): a candidate's file on disk
# may not exceed 16 GiB - too large is a condition like out of time,
# with the SAME recovery logic: a quant level whose every candidate is
# too large descends to the next quant number (a smaller quant is a
# smaller file - size recovery walks the same ladder the clock does)
MAX_CANDIDATE_GIB = 16.0



# the repetition count IS the seed set: n=1 for the benchmark, so the
# seed is 1 - one exam instance per level, identical for every model
def exam_seeds(n: int) -> list[int]:
    return list(range(1, n + 1))


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
      tokens (finish_reason 'length' = the paper is full)
    - the TIME bell: the attempt expires after TIME_BELL_SECONDS;
      the streamed read is cut and the socket closed, cancelling the
      server-side generation (finish_reason 'time_limit'). The
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


def rung_groups() -> list[tuple[str, tuple[str, ...]]]:
    """v9.4: the walk as (quant number, variations) pairs - F16
    alone, then EVERY variation of each number in roster LADDER
    order (q8_0; q6_k; q5_k_s, q5_0, q5_k_m, q5_1; ... q1)."""
    from bench.roster import LADDER

    groups: list[tuple[str, tuple[str, ...]]] = []
    for num in QUANT_NUMBERS:
        variants = (
            ("F16",)
            if num == "F16"
            else tuple(
                r
                for r in LADDER
                if r != "F16"
                and (r.startswith(num) or r.startswith("I" + num) or r.startswith("T" + num))
            )
        )
        if variants:
            groups.append((num, variants))
    return groups


def hit_time_bell(rec: dict[str, Any]) -> bool:
    """True when the candidate's sweep ended AT the time bell: the
    highest FAILING level has at least one attempt cut by the 32s
    bell ('time_limit') - the model may simply be too slow at this
    quant, so the recovery ladder gets a chance."""
    levels = rec.get("levels") or {}
    fail_keys = [k for k in levels if not levels[k].get("pass")]
    if not fail_keys:
        return False
    top = max(fail_keys, key=int)
    return any(
        a.get("finish_reason") == "time_limit"
        for a in (levels[top].get("attempts") or [])
    )


def rung_verdict(rec: dict[str, Any]) -> str | None:
    """One rung record's outcome, v9.4 - the PROCTOR rule (the
    author's ruling): one fail reason per exam, and the BELL is
    the gate. A paper with ANY bell-cut attempt came in after the
    bell: out of time, UNGRADED - pass/fail is reserved for papers
    that ended before the bell. 'pass' (the sweep ended with NO
    failing level), 'fail' (the failing paper ENDED - handed in
    before the bell - and the answer was wrong: a capability fail
    no smaller quant rescues), 'time' (the failing paper has at
    least one bell-cut attempt: after the bell, rejected, the walk
    may recover at a smaller quant). None = unmeasured.

    A record marked too_large (the SIZE gate, MAX_CANDIDATE_GIB)
    reads as 'time'-grade: not a graded paper, and its level can
    descend the same way a belled level does."""
    if rec.get("too_large"):
        return "time"  # the SIZE gate: same recovery grade as the bell
    if rec.get("score") is None:
        return None
    levels = rec.get("levels") or {}
    fail_keys = [k for k in levels if not levels[k].get("pass")]
    if not fail_keys:
        return "pass"
    top = max(fail_keys, key=int)
    # THE PROCTOR, WHOLE PAPER (the author's ruling): the proctor
    # receives an exam only when BOTH parts are answered - no candidate
    # hands in a half-finished exam. ANY belled part means the paper
    # was never handed in: out of time, UNGRADED (even when the sibling
    # part ended - a wrong chain beside a belled elevator is not a
    # graded fail; the paper as a whole came in after the bell). Only
    # a paper with EVERY part ended (stop/length, no bell, no error) is
    # handed in and graded: wrong answer -> capability fail, the walk
    # ends, no descent.
    for a in levels[top].get("attempts") or []:
        if a.get("finish_reason") == "time_limit":
            return "time"  # the bell rang mid-paper: not handed in
    return "fail"  # both parts answered: graded, and it failed


def model_verdict(fam_exam: dict[str, Any]) -> str | None:
    """The model's terminal verdict, v9.4 - derived from the records
    so a resumed run skips a completed walk and a crashed run
    resumes mid-walk:
      pass / fail    the walk's stop conditions, at QUANT LEVEL
                     granularity: a level with any passing candidate
                     (verdict pass); a level, fully evaluated, with
                     any wrong-answer candidate (verdict fail)
      time           every quant level was fully evaluated and only
                     bells came back - an exam fail per the author's
                     ruling; the live walk also certifies it with
                     the _out_of_time flag
      None           PENDING: an incomplete level or an errored
                     sweep - the walk has more to try"""
    if fam_exam.get("_out_of_time"):
        return "time"
    walked_all = True
    for _num, group in rung_groups():
        gpass = gfail = 0
        complete = True
        for rung in group:
            rec = fam_exam.get(rung)
            if not isinstance(rec, dict):
                complete = False
                continue
            if rec.get("unbuildable"):
                continue
            v = rung_verdict(rec)
            if v == "pass":
                gpass += 1
            elif v == "fail":
                gfail += 1
            elif v is None:
                complete = False
        if gpass:
            return "pass"
        # the level's every candidate ran and one answered wrong: a
        # capability fail ends the walk (all candidates of the level
        # are always evaluated; the verdict is level-granular)
        if gfail and complete:
            return "fail"
        if not complete:
            walked_all = False
    if walked_all:
        return "time"
    return None


def best_rung(fam_exam: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """The model's DECIDING (rung, record) pair, v9.4: the
    highest-scoring rung the walk ever recorded, ties to the earlier
    rung in walk order. The deciding rung is the ledger's quant
    column; the record carries the score the gc and ledger read."""
    best: tuple[str, dict[str, Any]] | None = None
    for _num, group in rung_groups():
        gfail = False
        for rung in group:
            rec = fam_exam.get(rung)
            if not isinstance(rec, dict) or rec.get("score") is None:
                continue
            if best is None or rec["score"] > best[1]["score"]:
                best = (rung, rec)
            if rung_verdict(rec) == "fail":
                gfail = True
        # the LEVEL decides: a failing level ends the walk AFTER all
        # its candidates were evaluated - records beyond that level
        # are relics of a pre-fix walk and never decide anything
        if gfail or any(
            isinstance(fam_exam.get(r), dict)
            and rung_verdict(fam_exam.get(r) or {}) == "pass"
            for r in group
        ):
            return best
    return best


def best_record(fam_exam: dict[str, Any]) -> dict[str, Any] | None:
    """The deciding record alone (the gc's read of best_rung)."""
    br = best_rung(fam_exam)
    return br[1] if br else None


def fail_reason(rec: dict[str, Any]) -> str:
    """Why the candidate failed its highest exam: read the last FAILING
    level's attempts and classify the mode - the quick diagnostic the
    ledger wants:
      out of time      the conversation expired (the 32s time bell)
      out of context   the token bell rang (the paper filled) first
      wrong chain      an answer arrived, the tokens/order were wrong
      error            a transport/tool failure, not the model's fault
      no record        nothing measured (or only passes stored)"""
    levels = rec.get("levels") or {}
    fail_keys = [k for k in levels if not levels[k].get("pass")]
    if not fail_keys:
        return "no record"
    top = max(fail_keys, key=int)
    reasons = []
    for a in levels[top].get("attempts") or []:
        fr = a.get("finish_reason")
        if str(fr or "").startswith("error"):
            reasons.append("error")
        elif fr == "time_limit":
            reasons.append("out of time")
        elif fr == "length":
            reasons.append("out of context")
        elif a.get("ok") is False:
            reasons.append("wrong chain")
    if "error" in reasons and not ({"wrong chain", "out of context", "out of time"} & set(reasons)):
        return "error"
    if "out of time" in reasons:
        return "out of time"
    if "out of context" in reasons:
        return "out of context"
    if "wrong chain" in reasons:
        return "wrong chain"
    return "unknown"


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


def candidates(
    state: dict[str, Any],
    families: list[str] | None,
    models_dir: str = "models",
    dry_run: bool = False,
) -> list[tuple[str, str]]:
    """v9.4: the roster as (family, F16) pairs, param-ascending - the
    F16 is the walk's FIRST group; the recovery rungs are acquired
    lazily by the walk itself. Acquisition stays lazy (the f16 is
    downloaded/converted on demand)."""
    order = [name for name, _ in roster_from_models_md()]
    fams = order if not families else [f.split("=")[0] for f in families]
    return [(fam, "F16") for fam in fams]


def run_family(
    fam: str,
    rung: str,
    gguf: str,
    models_dir: str,
    state: dict[str, Any],
    state_file: str,
    port: int,
    seeds: list[int],
    max_level: int,
    start_level: int,
    dry_run: bool = False,
    time_factor: int = 1024,
) -> dict[str, Any]:
    """One candidate's sweep - a (model, quant) pair: every level from
    the first unrecorded one, both parts per level, until the first
    failing level. The final score is the highest level passed (both
    parts, every seed). Resumable: recorded levels are never
    re-measured. State keys per candidate: exam.<fam>.<rung>."""
    ctx = bell_window(state, fam, models_dir)
    if ctx is None:
        return {"error": "no training window for the family - cannot set the paper"}
    exam = state.setdefault("exam", {}).setdefault(fam, {}).setdefault(rung, {})
    exam["rung"] = rung
    exam["bell_ctx"] = ctx
    # a stale error from an earlier run must not shadow this run's
    # levels/score in the summary - the file resolution and server
    # start already succeeded by the time we are here
    exam.pop("error", None)
    levels = exam.setdefault("levels", {})
    # benchmark OUTPUTS live in the results tree (uploaded by the git
    # rail), never under models/ - that directory holds only what can
    # be re-downloaded or re-created (quants, sources, the imatrix)
    answers_dir = os.path.join("results", "exam", fam, rung)
    os.makedirs(answers_dir, exist_ok=True)
    answers_path = os.path.join(answers_dir, "answers.jsonl")
    log_path = os.path.join(answers_dir, "exam-server.log")
    proc = None
    score = None
    try:
        if not dry_run:
            # server context: the bell + prompt headroom (the prompt
            # and template must fit alongside the generation budget).
            # --reasoning off --reasoning-budget 0 (the author's
            # ruling): the exam measures the ANSWER, not a hidden
            # reasoning budget - a model's thinking must live in the
            # visible paper, never in a separate channel that eats
            # tokens off-ledger
            proc, healthy = llama_server.start_server(
                gguf,
                port=port,
                extra_args=[
                    "-c",
                    str(ctx + 2048),
                    "--parallel",
                    "1",
                    "--reasoning",
                    "off",
                    "--reasoning-budget",
                    "0",
                ],
                log_path=log_path,
            )
            if not healthy or not llama_server.wait_healthy(port, proc=proc):
                exam["error"] = "server did not come up"
                return exam
        level = start_level
        while level <= max_level:
            key = str(level)
            if key in levels:
                rec = levels[key]
            else:
                attempts = []
                passed = True
                for seed in seeds:
                    # ONE exam paper per (seed, level): both parts run
                    # in the SAME context - part 1's prompt, the
                    # model's own reasoning, then part 2's prompt all
                    # live in one conversation, and the generation
                    # budget (the bell) is SHARED across the parts:
                    # what part 1 spends, part 2 no longer has
                    insts = {
                        "chain": build_chain(seed, level),
                        "elevator": build_elevator(seed, level),
                    }
                    messages: list[dict[str, str]] = []
                    remaining = ctx
                    # the TIME bell is PER EXAM (the paper: both parts
                    # in one conversation), not per part - the parts
                    # share it exactly as they share the token budget.
                    # Set once, before part 1.
                    paper_deadline = time.monotonic() + TIME_BELL_SECONDS
                    for part, prompter in (
                        ("chain", chain_prompt),
                        ("elevator", elevator_prompt),
                    ):
                        inst = insts[part]
                        prompt = prompter(inst)
                        attempt: dict[str, Any] = {
                            "seed": seed,
                            "level": level,
                            "part": part,
                            "expected": inst["path"],
                        }
                        if dry_run:
                            attempt["ok"] = None
                            attempts.append(attempt)
                            continue
                        if remaining <= 0:
                            # part 1 (or an earlier seed's paper) spent
                            # the whole bell: the paper is full, this
                            # part cannot even be asked
                            attempt.update(ok=False, answer_tokens=0, finish_reason="length")
                            attempts.append(attempt)
                            with open(answers_path, "a", encoding="utf-8") as fh:
                                fh.write(json.dumps(attempt, ensure_ascii=True) + "\n")
                            passed = False
                            continue
                        messages.append({"role": "user", "content": prompt})
                        t0 = time.monotonic()
                        # the paper's SHARED deadline; what part 1
                        # spent, part 2 no longer has
                        deadline = paper_deadline
                        try:
                            answer, tokens, finish = ask_exam(
                                port, messages, remaining, deadline=deadline
                            )
                        except Exception as e:
                            # one transport failure (server hiccup, HTTP
                            # error) must not kill the family's sweep:
                            # record it, fail the part, keep the paper
                            answer, tokens, finish = "", 0, f"error: {e}"
                        ok = score_exam(answer, inst, finish)
                        attempt.update(
                            ok=ok,
                            answer_tokens=tokens,
                            finish_reason=finish,
                            elapsed_s=round(time.monotonic() - t0, 1),
                            answer=(answer or "")[-2000:],
                        )
                        attempts.append(attempt)
                        with open(answers_path, "a", encoding="utf-8") as fh:
                            fh.write(json.dumps(attempt, ensure_ascii=True) + "\n")
                        if not ok:
                            passed = False
                        # the model's own reasoning STAYS in the paper
                        # (the shared context) for the next part to use
                        messages.append({"role": "assistant", "content": answer or ""})
                        remaining -= tokens
                rec = {"pass": passed and not dry_run, "attempts": attempts}
                levels[key] = rec
                _state_store.save_state(state_file, state)
                # mid-run log hygiene: a -lv 5 stream over hours is
                # 100MB+; keep the banner + the latest tail under the
                # github limits so no push can ever carry a giant blob
                try:
                    if os.path.isfile(log_path) and os.path.getsize(log_path) > 20 * 2**20:
                        with open(log_path, encoding="utf-8", errors="replace") as fh:
                            lines = fh.readlines()
                        with open(log_path, "w", encoding="utf-8") as fh:
                            fh.writelines(lines[:100])
                            fh.write(f"... [mid-run truncation: {len(lines)} lines]\n")
                            fh.writelines(lines[-300:])
                except OSError:
                    pass
                if not dry_run:
                    verdict = "PASS" if rec["pass"] else "FAIL"
                    capped = sum(1 for a in attempts if a.get("finish_reason") == "length")
                    belled = sum(1 for a in attempts if a.get("finish_reason") == "time_limit")
                    # the fail MODE must be visible at a glance, and it
                    # MUST MATCH the verdict the walk actually applied -
                    # the PROCTOR rule (rung_verdict): ANY belled attempt
                    # means the paper came in after the bell - out of
                    # time, ungraded; only papers that ENDED are graded
                    # (pass/fail). The label and the verdict share one
                    # source: rung_verdict on this level record.
                    mode = ""
                    if not rec["pass"]:
                        mode = (
                            ", OUT OF TIME"
                            if rung_verdict({"score": rec.get("score", 0),
                                              "levels": {str(level): rec}}) == "time"
                            else ", wrong answer"
                        )
                    print(
                        f"  level {level}: {verdict} "
                        f"(parts {[a.get('ok') for a in attempts]}"
                        + (f", {capped} ran out of context" if capped else "")
                        + mode
                        + ")"
                    )
            if not rec.get("pass"):
                score = level - 1
                break
            score = level
            level += 1
        if score is not None:
            exam["score"] = score
        if dry_run:
            exam["planned"] = (
                f"paper {ctx} tokens, sweep {start_level}..{max_level} "
                f"on seeds {seeds}, 2 parts per level"
            )
        return exam
    finally:
        if proc is not None:
            llama_server.stop_server(proc, port)
        # log hygiene (v9.4): the committed log keeps only its
        # INFORMATION - the startup banner (model, quant, ctx) and the
        # memory breakdown table. The -lv 4 stream is already small
        # (~16KB); this trim is the safety net that guarantees no push
        # can ever carry a giant blob.
        try:
            with open(log_path, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
            if len(lines) > 500:
                with open(log_path, "w", encoding="utf-8") as fh:
                    fh.writelines(lines[:100])
                    fh.write(f"... [{len(lines) - 400} middle lines truncated]\n")
                    fh.writelines(lines[-300:])
        except OSError:
            pass


def _size_too_large(path: str) -> bool:
    """The SIZE gate (v9.4, the author's ruling): True when the
    candidate's file on DISK exceeds MAX_CANDIDATE_GIB. No
    estimates - the author's ruling: the measured file size is
    the only truth (the file is acquired first, then measured;
    the verdict lands BEFORE any exam attempt)."""
    return os.path.getsize(path) / (1024**3) > MAX_CANDIDATE_GIB


def _acquire(fam: str, rung: str, models_dir: str) -> str | None:
    """Lazy acquisition: the candidate's file, downloaded/quantized
    on demand via the roster build path. None = the candidate cannot
    exist on this machine (RAM-infeasible, an unquantizable shape, a
    tool failure) - recorded, skipped."""
    import infra.hf_download as hf_download
    from bench.roster import build

    famdir = os.path.join(models_dir, fam)
    existing = hf_download.local_rung(famdir, rung)
    if existing and os.path.isfile(existing):
        return existing
    repo = dict(roster_from_models_md()).get(fam)
    if not repo:
        return None
    try:
        return build(fam, repo, famdir, rung)
    except SystemExit as e:
        if e.code == 130:
            raise
        return None
    except Exception:
        return None


def _gc(models_dir: str, state: dict[str, Any], exclude_fam: str | None) -> None:
    """The self-cleaning sweep, v9.4 - MODEL granularity: a model is
    eliminated when its deciding rung (the walk's best scorer) has
    a final score strictly below the global best AND the walk
    reached a terminal verdict - pass, fail, or out of time (an
    exam fail per the author's ruling: the recovery walk is
    EXHAUSTIVE, a timeout survived every quant). A PENDING model -
    timeouts with quants left to try, an errored sweep - is never
    touched: its record is not final. Elimination deletes the
    model's whole models/ directory (the data ALWAYS stays:
    answers in results/, records in state). The model being
    examined keeps its files until its walk finishes. Tied leaders
    are never eliminated - time ranks them (recorded per attempt)
    but the human breaks ties.

    SELF-HEALING (the author's ruling, the Qwen2.5-0.5B incident): a
    mid-run rule correction can move the global best retroactively,
    so a model eliminated against a wrongly-inflated best can
    re-derive as a SURVIVOR after its directory was already deleted.
    The gc detects exactly that - a survivor with a stale
    _eliminated flag and a missing directory - and RE-CREATES the
    deciding rung's artifact on the spot via the lazy acquisition
    path (download/convert/quantize as needed). The tier leaders'
    files are the one thing the tournament must never lose.
    are never eliminated - time ranks them (recorded per attempt)
    but the human breaks ties."""
    import shutil

    exam = state.get("exam") or {}
    best = -1
    for fam_exam in exam.values():
        if not isinstance(fam_exam, dict):
            continue
        br = best_rung(fam_exam)
        if br is not None:
            s = br[1].get("score")
            if s is not None and s > best:
                best = s
    if best < 0:
        return  # nobody has a score yet - nothing to clean
    for fam, fam_exam in exam.items():
        if not isinstance(fam_exam, dict) or fam == exclude_fam:
            continue
        verdict = model_verdict(fam_exam)
        if verdict is None:
            continue  # PENDING - the walk has more to try
        br = best_rung(fam_exam)
        if br is None:
            continue
        s = br[1].get("score")
        if s is None or s >= best:
            # a SURVIVOR: a stale _eliminated flag (e.g. a fossil of
            # the v9 premature-elimination bug) must be CLEARED - the
            # flag is derived state, the score is truth
            if s is not None and fam_exam.get("_eliminated"):
                fam_exam["_eliminated"] = False
                rung_file = _acquire(fam, br[0], models_dir)
                if rung_file:
                    print(
                        f"  gc: {fam} re-derives as a SURVIVOR (score {s} == best {best}) "
                        f"but its artifacts were missing - re-created {os.path.basename(rung_file)}"
                    )
                else:
                    print(
                        f"  gc: {fam} re-derives as a SURVIVOR (score {s} == best {best}) "
                        f"but its deciding rung {br[0]} could not be re-created on this machine"
                    )
            continue
        famdir = os.path.join(models_dir, fam)
        if not os.path.isdir(famdir):
            continue
        fam_exam["_eliminated"] = True
        shutil.rmtree(famdir, ignore_errors=True)
        print(f"  gc: {fam} eliminated (best-rung score {s} < best {best}) - artifacts deleted")


def run(
    models_dir: str,
    state: dict[str, Any],
    state_file: str,
    port: int,
    families: list[str] | None,
    n_seeds: int = 1,
    max_level: int = 32,
    dry_run: bool = False,
    on_family_done: Any = None,
) -> dict[tuple[str, str], Any]:
    """The exam controller (v9): ONE straight pass over the
    candidates - roster order (param-ascending) x the tg/s-sorted
    ladder - each candidate swept 0..first-fail IN FULL before the
    next begins (the author's efficiency ruling: an answer as soon as
    possible, the pruning starts with the first score).

    A stored score is final (idempotence): scored candidates are
    never re-run; the pass skips them and keeps their record. After
    each sweep the self-clean deletes strictly-lower scorers from
    disk (the data stays)."""
    seeds = exam_seeds(n_seeds)
    cands = candidates(state, families, models_dir)
    if not cands:
        return {}
    results: dict[tuple[str, str], Any] = {}
    for fam, rung in cands:
        key = (fam, rung)
        fam_exam = (state.get("exam") or {}).get(fam) or {}
        # v9 records are rung-keyed ONLY. The old family-keyed shape
        # (a boundary record stored directly under the family) is
        # PRE-v9 era data: it belongs to a different protocol and is
        # NEVER inherited as this candidate's record - doing so made
        # a --clean-less run silently skip candidates (the
        # Qwen3.5-0.8B-first bug). --clean wipes it; without --clean
        # an old-era family record is simply not this candidate's.
        fam_tree = state.setdefault("exam", {}).setdefault(fam, {})
        # idempotence: a walk that already reached a verdict is final
        if not dry_run and model_verdict(fam_tree) is not None:
            results[key] = best_record(fam_tree) or fam_tree
            continue
        if dry_run:
            results[key] = {"planned": f"quant walk 0..{max_level} on seeds {seeds}"}
            continue
        # v9.4: the EXHAUSTIVE quant walk - quant number by quant
        # number (f16, q8, q6, q5, q4, q3, q2, q1), EVERY variation
        # of a number (roster LADDER order) before the next, until
        # a verdict lands: a clean sweep PASSES the walk; a quant
        # number whose every testable variation answered and was
        # wrong FAILS it; only bells move the walk on. Quants
        # exhausted with no verdict anywhere = out of time - itself
        # an exam fail (recovery was exhaustive). An unbuildable
        # variation is skipped, not a verdict; an errored sweep
        # leaves the model PENDING, never falsely failed.
        walk_verdict = None
        errored = False
        gpass = gfail = gbell = 0
        # every candidate proves ITSELF from level 0 (the author's
        # ruling - the exam level does NOT carry across quant levels):
        # a rung that timed out at level 3 does not hand its passes
        # down - the next quant number's candidates take the exam from
        # the start, because a smaller quant has not proven anything
        for num, group in rung_groups():
            gpass = gfail = gbell = 0
            for rung in group:
                rec = fam_tree.get(rung) or {}
                if rec.get("too_large"):
                    continue  # the SIZE gate already rejected this rung
                if rec.get("score") is None and not rec.get("unbuildable"):
                    gguf = _acquire(fam, rung, models_dir)
                    if not gguf:
                        rec = {"unbuildable": True}
                        fam_tree[rung] = rec
                        _state_store.save_state(state_file, state)
                        print(f"  {fam} {rung}: unbuildable - skipped")
                    elif _size_too_large(gguf):
                        # the SIZE gate (the author's ruling): measured on
                        # the acquired file, BEFORE any exam attempt - too
                        # large is known and recovered before any other
                        # pass/fail condition can exist
                        rec = {"too_large": True}
                        fam_tree[rung] = rec
                        _state_store.save_state(state_file, state)
                        print(
                            f"  {fam} {rung}: TOO LARGE on disk "
                            f"(> {MAX_CANDIDATE_GIB:g} GiB) - size recovery: "
                            "the level may descend"
                        )
                        results[(fam, rung)] = rec
                        continue
                    else:
                        print(
                            f"-- {fam} {rung} ({num}), paper "
                            f"{bell_window(state, fam, models_dir)} tokens --"
                        )
                        # one candidate's failure never kills the exam - any
                        # exception is recorded and the sweep moves on.
                        try:
                            rec = run_family(
                                fam,
                                rung,
                                gguf,
                                models_dir,
                                state,
                                state_file,
                                port,
                                seeds,
                                max_level,
                                0,
                                dry_run,
                            )
                        except SystemExit as e:
                            if e.code == 130:
                                raise
                            rec = {"error": f"exam run failed: {e.code}"}
                        except Exception as e:
                            rec = {"error": f"exam run failed: {e}"}
                        fam_tree[rung] = rec
                        _state_store.save_state(state_file, state)
                results[(fam, rung)] = rec
                v = rung_verdict(rec)
                if v == "pass":
                    gpass += 1
                elif v == "fail":
                    gfail += 1
                elif v == "time":
                    # the bell OR the SIZE gate - both recover the same
                    # way: the level descends when every candidate is
                    # time/too_large
                    gbell += 1
                elif v is None and not rec.get("unbuildable"):
                    errored = True
            # the LEVEL's verdict - decided only AFTER every candidate
            # of the quant number was evaluated (they always all run):
            #   any pass  -> the walk ends; the high score is the
            #               highest score of the passes
            #   any fail  -> the walk ends (verdict fail); the high
            #               score is the best of the earlier passes
            #   all bell  -> the ONLY descent: the next quant number
            if gpass:
                walk_verdict = "pass"
                break
            if gfail:
                walk_verdict = "fail"
                break
        if walk_verdict is None and not errored:
            # every quant number was tried and only bells/too-larges came
            # back: the quants are exhausted - out of time, an exam fail
            fam_tree["_out_of_time"] = True
            _state_store.save_state(state_file, state)
            nlarge = sum(1 for r in fam_tree.values()
                         if isinstance(r, dict) and r.get("too_large"))
            why = "size" if nlarge else "the bell"
            print(f"  {fam}: quants exhausted ({why}) - out of time (an exam fail)")
        # the self-clean FIRST: a model whose deciding rung scored
        # strictly below the global best AND whose walk reached a
        # verdict leaves the disk (the data always stays), THEN the
        # family push - so this model's own deletions are staged
        # and committed in its push
        _gc(models_dir, state, fam)
        # v9.1: the F16 IS the model - the family is complete after
        # its one candidate; report and push (the watchability ruling)
        if on_family_done is not None:
            try:
                on_family_done(fam)
            except Exception as e:
                print(f"  family-done hook failed (ignored): {e}")
    return results
