from .tts_interface import TTSInterface


class TTSEngine(TTSInterface):
    """No-op TTS engine that disables speech synthesis."""

    def __init__(self):
        self.file_extension = "wav"

    def generate_audio(self, text: str, file_name_no_ext=None) -> str:  # type: ignore[override]
        """Return None to indicate no audio was generated."""
        return None  # type: ignore[return-value]
