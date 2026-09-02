"""Offline tests for the A2A -> OpenAI-compatible proxy.

Covers the pure request-mapping helpers and a synchronous agent call with a
stubbed A2A transport (no real agent / network required).
"""

import importlib.util
import os


def _load():
    spec = importlib.util.spec_from_file_location(
        "a2a_proxy_ut",
        os.path.join(os.path.dirname(__file__), "..", "a2a_openai_proxy.py"),
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_last_user_text_picks_last_user():
    m = _load()
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "second"},
    ]
    assert m.last_user_text(msgs) == "second"


def test_last_user_text_list_content():
    m = _load()
    msgs = [{"role": "user", "content": [{"text": "hello"}]}]
    assert m.last_user_text(msgs) == "hello"


def test_extract_text_artifact_shape():
    m = _load()
    res = {"artifacts": [{"parts": [{"text": "answer"}]}]}
    assert m._extract_text(res) == "answer"


def test_extract_text_status_message_shape():
    m = _load()
    res = {"status": {"message": {"parts": [{"text": "via status"}]}}}
    assert m._extract_text(res) == "via status"


def test_routes_token_prefers_hermes_override(monkeypatch):
    # HERMES_A2A_TOKEN set -> glados route uses it, not the OpenClaw token.
    monkeypatch.setenv("HERMES_A2A_TOKEN", "hermes-secret")
    monkeypatch.setenv("OPENCLAW_CONFIG", "/nonexistent/openclaw.json")
    m = _load()
    assert m.ROUTES["glados"]["token"] == "hermes-secret"
    assert m.ROUTES["wheatley"]["token"] != "hermes-secret"


def test_call_agent_sync(monkeypatch):
    m = _load()
    captured = {}

    def fake_rpc(endpoint, token, method, params, timeout):
        captured["endpoint"] = endpoint
        captured["method"] = method
        captured["params"] = params
        return {"result": {"artifacts": [{"parts": [{"text": "pong"}]}]}}

    monkeypatch.setattr(m, "_rpc", fake_rpc)
    out = m.call_agent("glados", "ping")
    assert out == "pong"
    assert captured["method"] == "message/send"
    assert captured["params"]["message"]["parts"][0]["text"] == "ping"
