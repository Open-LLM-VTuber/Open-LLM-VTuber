import os
import sys
import numpy as np
import soundfile as sf
from loguru import logger
from .tts_interface import TTSInterface

try:
    from kokoro_onnx import Kokoro
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False


class TTSEngine(TTSInterface):
    """
    Ultra-low latency Kokoro-82M ONNX TTS engine with style vector blending support.
    Synthesizes 24kHz audio in-memory without external network dependencies.
    """
    def __init__(
        self,
        model_path: str = "models/kokoro/kokoro-v0_19.onnx",
        voices_path: str = "models/kokoro/voices.bin",
        voice: str = "af_bella",
        speed: float = 1.0,
        lang: str = "en-us"
    ):
        if not KOKORO_AVAILABLE:
            raise ImportError("kokoro-onnx library is required. Run: uv add kokoro-onnx soundfile")

        self.model_path = model_path
        self.voices_path = voices_path
        self.voice = voice
        self.speed = speed
        self.lang = lang

        self.file_extension = "wav"
        self.new_audio_dir = "cache"
        os.makedirs(self.new_audio_dir, exist_ok=True)

        self._kokoro = None
        self._init_kokoro()

    def _init_kokoro(self):
        if not os.path.isfile(self.model_path) or not os.path.isfile(self.voices_path):
            logger.warning(
                f"Kokoro model files not found at {self.model_path} or {self.voices_path}. "
                "Download kokoro-v0_19.onnx and voices.bin to activate local Kokoro synthesis."
            )
            return

        try:
            self._kokoro = Kokoro(self.model_path, self.voices_path)
            logger.info("Kokoro-82M ONNX TTS engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Kokoro engine: {e}")

    def generate_audio(self, text: str, file_name_no_ext: str = None) -> str:
        """
        Synthesizes speech directly using Kokoro ONNX.
        """
        if not self._kokoro:
            self._init_kokoro()
            if not self._kokoro:
                logger.error("Kokoro engine is not initialized.")
                return None

        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)

        try:
            samples, sample_rate = self._kokoro.create(
                text=text,
                voice=self.voice,
                speed=self.speed,
                lang=self.lang
            )
            sf.write(file_name, samples, sample_rate)
            return file_name
        except Exception as e:
            logger.error(f"Kokoro audio generation failed: {e}")
            return None
