import sys
import os

import edge_tts
from loguru import logger
from .tts_interface import TTSInterface

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)


# Check out doc at https://github.com/rany2/edge-tts
# Use `edge-tts --list-voices` to list all available voices


class TTSEngine(TTSInterface):
    def __init__(
        self,
        voice="en-US-AvaMultilingualNeural",
        pitch="+0Hz",
        rate="+0%",
        volume="+0%"
    ):
        """
        Initialize Edge TTS.

        Args:
            voice (str): The voice name to use for edge TTS (use 'edge-tts --list-voices' to list available voices).

            pitch (str): Pitch adjustment in Hertz. For positive values, append with a '+'. E.g. +0Hz, -10Hz, +20Hz.

            rate (str): Speaking rate adjustment, as a percentage. E.g. +0%, -10%, +20%.

            volume (str): Volume adjustment percentage. E.g. +0%, -10%, +20%.

        """

        self.voice = voice
        self.pitch = pitch
        self.rate = rate
        self.volume = volume

        self.temp_audio_file = "temp"
        self.file_extension = "mp3"
        self.new_audio_dir = "cache"

        if not os.path.exists(self.new_audio_dir):
            os.makedirs(self.new_audio_dir)

    def generate_audio(self, text, file_name_no_ext=None):
        """
        Generate speech audio file using TTS.
        text: str
            the text to speak
        file_name_no_ext: str
            name of the file without extension


        Returns:
        str: the path to the generated audio file

        """
        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch,
                volume=self.volume,
            )
            communicate.save_sync(file_name)
        except Exception as e:
            logger.critical(f"\nError: edge-tts unable to generate audio: {e}")
            logger.critical("It's possible that edge-tts is blocked in your region.")
            return None

        return file_name
