"""bench.exam -- the quality exam (phase 2): the chain-hop test with
elevator logic (Daniela's design, KNOWLEDGE.md variants 4b/4c).

The phase-1 sweet walk found the quants that can FILL the context in
time; the exam now DISTINGUISHES QUALITY between them. The task: a
numbered list of (token, signed-number) pairs - the elevator (variant
4c): add the number to the pair's position to find the next pair, 0 =
end marker. This is the chain-following primitive proven teachable to
small models (the 2B solved it once the positions were printed:
"don't ask the model to count; print the numbers").

Protocol (Daniela's exam philosophy):
  - difficulty = number of hops (chain links): level 0 = read the
    start pair (1 pair, end marker), level d = d hops over d+1 pairs
  - PASS/FAIL, no partial credit (the phase-1 score was partial; the
    exam is a bell: the full chain in the ANSWER line, or fail)
  - the bell is a TOKEN CAP, not a time budget (KNOWLEDGE.md's formal
    protocol): no answer within cap completion tokens = fail
  - every model takes the SAME exams: a fixed set of seeds per level;
    a level pass requires passing every seed (n>=2 fights
    understanding-luck near boundaries)
  - applied in sweeps: level 0 tests every sweet spot; the next round's
    only candidates are the previous round's passers; rounds continue
    until no sweet spot passes - the final score is the highest exam
    difficulty achieved
  - answer tokens are recorded for every attempt (the spending
    signature: terse refusal / rumination / solve)

The prompt follows the validated design lessons: the input is stated
WELL-FORMED (no integrity auditing), the demo shows the PROCEDURE on
dummy tokens (outcomes teach nothing), scratchpad is invited (thinking
in the answer is load-bearing), and the final line is a fixed ANSWER
format graded semantically (format drift elsewhere is tolerated).
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

# the fixed seed set - every model takes the SAME exams (the
# protocol's fixed-N-seeds ruling; repetition fights chaos)
def exam_seeds(n: int) -> list[int]:
    return list(range(1, n + 1))

TRIGRAMS = re.compile(r"\b[a-z]{3}\b")

DEMO = """Worked example (dummy tokens, not part of the task):
  1. bbb  +2
  2. aaa  -1
  3. ccc  +1
  4. ddd   0
Start at aaa, which sits at position 2. aaa's number is -1: 2 + (-1) = 1, so the next pair is the one at position 1: bbb. bbb's number is +2: 1 + 2 = 3, so the next pair is the one at position 3: ccc. ccc's number is +1: 3 + 1 = 4, so the next pair is the one at position 4: ddd. ddd's number is 0: end of chain.
ANSWER: aaa, bbb, ccc, ddd"""


def _gen_tokens(rng: random.Random, n: int) -> list[str]:
    """n distinct random 3-letter lowercase trigrams (random on purpose:
    no alphabetical shortcut, no letter-order confusions by design)."""
    seen: set[str] = set()
    out: list[str] = []
    while len(out) < n:
        t = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(3))
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def build_exam(seed: int, level: int) -> dict[str, Any]:
    """One numbered-elevator instance at the given difficulty.

    level = number of hops: level 0 = 1 pair (the given start carries
    the 0 end marker), level d = d+1 pairs, d links to follow. The
    chain is a verified Hamiltonian path over the printed positions
    (every pair visited exactly once, ends at the 0 pair), built by
    construction: the path IS the chain, the jumps are the position
    differences along it. Tokens are fresh per (seed, level) - the
    same seed set for every model, so every candidate takes the SAME
    exam at every level."""
    rng = random.Random(f"exam-{seed}-{level}")
    n_pairs = max(1, level + 1)
    # chain order: pairs[0] is the start; its token is given in the
    # prompt. tokens[0..n-1] are the pair tokens, tokens[n] the
    # dangling end-of-chain token (printed nowhere - the ANSWER stops
    # at the 0 pair).
    tokens = _gen_tokens(rng, n_pairs)
    # printed order = a seeded shuffle of the chain; positions are
    # the printed row numbers (1-based) the jumps refer to
    printed = list(range(n_pairs))
    rng.shuffle(printed)
    rows = []  # printed rows: (position, token, jump)
    for chain_index, printed_index in enumerate(printed):
        last = chain_index == n_pairs - 1
        if last:
            jump = 0
        else:
            jump = printed[chain_index + 1] - printed_index
        rows.append((printed_index + 1, tokens[chain_index], jump))
    start = tokens[0]
    path = list(tokens)
    # verified by construction; the sanity re-check is the design's
    # own no-forks/no-loops rule made code (R-level: generated sets
    # are verified single chains)
    pos = {t: p for p, t, _ in rows}
    walked: list[str] = []
    cur = start
    while True:
        walked.append(cur)
        row = next(r for r in rows if r[1] == cur)
        if row[2] == 0:
            break
        nxt = pos_of(pos, row, rows, row[2])
        assert nxt is not None and nxt not in walked, "chain generation bug"
        cur = nxt
    assert walked == path, "chain generation bug"
    return {"level": level, "seed": seed, "rows": rows, "start": start, "path": path}


def pos_of(pos: dict[str, int], row: tuple[int, str, int], rows: list, jump: int) -> str | None:
    """The token at this row's position + jump (elevator arithmetic)."""
    target = row[0] + jump
    for p, t, _ in rows:
        if p == target:
            return t
    return None


