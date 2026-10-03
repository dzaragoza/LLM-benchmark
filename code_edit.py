#!/usr/bin/env python3
"""code_edit.py - deterministic single-file code edits for the agent
(session 34, addendum 20).

THE PROBLEM IT SOLVES: conversational editing (heredocs, hand-typed
diffs, string-paste tools) fails on whitespace, duplicate matches, and
silent partial writes. This tool makes an edit a TRANSACTION:

  verify -> apply -> write -> flush to disk -> re-read -> assert

Every edit is one of three kinds, each checked BEFORE anything is
written:
  replace   one exact occurrence of old text with new text
  insert    new text before/after an exact anchor line
  delete    one exact occurrence of text

USAGE
  import code_edit
  code_edit.edit("full_benchmark.py", [
      ("replace", old, new),             # one exact occurrence (must be unique)
      ("replace_all", old, new),         # every occurrence
      ("replace_n", old, new, 1),        # occurrence k of old (1-based), for dupes
      ("replace_regex", pattern, new),   # re.sub, count=1; pattern must match once
      ("replace_regex_all", pattern, new),  # re.sub, all matches (>=1 required)
      ("replace_region", start, end, new),  # replace text BETWEEN two unique anchors (exclusive)
      ("insert_before", anchor, new),
      ("insert_after", anchor, new),
      ("delete", old),
      ("set_lines", first, last, new_lines),   # 1-based inclusive line range
      ("insert_lines", line, new_lines),       # insert BEFORE the 1-based line
      ("delete_lines", first, last),           # 1-based inclusive
      ("indent", first, last, "    "),          # prefix each line in range
      ("dedent", first, last, "    "),          # remove the prefix
      ("append", text),                  # end of file
      ("prepend", text),                 # start of file
  ])
  code_edit.write("new_file.py", content)  # create/overwrite - same atomic write
  # -> None on success; raises CodeEditError with file state on failure.

DESIGN RULES
  - edits apply in order; each block is verified against the CURRENT
    buffer (so a later block can rely on an earlier one)
  - write is atomic (temp file + os.replace), then fsync of the file
    AND its directory, so the change survives a hard crash
  - after writing, the file is RE-READ and every block re-verified -
    what the disk says is what the caller gets
  - no fuzzy matching: the caller states exactly what to change;
    ambiguity is a hard error. replace_regex is the one escape hatch
    (re.sub with count=1; the pattern must match exactly once)
  - DELIMITER BALANCE: after applying all blocks, the tool checks that
    the edit did not unbalance the file's quotes, brackets, braces or
    parens (per line for most files; the whole buffer for minified or
    long-line files like our single-line HTML pickers) - a leftover
    duplicated fragment (seen in the wild, session 34 addendum 38)
    is caught at edit time, not at syntax-check time
  - line-range blocks are 1-BASED and inclusive, like an editor's
    selection; new_lines may be a string (one line, no newline
    needed) or a list of strings
"""

from __future__ import annotations

import ast
import os
import re
import tempfile
from collections.abc import Sequence

__all__ = [
    "CodeEditError",
    "edit",
    "edit_many",
    "preview",
    "write",
    "apply_patch_blocks",
    "safe_append",
]


class CodeEditError(Exception):
    """An edit block failed verification - the file was NOT modified."""


def _as_lines(text: str | Sequence[str]) -> list[str]:
    """new_lines may be a string (one line, newline optional) or a
    list/sequence of lines; returns bare lines (no newline)."""
    if isinstance(text, str):
        if not text:
            return []
        if not text.strip():
            return [text.rstrip("\n")]
        return text.rstrip("\n").split("\n")
    return [str(x).rstrip("\n") for x in text]


def _lines_of(buf: str) -> tuple[list[str], bool]:
    """Split into lines; trailing is True when the file ends with a
    newline (the join must restore it)."""
    trailing = buf.endswith("\n")
    lines = buf.split("\n")
    if trailing:
        lines = lines[:-1]
    return lines, trailing


def _join(lines: list[str], trailing: bool) -> str:
    return "\n".join(lines) + ("\n" if trailing else "")


def _check_range(first: object, last: object, n: int, i: int) -> tuple[int, int]:
    if not isinstance(first, int) or not isinstance(last, int):
        raise CodeEditError(f"block {i}: line range must be two ints - got {first!r}, {last!r}")
    if first < 1 or last < first or last > n:
        raise CodeEditError(
            f"block {i}: line range [{first}, {last}] out of bounds (file has {n} lines)"
        )
    return first, last


