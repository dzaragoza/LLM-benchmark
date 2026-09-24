#!/usr/bin/env python3
"""arc-eval.py -- strict ARC-Challenge evaluation on a list of models.

Accuracy stage of the pipeline (its phase 5): full ARC-Challenge test
split (1172 questions, owner ruling 2026-09-23), raw /v1/completions
prompt, max_tokens=1, temperature=0, top-20 logprobs, letter scoring -
the protocol IDENTICAL to the former strict-arc.py. Everything needed
to run ARC lives here: question fetch/cache, prompt build, llama-server
launch/teardown, per-question CSV output, and the completeness check
that guards the ranking stage. Mode-blind by design: the raw single-
token protocol never engages a chat template, so thinking mode is
irrelevant here.

Standalone use (from the repo root):
    python3 arc-eval.py \
        --models "./models/A/A-Q6_K.gguf,./models/B/B-Q8_0.gguf"
    python3 arc-eval.py --models <file> --arc-num 100

Imported by full-benchmark.py (arc_run, arc_csv_path, arc_csv_valid,
load_questions, safe_label).
"""

import argparse
import csv as _csv
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ARC_NUM_DEFAULT = 1172   # full ARC-Challenge test split (owner ruling 2026-09-23)
ARC_RESULTS_DIR_DEFAULT = "./arc-results"
ARC_PORT = 8081
ARC_THREADS = 8
ARC_CTX = 2048
ARC_NGPU = 99

GUIDE = {
    5: [
        "llama-server missing: ./llama-b10964-gpu/llama-server must exist",
        f"port busy: stop leftover servers (ARC uses port {ARC_PORT})",
        "question download blocked: the HF datasets-server must be reachable",
        "transient question errors make the CSV short: rerun the same "
        "command (complete CSVs for other models are kept)",
    ],
}


def fail(phase, rung, what, causes):
    """Abort loudly for one phase, with reader guidance."""
    print()
    print("=" * 60)
    print(f"PHASE {phase} FAILED at {rung}: {what}")
    print("Possible causes and fixes:")
    for c in causes:
        print(f"  - {c}")
    print("Fix the cause, then RERUN THE SAME COMMAND: the script is")
    print("idempotent and will resume from this phase.")
    print("=" * 60)
    sys.exit(1)


def find_server():
    """llama-server binary: repo-relative first, pre-reorg HOME fallback.
    Windows builds ship llama-server.exe - pick the right name."""
    home = os.path.expanduser("~")
    exe = "llama-server.exe" if os.name == "nt" else "llama-server"
    for d in (os.path.join(".", "llama-b10964-gpu"),
              os.path.join(home, "technical_reports", "llama-b10964-gpu")):
        p = os.path.join(d, exe)
        if os.path.isfile(p):
            return p
    return os.path.join(".", "llama-b10964-gpu", exe)


SERVER_BIN = find_server()


# =========================================================== questions

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
            print(f"    http get failed (attempt {attempt + 1}/{retries}): "
                  f"{e} - retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise last_err


def http_post_json(url, payload, timeout=120):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_questions(config, n):
    """ARC questions from the HF datasets-server; cached in the repo root
    (same questions across runs and models - McNemar pairing depends on it)."""
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
            params={"dataset": "allenai/ai2_arc", "config": config,
                    "split": "test", "offset": offset, "length": batch})
        for row in rows["rows"]:
            item = row["row"]
            qs.append({"q": item["question"],
                       "choices": list(zip(item["choices"]["label"],
                                           item["choices"]["text"])),
                       "ans": item["answerKey"]})
    with open(cache_file, "w") as f:
        json.dump(qs, f)
    return qs


def build_prompt(q):
    prompt = f"Question: {q['q']}\n"
    for label, text in q["choices"]:
        prompt += f"{label}) {text}\n"
    prompt += "\nThe answer is"
    return prompt


# =========================================================== scoring

def arc_score_one(q, url):
    """One question: compare logprobs of answer letters."""
    prompt = build_prompt(q)
    t0 = time.perf_counter()
    r = http_post_json(url, {"prompt": prompt, "max_tokens": 1,
                              "temperature": 0, "logprobs": 20})
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


# =========================================================== server

def arc_start_server(model_path):
    """Launch llama-server for ARC. Returns proc."""
    cmd = [SERVER_BIN, "-m", model_path,
           "-t", str(ARC_THREADS), "--port", str(ARC_PORT),
           "-c", str(ARC_CTX), "-ngl", str(ARC_NGPU)]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{ARC_PORT}/health"
    deadline = time.time() + 1800
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return proc
        except OSError:
            pass
        if proc.poll() is not None:
            return None
        time.sleep(2)
    proc.terminate()
    return None


