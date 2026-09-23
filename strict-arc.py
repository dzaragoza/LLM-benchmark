#!/usr/bin/env python3
"""
strict-arc.py — cross-study strict ARC runner (T14s / 7840U, Linux)
Methodology IDENTICAL across studies: raw /v1/completions prompt,
logprob scoring of answer letters, max_tokens=1, temperature=0,
top-20 logprobs, stdlib only, port hygiene, port 8081, -ngl 99, -c 2048.

NO EDITING NEEDED to switch studies — use --roster:
    python3 strict-arc.py --roster study2 --num 800 --csv runX
    python3 strict-arc.py --roster 51.2  --num 800 --csv runY

  study2 (default): fixed Study #2 roster (Qwen2.5-3B, Phi-3-mini,
      Llama3.2-3B via -hf / self-made files)
  51.2: AUTO-DISCOVERED — scans ~/technical_reports/51.2/ recursively
      for *.gguf files whose names contain a quant tag (q4_k_m, q4_0,
      q5_0, q5_k_m, q6_k, q8_0). F16/full-precision files are excluded
      automatically. Roster names come from filenames, so CSVs never
      collide (full sanitized names, post-bugfix).

CSV output dirs:
  study2 -> ~/technical_reports/102.4/arc-results/
  51.2   -> ~/technical_reports/51.2/arc-results/
  study3 -> ~/technical_reports/study3/arc-results/   (crossover bracket, T14s side)
"""

import urllib.request
import urllib.parse
import json
import argparse
import csv
import subprocess
import time
import sys
import os
import glob as _glob

# ============ constants (no user edits expected) ============
PORT = 8081
THREADS = 8
NGPU_LAYERS = 99

HOME = os.path.expanduser("~")
VULKAN_SERVER = HOME + "/technical_reports/llama-b10964-gpu/llama-server"
QUESTIONS_DIR = HOME + "/technical_reports"          # cross-report dataset cache
OUT_DIRS = {
    "study2": HOME + "/technical_reports/102.4/arc-results",
    "51.2":  HOME + "/technical_reports/51.2/arc-results",
    "study3": HOME + "/technical_reports/study3/arc-results",
}
DIR_51 = HOME + "/technical_reports/51.2"
QUANT_TAGS = ("q4_k_m", "q4_0", "q5_0", "q5_k_m", "q6_k", "q8_0")

# Study #2 roster — specs are full llama-server arg lists.
ROSTER_STUDY2 = [
    ("Qwen2.5-3B Q4_0",   [["-hf", "Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_0"]]),
    ("Qwen2.5-3B Q4_K_M", [["-hf", "Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M"]]),
    ("Qwen2.5-3B Q5_0",   [["-hf", "Qwen/Qwen2.5-3B-Instruct-GGUF:Q5_0"]]),
    ("Qwen2.5-3B Q5_K_M", [["-hf", "Qwen/Qwen2.5-3B-Instruct-GGUF:Q5_K_M"]]),
    ("Qwen2.5-3B Q6_K",   [["-hf", "Qwen/Qwen2.5-3B-Instruct-GGUF:Q6_K"]]),
    ("Qwen2.5-3B Q8_0",   [["-hf", "Qwen/Qwen2.5-3B-Instruct-GGUF:Q8_0"]]),
    ("Phi-3-mini Q4_K_M (shipped)", [["-hf", "microsoft/Phi-3-mini-4k-instruct-gguf:Q4"]]),
    ("Phi-3-mini Q5_K_M (self-made)", [["-m", HOME + "/technical_reports/102.4/phi3-mini/phi3-mini-q5_k_m.gguf"]]),
    ("Llama3.2-3B Q4_K_M", [["-m", HOME + "/technical_reports/102.4/llama3.2-3b/llama3.2-3b-q4_k_m.gguf"]]),
    ("Llama3.2-3B Q5_K_M", [["-m", HOME + "/technical_reports/102.4/llama3.2-3b/llama3.2-3b-q5_k_m.gguf"]]),
    ("Llama3.2-3B Q6_K",   [["-m", HOME + "/technical_reports/102.4/llama3.2-3b/llama3.2-3b-q6_k.gguf"]]),
    ("Llama3.2-3B Q8_0",   [["-m", HOME + "/technical_reports/102.4/llama3.2-3b/llama3.2-3b-q8_0.gguf"]]),
]