def _replace_nth(buf: str, old: str, new: str, k: int) -> str:
    """Replace the k-th (1-based) occurrence of old with new."""
    parts = buf.split(old)
    return old.join(parts[:k]) + new + old.join(parts[k:])


def _regex_once(buf: str, pattern: str, i: int, flags: int = 0) -> tuple[str, str]:
    matches = list(re.finditer(pattern, buf, flags))
    if len(matches) != 1:
        raise CodeEditError(
            f"block {i}: replace_regex pattern matched {len(matches)} "
            "times - must match exactly once"
        )
    return pattern, buf


def _region_of(buf: str, start: str, end: str, i: int) -> tuple[int, int]:
    """Locate the region strictly BETWEEN two unique anchors (anchors
    themselves are kept). start must occur exactly once; end must
    occur exactly once AFTER start."""
    n = buf.count(start)
    if n == 0:
        raise CodeEditError(f"block {i}: replace_region start anchor not found:\n{start[:200]}")
    if n > 1:
        raise CodeEditError(f"block {i}: replace_region start anchor found {n} times - add context")
    a = buf.index(start) + len(start)
    tail = buf[a:]
    m = tail.count(end)
    if m == 0:
        raise CodeEditError(
            f"block {i}: replace_region end anchor not found after start:\n{end[:200]}"
        )
    if m > 1:
        raise CodeEditError(
            f"block {i}: replace_region end anchor found {m} times after start - add context"
        )
    return a, a + tail.index(end)


_last_edit_regions: list[tuple[str, str]] = []


def _file_type(path: str) -> str:
    """The check rules differ per file type (session 35, addendum 4):
    prose files legally contain unbalanced quotes and brackets."""
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    if ext in ("md", "markdown", "rst", "txt", "log"):
        return "prose"
    if ext == "py":
        return "python"
    if ext in ("html", "htm", "js", "mjs", "css"):
        return "markup"
    if ext == "json":
        return "json"
    return "code"


SEPARATOR_LIKE = re.compile(r"^\|[-\s|]+\|$")


def _fix_markdown(out: str, path: str) -> str:
    """The md auto-fixer (session 35, addendum 17, author ruling: the
    editor FIXES the mechanical rules instead of failing): a blank
    line before a table header (MD058) and after a table body
    (MD058), and the single trailing newline (MD047), are inserted
    automatically. These are exactly the rules whose fix is unique
    and unambiguous; the judgement rules (MD056 ragged tables, MD055
    row pipes, fence balance) have no safe automatic fix and stay
    lint failures."""
    if _file_type(path) != "prose" or not path.endswith((".md", ".markdown")):
        return out
    lines = out.split("\n")
    fixed: list[str] = []
    for line in lines:
        row = line.startswith("|")
        prev = fixed[-1] if fixed else ""
        prev_blank = prev.strip() == ""
        prev_table = prev.startswith("|")
        if row and not prev_blank and not prev_table:
            fixed.append("")
        if not row and prev_table and not prev_blank and line.strip() != "":
            fixed.append("")
        prev2 = fixed[-2] if len(fixed) >= 2 else ""
        if row and fixed and fixed[-1].strip() == "" and SEPARATOR_LIKE.match(prev2):
            fixed.pop()
        fixed.append(line)
    out = "\n".join(fixed)
    if out:
        out = out.rstrip("\n") + "\n"
    return out


def _check_markdown(src: str, out: str, path: str) -> None:
    """The md-linter gate (session 35, addendum 16, revised 17): the
    mechanical rules (MD058 blank lines around tables, MD047 trailing
    newline) are AUTO-FIXED by _fix_markdown; what remains is the
    judgement class - a markdown edit must not INTRODUCE a violation
    with no safe automatic fix (MD056 ragged tables, MD055 row
    pipes, fence balance). Only NEW problems fail the edit;
    pre-existing violations stay flagged for pre-commit."""
    if _file_type(path) != "prose" or not path.endswith((".md", ".markdown")):
        return
    import md_check

    before = {p.split(": ", 1)[-1] for p in md_check.check_text(path, src)}
    new = [q for q in md_check.check_text(path, out) if q.split(": ", 1)[-1] not in before]
    if new:
        raise CodeEditError(
            f"{path}: the edit introduces markdown-lint violations "
            "(md_check rules, session 35 addendum 17):\n  " + "\n  ".join(new)
        )


