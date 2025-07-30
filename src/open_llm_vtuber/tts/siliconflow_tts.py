import requests
from loguru import logger
from .tts_interface import TTSInterface


class SiliconFlowTTS(TTSInterface):
    def __init__(
        self,
        api_url,
        api_key,
        default_model,
        default_voice,
        sample_rate,
        response_format,
        stream,
        speed,
        gain,
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.default_model = default_model
        self.default_voice = default_voice
        self.sample_rate = sample_rate
        self.response_format = response_format
        self.stream = stream
        self.speed = speed
        self.gain = gain

    def generate_audio(self, text: str, file_name_no_ext=None) -> str:
        cache_file = self.generate_cache_file_name(
            file_name_no_ext, file_extension=self.response_format
        )
        payload = {
            "input": text,
            "response_format": self.response_format,
            "sample_rate": self.sample_rate,
            "stream": self.stream,
            "speed": self.speed,
            "gain": self.gain,
            "model": self.default_model,
            "voice": self.default_voice,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            if self.api_url is None:
                logger.error("API URL 未正确配置，请检查配置文件。The configuration is incorrect. Please check the configuration file.")
                return ""
            response = requests.request(
                "POST", self.api_url, json=payload, headers=headers
            )
            response.raise_for_status()  # Check the response status code
            with open(cache_file, "wb") as f:
                f.write(response.content)
            logger.info(f"成功生成音频文件Successfully generated the audio file.: {cache_file}")
            return cache_file
        except requests.RequestException as e:
            logger.error(f"生成音频文件失败Failed to generate the audio file.: {e}")
            return ""

    def remove_file(self, filepath: str, verbose: bool = True) -> None:
        super().remove_file(filepath, verbose)

    def generate_cache_file_name(self, file_name_no_ext=None, file_extension="wav"):
        return super().generate_cache_file_name(file_name_no_ext, file_extension)