# Study #3 (crossover bracket) — T14s side: top 1.5B at full precision.
# Tests the zero-damage ceiling: does F16 beat the quant ladder?
# -hf only (no local file copies, per owner's provenance rule). The repo file
# is qwen2.5-1.5b-instruct-fp16.gguf — the :tag matcher resolves against
# filenames, so try "FP16" then "fp16" (exact matcher behavior unverified).
ROSTER_STUDY3 = [
    ("Qwen2.5-1.5B F16", [
        ["-hf", "Qwen/Qwen2.5-1.5B-Instruct-GGUF:FP16"],
        ["-hf", "Qwen/Qwen2.5-1.5B-Instruct-GGUF:fp16"],
    ]),
    # Phi-3-mini tiny-quant ladder (self-made: pinned converter at
    # ~/technical_reports/llama.cpp, quantizer = b10964 bundle, from official
    # microsoft/Phi-3-mini-4k-instruct safetensors via phi3-mini-f16.gguf)
    ("Phi-3-mini Q3_K_M", [["-m", HOME + "/technical_reports/study3/phi3-mini-q3_k_m.gguf"]]),
    # 2.x-bpw rung: Q2_K (2.96 bpw) — owner's call, swapped for IQ2_M to skip
    # the imatrix build (IQ formats require calibration; K-quants don't).
    ("Phi-3-mini Q2_K",  [["-m", HOME + "/technical_reports/study3/phi3-mini-q2_k.gguf"]]),
    # 1.x-bpw rung: Q1_0 (1.125 bpw, group 64) — same swap rationale.
    ("Phi-3-mini Q1_0",  [["-m", HOME + "/technical_reports/study3/phi3-mini-q1_0.gguf"]]),
]