def _strip_apostrophes(text: str) -> str:
    """Drop single quotes so the balance check ignores prose
    apostrophes inside markup files, while DOUBLE quotes (HTML/JS
    attribute and string delimiters) stay counted - a truncated
    attribute quote is a real error (session 35, addendum 4)."""
    return text.replace("'", "")


def _check_delimiters(src: str, out: str, path: str) -> None:
    """Sanity check that the edit did not unbalance quotes, brackets,
    braces or parens. File-type aware (session 35, addendum 4):
    - prose (md/txt/...): NO check - apostrophes and brackets in
      sentences are legal; truncation/duplication is still caught by
      the pre-write verify.
    - python: region-based check (each replaced region balances as a
      unit; a region may open a delimiter that closes after it).
    - markup (html/js/css): whole-buffer bracket check, quotes
      stripped (prose inside the page carries apostrophes) - only
      applies when the source already balanced.
    - json/other code: whole-buffer balance, quotes included."""
    ftype = _file_type(path)
    if ftype == "prose":
        return
    pairs = {"(": ")", "[": "]", "{": "}"}
    closers = set(pairs.values())

    def balance_no_underflow(text: str) -> str | None:
        # a region may OPEN a delimiter that closes after it (an edit
        # that inserts a call whose closing paren lands on a later
        # line) or CLOSE one that opened before it (a replace that
        # starts inside a parameter list and ends with ") -> ..."),
        # so unclosed-at-end AND closer-underflow are both fine here;
        # the real failure modes - a MISMATCHED closer or an unclosed
        # quote - are not.
        problem = balance(text)
        if problem and ("quote" in problem):
            return problem
        return None

    pairs = {"(": ")", "[": "]", "{": "}"}
    closers = set(pairs.values())

    def balance(text: str) -> str | None:
        stack: list[tuple[str, int]] = []
        quote: str | None = None
        tq_open: str | None = None
        escape = False
        in_comment = False
        for ln_no, ln in enumerate(text.split("\n"), 1):
            i = 0
            n = len(ln)
            while i < n:
                ch = ln[i]
                if escape:
                    escape = False
                    i += 1
                    continue
                if quote:
                    if ch == "\\":
                        escape = True
                    elif ch == quote:
                        quote = None
                    i += 1
                    continue
                if in_comment:
                    i += 1
                    continue
                if tq_open:
                    end = ln.find(tq_open)
                    if end < 0:
                        break
                    i = end + 3
                    tq_open = None
                    continue
                if ch in ('"', "'"):
                    tq = ln[i : i + 3]
                    if tq == '"""' or tq == "'''":
                        end = ln.find(tq, i + 3)
                        if end < 0:
                            tq_open = tq
                            break
                        i = end + 3
                        continue
                    quote = ch
                elif ch == "#" or (ch == "/" and ln[i : i + 2] == "//"):
                    in_comment = True
                elif ch in pairs:
                    stack.append((ch, ln_no))
                elif ch in closers:
                    if not stack or pairs[stack[-1][0]] != ch:
                        return f"unbalanced {ch!r} (line {ln_no})"
                    stack.pop()
                i += 1
            in_comment = False  # comments do not span lines here
        if quote:
            return f"unclosed quote {quote!r}"
        if stack:
            o, ln_no = stack[-1]
            return f"unclosed {o!r} (opened line {ln_no})"
        return None

    def changed_lines(a: str, b: str) -> bool:
        return a != b

    max_len = max((len(ln) for ln in out.splitlines()), default=0)
    if ftype in ("markup", "json") or max_len > 500:
        # minified/long-line file: balance over the whole buffer, and
        # only warn-grade: compare only if the source already balanced
        if ftype == "markup":
            check_src, check_out = _strip_apostrophes(src), _strip_apostrophes(out)
        else:
            check_src, check_out = src, out
        if balance(check_src) is None:
            problem = balance(check_out)
            if problem:
                raise CodeEditError(
                    f"{path}: delimiter balance check failed after edit ({problem}) - "
                    "the buffer was balanced before; likely a duplicated or truncated fragment"
                )
    else:
        # region-based, not line-based (session 35: a per-line check
        # blames legitimate multi-line code - a lone "print(", an
        # ap.add_argument( block's closing ")" - for pre-existing
        # per-line imbalance. The failure mode the check exists for is
        # a TRUNCATED or DUPLICATED fragment, and that is a property of
        # the edited REGION, not of any single line: each region must
        # balance as a unit.)
        src2, regions = src, []
        for old_text, new_text in _last_edit_regions:
            i = src2.find(old_text)
            j = out.find(new_text)
            if i >= 0 and j >= 0:
                regions.append((j, j + len(new_text)))
            src2 = src2.replace(old_text, "", 1)
        covered = list(regions)
        if not covered and balance(src) is None:
            # insert/delete-only edit: like with like - the whole-buffer
            # check applies only when the source already balanced
            covered = [(0, len(out))]
        for j0, j1 in covered:
            region = out[j0:j1]
            problem = balance_no_underflow(region)
            if problem:
                raise CodeEditError(
                    f"{path}: delimiter balance check failed in the edited "
                    f"region (offset {j0}, {problem}) - likely a duplicated "
                    "or truncated fragment"
                )
    _ = changed_lines  # kept for clarity; per-line comparison handled above


