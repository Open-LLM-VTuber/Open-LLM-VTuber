"""Path utilities."""

from pathlib import Path
from loguru import logger


def validate_file(file_path: str | Path, suffix: str = ".json") -> Path:
    """Check if the file path is valid.

    Args:
        file_path (str | Path): The path to the file.
        suffix (str): The expected file extension. Default is '.json'.

    Returns:
        Path: The absolute Path object of the file if valid.

    Raises:
        ValueError: If the file path is not valid with giving suffix.
    """
    file_path = Path(file_path).absolute()
    if file_path.exists() and file_path.is_file() and file_path.suffix == suffix:
        return file_path
    logger.error(f"File '{file_path}' not a valid '{suffix}' file.")
    raise ValueError(f"File '{file_path}' not a valid '{suffix}' file.")
