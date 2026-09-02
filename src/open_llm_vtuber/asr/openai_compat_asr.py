import io
import wave

import numpy as np
import requests
from loguru import logger

from .asr_interface import ASRInterface


class VoiceRecognition(ASRInterface):
    """OpenAI-compatible ASR engine.

    Bridges Open-LLM-VTuber to any server that implements the OpenAI
    ``/v1/audio/transcriptions`` endpoint (e.g. a local faster-whisper
    wrapper such as the GLaDOS local ASR server). This keeps speech
    recognition fully offline when pointed at a local endpoint.

    The endpoint is expected to accept a multipart ``file`` upload plus
    optional ``model``/``language``/``prompt``/``temperature`` fields and
    to return the transcription as plain text (``response_format=text``)
    or as JSON (``{"text": "..."}``).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8733/v1",
        model: str = "base",
        api_key: str = "local",
        language: str | None = None,
        timeout: int = 60,
    ) -> None:
        logger.info("Initializing OpenAI-compatible ASR (base_url={})...", base_url)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.language = language
        self.timeout = timeout

    def _to_wav_buffer(self, audio: np.ndarray) -> io.BytesIO:
        """Convert a float32 numpy audio array into a 16-bit PCM WAV buffer."""
        audio = np.clip(audio, -1, 1)
        audio_integer = (audio * 32767).astype(np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(self.NUM_CHANNELS)
            wf.setsampwidth(self.SAMPLE_WIDTH)
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(audio_integer.tobytes())
        buffer.seek(0)
        return buffer

    def transcribe_np(self, audio: np.ndarray) -> str:
        """Transcribe speech audio in numpy array format and return the text."""
        logger.info("Transcribing audio (OpenAICompatASR)...")
        buffer = self._to_wav_buffer(audio)

        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

        data = {"model": self.model, "response_format": "text"}
        if self.language:
            data["language"] = self.language

        try:
            response = requests.post(
                f"{self.base_url}/audio/transcriptions",
                headers=headers,
                data=data,
                files={"file": ("audio.wav", buffer.read(), "audio/wav")},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("OpenAI-compatible ASR request failed: {}", exc)
            return ""

        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            payload = response.json()
            return payload.get("text", "") if isinstance(payload, dict) else str(payload)
        return response.text.strip()