_KINDS = (
    "replace",
    "replace_all",
    "replace_n",
    "replace_regex",
    "replace_regex_all",
    "replace_region",
    "delete",
    "delete_lines",
    "insert_before",
    "insert_after",
    "set_lines",
    "insert_lines",
    "append",
    "prepend",
    "indent",
    "dedent",
)


def _normalize_block(block: tuple) -> tuple:
    """Accept the bare (old, new) / (old,) shorthand (session 35,
    addendum 6): a 2/3-tuple whose first element is not a known kind
    is a replace/delete in disguise - the kind tag is inferred, not
    an error."""
    if not block:
        raise CodeEditError("block: empty tuple")
    kind = block[0]
    if isinstance(kind, str) and kind in _KINDS:
        return tuple(block)
    if len(block) == 2:
        return ("replace", block[0], block[1])
    if len(block) == 3 and all(isinstance(x, str) for x in block):
        raise CodeEditError(
            f"block: first element {kind!r} is not a known kind {_KINDS} - "
            "did you forget the kind tag, or is the target not unique?"
        )
    raise CodeEditError(f"block: cannot interpret {block!r} - expected (kind, old, new)")


def _verify_blocks(src: str, blocks: Sequence[tuple]) -> None:
    """Check every block against src, in order, simulating the apply."""
    buf = src
    for i, block in enumerate(blocks):
        block = _normalize_block(block)
        if len(block) < 2:
            raise CodeEditError(f"block {i}: expected (kind, old, new) - got {block!r}")
        kind = block[0]
        if kind == "replace":
            if len(block) != 3:
                raise CodeEditError(f"block {i}: replace needs (replace, old, new)")
            n = buf.count(block[1])
            if n == 0:
                raise CodeEditError(
                    f"block {i}: replace target not found:\n"
                    f"--- target ---\n{block[1][:400]}\n--- end ---"
                )
            if n > 1:
                raise CodeEditError(
                    f"block {i}: replace target found {n} times - add context to make it unique"
                )
            buf = buf.replace(block[1], block[2], 1)
        elif kind == "delete":
            if len(block) != 2:
                raise CodeEditError(f"block {i}: delete needs (delete, old)")
            n = buf.count(block[1])
            if n == 0:
                raise CodeEditError(f"block {i}: delete target not found:\n{block[1][:400]}")
            if n > 1:
                raise CodeEditError(f"block {i}: delete target found {n} times - add context")
            buf = buf.replace(block[1], "", 1)
        elif kind in ("insert_before", "insert_after"):
            if len(block) != 3:
                raise CodeEditError(f"block {i}: insert needs (kind, anchor, new)")
            n = buf.count(block[1])
            if n == 0:
                raise CodeEditError(f"block {i}: anchor not found:\n{block[1][:200]}")
            if n > 1:
                raise CodeEditError(f"block {i}: anchor found {n} times - add context")
            new = _sep(block[1], block[2], kind == "insert_after")
            new_text = new + block[1] if kind == "insert_before" else block[1] + new
            buf = buf.replace(block[1], new_text, 1)
        elif kind == "replace_all":
            if len(block) != 3:
                raise CodeEditError(f"block {i}: replace_all needs (replace_all, old, new)")
            if buf.count(block[1]) == 0:
                raise CodeEditError(f"block {i}: replace_all target not found:\n{block[1][:400]}")
            buf = buf.replace(block[1], block[2])
        elif kind == "replace_n":
            if len(block) != 4 or not isinstance(block[3], int) or block[3] < 1:
                raise CodeEditError(f"block {i}: replace_n needs (replace_n, old, new, k>=1)")
            n = buf.count(block[1])
            if n < block[3]:
                raise CodeEditError(
                    f"block {i}: replace_n wants occurrence {block[3]} of "
                    f"{n} found - target not present enough times"
                )
            buf = _replace_nth(buf, block[1], block[2], block[3])
        elif kind == "replace_regex":
            if len(block) != 3:
                raise CodeEditError(f"block {i}: replace_regex needs (replace_regex, pattern, new)")
            try:
                _regex_once(buf, block[1], i)
            except re.error as e:
                raise CodeEditError(f"block {i}: bad regex {block[1]!r}: {e}") from e
            buf = re.sub(block[1], block[2], buf, count=1)
        elif kind == "replace_regex_all":
            if len(block) != 3:
                raise CodeEditError(
                    f"block {i}: replace_regex_all needs (replace_regex_all, pattern, new)"
                )
            try:
                matches = len(re.findall(block[1], buf))
            except re.error as e:
                raise CodeEditError(f"block {i}: bad regex {block[1]!r}: {e}") from e
            if matches == 0:
                raise CodeEditError(f"block {i}: replace_regex_all pattern matched nothing")
            buf = re.sub(block[1], block[2], buf)
        elif kind == "replace_region":
            if len(block) != 4:
                raise CodeEditError(
                    f"block {i}: replace_region needs (replace_region, start, end, new)"
                )
            a, b = _region_of(buf, block[1], block[2], i)
            buf = buf[:a] + block[3] + buf[b:]
        elif kind == "set_lines":
            if len(block) != 4:
                raise CodeEditError(f"block {i}: set_lines needs (set_lines, first, last, new)")
            lines, trailing = _lines_of(buf)
            first, last = _check_range(block[1], block[2], len(lines), i)
            buf = _join(lines[: first - 1] + _as_lines(block[3]) + lines[last:], trailing)
        elif kind == "insert_lines":
            if len(block) != 3:
                raise CodeEditError(f"block {i}: insert_lines needs (insert_lines, line, new)")
            lines, trailing = _lines_of(buf)
            _check_range(block[1], block[1], len(lines) + 1, i)
            buf = _join(
                lines[: block[1] - 1] + _as_lines(block[2]) + lines[block[1] - 1 :], trailing
            )
        elif kind == "delete_lines":
            if len(block) != 3:
                raise CodeEditError(f"block {i}: delete_lines needs (delete_lines, first, last)")
            lines, trailing = _lines_of(buf)
            first, last = _check_range(block[1], block[2], len(lines), i)
            buf = _join(lines[: first - 1] + lines[last:], trailing)
        elif kind == "indent":
            if len(block) != 4:
                raise CodeEditError(f"block {i}: indent needs (indent, first, last, prefix)")
            lines, trailing = _lines_of(buf)
            first, last = _check_range(block[1], block[2], len(lines), i)
            buf = _join(
                lines[: first - 1]
                + [block[3] + ln for ln in lines[first - 1 : last]]
                + lines[last:],
                trailing,
            )
        elif kind == "dedent":
            if len(block) != 4:
                raise CodeEditError(f"block {i}: dedent needs (dedent, first, last, prefix)")
            lines, trailing = _lines_of(buf)
            first, last = _check_range(block[1], block[2], len(lines), i)
            pre = block[3] if isinstance(block[3], str) else "    "
            buf = _join(
                lines[: first - 1]
                + [
                    ln[len(pre) :] if ln.startswith(pre) else ln.lstrip()
                    for ln in lines[first - 1 : last]
                ]
                + lines[last:],
                trailing,
            )
        elif kind == "append":
            if len(block) != 2:
                raise CodeEditError(f"block {i}: append needs (append, text)")
            buf = buf + block[1]
        elif kind == "prepend":
            if len(block) != 2:
                raise CodeEditError(f"block {i}: prepend needs (prepend, text)")
            buf = block[1] + buf
        else:
            raise CodeEditError(f"block {i}: unknown kind {kind!r}")


