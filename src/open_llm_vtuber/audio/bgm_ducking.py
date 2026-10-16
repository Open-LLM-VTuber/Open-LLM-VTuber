"""
Adaptive Dynamic BGM & Sidechain Audio Ducking Controller.
Manages stream background audio and applies smooth attenuation when the avatar speaks.
"""
import time
from typing import Optional
from loguru import logger


class DynamicBGMDucker:
    """
    Simulates / manages dynamic audio ducking parameters for stream BGM:
    Normal Gain: -12 dB (0.25)
    Ducked Gain: -26 dB (0.05)
    Attack Time: 45 ms
    Release Time: 350 ms
    """
    def __init__(self, normal_gain_db: float = -12.0, ducked_gain_db: float = -26.0):
        self.normal_gain_db = normal_gain_db
        self.ducked_gain_db = ducked_gain_db
        self.is_ducked = False
        self.last_duck_time = 0.0

    def on_speech_start(self) -> dict:
        """Called the instant the TTS starts streaming audio."""
        self.is_ducked = True
        self.last_duck_time = time.time()
        logger.info(f"Audio Ducking: BGM ducked to {self.ducked_gain_db} dB (45ms attack)")
        return {
            "action": "duck",
            "target_gain_db": self.ducked_gain_db,
            "ramp_ms": 45
        }

    def on_speech_end(self) -> dict:
        """Called the instant speech finishes playback."""
        self.is_ducked = False
        logger.info(f"Audio Ducking: BGM restoring to {self.normal_gain_db} dB (350ms release)")
        return {
            "action": "restore",
            "target_gain_db": self.normal_gain_db,
            "ramp_ms": 350
        }
