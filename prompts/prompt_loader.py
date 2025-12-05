import os
import chardet
from loguru import logger

current_dir = os.path.dirname(os.path.abspath(__file__))

PROMPT_DIR = current_dir
PERSONA_PROMPT_DIR = os.path.join(PROMPT_DIR, "persona")
UTIL_PROMPT_DIR = os.path.join(PROMPT_DIR, "utils")


def _load_file_content(file_path: str) -> str:
    """
    Load the content of a file with robust encoding handling.

    Args:
        file_path: Path to the file to load

    Returns:
        str: Content of the file

    Raises:
        FileNotFoundError: If the file doesn't exist
        UnicodeError: If the file cannot be decoded with any attempted encoding
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Try common encodings first
    encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "ascii"]

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as file:
                return file.read()
        except UnicodeDecodeError:
            continue

    # If all common encodings fail, try to detect encoding
    try:
        with open(file_path, "rb") as file:
            raw_data = file.read()
        detected = chardet.detect(raw_data)
        detected_encoding = detected["encoding"]

        if detected_encoding:
            try:
                return raw_data.decode(detected_encoding)
            except UnicodeDecodeError:
                pass
    except Exception as e:
        logger.error(f"Error detecting encoding for {file_path}: {e}")

    raise UnicodeError(f"Failed to decode {file_path} with any encoding")


def load_persona(persona_name: str) -> str:
    """Load the content of a specific persona prompt file."""
    persona_file_path = os.path.join(PERSONA_PROMPT_DIR, f"{persona_name}.txt")
    try:
        return _load_file_content(persona_file_path)
    except Exception as e:
        logger.error(f"Error loading persona {persona_name}: {e}")
        raise


def load_util(util_name: str) -> str:
    """Load the content of a specific utility prompt file."""
    util_file_path = os.path.join(UTIL_PROMPT_DIR, f"{util_name}.txt")
    try:
        return _load_file_content(util_file_path)
    except Exception as e:
        logger.error(f"Error loading util {util_name}: {e}")
        raise