def _sep(anchor: str, new: str, after: bool) -> str:
    """The separator an insert needs (session 35, addendum 9 - register
    entry 6): when the join point sits between two non-newline
    characters the texts would fuse into one broken line, so a newline
    is forced. An explicit blank line in `new` is preserved as-is."""
    edge_a = anchor[-1] if anchor else "\n"
    edge_b = new[0] if new else "\n"
    if after and edge_a != "\n" and edge_b != "\n":
        return "\n" + new
    if not after and edge_b != "\n" and edge_a != "\n":
        return new + "\n"
    return new


def _apply(src: str, blocks: Sequence[tuple]) -> str:
    buf = src
    for block in blocks:
        kind = block[0]
        if kind == "replace":
            buf = buf.replace(block[1], block[2], 1)
        elif kind == "delete":
            buf = buf.replace(block[1], "", 1)
        elif kind == "replace_all":
            buf = buf.replace(block[1], block[2])
        elif kind == "insert_before":
            buf = buf.replace(block[1], _sep(block[1], block[2], False) + block[1], 1)
        elif kind == "insert_after":
            buf = buf.replace(block[1], block[1] + _sep(block[1], block[2], True), 1)
        elif kind == "replace_n":
            buf = _replace_nth(buf, block[1], block[2], block[3])
        elif kind == "replace_regex":
            buf = re.sub(block[1], block[2], buf, count=1)
        elif kind == "replace_regex_all":
            buf = re.sub(block[1], block[2], buf)
        elif kind == "replace_region":
            a, b = _region_of(buf, block[1], block[2], 0)
            buf = buf[:a] + block[3] + buf[b:]
        elif kind == "set_lines":
            lines, trailing = _lines_of(buf)
            buf = _join(lines[: block[1] - 1] + _as_lines(block[3]) + lines[block[2] :], trailing)
        elif kind == "insert_lines":
            lines, trailing = _lines_of(buf)
            buf = _join(
                lines[: block[1] - 1] + _as_lines(block[2]) + lines[block[1] - 1 :], trailing
            )
        elif kind == "delete_lines":
            lines, trailing = _lines_of(buf)
            buf = _join(lines[: block[1] - 1] + lines[block[2] :], trailing)
        elif kind == "indent":
            lines, trailing = _lines_of(buf)
            buf = _join(
                lines[: block[1] - 1]
                + [block[3] + ln for ln in lines[block[1] - 1 : block[2]]]
                + lines[block[2] :],
                trailing,
            )
        elif kind == "dedent":
            lines, trailing = _lines_of(buf)
            pre = block[3] if isinstance(block[3], str) else "    "
            buf = _join(
                lines[: block[1] - 1]
                + [
                    ln[len(pre) :] if ln.startswith(pre) else ln.lstrip()
                    for ln in lines[block[1] - 1 : block[2]]
                ]
                + lines[block[2] :],
                trailing,
            )
        elif kind == "append":
            buf = buf + block[1]
        elif kind == "prepend":
            buf = block[1] + buf
    return buf