def exam_prompt(exam: dict[str, Any]) -> str:
    """The validated prompt skeleton: well-formed statement, procedure
    demo on dummy tokens, printed indices, scratchpad invitation, and
    the fixed final ANSWER line the grader reads."""
    lines = ["You are solving a CHAIN-FOLLOWING task.", ""]
    lines.append(
        "You are given a numbered list of pairs. Each pair is a 3-letter token "
        "and a signed number. The number tells you where the next pair in the "
        "chain lives: add the number to the pair's position in the list, and the "
        "pair at the resulting position is the next link in the chain. A pair "
        "with the number 0 is the END of the chain."
    )
    lines.append("")
    lines.append(
        "The input is WELL-FORMED: no loops, no typos, exactly one valid chain "
        "exists, and it visits every pair exactly once. Do not spend time "
        "checking this - it is guaranteed."
    )
    lines.append("")
    lines.append(DEMO)
    lines.append("")
    lines.append(f"The task (the chain starts at {exam['start']}):")
    for p, t, j in exam["rows"]:
        lines.append(f"  {p}. {t}  {j:+d}")
    lines.append("")
    lines.append(
        f"Solve the task: start at {exam['start']}, follow the chain pair by "
        "pair until you reach the pair with the number 0."
    )
    lines.append("")
    lines.append(
        "You may work freely - show your steps, there is no penalty for "
        "working out loud and no penalty for being wrong along the way. But "
        "you must finish with a final line of exactly this form:"
    )
    lines.append("ANSWER: <the tokens of the chain in order, comma-separated>")
    return "\n".join(lines)


def ask_exam(port: int, prompt: str, cap: int, no_thinking: bool = True) -> tuple[str, int]:
    """One completion under the bell: max_tokens = the token cap (fail =
    no answer within cap tokens, the formal protocol). Returns the text
    and the ACTUAL completion-token count (the spending signature -
    the answer's cost is a first-class metric, KNOWLEDGE.md's metric
    update)."""
    payload: dict[str, Any] = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": cap,
        "temperature": 0,
        "stream": False,
    }
    if no_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    data = llama_server.post_json(port, "/v1/chat/completions", payload)
    msg = data["choices"][0]["message"]
    text = msg.get("content") or msg.get("reasoning_content") or ""
    usage = data.get("usage") or {}
    return text, int(usage.get("completion_tokens") or 0)


def score_exam(answer: str, exam: dict[str, Any]) -> bool:
    """PASS/FAIL on completion (the protocol's bell): the ANSWER line
    must carry the full chain in order. Graded semantically - the
    tokens are matched case-insensitively in order; surrounding text
    or separators are tolerated, the ORDER is not. Missing ANSWER line
    = fail (the bell rang without an answer: no score for traces)."""
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
    return found == [t.lower() for t in exam["path"]]


