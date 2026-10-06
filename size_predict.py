"""Config-only file-size prediction for self-made Q8_0 GGUFs (addendum 110).

Reads a model's config.json (the 2 KB metadata file; no weights
downloaded) and computes the exact tensor inventory for standard
dense transformer architectures (GQA attention + gated MLP, the
qwen/granite/phi shape), then applies the llama.cpp conversion
policy identified in addendum 109:

  - body tensors: Q8_0 blocks, 8.5 bits/weight exactly
  - the OUTPUT tensor (lm_head, or the embedding when
    tie_word_embeddings is true) is kept at F16 by the converter's
    --leave-output-tensor default
  - a tied embedding IS the output tensor -> F16
  - an untied embedding quantizes to Q8_0; the lm_head stays F16

Validated on the measured v3.1 qwen set (7 files): -2.7% to +3.1%.
Non-standard attention variants or MoE configs are refused loudly
rather than mis-predicted.

Usage: python3 size_predict.py config.json [config.json ...]
"""

from __future__ import annotations

import json
import sys

import bench.tee_output as tee_output

GIB = 1024**3
Q8_BYTES = 8.5 / 8
F16_BYTES = 2.0


def fail(cfg_path: str, why: str) -> None:
    print(f"{cfg_path}: REFUSED - {why}")
    sys.exit(1)


def predict(cfg_path: str) -> tuple[float, float]:
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    h = cfg.get("hidden_size")
    layers = cfg.get("num_hidden_layers")
    vocab = cfg.get("vocab_size")
    i = cfg.get("intermediate_size")
    if None in (h, layers, vocab, i):
        fail(cfg_path, "missing hidden_size/num_hidden_layers/vocab_size/intermediate_size")
    if cfg.get("num_experts") or cfg.get("moe_intermediate_size"):
        fail(cfg_path, "MoE architecture not covered (addendum 110 scope: dense)")
    kv = cfg.get("num_key_value_heads") or cfg.get("num_attention_heads")
    heads = cfg.get("num_attention_heads")
    if kv is None or heads is None:
        fail(cfg_path, "no attention head counts")
    head_dim = cfg.get("head_dim", h // heads)
    tied = bool(cfg.get("tie_word_embeddings", False))
    # GQA attention per layer: q,k,v,o (k/v at kv heads)
    attn = (h * h + h * (kv * head_dim) * 2 + h * h) * layers
    # gated MLP: gate, up, down
    mlp = 3 * h * i * layers
    body = attn + mlp
    emb = vocab * h
    tied_size = (body * Q8_BYTES + emb * F16_BYTES) / GIB
    untied_size = (body * Q8_BYTES + emb * Q8_BYTES + emb * F16_BYTES) / GIB
    params = body + emb if tied else body + 2 * emb
    size = tied_size if tied else untied_size
    return params / 1e9, size


def main(argv: list[str]) -> int:
    tee_output.install()
    if len(argv) < 2:
        print(__doc__)
        return 2
    for path in argv[1:]:
        params, gib = predict(path)
        print(f"{path}: params {params:.3f}B, Q8_0 file {gib:.2f} GiB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
