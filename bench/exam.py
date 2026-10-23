"""bench.exam -- THE benchmark (v9.1): the exam is the only phase.

Daniela's v9.1 ruling: keep the v9 machinery, sharpen the search -
comprehensiveness yielded to efficiency.

  candidates  ONE per model: (model, F16), roster order
              (param-ascending, per md/models.md). The F16
              candidate's max score IS the model's max score.
  the paper    the full training window, as the generation budget.
  the bell     TOKEN only: max_tokens = the window (finish_reason
              'length' = the paper filled). The time limit is
              RETIRED (the author's ruling after the first
              time-out: an arbitrary measure).
  grading     PASS/FAIL, both parts (chain follow + elevator) per
              level, ordered-subsequence (the flexible trial era).
  self-clean  MODEL granularity: a model whose F16 scored strictly
              below the global best is eliminated - its models/
              directory is deleted (the data always stays). Tied
              leaders are NEVER eliminated; TIME ranks them
              (elapsed per attempt is recorded) but decides nothing
              - the human breaks ties.

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
    """v9.1: the roster as (family, F16) pairs, param-ascending - ONE
    candidate per model. The F16 candidate's max score IS the model's
    max score (the author's v9.1 ruling: comprehensiveness yielded to
    efficiency; the quant ablation era ended). Acquisition stays
    lazy (the f16 is downloaded/converted on demand)."""
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
                        # the TIME bell: the conversation expires 1024s
                        # after the question is asked - the UX budget at
                        # its source, per attempt
                        # the time bell: the attempt expires 1024s
                        # after the question was asked - no model gets
                        # more than 1024s to solve any exam (v9.2).
                        # The attempt is graded on what the model
                        # produced by the bell (a complete ANSWER
                        # line still passes; an unfinished one fails)
                        deadline = t0 + TIME_BELL_SECONDS
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
                if not dry_run:
                    verdict = "PASS" if rec["pass"] else "FAIL"
                    capped = sum(1 for a in attempts if a.get("finish_reason") == "length")
                    print(
                        f"  level {level}: {verdict} "
                        f"(parts {[a.get('ok') for a in attempts]}"
                        + (f", {capped} ran out of context" if capped else "")
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
        # the -lv 5 server log is debug gold but HUGE (100MB+ per
        # candidate - the push-breaking kind); its value is the
        # startup banner (head) and the memory breakdown (tail), so
        # keep those and drop the middle
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
    """The self-cleaning sweep, v9.1 - MODEL granularity: a model is
    eliminated when its F16 candidate has a final score strictly
    below the global best (the F16 score IS the model's max score).
    Elimination deletes the model's whole models/ directory (the
    data ALWAYS stays: answers in results/, records in state). The
    model being examined keeps its files until its F16 sweep
    finishes. Unscored models (pending, interrupted) are never
    touched. Tied leaders are never
    eliminated - time ranks them (recorded per attempt) but the
    human breaks ties."""
    import shutil

    exam = state.get("exam") or {}
    best = -1
    for fam_exam in exam.values():
        if not isinstance(fam_exam, dict):
            continue
        rec = fam_exam.get("F16")
        if isinstance(rec, dict):
            s = rec.get("score")
            if s is not None and s > best:
                best = s
    if best < 0:
        return  # nobody has a score yet - nothing to clean
    for fam, fam_exam in exam.items():
        if not isinstance(fam_exam, dict) or fam == exclude_fam:
            continue
        rec = fam_exam.get("F16")
        if not isinstance(rec, dict):
            continue
        s = rec.get("score")
        if s is None or s >= best:
            # pending, or a SURVIVOR: a stale _eliminated flag (e.g.
            # a fossil of the v9 premature-elimination bug) must be
            # CLEARED - the flag is derived state, the score is truth
            if s is not None and fam_exam.get("_eliminated"):
                fam_exam["_eliminated"] = False
            continue
        famdir = os.path.join(models_dir, fam)
        if not os.path.isdir(famdir):
            continue
        fam_exam["_eliminated"] = True
        shutil.rmtree(famdir, ignore_errors=True)
        print(f"  gc: {fam} eliminated (F16 score {s} < best {best}) - artifacts deleted")


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
        rec = fam_exam.get(rung) or {}
        # a stored final score is final - skip (idempotence)
        if rec.get("score") is not None and not dry_run:
            results[key] = rec
            continue
        if dry_run:
            results[key] = {"planned": f"sweep 0..{max_level} on seeds {seeds}"}
            continue
        gguf = _acquire(fam, rung, models_dir)
        if not gguf:
            rec = {"error": "candidate cannot exist on this machine (unbuildable)"}
            results[key] = rec
            state.setdefault("exam", {}).setdefault(fam, {})[rung] = rec
            _state_store.save_state(state_file, state)
            print(f"  {fam} {rung}: unbuildable - skipped")
            continue
        print(f"-- {fam} {rung}, paper {bell_window(state, fam, models_dir)} tokens --")
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
        results[key] = rec
        # the self-clean FIRST: a model whose F16 scored strictly
        # below the global best leaves the disk (the data always
        # stays), THEN the family push - so this model's own
        # deletions are staged and committed in its push
        _gc(models_dir, state, fam)
        # v9.1: the F16 IS the model - the family is complete after
        # its one candidate; report and push (the watchability ruling)
        if on_family_done is not None:
            try:
                on_family_done(fam)
            except Exception as e:
                print(f"  family-done hook failed (ignored): {e}")
    return results
