#!/usr/bin/env python3
"""full-benchmark.py -- the single end-to-end benchmark for the study.

One script, four stages, one final output: the RANKING of the selected
models by strict ARC-Challenge score, with exact McNemar separation
tests on every consecutive rank gap.

  STAGE A (phases 1-4, per family, downward quant ladder):
    1. DOWNLOAD - premade rung file or the data to create it later.
    2. CREATE   - convert safetensors -> f16, quantize f16 -> rung.
    3. BENCH    - live-bench.py, 1 rep, worst-turn metric.
    4. ANALYZE  - verdict: PASS if worst >= floor - 2*sigma (lenient
                  2-sigma ruling, 2026-09-23); first PASS = selected.
  STAGE B (phase 5): strict ARC-Challenge on every selected model
    (FULL test split, 1172 questions; logprob letter scoring,
    temperature 0; per-question CSVs in --arc-results-dir).
  STAGE C (phase 6): pairwise exact McNemar; final output = ranking.

Everything is IDEMPOTENT and RESUMABLE: ./benchmark-state.json is
rewritten after every phase; rerun the same command to resume. Files
are never re-downloaded/re-quantized; complete ARC CSVs are never
re-run. Every failure stops the script with reader guidance.

Supersedes select-quant.py + strict-arc.py + paired-arc.py (removed
2026-09-23 by owner ruling; their final commits remain in git history).
The ARC protocol is IDENTICAL to strict-arc.py: raw /v1/completions
prompt, max_tokens=1, temperature=0, top-20 logprobs, port 8081,
-ngl 99, -c 2048, -t 8.

Thinking-model category (owner ruling 2026-09-24): benchmarked
separately with --thinking (the SAME worst-turn gate and ARC protocol;
reasoning tokens are measured descriptively - latency spent thinking
is the user's informed choice and is NOT gated). Keep the category in
its own --state-file/--results-file so rankings stay separate.

Ad-hoc use (no selection stage): rank arbitrary model files directly:
    python3 full-benchmark.py --arc-only \
        --arc-models "./models/A/q8.gguf,./models/B/q6.gguf"

Usage (from the repo root):
    python3 full-benchmark.py --dry-run "Qwen/Qwen2.5-3B-Instruct-GGUF" ...
    python3 full-benchmark.py "Qwen/Qwen2.5-3B-Instruct-GGUF" \
        "microsoft/Phi-3-mini-4k-instruct-gguf" \
        "meta-llama/Llama-3.2-3B-Instruct" \
        "google/gemma-3-4b-it-qat-q4_0-gguf=google/gemma-3-4b-it"

  Hybrid non-thinking mode (--no-thinking): for hybrid models in the
  non-thinking category - threads --no-thinking to live-bench.py
  (chat_template_kwargs enable_thinking=false; first-turn dump check
  confirms no reasoning appears).
"""

import argparse
import csv as _csv
import glob
import json
import math
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from itertools import combinations

try:
    from huggingface_hub import hf_hub_download, list_repo_files, snapshot_download
except ImportError:
    sys.exit("huggingface_hub is required: pip install -r requirements.txt "
             "(then activate the repo venv: .venv/bin/activate on "
             "Linux/macOS, .venv\\Scripts\\Activate.ps1 on Windows)")

QUANTIZE_BIN = os.path.join(".", "llama-b10964-gpu",
                            "llama-quantize.exe" if os.name == "nt"
                            else "llama-quantize")
LIVE_BENCH = "./live-bench.py"
CORPUS_DEFAULT = "./live-corpus.json"
MODELS_DIR_DEFAULT = "./models"
STATE_FILE_DEFAULT = "./benchmark-state.json"
RESULTS_FILE_DEFAULT = "./benchmark-results.json"
LADDER_DEFAULT = ["Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M", "Q2_K"]
FLOOR_DEFAULT = 20.0
ARC_NUM_DEFAULT = 1172   # full ARC-Challenge test split (owner ruling 2026-09-23)
ARC_RESULTS_DIR_DEFAULT = "./arc-results"
ARC_PORT = 8081
ARC_THREADS = 8
ARC_CTX = 2048
ARC_NGPU = 99


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