def build_roster_51():
    """Study #1 (51.2 GB/s) roster — 12 configs, 3 families, from the report:
      Qwen2.5-1.5B-Instruct, glm-edge-1.5b-chat, SmolLM2-1.7B-Instruct,
      each at Q4_K_M / Q5_0 / Q5_K_M / Q6_K.
    Spec resolution per config, in order:
      1. local GGUF anywhere under ~/technical_reports/51.2/ whose path
         contains the family hint AND the quant tag (self-made files
         live here too)
      2. first-party -hf repo fallback (GLM ships the full ladder;
         Qwen and SmolLM2 official repos ship only Q4_K_M and Q8_0 —
         their Q5_0/Q5_K_M/Q6_K have NO -hf fallback and must be local,
         or re-quantized from official safetensors first)
    Configs with no resolvable spec are reported at roster-print time,
    with a y/N prompt, BEFORE anything runs."""
    FAMILIES = [
        # (family label, filename hint, first-party HF repo, study-#1 quant grid)
        ("Qwen2.5-1.5B", "qwen2.5-1.5b-instruct", "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
         ["Q4_0", "Q5_0", "Q5_K_M", "Q6_K"]),          # all self-made in study #1
        ("glm-edge-1.5b", "glm", "zai-org/glm-edge-1.5b-chat-gguf",
         ["Q4_1", "Q5_0", "Q5_1", "Q5_K_M", "Q6_K"]),  # repo ships full ladder
        ("SmolLM2-1.7B", "smollm2", "HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF",
         ["Q4_K_M", "Q5_0", "Q5_K_M", "Q6_K"]),        # only Q4_K_M shipped
    ]
    # per-family quants that the first-party repo genuinely ships
    # (Qwen 1.5B repo confirmed full set 2026-09-22: q4_0..q8_0 — earlier
    #  "only Q4_K_M/Q8_0" note was the 3B repo, wrongly carried over)
    HF_AVAILABLE = {
        "glm": {"Q4_1", "Q5_0", "Q5_1", "Q5_K_M", "Q6_K"},  # full ladder
        "qwen2.5-1.5b-instruct": {"Q4_0", "Q5_0", "Q5_K_M", "Q6_K"},
        "smollm2": {"Q4_K_M"},                               # repo ships Q4_K_M only
    }

    # index all local ggufs once (case-insensitive matching)
    local_files = []
    for f in sorted(_glob.glob(os.path.join(DIR_51, "**", "*.gguf"), recursive=True)):
        local_files.append((f, os.path.basename(f).lower()))

    roster, missing = [], []
    for fam_label, hint, repo, quants in FAMILIES:
        for quant in quants:
            tag = quant.lower()
            name = f"{fam_label} {quant}"
            # candidate 1: local file(s) matching family + quant tag
            # (hint excludes the *base* model: 'qwen2.5-1.5b-base' lacks 'instruct')
            specs = [["-m", f] for f, low in local_files if hint in low and tag in low]
            # candidate 2: first-party -hf, only if the repo ships that tag
            if quant in HF_AVAILABLE[hint]:
                specs.append(["-hf", f"{repo}:{quant}"])
            if specs:
                roster.append((name, specs))
            else:
                missing.append(name)

    if missing:
        print("WARNING — no local file and no first-party -hf fallback for:",
              file=sys.stderr)
        for m in missing:
            print(f"  {m}  (self-made quant; if the .gguf is not under 51.2/, "
                  f"re-quantize from official safetensors with the pinned "
                  f"llama-quantize, then re-run)", file=sys.stderr)
        print("These will be SKIPPED. Continue? [y/N] ", end="", flush=True)
        if input().strip().lower() != "y":
            sys.exit(1)
    return roster
# ============================================================


def http_get_json(url, params=None, timeout=60, retries=4):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last_err = e
            wait = 5 * (attempt + 1)
            print(f"    http get failed (attempt {attempt + 1}/{retries}): {e} — retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise last_err


def http_post_json(url, payload, timeout=120):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_questions(config, n):
    """Fetch ARC questions from the HuggingFace datasets-server API.
    Cache is pinned to the cross-report directory so repeat runs and
    repeat studies don't refetch (same 800 questions across studies —
    this is what makes McNemar pairing valid)."""
    cache_file = os.path.join(QUESTIONS_DIR, f"arc-{config}-test-{n}.json")
    if os.path.exists(cache_file):
        print(f"    using cached questions: {cache_file}", file=sys.stderr)
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)

    qs = []
    for offset in range(0, n, 100):
        batch = min(100, n - offset)
        rows = http_get_json(
            "https://datasets-server.huggingface.co/rows",
            params={
                "dataset": "allenai/ai2_arc",
                "config": config,
                "split": "test",
                "offset": offset,
                "length": batch,
            })
        for row in rows["rows"]:
            item = row["row"]
            qs.append({
                "q": item["question"],
                "choices": list(zip(
                    item["choices"]["label"],
                    item["choices"]["text"],
                )),
                "ans": item["answerKey"],
            })
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(qs, f)
    return qs


def build_prompt(q):
    prompt = f"Question: {q['q']}\n"
    for label, text in q["choices"]:
        prompt += f"{label}) {text}\n"
    prompt += "\nThe answer is"
    return prompt