def safe_append(path: str, addition: str) -> str:
    """Append text to a file as one verified transaction (session 36,
    addendum 21: born from the day's heredoc-escaping incidents - the
    escaped-newline corruption of test files and the triple-repair
    chain it took). Three guarantees the naive `cat >>` heredoc cannot
    make:
    1. IDEMPOTENT: if the addition's first line already exists in the
       target (the exact append already landed), the file is left
       untouched and reported as such - a retried command can never
       double-append.
    2. NON-CORRUPTING: no shell is involved, so no escaping layer can
       eat the content; the bytes written are exactly the bytes given.
    3. ATOMIC: the write goes through _atomic_write_sync (temp file +
       fsync + os.replace) - a crash mid-append cannot leave a torn
       file. For .py targets the result is compiled (ast.parse)
       BEFORE the write - a syntactically broken addition is refused
       with the file untouched.
    Returns a report string: 'appended N line(s) to <path>' or
    'idempotent skip: addition already present in <path>'.
    """
    existing = open(path, encoding="utf-8").read()
    first_lines = [ln for ln in addition.split("\n") if ln.strip()]
    if first_lines and first_lines[0].strip() in existing:
        return f"idempotent skip: addition already present in {path}"
    out = existing
    if out and not out.endswith("\n"):
        out += "\n"
    out += addition
    if _file_type(path) == "python":
        ast.parse(out)
    _atomic_write_sync(path, out)
    n = addition.count("\n") + (1 if addition and not addition.endswith("\n") else 0)
    return f"appended {n} line(s) to {path}"