GUIDE = {
    1: [
        "gated repo: accept the license on hf.co and log in (hf auth login)",
        "wrong repo id: verify it exists at https://huggingface.co/<repo>",
        "network / disk space: check the download progress and df -h",
        "python deps: pip install -r requirements.txt (huggingface_hub)",
    ],
    2: [
        "converter deps: pip install -r requirements.txt "
        "(needs transformers, torch, gguf, sentencepiece, protobuf)",
        "pinned converter missing: ./llama.cpp must be the b10964 checkout",
        "quantizer missing: place the b10964 build at ./llama-b10964-gpu/",
        "RAM/disk: f16 conversion needs several GB of each",
    ],
    3: [
        "llama-server missing: ./llama-b10964-gpu/llama-server must exist",
        "corpus missing: python3 live-bench.py --make-corpus",
        "port conflict: stop other llama-server instances (or pass --port)",
        "GPU stack: the server startup log names the GPU - it must "
        "be the real one via the vendor driver, never a software "
        "rasterizer (llvmpipe on Linux)",
    ],
    4: [
        "dump unreadable: the .live-dump.json is malformed or empty",
        "if the bench was interrupted, delete the dump and rerun "
        "(phase 3 will redo it)",
    ],
    5: [
        "llama-server missing: ./llama-b10964-gpu/llama-server must exist",
        f"port busy: stop leftover servers (ARC uses port {ARC_PORT})",
        "question download blocked: the HF datasets-server must be reachable",
        "transient question errors make the CSV short: rerun the same "
        "command (complete CSVs for other models are kept)",
    ],
    6: [
        "CSVs disagree on question count: rerun with the same --arc-num",
        "a CSV is missing: rerun (phase 5 is idempotent per model)",
    ],
}


# =========================================================== rung helpers

def find_rung_file(names, rung):
    tok = rung.lower()
    for f in names:
        low = f.lower()
        if not low.endswith(".gguf") or "mmproj" in low:
            continue
        if "f16" in low or "fp16" in low or "bf16" in low:
            continue
        if tok in low:
            return f
    return None


def find_f16_files(names):
    singles, shards = [], []
    for f in names:
        low = f.lower()
        if not low.endswith(".gguf") or "mmproj" in low:
            continue
        if "00001-of-" in low and ("f16" in low or "fp16" in low):
            prefix = low.split("00001-of-")[0]
            shards.append([n for n in names
                           if n.lower().startswith(prefix)
                           and n.lower().endswith(".gguf")])
        elif "f16" in low or "fp16" in low:
            singles.append(f)
    if shards:
        return sorted(shards[0], key=lambda s: s.lower())
    for f in singles:
        if f.lower().endswith(("-f16.gguf", "-fp16.gguf")):
            return [f]
    return ([singles[0]] if singles else [])


def has_safetensors(names):
    return any(f.lower().endswith(".safetensors") for f in names)


def resolve_f16_local(famdir):
    """Local f16/fp16/bf16 GGUF (fp16 does NOT match a *f16* glob)."""
    if not os.path.isdir(famdir):
        return None
    hits = []
    for pat in ("*f16*.gguf", "*fp16*.gguf", "*bf16*.gguf"):
        hits += glob.glob(os.path.join(famdir, pat))
    hits = [h for h in hits if "mmproj" not in os.path.basename(h).lower()]
    return sorted(hits)[0] if hits else None


def local_rung(famdir, rung):
    if not os.path.isdir(famdir):
        return None
    f = find_rung_file(os.listdir(famdir), rung)
    return os.path.join(famdir, f) if f else None


# =========================================================== state

def load_state(path):
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return {"families": {}}


def save_state(path, state):
    with open(path, "w") as f:
        json.dump(state, f, indent=1)


# =========================================================== phases 1-4

