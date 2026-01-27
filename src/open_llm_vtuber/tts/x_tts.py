import requests
from loguru import logger
from .tts_interface import TTSInterface


class TTSEngine(TTSInterface):
    def __init__(
        self,
        api_url: str = "http://127.0.0.1:8020/tts_to_audio",
        speaker_wav: str = "female",
        language: str = "en",
    ):
        self.api_url = api_url
        self.speaker_wav = speaker_wav
        self.language = language
        self.new_audio_dir = "cache"
        self.file_extension = "wav"

    def generate_audio(self, text, file_name_no_ext=None):
        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)

        # Prepare the data for the POST request
        data = {
            "text": text,
            "speaker_wav": self.speaker_wav,
            "language": self.language,
        }

        # Send POST request to the TTS API
        response = requests.post(self.api_url, json=data, timeout=120)

        # Check if the request was successful
        if response.status_code == 200:
            # Save the audio content to a file
            with open(file_name, "wb") as audio_file:
                audio_file.write(response.content)
            return file_name
        else:
            # Handle errors or unsuccessful requests
            logger.critical(
                f"Error: Failed to generate audio. Status code: {response.status_code}"
            )
            return None
