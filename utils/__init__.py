# This file makes the 'utils' directory a Python package.

from .email_handler import send_email
from .audio_utils import save_audio_to_wav
from .web_accessor import WebAccessor

__all__ = [
    'send_email',
    'save_audio_to_wav',
    'WebAccessor',
]