def run_family(
    fam: str,
    gguf: str,
    models_dir: str,
    state: dict[str, Any],
    state_file: str,
    port: int,
    cap: int,
    seeds: list[int],
    max_level: int,
    start_level: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    """One family's sweep: every level from the first unrecorded one,
    every seed per level, until the first failing level. The final
    score is the highest level passed (all seeds). Resumable: recorded
    levels are never re-measured (idempotence, the state-store rule)."""
    exam = state.setdefault("exam", {}).setdefault(fam, {})
    exam["rung"] = os.path.basename(gguf)
    levels = exam.setdefault("levels", {})
    answers_dir = os.path.join(models_dir, "exam-results", fam)
    os.makedirs(answers_dir, exist_ok=True)
    answers_path = os.path.join(answers_dir, "answers.jsonl")
    ctx = max(4096, cap + 2048)
    log_path = os.path.join(answers_dir, "exam-server.log")
    proc = None
    score = None
    try:
        if not dry_run:
            proc, healthy = llama_server.start_server(
                gguf, port=port, extra_args=["-c", str(ctx), "--parallel", "1"], log_path=log_path
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
                    inst = build_exam(seed, level)
                    prompt = exam_prompt(inst)
                    attempt: dict[str, Any] = {
                        "seed": seed,
                        "level": level,
                        "expected": inst["path"],
                    }
                    if dry_run:
                        attempt["ok"] = None
                        attempts.append(attempt)
                        continue
                    t0 = time.monotonic()
                    answer, tokens = ask_exam(port, prompt, cap)
                    ok = score_exam(answer, inst)
                    attempt.update(
                        ok=ok,
                        answer_tokens=tokens,
                        elapsed_s=round(time.monotonic() - t0, 1),
                        answer=(answer or "")[-400:],
                    )
                    attempts.append(attempt)
                    with open(answers_path, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(attempt, ensure_ascii=True) + "\n")
                    if not ok:
                        passed = False
                rec = {"pass": passed and not dry_run, "attempts": attempts}
                levels[key] = rec
                _state_store.save_state(state_file, state)
                verdict = "PASS" if rec["pass"] else "FAIL"
                toks = [a.get("answer_tokens") for a in attempts if a.get("answer_tokens") is not None]
                tstr = f", {len(toks)}/{len(seeds)} attempts capped" if len(toks) < len(seeds) else ""
                print(
                    f"  level {level}: {verdict} (seeds "
                    f"{[a.get('ok') for a in attempts]}{tstr})"
                )
            if not rec.get("pass"):
                score = level - 1
                break
            score = level
            level += 1
        if score is not None:
            exam["score"] = score
        if dry_run:
            exam["planned"] = f"sweep {start_level}..{max_level} on seeds {seeds}"
        return exam
    finally:
        if proc is not None:
            llama_server.stop_server(proc, port)


def candidates(state: dict[str, Any], families: list[str] | None) -> list[str]:
    """The exam roster: the phase-1 sweet spots (the in-window boundary
    rungs), param-ascending - only a measured sweet spot is a phase-2
    candidate. An explicit family list filters to its sweet-spot
    members (a family with no sweet spot is reported, not examined)."""
    sweet = state.get("sweet") or {}
    order = [name for name, _ in roster_from_models_md()]
    fams = [f for f in order if (sweet.get(f) or {}).get("sweet_spot")]
    if families:
        wanted = [f.split("=")[0] for f in families]
        missing = [f for f in wanted if f not in fams]
        for f in missing:
            print(f"  {f}: not a sweet-spot candidate - skipped")
        fams = [f for f in fams if f in wanted]
    return fams


def run(
    models_dir: str,
    state: dict[str, Any],
    state_file: str,
    port: int,
    families: list[str] | None,
    cap: int = 2048,
    n_seeds: int = 3,
    max_level: int = 32,
    dry_run: bool = False,
) -> dict[str, Any]:
    """The exam controller: sweeps of escalating difficulty over the
    sweet-spot candidates. Round d's only candidates are round d-1's
    passers; the rounds continue until no candidate passes. The final
    score per candidate is the highest difficulty achieved."""
    seeds = exam_seeds(n_seeds)
    fams = candidates(state, families)
    if not fams:
        return {}
    results: dict[str, Any] = {}
    alive = fams
    level = 0
    while alive and level <= max_level:
        print(f"\n{'=' * 60}\nEXAM ROUND: difficulty {level} ({len(alive)} candidates)")
        survivors = []
        for fam in alive:
            sweet_rec = (state.get("sweet") or {}).get(fam) or {}
            gguf = sweet_rec.get("sweet_spot_file")
            if not gguf or not os.path.isfile(gguf):
                results[fam] = {"error": f"sweet-spot file missing: {gguf}"}
                continue
            rec = (state.get("exam") or {}).get(fam) or {}
            if str(level) in (rec.get("levels") or {}) and not dry_run:
                passed = rec["levels"][str(level)].get("pass")
            elif dry_run:
                passed = None
            else:
                print(f"-- {fam} ({sweet_rec.get('sweet_spot')}) --")
                rec = run_family(
                    fam,
                    gguf,
                    models_dir,
                    state,
                    state_file,
                    port,
                    cap,
                    seeds,
                    max_level,
                    level,
                    dry_run,
                )
                results[fam] = rec
                passed = rec.get("error") is None and (rec.get("levels") or {}).get(
                    str(level), {}
                ).get("pass")
            if passed:
                survivors.append(fam)
            if dry_run:
                survivors = alive  # the plan shows every candidate's sweep
        alive = survivors
        level += 1
    for fam in fams:
        if fam not in results:
            results[fam] = (state.get("exam") or {}).get(fam) or {}
    return results
