"""Addendum 140: the template-sanity preflight.

MiniCPM5-1B's session-45 failure: the GGUF's embedded chat
template mangles the message (its prefill was an endless
<|im_start|> assistant loop) and the answers parroted haystack
noise. A measured 0 would lie about the model's reach - the cell
must be LABELLED template_malfunction, not scored.
"""

import bench.v7 as v7m


class _Gate:
    def __init__(self, reply: str):
        self._reply = reply

    def ask(self, port, prompt, max_tokens=64, no_thinking=True):
        return self._reply


def _check(monkeypatch, reply: str) -> None | v7m.TemplateMalfunction:
    monkeypatch.setattr(v7m, "ruler_gate", _Gate(reply))
    try:
        v7m.preflight_template_sanity(8210)
        return None
    except v7m.TemplateMalfunction as e:
        return e


def test_probe_detects_template_fragments(monkeypatch):
    e = _check(monkeypatch, "<|im_start|> assistant The sun is yellow. Here we go.")
    assert e is not None and "template fragment" in str(e)


def test_probe_detects_prompt_echo(monkeypatch):
    e = _check(monkeypatch, "Reply with the single word PINEAPPLE and nothing else.")
    assert e is not None and "prompt echo" in str(e)


def test_probe_passes_healthy_reply(monkeypatch):
    assert _check(monkeypatch, "PINEAPPLE") is None


def test_probe_detects_empty_reply(monkeypatch):
    e = _check(monkeypatch, "")
    assert e is not None and "empty" in str(e)


def test_malfunction_labels_cell_not_score(tmp_path, monkeypatch):
    """In the certify loop a TemplateMalfunction marks the cell
    error=template_malfunction and skips scoring - the entry
    carries no score, so the tables never show a fake 0."""
    monkeypatch.setattr(
        v7m,
        "climb_allocations",
        lambda b, budget=4, policy="greedy": [
            {
                "family": "famA",
                "params_b": 0.3,
                "ctx": 4096,
                "wq": "F16",
                "kq": "f16",
                "vq": "f16",
                "est_gib": 1.0,
            },
        ],
    )
    monkeypatch.setattr(v7m, "_acquire_missing_model", lambda *a, **k: "/tmp/x.gguf")
    monkeypatch.setattr(v7m.llama_server, "start_server", lambda *a, **k: (object(), True))
    monkeypatch.setattr(v7m.llama_server, "wait_healthy", lambda *a, **k: True)
    monkeypatch.setattr(v7m.llama_server, "stop_server", lambda *a, **k: None)
    monkeypatch.setattr(v7m, "save_state", lambda *a: None)

    def boom(port):
        raise v7m.TemplateMalfunction("template fragment in sanity probe: '<|im_start|>'")

    monkeypatch.setattr(v7m, "preflight_template_sanity", boom)
    monkeypatch.setattr(
        v7m, "corpus_from_artifact", lambda port: {"questions": [], "cuts": {}, "sentences": []}
    )
    state = {"families": {}}
    res = v7m.certify_v7(str(tmp_path), state, str(tmp_path / "st.json"), 8210, False)
    assert "template_malfunction" in res[0]["error"]
    assert res[0].get("score") is None
    assert "v7" not in state["families"]["famA"] or not state["families"]["famA"]["v7"]
