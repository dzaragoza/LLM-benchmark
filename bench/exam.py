"""bench.exam -- THE benchmark (v9.1): the exam is the only phase.

Daniela's v9.1 ruling: keep the v9 machinery, sharpen the search -
comprehensiveness yielded to efficiency.

  candidates  ONE per model: (model, F16), roster order
              (param-ascending, per md/models.md). The F16
              candidate's max score IS the model's max score.
  the paper    the full training window, as the generation budget.
  the bell     TOKEN and TIME: max_tokens = the window (finish_reason
              'length' = the paper filled); one attempt may run at
              most 1024s (finish_reason 'time_limit' = the bell).
  the walk     v9.4 corrected: the LEVEL is the outer loop -
              every level runs ALL quants, ALWAYS (f16, then every
              variation of q8, q6, q5, q4, q3, q2, q1 in roster
              LADDER order). A level PASSES when any rung passes
              it - there can be several; the deciding rung is the
              quant with the HIGHEST score. It FAILS when none
              does, and the sweep stops there. The fail kind is
              classified from the level's attempts across every
              rung: a wrong chain beats the bell; only bells =
              'out of time' - final, an exam fail (the quants
              were exhausted at the level by construction).
  grading     PASS/FAIL, both parts (chain follow + elevator) per
              level, ordered-subsequence (the flexible trial era).
  self-clean  MODEL granularity: a model whose score is
              strictly below the global best is eliminated once
              its walk is DONE (a failing level reached or the
              ceiling swept - 'out of time' is a fail kind like
              any other). A PENDING model (walk unfinished) is
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

# the TIME bell (v9.2, the author's decision): one exam attempt
# may run at most 1024 seconds - no model gets more than 1024s to
# solve any exam. The streamed read is cut at the wall and the
# socket closed, cancelling the server-side generation; the attempt
# is graded on whatever the model produced ('time_limit'). Time
# ALSO ranks tied leaders (recorded per attempt) - but the human
# breaks ties.
TIME_BELL_SECONDS = 1024

# v9.4 corrected: the per-level quant walk order, by quant NUMBER
# quality-descending (each step down trades precision for speed -
# the clock is what a rung lost to, so the level walks on to a
# smaller quant until one passes it)
QUANT_NUMBERS = ("F16", "Q8", "Q6", "Q5", "Q4", "Q3", "Q2", "Q1")



# the repetition count IS the seed set: n=1 for the benchmark, so the
# seed is 1 - one exam instance per level, identical for every model
def exam_seeds(n: int) -> list[int]:
    return list(range(1, n + 1))


TRIGRAMS = re.compile(r"\b[a-z]{3}\b")
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
    the 1024s bell - a COMPLETE ANSWER line still passes (the model
    answered within the bell; the cut only ended the stream), an
    unfinished one fails. The paper bell is tokens-only budget."""
    if finish_reason == "length":
        return False
    text = (answer or "").lower()
    m = re.search(r"answer\s*:\s*(.+)", text)
    line = m.group(1) if m else ""
    if not m:
        # format-instruction drift is real (KNOWLEDGE.md): accept a
        # bare final line that starts with the chain's start token
        lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
        if lines and lines[-1].split(",")[0].strip() == exam["path"][0].lower():
            line = lines[-1]
        else:
            return False
    found = [t for t in TRIGRAMS.findall(line)]
    expected = [t.lower() for t in exam["path"]]
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
                and (r.startswith(num) or r.startswith("IQ" + num) or r.startswith("T" + num))
            )
        )
        if variants:
            groups.append((num, variants))
    return groups


def hit_time_bell(rec: dict[str, Any]) -> bool:
    """True when the candidate's sweep ended AT the time bell: the
    highest FAILING level has at least one attempt cut by the 1024s
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


def _walk_levels(fam_exam: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The v9.4 level records: state.exam.<fam>.levels.<level> - one
    dict per level with a per-rung pass flag and attempt lists (the
    flat per-rung level trees of the pre-correction era are folded
    in - a migrated record reads the same as a fresh one)."""
    levels = fam_exam.get("levels")
    if isinstance(levels, dict):
        return levels
    migrated: dict[str, dict[str, Any]] = {}
    for rung, rec in fam_exam.items():
        if not isinstance(rec, dict) or rung.startswith("_"):
            continue
        for lv, lrec in (rec.get("levels") or {}).items():
            slot = migrated.setdefault(str(lv), {})
            slot.setdefault("attempts", []).extend(lrec.get("attempts") or [])
            slot["pass"] = slot.get("pass") or bool(lrec.get("pass"))
    return migrated