def phase1_download(fam, famdir, rung, model_repo, model_files,
                    source_repo, source_files, dry_run):
    os.makedirs(famdir, exist_ok=True)
    if local_rung(famdir, rung):
        return local_rung(famdir, rung), "local file"
    repo_file = find_rung_file(model_files, rung)
    if repo_file:
        if dry_run:
            return None, f"download {model_repo}/{repo_file}"
        try:
            hf_hub_download(model_repo, repo_file, local_dir=famdir)
        except Exception as e:
            fail(1, rung, f"download of {model_repo}/{repo_file} failed: {e}",
                 GUIDE[1])
        p = local_rung(famdir, rung)
        if not p:
            fail(1, rung, "downloaded file not found afterwards", GUIDE[1])
        return p, f"downloaded {model_repo}/{repo_file}"

    if resolve_f16_local(famdir):
        return None, "quantize from local f16"
    f16_names = find_f16_files(source_files)
    if f16_names:
        if dry_run:
            return None, (f"download f16 from {source_repo} "
                          f"({'+'.join(f16_names)}), quantize")
        try:
            for name in f16_names:
                hf_hub_download(source_repo, name, local_dir=famdir)
        except Exception as e:
            fail(1, rung, f"f16 download from {source_repo} failed: {e}",
                 GUIDE[1])
        if not resolve_f16_local(famdir):
            fail(1, rung, "f16 download finished but file is missing",
                 GUIDE[1])
        return None, f"downloaded f16 from {source_repo}, quantize"
    if has_safetensors(source_files):
        st_dir = os.path.join(famdir, "safetensors-source")
        if dry_run or (os.path.isdir(st_dir)
                       and glob.glob(os.path.join(st_dir, "*.safetensors"))):
            return None, f"safetensors from {source_repo}, convert + quantize"
        try:
            print(f"  [1] downloading safetensors from {source_repo} "
                  "(several GB, once per family)")
            snapshot_download(source_repo, local_dir=st_dir)
        except Exception as e:
            fail(1, rung, f"safetensors download from {source_repo} "
                 f"failed: {e}", GUIDE[1])
        if not glob.glob(os.path.join(st_dir, "*.safetensors")):
            fail(1, rung, "snapshot download finished, no safetensors found",
                 GUIDE[1])
        return None, f"safetensors from {source_repo}, convert + quantize"
    fail(1, rung, f"no {rung} file, no f16 GGUF, no safetensors in "
         f"{source_repo} - nothing to download or quantize from", GUIDE[1])


def phase2_create(fam, famdir, rung, source_repo, plan, dry_run):
    p = local_rung(famdir, rung)
    if p:
        return p
    if dry_run:
        return None
    f16 = resolve_f16_local(famdir)
    if not f16:
        st_dir = os.path.join(famdir, "safetensors-source")
        out_f16 = os.path.join(famdir, fam + "-f16.gguf")
        print("  [2] converting safetensors -> f16 (pinned converter)")
        r = subprocess.run([sys.executable, "./llama.cpp/convert_hf_to_gguf.py",
                            st_dir, "--outfile", out_f16, "--outtype", "f16"])
        if r.returncode != 0 or not os.path.isfile(out_f16):
            fail(2, rung, "f16 conversion failed "
                 "(see the converter output above)", GUIDE[2])
        f16 = out_f16
    out = os.path.join(famdir, f"{fam}-{rung}.gguf")
    print(f"  [2] quantizing {os.path.basename(f16)} -> {rung}")
    r = subprocess.run([QUANTIZE_BIN, f16, out, rung])
    if r.returncode != 0 or not os.path.isfile(out):
        fail(2, rung, "llama-quantize failed "
             "(see the quantizer output above)", GUIDE[2])
    return out


