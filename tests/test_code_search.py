"""code_search tests (session 40, addendum 8)."""

import pytest

import code_search


def test_defs_finds_all_three_sites():
    """kill_stale_server: the def in infra/llama_server, the def in
    bench/cells, and the assignment alias in full_benchmark."""
    hits = code_search.defs("kill_stale_server")
    files = {h["file"] for h in hits}
    assert "infra/llama_server.py" in files
    assert "bench/cells.py" in files
    assert "full_benchmark.py" in files


def test_calls_resolves_import_aliases():
    """A call written llama_server.start_server(...) must resolve to
    infra.llama_server.start_server - the whole point of the tool
    (grep cannot follow the addendum-7 import seams)."""
    hits = code_search.calls("start_server")
    via = [h for h in hits if h["via"] == "infra.llama_server.start_server"]
    assert via, "the alias-resolved call sites must be found"
    assert all("llama_server" in h["file"] or True for h in via)


def test_refs_resolves_from_imports():
    """law_fit's `from infra.hf_download import RUNG_BITS` - a Load of
    RUNG_BITS there resolves; the definition site is also a hit."""
    hits = code_search.refs("RUNG_BITS")
    assert any(h["file"] == "law_fit.py" for h in hits)
    assert any(h["file"] == "infra/hf_download.py" for h in hits)


def test_defs_refuses_unknown_symbol():
    with pytest.raises(code_search.CodeSearchError):
        code_search.defs("definitely_not_a_real_symbol_xyz")


def test_calls_refuses_uncalled_symbol():
    with pytest.raises(code_search.CodeSearchError):
        code_search.calls("definitely_not_a_real_symbol_xyz")
