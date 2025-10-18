# src/open_llm_vtuber/tts/elevenlabs_tts.py
import os
from pathlib import Path

from loguru import logger
from elevenlabs.client import ElevenLabs

from .tts_interface import TTSInterface


class TTSEngine(TTSInterface):
    """
    Uses ElevenLabs TTS API to generate speech.
    API Reference: https://elevenlabs.io/docs/api-reference/text-to-speech
    """

    def __init__(
        self,
        api_key: str,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2",
        output_format: str = "mp3_44100_128",
        stability: float = 0.5,
        similarity_boost: float = 0.5,
        style: float = 0.0,
        use_speaker_boost: bool = True,
    ):
        """
        Initializes the ElevenLabs TTS engine.

        Args:
            api_key (str): API key for ElevenLabs service.
            voice_id (str): Voice ID from ElevenLabs (e.g., JBFqnCBsd6RMkjVDRZzb).
            model_id (str): Model ID for ElevenLabs (e.g., eleven_multilingual_v2).
            output_format (str): Output audio format (e.g., mp3_44100_128).
            stability (float): Voice stability (0.0 to 1.0).
            similarity_boost (float): Voice similarity boost (0.0 to 1.0).
            style (float): Voice style exaggeration (0.0 to 1.0).
            use_speaker_boost (bool): Enable speaker boost for better quality.
        """
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.output_format = output_format
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.style = style
        self.use_speaker_boost = use_speaker_boost

        # Determine file extension from output format
        if "mp3" in output_format:
            self.file_extension = "mp3"
        elif "pcm" in output_format:
            self.file_extension = "wav"
        else:
            logger.warning(f"Unknown output format '{output_format}', defaulting to mp3 extension.")
            self.file_extension = "mp3"  # Default to mp3

        try:
            # Initialize ElevenLabs client
            self.client = ElevenLabs(api_key=api_key)
            logger.info("ElevenLabs TTS Engine initialized successfully")
        except Exception as e:
            logger.critical(f"Failed to initialize ElevenLabs client: {e}")
            self.client = None
            raise e

    def generate_audio(self, text: str, file_name_no_ext: str | None = None) -> str | None:
        """
        Generate speech audio file using ElevenLabs TTS.

        Args:
            text (str): The text to synthesize.
            file_name_no_ext (str, optional): Name of the file without extension. Defaults to a generated name.

        Returns:
            str: The path to the generated audio file, or None if generation failed.
        """
        if not self.client:
            logger.error("ElevenLabs client not initialized. Cannot generate audio.")
            return None

        # Use the configured file extension
        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)
        speech_file_path = Path(file_name)

        try:
            logger.debug(
                f"Generating audio via ElevenLabs for text: '{text[:50]}...' with voice '{self.voice_id}' model '{self.model_id}'"
            )

            # Generate audio using ElevenLabs API
            audio = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id=self.model_id,
                output_format=self.output_format,
                voice_settings={
                    "stability": self.stability,
                    "similarity_boost": self.similarity_boost,
                    "style": self.style,
                    "use_speaker_boost": self.use_speaker_boost,
                },
            )

            # Write the audio data to file
            with open(speech_file_path, "wb") as f:
                for chunk in audio:
                    f.write(chunk)

            logger.info(
                f"Successfully generated audio file via ElevenLabs: {speech_file_path}"
            )

        except Exception as e:
            logger.critical(f"Error: ElevenLabs TTS unable to generate audio: {e}")
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


# Example usage (optional, for testing)
# if __name__ == '__main__':
#     tts_engine = TTSEngine(
#         api_key="your_api_key",
#         voice_id="JBFqnCBsd6RMkjVDRZzb",
#         model_id="eleven_multilingual_v2"
#     )
#     test_text = "Hello world! This is a test using ElevenLabs."
#     audio_path = tts_engine.generate_audio(test_text, "elevenlabs_test")
#     if audio_path:
#         print(f"Generated audio saved to: {audio_path}")
#     else:
#         print("Failed to generate audio.")
