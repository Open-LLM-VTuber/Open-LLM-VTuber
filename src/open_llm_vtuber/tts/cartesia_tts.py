from __future__ import annotations

# src/open_llm_vtuber/tts/cartesia_tts.py
from pathlib import Path
from typing import Literal
import os

from loguru import logger
from open_llm_vtuber.config_manager.tts import CartesiaEmotions, CartesiaLanguages
from .tts_interface import TTSInterface

try:
    from cartesia import (
        Cartesia,
        OutputFormat_Mp3Params,
        OutputFormat_WavParams,
    )

    CARTESIA_AVAILABLE = True
except ImportError:
    CARTESIA_AVAILABLE = False
    logger.warning("cartesia not installed. Run: uv add cartesia")


CartesiaModels = Literal[
    "sonic-3", "sonic-2", "sonic-turbo", "sonic-multilingual", "sonic"
]


wav_output_format: OutputFormat_WavParams = {
    "container": "wav",
    "sample_rate": 44100,
    "encoding": "pcm_f32le",
}
mp3_output_format: OutputFormat_Mp3Params = {
    "container": "mp3",
    "sample_rate": 44100,
    "bit_rate": 128000,
}


class TTSEngine(TTSInterface):
    """
    Uses Cartesia TTS API to generate speech.
    API Reference: https://docs.cartesia.ai/use-an-sdk/python
    """

    def __init__(
        self,
        api_key: str,
        voice_id: str = "6ccbfb76-1fc6-48f7-b71d-91ac6298247b",
        model_id: CartesiaModels = "sonic-3",
        output_format: Literal["wav", "mp3"] = "wav",
        language: CartesiaLanguages = "en",
        emotion: CartesiaEmotions = "neutral",
        volume: float = 1.0,
        speed: float = 1.0,
    ):
        """
        Initializes the Cartesia TTS engine.

        Args:
            api_key (str): API key for Cartesia service.
            voice_id (str): Voice ID from Cartesia (e.g., 6ccbfb76-1fc6-48f7-b71d-91ac6298247b).
            model_id (str): Model ID for Cartesia (e.g., sonic-3).
            language (CartesiaLanguages): The language that the given voice should speak (e.g., en).
            volume (int): The volume of the generation, ranging from 0.5 to 2.0 (e.g., 1).
            speed (int): The speed of the generation, ranging from 0.6 to 1.5 (e.g., 1).
            emotion (CartesiaEmotions): The emotional guidance for a generation (e.g., neutral).
            output_format (str): Output audio format (e.g., mp3).
        """
        if not CARTESIA_AVAILABLE:
            raise ImportError(
                "cartesia is required. Install with: pip install cartesia"
            )

        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.output_format = output_format
        self.language = language
        self.emotion = emotion
        self.volume = volume
        self.speed = speed

        try:
            self.client = Cartesia(api_key=self.api_key)
            logger.info("Cartesia TTS Engine initialized successfully")
        except Exception as e:
            logger.critical(f"Failed to initialize Cartesia client: {e}")
            self.client = None
            raise e

    def generate_audio(self, text: str, file_name_no_ext: str | None = None) -> str:
        """
        Generate speech audio file using Cartesia TTS.

        Args:
            text (str): The text to synthesize.
            file_name_no_ext (str, optional): Name of the file without extension. Defaults to a generated name.

        Returns:
            str: The path to the generated audio file, or None if generation failed.
        """
        if not self.client:
            logger.error("Cartesia client not initialized. Cannot generate audio.")
            return "Cartesia client not initialized. Cannot generate audio."
        # Use the configured file extension
        file_name = self.generate_cache_file_name(file_name_no_ext, self.output_format)
        speech_file_path = Path(file_name)
        output_format = (
            wav_output_format if self.output_format == "wav" else mp3_output_format
        )
        try:
            logger.debug(
                f"Generating audio via Cartesia for text: '{text[:50]}...' with voice '{self.voice_id}' model '{self.model_id}'"
            )
            audio = self.client.tts.bytes(
                output_format=output_format,
                model_id=self.model_id,
                transcript=text,
                language=self.language,
                generation_config={
                    "volume": self.volume,
                    "speed": self.speed,
                    "emotion": self.emotion,
                },
                voice={
                    "mode": "id",
                    "id": self.voice_id,
                },
            )

            with open(speech_file_path, "wb") as f:
                for chunk in audio:
                    f.write(chunk)

            logger.info(
                f"Successfully generated audio file via Cartesia: {speech_file_path}"
            )
        except Exception as e:
            logger.critical(f"Error: Cartesia TTS unable to generate audio: {e}")
            # Clean up potentially incomplete file
            if speech_file_path.exists():
                try:
                    os.remove(speech_file_path)
                except OSError as rm_err:
                    logger.error(
                        f"Could not remove incomplete file {speech_file_path}: {rm_err}"
                    )
            raise e

        return str(speech_file_path)


# Code Used to Test Cartesia TTS Engine
# if __name__ == "__main__":
#     tts_engine = TTSEngine()
#     test_text = "Hello world! This is a test using Cartesia."
#     audio_path = tts_engine.generate_audio(test_text, "cartesia_test")
#     if audio_path:
#         print(f"Generated audio saved to: {audio_path}")
#     else:
#         print("Failed to generate audio.")