def score(q, url):
    """One question: compare logprobs of answer letters.
    Returns (correct: bool, seconds: float, prompt_chars: int)."""
    prompt = build_prompt(q)
    t0 = time.perf_counter()
    r = http_post_json(url, {
        "prompt": prompt,
        "max_tokens": 1,
        "temperature": 0,
        "logprobs": 20,
    })
    elapsed = time.perf_counter() - t0

    labels = {label for label, _ in q["choices"]}

    logps = {}
    try:
        top = r["choices"][0]["logprobs"]["content"][0]["top_logprobs"]
        for entry in top:
            tok = entry["token"].strip().rstrip(").,.")
            if tok in labels:
                logps[tok] = max(logps.get(tok, -999), entry["logprob"])
    except (KeyError, IndexError, TypeError):
        pass

    correct = False
    if logps:
        correct = max(logps, key=logps.get) == q["ans"]
    else:
        try:
            gen = r["choices"][0]["text"].strip()
            correct = len(gen) > 0 and gen[0] in labels and gen[0] == q["ans"]
        except (KeyError, IndexError):
            pass
    return correct, elapsed, len(prompt)


def try_server(spec):
    """Launch llama-server with a full arg list. Returns (proc|None, note)."""
    cmd = [
        VULKAN_SERVER,
    ] + spec + [
        "-t", str(THREADS),
        "--port", str(PORT),
        "-c", "2048",
        "-ngl", str(NGPU_LAYERS),
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    url = f"http://127.0.0.1:{PORT}/health"
    deadline = time.time() + 1800  # 30 min max (model downloads can be slow)
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return proc, "ok"
        except OSError:
            pass
        if proc.poll() is not None:
            return None, "died during startup"
        time.sleep(2)
    proc.terminate()
    return None, "never became healthy"


def start_server(specs):
    """Try each candidate spec in order. Returns (proc, spec_used) or raises."""
    last = "no specs"
    for spec in specs:
        proc, note = try_server(spec)
        if proc is not None:
            return proc, spec
        print(f"    spec failed ({note}): {spec}", file=sys.stderr)
        last = f"{note}: {spec}"
        time.sleep(3)
    raise RuntimeError(last)


def stop_server(proc):
    """Kill the server and verify the port is free. On Linux, escalate
    terminate -> kill; llama-server can also linger here and silently
    redirect subsequent runs at the WRONG model."""
    if proc.poll() is None:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
    # wait until the port is actually free (max ~60s)
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2):
                pass  # something still answers — keep waiting
        except OSError:
            return  # port free / no responder
        time.sleep(2)
    print(f"    WARNING: port {PORT} still busy after 60s — results may be invalid!", file=sys.stderr)


def tokenize_stats(questions, port):
    """Tokenize all prompts via llama-server /tokenize; return (mean, total)."""
    toks_url = f"http://127.0.0.1:{port}/tokenize"
    total = 0
    for q in questions:
        payload = {"content": build_prompt(q)}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            toks_url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            r = json.loads(resp.read().decode("utf-8"))
        total += len(r.get("tokens", []))
    return total / len(questions), total


def run_quiz(questions, url, name, csv_path=None):
    """Returns (correct, timings_list)."""
    correct = 0
    timings = []
    f = w = None
    try:
        if csv_path:
            f = open(csv_path, "w", newline="", encoding="utf-8")
            w = csv.writer(f)
            w.writerow(["model", "question", "correct", "seconds", "prompt_chars"])
        for i, q in enumerate(questions):
            try:
                ok, secs, pchars = score(q, url)
                timings.append(secs)
                if ok:
                    correct += 1
                if w:
                    w.writerow([name, i, int(ok), f"{secs:.4f}", pchars])
            except Exception as e:
                print(f"    Q{i}: {e}", file=sys.stderr)
    finally:
        if f:
            f.close()
    return correct, timings


