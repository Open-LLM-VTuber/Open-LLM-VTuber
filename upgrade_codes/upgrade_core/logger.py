import os
import sys
import logging
from datetime import datetime
def configure_logging():
    if not os.path.exists("logs"):
        os.makedirs("logs")
    log_filename = f"./logs/upgrade_{datetime.now().strftime('%Y-%m-%d-%H-%M')}.log"
    logger = logging.getLogger("upgrade")
    logger.setLevel(logging.DEBUG)

    # File handler (no colors)
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Colored console handler
    class ColoredFormatter(logging.Formatter):
        COLORS = {
            logging.DEBUG: "\033[96m",  # cyan
            logging.INFO: "\033[92m",  # green
            logging.WARNING: "\033[93m",  # yellow
            logging.ERROR: "\033[91m",  # red
            logging.CRITICAL: "\033[95m",  # magenta
        }
        RESET = "\033[0m"

        def format(self, record):
            color = self.COLORS.get(record.levelno, self.RESET)
            message = super().format(record)
            return f"{color}{message}{self.RESET}"

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    stream_formatter = ColoredFormatter("[%(levelname)s] %(message)s")
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    return logger
