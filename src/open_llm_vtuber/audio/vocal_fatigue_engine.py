# src/open_llm_vtuber/audio/vocal_fatigue_engine.py
"""
Zero-Cost Real-Time Vocal Fatigue & Hydration Dynamics Engine.

Simulates biological vocal fold strain based on accumulated phonation time,
vocal intensity (RMS energy), and pitch excursion. As fatigue accumulates,
it dynamically modulates acoustic filters (spectral tilt, jitter, breathiness)
and prompts behavioral cues (clearing throat, sipping water) until reset
by chat '!hydrate' interactions or stream breaks.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger


@dataclass
class VocalState:
    fatigue_level: float = 0.0          # 0.0 (fresh) to 1.0 (exhausted/strained)
    total_spoken_seconds: float = 0.0
    accumulated_strain: float = 0.0
    hydration_level: float = 1.0        # 1.0 (hydrated) to 0.0 (dehydrated)
    last_sip_timestamp: float = field(default_factory=time.time)
    sip_count: int = 0
    is_hoarse: bool = False
    status_tag: str = "Pristine"


class VocalFatigueEngine:
    """
    Biological Vocal Fold Fatigue & Hydration Recovery Simulation.
    """

    def __init__(
        self,
        fatigue_rate_per_sec: float = 0.0008,   # Reaches ~0.5 after ~10 min continuous speech
        recovery_rate_idle: float = 0.0002,     # Passive recovery per idle second
        hydrate_recovery_amount: float = 0.35,  # Recovery per !hydrate command
        strain_threshold_hoarse: float = 0.70,  # Level where hoarseness kicks in
    ):
        self.fatigue_rate_per_sec = fatigue_rate_per_sec
        self.recovery_rate_idle = recovery_rate_idle
        self.hydrate_recovery_amount = hydrate_recovery_amount
        self.strain_threshold_hoarse = strain_threshold_hoarse
        self.state = VocalState()
        self.last_update_ts = time.perf_counter()

    def update_idle_time(self, idle_seconds: Optional[float] = None) -> float:
        """
        Passively recovers vocal stamina during silence / pauses.
        """
        now = time.perf_counter()
        if idle_seconds is None:
            idle_seconds = max(0.0, now - self.last_update_ts)
        self.last_update_ts = now

        recovered = idle_seconds * self.recovery_rate_idle
        self.state.fatigue_level = max(0.0, self.state.fatigue_level - recovered)
        self._update_status()
        return self.state.fatigue_level

    def register_utterance(
        self,
        duration_sec: float,
        intensity: float = 0.7,   # 0.0 - 1.0 (shouting = 1.0, whisper = 0.2)
        pitch_factor: float = 1.0 # 1.0 = normal, >1.3 = falsetto / scream
    ) -> Dict[str, Any]:
        """
        Registers speech phonation and updates vocal fatigue index.
        Higher intensity and high pitch exponentially increase vocal cord strain.
        """
        self.update_idle_time(0.0)

        # Non-linear vocal strain formula: Strain = duration * (intensity^1.5) * (pitch_factor^1.2)
        strain_increment = (
            duration_sec 
            * self.fatigue_rate_per_sec 
            * (intensity ** 1.5) 
            * (pitch_factor ** 1.2)
        )

        self.state.total_spoken_seconds += duration_sec
        self.state.accumulated_strain += strain_increment
        self.state.fatigue_level = min(1.0, self.state.fatigue_level + strain_increment)

        # Dehydration slowly increases with speech duration
        dehydration_delta = duration_sec * 0.0003
        self.state.hydration_level = max(0.0, self.state.hydration_level - dehydration_delta)

        self._update_status()

        return {
            "fatigue_level": round(self.state.fatigue_level, 4),
            "hydration_level": round(self.state.hydration_level, 4),
            "is_hoarse": self.state.is_hoarse,
            "status_tag": self.state.status_tag,
            "suggested_action": self.get_vocal_suggestion(),
        }

    def trigger_hydrate(self, username: str = "Chat") -> Dict[str, Any]:
        """
        Chat command '!hydrate' or water donation trigger. Restores vocal hydration
        and significantly lowers fatigue.
        """
        self.state.sip_count += 1
        self.state.last_sip_timestamp = time.time()
        self.state.hydration_level = min(1.0, self.state.hydration_level + 0.5)
        self.state.fatigue_level = max(0.0, self.state.fatigue_level - self.hydrate_recovery_amount)
        self._update_status()

        logger.info(f"[VocalFatigue] Hydrated by {username}! New fatigue: {self.state.fatigue_level:.2f}")

        return {
            "event": "hydrate",
            "initiated_by": username,
            "current_fatigue": round(self.state.fatigue_level, 3),
            "hydration_level": round(self.state.hydration_level, 3),
            "sfx_cue": "water_sip.wav",
            "live2d_expression": "ExpressionDrinkWater",
            "thank_prompt": f"Take a refreshing sip of water and thank {username} for reminding you to hydrate!"
        }

    def _update_status(self):
        f = self.state.fatigue_level
        self.state.is_hoarse = (f >= self.strain_threshold_hoarse)

        if f < 0.25:
            self.state.status_tag = "Pristine"
        elif f < 0.50:
            self.state.status_tag = "Warm"
        elif f < 0.70:
            self.state.status_tag = "Fatigued"
        elif f < 0.85:
            self.state.status_tag = "Hoarse"
        else:
            self.state.status_tag = "Strained_Critical"

    def get_vocal_suggestion(self) -> Optional[str]:
        """Returns prompt guidance or audio cue depending on vocal state."""
        if self.state.fatigue_level >= 0.85:
            return "Clear throat softly, mention voice feeling raspy, take deep breath."
        elif self.state.fatigue_level >= 0.70:
            return "Add a subtle breathy sigh at the end of sentence."
        return None

    def get_audio_filter_params(self) -> Dict[str, float]:
        """
        Returns parameters for dynamic real-time DSP filters (e.g. high-pass rolloff, breathy noise injection)
        corresponding to physical vocal fold fatigue.
        """
        f = self.state.fatigue_level
        return {
            "spectral_tilt_db": round(-3.0 * f, 2),        # High frequencies slightly dampened
            "breathiness_gain": round(0.15 * f, 3),         # Subtle aspiration noise
            "pitch_jitter_cents": round(4.0 * f, 2),        # Subtle vocal cord tremor under fatigue
        }


if __name__ == "__main__":
    engine = VocalFatigueEngine()
    print("Initial Vocal State:", engine.state)

    # Simulate 5 minutes of intense high-energy streaming speech
    for _ in range(10):
        res = engine.register_utterance(duration_sec=30.0, intensity=0.9, pitch_factor=1.2)
    print("After 300s Intense Speech:", res)
    print("Audio DSP Filter params:", engine.get_audio_filter_params())

    # Chat triggers hydrate
    hydrate_res = engine.trigger_hydrate(username="TwitchKitten42")
    print("Hydrate Result:", hydrate_res)
