import shutil
from loguru import logger
from gradio_client import Client, file
from .tts_interface import TTSInterface


class TTSEngine(TTSInterface):
    def __init__(
        self,
        api_url: str = "http://127.0.0.1:7860/",
        prompt_wav_upload: str = "voice_clone/voice_clone_voice.wav",
        api_name: str = "voice_clone",
        gender: str = "male",
        pitch: int = 3,
        speed: int = 3,
    ):
        self.api_url = api_url
        self.new_audio_dir = "cache"
        self.file_extension = "wav"
        self.used_voices = prompt_wav_upload
        self.api_name = api_name
        self.gender = gender
        self.pitch = pitch
        self.speed = speed
        self.client = Client(api_url)

    def generate_audio(self, text, file_name_no_ext=None):
        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)
        match self.api_name:
            case "voice_clone":
                try:
                    source_file = self.client.predict(
                        text=text,
                        prompt_text="",
                        prompt_wav_upload=file(self.used_voices),
                        prompt_wav_record=None,
                        api_name="/voice_clone",
                    )
                    shutil.copyfile(source_file, file_name)
                    return file_name
                except Exception as e:
                    logger.critical(f"Error: Failed to generate audio. {e}")
                    return None
            case "voice_creation":
                try:
                    source_file = self.client.predict(
                        text=text,
                        gender=self.gender,
                        pitch=self.pitch,
                        speed=self.speed,
                        api_name="/voice_creation",
                    )
                    shutil.copyfile(source_file, file_name)
                    return file_name
                except Exception as e:
                    logger.critical(f"Error: Failed to generate audio. {e}")
                    return None
            case _:
                logger.critical(f"Error: Unknown api_name: {self.api_name}")
                return None
