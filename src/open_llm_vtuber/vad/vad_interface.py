from abc import ABC, abstractmethod


class VADInterface(ABC):
    @abstractmethod
    def detect_speech(self, audio_data: bytes):
        """
        Detect if there is voice activity in the audio data.
        :param audio_data: Input audio data
        :return: Returns a sequence of audio bytes containing human voice if voice activity is detected
        """
        pass
