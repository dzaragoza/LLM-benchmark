"""Pins: R-31 (session 45, addendum 163) - the I/O layer covered by a
loopback HTTP stub: real sockets, real urllib, so post_json/ask/tokenize/
trim_to_tokens/wait_healthy execute their REAL request paths - the error
bodies, the payload shapes, the bisection loop - against an in-process
server that answers like llama-server. The addendum-112 discipline holds:
the stub fakes the SERVER, never the measurement contract; no GPU, no
llama-server binary, and production code paths run unmodified.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import infra.llama_server as ls
import ruler_gate


class StubServer:
    """A loopback llama-server stand-in. Routes: POST /tokenize, POST
    /v1/chat/completions, GET /health. Behavior is scripted per route:
    a callable (payload) -> (status, body), or a fixed body."""

    def __init__(self):
        self.routes: dict = {}
        self.calls: list = []
        self._srv: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.port = 0

    def start(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def _dispatch(self, method):
                body = b""
                length = int(self.headers.get("Content-Length") or 0)
                if length:
                    body = self.rfile.read(length)
                outer.calls.append((method, self.path, body))
                fn = outer.routes.get(self.path)
                if fn is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                payload = json.loads(body) if body else {}
                status, out = fn(payload) if callable(fn) else fn
                data = json.dumps(out).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self._dispatch("GET")

            def do_POST(self):
                self._dispatch("POST")

            def log_message(self, *a):
                pass

        self._srv = HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self._srv.server_port
        self._thread = threading.Thread(target=self._srv.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        if self._srv:
            self._srv.shutdown()
            self._srv.server_close()


@pytest.fixture
def stub():
    s = StubServer().start()
    yield s
    s.stop()


def test_tokenize_real_request_path(stub):
    """tokenize POSTs the content and returns the server's token list -
    the real HTTP round trip, the real JSON decode, the real
    no-tokens-field error."""
    stub.routes["/tokenize"] = (200, {"tokens": [1, 2, 3]})
    toks = ls.tokenize(stub.port, "hello world")
    assert toks == [1, 2, 3]
    method, path, body = stub.calls[-1]
    assert (method, path) == ("POST", "/tokenize")
    assert json.loads(body)["content"] == "hello world"


def test_tokenize_missing_tokens_field_raises(stub):
    stub.routes["/tokenize"] = (200, {"unexpected": True})
    with pytest.raises(ValueError, match="no tokens field"):
        ls.tokenize(stub.port, "hello")


def test_ask_content_and_reasoning_fields(stub):
    """ask reads content first, falls back to reasoning_content - the
    thinking-mode contract; no_thinking injects the chat_template_kwargs."""
    stub.routes["/v1/chat/completions"] = (
        200,
        {"choices": [{"message": {"content": "answer", "reasoning_content": "thinking"}}]},
    )
    assert ruler_gate.ask(stub.port, "q") == "answer"
    method, path, body = stub.calls[-1]
    payload = json.loads(body)
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}


def test_ask_falls_back_to_reasoning_content(stub):
    stub.routes["/v1/chat/completions"] = (200, {
        "choices": [{"message": {"content": None, "reasoning_content": "the answer"}}]
    })
    assert ruler_gate.ask(stub.port, "q") == "the answer"


def test_ask_http_error_carries_the_body(stub):
    """The ValueError surfaces the server's error body - the HTTP-400
    diagnostics class (the addendum-102 live crash shape)."""
    stub.routes["/v1/chat/completions"] = (400, {"error": "window exceeded"})
    with pytest.raises(ValueError, match="400"):
        ruler_gate.ask(stub.port, "q")


def test_trim_to_tokens_never_over_budget(stub):
    """The bisection trim converges to <= target tokens - the depth
    arithmetic's never-over invariant, over the real request path."""

    def fake_tokenize(payload):
        n = max(1, len(payload["content"]) // 4)
        return 200, {"tokens": list(range(n))}

    stub.routes["/tokenize"] = fake_tokenize
    text = "x" * 400
    out, n = ls.trim_to_tokens(stub.port, text, 50)
    assert n <= 50
    assert out and len(out) < len(text)


def test_wait_healthy_polls_to_green(stub):
    stub.routes["/health"] = (200, {"status": "ok"})
    assert ls.wait_healthy(stub.port, timeout=5) is True


def test_wait_healthy_unreachable_returns_false():
    """Nothing listening on the port - the launch-failure branch,
    exercised over the real socket error path (fast timeout)."""
    assert ls.wait_healthy(9, timeout=0.2) is False
