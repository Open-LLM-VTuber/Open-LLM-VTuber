import os
from typing import Optional
from TTS.api import TTS
from loguru import logger
import torch
from .tts_interface import TTSInterface


class TTSEngine(TTSInterface):
    """
    CoquiTTS engine implementation supporting both single-speaker and multi-speaker modes.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        speaker_wav: Optional[str] = None,
        language: Optional[str] = "en",
        device: Optional[str] = None,
    ):
        """
        Initialize CoquiTTS engine.

        Args:
            model_name: Name of the TTS model to use. If None, will use default model.
            speaker_wav: Path to speaker wav file for voice cloning. Only used in multi-speaker mode.
            language: Language code for multi-lingual models. Default is "en".
            device: Device to run model on ("cuda", "cpu", etc). If None, will auto-detect.
        """
        # Auto-detect device if not specified
        if device:
            self.device = device
        else:
            logger.info("coqui_tts: Using default device")
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(f"coqui_tts: Using device: {device}")

        try:
            # Initialize TTS model
            if model_name:
                self.tts = TTS(model_name=model_name).to(self.device)
            else:
                # Use default model if none specified
                self.tts = TTS().to(self.device)

            self.speaker_wav = speaker_wav
            self.language = language

            # Check if model is multi-speaker
            self.is_multi_speaker = (
                hasattr(self.tts, "speakers") and self.tts.speakers is not None
            )

        except Exception as e:
            raise RuntimeError(f"Failed to initialize CoquiTTS model: {str(e)}")

    def generate_audio(self, text: str, file_name_no_ext: Optional[str] = None) -> str:
        """
        Generate speech audio file using CoquiTTS.

        Args:
            text: Text to synthesize
            file_name_no_ext: Output filename without extension (optional)

        Returns:
            Path to generated audio file
        """
        try:
            # Generate output path
            output_path = self.generate_cache_file_name(file_name_no_ext, "wav")

            # Generate speech based on speaker mode
            if self.is_multi_speaker and self.speaker_wav:
                # Multi-speaker mode with voice cloning
                self.tts.tts_to_file(
                    text=text,
                    speaker_wav=self.speaker_wav,
                    language=self.language,
                    file_path=output_path,
                )
            else:
                # Single speaker mode
                self.tts.tts_to_file(text=text, file_path=output_path)

            if not os.path.exists(output_path):
                raise FileNotFoundError(
                    f"Failed to generate audio file at {output_path}"
                )

            return output_path

        except Exception as e:
            raise RuntimeError(f"Failed to generate audio: {str(e)}")

    @staticmethod
    def list_available_models() -> list:
        """
        List all available CoquiTTS models.

        Returns:
            List of available model names
        """
        try:
            return TTS().list_models()
        except Exception as e:
            raise RuntimeError(f"Failed to list available models: {str(e)}")

    def get_speaker_info(self) -> dict:
        """
        Get information about available speakers for multi-speaker models.

        Returns:
            Dictionary containing speaker information
        """
        if not self.is_multi_speaker:
            return {"multi_speaker": False}

        try:
            return {
                "multi_speaker": True,
                "speakers": self.tts.speakers,
                "languages": self.tts.languages
                if hasattr(self.tts, "languages")
                else None,
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get speaker information: {str(e)}")