def walk_done(fam_exam: dict[str, Any]) -> bool:
    """True when the per-level walk finished: a recorded failing
    level exists (the sweep stopped - pass/fail/out-of-time all
    stop there) or every level 0..32 was passed (ceiling sweep)."""
    levels = _walk_levels(fam_exam)
    if any(not l.get("pass") for l in levels.values()):
        return True
    if fam_exam.get("_walk_ceiling"):
        return True
    return False


def model_score(fam_exam: dict[str, Any]) -> int | None:
    """The model's score, v9.4: the highest level whose record shows
    a pass (some rung passed it), with all levels below also passed.
    None while the walk is pending."""
    levels = _walk_levels(fam_exam)
    score = None
    for lv in sorted(levels, key=int):
        if not levels[lv].get("pass"):
            break
        score = int(lv)
    return score


def level_fail_kind(level_rec: dict[str, Any]) -> str | None:
    """Classify a FAILING level from its attempts across every rung
    (the order is the diagnostic priority): 'wrong chain' beats
    'out of context' beats 'out of time' - only bells at the level
    = 'out of time', the fail reason the ledger prints."""
    reasons = []
    for a in level_rec.get("attempts") or []:
        fr = a.get("finish_reason")
        if str(fr or "").startswith("error"):
            reasons.append("error")
        elif fr == "time_limit":
            reasons.append("out of time")
        elif fr == "length":
            reasons.append("out of context")
        elif a.get("ok") is False:
            reasons.append("wrong chain")
    if "wrong chain" in reasons:
        return "wrong chain"
    if "out of context" in reasons:
        return "out of context"
    if "error" in reasons:
        return "error"
    if "out of time" in reasons:
        return "out of time"
    return None


def deciding_rung(fam_exam: dict[str, Any]) -> str | None:
    """The quant with the HIGHEST score at the walk's levels, v9.4 -
    the ledger's quant column. Derived from the attempts: each
    attempt records its rung, so the per-rung highest passed level
    falls out of the record. Ties go to the earliest rung in walk
    order (F16 first)."""
    levels = _walk_levels(fam_exam)
    per_rung: dict[str, int] = {}
    for lv in sorted(levels, key=int):
        for a in levels[lv].get("attempts") or []:
            rung = a.get("rung")
            if rung and a.get("ok") is True and levels[lv].get("pass"):
                cur = per_rung.get(rung)
                if cur is None or int(lv) > cur:
                    per_rung[rung] = int(lv)
    # the HIGHEST score wins; ties go to the earliest rung in walk order
    order = [rung for _num, group in rung_groups() for rung in group]
    best_r = None
    best_s = -1
    for rung in order:
        s = per_rung.get(rung)
        if s is not None and s > best_s:
            best_r, best_s = rung, s
    return best_r


