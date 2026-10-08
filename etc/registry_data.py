#!/usr/bin/env python3
"""Registry data store: every models.md model's own config.json extract,
kept checked-in so audits are a git diff, not 50 hub fetches.

Usage:
  python3 etc/registry_data.py fetch        # re-pull configs -> etc/registry_data.json
  python3 etc/registry_data.py check        # verify md/models.md rows against the store
  python3 etc/registry_data.py geometry ID  # print derived geometry for one model

The JSON carries the RAW config fields plus derived geometry (window,
KV KiB/token, q4_0 KV at 262,144) and the source repo. models.md notes
cite the store; the store never edits models.md.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "etc" / "registry_data.json"

CEILING_DEPTH = 262144
KV_QUANT_F16 = 1.0
KV_QUANT_Q40 = 0.28125
GIB = 2**30

# models.md roster -> source repo. measured: config pulled at fetch time.
ROSTER = {
    "Qwen3.5-0.8B": "Qwen/Qwen3.5-0.8B",
    "Qwen3.5-2B": "Qwen/Qwen3.5-2B",
    "Qwen3.5-4B": "Qwen/Qwen3.5-4B",
    "AI21-Jamba2-3B": "ai21labs/AI21-Jamba2-3B",
    "AI21-Jamba-Reasoning-3B": "ai21labs/AI21-Jamba-Reasoning-3B",
    "RWKV7-World-2.9B": "RWKV/RWKV7-Goose-World3-2.9B-HF",
    "Qwen2.5-1.5B-Instruct": "Qwen/Qwen2.5-1.5B-Instruct",
    "Qwen3-1.7B": "Qwen/Qwen3-1.7B",
    "Qwen3-4B-Instruct-2507": "Qwen/Qwen3-4B-Instruct-2507",
    "phi-1": "microsoft/phi-1",
    "phi-2": "microsoft/phi-2",
    "phi-4-mini-instruct": "microsoft/phi-4-mini-instruct",
    "Phi-3.5-mini-instruct": "microsoft/Phi-3.5-mini-instruct",
    "Phi-3-mini-4k-instruct": "microsoft/Phi-3-mini-4k-instruct",
    "granite-3.0-2b-instruct": "ibm-granite/granite-3.0-2b-instruct",
    "granite-3.1-2b-instruct": "ibm-granite/granite-3.1-2b-instruct",
    "granite-3.2-2b-instruct": "ibm-granite/granite-3.2-2b-instruct",
    "granite-3.3-2b-instruct": "ibm-granite/granite-3.3-2b-instruct",
    "granite-4.0-350m": "ibm-granite/granite-4.0-350m",
    "granite-4.0-h-350m": "ibm-granite/granite-4.0-h-350m",
    "granite-4.0-1b": "ibm-granite/granite-4.0-1b",
    "granite-4.0-micro": "ibm-granite/granite-4.0-micro",
    "granite-4.0-h-micro": "ibm-granite/granite-4.0-h-micro",
    "granite-4.0-h-1b": "ibm-granite/granite-4.0-h-1b",
    "granite-4.1-3b": "ibm-granite/granite-4.1-3b",
    "granite-4.2-3b": "ibm-granite/granite-4.2-3b",
    "MiniCPM-1B-sft": "openbmb/MiniCPM-1B-sft-bf16",
    "MiniCPM-2B-sft": "openbmb/MiniCPM-2B-sft-bf16",
    "MiniCPM3-4B": "openbmb/MiniCPM3-4B",
    "MiniCPM4-0.5B": "openbmb/MiniCPM4-0.5B",
    "MiniCPM5-1B": "openbmb/MiniCPM5-1B",
    "MiniCPM5-2B": "openbmb/MiniCPM5-2B",
    "gemma-4-e2b-it": "google/gemma-4-e2b-it",
    "gemma-3-1b-it": "google/gemma-3-1b-it",
    "gemma-3-4b-it": "google/gemma-3-4b-it",
    "Ministral-3-3B-Instruct-2512": "mistralai/Ministral-3-3B-Instruct-2512",
    "Llama-3.2-1B-Instruct": "meta-llama/Llama-3.2-1B-Instruct",
    "SmolLM3-3B": "HuggingFaceTB/SmolLM3-3B",
}
# The roster is CUT at gemma-4-e2b-it (5.12B) - the author's 80 GB
# disk ruling (session 40, addendum 51): every family above it (from
# Llama-3.1-8B up) cannot fit the f16 pipeline, whose transient peak
# is source + gguf together, roughly 2x the steady-state size. The
# models.md rows stay as the geometry record of what was cut.
CUT_BELOW_DISK = "gemma-4-e2b-it"

# gated repos the study cannot fetch; geometry from the author's pull / public cards.
# kept explicit so `check` knows why a row has no hub extract.
GATED = {
    "gemma-3-1b-it": "author pull (addendum 22)",
    "gemma-3-4b-it": "author pull (addendum 22)",
    "Llama-3.2-1B-Instruct": "author pull (addendum 22)",
}


# parameter counts in billions, RETRIEVED FROM HF (session 40,
# addendum 29 - the author's WoW: never guessed). Two retrieval
# paths, both from the hub: (1) safetensors repos - model_info's
# safetensors.total is the EXACT tensor count summed by HF;
# (2) bin-only repos (the MiniCPM trio) - HF exposes no tensor
# count for pickles, so the count is the exact pytorch_model.bin
# size divided by the storage width the repo ships (bf16 = 2
# bytes/param), recorded with its source so the derivation is
# auditable. Both land in the STORE at fetch time; nothing is
# parsed from names and nothing is hand-declared.


def _params_b_from_hub(repo: str) -> tuple[float | None, str]:
    """(params_b, source) retrieved from HF for one repo."""
    from huggingface_hub import HfApi

    api = HfApi()
    info = api.model_info(repo, files_metadata=True)
    st = getattr(info, "safetensors", None)
    total = getattr(st, "total", None) if st else None
    if total:
        return total / 1e9, f"hub safetensors.total ({total:,} tensors)"
    for s in info.siblings or []:
        if s.rfilename == "pytorch_model.bin" and s.size:
            return s.size / 2 / 1e9, f"hub pytorch_model.bin size {s.size:,} / 2 (bf16)"
    return None, "NO PARAMS ON HUB"


def params_b(name: str) -> float | None:
    """The model's parameter count in billions (session 40, addendum
    28: the param-ascending roster order; addendum 29: retrieved from
    HF via the STORE, never guessed). Total params - MoE counts the
    total, not the active subset."""
    store = json.loads(STORE.read_text())
    entry = store.get(name) or {}
    return entry.get("params_b")


def params_sorted_roster() -> list[str]:
    """The roster in param-ascending order (session 40, addendum 28 -
    the author's from-scratch ruling: all registered models, smallest
    parameters first, retrieved from HF - addendum 29). Unknown counts
    (a fetch failure) sort last, alphabetically - the registry check
    flags them so an uncounted model is never silently misplaced."""
    return sorted(
        ROSTER,
        key=lambda n: (
            params_b(n) is None,
            params_b(n) if params_b(n) is not None else 0.0,
            n,
        ),
    )


FETCH_FIELDS = [
    "max_position_embeddings",
    "num_hidden_layers",
    "num_attention_heads",
    "num_key_value_heads",
    "head_dim",
    "hidden_size",
    "intermediate_size",
    "full_attention_interval",
    "rope_scaling",
    "rope_theta",
    "sliding_window",
    "num_experts",
    "num_experts_per_tok",
    "moe_intermediate_size",
    "architectures",
    "model_type",
    "layer_types",
]


def unwrap(config):
    """Return the text config (multimodal wrappers nest it)."""
    c = config
    trail = []
    while isinstance(c, dict):
        if c.get("max_position_embeddings") is not None:
            return c, trail
        nxt = c.get("text_config") or c.get("language_model")
        if not nxt:
            return c, trail
        c = nxt
        trail.append("text_config")
    return c, trail


def geometry(c):
    L = c.get("num_hidden_layers")
    heads = c.get("num_attention_heads")
    kvh = c.get("num_key_value_heads", heads)
    hd = c.get("head_dim")
    if hd is None and c.get("hidden_size") and heads:
        hd = c["hidden_size"] // heads
    interval = c.get("full_attention_interval") or 1
    # addendum 135: layer_types wins when present - a granite-h
    # config lists 28 mamba + 4 attention layers, so only 4 layers
    # keep a full-window cache (the interval field stays for
    # interval-only configs like Qwen3.5)
    layer_types = c.get("layer_types") or []
    attn_layers = sum(1 for t in layer_types if str(t).lower() == "attention")
    if attn_layers:
        interval = L // attn_layers
    if not (L and kvh and hd):
        return None
    per_token = L * 2 * kvh * hd * 2
    return {
        "layers": L,
        "kv_heads": kvh,
        "head_dim": hd,
        "kv_bytes_per_token_f16": per_token,
        "kv_kib_per_token_f16": round(per_token / 1024, 1),
        "full_attention_interval": interval,
        "kv_q4_0_gib_at_262144": round(
            CEILING_DEPTH * per_token / interval * KV_QUANT_Q40 / GIB, 2
        ),
        "window": c.get("max_position_embeddings"),
        "rope_scaling": c.get("rope_scaling"),
    }


def fetch():
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        hf_hub_download = None

    out = {"_meta": {"roster_size": len(ROSTER), "gated": GATED}}
    for name, repo in ROSTER.items():
        if name in GATED:
            entry = {"repo": repo, "source": GATED[name], "extract": None}
            try:
                pb, psrc = _params_b_from_hub(repo)
                if pb:
                    entry["params_b"] = round(pb, 4)
                    entry["params_source"] = psrc
            except Exception:
                pass
            out[name] = entry
            continue
        if hf_hub_download is None:
            out[name] = {
                "repo": repo,
                "source": "FETCH ERROR huggingface_hub not installed",
                "extract": None,
            }
            continue
        try:
            raw = json.load(open(hf_hub_download(repo, "config.json")))
            c, trail = unwrap(raw)
            extract = {k: c.get(k) for k in FETCH_FIELDS}
            entry = {
                "repo": repo,
                "source": "hub config.json" + (f" ({'/'.join(trail)})" if trail else ""),
                "extract": extract,
                "geometry": geometry(c),
            }
            try:
                pb, psrc = _params_b_from_hub(repo)
                if pb:
                    entry["params_b"] = round(pb, 4)
                    entry["params_source"] = psrc
            except Exception:
                pass
            out[name] = entry
        except Exception as e:
            out[name] = {"repo": repo, "source": f"FETCH ERROR {type(e).__name__}", "extract": None}
    STORE.write_text(json.dumps(out, indent=1) + "\n")
    ok = sum(1 for v in out.values() if isinstance(v, dict) and v.get("extract"))
    print(
        f"store written: {STORE.relative_to(ROOT)}"
        f" ({ok}/{len(ROSTER)} hub extracts, {len(GATED)} gated/paper-sourced)"
    )


def check():
    store = json.loads(STORE.read_text())
    models_md = (ROOT / "md" / "models.md").read_text()
    missing, unsourced, uncounted = [], [], []
    for name in ROSTER:
        if (
            name not in models_md
            and name.replace(
                "Ministral-3-3B-Instruct-2512", "mistralai/Ministral-3-3B-Instruct-2512"
            )
            not in models_md
        ):
            missing.append(name)
    for name, v in store.items():
        if name == "_meta":
            continue
        if v.get("source", "").startswith("FETCH ERROR"):
            unsourced.append(name)
        if not v.get("params_b"):
            uncounted.append(name)
    print(
        f"store: {len(store) - 1} models; roster missing from models.md:"
        f" {missing or 'none'}; fetch errors: {unsourced or 'none'};"
        f" params not retrieved from HF: {uncounted or 'none'}"
    )
    return 1 if (missing or unsourced or uncounted) else 0


def show(name):
    store = json.loads(STORE.read_text())
    if name not in store:
        print(f"unknown id {name}; ids: {', '.join(k for k in store if k != '_meta')}")
        return 1
    print(json.dumps(store[name], indent=1))
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "fetch":
        fetch()
    elif cmd == "geometry":
        return show(sys.argv[2]) if len(sys.argv) > 2 else 1
    elif cmd == "check":
        return check()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
