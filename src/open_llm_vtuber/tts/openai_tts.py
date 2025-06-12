# src/open_llm_vtuber/tts/openai_tts.py
import os
import sys
from pathlib import Path

from loguru import logger
from openai import OpenAI  # Use the official OpenAI library

from .tts_interface import TTSInterface

# Add the current directory to sys.path for relative imports if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)


class TTSEngine(TTSInterface):
    """
    Uses an OpenAI-compatible TTS API endpoint to generate speech.
    Connects to a server specified by `base_url`.
    API Reference: https://platform.openai.com/docs/api-reference/audio/createSpeech (for standard parameters)
    """

    def __init__(
        self,
        model="kokoro",  # Default model based on user example
        voice="af_sky+af_bella",  # Default voice based on user example
        api_key="not-needed",  # Default for local/compatible servers that don't require auth
        base_url="http://localhost:8880/v1",  # Default to the specified endpoint
        file_extension: str = "mp3",  # Configurable file extension
        **kwargs,  # Allow passing additional args to OpenAI client
    ):
        """
        Initializes the OpenAI TTS engine.

        Args:
            model (str): The TTS model to use (e.g., 'tts-1', 'tts-1-hd').
            voice (str): The voice to use (e.g., 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer').
            api_key (str, optional): API key for the TTS service. Defaults to "not-needed".
            base_url (str, optional): Base URL of the OpenAI-compatible TTS endpoint. Defaults to "http://localhost:8880/v1".
        """
        self.model = model
        self.voice = voice
        self.file_extension = file_extension.lower()  # Use configured extension
        if self.file_extension not in ["mp3", "wav"]:
            logger.warning(
                f"Unsupported file extension '{self.file_extension}' configured for OpenAI TTS. Defaulting to 'mp3'."
            )
            self.file_extension = "mp3"
        self.new_audio_dir = "cache"
        self.temp_audio_file = "temp_openai"  # Use a different temp name

        if not os.path.exists(self.new_audio_dir):
            os.makedirs(self.new_audio_dir)

        try:
            # Initialize OpenAI client
            self.client = OpenAI(api_key=api_key, base_url=base_url, **kwargs)
            logger.info(
                f"OpenAI-compatible TTS Engine initialized, targeting endpoint: {base_url}"
            )
        except Exception as e:
            logger.critical(f"Failed to initialize OpenAI client: {e}")
            self.client = None  # Ensure client is None if init fails

    def generate_audio(self, text, file_name_no_ext=None, speed=1.0):
        """
        Generate speech audio file using OpenAI TTS.

        Args:
            text (str): The text to synthesize.
            file_name_no_ext (str, optional): Name of the file without extension. Defaults to a generated name.
            speed (float): The speed of the speech (0.25 to 4.0). Defaults to 1.0.

        Returns:
            str: The path to the generated audio file, or None if generation failed.
        """
        if not self.client:
            logger.error("OpenAI client not initialized. Cannot generate audio.")
            return None

        # Use the configured file extension
        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)
        speech_file_path = Path(file_name)

        try:
            logger.debug(
                f"Generating audio via {self.client.base_url} for text: '{text[:50]}...' with voice '{self.voice}' model '{self.model}'"
            )
            # Use with_streaming_response for potentially better handling of large audio files or network issues
            with (
                self.client.audio.speech.with_streaming_response.create(
                    model=self.model,  # Model name expected by the compatible server (e.g., "kokoro")
                    voice=self.voice,  # Voice name(s) expected by the compatible server (e.g., "af_sky+af_bella")
                    input=text,
                    response_format=self.file_extension,  # Use configured extension
                    speed=speed,
                ) as response
            ):
                # Stream the audio content to the file
                response.stream_to_file(speech_file_path)

            logger.info(
                f"Successfully generated audio file via compatible endpoint: {speech_file_path}"
            )

        except Exception as e:
            logger.critical(f"Error: OpenAI TTS unable to generate audio: {e}")
            # Clean up potentially incomplete file
            if speech_file_path.exists():
                try:
                    os.remove(speech_file_path)
                except OSError as rm_err:
                    logger.error(
                        f"Could not remove incomplete file {speech_file_path}: {rm_err}"
                    )
            return None

        return str(speech_file_path)


# Example usage (optional, for testing with the compatible endpoint)
# if __name__ == '__main__':
#     # Configure TTSEngine to use the specific model and voice from the example
#     # The base_url and api_key will use the defaults set in __init__
#     tts_engine = TTSEngine(model="kokoro", voice="af_sky+af_bella")
#     test_text = "Hello world! This is a test using the compatible endpoint."
#     audio_path = tts_engine.generate_audio(test_text, "compatible_endpoint_test")
#     if audio_path:
#         print(f"Generated audio saved to: {audio_path}")
#     else:
#         print("Failed to generate audio.")