def fail_reason(rec: dict[str, Any]) -> str:
    """Why the candidate failed its highest exam: read the last FAILING
    level's attempts and classify the mode - the quick diagnostic the
    ledger wants:
      out of time      the conversation expired (the 1024s time bell)
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
    in-window rule: the time bell (1024s per attempt) is what makes
    the fill-rate problem the model's, not the benchmark's."""
    # the window may be cached in state (a previous era's read) -
    # a fast path, not a dependency on the retired sweet tree
    cached = ((state.get("sweet") or {}).get(fam) or {}).get("window")
    if cached:
        return int(cached)
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
    models_dir: str,
    state: dict[str, Any],
    state_file: str,
    port: int,
    seeds: list[int],
    max_level: int = 32,
    dry_run: bool = False,
) -> dict[str, Any]:
    """v9.4 corrected: the LEVEL is the outer loop - every level runs
    ALL quants, always (F16, then every variation of q8..q1 in
    roster LADDER order). A level passes when ANY rung passes it;
    the sweep stops at the first level no rung passes. The score is
    the highest level passed; the deciding rung is the quant with
    the highest score. A rung that cannot exist on this machine is
    skipped (unbuildable), never a verdict. Resumable: a recorded
    level is never re-measured. State: exam.<fam>.levels.<level> -
    one record per level with the per-rung pass flag and every
    attempt (each tagged with its rung)."""
    ctx = bell_window(state, fam, models_dir)
    if ctx is None:
        return {"error": "no training window for the family - cannot set the paper"}
    fam_exam = state.setdefault("exam", {}).setdefault(fam, {})
    levels = fam_exam.setdefault("levels", {})
    answers_dir = os.path.join("results", "exam", fam, "walk")
    os.makedirs(answers_dir, exist_ok=True)
    answers_path = os.path.join(answers_dir, "answers.jsonl")
    rungs: list[tuple[str, str]] = [
        (rung, num) for num, group in rung_groups() for rung in group
    ]
    proc = None
    active: str | None = None
    score = None
    try:
        level = 0
        while level <= max_level:
            key = str(level)
            rec = levels.get(key)
            if rec is None:
                attempts: list[dict[str, Any]] = []
                passed = False
                for seed in seeds:
                    for rung, _num in rungs:
                        rec_r = fam_exam.get(rung)
                        if not isinstance(rec_r, dict):
                            rec_r = {}
                        if rec_r.get("unbuildable"):
                            continue
                        # ONE exam paper per (seed, level, rung): both
                        # parts in the SAME context - part 1's prompt,
                        # the model's own reasoning, then part 2's
                        # prompt in one conversation, the generation
                        # budget (the bell) SHARED across the parts
                        insts = {
                            "chain": build_chain(seed, level),
                            "elevator": build_elevator(seed, level),
                        }
                        messages: list[dict[str, str]] = []
                        remaining = ctx
                        part_ok = True
                        for part, prompter in (
                            ("chain", chain_prompt),
                            ("elevator", elevator_prompt),
                        ):
                            inst = insts[part]
                            prompt = prompter(inst)
                            attempt: dict[str, Any] = {
                                "seed": seed,
                                "level": level,
                                "rung": rung,
                                "part": part,
                                "expected": inst["path"],
                            }
                            if dry_run:
                                attempt["ok"] = None
                                attempts.append(attempt)
                                continue
                            if remaining <= 0:
                                attempt.update(ok=False, answer_tokens=0, finish_reason="length")
                                attempts.append(attempt)
                                with open(answers_path, "a", encoding="utf-8") as fh:
                                    fh.write(json.dumps(attempt, ensure_ascii=True) + "\n")
                                part_ok = False
                                continue
                            if active != rung:
                                if proc is not None:
                                    llama_server.stop_server(proc, port)
                                    proc = None
                                gguf = _acquire(fam, rung, models_dir)
                                if not gguf:
                                    fam_exam.setdefault(rung, {})["unbuildable"] = True
                                    _state_store.save_state(state_file, state)
                                    print(f"  {fam} {rung}: unbuildable - skipped")
                                    part_ok = False
                                    break
                                log_path = os.path.join(answers_dir, f"exam-server-{rung}.log")
                                proc, healthy = llama_server.start_server(
                                    gguf,
                                    port=port,
                                    extra_args=[
                                        "-c", str(ctx + 2048),
                                        "--parallel", "1",
                                        "--reasoning", "off",
                                        "--reasoning-budget", "0",
                                    ],
                                    log_path=log_path,
                                )
                                if not healthy or not llama_server.wait_healthy(port, proc=proc):
                                    attempt.update(ok=False, answer_tokens=0,
                                                   finish_reason="error: server did not come up")
                                    attempts.append(attempt)
                                    part_ok = False
                                    break
                                active = rung
                            messages.append({"role": "user", "content": prompt})
                            t0 = time.monotonic()
                            # the TIME bell: the attempt expires 1024s
                            # after the question was asked - no model
                            # gets more than 1024s to solve any exam
                            deadline = t0 + TIME_BELL_SECONDS
                            try:
                                answer, tokens, finish = ask_exam(
                                    port, messages, remaining, deadline=deadline
                                )
                            except Exception as e:
                                # one transport failure must not kill the
                                # walk: record it, fail the part, move on
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
                                part_ok = False
                            messages.append({"role": "assistant", "content": answer or ""})
                            remaining -= tokens
                        if part_ok and not dry_run:
                            passed = True
                        if passed and not dry_run:
                            break
                rec = {"pass": passed and not dry_run, "attempts": attempts}
                levels[key] = rec
                _state_store.save_state(state_file, state)
                if not dry_run:
                    verdict = "PASS" if rec["pass"] else "FAIL"
                    kinds = {a.get("rung") for a in attempts}
                    print(
                        f"  level {level}: {verdict} "
                        f"({len(kinds)} quants tried, {len(attempts)} attempts)"
                    )
            if not rec.get("pass"):
                break
            score = level
            level += 1
        if level > max_level and score == max_level:
            fam_exam["_walk_ceiling"] = True
        if score is not None:
            fam_exam["score"] = score
        if dry_run:
            fam_exam["planned"] = (
                f"paper {ctx} tokens, levels 0..{max_level} on seeds {seeds}, "
                f"all {len(rungs)} quants per level"
            )
        return fam_exam
    finally:
        if proc is not None:
            llama_server.stop_server(proc, port)


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
    """The self-cleaning sweep, v9.4 corrected - MODEL granularity:
    a model is eliminated when its score (the walk's highest passed
    level) is strictly below the global best AND its walk is DONE -
    a failing level reached or the ceiling swept ('out of time' is
    a fail kind like any other: the level already ran every quant).
    A PENDING model is never touched: its record is not final.
    Elimination deletes the model's whole models/ directory (the
    data ALWAYS stays: answers in results/, records in state). The
    model being examined keeps its files until its walk finishes.
    Tied leaders are never eliminated - time ranks them (recorded
    per attempt) but the human breaks ties."""
    import shutil

    exam = state.get("exam") or {}
    best = -1
    for fam_exam in exam.values():
        if not isinstance(fam_exam, dict):
            continue
        s = model_score(fam_exam)
        if s is not None and s > best:
            best = s
    if best < 0:
        return  # nobody has a score yet - nothing to clean
    for fam, fam_exam in exam.items():
        if not isinstance(fam_exam, dict) or fam == exclude_fam:
            continue
        if not walk_done(fam_exam):
            continue  # PENDING - the walk has more to try
        s = model_score(fam_exam)
        if s is None or s >= best:
            # a SURVIVOR: a stale _eliminated flag (e.g. a fossil of
            # the v9 premature-elimination bug) must be CLEARED - the
            # flag is derived state, the score is truth
            if s is not None and fam_exam.get("_eliminated"):
                fam_exam["_eliminated"] = False
            continue
        famdir = os.path.join(models_dir, fam)
        if not os.path.isdir(famdir):
            continue
        fam_exam["_eliminated"] = True
        shutil.rmtree(famdir, ignore_errors=True)
        print(f"  gc: {fam} eliminated (score {s} < best {best}) - artifacts deleted")


