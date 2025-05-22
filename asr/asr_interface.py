import abc
import numpy as np
from .asr_with_vad import VoiceRecognitionVAD


class ASRInterface(metaclass=abc.ABCMeta):

    asr_with_vad: VoiceRecognitionVAD = None
    SAMPLE_RATE = 16000  # Default sample rate, specific ASR might override or use this
    NUM_CHANNELS = 1
    SAMPLE_WIDTH = 2 # Bytes per sample

    def transcribe_with_local_vad(self, 
                                   audio_save_callback: Callable[[np.ndarray, str, int], None] | None = None,
                                   audio_save_format: str = "wav",
                                   session_log_dir: str | None = None
                                   ) -> str:
        """Activate the microphone on this device, transcribe audio when a pause in speech is detected using VAD, 
        and return the transcription. Optionally saves the recorded audio.

        This method should block until a transcription is available.

        Args:
            audio_save_callback: Optional callback function to save recorded audio.
                                 Expected signature: (audio_data: np.ndarray, filepath: str, sample_rate: int) -> None
            audio_save_format: Format for saving audio (e.g., "wav").
            session_log_dir: Directory to save recorded audio.

        Returns:
            The transcription of the speech audio.
        """
        if self.asr_with_vad is None:
            # Pass the callback and related params to VoiceRecognitionVAD
            self.asr_with_vad = VoiceRecognitionVAD(
                asr_transcribe_func=self.transcribe_np,
                audio_save_callback=audio_save_callback,
                audio_save_format=audio_save_format,
                session_log_dir=session_log_dir
            )
        # Ensure start_listening can somehow use these or they are set if VAD is re-initialized elsewhere.
        # For now, VAD is initialized once here. If it's re-initialized, this logic might need adjustment
        # or these params need to be stored on self.asr_with_vad if its methods are called directly later.
        return self.asr_with_vad.start_listening()

    @abc.abstractmethod
    def transcribe_np(self, audio: np.ndarray) -> str:
        """Transcribe speech audio in numpy array format and return the transcription.

        Args:
            audio: The numpy array of the audio data to transcribe.
        """
        raise NotImplementedError

    def nparray_to_audio_file(
        self, audio: np.ndarray, sample_rate: int, file_path: str
    ) -> None:
        """Convert a numpy array of audio data to a .wav file.

        Args:
            audio: The numpy array of audio data.
            sample_rate: The sample rate of the audio data.
            file_path: The path to save the .wav file.
        """
        import wave

        # Make sure the audio is in the range [-1, 1]
        audio = np.clip(audio, -1, 1)
        # Convert the audio to 16-bit PCM
        audio_integer = (audio * 32767).astype(np.int16)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_integer.tobytes())
