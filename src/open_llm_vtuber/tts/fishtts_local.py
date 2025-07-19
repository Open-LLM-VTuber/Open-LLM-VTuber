import requests
from loguru import logger
from .tts_interface import TTSInterface
import ormsgpack
from pydub import AudioSegment
from pydub.playback import play
from typing import Optional, List, Union

from fish_speech.utils.file import audio_to_bytes, read_ref_text
from fish_speech.utils.schema import ServeReferenceAudio, ServeTTSRequest


class TTSEngine(TTSInterface):
    def __init__(
        self,
        api_url: str = "http://127.0.0.1:8080/v1/tts",
        reference_id: Optional[str] = None,
        reference_audio: Optional[List[str]] = None,
        reference_text: Optional[List[str]] = None,
        output: str = "generated_audio",
        audio_format: str = "wav",
        latency: str = "normal",
        max_new_tokens: int = 1024,
        chunk_length: int = 300,
        top_p: float = 0.8,
        repetition_penalty: float = 1.1,
        temperature: float = 0.8,
        streaming: bool = False,
        channels: int = 1,
        rate: int = 44100,
        use_memory_cache: str = "off",
        seed: Optional[int] = None,
        api_key: str = "YOUR_API_KEY",
    ):
        self.api_url = api_url
        self.reference_id = reference_id
        self.reference_audio = reference_audio or []
        self.reference_text = reference_text or []
        self.output = output
        self.audio_format = audio_format
        self.latency = latency
        self.max_new_tokens = max_new_tokens
        self.chunk_length = chunk_length
        self.top_p = top_p
        self.repetition_penalty = repetition_penalty
        self.temperature = temperature
        self.streaming = streaming
        self.channels = channels
        self.rate = rate
        self.use_memory_cache = use_memory_cache
        self.seed = seed
        self.api_key = api_key
        self.new_audio_dir = "cache"
        self.file_extension = audio_format

    def generate_audio(self, text, file_name_no_ext=None):
        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)

        # Prepare reference data
        byte_audios = [audio_to_bytes(ref_audio) for ref_audio in self.reference_audio] if self.reference_audio else []
        ref_texts = [read_ref_text(ref_text) for ref_text in self.reference_text] if self.reference_text else []

        data = {
            "text": text,
            "references": [
                ServeReferenceAudio(
                    audio=ref_audio if ref_audio is not None else b"", 
                    text=ref_text
                )
                for ref_text, ref_audio in zip(ref_texts, byte_audios)
            ],
            "reference_id": self.reference_id,
            "format": self.audio_format,
            "max_new_tokens": self.max_new_tokens,
            "chunk_length": self.chunk_length,
            "top_p": self.top_p,
            "repetition_penalty": self.repetition_penalty,
            "temperature": self.temperature,
            "streaming": self.streaming,
            "use_memory_cache": self.use_memory_cache,
            "seed": self.seed,
        }

        pydantic_data = ServeTTSRequest(**data)

        try:
            response = requests.post(
                self.api_url,
                data=ormsgpack.packb(pydantic_data, option=ormsgpack.OPT_SERIALIZE_PYDANTIC),
                stream=self.streaming,
                headers={
                    "authorization": f"Bearer {self.api_key}",
                    "content-type": "application/msgpack",
                },
                timeout=120
            )

            if response.status_code == 200:
                if self.streaming:
                    # For streaming, we'll save the entire response to a file first
                    with open(file_name, "wb") as audio_file:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                audio_file.write(chunk)
                else:
                    with open(file_name, "wb") as audio_file:
                        audio_file.write(response.content)

                return file_name
            else:
                logger.critical(
                    f"Error: Failed to generate audio. Status code: {response.status_code}\n{response.json()}"
                )
                return ""

        except Exception as e:
            logger.critical(f"Error during TTS request: {str(e)}")
            return ""