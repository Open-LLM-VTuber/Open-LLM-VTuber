import abc


class TranslateInterface(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def translate(self, text: str) -> str:
        """
        Translate the input text to the target language."""
        raise NotImplementedError
