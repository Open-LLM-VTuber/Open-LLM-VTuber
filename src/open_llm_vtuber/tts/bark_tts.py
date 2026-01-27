import os
import sys
import time
import platform
from bark import SAMPLE_RATE, generate_audio, preload_models
from loguru import logger
from scipy.io.wavfile import write as write_wav
from .tts_interface import TTSInterface

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)


class TTSEngine(TTSInterface):
    def __init__(self, voice="v2/en_speaker_1"):
        if platform.system() == "Darwin":
            logger.info(">> Note: Running barkTTS on macOS can be very slow.")
            os.environ["SUNO_ENABLE_MPS"] = "True"
            os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
            os.environ["SUNO_OFFLOAD_CPU"] = "False"

        # download and load all models
        preload_models()
        self.voice = voice

        self.temp_audio_file = "temp"
        self.file_extension = "wav"
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

        start_time = time.time()

        # generate audio from text
        audio_array = generate_audio(text, history_prompt=self.voice)

        # save audio to disk
        write_wav(filename=file_name, rate=SAMPLE_RATE, data=audio_array)

        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(
            "Execution time:",
            execution_time,
            "seconds",
            "\n",
            execution_time / 60,
            "minutes",
        )

        return file_name
