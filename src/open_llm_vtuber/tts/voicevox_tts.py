# src/open_llm_vtuber/tts/voicevox_tts.py
"""
VOICEVOX TTS Engine

VOICEVOX is a free Japanese text-to-speech engine.
This module interfaces with the VOICEVOX engine via its local HTTP API.

API Documentation: https://voicevox.github.io/voicevox_engine/api/
Default endpoint: http://localhost:50021
"""

import os
import requests
from loguru import logger

from .tts_interface import TTSInterface


class TTSEngine(TTSInterface):
    """
    VOICEVOX TTS Engine implementation.

    Uses the VOICEVOX local API to generate speech audio.
    The VOICEVOX engine must be running locally before using this TTS.

    Available speakers can be obtained via GET /speakers endpoint.
    Common speaker IDs:
        - 0: 四国めたん (あまあま)
        - 1: ずんだもん (あまあま)
        - 2: 四国めたん (ノーマル)
        - 3: ずんだもん (ノーマル)
        - 8: 春日部つむぎ (ノーマル)
        - 10: 雨晴はう (ノーマル)
        etc.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:50021",
        speaker_id: int = 1,
        speed_scale: float = 1.0,
        pitch_scale: float = 0.0,
        intonation_scale: float = 1.0,
        volume_scale: float = 1.0,
        pre_phoneme_length: float = 0.1,
        post_phoneme_length: float = 0.1,
        timeout: int = 30,
    ):
        """
        Initialize the VOICEVOX TTS engine.

        Args:
            base_url: Base URL of the VOICEVOX engine API (default: http://localhost:50021)
            speaker_id: Speaker ID to use (default: 1 = ずんだもん あまあま)
            speed_scale: Speech speed multiplier (default: 1.0)
            pitch_scale: Pitch adjustment in semitones (default: 0.0)
            intonation_scale: Intonation scale (default: 1.0)
            volume_scale: Volume scale (default: 1.0)
            pre_phoneme_length: Silence before speech in seconds (default: 0.1)
            post_phoneme_length: Silence after speech in seconds (default: 0.1)
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = base_url.rstrip("/")
        self.speaker_id = speaker_id
        self.speed_scale = speed_scale
        self.pitch_scale = pitch_scale
        self.intonation_scale = intonation_scale
        self.volume_scale = volume_scale
        self.pre_phoneme_length = pre_phoneme_length
        self.post_phoneme_length = post_phoneme_length
        self.timeout = timeout

        self.new_audio_dir = "cache"
        if not os.path.exists(self.new_audio_dir):
            os.makedirs(self.new_audio_dir)

        logger.info(
            f"VOICEVOX TTS Engine initialized: base_url={self.base_url}, speaker_id={self.speaker_id}"
        )

    def generate_audio(self, text: str, file_name_no_ext: str = None) -> str:
        """
        Generate speech audio file using VOICEVOX.

        Args:
            text: The text to synthesize.
            file_name_no_ext: Name of the file without extension (optional).

        Returns:
            str: The path to the generated audio file, or None if generation failed.
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to VOICEVOX TTS")
            return None

        file_name = self.generate_cache_file_name(file_name_no_ext, "wav")

        try:
            # Step 1: Create audio query
            audio_query = self._create_audio_query(text)
            if audio_query is None:
                return None

            # Step 2: Apply custom parameters
            audio_query["speedScale"] = self.speed_scale
            audio_query["pitchScale"] = self.pitch_scale
            audio_query["intonationScale"] = self.intonation_scale
            audio_query["volumeScale"] = self.volume_scale
            audio_query["prePhonemeLength"] = self.pre_phoneme_length
            audio_query["postPhonemeLength"] = self.post_phoneme_length

            # Step 3: Synthesize audio
            audio_data = self._synthesize(audio_query)
            if audio_data is None:
                return None

            # Step 4: Save to file
            with open(file_name, "wb") as f:
                f.write(audio_data)

            logger.info(f"Successfully generated VOICEVOX audio: {file_name}")
            return file_name

        except Exception as e:
            logger.error(f"VOICEVOX TTS error: {e}")
            return None

    def _create_audio_query(self, text: str) -> dict | None:
        """
        Create an audio query from text.

        Args:
            text: The text to convert.

        Returns:
            dict: The audio query object, or None if failed.
        """
        try:
            url = f"{self.base_url}/audio_query"
            params = {"text": text, "speaker": self.speaker_id}

            response = requests.post(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.ConnectionError:
            logger.error(
                f"Failed to connect to VOICEVOX engine at {self.base_url}. "
                "Make sure VOICEVOX is running."
            )
            return None
        except requests.exceptions.Timeout:
            logger.error("VOICEVOX audio_query request timed out")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"VOICEVOX audio_query HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"VOICEVOX audio_query error: {e}")
            return None

    def _synthesize(self, audio_query: dict) -> bytes | None:
        """
        Synthesize audio from an audio query.

        Args:
            audio_query: The audio query object from _create_audio_query.

        Returns:
            bytes: The WAV audio data, or None if failed.
        """
        try:
            url = f"{self.base_url}/synthesis"
            params = {"speaker": self.speaker_id}
            headers = {"Content-Type": "application/json"}

            response = requests.post(
                url,
                params=params,
                headers=headers,
                json=audio_query,
                timeout=self.timeout,
            )
            response.raise_for_status()

            return response.content

        except requests.exceptions.ConnectionError:
            logger.error(
                f"Failed to connect to VOICEVOX engine at {self.base_url}. "
                "Make sure VOICEVOX is running."
            )
            return None
        except requests.exceptions.Timeout:
            logger.error("VOICEVOX synthesis request timed out")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"VOICEVOX synthesis HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"VOICEVOX synthesis error: {e}")
            return None

    def get_speakers(self) -> list | None:
        """
        Get list of available speakers from VOICEVOX.

        Returns:
            list: List of speaker information, or None if failed.
        """
        try:
            url = f"{self.base_url}/speakers"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get VOICEVOX speakers: {e}")
            return None
