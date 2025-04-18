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
        device: str = "auto",
    ) -> None:
        self.MODEL_PATH = model_path

        self.model = WhisperModel(
            model_path,
            download_root=download_root,
            device=device,
            compute_type="float32",
        )

    def transcribe_np(self, audio: np.ndarray) -> str:
        segments, info = self.model.transcribe(
            audio,
            beam_size=5 if self.BEAM_SEARCH else 1,
            condition_on_previous_text=False,
        )

        text = [segment.text for segment in segments]

        if not text:
            return ""
        else:
            return "".join(text)
