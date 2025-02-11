# anyasfriend/components/interfaces/vad.py

from abc import ABC, abstractmethod


class VAD(ABC):
    @abstractmethod
    def detect_speech(self, audio_data: bytes):
        """
        检测音频数据中是否包含语音活动。
        :param audio_data: 输入的音频数据
        :return: 如果音频中有语音活动，则返回一串有人声的语音字节序列
        """
        pass