def live_dump_name(path, thinking=False, no_thinking=False):
    """Mode-suffixed dump name: a thinking-mode dump must NEVER be reused
    by a non-thinking run (or vice versa) - the resume check compares
    timestamps only, so the mode must live in the filename (Session 25
    bug: --no-thinking run inherited thinking-mode dumps and reported
    the thinking gate numbers as its own)."""
    if thinking:
        return path + ".live-dump.think.json"
    if no_thinking:
        return path + ".live-dump.nothink.json"
    return path + ".live-dump.json"


def phase3_bench(path, corpus, dry_run, thinking=False, no_thinking=False):
    dump = live_dump_name(path, thinking, no_thinking)
    label = os.path.basename(path)

    def dump_valid():
        if not os.path.isfile(dump):
            return False
        try:
            with open(dump) as f:
                turns = json.load(f)
        except Exception:
            return False
        return any(t.get("model") == label and t.get("server_tps")
                   for t in turns)

    if dump_valid() and os.path.getmtime(dump) > os.path.getmtime(path):
        print("  [3] reusing existing dump (newer than model file)")
        return dump
    if dry_run:
        return dump
    cmd = [sys.executable, LIVE_BENCH, "--corpus", corpus,
           "--models", path, "--repeats", "1", "--dump", dump]
    if thinking:
        cmd.append("--thinking")
    if no_thinking:
        cmd.append("--no-thinking")
    r = subprocess.run(cmd)
    if r.returncode != 0 or not dump_valid():
        fail(3, label, "live-bench.py failed or produced no usable dump "
             "(see its output above)", GUIDE[3])
    return dump


def phase4_analyze(path, floor, thinking=False, no_thinking=False):
    dump = live_dump_name(path, thinking, no_thinking)
    label = os.path.basename(path)
    try:
        with open(dump) as f:
            turns = json.load(f)
    except Exception as e:
        fail(4, label, f"cannot read dump: {e}", GUIDE[4])
    mine = [t for t in turns
            if t.get("model") == label and t.get("server_tps")]
    if not mine:
        fail(4, label, "dump has no turns for this model", GUIDE[4])
    convs = {}
    for t in mine:
        convs.setdefault(t["conv"], []).append(t["server_tps"])
    conv_worsts = [min(v) for v in convs.values()]
    worst = min(conv_worsts)
    mean = sum(t["server_tps"] for t in mine) / len(mine)
    if len(conv_worsts) > 1:
        mu = sum(conv_worsts) / len(conv_worsts)
        sd = math.sqrt(sum((w - mu) ** 2 for w in conv_worsts)
                       / (len(conv_worsts) - 1))
        sigma = sd / math.sqrt(len(conv_worsts))
    else:
        sigma = 0.0
    threshold = floor - 2 * sigma
    if worst >= floor:
        verdict = "PASS (confident)"
    elif worst >= threshold:
        verdict = "PASS (within 2-sigma)"
    else:
        verdict = "FAIL"
    return {"worst": worst, "mean": mean, "sigma": sigma,
            "threshold": threshold, "verdict": verdict,
            "n_turns": len(mine), "n_convs": len(conv_worsts),
            "dump": dump}


# =========================================================== ARC (phase 5)
# Protocol identical to the former strict-arc.py: raw /v1/completions,
# max_tokens=1, temperature=0, top-20 logprobs, stdlib only.

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


def phase5_arc(label, model_path, questions, arc_num, arc_dir,
               state, state_path, dry_run):
    """Full strict-ARC run on one model. Post-condition: complete CSV."""
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
    state.setdefault("arc", {})[label] = {"csv": csv_path,
                                          "score": correct}
    save_state(state_path, state)
    print(f"  [5] {label}: {correct}/{arc_num} = "
          f"{100 * correct / arc_num:.1f}%")
    return csv_path


# =========================================================== rank (phase 6)

def binom_two_sided(k, n, p=0.5):
    def pmf(i):
        return math.comb(n, i) * p ** i * (1 - p) ** (n - i)
    pk = pmf(k)
    return min(1.0, sum(pmf(i) for i in range(n + 1)
                        if pmf(i) <= pk + 1e-12))


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return binom_two_sided(min(b, c), n)


