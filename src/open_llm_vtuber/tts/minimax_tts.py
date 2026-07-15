import os
import requests
from loguru import logger
from .tts_interface import TTSInterface


class TTSEngine(TTSInterface):
    def __init__(
        self,
        group_id: str,
        api_key: str,
        api_url: str = "https://api.minimax.io/v1/t2a_v2",
        model: str = "speech-2.8-hd",
        voice_id: str = "male-qn-qingse",
        pronunciation_dict: str = "",
    ):
        self.group_id = group_id
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.voice_id = voice_id
        self.pronunciation_dict = pronunciation_dict
        self.file_extension = "mp3"
        self.cache_dir = "cache"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def generate_audio(self, text: str, file_name_no_ext=None) -> str:
        import json

        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)
        params = {"GroupId": self.group_id} if self.group_id else None
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "authorization": "Bearer " + self.api_key,
        }

        # 处理 pronunciation_dict 字符串为 dict，如果为空则传 {"tone": []}
        try:
            pronunciation_dict = (
                json.loads(self.pronunciation_dict)
                if self.pronunciation_dict.strip()
                else {"tone": []}
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse pronunciation_dict: {e}")
            pronunciation_dict = {"tone": []}

        body = {
            "model": self.model,
            "text": text,
            "stream": True,
            "voice_setting": {
                "voice_id": self.voice_id,
                "speed": 1.0,
                "vol": 1.0,
                "pitch": 0,
            },
            "pronunciation_dict": pronunciation_dict,
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": self.file_extension,
                "channel": 1,
            },
        }

        try:
            response = requests.request(
                "POST",
                self.api_url,
                params=params,
                stream=True,
                headers=headers,
                data=json.dumps(body),
                timeout=120,
            )
            audio = b""
            for chunk in response.raw:
                if chunk:
                    if chunk[:5] == b"data:":
                        try:
                            data = json.loads(chunk[5:])
                            if "data" in data and "extra_info" not in data:
                                if "audio" in data["data"]:
                                    hex_audio = data["data"]["audio"]
                                    decoded = bytes.fromhex(hex_audio)
                                    audio += decoded
                        except Exception as e:
                            logger.error(f"Failed to parse audio chunk: {e}")
            with open(file_name, "wb") as f:
                f.write(audio)
            return file_name
        except Exception as e:
            logger.error(f"Exception in minimax_tts generate_audio: {e}")
            return None
