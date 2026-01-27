import abc
import numpy as np
import asyncio


class ASRInterface(metaclass=abc.ABCMeta):
    SAMPLE_RATE = 16000
    NUM_CHANNELS = 1
    SAMPLE_WIDTH = 2

    async def async_transcribe_np(self, audio: np.ndarray) -> str:
        """Asynchronously transcribe speech audio in numpy array format.

        By default, this runs the synchronous transcribe_np in a coroutine.
        Subclasses can override this method to provide true async implementation.

        Args:
            audio: The numpy array of the audio data to transcribe.

        Returns:
            str: The transcription result.
        """
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        return await asyncio.to_thread(self.transcribe_np, audio)

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
