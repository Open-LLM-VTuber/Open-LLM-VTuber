"""Offline unit tests for the OpenAI-compatible TTS engine.

These tests mock the outbound HTTP call (``requests.post``), so they run
without any network access, API key, or running TTS server. They verify
request shaping, file output, error handling, and config fallbacks.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

import open_llm_vtuber.tts.openai_compat_tts as tts_mod
from open_llm_vtuber.tts.openai_compat_tts import TTSEngine


class FakeResponse:
    """Minimal stand-in for a ``requests`` response."""

    def __init__(self, content: bytes = b"FAKEAUDIO", content_type: str = "audio/mpeg"):
        self.content = content
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self) -> None:
        return None


@pytest.fixture
def engine(tmp_path, monkeypatch):
    # Run inside a temp dir so the engine's hard-coded "cache/" output lands
    # there and is cleaned up automatically.
    monkeypatch.chdir(tmp_path)
    return TTSEngine(
        base_url="http://localhost:9999/v1",
        model="kokoro",
        voice="af_sky",
        api_key="secret-token",
    )


def test_success_writes_audio_file(engine, monkeypatch):
    resp = FakeResponse(content=b"RIFF....wavbytes")
    with patch.object(tts_mod.requests, "post", return_value=resp) as mock_post:
        path = engine.generate_audio("hello world", file_name_no_ext="out")

    assert path is not None
    p = Path(path)
    assert p.exists()
    assert p.read_bytes() == b"RIFF....wavbytes"

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["input"] == "hello world"
    assert kwargs["json"]["model"] == "kokoro"
    assert kwargs["json"]["voice"] == "af_sky"
    assert kwargs["json"]["response_format"] == "mp3"
    assert kwargs["json"]["speed"] == 1.0
    # api_key should be forwarded as a Bearer header.
    assert kwargs["headers"]["Authorization"] == "Bearer secret-token"


def test_unsupported_extension_falls_back_to_mp3(monkeypatch):
    import tempfile

    d = tempfile.mkdtemp()
    monkeypatch.chdir(d)
    eng = TTSEngine(base_url="http://localhost:9999/v1", file_extension="xyz")
    # The engine mutates file_extension to the safe default.
    assert eng.file_extension == "mp3"
    resp = FakeResponse()
    with patch.object(tts_mod.requests, "post", return_value=resp) as mock_post:
        path = eng.generate_audio("x", file_name_no_ext="f")
    assert Path(path).name == "f.mp3"
    assert mock_post.call_args[1]["json"]["response_format"] == "mp3"


def test_request_failure_returns_none(engine, monkeypatch):
    import requests

    with patch.object(
        tts_mod.requests, "post", side_effect=requests.RequestException("boom")
    ):
        path = engine.generate_audio("x", file_name_no_ext="fail")
    assert path is None


def test_empty_audio_is_rejected_and_cleaned_up(engine, monkeypatch):
    resp = FakeResponse(content=b"")  # zero-byte body
    with patch.object(tts_mod.requests, "post", return_value=resp):
        path = engine.generate_audio("x", file_name_no_ext="empty")
    # Empty output must be treated as failure and the stray file removed.
    assert path is None
    assert not Path("cache/empty.mp3").exists()


def test_base_url_trailing_slash_is_stripped(monkeypatch):
    import tempfile

    monkeypatch.chdir(tempfile.mkdtemp())
    eng = TTSEngine(base_url="http://localhost:9999/v1/")
    assert eng.base_url == "http://localhost:9999/v1"
    resp = FakeResponse()
    with patch.object(tts_mod.requests, "post", return_value=resp) as mock_post:
        eng.generate_audio("x", file_name_no_ext="u")
    assert mock_post.call_args[0][0] == "http://localhost:9999/v1/audio/speech"


def test_json_content_type_is_tolerated(engine, monkeypatch):
    # Some misconfigured endpoints return JSON instead of raw audio; the
    # engine should still write whatever bytes it received without crashing.
    resp = FakeResponse(content=b'{"detail":"ok"}', content_type="application/json")
    with patch.object(tts_mod.requests, "post", return_value=resp):
        path = engine.generate_audio("x", file_name_no_ext="j")
    assert path is not None
    assert Path(path).exists()
