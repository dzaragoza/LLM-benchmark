#!/usr/bin/env python3
"""tokenizer_probe.py -- the w/t first channel, measured offline.

Pre-registered hypothesis (addendum 51, instrument built before any
validation run): a family's measured words/token has two channels -

  1. tokenizer efficiency - how many whitespace words the family's
     tokenizer packs per token on fixed text. Knowable OFFLINE from
     the tokenizer files alone (a few MB, no weights, no server).
  2. sparseness at the worst turn - the model's content CHOICE
     (math/markdown/terse answers). Unknowable before generation;
     measured by the gate's per-turn dumps.

If channel 1 dominates healthy turns, the selection predictor's
unknown-family term becomes: tokenizer w/t (offline) minus a
sparseness risk bounded by the family's first run. The gemma lesson
(addendum 46) is the claim to test: no family constant predicts
content sparseness - but maybe a tokenizer constant predicts the
rest.

Word rule (single-sourced with the gate): words = whitespace tokens,
len(text.split()) - the exact rule speed_gate uses on answers. Text
sets are the registered constants, not new ones: the live corpus's
user prompts (22 turns) and the ARC-Challenge prompt set (1172).

Usage (repo root; transformers is already in requirements.txt for
the converter - no new dependency):

  python3 tokenizer_probe.py --repo Qwen/Qwen3.5-9B
  python3 tokenizer_probe.py --repo microsoft/Phi-4-mini-instruct
  python3 tokenizer_probe.py --dump './models/*/*.live-dump*.json'

  python3 tokenizer_probe.py --repo Qwen/Qwen3.5-9B \
      --dump './models/*/*.live-dump*.json'   # side-by-side view

The --dump mode prints each dump's measured per-turn w/t
distribution (n, min, p50, mean) next to the tokenizer term - the
comparison itself stays a human judgment (no magic verdict). One
family per --repo invocation; tokenizers load from the HF cache
when present, fetching only tokenizer files on first use.
"""

import argparse
import glob
import json
import os
import sys

CORPUS_DEFAULT = "./live-corpus.json"


def count_words(text):
    """The gate's word rule, single-sourced: whitespace words."""
    return len(text.split()) if text.strip() else 0


def load_tokenizer(repo):
    """Tokenizer files only - no weights download."""
    try:
        from transformers import AutoTokenizer
    except ImportError:
        sys.exit("transformers is required (already in requirements.txt "
                 "for the converter; pip install -r requirements.txt)")
    try:
        return AutoTokenizer.from_pretrained(repo)
    except Exception as e:
        sys.exit(f"could not load tokenizer from {repo}: {e}\n"
                 "  (gated repo? accept the license on hf.co and "
                 "hf auth login)")


def corpus_texts(corpus_path):
    """The corpus's user prompts - fixed, pre-registered text set."""
    with open(corpus_path, encoding="utf-8") as f:
        corpus = json.load(f)
    return [t for conv in corpus["conversations"]
            for t in conv["user_turns"]]


def arc_texts(arc_config, arc_num):
    """The ARC prompt set - the second registered text set."""
    import hf_download
    questions = hf_download.load_questions(arc_config, arc_num)
    return [q["prompt"] if isinstance(q, dict) else str(q)
            for q in questions]


def tokenizer_wt(tok, texts, label):
    """Words per token of one text set under one tokenizer."""
    words = sum(count_words(t) for t in texts)
    tokens = sum(len(tok(t)["input_ids"]) for t in texts)
    wt = words / tokens if tokens else 0.0
    print(f"  {label:24} {len(texts):5} texts  "
          f"{words:7} words  {tokens:8} tokens  w/t {wt:.3f}")
    return wt


def dump_wt_distribution(path):
    """Measured per-turn w/t from a live dump (v2.1+: gen_words +
    generated tokens per turn). Returns None for legacy dumps."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    turns = data if isinstance(data, list) else data.get("turns", [])
    pts = []
    for t in turns:
        words = t.get("gen_words")
        toks = t.get("gen_tokens") or t.get("generated_tokens")
        if words is None or not toks:
            continue
        pts.append(words / toks)
    if not pts:
        return None
    pts.sort()
    n = len(pts)
    return {
        "label": (data.get("label") if isinstance(data, dict) else None)
                 or os.path.basename(path),
        "n": n,
        "min": pts[0],
        "p50": pts[n // 2],
        "mean": sum(pts) / n,
        "below": sum(1 for w in pts if w < 0.30),
    }


def main():
    ap = argparse.ArgumentParser(
        description="offline words/token probe: tokenizer efficiency on "
                    "the registered text sets (the w/t predictor's first "
                    "channel, addendum 51)")
    ap.add_argument("--repo", default=None,
                    help="HF repo id - tokenizer files only, no weights")
    ap.add_argument("--corpus", default=CORPUS_DEFAULT)
    ap.add_argument("--arc-config", default="ARC-Challenge",
                    help="ARC config name (hf_download.load_questions "
                         "resolves the repo-root cache "
                         "arc-<config>-test-<n>.json or fetches from "
                         "the HF datasets-server)")
    ap.add_argument("--arc-num", type=int, default=1172,
                    help="number of ARC questions (the registered full "
                         "test split)")
    ap.add_argument("--dump", action="append", default=[],
                    help="live-dump glob(s) for the measured side "
                         "(repeatable)")
    args = ap.parse_args()

    if not args.repo and not args.dump:
        sys.exit("pass --repo (tokenizer side), --dump (measured side), "
                 "or both")

    if args.repo:
        print("=" * 72)
        print(f"TOKENIZER SIDE  ({args.repo} - tokenizer files only)")
        print("=" * 72)
        tok = load_tokenizer(args.repo)
        tokenizer_wt(tok, corpus_texts(args.corpus),
                     "corpus user prompts")
        try:
            arc = arc_texts(args.arc_config, args.arc_num)
            tokenizer_wt(tok, arc, "ARC prompts")
        except Exception as e:
            print(f"  ARC prompts: skipped ({e})")
        print()
        print("  reading: if these terms predict the family's measured "
              "healthy-turn")
        print("  w/t, the unknown-family selection filter needs only the "
              "sparseness")
        print("  channel from the first run. Compare with --dump.")

    if args.dump:
        print()
        print("=" * 72)
        print("MEASURED SIDE  (per-turn w/t distributions from dumps)")
        print("=" * 72)
        paths = sorted(set(p for g in args.dump for p in glob.glob(g)
                           if not p.endswith(".mem.json")))
        if not paths:
            sys.exit("no dumps matched the --dump glob(s)")
        print(f"  {'dump':44} {'n':>4} {'min':>6} {'p50':>6} "
              f"{'mean':>6} {'<0.30':>5}")
        for p in paths:
            d = dump_wt_distribution(p)
            if d is None:
                print(f"  {os.path.basename(p):44} legacy dump "
                      "(no per-turn gen_words/tokens) - skipped")
                continue
            print(f"  {d['label'][:44]:44} {d['n']:4d} {d['min']:6.3f} "
                  f"{d['p50']:6.3f} {d['mean']:6.3f} {d['below']:5d}")
        print()
        print("  reading: min << p50 = the sparseness channel lives in a "
              "few turns;")
        print("  min ~ p50 = the tokenizer term IS the family constant.")


if __name__ == "__main__":
    main()
