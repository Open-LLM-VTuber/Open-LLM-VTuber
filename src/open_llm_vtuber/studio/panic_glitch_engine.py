# src/open_llm_vtuber/studio/panic_glitch_engine.py
"""
Panic Glitch & Horror Audio/Visual Engine
Produces jumpscare audio distortion (analog overdrive clipping, sub-bass terror rumble),
Live2D high-frequency panic micro-tremors (14Hz shudders), and OBS chromatic aberration glitch triggers.
"""

import time
import math
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger
import numpy as np


@dataclass
class GlitchVisualState:
    chromatic_aberration_px: float
    scanline_intensity: float
    rgb_split_angle: float
    frame_freeze_ms: int
    camera_shake_px: float
    color_inversion: bool


@dataclass
class PanicMotionState:
    param_angle_x: float
    param_angle_y: float
    param_angle_z: float
    param_eye_open: float
    param_eye_ball_x: float
    param_eye_ball_y: float
    param_mouth_open_y: float


class PanicGlitchHorrorEngine:
    """
    Real-time acoustic and kinematic distortion engine for horror gaming and jumpscare moments.
    """

    def __init__(self, sample_rate: int = 24000):
        self.sample_rate = sample_rate
        self.panic_level = 0.0  # 0.0 (Calm) to 1.0 (Maximum Terror)
        self.last_jumpscare_ts = 0.0
        logger.info("PanicGlitchHorrorEngine initialized.")

    def trigger_jumpscare(self, intensity: float = 1.0) -> Dict[str, Any]:
        """
        Instantly kicks the engine into maximum panic shock state.
        """
        self.panic_level = min(1.0, max(0.2, intensity))
        self.last_jumpscare_ts = time.time()
        
        visual = self.compute_visual_glitch(self.panic_level)
        motion = self.compute_panic_kinematics(self.panic_level, time_sec=0.0)

        logger.warning(f"JUMPSCARE TRIGGERED! Panic Level: {self.panic_level:.2f}")
        return {
            "status": "JUMPSCARE_ACTIVE",
            "panic_level": self.panic_level,
            "visual_fx": visual,
            "initial_kinematics": motion,
            "obs_filter_directive": {
                "filter_name": "Chromatic_Aberration_Shock",
                "enabled": True,
                "duration_ms": int(1200 * self.panic_level)
            }
        }

    def compute_visual_glitch(self, intensity: float) -> GlitchVisualState:
        """Calculates OBS shader and CSS glitch parameters."""
        return GlitchVisualState(
            chromatic_aberration_px=round(18.0 * intensity, 2),
            scanline_intensity=round(0.85 * intensity, 2),
            rgb_split_angle=round(45.0 + 90.0 * intensity, 1),
            frame_freeze_ms=int(60 * intensity),
            camera_shake_px=round(24.0 * intensity, 1),
            color_inversion=(intensity > 0.85)
        )

    def compute_panic_kinematics(self, intensity: float, time_sec: float) -> PanicMotionState:
        """
        Computes 14Hz shudder oscillation on avatar head/body angles and dilated eye movements.
        """
        # 14Hz high-frequency panic micro-tremor
        tremor_14hz = math.sin(2 * math.pi * 14.0 * time_sec)
        jitter = math.cos(2 * math.pi * 19.5 * time_sec)

        angle_x = (tremor_14hz * 3.5 + jitter * 2.0) * intensity
        angle_y = (math.cos(2 * math.pi * 11.0 * time_sec) * 4.0) * intensity
        angle_z = (tremor_14hz * 5.0) * intensity

        # Eyes widen in shock (pupil dilation simulation)
        eye_open = min(1.2, 1.0 + 0.2 * intensity)
        # Rapid frantic eye saccades
        eye_x = 0.4 * math.sin(2 * math.pi * 7.0 * time_sec) * intensity
        eye_y = 0.3 * math.cos(2 * math.pi * 8.5 * time_sec) * intensity
        mouth_open = min(1.0, 0.3 + 0.6 * intensity)

        return PanicMotionState(
            param_angle_x=round(angle_x, 2),
            param_angle_y=round(angle_y, 2),
            param_angle_z=round(angle_z, 2),
            param_eye_open=round(eye_open, 2),
            param_eye_ball_x=round(eye_x, 2),
            param_eye_ball_y=round(eye_y, 2),
            param_mouth_open_y=round(mouth_open, 2)
        )

    def apply_horror_audio_overdrive(
        self,
        pcm_audio: np.ndarray,
        intensity: float = 0.8
    ) -> np.ndarray:
        """
        Applies non-linear analog preamp soft overdrive (tanh saturation)
        and mixes in a 42 Hz infrasonic terror rumble and acoustic high screech.
        """
        t0 = time.perf_counter()
        n_samples = len(pcm_audio)
        if n_samples == 0:
            return pcm_audio

        t = np.linspace(0, n_samples / self.sample_rate, n_samples, endpoint=False)

        # 1. Analog preamp boost & tanh saturation
        preamp_gain = 1.0 + (3.5 * intensity)
        saturated = np.tanh(pcm_audio * preamp_gain)

        # 2. Sub-bass panic rumble (42 Hz sine pulsating with irregular heartbeat rhythm)
        heartbeat_envelope = np.maximum(0.0, np.sin(2 * np.pi * 1.6 * t)) ** 4
        sub_rumble = np.sin(2 * np.pi * 42.0 * t) * heartbeat_envelope * 0.25 * intensity

        # 3. High-pitch acoustic tension whistle (3200 Hz dissonant harmonic)
        screech = np.sin(2 * np.pi * 3200.0 * t) * (0.04 * intensity)

        # Composite output with limiter
        output = saturated * 0.75 + sub_rumble + screech
        output = np.clip(output, -0.98, 0.98).astype(np.float32)

        elapsed = (time.perf_counter() - t0) * 1000.0
        logger.debug(f"Applied horror audio overdrive to {n_samples} samples in {elapsed:.2f}ms")
        return output
