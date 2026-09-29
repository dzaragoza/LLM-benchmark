"""gguf_meta.py (addendum 137c): the GGUF-header context_length
reader - the ladder's trained-window cap straight from metadata
(no server launch; the probe-banner parse failed on the author's
build)."""

import struct

import gguf_meta


def _s(b: bytes) -> bytes:
    return struct.pack("<Q", len(b)) + b


def _build(entries: list[tuple[bytes, int, bytes]]) -> bytes:
    md = struct.pack("<Q", len(entries))
    for k, t, v in entries:
        md += _s(k) + struct.pack("<I", t) + v
    return b"GGUF" + struct.pack("<I", 3) + struct.pack("<Q", 0) + md


def test_uint32_context_length_after_array(tmp_path):
    p = tmp_path / "a.gguf"
    p.write_bytes(
        _build(
            [
                (b".general.architecture", 8, _s(b"qwen2")),
                (
                    b".general.some_array",
                    9,
                    struct.pack("<I", 8)
                    + struct.pack("<Q", 2)
                    + struct.pack("<Q", 2)
                    + b"aa"
                    + struct.pack("<Q", 2)
                    + b"bb",
                ),
                (b"qwen2.context_length", 4, struct.pack("<I", 131072)),
            ]
        )
    )
    assert gguf_meta.gguf_context_length(str(p)) == 131072


def test_string_context_length_with_k_suffix(tmp_path):
    p = tmp_path / "b.gguf"
    p.write_bytes(
        _build(
            [
                (b".general.architecture", 8, _s(b"qwen2")),
                (
                    b"qwen2.context_length",
                    8,
                    _s(b"128K"),
                ),
            ]
        )
    )
    assert gguf_meta.gguf_context_length(str(p)) == 131072


def test_uint64_any_arch_key(tmp_path):
    p = tmp_path / "c.gguf"
    p.write_bytes(
        _build(
            [
                (b".general.architecture", 8, _s(b"llama")),
                (b"llama.context_length", 10, struct.pack("<Q", 262144)),
            ]
        )
    )
    assert gguf_meta.gguf_context_length(str(p)) == 262144


def test_missing_context_length_returns_none(tmp_path):
    p = tmp_path / "d.gguf"
    p.write_bytes(_build([(b".general.architecture", 8, _s(b"qwen2"))]))
    assert gguf_meta.gguf_context_length(str(p)) is None