def run(
    models_dir: str,
    state: dict[str, Any],
    state_file: str,
    port: int,
    families: list[str] | None,
    n_seeds: int =  1,
    max_level: int = 32,
    dry_run: bool = False,
    on_family_done: Any = None,
) -> dict[tuple[str, str], Any]:
    """The exam controller, v9.4 corrected: ONE straight pass over the
    models (roster order, param-ascending) - each model's LEVEL walk
    runs IN FULL (every level, all quants per level) before the next
    begins. A DONE walk (failing level reached, or ceiling swept) is
    final and never re-run; a PENDING walk resumes. After each walk
    the self-clean deletes strictly-lower scorers from disk (the
    data stays)."""
    seeds = exam_seeds(n_seeds)
    cands = candidates(state, families, models_dir)
    if not cands:
        return {}
    results: dict[tuple[str, str], Any] = {}
    for fam, _rung in cands:
        key = (fam, "walk")
        fam_tree = state.setdefault("exam", {}).setdefault(fam, {})
        if not dry_run and walk_done(fam_tree):
            results[key] = fam_tree
            continue
        if dry_run:
            results[key] = {"planned": f"level walk 0..{max_level} on seeds {seeds}, all quants"}
            continue
        print(f"-- {fam}, paper {bell_window(state, fam, models_dir)} tokens --")
        # one model's failure never kills the exam - any exception is
        # recorded and the walk moves on.
        try:
            rec = run_family(
                fam,
                models_dir,
                state,
                state_file,
                port,
                seeds,
                max_level,
                dry_run,
            )
        except SystemExit as e:
            if e.code == 130:
                raise
            rec = {"error": f"exam run failed: {e.code}"}
        except Exception as e:
            rec = {"error": f"exam run failed: {e}"}
        results[key] = rec
        # the self-clean FIRST: a model whose walk is DONE and scored
        # strictly below the global best leaves the disk (the data
        # always stays), THEN the family push - so this model's own
        # deletions are staged and committed in its push
        _gc(models_dir, state, fam)
        if on_family_done is not None:
            try:
                on_family_done(fam)
            except Exception as e:
                print(f"  family-done hook failed (ignored): {e}")
    return results


