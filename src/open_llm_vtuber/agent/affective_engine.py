"""
PAD (Pleasure, Arousal, Dominance) 3D Affective State Machine for AI Influencers.
Implements dynamic mood drift, game event impulses, and emotional baseline recovery.
"""
import time
import math
from typing import Dict, Tuple
from loguru import logger


class AffectiveEngine:
    """
    Tracks and updates 3D emotional vector S = [V, A, D] in [-1.0, 1.0].
    Valence:   Negative (-1.0) to Positive (1.0) [Sad/Angry <-> Happy/Joyful]
    Arousal:   Passive (-1.0) to Active (1.0)   [Sleepy/Bored <-> Excited/Panicked]
    Dominance: Submissive (-1.0) to Dominant (1.0) [Intimidated <-> Confident/Roasting]
    """
    def __init__(
        self,
        baseline_v: float = -0.1,
        baseline_a: float = 0.2,
        baseline_d: float = 0.5,
        alpha: float = 0.03,  # Baseline drift rate
        gamma: float = 0.30   # Impulse decay rate
    ):
        # Character resting personality
        self.m_rest = [baseline_v, baseline_a, baseline_d]
        # Current slow baseline mood
        self.m_base = list(self.m_rest)
        # Current fast emotion impulse
        self.m_impulse = [0.0, 0.0, 0.0]
        self.alpha = alpha
        self.gamma = gamma
        self.last_update = time.time()

        # Preset event impulse values: (delta_V, delta_A, delta_D)
        self.event_map = {
            "GAME_DEATH": (-0.35, 0.40, 0.35),
            "STREAK_DEATH": (-0.50, 0.55, 0.60),
            "VICTORY": (0.65, 0.50, 0.55),
            "JUMPSCARE": (-0.30, 0.85, -0.40),
            "SUPERCHAT_DONATION": (0.75, 0.60, -0.10),
            "TOXIC_CHAT": (-0.25, 0.35, 0.65),
            "COMPLIMENT": (0.45, 0.20, 0.10),
            "IDLE_SILENCE": (-0.15, -0.40, -0.20),
        }

    def _decay(self):
        now = time.time()
        dt = max(0.1, now - self.last_update)
        self.last_update = now

        # Decay fast impulse toward 0
        decay_factor = math.exp(-self.gamma * dt)
        self.m_impulse = [val * decay_factor for val in self.m_impulse]

        # Drift baseline toward rest personality
        drift_factor = math.exp(-self.alpha * dt)
        self.m_base = [
            self.m_rest[i] + (self.m_base[i] - self.m_rest[i]) * drift_factor
            for i in range(3)
        ]

    def trigger_event(self, event_name: str, multiplier: float = 1.0):
        """Apply an emotional impulse from a stream/game event."""
        self._decay()
        impulse = self.event_map.get(event_name.upper())
        if not impulse:
            logger.debug(f"AffectiveEngine: Unknown event {event_name}")
            return

        for i in range(3):
            delta = impulse[i] * multiplier
            self.m_impulse[i] = max(-1.0, min(1.0, self.m_impulse[i] + delta))
            # Slightly drag baseline mood
            self.m_base[i] = max(-1.0, min(1.0, self.m_base[i] + delta * 0.15))

        logger.info(f"AffectiveEngine event '{event_name}': Current mood -> {self.get_mood_label()}")

    @property
    def current_pad(self) -> Tuple[float, float, float]:
        self._decay()
        v = max(-1.0, min(1.0, self.m_base[0] + self.m_impulse[0]))
        a = max(-1.0, min(1.0, self.m_base[1] + self.m_impulse[1]))
        d = max(-1.0, min(1.0, self.m_base[2] + self.m_impulse[2]))
        return (round(v, 2), round(a, 2), round(d, 2))

    def get_mood_label(self) -> str:
        v, a, d = self.current_pad
        if v > 0.4 and a > 0.3:
            return "Euphoric & Triumphant" if d > 0.3 else "Overjoyed & Flustered"
        elif v > 0.2 and a <= 0.3:
            return "Cheerful & Relaxed"
        elif v < -0.3 and a > 0.4:
            return "Tilted & Spiteful" if d > 0.3 else "Panicked & Distressed"
        elif v < -0.2 and a <= 0.0:
            return "Cynical & Sarcastic"
        elif a < -0.3:
            return "Lethargic & Bored"
        elif d > 0.5:
            return "Smug & Condescending"
        return "Calm & Confident"

    def get_prompt_directive(self) -> str:
        """Generates dynamic emotional context to inject into LLM system prompt."""
        v, a, d = self.current_pad
        label = self.get_mood_label()

        directives = {
            "Euphoric & Triumphant": "You are feeling ecstatic, completely unstoppable, and full of bragging rights!",
            "Overjoyed & Flustered": "You are super happy, grateful, and slightly shy/flustered by the viewer support!",
            "Cheerful & Relaxed": "You are in a pleasant, friendly, welcoming mood.",
            "Tilted & Spiteful": "You are deeply annoyed and tilted by gameplay errors. Speak with sharp sarcasm, roast chat, and blame server lag!",
            "Panicked & Distressed": "You are shocked and alarmed by what just happened on screen. Speak with frantic urgency!",
            "Cynical & Sarcastic": "You are in a dry, deadpan, cynical mood.",
            "Lethargic & Bored": "You are bored because chat has been quiet. Whine playfully or sigh, demanding chat entertain you.",
            "Smug & Condescending": "You are acting smug, overly confident, and like you are superior to all the humans watching.",
            "Calm & Confident": "You are collected, sharp-witted, and composed."
        }

        directive = directives.get(label, "Express yourself naturally in character.")
        return f"[Affective State: {label} (Valence: {v}, Arousal: {a}, Dominance: {d})]\n{directive}"

    def get_expression_hint(self) -> str:
        v, a, d = self.current_pad
        if v < -0.3 and d > 0.2:
            return "anger"
        elif v < -0.3 and d <= 0.2:
            return "fear"
        elif v > 0.4:
            return "joy"
        elif d > 0.4:
            return "smirk"
        elif v < -0.1:
            return "sadness"
        return "neutral"

    def get_tts_modulation(self) -> Dict[str, float]:
        v, a, d = self.current_pad
        # Higher arousal -> faster speech; lower valence -> slightly lower pitch
        speed = round(1.0 + 0.20 * a, 2)
        pitch = round(1.0 + 0.15 * v, 2)
        return {"speed": max(0.8, min(1.35, speed)), "pitch": max(0.85, min(1.25, pitch))}
