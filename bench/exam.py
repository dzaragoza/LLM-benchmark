"""bench.exam -- the quality exam (phase 2): chain hops + elevator
logic (Daniela's design, KNOWLEDGE.md variants 1 and 4c, the exam
protocol).

The phase-1 sweet walk found the quants that can FILL the context in
time; the exam now DISTINGUISHES QUALITY between them. Each level has
TWO parts:

  part 1  CHAIN FOLLOW (variant 1): pairs (A, B) where B is the first
          item of exactly one other pair - identity matching; the
          chain ends at the dangling token that never heads a pair.
  part 2  ELEVATOR (variant 4c): a numbered list of (token,
          signed-number) pairs - add the number to the pair's position
          to find the next pair, 0 = end marker. The chain-following
          primitive proven teachable to small models once the indices
          are printed ("don't ask the model to count; print the
          numbers").

A level passes only when BOTH parts pass.

Protocol (Daniela's exam philosophy):
  - difficulty = number of hops, adjustable from level 0 upward
  - PASS/FAIL, no partial credit: the ANSWER line must carry the full
    chain in order, graded semantically
  - the BELL is the CONTEXT, integrated with the phase-1 sweet-spot
    measurements: the exam context is min(training window, tg/s x
    1024) - the number of tokens the sweet spot can actually fill
    (the in-window guarantee makes this the window for in-window
    rungs; the tg/s leg binds otherwise). The exam ends when the
    model EMITS an answer (finish_reason=stop) or RUNS OUT OF CONTEXT
    (finish_reason=length) - both conditions are checked, and
    running out is a FAIL (no answer within the bell).
  - the seed follows the REPETITION count: n=1 for the benchmark, so
    every exam instance is built from seed 1 - every model takes the
    SAME exam
  - predictability is protocol-registered (protocol.md:179):
    temperature 0 (greedy argmax), sampler seed 1024, thinking
    disabled - the model behaves as deterministically as it can
  - applied in sweeps: level 0 tests every sweet spot, the next
    round's only candidates are the previous round's passers, rounds
    continue until no sweet spot passes - the final score is the
    highest exam difficulty achieved
  - answer tokens are recorded for every attempt (the spending
    signature: terse refusal / rumination / solve)

The prompts follow the validated design lessons: the input is stated
WELL-FORMED (no integrity auditing), the demos show the PROCEDURE on
dummy tokens, scratchpad is invited (thinking in the answer is
load-bearing), and the final line is a fixed ANSWER format graded
semantically (format drift elsewhere is tolerated).
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
from bench.sweet import roster_from_models_md

# protocol.md:179 - Determinism: temperature 0, seed 1024
SAMPLER_SEED = 1024

# the TIME bell: one exam attempt may run at most 1024s - the UX
# budget itself (the same 1024 as tg/s x 1024 = context). The
# conversation expires: the streamed read is cut and the socket
# closed, cancelling the server-side generation
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
    """One completion under BOTH bells, streamed and cut at the wall:

    - the TOKEN bell: max_tokens = the paper's remaining generation
      tokens (finish_reason 'length' = the paper is full)
    - the TIME bell (deadline): the conversation EXPIRES - the client
      stops reading and closes the socket, which cancels the
      server-side generation (finish_reason 'time_limit'). The 1024s
      UX budget enforced at its source, per attempt.

    Streaming instead of the silent blocking wait: chunks arrive as
    the model writes and the deadline is checked per chunk - the cut
    is clean and the wait is bounded. Returns (text,
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
    tolerated, the ORDER not. An exam that ran out of context
    (finish_reason 'length') FAILS even if a partial answer leaked -
    the bell rang before completion. Missing ANSWER line = fail."""
    if finish_reason in ("length", "time_limit"):
        return False
    text = (answer or "").lower()
    m = re.search(r"answer\s*:\s*(.+)", text)
    line = m.group(1) if m else ""
    if not m:
        # format-instruction drift is real (KNOWLEDGE.md): accept a
        # bare final line that starts with the chain's start token
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
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


def bell_rung(window: int | None, tg: float | None, time_factor: int = 1024) -> int | None:
    """The bell for ONE rung: min(training window, tg/s x time_factor).
    Under the window the window binds; over it the rung's own fill
    rate binds. The time_factor is the run's time parameter (the same
    1024 that set the sweet spots)."""
    if not window or tg is None:
        return None
    return max(1024, min(int(window), int(tg * time_factor)))


def candidates(
    state: dict[str, Any], families: list[str] | None, models_dir: str = "models"
) -> list[tuple[str, str, str]]:
    """The exam roster as (family, rung, gguf) tuples, param-ascending,
    per the v8 rule pair:

      tg/s x 1024 > window (UNDER): the boundary rung is THE sweet
      spot - one candidate.
      no rung meets it (OVER): EVERY measured quant is a sweet spot -
      the whole ladder, one candidate per rung, each with its own
      bell (min(window, its own tg x 1024)).

    An explicit family list filters; each family prints its regime.
    Rungs whose file is missing are reported and skipped (the sweep
    continues with the working ones)."""
    import infra.hf_download as hf_download

    sweet = state.get("sweet") or {}
    order = [name for name, _ in roster_from_models_md()]
    fams = order if not families else [f.split("=")[0] for f in families]
    out: list[tuple[str, str, str]] = []
    for fam in fams:
        rec = sweet.get(fam) or {}
        rungs = rec.get("rungs") or {}
        if rec.get("over_window"):
            rung_names = [r for r, m in rungs.items() if m.get("tg") is not None]
            regime = "OVER the window - every measured quant is a sweet spot"
        elif rec.get("sweet_spot"):
            rung_names = [rec["sweet_spot"]]
            regime = "UNDER the window - the boundary rung"
        else:
            print(f"  {fam}: no measured rungs - skipped")
            continue
        famdir = os.path.join(models_dir, fam)
        resolved = []
        for r in rung_names:
            gguf = hf_download.local_rung(famdir, r) or os.path.join(
                famdir, f"{fam}-{r}.gguf"
            )
            if os.path.isfile(gguf):
                resolved.append((fam, r, gguf))
            else:
                print(f"  {fam} {r}: file missing ({gguf}) - skipped")
        if resolved:
            print(f"  {fam}: {len(resolved)} candidate(s), {regime}")
        out.extend(resolved)
    return out


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
    sweet_rec = (state.get("sweet") or {}).get(fam) or {}
    rung_rec = (sweet_rec.get("rungs") or {}).get(rung) or {}
    ctx = bell_rung(sweet_rec.get("window"), rung_rec.get("tg"), time_factor)
    if ctx is None:
        return {"error": "no measured rung (window/tg) to set the bell"}
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
            # and template must fit alongside the generation budget)
            proc, healthy = llama_server.start_server(
                gguf,
                port=port,
                extra_args=["-c", str(ctx + 2048), "--parallel", "1"],
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
                f"bell ctx {ctx} (window {sweet_rec.get('window')} vs tg/s x 1024), "
                f"sweep {start_level}..{max_level} on seeds {seeds}, 2 parts per level"
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


def fail_reason(rec: dict[str, Any]) -> str:
    """Why the candidate failed its highest exam: read the last FAILING
    level's attempts and classify the mode - the quick diagnostic the
    ledger wants. Never a score, a REASON:
      out of context   the bell rang (finish_reason length) - the
                       paper filled before the answer
      wrong chain      an answer arrived, the tokens/order were wrong
      error            a transport/tool failure, not the model's
                       fault
      no record        nothing measured (or only passes stored)"""
    levels = rec.get("levels") or {}
    fail_keys = [k for k in levels if not levels[k].get("pass")]
    if not fail_keys:
        return "no record"
    top = max(fail_keys, key=int)
    attempts = levels[top].get("attempts") or []
    reasons = []
    for a in attempts:
        if str(a.get("finish_reason") or "").startswith("error"):
            reasons.append("error")
        elif a.get("finish_reason") == "length" or a.get("ok") is None and not a.get("prompt"):
            reasons.append("out of context")
        elif a.get("ok") is False:
            reasons.append("wrong chain")
    if "error" in reasons and "wrong chain" not in reasons and "out of context" not in reasons:
        return "error"
    if "out of context" in reasons:
        return "out of context"
    if "wrong chain" in reasons:
        return "wrong chain"
    return "unknown"


def candidates(
    state: dict[str, Any], families: list[str] | None, models_dir: str = "models"
) -> list[tuple[str, str, str]]:
    """The exam roster as (family, rung, gguf) tuples, param-ascending,
    per the v8 rule pair:

      tg/s x 1024 > window (UNDER): the boundary rung is THE sweet
      spot - one candidate.
      no rung meets it (OVER): EVERY measured quant is a sweet spot -
      the whole ladder, one candidate per rung, each with its own
      bell (min(window, its own tg x 1024)).

    An explicit family list filters; each family prints its regime.
    Rungs whose file is missing are reported and skipped (the sweep
    continues with the working ones)."""
    import infra.hf_download as hf_download

    sweet = state.get("sweet") or {}
    order = [name for name, _ in roster_from_models_md()]
    fams = order if not families else [f.split("=")[0] for f in families]
    out: list[tuple[str, str, str]] = []
    for fam in fams:
        rec = sweet.get(fam) or {}
        rungs = rec.get("rungs") or {}
        if rec.get("over_window"):
            rung_names = [r for r, m in rungs.items() if m.get("tg") is not None]
            regime = "OVER the window - every measured quant is a sweet spot"
        elif rec.get("sweet_spot"):
            rung_names = [rec["sweet_spot"]]
            regime = "UNDER the window - the boundary rung"
        else:
            print(f"  {fam}: no measured rungs - skipped")
            continue
        famdir = os.path.join(models_dir, fam)
        resolved = []
        for r in rung_names:
            gguf = hf_download.local_rung(famdir, r) or os.path.join(
                famdir, f"{fam}-{r}.gguf"
            )
            if os.path.isfile(gguf):
                resolved.append((fam, r, gguf))
            else:
                print(f"  {fam} {r}: file missing ({gguf}) - skipped")
        if resolved:
            print(f"  {fam}: {len(resolved)} candidate(s), {regime}")
        out.extend(resolved)
    return out


def run(
    models_dir: str,
    state: dict[str, Any],
    state_file: str,
    port: int,
    families: list[str] | None,
    n_seeds: int = 1,
    max_level: int = 32,
    dry_run: bool = False,
    time_factor: int = 1024,
) -> dict[tuple[str, str], Any]:
    """The exam controller: sweeps of escalating difficulty over the
    sweet-spot candidates - (model, quant) pairs. Round d's only
    candidates are round d-1's passers; the rounds continue until no
    candidate passes. The final score per candidate is the highest
    difficulty achieved (both parts)."""
    seeds = exam_seeds(n_seeds)
    cands = candidates(state, families, models_dir)
    if not cands:
        return {}
    results: dict[tuple[str, str], Any] = {}
    alive = cands
    level = 0
    while alive and level <= max_level:
        print(f"\n{'=' * 60}\nEXAM ROUND: difficulty {level} ({len(alive)} candidates)")
        survivors = []
        for cand in alive:
            fam, rung, gguf = cand
            key = (fam, rung)
            fam_exam = (state.get("exam") or {}).get(fam) or {}
            # old-era rollback records are family-keyed (the boundary
            # candidate directly); new-era records are rung-keyed
            rec = fam_exam.get(rung) or {}
            if not rec and "levels" in fam_exam:
                rec = fam_exam
            if str(level) in (rec.get("levels") or {}) and not dry_run:
                passed = rec["levels"][str(level)].get("pass")
            elif dry_run:
                passed = None
            else:
                sweet_rec = (state.get("sweet") or {}).get(fam) or {}
                rung_rec = (sweet_rec.get("rungs") or {}).get(rung) or {}
                print(
                    f"-- {fam} {rung}, bell "
                    f"{bell_rung(sweet_rec.get('window'), rung_rec.get('tg'), time_factor)} "
                    f"tokens --"
                )
                # one candidate's failure never kills the exam (the
                # author's ruling: continue with the working ones) -
                # any exception is recorded and the sweep moves on
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
                        level,
                        dry_run,
                        time_factor,
                    )
                except SystemExit as e:
                    if e.code == 130:
                        raise
                    rec = {"error": f"exam run failed: {e.code}"}
                except Exception as e:
                    rec = {"error": f"exam run failed: {e}"}
                results[key] = rec
                passed = rec.get("error") is None and (rec.get("levels") or {}).get(
                    str(level), {}
                ).get("pass")
            if passed:
                survivors.append(cand)
            if dry_run:
                survivors = alive  # the plan shows every candidate's sweep
        alive = survivors
        level += 1
    for cand in cands:
        key = (cand[0], cand[1])
        if key not in results:
            fam, rung = key
            results[key] = ((state.get("exam") or {}).get(fam) or {}).get(rung) or {}
    return results