def phase6_rank(labels, arc_num, arc_dir, state, state_path):
    """Pairwise exact McNemar; the script's FINAL OUTPUT is the ranking."""
    models = {}
    for label in labels:
        path = arc_csv_path(arc_dir, label)
        if not arc_csv_valid(path, arc_num):
            fail(6, label, f"ARC CSV missing or short (expected "
                 f"{arc_num} questions)", GUIDE[6])
        per_q = {}
        with open(path, newline="", encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                per_q[int(row["question"])] = bool(int(row["correct"]))
        models[label] = per_q

    scores = {m: sum(v.values()) for m, v in models.items()}
    ranking = sorted(models, key=lambda m: (-scores[m], m))

    pairs = {}
    for m1, m2 in combinations(sorted(models), 2):
        common = set(models[m1]) & set(models[m2])
        b = sum(1 for q in common if models[m1][q] and not models[m2][q])
        c = sum(1 for q in common if not models[m1][q] and models[m2][q])
        diff = 100 * (b - c) / len(common) if common else 0.0
        pairs[f"{m1}|{m2}"] = {"n_common": len(common), "only1": b,
                              "only2": c, "diff_pp": diff,
                              "p_exact": mcnemar_exact(b, c)}

    state["ranking"] = {"arc_num": arc_num,
                        "scores": {m: scores[m] for m in ranking},
                        "order": ranking, "pairs": pairs}
    save_state(state_path, state)

    print()
    print("=" * 60)
    print(f"FINAL RANKING (ARC-Challenge, n={arc_num}, exact McNemar)")
    for i, m in enumerate(ranking, 1):
        print(f"  {i}. {m}: {scores[m]}/{arc_num} = "
              f"{100 * scores[m] / arc_num:.1f}%")
    print("-" * 60)
    print("consecutive-pair McNemar (does the rank order separate?)")
    for i in range(len(ranking) - 1):
        m1, m2 = ranking[i], ranking[i + 1]
        key = f"{m1}|{m2}" if f"{m1}|{m2}" in pairs else f"{m2}|{m1}"
        p = pairs[key]
        print(f"  #{i + 1} vs #{i + 2}: {p['diff_pp']:+.2f} pp  "
              f"(b={p['only1']}, c={p['only2']}, n={p['n_common']}), "
              f"p = {p['p_exact']:.4f}"
              f"{'  SEPARATED' if p['p_exact'] < 0.05 else '  (not separated)'}")
    print("=" * 60)
    return ranking


# =========================================================== selection

def process_family(spec, ladder, corpus, floor, models_dir, state,
                   state_path, dry_run, force, thinking=False,
                   no_thinking=False):
    model_repo, _, source_repo = spec.partition("=")
    if not source_repo:
        source_repo = model_repo
    fam = os.path.basename(model_repo.rstrip("/"))
    famdir = os.path.join(models_dir, fam)
    fst = state["families"].setdefault(
        fam, {"spec": spec, "runs": {}, "selected": None})

    print()
    print("=" * 60)
    print(f"family: {fam}")
    print(f"  model repo : {model_repo}")
    print(f"  source repo: {source_repo}")
    print(f"  folder     : {famdir}")
    if fst["selected"] and not force:
        s = fst["runs"][fst["selected"]]
        print(f"  already selected: {fst['selected']} "
              f"({s['verdict']}, worst {s['worst']:.1f} t/s) - skipping "
              "(--force to redo)")
        return

    try:
        model_files = list_repo_files(model_repo)
        source_files = (model_files if source_repo == model_repo
                        else list_repo_files(source_repo))
    except Exception as e:
        fail(1, "-", f"cannot list repo files for {model_repo}: {e}", GUIDE[1])

    for rung in ladder:
        run = fst["runs"].get(rung, {"phases_done": []})
        fst["runs"][rung] = run
        if str(run.get("verdict", "")).startswith("PASS"):
            break
        if run.get("verdict") == "FAIL":
            continue
        print(f"\n  rung {rung}:")
        if 1 not in run["phases_done"]:
            path, plan = phase1_download(fam, famdir, rung, model_repo,
                                         model_files, source_repo,
                                         source_files, dry_run)
            run["plan"] = plan
            run["phases_done"].append(1)
            save_state(state_path, state)
            print(f"  [1] downloads ok  (plan: {plan})")
        if 2 not in run["phases_done"]:
            path = phase2_create(fam, famdir, rung, source_repo,
                                 run.get("plan", ""), dry_run)
            if path:
                run["file"] = path
            run["phases_done"].append(2)
            save_state(state_path, state)
            print(f"  [2] rung file ready  ({run.get('file', 'dry run')})")
        path = run.get("file") or local_rung(famdir, rung)
        if dry_run and not path:
            print(f"  [3] would live-bench the {rung} file")
            print(f"  [4] would analyze (floor {floor:g} - 2*sigma)")
            continue
        if 3 not in run["phases_done"]:
            dump = phase3_bench(path, corpus, dry_run, thinking,
                                no_thinking)
            run["phases_done"].append(3)
            save_state(state_path, state)
            print(f"  [3] live bench ok  (dump: {os.path.basename(dump)})")
        if 4 not in run["phases_done"]:
            res = phase4_analyze(path, floor, thinking, no_thinking)
            run.update(res)
            run["phases_done"].append(4)
            save_state(state_path, state)
            print(f"  [4] worst {res['worst']:.1f} t/s "
                  f"(mean {res['mean']:.1f}, sigma {res['sigma']:.2f}, "
                  f"threshold {res['threshold']:.1f}) -> {res['verdict']}")
        if str(run["verdict"]).startswith("PASS"):
            fst["selected"] = rung
            run["rung"] = rung
            save_state(state_path, state)
            print(f"  SELECTED {rung} for {fam}")
            break


# =========================================================== main

def main():
    ap = argparse.ArgumentParser(
        description="end-to-end benchmark: quant selection, strict full "
                    "ARC, exact-McNemar ranking - one final output")
    ap.add_argument("families", nargs="*",
                    help='family specs: "model_repo" or '
                         '"model_repo=source_repo" (skip for --arc-only)')
    ap.add_argument("--corpus", default=CORPUS_DEFAULT)
    ap.add_argument("--floor", type=float, default=FLOOR_DEFAULT)
    ap.add_argument("--ladder", default=",".join(LADDER_DEFAULT))
    ap.add_argument("--models-dir", default=MODELS_DIR_DEFAULT)
    ap.add_argument("--state-file", default=STATE_FILE_DEFAULT)
    ap.add_argument("--results-file", default=RESULTS_FILE_DEFAULT)
    ap.add_argument("--arc-num", type=int, default=ARC_NUM_DEFAULT,
                    help="ARC-Challenge questions (default: full 1172)")
    ap.add_argument("--arc-results-dir", default=ARC_RESULTS_DIR_DEFAULT)
    ap.add_argument("--arc-config", default="ARC-Challenge",
                    choices=["ARC-Challenge", "ARC-Easy"])
    ap.add_argument("--arc-only", action="store_true",
                    help="skip selection; ARC + rank only")
    ap.add_argument("--arc-models", default=None,
                    help="comma-separated .gguf files to ARC and rank "
                         "(with --arc-only); labels from filenames")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="redo families that already have a selection")
    ap.add_argument("--thinking", action="store_true",
                    help="thinking-model category: pass --thinking to "
                         "live-bench (same worst-turn gate; reasoning "
                         "measured descriptively). Use separate "
                         "--state-file/--results-file for this category.")
    ap.add_argument("--no-thinking", action="store_true",
                    help="hybrid models, non-thinking category: "
                         "run with thinking disabled "
                         "(threads --no-thinking to live-bench.py)")
    args = ap.parse_args()

    if args.thinking and args.no_thinking:
        ap.error("--thinking and --no-thinking are mutually exclusive")

    ladder = [x.strip() for x in args.ladder.split(",") if x.strip()]

    if not args.dry_run:
        for path, msg in [
            (LIVE_BENCH, f"live-bench.py not found at {LIVE_BENCH} - run "
                         "from the repo root"),
            (args.corpus, f"corpus not found at {args.corpus} - build it: "
                          "python3 live-bench.py --make-corpus"),
            (QUANTIZE_BIN, f"llama-quantize not found at {QUANTIZE_BIN} - "
                           "place the b10964 build in the repo root"),
            ("./llama.cpp/convert_hf_to_gguf.py",
             "converter not found - the llama.cpp checkout must be in "
             "the repo root"),
            (SERVER_BIN, "llama-server not found - place the b10964 "
                         "build in the repo root"),
        ]:
            if not os.path.isfile(path):
                sys.exit(msg)

    state = load_state(args.state_file)

    if args.arc_only:
        if args.arc_models:
            jobs = []
            for p in args.arc_models.split(","):
                p = p.strip()
                if not os.path.isfile(p):
                    sys.exit(f"model file not found: {p}")
                jobs.append((safe_label(os.path.basename(p)), p))
        else:
            jobs = []
            for fam, fst in state["families"].items():
                if fst.get("selected"):
                    run = fst["runs"][fst["selected"]]
                    jobs.append((f"{fam} {fst['selected']}", run["file"]))
            if not jobs:
                sys.exit("no selections in state - run the full pipeline "
                         "first, or pass --arc-models")
        questions = load_questions(args.arc_config, args.arc_num)
        for label, path in jobs:
            phase5_arc(label, path, questions, args.arc_num,
                       args.arc_results_dir, state, args.state_file,
                       args.dry_run)
        if not args.dry_run:
            phase6_rank([l for l, _ in jobs], args.arc_num,
                        args.arc_results_dir, state, args.state_file)
        return

    if not args.families:
        ap.error("no family specs given (or use --arc-only)")

    for spec in args.families:
        process_family(spec, ladder, args.corpus, args.floor,
                       args.models_dir, state, args.state_file,
                       args.dry_run, args.force, args.thinking,
                       args.no_thinking)

    if args.dry_run:
        print("\ndry run complete - no files were downloaded or tested")
        return

    # ---- phases 5-6: full ARC on selected models, then the ranking
    selections = {}
    for fam, fst in state["families"].items():
        if fst.get("selected") and fst["runs"][fst["selected"]].get("file"):
            selections[fam] = fst["runs"][fst["selected"]]
    if selections:
        print()
        print("=" * 60)
        print(f"PHASES 5-6: full {args.arc_config} on selected models "
              f"({args.arc_num} questions each)")
        questions = load_questions(args.arc_config, args.arc_num)
        labels = []
        for fam, sel in selections.items():
            label = f"{fam} {state['families'][fam]['selected']}"
            labels.append(label)
            phase5_arc(label, sel["file"], questions, args.arc_num,
                       args.arc_results_dir, state, args.state_file, False)
        phase6_rank(labels, args.arc_num, args.arc_results_dir,
                    state, args.state_file)
    else:
        print("\nno family has a selection yet - skipping ARC phases")

    # ---- results file: everything for later analysis
    results = []
    for fam, fst in state["families"].items():
        history = [dict(r, rung=rung) for rung, r in fst["runs"].items()]
        history.sort(key=lambda r: ladder.index(r["rung"])
                     if r["rung"] in ladder else 99)
        sel = fst["selected"]
        results.append({"family": fam, "spec": fst["spec"],
                        "history": history,
                        "selected": (dict(fst["runs"][sel], rung=sel)
                                    if sel else None)})
    doc = {"selection": results, "arc": state.get("arc", {}),
           "ranking": state.get("ranking")}
    with open(args.results_file, "w") as f:
        json.dump(doc, f, indent=1)
    print(f"\nresume state -> {args.state_file}")
    print(f"all data     -> {args.results_file}")


if __name__ == "__main__":
    main()
