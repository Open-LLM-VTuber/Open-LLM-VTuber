"""Offline unit tests for the OpenAI-compatible ASR engine.

These tests mock ``requests.post`` so they run without a live ASR server.
They verify WAV buffer encoding, transcription request shaping, the
text-vs-JSON response branches, error handling, and language passthrough.
"""

import io
import json
import wave
from unittest.mock import patch

import numpy as np

import open_llm_vtuber.asr.openai_compat_asr as asr_mod
from open_llm_vtuber.asr.openai_compat_asr import VoiceRecognition


class FakeTextResponse:
    """Minimal stand-in for a ``requests`` response returning plain text."""

    def __init__(self, text: str):
        self._text = text
        self.content = text.encode("utf-8")
        self.headers = {"Content-Type": "text/plain"}

    @property
    def text(self) -> str:
        return self._text

    def raise_for_status(self):
        return None


class FakeJSONResponse:
    """Minimal stand-in for a ``requests`` response returning JSON."""

    def __init__(self, payload: dict):
        self._payload = payload
        self.content = json.dumps(payload).encode("utf-8")
        self.headers = {"Content-Type": "application/json"}

    @property
    def text(self) -> str:
        return json.dumps(self._payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def _silence(seconds: float = 1.0, sr: int = 16000) -> np.ndarray:
    return np.zeros(int(seconds * sr), dtype=np.float32)


def test_to_wav_buffer_encodes_16bit_pcm_mono_16k():
    eng = VoiceRecognition()
    sig = np.full(1600, 0.5, dtype=np.float32)  # 0.1s, half-scale
    buf = eng._to_wav_buffer(sig)
    data = buf.getvalue()

    assert data[:4] == b"RIFF"
    with wave.open(io.BytesIO(data), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
    # Half-scale float should map near +16383 in 16-bit signed.
    samples = np.frombuffer(data[44:], dtype="<i2")
    assert samples.max() > 10000


def test_transcribe_text_response():
    eng = VoiceRecognition(base_url="http://localhost:8733/v1")
    resp = FakeTextResponse("hello there")
    with patch.object(asr_mod.requests, "post", return_value=resp) as mock_post:
        out = eng.transcribe_np(_silence())

    assert out == "hello there"
    _, kwargs = mock_post.call_args
    assert kwargs["data"]["model"] == "base"
    assert kwargs["data"]["response_format"] == "text"
    assert "file" in kwargs["files"]
    assert kwargs["files"]["file"][0] == "audio.wav"


def test_transcribe_json_response():
    eng = VoiceRecognition()
    resp = FakeJSONResponse({"text": "json hello"})
    with patch.object(asr_mod.requests, "post", return_value=resp):
        out = eng.transcribe_np(_silence())
    assert out == "json hello"


def test_transcribe_strips_whitespace():
    eng = VoiceRecognition()
    resp = FakeTextResponse("  padded text  \n")
    with patch.object(asr_mod.requests, "post", return_value=resp):
        out = eng.transcribe_np(_silence())
    assert out == "padded text"


def test_transcribe_failure_returns_empty_string():
    eng = VoiceRecognition()
    import requests

    with patch.object(
        asr_mod.requests, "post", side_effect=requests.RequestException("boom")
    ):
        out = eng.transcribe_np(_silence())
    assert out == ""


def test_language_is_passed_when_set():
    eng = VoiceRecognition(language="en")
    resp = FakeTextResponse("x")
    with patch.object(asr_mod.requests, "post", return_value=resp) as mock_post:
        eng.transcribe_np(_silence())
    assert mock_post.call_args[1]["data"]["language"] == "en"


def test_language_omitted_when_none():
    eng = VoiceRecognition(language=None)
    resp = FakeTextResponse("x")
    with patch.object(asr_mod.requests, "post", return_value=resp) as mock_post:
        eng.transcribe_np(_silence())
    assert "language" not in mock_post.call_args[1]["data"]


def test_base_url_trailing_slash_is_stripped():
    eng = VoiceRecognition(base_url="http://localhost:8733/v1/")
    assert eng.base_url == "http://localhost:8733/v1"
    resp = FakeTextResponse("x")
    with patch.object(asr_mod.requests, "post", return_value=resp) as mock_post:
        eng.transcribe_np(_silence())
    assert (
        mock_post.call_args[0][0] == "http://localhost:8733/v1/audio/transcriptions"
    )
