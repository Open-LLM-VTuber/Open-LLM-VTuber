# src/open_llm_vtuber/narrative/dream_sequence_engine.py
"""
Procedural Surrealist Dream Sequence State Machine for AFK & Stream Intermissions.

When the stream enters a lull, intermission, or sleepathon phase, this engine manages
a multi-stage subconscious dream cycle (AWAKE -> DROWSY -> REM_DREAM -> LUCID_SURREAL -> WAKING_UP).
It modulates Live2D physical parameters (slow breathing, closed eyes, floating drift),
procedurally generates surreal sleep-talking narratives, and wakes up immediately upon
chat raids, donations, or sudden chatter surges.
"""

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger


class DreamState(str, Enum):
    AWAKE = "AWAKE"
    DROWSY = "DROWSY"
    REM_DREAM = "REM_DREAM"
    LUCID_SURREAL = "LUCID_SURREAL"
    WAKING_UP = "WAKING_UP"


@dataclass
class DreamManifest:
    current_state: DreamState = DreamState.AWAKE
    state_start_time: float = field(default_factory=time.time)
    dream_theme: str = "Neon Galaxy of Infinite Boba"
    sleep_talk_phrases: List[str] = field(default_factory=list)
    lucidity_level: float = 0.0  # 0.0 (deep unconscious) to 1.0 (lucid/aware)
    total_sleep_seconds: float = 0.0


