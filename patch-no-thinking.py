#!/usr/bin/env python3
"""One-off patcher: add --no-thinking mode to full-benchmark.py (hybrid models,
non-thinking category). Applies byte-exact anchored edits to the CURRENT
full-benchmark.py (thinking+Windows build), verifies the input sha256,
py-compiles the result, and rewrites full-benchmark.py + full-benchmark.py.b64.

Run from the repo root:  python3 patch-no-thinking.py
Then: git add full-benchmark.py full-benchmark.py.b64 && git commit && git push
Delete this script after use (one-off tool).
"""
import base64, hashlib, py_compile, sys

EXPECTED_IN_SHA = "2e8c4c6c76c76e8a4498373be232780f2483dced561140e17f250467cc0b7859"

def main():
    src = open("full-benchmark.py", "rb").read()
    in_sha = hashlib.sha256(src).hexdigest()
    if in_sha != EXPECTED_IN_SHA:
        sys.exit("INPUT MISMATCH: full-benchmark.py sha256 = %s\nexpected %s\n"
                 "(decode the current .b64 first: base64 -d full-benchmark.py.b64 > full-benchmark.py)"
                 % (in_sha, EXPECTED_IN_SHA))
    t = src.decode()
    def rep(old, new, count=1):
        nonlocal t
        n = t.count(old)
        if n != count:
            sys.exit("ANCHOR FAIL: expected %d occurrence(s) of %r, found %d" % (count, old[:60], n))
        t = t.replace(old, new)
        print("  patched: %r" % old[:50])

    # 1. phase3_bench signature
    rep("def phase3_bench(path, corpus, dry_run, thinking=False):",
        "def phase3_bench(path, corpus, dry_run, thinking=False, no_thinking=False):")

    # 2. live-bench cmd threading
    rep('    if thinking:\n        cmd.append("--thinking")',
        '    if thinking:\n        cmd.append("--thinking")\n'
        '    if no_thinking:\n        cmd.append("--no-thinking")')

    # 3. call sites that pass args.thinking -> thread args.no_thinking
    n = t.count("thinking=args.thinking")
    if n < 1:
        sys.exit("ANCHOR FAIL: no 'thinking=args.thinking' call site found - "
                 "print the file's --thinking threading lines and report back")
    t = t.replace("thinking=args.thinking",
                  "thinking=args.thinking, no_thinking=args.no_thinking")
    print("  patched: thinking=args.thinking x%d" % n)

    # 4. argparse: insert --no-thinking twin after the --thinking argument
    i = t.find('ap.add_argument("--thinking"')
    if i < 0:
        sys.exit("ANCHOR FAIL: --thinking argparse not found")
    j = t.find(")\n", i)
    if j < 0:
        sys.exit("ANCHOR FAIL: unterminated --thinking argparse")
    insert_at = j + 2
    twin = ('    ap.add_argument("--no-thinking", action="store_true",\n'
            '                    help="hybrid models, non-thinking category: "\n'
            '                         "run with thinking disabled "\n'
            '                         "(threads --no-thinking to live-bench.py)")\n')
    t = t[:insert_at] + twin + t[insert_at:]
    print("  patched: --no-thinking argparse added")

    # 5. mutual exclusion after parse_args
    rep("    args = ap.parse_args()\n",
        "    args = ap.parse_args()\n"
        "\n"
        "    if args.thinking and args.no_thinking:\n"
        '        ap.error("--thinking and --no-thinking are mutually exclusive")\n')

    # 6. docstring note (module docstring: between the first two triple quotes)
    q1 = t.find('\"\"\"')
    q2 = t.find('\"\"\"', q1 + 3)
    doc = t[q1:q2]
    note = ("\n  Hybrid non-thinking mode (--no-thinking): for hybrid models in the\n"
            "  non-thinking category - threads --no-thinking to live-bench.py\n"
            "  (chat_template_kwargs enable_thinking=false; first-turn dump check\n"
            "  confirms no reasoning appears).\n")
    if "--no-thinking" not in doc:
        t = t[:q2] + note + t[q2:]
        print("  patched: docstring note added")

    # write + verify + encode
    out = t.encode()
    open("full-benchmark.py", "wb").write(out)
    py_compile.compile("full-benchmark.py", doraise=True)
    open("full-benchmark.py.b64", "wb").write(base64.b64encode(out))
    print()
    print("OK. full-benchmark.py: %d bytes, sha256 %s" % (len(out), hashlib.sha256(out).hexdigest()))
    print("full-benchmark.py.b64 rewritten (%d chars)." % len(base64.b64encode(out)))
    print("Sanity lines containing 'no_thinking':")
    for line in t.splitlines():
        if "no_thinking" in line or "--no-thinking" in line:
            print("   ", line.rstrip())

if __name__ == "__main__":
    main()
