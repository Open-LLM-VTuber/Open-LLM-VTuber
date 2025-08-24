import numpy as np
import whisper
from .asr_interface import ASRInterface


class VoiceRecognition(ASRInterface):
    def __init__(
        self,
        name: str = "base",
        download_root: str = None,
        device="cpu",
        prompt: str = None,
    ) -> None:
        self.model = whisper.load_model(
            name=name,
            device=device,
            download_root=download_root,
        )
        self.prompt = prompt

    def transcribe_np(self, audio: np.ndarray) -> str:
        if self.prompt is not None:
            result = self.model.transcribe(audio, prompt=self.prompt)
        else:
            result = self.model.transcribe(audio)
        full_text = result["text"]
        return full_text
