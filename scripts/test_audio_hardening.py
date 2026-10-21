"""Unit tests for the A23 audio-export switch and the A24 GPT-SoVITS hardening.

Standalone on purpose (same approach as ``scripts/test_security_metrics.py``):
the repository has no pytest setup and a bare interpreter may not have the
runtime dependencies. Light shims for ``loguru``/``requests``/``pydub`` keep the
modules importable, the HTTP layer is mocked, and nothing here touches the
network or a real GPT-SoVITS server.

    python scripts/test_audio_hardening.py
    python scripts/test_audio_hardening.py -v GPTSoVITSTests
"""

import base64
import logging
import os
import shutil
import sys
import tempfile
import threading
import types
import unittest
from unittest import mock

# Add project root to path to enable imports (same as the live scripts).
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def _install_loguru_shim() -> None:
    """Allow modules that only use ``loguru`` for logging to import."""
    try:
        import loguru  # noqa: F401

        return
    except ImportError:
        pass

    class _ShimLogger:
        def __init__(self, name="loguru"):
            self._log = logging.getLogger(name)

        def bind(self, **_kwargs):
            return self

        def debug(self, msg, *a, **k):
            self._log.debug(msg, *a, **k)

        def info(self, msg, *a, **k):
            self._log.info(msg, *a, **k)

        def warning(self, msg, *a, **k):
            self._log.warning(msg, *a, **k)

        def error(self, msg, *a, **k):
            self._log.error(msg, *a, **k)

        def critical(self, msg, *a, **k):
            self._log.critical(msg, *a, **k)

        def exception(self, msg, *a, **k):
            self._log.exception(msg, *a, **k)

    module = types.ModuleType("loguru")
    module.logger = _ShimLogger()
    sys.modules["loguru"] = module


def _install_requests_shim() -> None:
    """Provide the tiny ``requests`` surface used by the GPT-SoVITS engine."""
    try:
        import requests  # noqa: F401

        return
    except ImportError:
        pass

    module = types.ModuleType("requests")

    class RequestException(Exception):
        pass

    class ConnectionError(RequestException):  # noqa: A001 - mirrors requests
        pass

    class Timeout(RequestException):
        pass

    def _no_network(*_args, **_kwargs):
        raise RequestException("network access is not available in this test")

    module.RequestException = RequestException
    module.ConnectionError = ConnectionError
    module.Timeout = Timeout
    module.get = _no_network
    sys.modules["requests"] = module


def _install_pydub_shim() -> None:
    """Provide placeholders so ``utils.stream_audio`` can be imported."""
    try:
        import pydub  # noqa: F401

        return
    except ImportError:
        pass

    module = types.ModuleType("pydub")
    module.AudioSegment = type("AudioSegment", (), {})
    utils = types.ModuleType("pydub.utils")
    utils.make_chunks = lambda *_args, **_kwargs: []
    module.utils = utils
    sys.modules["pydub"] = module
    sys.modules["pydub.utils"] = utils


_install_loguru_shim()
_install_requests_shim()
_install_pydub_shim()

from src.open_llm_vtuber.agent.output_types import DisplayText  # noqa: E402
from src.open_llm_vtuber.tts import gpt_sovits_tts  # noqa: E402
from src.open_llm_vtuber.utils import stream_audio  # noqa: E402


class _FakeExport:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data


class _FakeAudioSegment:
    """Minimal ``pydub.AudioSegment`` stand-in (no ffmpeg, no audio files)."""

    payload = b"RIFF\x24\x00\x00\x00WAVEfmt "
    export_calls: list = []
    loaded_paths: list = []

    @classmethod
    def from_file(cls, path: str) -> "_FakeAudioSegment":
        cls.loaded_paths.append(path)
        return cls()

    def export(self, **kwargs) -> _FakeExport:
        _FakeAudioSegment.export_calls.append(kwargs)
        return _FakeExport(_FakeAudioSegment.payload)

    @property
    def rms(self) -> int:
        return 10


