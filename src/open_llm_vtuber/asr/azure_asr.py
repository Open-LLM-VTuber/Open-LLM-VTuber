import os
from typing import Callable
import numpy as np
from loguru import logger
import azure.cognitiveservices.speech as speechsdk
from .asr_interface import ASRInterface
import soundfile as sf
import uuid
import asyncio

CACHE_DIR = "cache"


class VoiceRecognition(ASRInterface):
    def __init__(
        self,
        subscription_key=os.getenv("AZURE_API_Key"),
        region=os.getenv("AZURE_REGION"),
        languages=["en-US", "zh-CN"],
        callback: Callable = logger.info,
    ):
        if not subscription_key or not region:
            raise ValueError(
                "Azure Speech Services requires both subscription_key and region. "
                "Please check your configuration."
            )

        self.subscription_key = subscription_key
        self.region = region
        self.callback = callback

        try:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.subscription_key, region=self.region
            )

            # Set the languages for auto detection
            self.speech_config.set_property(
                speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguages,
                ",".join(languages),
            )
        except Exception as e:
            logger.error(f"Failed to initialize Azure Speech Config: {e}")
            raise

    def _create_speech_recognizer(self, uses_default_microphone: bool = True):
        """
        Create a speech recognizer instance with the specified configuration.

        Args:
            uses_default_microphone (bool): Whether to use default microphone

        Returns:
            SpeechRecognizer: Configured speech recognizer instance
        """
        try:
            audio_config = speechsdk.AudioConfig(
                use_default_microphone=uses_default_microphone
            )
            return speechsdk.SpeechRecognizer(
                speech_config=self.speech_config, audio_config=audio_config
            )
        except Exception as e:
            logger.warning(f"Failed to create speech recognizer: {e}")
            raise

    async def async_transcribe_np(self, audio: np.ndarray) -> str:
        """
        Asynchronously transcribe audio data using Azure Speech Services with auto language detection.

        Args:
            audio (np.ndarray): Audio data as numpy array

        Returns:
            str: Transcribed text

        Raises:
            Exception: If transcription fails
        """
        temp_file = os.path.join(CACHE_DIR, f"{uuid.uuid4()}.wav")

        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            sf.write(temp_file, audio, 16000, "PCM_16")

            audio_config = speechsdk.AudioConfig(filename=temp_file)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config, audio_config=audio_config
            )

            # Perform recognition
            result = speech_recognizer.recognize_once()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                # Get detected language
                detected_language = result.properties.get(
                    speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult
                )
                logger.debug(f"Detected language: {detected_language}")
                return result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning(
                    f"No speech could be recognized: {result.no_match_details}"
                )
                return ""
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                logger.error(
                    f"Speech Recognition canceled: {cancellation_details.reason}"
                )
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    logger.error(f"Error details: {cancellation_details.error_details}")
                raise Exception(
                    f"Speech Recognition failed: {cancellation_details.reason}"
                )

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
        finally:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.debug(f"Failed to remove temporary file {temp_file}: {e}")

    def transcribe_np(self, audio: np.ndarray) -> str:
        """
        Synchronously transcribe audio data using Azure Speech Services.

        Args:
            audio (np.ndarray): Audio data as numpy array

        Returns:
            str: Transcribed text

        Raises:
            Exception: If transcription fails
        """
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run async method synchronously
            return loop.run_until_complete(self.async_transcribe_np(audio))
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise


if __name__ == "__main__":
    service = VoiceRecognition()
