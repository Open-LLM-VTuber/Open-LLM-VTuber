####
# change from xTTS.py
####

import re
import threading
import time

import requests
from loguru import logger

from .tts_interface import TTSInterface

# A24: GPT-SoVITS typically runs on one GPU (or CPU). Firing one request per
# sentence saturates it: every extra request only waits in the model queue,
# holding a socket and a worker thread. These defaults keep the streaming
# pipeline fast without flooding the TTS backend.
DEFAULT_REQUEST_TIMEOUT = 20.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BACKOFF = 0.5
DEFAULT_MAX_CONCURRENCY = 2


class GPTSoVITSError(RuntimeError):
    """Base class for GPT-SoVITS request failures."""


class RetryableGPTSoVITSError(GPTSoVITSError):
    """Transient failure: timeout, connection error, 5xx or a non-audio body."""


class PermanentGPTSoVITSError(GPTSoVITSError):
    """Failure that retrying cannot fix (4xx, wrong URL or parameters)."""


def _looks_like_audio(payload: bytes) -> bool:
    """Return True when the body starts with a known audio signature.

    GPT-SoVITS answers ``200`` with an HTML/JSON error page when the model is
    not loaded. Saving that body as ``.wav`` only fails later inside pydub with
    a confusing message (audit 5.2.7), so the body is validated here.
    """
    if not payload:
        return False
    if payload.startswith((b"RIFF", b"ID3", b"OggS", b"fLaC")):
        return True
    # MPEG audio frame sync (11 bits set): MP3 answers without an ID3 tag.
    return len(payload) > 1 and payload[0] == 0xFF and (payload[1] & 0xE0) == 0xE0


class TTSEngine(TTSInterface):
    def __init__(
        self,
        api_url: str = "http://127.0.0.1:9880/tts",
        text_lang: str = "zh",
        ref_audio_path: str = "",
        prompt_lang: str = "zh",
        prompt_text: str = "",
        text_split_method: str = "cut5",
        batch_size: str = "1",
        media_type: str = "wav",
        streaming_mode: str = "false",
        request_timeout: float | None = None,
        max_retries: int | None = None,
        retry_backoff: float | None = None,
        max_concurrency: int | None = None,
    ):
        self.api_url = api_url
        self.text_lang = text_lang
        self.ref_audio_path = ref_audio_path
        self.prompt_lang = prompt_lang
        self.prompt_text = prompt_text
        self.text_split_method = text_split_method
        self.batch_size = batch_size
        self.media_type = media_type
        # "ture" was the historical typo in this default; the GPT-SoVITS client
        # expects a complete WAV, so streaming stays off unless configured.
        self.streaming_mode = streaming_mode or "false"
        self.request_timeout = float(
            DEFAULT_REQUEST_TIMEOUT if request_timeout is None else request_timeout
        )
        self.max_retries = max(
            0, int(DEFAULT_MAX_RETRIES if max_retries is None else max_retries)
        )
        self.retry_backoff = max(
            0.0,
            float(DEFAULT_RETRY_BACKOFF if retry_backoff is None else retry_backoff),
        )
        self.max_concurrency = max(
            1,
            int(
                DEFAULT_MAX_CONCURRENCY if max_concurrency is None else max_concurrency
            ),
        )
        # BoundedSemaphore (not asyncio.Semaphore): generate_audio runs inside
        # the worker threads created by TTSInterface.async_generate_audio.
        self._semaphore = threading.BoundedSemaphore(self.max_concurrency)

    def _build_params(self, text: str) -> dict:
        return {
            "text": text,
            "text_lang": self.text_lang,
            "ref_audio_path": self.ref_audio_path,
            "prompt_lang": self.prompt_lang,
            "prompt_text": self.prompt_text,
            "text_split_method": self.text_split_method,
            "batch_size": self.batch_size,
            "media_type": self.media_type,
            "streaming_mode": self.streaming_mode,
        }

    def _request_audio(self, params: dict) -> bytes:
        """Perform one request and classify the failure as retryable or not."""
        try:
            response = requests.get(
                self.api_url, params=params, timeout=self.request_timeout
            )
        except requests.RequestException as e:
            # Timeout, DNS error, connection reset...: the sentence may still
            # be synthesized on the next attempt.
            raise RetryableGPTSoVITSError(f"transport error: {e}") from e

        if response.status_code >= 500:
            raise RetryableGPTSoVITSError(
                f"HTTP {response.status_code}: {response.text[:200]!r}"
            )
        if response.status_code != 200:
            raise PermanentGPTSoVITSError(
                f"HTTP {response.status_code}: {response.text[:200]!r}"
            )

        content = response.content
        if not _looks_like_audio(content):
            raise RetryableGPTSoVITSError(
                "response is not audio (is the GPT-SoVITS model loaded?)"
            )
        return content

    def generate_audio(self, text, file_name_no_ext=None):
        file_name = self.generate_cache_file_name(file_name_no_ext, self.media_type)
        cleaned_text = re.sub(r"\[.*?\]", "", text)
        params = self._build_params(cleaned_text)

        attempts = self.max_retries + 1
        audio_bytes: bytes | None = None

        # One slot per in-flight request. Waiting here is cheaper than waiting
        # on the GPU: the sentence keeps its order and the turn stays bounded.
        with self._semaphore:
            for attempt in range(1, attempts + 1):
                try:
                    audio_bytes = self._request_audio(params)
                    break
                except RetryableGPTSoVITSError as e:
                    if attempt >= attempts:
                        logger.error(
                            f"GPT-SoVITS failed after {attempts} attempt(s): {e}"
                        )
                        # Raising lets TTSTaskManager emit the silent payload
                        # for this sentence while keeping the turn order.
                        raise
                    delay = self.retry_backoff * (2 ** (attempt - 1))
                    logger.warning(
                        f"GPT-SoVITS attempt {attempt}/{attempts} failed ({e}); "
                        f"retrying in {delay:.1f}s"
                    )
                    if delay > 0:
                        time.sleep(delay)

        if audio_bytes is None:  # pragma: no cover - defensive
            raise GPTSoVITSError("GPT-SoVITS returned no audio")

        with open(file_name, "wb") as audio_file:
            audio_file.write(audio_bytes)
        return file_name
