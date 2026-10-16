# src/open_llm_vtuber/narrative/hardcore_trauma_engine.py
"""
Multi-Stream Hardcore Trauma & Emotional Resilience State Machine.

Persists psychological consequences of catastrophic stream disasters
(e.g., losing a 100-hour hardcore Minecraft world or demoting from Diamond rank)
across multiple consecutive broadcast days:
- Phase 1 (Depression & Grief): Cold blue color LUT, slowed speech rate (0.88x), sullen tone
- Phase 2 (Spite & Denial): High-contrast fiery LUT, snappy aggressive sarcasm, blaming RNG
- Phase 3 (Heroic Redemption): Warm golden aura, renewed determination, Nether revenge arc
Maintains persistent JSON state in data/trauma_state.json with zero runtime overhead.
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from loguru import logger


@dataclass
class TraumaStreamProfile:
    has_active_trauma: bool
    incident: str
    phase_number: int       # 0: Normal, 1: Grief, 2: Spite, 3: Redemption
    phase_label: str        # "NORMAL", "GRIEF_DEPRESSION", "SPITE_DENIAL", "HEROIC_REDEMPTION"
    lut_color_filter: str   # "neutral", "cold_desaturated_blue", "high_contrast_fiery", "warm_golden_sun"
    speech_rate_multiplier: float  # 0.88x, 1.12x, 1.0x
    conversational_directive: str


class HardcoreTraumaEngine:
    """
    Persistent Multi-Session Psychological Disaster Tracker.
    """

    def __init__(self, state_path: str = "data/trauma_state.json"):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_or_init()

    def _load_or_init(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading trauma state ({e}). Rebuilding fresh state.")

        initial = {
            "has_active_trauma": False,
            "incident": "None",
            "current_phase": 0,
            "streams_in_phase": 0,
        }
        self._save(initial)
        return initial

    def _save(self, state: Dict[str, Any]):
        self.state = state
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def trigger_catastrophic_loss(self, incident_description: str) -> TraumaStreamProfile:
        """
        Called when the avatar experiences an existential loss (e.g. falling into lava with max gear).
        """
        self.state = {
            "has_active_trauma": True,
            "incident": incident_description,
            "current_phase": 1,
            "streams_in_phase": 0,
        }
        self._save(self.state)
        logger.warning(f"[HardcoreTrauma] CATASTROPHIC LOSS LOGGED: \"{incident_description}\" -> Phase 1 Active")
        return self.get_current_stream_profile()

    def advance_to_next_stream_session(self) -> TraumaStreamProfile:
        """
        Advances the emotional healing cycle after a stream concludes.
        Each phase lasts 1-2 sessions before transitioning to the next stage.
        """
        if not self.state.get("has_active_trauma"):
            return self.get_current_stream_profile()

        self.state["streams_in_phase"] += 1

        # Transition to next stage after 2 sessions
        if self.state["streams_in_phase"] >= 2:
            self.state["current_phase"] += 1
            self.state["streams_in_phase"] = 0

        # Trauma resolved after Phase 3
        if self.state["current_phase"] > 3:
            self.state["has_active_trauma"] = False
            self.state["current_phase"] = 0
            logger.info("[HardcoreTrauma] Emotional trauma cycle fully resolved! Returned to normal baseline.")

        self._save(self.state)
        return self.get_current_stream_profile()

    def get_current_stream_profile(self) -> TraumaStreamProfile:
        """
        Generates visual LUT shader directives and persona behavioral prompts for today's stream.
        """
        if not self.state.get("has_active_trauma") or self.state.get("current_phase") == 0:
            return TraumaStreamProfile(
                has_active_trauma=False,
                incident="None",
                phase_number=0,
                phase_label="NORMAL",
                lut_color_filter="neutral",
                speech_rate_multiplier=1.0,
                conversational_directive="Standard cheerful, engaging streaming persona.",
            )

        phase = self.state["current_phase"]
        incident = self.state["incident"]

        if phase == 1:
            return TraumaStreamProfile(
                has_active_trauma=True,
                incident=incident,
                phase_number=1,
                phase_label="GRIEF_DEPRESSION",
                lut_color_filter="cold_desaturated_blue",
                speech_rate_multiplier=0.88,
                conversational_directive=(
                    f"You are still devastated and heartbroken after: '{incident}'. "
                    f"Speak in a soft, subdued, melancholic voice with quiet sighs. "
                    f"If chat brings it up, deflect sadly: 'Please chat... I don't want to talk about the lava...'"
                ),
            )
        elif phase == 2:
            return TraumaStreamProfile(
                has_active_trauma=True,
                incident=incident,
                phase_number=2,
                phase_label="SPITE_DENIAL",
                lut_color_filter="high_contrast_fiery",
                speech_rate_multiplier=1.12,
                conversational_directive=(
                    f"You are furious and in bitter denial about: '{incident}'. "
                    f"Speak with snappy, aggressive sarcasm. Blame server lag, game bugs, and RNG. "
                    f"Refuse to admit it was your fault: 'The hitbox was literally broken! Anyone would have died!'"
                ),
            )
        else:  # Phase 3
            return TraumaStreamProfile(
                has_active_trauma=True,
                incident=incident,
                phase_number=3,
                phase_label="HEROIC_REDEMPTION",
                lut_color_filter="warm_golden_sun",
                speech_rate_multiplier=1.0,
                conversational_directive=(
                    f"You have risen from the ashes after: '{incident}'. "
                    f"Speak with blazing, heroic determination! You are embarking on the ultimate comeback stream "
                    f"to reclaim everything you lost and prove your greatness to chat!"
                ),
            )


if __name__ == "__main__":
    trauma = HardcoreTraumaEngine(state_path="data/test_trauma_state.json")
    prof1 = trauma.trigger_catastrophic_loss("Lost 150-hour hardcore world to a creeper while checking chat.")
    print("Phase 1 Profile:", prof1.phase_label, "| Speed:", prof1.speech_rate_multiplier)

    # Advance through healing stages
    trauma.advance_to_next_stream_session()
    prof2 = trauma.advance_to_next_stream_session()
    print("Phase 2 Profile:", prof2.phase_label, "| LUT:", prof2.lut_color_filter)

    trauma.advance_to_next_stream_session()
    prof3 = trauma.advance_to_next_stream_session()
    print("Phase 3 Profile:", prof3.phase_label, "| Directive:\n", prof3.conversational_directive)
