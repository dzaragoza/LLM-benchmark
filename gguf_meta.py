"""ladder_bench.py GGUF metadata path: read context_length / n_ctx_train
straight from the GGUF header (no server launch, no log parsing) -
the robust source for the trained-window cap."""

from __future__ import annotations

import struct


def _gguf_read_metadata_string(data: bytes, off: int, kind: int) -> tuple[str, int]:
    if kind == 8:  # string
        (n,) = struct.unpack_from("<Q", data, off)
        off += 8
        s = data[off : off + n].decode("utf-8", "replace")
        return s, off + n
    if kind == 4:  # uint32
        (v,) = struct.unpack_from("<I", data, off)
        return str(v), off + 4
    if kind == 5:  # int32
        (v,) = struct.unpack_from("<i", data, off)
        return str(v), off + 4
    if kind == 6:  # float32
        (v,) = struct.unpack_from("<f", data, off)
        return str(v), off + 4
    if kind == 7:  # bool
        return str(data[off]), off + 1
    if kind == 9:  # array
        (t,) = struct.unpack_from("<I", data, off)
        off += 4
        (n,) = struct.unpack_from("<Q", data, off)
        off += 8
        for _ in range(n):
            if t == 8:
                _, off = _gguf_read_metadata_string(data, off, t)
            elif t == 10:  # uint64
                off += 8
            elif t == 11:  # int64
                off += 8
            elif t == 12:  # float64
                off += 8
            elif t in (4, 5, 6):
                off += 4
            elif t == 7:
                off += 1
            else:
                raise ValueError(f"array element type {t} unsupported")
        return "[]", off
    if kind == 10:  # uint64
        (v,) = struct.unpack_from("<Q", data, off)
        return str(v), off + 8
    if kind == 11:  # int64
        (v,) = struct.unpack_from("<q", data, off)
        return str(v), off + 8
    if kind == 12:  # float64
        (v,) = struct.unpack_from("<d", data, off)
        return str(v), off + 8
    raise ValueError(f"metadata value type {kind} unsupported")


def _gguf_string_val(s: str) -> int | None:
    t = s.strip()
    if t.endswith("K"):
        try:
            return int(float(t[:-1]) * 1024)
        except ValueError:
            return None
    if t.endswith("M"):
        try:
            return int(float(t[:-1]) * 1024 * 1024)
        except ValueError:
            return None
    try:
        return int(float(t))
    except ValueError:
        return None


def gguf_context_length(path: str) -> int | None:
    """Return the GGUF's context_length / n_ctx_train metadata value
    (int tokens) or None. Reads only the header; no server launch."""
    with open(path, "rb") as f:
        data = f.read(2 * 1024 * 1024)
    if len(data) < 16 or data[:4] != b"GGUF":
        return None
    _, _ver = struct.unpack_from("<II", data, 4)
    n_tensors, n_metadata = struct.unpack_from("<QQ", data, 8)
    off = 24
    ctx: int | None = None
    for _ in range(n_metadata):
        (kind_len,) = struct.unpack_from("<Q", data, off)
        off += 8
        key = data[off : off + kind_len].decode("utf-8", "replace")
        off += kind_len
        (kind,) = struct.unpack_from("<I", data, off)
        off += 4
        val, off = _gguf_read_metadata_string(data, off, kind)
        if key == ".general.context_length" or key.endswith(".context_length"):
            v = _gguf_string_val(val)
            if v is not None:
                ctx = v
    return ctx
