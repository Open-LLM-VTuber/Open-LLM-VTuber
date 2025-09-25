import numpy as np
from faster_whisper import WhisperModel
from .asr_interface import ASRInterface


class VoiceRecognition(ASRInterface):
    BEAM_SEARCH = True
    # SAMPLE_RATE # Defined in asr_interface.py

    def __init__(
        self,
        model_path: str = "distil-medium.en",
        download_root: str = None,
        language: str = "en",
        device: str = "auto",
        compute_type: str = "int8",
        prompt: str = None,
    ) -> None:
        self.MODEL_PATH = model_path
        self.LANG = language
        self.prompt = prompt
        self.model = WhisperModel(
            model_size_or_path=model_path,
            download_root=download_root,
            device=device,
            compute_type=compute_type,
        )

    def transcribe_np(self, audio: np.ndarray) -> str:
        if self.prompt:
            segments, info = self.model.transcribe(
                audio,
                beam_size=5 if self.BEAM_SEARCH else 1,
                language=self.LANG if self.LANG else None,
                condition_on_previous_text=False,
                initial_prompt=self.prompt,
            )
        else:
            segments, info = self.model.transcribe(
                audio,
                beam_size=5 if self.BEAM_SEARCH else 1,
                language=self.LANG if self.LANG else None,
                condition_on_previous_text=False,
            )
        text = [segment.text for segment in segments]

        if not text:
            return ""
        else:
            return "".join(text)
