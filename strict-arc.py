#!/usr/bin/env python3
"""
strict-arc.py — Phase 2 edition (minimal diff from Phase 1 reference)

Evaluated models (Phase 2, 2 GiB class, first-party/self-made only):
  - Qwen3-1.7B Q4_K_M (self-made: official safetensors -> convert 7d4b92b -> F16 -> Q4_K_M)
  - Qwen3-1.7B Q8_0   (official Qwen/Qwen3-1.7B-GGUF repo)

Methodology IDENTICAL to Phase 1 reference version:
  raw /v1/completions prompt, logprob scoring of answer letters,
  max_tokens=1, temperature=0, top-20 logprobs, stdlib only,
  taskkill port hygiene, port 8081, -ngl 99, -c 2048.

NOTE: no chat template is involved, so Qwen3 thinking-mode cannot
contaminate results (logprob scoring, single token, raw completion).

Usage:
    python strict_arc.py                        (both models, 32 questions)
    python strict_arc.py --num 800              (full Phase 2 run)
    python strict_arc.py --csv results          (per-question timing dump)
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

# ============ EDIT ME ============
PORT = 8081
THREADS = 8
NGPU_LAYERS = 99

VULKAN_SERVER = r"C:\Users\danie\llama-b10964-bin-win-vulkan-x64\llama-server.exe"

# Phase 2 roster — specs are full llama-server arg lists.
# (-hf for repo models, -m for local self-made files.)
ROSTER = [
    ("SmolLM2-1.7B Q4_K_M official",  [["-hf", "HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF:Q4_K_M"]]),
    ("SmolLM2-1.7B Q6_K self-made",   [["-m", r"C:\Users\danie\smollm2-1.7b-Q6_K.gguf"]]),
    ("SmolLM2-1.7B Q5_0 self-made",   [["-m", r"C:\Users\danie\smollm2-1.7b-Q5_0.gguf"]]),
    ("SmolLM2-1.7B Q5_K_M self-made", [["-m", r"C:\Users\danie\smollm2-1.7b-Q5_K_M.gguf"]]),
    ("Qwen2.5-1.5B Q5_0 official",    [["-hf", "Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q5_0"]]),
    ("Qwen2.5-1.5B Q5_K_M official",  [["-hf", "Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q5_K_M"]]),
    ("glm-edge-1.5b Q5_0 official",   [["-hf", "zai-org/glm-edge-1.5b-chat-gguf:Q5_0"]]),
    ("glm-edge-1.5b Q5_K_M official", [["-hf", "zai-org/glm-edge-1.5b-chat-gguf:Q5_K_M"]]),
]
# ================================


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
    Caches to a local JSON file so repeat runs don't refetch."""
    cache_file = f"arc-{config}-test-{n}.json"
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
    """Hard-kill the server (soft terminate is not reliable for llama-server
    on Windows — it can survive and keep holding the port, which silently
    redirects subsequent runs at the WRONG model). Verifies the port is free."""
    if proc.poll() is None:
        if os.name == "nt":
            # /T kills the process tree, /F forces it
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
                    help="basename for per-question timing CSV (one per model)")
    args = ap.parse_args()

    print(f"Loading {args.num} {args.config} questions...", file=sys.stderr)
    questions = load_questions(args.config, args.num)
    print(f"{len(questions)} questions loaded. Roster: {len(ROSTER)} models.", file=sys.stderr)

    url = f"http://127.0.0.1:{PORT}/v1/completions"
    results = []

    for name, specs in ROSTER:
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
        csv_path = f"{name.split()[0]}-arc-timing.csv" if args.csv else None
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
    skipped = len(ROSTER) - len(results)
    if skipped:
        print(f"\n({skipped} models skipped — failed to start)")


if __name__ == "__main__":
    main()