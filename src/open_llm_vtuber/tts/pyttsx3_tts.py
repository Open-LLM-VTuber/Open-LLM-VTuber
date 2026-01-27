import os
import sys
import threading

import pyttsx3
from loguru import logger

from .tts_interface import TTSInterface

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)


# using https://github.com/thevickypedia/py3-tts because pyttsx3 is unmaintained and not working


class TTSEngine(TTSInterface):
    def __init__(self):
        self.engine = pyttsx3.init()
        self.temp_audio_file = "temp"
        self.file_extension = "aiff"
        self.new_audio_dir = "cache"
        self.lock = threading.Lock()

        if not os.path.exists(self.new_audio_dir):
            os.makedirs(self.new_audio_dir)

    #! This method (pyttsx3) is not thread safe. It will blow if it's called from multiple threads at the same time.
    def generate_audio(self, text, file_name_no_ext=None):
        logger.debug(f"Start Generating {file_name_no_ext}")
        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)

        with self.lock:
            self.engine.save_to_file(text=text, filename=file_name)
            self.engine.runAndWait()
        logger.info(f"Finished Generating {file_name}")
        return file_name


if __name__ == "__main__":
    TTSEngine = TTSEngine()
    TTSEngine.generate_audio(
        "Hello, this is a test. But this is not a test. You are screwed bro. You only live once. YOLO."
    )

    def worker(engine, text, index):
        file_name = f"audio_{index}"
        engine.generate_audio(text, file_name)

    texts = [
        "Hello, this is a test.",
        "This is another test.",
        "Yet another test sentence.",
        "Testing multithreading.",
        "Final test sentence.",
    ]

    threads = []
    for i, text in enumerate(texts):
        t = threading.Thread(target=worker, args=(TTSEngine, text, i))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
