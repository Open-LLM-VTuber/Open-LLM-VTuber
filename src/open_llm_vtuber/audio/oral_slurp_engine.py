# src/open_llm_vtuber/audio/oral_slurp_engine.py
"""
Oral Kinematics & Procedural Slurp ASMR Engine
Generates multi-phase oral kinematics (jaw grinding, pursing, tongue protrusion)
and real-time procedural wet suction/gulp audio synthesis for eating & beverage streams.
"""

import time
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import numpy as np


@dataclass
class OralKeyframe:
    timestamp_ms: float
    param_mouth_open_y: float
    param_mouth_form: float
    param_tongue: float
    param_cheek: float
    param_angle_x: float
    param_angle_y: float
    phase: str


class OralKinematicsSlurpEngine:
    """
    Simulates high-fidelity oral kinematics and procedural acoustic suction
    for ramen, boba, tea, soup, or snack ASMR moments.
    """

    def __init__(self, sample_rate: int = 24000):
        self.sample_rate = sample_rate
        logger.info(f"OralKinematicsSlurpEngine initialized at {sample_rate}Hz.")

    def generate_slurp_sequence(
        self,
        duration_ms: float = 1800.0,
        intensity: float = 1.0,
        item_type: str = "ramen_noodles"
    ) -> Dict[str, Any]:
        """
        Synthesizes both procedural audio waveform and Live2D oral kinematic keyframe trajectory.
        
        Phases:
        1. APPROACH (0% - 20%): Mouth opens wide, head tips downward toward bowl/cup.
        2. SUCTION / SLURP (20% - 70%): Lips purse, mouth vibrates with hydrodynamic suction, tongue activates.
        3. GULP / SWALLOW (70% - 85%): Mouth snaps shut, cheeks momentarily bulge, throat swallows.
        4. SATISFACTION (85% - 100%): Smile morphs in, eyes crescent squint, gentle breath release.
        """
        t0 = time.perf_counter()
        intensity = max(0.2, min(2.0, intensity))
        fps = 60
        total_frames = int(duration_ms / 1000.0 * fps)
        keyframes: List[OralKeyframe] = []

        t_approach = 0.20 * duration_ms
        t_slurp_end = 0.70 * duration_ms
        t_swallow_end = 0.85 * duration_ms

        for i in range(total_frames):
            cur_ms = (i / fps) * 1000.0
            
            if cur_ms < t_approach:
                # Approach phase: open mouth, head tilts down
                p = cur_ms / t_approach
                open_y = 0.1 + 0.7 * math.sin(p * math.pi * 0.5)
                form = 0.0
                tongue = 0.1 * p
                cheek = 0.0
                angle_x = -2.0 * p
                angle_y = -12.0 * p
                phase = "approach"

            elif cur_ms < t_slurp_end:
                # Slurp phase: pursed lips, dynamic vibrating mouth, head suction bobbing
                p = (cur_ms - t_approach) / (t_slurp_end - t_approach)
                # Rapid micro-tremor representing fluid intake modulation (18-24 Hz)
                vibration = 0.12 * math.sin(2 * math.pi * 22.0 * (cur_ms / 1000.0))
                open_y = max(0.15, 0.45 + vibration * intensity)
                form = -0.85  # tight purse 'O' shape
                tongue = 0.6 + 0.3 * math.sin(2 * math.pi * 8.0 * (cur_ms / 1000.0))
                cheek = 0.25 * math.sin(p * math.pi)
                angle_x = 1.5 * math.sin(2 * math.pi * 4.0 * (cur_ms / 1000.0))
                angle_y = -12.0 + 3.0 * math.sin(2 * math.pi * 3.0 * (cur_ms / 1000.0))
                phase = "slurp"

            elif cur_ms < t_swallow_end:
                # Swallow phase: mouth snaps closed, cheeks contract
                p = (cur_ms - t_slurp_end) / (t_swallow_end - t_slurp_end)
                open_y = max(0.0, 0.4 * (1.0 - p))
                form = 0.1 * p
                tongue = max(0.0, 0.6 * (1.0 - p))
                cheek = 0.4 * math.sin(p * math.pi)  # cheek puff on swallow
                angle_x = 0.0
                angle_y = -8.0 + 8.0 * p
                phase = "swallow"

            else:
                # Satisfaction phase: happy crescent eyes, warm smile
                p = (cur_ms - t_swallow_end) / (duration_ms - t_swallow_end)
                open_y = 0.15 * math.sin(p * math.pi * 0.5)
                form = 0.9 * p  # broad happy smile
                tongue = 0.0
                cheek = 0.5 * p  # blushing cheeks
                angle_x = 1.0 * p
                angle_y = 2.0 * p
                phase = "satisfaction"

            keyframes.append(
                OralKeyframe(
                    timestamp_ms=round(cur_ms, 2),
                    param_mouth_open_y=round(open_y, 3),
                    param_mouth_form=round(form, 3),
                    param_tongue=round(tongue, 3),
                    param_cheek=round(cheek, 3),
                    param_angle_x=round(angle_x, 2),
                    param_angle_y=round(angle_y, 2),
                    phase=phase
                )
            )

        # Procedural Audio Synthesis
        audio_samples = self._synthesize_procedural_slurp(duration_ms, intensity, item_type)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "duration_ms": duration_ms,
            "item_type": item_type,
            "intensity": intensity,
            "keyframe_count": len(keyframes),
            "keyframes": keyframes,
            "audio_samples_count": len(audio_samples),
            "audio_waveform": audio_samples,
            "synthesis_latency_ms": round(elapsed_ms, 2)
        }

    def _synthesize_procedural_slurp(
        self,
        duration_ms: float,
        intensity: float,
        item_type: str
    ) -> np.ndarray:
        """
        Numpy zero-cost procedural synthesis of suction slurping and gulp acoustics.
        """
        total_samples = int(self.sample_rate * (duration_ms / 1000.0))
        t = np.linspace(0, duration_ms / 1000.0, total_samples, endpoint=False)
        output = np.zeros(total_samples, dtype=np.float32)

        slurp_start_s = 0.20 * (duration_ms / 1000.0)
        slurp_end_s = 0.70 * (duration_ms / 1000.0)
        gulp_start_s = 0.72 * (duration_ms / 1000.0)
        gulp_end_s = 0.84 * (duration_ms / 1000.0)

        # 1. Slurp Suction Noise: Shaped resonant turbulent aspiration
        slurp_mask = (t >= slurp_start_s) & (t < slurp_end_s)
        n_slurp = np.sum(slurp_mask)
        if n_slurp > 0:
            t_sub = t[slurp_mask] - slurp_start_s
            p_sub = t_sub / (slurp_end_s - slurp_start_s)
            
            # Formant resonance sweep (frequency rises as tube shortens/tightens)
            sweep_f = 600.0 + 1400.0 * (p_sub ** 1.5)
            suction_carrier = np.sin(2 * np.pi * sweep_f * t_sub)
            
            # Bubble turbulence (amplitude modulation + noise bursts)
            noise = np.random.normal(0, 0.4, n_slurp).astype(np.float32)
            amplitude_envelope = np.sin(np.pi * p_sub) ** 0.8
            flutter = 0.5 + 0.5 * np.sin(2 * np.pi * 24.0 * t_sub)
            
            slurp_component = (suction_carrier * 0.4 + noise * 0.6) * amplitude_envelope * flutter * intensity
            output[slurp_mask] += slurp_component

        # 2. Bubble popping bursts (cavitation clicks)
        num_clicks = int(14 * intensity)
        for _ in range(num_clicks):
            click_time = slurp_start_s + np.random.uniform(0, slurp_end_s - slurp_start_s)
            idx = int(click_time * self.sample_rate)
            click_len = int(0.008 * self.sample_rate)
            if idx + click_len < total_samples:
                click_t = np.linspace(0, 0.008, click_len)
                click_wave = np.sin(2 * np.pi * 2800.0 * click_t) * np.exp(-click_t / 0.002)
                output[idx:idx + click_len] += click_wave * 0.15 * intensity

        # 3. Gulp sound (low frequency damped resonant pop)
        gulp_mask = (t >= gulp_start_s) & (t < gulp_end_s)
        n_gulp = np.sum(gulp_mask)
        if n_gulp > 0:
            t_gulp = t[gulp_mask] - gulp_start_s
            gulp_freq = 135.0
            gulp_wave = np.sin(2 * np.pi * gulp_freq * t_gulp) * np.exp(-t_gulp / 0.035)
            output[gulp_mask] += gulp_wave * 0.55 * intensity

        # Soft clip to [-0.95, 0.95]
        output = np.tanh(output * 1.2) * 0.95
        return output
