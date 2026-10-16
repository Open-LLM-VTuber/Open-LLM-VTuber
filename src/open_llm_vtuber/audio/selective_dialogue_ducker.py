# src/open_llm_vtuber/audio/selective_dialogue_ducker.py
"""
Selective Game Dialogue Ducker & NPC Vocal Isolator
Utilizes Mid-Side (M/S) stereo decomposition and vocal formant bandpass filtering
to duck game BGM and ambient sound while cleanly preserving in-game NPC speech lines.
"""

import time
from typing import Dict, Any, Tuple
from dataclasses import dataclass
from loguru import logger
import numpy as np
from scipy.signal import butter, lfilter


@dataclass
class DuckingProfile:
    bgm_attenuation_db: float = -14.0
    side_attenuation_db: float = -16.0
    npc_speech_boost_db: float = 0.5
    speech_band_low_hz: float = 300.0
    speech_band_high_hz: float = 3400.0


class SelectiveGameDialogueDucker:
    """
    Real-time Mid-Side stereo audio processor that intelligently attenuates game background
    music and wide stereophonic sound effects while preserving centered NPC speech formants.
    """

    def __init__(self, sample_rate: int = 48000, profile: DuckingProfile = None):
        self.sample_rate = sample_rate
        self.profile = profile or DuckingProfile()

        # Design 2nd-order Butterworth bandpass filter for human speech formants (300Hz - 3400Hz)
        nyquist = sample_rate * 0.5
        low = self.profile.speech_band_low_hz / nyquist
        high = min(0.95, self.profile.speech_band_high_hz / nyquist)
        self.b_speech, self.a_speech = butter(2, [low, high], btype="bandpass")
        logger.info(f"SelectiveGameDialogueDucker initialized at {sample_rate}Hz.")

    def process_stereo_stream(
        self,
        left_channel: np.ndarray,
        right_channel: np.ndarray,
        vtuber_is_speaking: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Processes interleaved or split stereo game audio.
        Returns processed (L, R) and diagnostic metrics.
        """
        t0 = time.perf_counter()
        n_samples = len(left_channel)

        # 1. Mid-Side (M/S) Stereo Decomposition
        # Mid (M) = Center channel (NPC vocals, center sound)
        # Side (S) = Stereo difference (reverb, wide BGM, ambient stereo field)
        mid = 0.5 * (left_channel + right_channel)
        side = 0.5 * (left_channel - right_channel)

        # 2. Extract Center Speech Formants
        mid_speech = lfilter(self.b_speech, self.a_speech, mid)
        mid_residual = mid - mid_speech  # low sub-bass and ultra-high treble in center

        # Detect NPC Voice Activity in center channel
        speech_rms = float(np.sqrt(np.mean(mid_speech ** 2) + 1e-9))
        residual_rms = float(np.sqrt(np.mean(mid_residual ** 2) + 1e-9))
        npc_speech_ratio = speech_rms / (residual_rms + 1e-6)
        npc_detected = npc_speech_ratio > 1.2 and speech_rms > 0.02

        if vtuber_is_speaking:
            # Duck BGM & Side Ambience aggressively
            gain_side = 10.0 ** (self.profile.side_attenuation_db / 20.0)
            gain_residual = 10.0 ** (self.profile.bgm_attenuation_db / 20.0)
            # Preserve or slightly highlight NPC vocals
            gain_speech = 10.0 ** (self.profile.npc_speech_boost_db / 20.0)
        else:
            # Transparency mode: no ducking
            gain_side = 1.0
            gain_residual = 1.0
            gain_speech = 1.0

        # 3. Reconstruct Mid and Side
        proc_mid = (mid_speech * gain_speech) + (mid_residual * gain_residual)
        proc_side = side * gain_side

        # 4. Reconstruct Left / Right Stereo from M/S
        # L = Mid + Side, R = Mid - Side
        proc_left = proc_mid + proc_side
        proc_right = proc_mid - proc_side

        # Soft clip to [-1.0, 1.0]
        proc_left = np.clip(proc_left, -1.0, 1.0).astype(np.float32)
        proc_right = np.clip(proc_right, -1.0, 1.0).astype(np.float32)

        elapsed = (time.perf_counter() - t0) * 1000.0
        metrics = {
            "elapsed_ms": round(elapsed, 2),
            "vtuber_speaking": vtuber_is_speaking,
            "npc_speech_detected": npc_detected,
            "npc_speech_ratio": round(npc_speech_ratio, 2),
            "speech_rms": round(speech_rms, 4),
            "side_gain_applied": round(gain_side, 3)
        }

        return proc_left, proc_right, metrics