def stats(timings):
    if not timings:
        return None
    s = sorted(timings)
    n = len(s)
    mean = sum(s) / n
    p50 = s[n // 2]
    p95 = s[min(n - 1, int(round(0.95 * n)) - 1 if n > 1 else 0)]
    return {"mean": mean, "p50": p50, "p95": p95, "min": s[0], "max": s[-1]}


def main():
    ap = argparse.ArgumentParser(description="ARC runner, strict evaluation (GPU-only, timed)")
    ap.add_argument("--num", type=int, default=32, help="questions per model")
    ap.add_argument("--config", default="ARC-Challenge",
                    choices=["ARC-Challenge", "ARC-Easy"])
    ap.add_argument("--csv", default=None,
                    help="enable per-question timing CSVs (one per model)")
    ap.add_argument("--roster", default="study2", choices=["study2", "51.2", "study3"],
                    help="which roster to run (51.2 = study #1 grid auto-resolved; study3 = F16 crossover, T14s side)")
    args = ap.parse_args()

    out_dir = OUT_DIRS[args.roster]
    os.makedirs(out_dir, exist_ok=True)

    if args.roster == "51.2":
        roster = build_roster_51()
        if not roster:
            print(f"ERROR: no quantized GGUFs found under {DIR_51} "
                  f"(looked for tags: {', '.join(QUANT_TAGS)})", file=sys.stderr)
            sys.exit(1)
        print("Auto-discovered 51.2 roster:", file=sys.stderr)
        for name, specs in roster:
            spec = specs[0]
            print(f"  {name}  <-  {spec[0]} {spec[1]}", file=sys.stderr)
    else:
        roster = ROSTER_STUDY2 if args.roster == "study2" else ROSTER_STUDY3

    print(f"Loading {args.num} {args.config} questions...", file=sys.stderr)
    questions = load_questions(args.config, args.num)
    print(f"{len(questions)} questions loaded. Roster: {len(roster)} models.", file=sys.stderr)

    url = f"http://127.0.0.1:{PORT}/v1/completions"
    results = []

    for name, specs in roster:
        # sanity check: make sure we're not talking to a leftover server
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2):
                pass
            print(f"    WARNING: port {PORT} answered BEFORE start — leftover server, results would be invalid!", file=sys.stderr)
        except OSError:
            pass
        print(f"[{name}] starting server...", file=sys.stderr)
        try:
            proc, spec_used = start_server(specs)
        except RuntimeError as e:
            print(f"{name}: SKIP ({e})", flush=True)
            continue
        print(f"    using: {spec_used}", file=sys.stderr)
        try:
            mean_tok, total_tok = tokenize_stats(questions, PORT)
            print(f"    prompt tokens: mean {mean_tok:.1f}  total {total_tok}", flush=True)
        except Exception as e:
            print(f"    tokenize_stats failed: {e}", file=sys.stderr)
        # CSV naming: FULL sanitized config name (bugfix 2026-09-22 — the old
        # name.split()[0] scheme made family-prefixed configs overwrite each other).
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in name)
        csv_path = os.path.join(out_dir, f"{safe}-arc-timing.csv") if args.csv else None
        t_start = time.perf_counter()
        try:
            correct, timings = run_quiz(questions, url, name, csv_path)
        finally:
            stop_server(proc)
        wall = time.perf_counter() - t_start

        st = stats(timings)
        pct = correct / len(questions)
        results.append((name, correct, len(questions)))
        print(f"{name} [vulkan]: {correct}/{len(questions)} = {pct:.1%}", flush=True)
        if st:
            print(f"    timing: total {wall:.1f}s wall | per-question "
                  f"mean {st['mean']*1000:.0f}ms  p50 {st['p50']*1000:.0f}ms  "
                  f"p95 {st['p95']*1000:.0f}ms  min {st['min']*1000:.0f}ms  "
                  f"max {st['max']*1000:.0f}ms", flush=True)
            if csv_path:
                print(f"    per-question CSV: {csv_path}", flush=True)

    print("\n" + "=" * 50)
    print("FINAL SCORES (sorted)")
    for name, c, n in sorted(results, key=lambda r: -r[1] / r[2]):
        print(f"  {name}: {c}/{n} = {c / n:.1%}")
    skipped = len(roster) - len(results)
    if skipped:
        print(f"\n({skipped} models skipped — failed to start)")


if __name__ == "__main__":
    main()
