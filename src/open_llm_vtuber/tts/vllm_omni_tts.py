from abc import ABC, abstractmethod
from typing import Optional

import numpy as np
import httpx
from loguru import logger

from .tts_interface import TTSInterface


# ---------------------------------------------------------------------------
# Handler ABC + concrete handlers
#
# A handler knows everything model-specific: sample rate, which payload fields
# to send, and how to translate the user-facing voice modes (preset / clone /
# design) into the model's own request schema.
# ---------------------------------------------------------------------------


class ModelHandler(ABC):
    """Builds /v1/audio/speech payloads for one model family."""

    sample_rate: int  # used by the engine for PCM chunk math

    @abstractmethod
    def build_payload(self, text: str, stream: bool) -> dict: ...


def _get(obj, key, default=None):
    """Read a field from either a Pydantic model or a plain dict."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class Qwen3Handler(ModelHandler):
    """Handler for the Qwen3-TTS family.

    Qwen3 ships three model variants that each support exactly one voice mode:
        -Base         → voice_clone   (ref_audio + ref_text)
        -CustomVoice  → voice_preset  (named voice)
        -VoiceDesign  → voice_design  (free-form prompt)
    """

    sample_rate = 24000
    DEFAULT_PRESET = "vivian"
    # Size of the server's first code2wav decode block, in codec frames
    # (12Hz codec → 8 frames ≈ 0.67s of audio). The server default uses a
    # tiny initial block for minimal first-byte latency, but then delivers
    # audio slower than realtime for the first few seconds — measured
    # worst-case deficit ~2s of silence the client must insert somewhere.
    # With 8, delivery never falls behind realtime (deficit 0.00s measured)
    # for +0.2s first-byte latency.
    INITIAL_CODEC_CHUNK_FRAMES = 8

    def __init__(
        self,
        model: str,
        language: Optional[str] = None,
        voice_preset=None,
        voice_clone=None,
        voice_design=None,
    ):
        modes = [m for m in (voice_preset, voice_clone, voice_design) if m]
        if len(modes) > 1:
            raise ValueError(
                "voice_preset, voice_clone, and voice_design are mutually exclusive"
            )

        if voice_clone:
            if not model.endswith("-Base"):
                raise ValueError(
                    f"voice_clone requires a Qwen3-*-Base model; got {model}"
                )
            self._task = "Base"
            self._ref_audio = _get(voice_clone, "audio")
            self._ref_text = _get(voice_clone, "text")
            self._voice = self.DEFAULT_PRESET
        elif voice_design:
            if not model.endswith("-VoiceDesign"):
                raise ValueError(
                    f"voice_design requires a Qwen3-*-VoiceDesign model; got {model}"
                )
            self._task = "VoiceDesign"
            self._instructions = _get(voice_design, "prompt")
            self._voice = self.DEFAULT_PRESET
        else:
            if not model.endswith("-CustomVoice"):
                raise ValueError(
                    f"voice_preset requires a Qwen3-*-CustomVoice model; got {model}"
                )
            self._task = "CustomVoice"
            self._voice = _get(voice_preset, "name") or self.DEFAULT_PRESET

        self.model = model
        self.language = language or "Auto"

    def build_payload(self, text: str, stream: bool) -> dict:
        payload = {
            "model": self.model,
            "input": text,
            "voice": self._voice,
            "stream": stream,
            "response_format": "pcm" if stream else "wav",
            "language": self.language,
            "task_type": self._task,
        }
        if stream:
            payload["initial_codec_chunk_frames"] = self.INITIAL_CODEC_CHUNK_FRAMES
        if self._task == "Base":
            payload["ref_audio"] = self._ref_audio
            payload["ref_text"] = self._ref_text
        elif self._task == "VoiceDesign":
            payload["instructions"] = self._instructions
        return payload


class GenericHandler(ModelHandler):
    """Fallback for any model without a dedicated handler.

    Omits `model` from the payload — vLLM-Omni treats it as optional and
    falls back to whichever model is currently loaded. Forwards voice preset
    and language only. Voice cloning / design need a model-specific
    translation, so they're rejected here.
    """

    sample_rate = 24000

    def __init__(
        self,
        model: Optional[str] = None,
        language: Optional[str] = None,
        voice_preset=None,
        voice_clone=None,
        voice_design=None,
    ):
        if voice_clone or voice_design:
            raise ValueError(
                "voice_clone/voice_design require a model with a registered "
                f"handler; no handler for {model!r}"
            )
        self._voice = _get(voice_preset, "name") if voice_preset else None
        self._language = language

    def build_payload(self, text: str, stream: bool) -> dict:
        payload = {
            "input": text,
            "stream": stream,
            "response_format": "pcm" if stream else "wav",
        }
        if self._voice:
            payload["voice"] = self._voice
        if self._language:
            payload["language"] = self._language
        return payload


# Registry: HF model-name prefix → handler class. First prefix match wins.
# Add new families here; no other engine code needs to change.
_HANDLERS: list[tuple[str, type[ModelHandler]]] = [
    ("Qwen/Qwen3-TTS", Qwen3Handler),
]


def _pick_handler(model: Optional[str]) -> type[ModelHandler]:
    if model:
        for prefix, cls in _HANDLERS:
            if model.startswith(prefix):
                return cls
    return GenericHandler


# ---------------------------------------------------------------------------
# Engine shell
# ---------------------------------------------------------------------------


class TTSEngine(TTSInterface):
    """TTS engine backed by a vLLM-Omni server.

    The engine itself is thin: it picks a handler from the configured `model`,
    delegates payload construction to it, and handles the HTTP/streaming
    transport. PCM chunk math uses the sample rate the handler reports.
    """

    # Fixed for now; lifted to user-facing config later if a use case appears.
    # Measured against a live server: raw HTTP first-bytes arrive ~0.4s after
    # the request, so every ms of client-side chunk buffering adds directly
    # to time-to-first-audio. 100ms halves that penalty vs the previous
    # 200ms while keeping the websocket message rate modest (~10/s).
    _CHUNK_SIZE_MS = 100

    def __init__(
        self,
        base_url: str = "http://localhost:8091/v1",
        model: Optional[str] = None,
        language: Optional[str] = None,
        voice_preset=None,
        voice_clone=None,
        voice_design=None,
        **kwargs,
    ):
        self.base_url = base_url.rstrip("/")
        handler_cls = _pick_handler(model)
        self.handler = handler_cls(
            model=model,
            language=language,
            voice_preset=voice_preset,
            voice_clone=voice_clone,
            voice_design=voice_design,
        )
        self.sample_rate = self.handler.sample_rate
        # Bytes per yielded chunk: 16-bit PCM, aligned to 2 bytes
        self.chunk_bytes = (
            int(self.sample_rate * 2 * self._CHUNK_SIZE_MS / 1000) // 2
        ) * 2
        logger.info(
            f"vLLM-Omni TTS initialized: {self.base_url} "
            f"handler={handler_cls.__name__} model={model}"
        )

    def _build_payload(self, text: str, stream: bool) -> dict:
        return self.handler.build_payload(text, stream)

    def generate_audio(self, text: str, file_name_no_ext=None) -> str:
        """Synchronous fallback: fetch full WAV and save to cache file."""

        try:
            with httpx.Client(timeout=300.0) as client:
                r = client.post(
                    f"{self.base_url}/audio/speech",
                    json=self._build_payload(text, stream=False),
                )
                r.raise_for_status()
                wav_bytes = r.content

            path = self.generate_cache_file_name(file_name_no_ext, "wav")
            with open(path, "wb") as f:
                f.write(wav_bytes)
            return path
        except Exception as e:
            logger.error(f"vLLM-Omni TTS generate_audio error: {e}")
            return None

    async def async_generate_audio_streaming(self, text: str):
        """Async generator yielding (np.ndarray[float32], sample_rate) chunks.

        Streams raw 16-bit signed PCM at self.sample_rate Hz from vLLM-Omni,
        buffering into self.chunk_bytes-sized chunks before yielding.
        """
        buffer = b""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/audio/speech",
                    json=self._build_payload(text, stream=True),
                ) as r:
                    r.raise_for_status()
                    async for raw in r.aiter_bytes(chunk_size=4096):
                        buffer += raw
                        while len(buffer) >= self.chunk_bytes:
                            chunk = buffer[: self.chunk_bytes]
                            buffer = buffer[self.chunk_bytes :]
                            arr = (
                                np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
                                / 32768.0
                            )
                            yield arr, self.sample_rate

            # Flush remainder (align to 2 bytes / one int16 sample)
            remainder = (len(buffer) // 2) * 2
            if remainder >= 2:
                arr = (
                    np.frombuffer(buffer[:remainder], dtype=np.int16).astype(np.float32)
                    / 32768.0
                )
                yield arr, self.sample_rate

        except Exception as e:
            logger.error(f"vLLM-Omni TTS streaming error: {e}")
            raise
