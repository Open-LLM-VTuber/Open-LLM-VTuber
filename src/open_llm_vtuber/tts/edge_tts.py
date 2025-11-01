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
    def __init__(self, voice="en-US-AvaMultilingualNeural", pitch="+0Hz", rate="+0%", volume="+0%"):
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


# en-AU-NatashaNeural.mp3
# en-AU-WilliamNeural.mp3
# en-CA-ClaraNeural.mp3
# en-CA-LiamNeural.mp3
# en-GB-LibbyNeural.mp3
# en-GB-MaisieNeural.mp3
# en-GB-RyanNeural.mp3
# en-GB-SoniaNeural.mp3
# en-GB-ThomasNeural.mp3
# en-HK-SamNeural.mp3
# en-HK-YanNeural.mp3
# en-IE-ConnorNeural.mp3
# en-IE-EmilyNeural.mp3
# en-IN-NeerjaExpressiveNeural.mp3
# en-IN-NeerjaNeural.mp3
# en-IN-PrabhatNeural.mp3
# en-KE-AsiliaNeural.mp3
# en-KE-ChilembaNeural.mp3
# en-NG-AbeoNeural.mp3
# en-NG-EzinneNeural.mp3
# en-NZ-MitchellNeural.mp3
# en-NZ-MollyNeural.mp3
# en-PH-JamesNeural.mp3
# en-PH-RosaNeural.mp3
# en-SG-LunaNeural.mp3
# en-SG-WayneNeural.mp3
# en-TZ-ElimuNeural.mp3
# en-TZ-ImaniNeural.mp3
# en-US-AnaNeural.mp3
# en-US-AndrewMultilingualNeural.mp3
# en-US-AndrewNeural.mp3
# en-US-AriaNeural.mp3
# en-US-AvaMultilingualNeural.mp3
# en-US-AvaNeural.mp3
# en-US-BrianMultilingualNeural.mp3
# en-US-BrianNeural.mp3
# en-US-ChristopherNeural.mp3
# en-US-EmmaMultilingualNeural.mp3
# en-US-EmmaNeural.mp3
# en-US-EricNeural.mp3
# en-US-GuyNeural.mp3
# en-US-JennyNeural.mp3
# en-US-MichelleNeural.mp3
# en-US-RogerNeural.mp3
# en-US-SteffanNeural.mp3
# en-ZA-LeahNeural.mp3
# en-ZA-LukeNeural.mp3