def _fake_make_chunks(audio, chunk_length_ms):  # noqa: ARG001 - pydub signature
    return [audio, audio]


class _FakeResponse:
    def __init__(self, status_code: int = 200, content: bytes = b"", text: str = ""):
        self.status_code = status_code
        self.content = content
        self.text = text


AUDIO_BODY = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 32


class AudioExportTests(unittest.TestCase):
    """A23: the container is configurable and defaults to WAV."""

    def setUp(self):
        self._cwd = os.getcwd()
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)
        _FakeAudioSegment.export_calls = []
        _FakeAudioSegment.loaded_paths = []
        self._patches = [
            mock.patch.object(stream_audio, "AudioSegment", _FakeAudioSegment),
            mock.patch.object(stream_audio, "make_chunks", _fake_make_chunks),
        ]
        for patcher in self._patches:
            patcher.start()

    def tearDown(self):
        for patcher in self._patches:
            patcher.stop()
        os.chdir(self._cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        stream_audio.configure_audio_export("wav", "64k")

    def test_default_is_wav(self):
        payload = stream_audio.prepare_audio_payload("cache/a.wav")

        self.assertEqual(_FakeAudioSegment.export_calls, [{"format": "wav"}])
        self.assertEqual(payload["audio_format"], "wav")
        self.assertEqual(base64.b64decode(payload["audio"]), _FakeAudioSegment.payload)
        self.assertEqual(payload["volumes"], [1.0, 1.0])

    def test_mp3_uses_configured_bitrate(self):
        self.assertEqual(stream_audio.configure_audio_export("MP3", "96k"), "mp3")

        payload = stream_audio.prepare_audio_payload("cache/a.wav")

        self.assertEqual(
            _FakeAudioSegment.export_calls, [{"format": "mp3", "bitrate": "96k"}]
        )
        self.assertEqual(payload["audio_format"], "mp3")
        self.assertEqual(base64.b64decode(payload["audio"]), _FakeAudioSegment.payload)

    def test_mp3_default_bitrate_is_64k(self):
        stream_audio.configure_audio_export("mp3", None)

        stream_audio.prepare_audio_payload("cache/a.wav")

        self.assertEqual(
            _FakeAudioSegment.export_calls, [{"format": "mp3", "bitrate": "64k"}]
        )

    def test_invalid_format_is_rejected_and_keeps_previous(self):
        stream_audio.configure_audio_export("mp3", "64k")

        with self.assertRaises(ValueError):
            stream_audio.configure_audio_export("ogg")

        self.assertEqual(stream_audio.get_audio_export_format(), "mp3")

    def test_silent_payload_carries_format(self):
        stream_audio.configure_audio_export("mp3")

        payload = stream_audio.prepare_audio_payload(
            None, display_text=DisplayText(text="hola")
        )

        self.assertIsNone(payload["audio"])
        self.assertEqual(payload["audio_format"], "mp3")
        self.assertEqual(payload["volumes"], [])
        self.assertEqual(payload["display_text"]["text"], "hola")


class GPTSoVITSTests(unittest.TestCase):
    """A24: retry/backoff, non-retryable errors and the concurrency cap."""

    def setUp(self):
        self._cwd = os.getcwd()
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)
        # Pre-create it: generate_cache_file_name uses check-then-makedirs,
        # which would race between the worker threads of the cap test.
        os.makedirs("cache", exist_ok=True)
        self.engine = gpt_sovits_tts.TTSEngine(
            api_url="http://gpt-sovits.test/tts",
            ref_audio_path="ref.wav",
            streaming_mode=None,  # must fall back to "false"
            retry_backoff=0,  # no sleeps in the retry tests
        )

    def tearDown(self):
        os.chdir(self._cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _generate(self, get_mock, text="[smile] Hola", name="utt"):
        with mock.patch.object(gpt_sovits_tts.requests, "get", get_mock):
            return self.engine.generate_audio(text, name)

    def test_success_writes_audio_with_bounded_timeout(self):
        get_mock = mock.Mock(return_value=_FakeResponse(200, AUDIO_BODY, "ok"))

        path = self._generate(get_mock)

        self.assertTrue(os.path.exists(path))
        with open(path, "rb") as audio_file:
            self.assertEqual(audio_file.read(), AUDIO_BODY)
        self.assertEqual(get_mock.call_count, 1)
        called = get_mock.call_args.kwargs
        self.assertEqual(called["timeout"], 20.0)
        self.assertEqual(called["params"]["streaming_mode"], "false")
        self.assertEqual(called["params"]["text"], " Hola")  # [..] tags stripped
        self.assertEqual(called["params"]["media_type"], "wav")

    def test_transport_error_is_retried(self):
        get_mock = mock.Mock(
            side_effect=[
                gpt_sovits_tts.requests.ConnectionError("connection reset"),
                _FakeResponse(200, AUDIO_BODY),
            ]
        )

        path = self._generate(get_mock)

        self.assertTrue(os.path.exists(path))
        self.assertEqual(get_mock.call_count, 2)
        self.assertEqual(len(os.listdir("cache")), 1)

    def test_5xx_exhausts_retries_and_raises(self):
        get_mock = mock.Mock(return_value=_FakeResponse(503, b"", "busy"))

        with self.assertRaises(gpt_sovits_tts.RetryableGPTSoVITSError):
            self._generate(get_mock)

        self.assertEqual(get_mock.call_count, 3)  # 1 attempt + 2 retries
        self.assertEqual(os.listdir("cache"), [])

    def test_4xx_is_not_retried(self):
        get_mock = mock.Mock(return_value=_FakeResponse(400, b"", "bad ref audio"))

        with self.assertRaises(gpt_sovits_tts.PermanentGPTSoVITSError):
            self._generate(get_mock)

        self.assertEqual(get_mock.call_count, 1)

    def test_non_audio_200_is_retried(self):
        # GPT-SoVITS answers 200 with HTML when the model is not loaded.
        get_mock = mock.Mock(
            return_value=_FakeResponse(200, b"<html>model not loaded</html>")
        )

        with self.assertRaises(gpt_sovits_tts.RetryableGPTSoVITSError):
            self._generate(get_mock)

        self.assertEqual(get_mock.call_count, 3)
        self.assertEqual(os.listdir("cache"), [])

    def test_max_retries_zero_single_attempt(self):
        engine = gpt_sovits_tts.TTSEngine(
            api_url="http://gpt-sovits.test/tts", max_retries=0
        )
        get_mock = mock.Mock(return_value=_FakeResponse(500, b"", "boom"))

        with mock.patch.object(gpt_sovits_tts.requests, "get", get_mock):
            with self.assertRaises(gpt_sovits_tts.RetryableGPTSoVITSError):
                engine.generate_audio("hola", "utt")

        self.assertEqual(get_mock.call_count, 1)
        self.assertEqual(engine.max_retries, 0)

    def test_concurrency_is_capped(self):
        tracker = {"current": 0, "max": 0}
        lock = threading.Lock()
        two_in_flight = threading.Event()

        def fake_get(*_args, **_kwargs):
            with lock:
                tracker["current"] += 1
                tracker["max"] = max(tracker["max"], tracker["current"])
                if tracker["current"] >= 2:
                    two_in_flight.set()
            two_in_flight.wait(timeout=5)
            with lock:
                tracker["current"] -= 1
            return _FakeResponse(200, AUDIO_BODY)

        results = []

        def worker(index):
            results.append(self.engine.generate_audio("hola", f"utt{index}"))

        with mock.patch.object(gpt_sovits_tts.requests, "get", side_effect=fake_get):
            threads = [
                threading.Thread(target=worker, args=(index,)) for index in range(6)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)

        self.assertEqual(len(results), 6)
        self.assertEqual(tracker["max"], 2)  # never more than the cap
        self.assertEqual(len(os.listdir("cache")), 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
