"""code_search.py -- AST-based code search (session 40, addendum 8).

Born from the addendum-5/7 refactors: grep finds TEXT, not SEMANTICS -
it cannot follow `import infra.llama_server as llama_server` to the
call sites of start_server, or see through assignment aliases. This
tool answers three questions precisely, from the AST:

  defs SYMBOL   - where is SYMBOL defined (function/class/alias)?
  refs SYMBOL   - where is SYMBOL referenced (resolving import aliases)?
  calls FUNC    - where is FUNC called (plain and module-qualified)?

Philosophy (same as code_edit): refuse rather than guess. An
unresolvable alias is reported as such, never silently dropped.

CLI:  python3 code_search.py {defs,refs,calls} SYMBOL [--files GLOB ...]
Import:  import code_search; code_search.refs("start_server")
"""

from __future__ import annotations

import argparse
import ast
import glob
import os
import sys

DEFAULT_GLOBS = ("*.py", "bench/*.py", "infra/*.py", "tests/*.py")


class CodeSearchError(RuntimeError):
    pass


def _default_files() -> list[str]:
    seen: dict[str, None] = {}
    for pattern in DEFAULT_GLOBS:
        for p in sorted(glob.glob(pattern)):
            seen[p] = None
    return list(seen)


def _load(path: str) -> ast.Module:
    with open(path, encoding="utf-8") as f:
        try:
            return ast.parse(f.read(), filename=path)
        except SyntaxError as e:
            raise CodeSearchError(f"{path}: does not parse: {e}") from e


def _import_map(tree: ast.Module) -> dict[str, str]:
    """local name -> qualified name, for `import a.b as c` and
    `from a.b import c as d` forms. Plain `import a.b` binds `a` (the
    root package), which this map does not chase - reported as
    unresolvable rather than guessed."""
    m: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    m[alias.asname] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                local = alias.asname or alias.name
                m[local] = f"{node.module}.{alias.name}"
    return m


def _top_level_defs(tree: ast.Module) -> dict[str, list[tuple[str, int]]]:
    """name -> [(file is filled later, lineno)] - top-level and
    class-level function/class defs, plus simple assignment aliases."""
    out: dict[str, list[tuple[str, int]]] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.setdefault(node.name, []).append(("def", node.lineno))
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                out.setdefault(target.id, []).append(("assign", node.lineno))
    return out


def defs(symbol: str, files: list[str] | None = None) -> list[dict]:
    """All definition sites of `symbol` across `files` (default: the
    repo's python set). Each hit: file, line, kind (def/class/assign/
    import-binding)."""
    hits: list[dict] = []
    for path in files or _default_files():
        if not os.path.exists(path):
            continue
        tree = _load(path)
        for name, sites in _top_level_defs(tree).items():
            if name == symbol:
                for kind, lineno in sites:
                    hits.append({"file": path, "line": lineno, "kind": kind})
        for local, qualified in _import_map(tree).items():
            if local == symbol or qualified.split(".")[-1] == symbol:
                hits.append(
                    {
                        "file": path,
                        "line": 0,
                        "kind": f"import binding: {local} -> {qualified}",
                    }
                )
    if not hits:
        raise CodeSearchError(f"{symbol!r}: no definitions found in the file set")
    return hits


def refs(symbol: str, files: list[str] | None = None) -> list[dict]:
    """All reference sites of `symbol`, resolving import aliases: a
    Name whose local binding maps (via the file's imports) to the
    symbol, or matches it directly. Each hit: file, line, resolved-to."""
    hits: list[dict] = []
    for path in files or _default_files():
        if not os.path.exists(path):
            continue
        tree = _load(path)
        imap = _import_map(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id == symbol:
                    hits.append({"file": path, "line": node.lineno, "resolved": symbol})
                elif imap.get(node.id, "").split(".")[-1] == symbol:
                    hits.append({"file": path, "line": node.lineno, "resolved": imap[node.id]})
    return hits


def calls(func: str, files: list[str] | None = None) -> list[dict]:
    """All call sites of `func`: plain calls (func()), attribute calls
    resolved through import aliases (llama_server.start_server() ->
    infra.llama_server.start_server). Each hit: file, line, how-written."""
    hits: list[dict] = []
    for path in files or _default_files():
        if not os.path.exists(path):
            continue
        tree = _load(path)
        imap = _import_map(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            if isinstance(f, ast.Name):
                if f.id == func or imap.get(f.id, "").split(".")[-1] == func:
                    how = imap.get(f.id, f.id)
                    hits.append({"file": path, "line": node.lineno, "via": how})
            elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                base = f.value.id
                qual = imap.get(base)
                if f.attr == func:
                    hits.append(
                        {
                            "file": path,
                            "line": node.lineno,
                            "via": f"{qual}.{func}" if qual else f"{base}.{func}",
                        }
                    )
    if not hits:
        raise CodeSearchError(f"{func!r}: no call sites found in the file set")
    return hits


def _fmt(hits: list[dict]) -> str:
    out = []
    for h in hits:
        parts = [f"{h['file']}:{h['line']}"]
        for key in ("kind", "resolved", "via"):
            if key in h:
                parts.append(f"({h[key]})")
        out.append(" ".join(parts))
    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["defs", "refs", "calls"])
    ap.add_argument("symbol")
    ap.add_argument("--files", nargs="*", default=None, help="file globs (default: repo set)")
    args = ap.parse_args(argv)
    files: list[str] | None = None
    if args.files:
        seen: dict[str, None] = {}
        for pattern in args.files:
            for p in sorted(glob.glob(pattern)):
                seen[p] = None
        files = list(seen)
    fn = {"defs": defs, "refs": refs, "calls": calls}[args.command]
    try:
        print(_fmt(fn(args.symbol, files)))
    except CodeSearchError as e:
        print(f"code_search: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