class DreamSequenceEngine:
    """
    Subconscious Narrative & Visual Dream Simulator.
    """

    DREAM_THEMES = [
        "A cyberpunk ocean where jellyfish speak in Python code",
        "An endless cloud labyrinth of giant floating strawberries",
        "A retro 8-bit kingdom where all the townsfolk are sentient game controllers",
        "A celestial tea party held on the rings of Saturn with cosmic cats",
        "A zero-gravity arcade where high scores bend the laws of physics",
    ]

    SLEEP_TALK_TEMPLATES = [
        "...mumble... wait, don't eat that GPU... it's not candy...",
        "...zZz... five more minutes, chat... the ducks are compiling...",
        "...huh? no, the diamond sword goes in the toaster... obviously...",
        "...floating so high... the stars taste like blueberries...",
        "...who programmed this gravity? ...wheeee...",
    ]

    def __init__(self, idle_timeout_sec: float = 180.0):
        self.idle_timeout_sec = idle_timeout_sec
        self.manifest = DreamManifest()
        self.last_activity_time = time.time()

    def register_activity(self):
        """Notifies engine of chat or user interaction."""
        self.last_activity_time = time.time()
        if self.manifest.current_state in [DreamState.REM_DREAM, DreamState.LUCID_SURREAL, DreamState.DROWSY]:
            self.trigger_wake_up(reason="Chat activity resumed")

    def update_cycle(self, current_time: Optional[float] = None) -> Dict[str, Any]:
        """
        Advances the subconscious dream state machine.
        """
        now = current_time or time.time()
        idle_duration = now - self.last_activity_time

        prev_state = self.manifest.current_state

        if self.manifest.current_state == DreamState.AWAKE:
            if idle_duration > self.idle_timeout_sec:
                self.manifest.current_state = DreamState.DROWSY
                self.manifest.state_start_time = now
                logger.info("[DreamSequence] Streamer drifting into DROWSY state...")

        elif self.manifest.current_state == DreamState.DROWSY:
            if now - self.manifest.state_start_time > 30.0:  # 30s falling asleep
                self.manifest.current_state = DreamState.REM_DREAM
                self.manifest.state_start_time = now
                self.manifest.dream_theme = random.choice(self.DREAM_THEMES)
                logger.info(f"[DreamSequence] Entering REM_DREAM: {self.manifest.dream_theme}")

        elif self.manifest.current_state == DreamState.REM_DREAM:
            self.manifest.total_sleep_seconds += 1.0
            if now - self.manifest.state_start_time > 120.0:
                self.manifest.current_state = DreamState.LUCID_SURREAL
                self.manifest.state_start_time = now
                self.manifest.lucidity_level = 0.8
                logger.info("[DreamSequence] Entering LUCID_SURREAL state!")

        elif self.manifest.current_state == DreamState.WAKING_UP:
            if now - self.manifest.state_start_time > 10.0:
                self.manifest.current_state = DreamState.AWAKE
                self.manifest.state_start_time = now
                logger.info("[DreamSequence] Fully AWAKE and alert!")

        live2d_params = self._get_live2d_dream_parameters(now)

        # Check if sleep-talking occurs (10% chance every 15s in REM)
        sleep_talk = None
        if self.manifest.current_state in [DreamState.REM_DREAM, DreamState.LUCID_SURREAL]:
            if random.random() < 0.08:
                sleep_talk = random.choice(self.SLEEP_TALK_TEMPLATES)

        return {
            "state": self.manifest.current_state.value,
            "theme": self.manifest.dream_theme,
            "lucidity": round(self.manifest.lucidity_level, 2),
            "live2d_parameters": live2d_params,
            "sleep_talk": sleep_talk,
        }

    def trigger_wake_up(self, reason: str = "Raid") -> Dict[str, Any]:
        """Emergency wakeup trigger from chat raid, loud sound, or donation."""
        self.manifest.current_state = DreamState.WAKING_UP
        self.manifest.state_start_time = time.time()
        logger.info(f"[DreamSequence] WAKE UP triggered! Reason: {reason}")
        return {
            "event": "WAKE_UP",
            "reason": reason,
            "action": "Play startled gasp and rub eyes animation",
            "suggested_utterance": f"Woah! *gasps, blinks repeatedly* What happened?! Oh, chat! {reason} just woke me up from the wildest dream!"
        }

    def _get_live2d_dream_parameters(self, now: float) -> Dict[str, float]:
        """Computes live parameter overrides for sleeping/dreaming visuals."""
        st = self.manifest.current_state

        if st == DreamState.AWAKE:
            return {}

        # Slower, deeper respiration wave (frequency halved)
        breath_val = 0.5 + 0.5 * math.sin(now * 1.2)
        # Gentle floating oscillation on head roll Z
        float_z = 3.5 * math.sin(now * 0.6)

        if st == DreamState.DROWSY:
            return {
                "ParamEyeLOpen": 0.35,
                "ParamEyeROpen": 0.35,
                "ParamBreath": round(breath_val, 3),
                "ParamAngleZ": round(float_z * 0.5, 2),
            }
        elif st in [DreamState.REM_DREAM, DreamState.LUCID_SURREAL]:
            return {
                "ParamEyeLOpen": 0.0,
                "ParamEyeROpen": 0.0,
                "ParamBreath": round(breath_val, 3),
                "ParamAngleZ": round(float_z, 2),
                "ParamEyeBallY": round(0.4 * math.sin(now * 4.0), 2),  # REM rapid eye flutter behind closed lids
            }
        elif st == DreamState.WAKING_UP:
            return {
                "ParamEyeLOpen": 0.9,
                "ParamEyeROpen": 0.9,
                "ParamBreath": 0.8,
                "ParamBrowLY": 0.4,
                "ParamBrowRY": 0.4,
            }
        return {}


if __name__ == "__main__":
    engine = DreamSequenceEngine(idle_timeout_sec=2.0)
    print("Initial State:", engine.update_cycle())

    # Simulate waiting 3 seconds to trigger DROWSY -> REM
    time.sleep(2.1)
    print("After Idle:", engine.update_cycle())

    # Force REM
    engine.manifest.current_state = DreamState.REM_DREAM
    engine.manifest.state_start_time = time.time()
    for _ in range(3):
        print("Dream Tick:", engine.update_cycle())

    # Wake up
    wake = engine.trigger_wake_up(reason="Mega Raid with 1,500 viewers")
    print("Wake Result:", wake)