def arc_stop_server(proc):
    """Kill the server and verify the port is free (a lingering server
    silently redirects the next run at the WRONG model)."""
    if proc.poll() is None:
        proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            # Windows: kill the whole tree (children may hold the port).
            subprocess.run(["taskkill", "/PID", str(proc.pid),
                            "/T", "/F"], capture_output=True)
        else:
            proc.kill()
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{ARC_PORT}/health", timeout=2):
                pass
        except OSError:
            return
        time.sleep(2)
    print(f"    WARNING: port {ARC_PORT} still busy after 60s - results "
          "may be invalid!", file=sys.stderr)


# =========================================================== csv

def safe_label(label):
    return "".join(ch if ch.isalnum() or ch in "-_." else "_"
                   for ch in label)


def arc_csv_path(arc_dir, label):
    return os.path.join(arc_dir, safe_label(label) + "-arc-timing.csv")


def arc_csv_valid(path, n):
    """Complete run = exactly n question rows, ids 0..n-1."""
    if not os.path.isfile(path):
        return False
    seen = set()
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                seen.add(int(row["question"]))
    except Exception:
        return False
    return seen == set(range(n))


# =========================================================== run

def arc_run(label, model_path, questions, arc_num, arc_dir,
            on_scored=None, dry_run=False):
    """Full strict-ARC run on one model. Post-condition: complete CSV
    (or a dry-run report). on_scored(label, score) fires once per
    completed model - the caller uses it to persist resume state."""
    csv_path = arc_csv_path(arc_dir, label)
    if arc_csv_valid(csv_path, arc_num):
        print(f"  [5] ARC CSV already complete for {label} - skipping")
        return csv_path
    if dry_run:
        print(f"  [5] would run ARC ({arc_num} questions) on {label}")
        return csv_path
    os.makedirs(arc_dir, exist_ok=True)
    url = f"http://127.0.0.1:{ARC_PORT}/v1/completions"
    print(f"  [5] ARC run: {label}  ({arc_num} questions)")
    proc = arc_start_server(model_path)
    if proc is None:
        fail(5, label, "llama-server did not become healthy for "
             f"{os.path.basename(model_path)}", GUIDE[5])
    correct, done = 0, 0
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = _csv.writer(f)
            w.writerow(["model", "question", "correct", "seconds",
                        "prompt_chars"])
            for i, q in enumerate(questions):
                try:
                    ok, secs, pchars = arc_score_one(q, url)
                    done += 1
                    if ok:
                        correct += 1
                    w.writerow([label, i, int(ok), f"{secs:.4f}", pchars])
                except Exception as e:
                    print(f"    Q{i}: {e}", file=sys.stderr)
    finally:
        arc_stop_server(proc)
    if not arc_csv_valid(csv_path, arc_num):
        fail(5, label, f"ARC run incomplete ({done}/{arc_num} questions "
             "answered - transient errors); rerun the same command",
             GUIDE[5])
    if on_scored is not None:
        on_scored(label, correct)
    print(f"  [5] {label}: {correct}/{arc_num} = "
          f"{100 * correct / arc_num:.1f}%")
    return csv_path


# =========================================================== main

def main():
    ap = argparse.ArgumentParser(
        description="strict ARC-Challenge evaluation on a list of models "
                    "(raw completions, logprob letter scoring)")
    ap.add_argument("--models", required=True,
                    help="comma-separated .gguf files; labels from "
                         "filenames")
    ap.add_argument("--arc-num", type=int, default=ARC_NUM_DEFAULT,
                    help="ARC-Challenge questions (default: full 1172)")
    ap.add_argument("--arc-results-dir", default=ARC_RESULTS_DIR_DEFAULT)
    ap.add_argument("--arc-config", default="ARC-Challenge",
                    choices=["ARC-Challenge", "ARC-Easy"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    jobs = []
    for p in args.models.split(","):
        p = p.strip()
        if not p:
            continue
        if not args.dry_run and not os.path.isfile(p):
            sys.exit(f"model file not found: {p}")
        jobs.append((safe_label(os.path.basename(p)), p))
    if not jobs:
        sys.exit("no model files given")
    questions = load_questions(args.arc_config, args.arc_num)
    for label, path in jobs:
        arc_run(label, path, questions, args.arc_num,
                args.arc_results_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