def replace_verified(path: str, replaces: Sequence[tuple[str, str]], count: int = 1) -> None:
    """Scripted replaces with asserts, as a first-class transaction
    (session 37, addendum 12). Born from the session-37 incident class
    (notebook addendum 6): when the conversational edit tool fails on
    wrapped-line old_str, the established workaround was a hand-rolled
    `python3 open/write` script with asserts - which BYPASSES every
    guarantee of this tool (the md auto-fixer, the md-lint gate, the
    delimiter check, the atomic synced write). The addendum-6 MD058
    escaped to git exactly that way. This function is that pattern
    done right, so there is never a reason to bypass the editor:

    replaces: a list of (old, new) pairs. Each old must occur EXACTLY
    `count` times in the file (count=1 default: unique; the assert is
    the scripted-replace assert, enforced by the tool now). Pairs
    apply in order against the running buffer, so a later pair may
    match text a earlier pair inserted. On ANY assert failure the file
    is untouched (nothing is written until every pair verifies).

    The full edit() pipeline runs on the assembled result: the md
    auto-fixer (blank lines around tables, trailing newline), the
    md-lint no-new-violations gate, and the delimiter balance check -
    a scripted replace can no longer smuggle a lint break into git.
    """
    blocks: list[tuple] = []
    for i, (old, new) in enumerate(replaces):
        n = src_count(path, old)
        if n != count:
            raise CodeEditError(
                f"{path}: replace pair {i} assert failed: old text occurs "
                f"{n} time(s), expected exactly {count}"
            )
        blocks.append(("replace_n", old, new, 1) if count == 1 else ("replace_all", old, new))
    edit(path, blocks)


def src_count(path: str, text: str) -> int:
    """How many times text occurs in path right now (the assert helper
    for replace_verified; exposed for callers that build their own
    conditions)."""
    return open(path, encoding="utf-8").read().count(text)


