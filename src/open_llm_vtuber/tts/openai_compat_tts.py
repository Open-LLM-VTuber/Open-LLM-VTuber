import os

import requests
from loguru import logger

from .tts_interface import TTSInterface


class TTSEngine(TTSInterface):
    """OpenAI-compatible TTS engine (requests-based, offline-friendly).

    Bridges Open-LLM-VTuber to any server that implements the OpenAI
    ``/v1/audio/speech`` endpoint (e.g. a local Kokoro, fish-speech, or
    any OpenAI-compatible TTS wrapper). Unlike ``openai_tts`` (which depends
    on the official OpenAI SDK client), this engine speaks plain
    ``requests`` HTTP — so it works fully offline when pointed at a local
    endpoint with no external package or cloud dependency.

    The endpoint is expected to accept a JSON body
    ``{"model", "voice", "input", "response_format"}`` and to return the
    raw audio bytes (mp3/wav) directly, not a JSON envelope.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8880/v1",
        model: str = "kokoro",
        voice: str = "af_sky",
        api_key: str = "not-needed",
        file_extension: str = "mp3",
        speed: float = 1.0,
        timeout: int = 60,
    ) -> None:
        logger.info(
            "Initializing OpenAI-compatible TTS (base_url={}, model={}, voice={})...",
            base_url,
            model,
            voice,
        )
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.voice = voice
        self.api_key = api_key
        self.speed = speed
        self.timeout = timeout
        self.file_extension = str(file_extension).lower()
        if self.file_extension not in ("mp3", "wav", "ogg", "opus", "aac", "flac"):
            logger.warning(
                "Unsupported file extension '{}' for OpenAI-compatible TTS; defaulting to 'mp3'.",
                self.file_extension,
            )
            self.file_extension = "mp3"
        self.new_audio_dir = "cache"
        self.temp_audio_file = "temp_openai_compat"

        if not os.path.exists(self.new_audio_dir):
            os.makedirs(self.new_audio_dir)

    def generate_audio(self, text: str, file_name_no_ext=None, speed: float = 1.0) -> str | None:
        """Generate speech audio file using a local/openai-compatible TTS server.

        Args:
            text (str): The text to synthesize.
            file_name_no_ext (str, optional): Name of the file without extension.
            speed (float): Speech speed (OpenAI accepts 0.25-4.0). Defaults to 1.0.

        Returns:
            str | None: The path to the generated audio file, or None if it failed.
        """
        speed = speed or self.speed
        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)
        speech_file_path = os.path.abspath(file_name)

        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        headers["Content-Type"] = "application/json"

        payload = {
            "model": self.model,
            "voice": self.voice,
            "input": text,
            "response_format": self.file_extension,
            "speed": speed,
        }

        try:
            logger.debug(
                "Generating audio via {}/audio/speech for text: '{}...'",
                self.base_url,
                text[:50],
            )
            response = requests.post(
                f"{self.base_url}/audio/speech",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("OpenAI-compatible TTS request failed: {}", exc)
            return None

        # The OpenAI speech endpoint returns raw audio bytes, not JSON.
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            logger.warning(
                "OpenAI-compatible TTS returned JSON ({}); expected raw audio. "
                "The endpoint may not implement /v1/audio/speech correctly.",
                content_type,
            )

        try:
            with open(speech_file_path, "wb") as f:
                f.write(response.content)
        except OSError as exc:
            logger.error("Failed to write audio file {}: {}", speech_file_path, exc)
            return None

        if not os.path.getsize(speech_file_path):
            logger.error("OpenAI-compatible TTS produced an empty audio file.")
            try:
                os.remove(speech_file_path)
            except OSError:
                pass
            return None

        logger.info(
            "Successfully generated audio file via compatible endpoint: {}",
            speech_file_path,
        )
        return speech_file_path