def _atomic_write_sync(path: str, content: str) -> None:
    """Write to a temp file in the same directory, fsync it, os.replace
    over the target, then fsync the DIRECTORY entry - the rename is
    what makes it crash-atomic; the dir fsync is what makes the rename
    itself durable."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".code_edit_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        dir_fd = os.open(d, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def edit(path: str, blocks: Sequence[tuple]) -> None:
    """Apply edit blocks to a file as one verified transaction.

    Raises CodeEditError (file untouched) when any block cannot be
    verified against the current content.
    """
    with open(path, encoding="utf-8") as f:
        src = f.read()
    blocks = [_normalize_block(tuple(b)) for b in blocks]
    _verify_blocks(src, blocks)
    out = _apply(src, blocks)
    _last_edit_regions.clear()
    _last_edit_regions.extend((b[1], b[2]) for b in blocks if b[0] == "replace")
    _check_delimiters(src, out, path)
    # verify every post-condition against the IN-MEMORY result BEFORE
    # touching disk (session 35, addendum 4: these checks used to run
    # after the write, so a failed verify left the file MODIFIED and
    # broke the file-untouched contract). They are all deterministic
    # against out, so they belong here.
    _verify_result(out, blocks, path)
    # the md auto-fixer runs AFTER the verify (addendum 17): the
    # post-conditions check the RAW inserted text, then the fixer
    # normalizes the mechanical whitespace (blank lines around
    # tables, the trailing newline) - a fixer pass may legitimately
    # reflow what a block inserted.
    out = _fix_markdown(out, path)
    _check_markdown(src, out, path)
    _atomic_write_sync(path, out)
    with open(path, encoding="utf-8") as f:
        now = f.read()
    if now != out:
        raise CodeEditError(
            f"{path}: disk content diverged after write - the file may be corrupt; re-check"
        )


def _verify_result(out: str, blocks: Sequence[tuple], path: str) -> None:
    """Check every block post-condition against the in-memory result.
    Runs BEFORE the write so a failure leaves the file untouched."""
    for i, block in enumerate(blocks):
        kind = block[0]
        if kind in ("replace", "replace_all", "replace_n") and block[2] and block[2] not in out:
            raise CodeEditError(f"{path}: block {i} verify failed (new text not in the result)")
        if (
            kind
            in (
                "insert_before",
                "insert_after",
                "set_lines",
                "insert_lines",
                "append",
                "prepend",
            )
            and block[-1]
            and _as_lines(block[-1])
            and not all(ln in out for ln in _as_lines(block[-1]))
            and block[-1] not in out
        ):
            raise CodeEditError(
                f"{path}: block {i} verify failed (inserted text not in the result)"
            )
        if kind == "delete" and block[1] in out:
            raise CodeEditError(
                f"{path}: block {i} verify failed (deleted text still in the result)"
            )
        if kind == "replace_regex":
            try:
                if not re.search(block[1], out):
                    raise CodeEditError(
                        f"{path}: block {i} verify failed (pattern result not in the result)"
                    )
            except re.error as e:
                raise CodeEditError(f"{path}: block {i}: bad regex: {e}") from e


def write(path: str, content: str) -> None:
    """Create or overwrite a file with the same atomic, synced write
    as edit(); the ONLY path for new files (an edit on a missing file
    is still an error - write is deliberate). Markdown content runs
    through the auto-fixer (session 35, addendum 17)."""
    content = _fix_markdown(content, path)
    _atomic_write_sync(path, content)
    with open(path, encoding="utf-8") as f:
        if f.read() != content:
            raise CodeEditError(f"{path}: disk content diverged after write - re-check")


def preview(path: str, blocks: Sequence[tuple]) -> str:
    """The unified diff edit() would produce - verifies every block,
    writes NOTHING. For eyeballing a change before committing to it."""
    import difflib

    with open(path, encoding="utf-8") as f:
        src = f.read()
    _verify_blocks(src, blocks)
    out = _apply(src, blocks)
    _check_delimiters(src, out, path)
    out = _fix_markdown(out, path)
    _check_markdown(src, out, path)
    return "".join(
        difflib.unified_diff(
            src.splitlines(keepends=True),
            out.splitlines(keepends=True),
            fromfile=path,
            tofile=path + " (edited)",
        )
    )


def edit_many(edits: Sequence[tuple[str, Sequence[tuple]]]) -> None:
    """Apply one edit() per file as ONE cross-file transaction: every
    file's blocks are verified FIRST; a failure anywhere touches
    NOTHING (the whole set rolls back to git - no half-edited sets).
    edits: [(path, blocks), ...] - paths must be unique."""
    seen: set[str] = set()
    specs = []
    for path, blocks in edits:
        if path in seen:
            raise CodeEditError(f"edit_many: duplicate path {path}")
        seen.add(path)
        with open(path, encoding="utf-8") as f:
            src = f.read()
        _verify_blocks(src, blocks)
        out = _apply(src, blocks)
        _check_delimiters(src, out, path)
        _verify_result(out, blocks, path)
        specs.append((path, src, out))
    for path, _src, out in specs:
        _atomic_write_sync(path, out)
        with open(path, encoding="utf-8") as f:
            if f.read() != out:
                raise CodeEditError(
                    f"{path}: disk content diverged after write - the file may be corrupt; re-check"
                )


def check(path: str, blocks: Sequence[tuple]) -> str:
    """Pre-flight a block set WITHOUT writing (session 35, addendum 6):
    runs every check edit() would run (verify, delimiters, result) and
    returns the preview diff. A failing check raises CodeEditError with
    the exact block and reason. Use this to validate blocks before
    committing to the write."""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    blocks = [_normalize_block(tuple(b)) for b in blocks]
    _verify_blocks(src, blocks)
    out = _apply(src, blocks)
    _check_delimiters(src, out, path)
    _verify_result(out, blocks, path)
    return preview(path, blocks)


def apply_patch_blocks(path: str, blocks: Sequence[tuple]) -> None:
    """Alias kept for callers that think in patch blocks."""
    edit(path, blocks)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", help="file to edit")
    ap.add_argument(
        "--check",
        action="store_true",
        help="verify blocks only (JSON on stdin) - no write",
    )
    ap.add_argument(
        "--preview",
        action="store_true",
        help="print the unified diff edit() would produce - no write",
    )
    args = ap.parse_args()
    import json
    import sys

    spec = json.load(sys.stdin)
    if args.check:
        with open(args.path, encoding="utf-8") as f:
            _verify_blocks(f.read(), [tuple(b) for b in spec["blocks"]])
        print("OK - all blocks verify")
    elif args.preview:
        sys.stdout.write(preview(args.path, [tuple(b) for b in spec["blocks"]]))
    else:
        edit(args.path, [tuple(b) for b in spec["blocks"]])
        print(f"OK - {len(spec['blocks'])} block(s) applied and synced to {args.path}")
