# src/open_llm_vtuber/studio/particle_expressiveness.py
"""
Procedural Anime Particle Expressiveness & Micro-Physiological FX Engine.

Simulates classic anime visual tropes anchored to Live2D facial geometry:
- Comical Sweat Drops (nervous, flustered, awkward)
- Ear Steam Puffs (angry, tilted, frustrated)
- Twin Tear Fountains (dramatic defeat, crying, sorrow)
- Starry Eye Sparkles (hype, victory, greed/treasures)

Couples directly with the PAD Affective Engine to automatically spawn particle
effects based on real-time valence, arousal, and dominance emotional vectors.
"""

import math
import random
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple
from loguru import logger


@dataclass
class AnimeParticle:
    particle_id: str
    effect_type: str  # "SWEAT_DROP", "ANGRY_STEAM", "COMEDIC_TEARS", "SPARKLE_EYES"
    anchor_zone: str  # "forehead_right", "temple_left", "temple_right", "eye_left", "eye_right"
    x: float
    y: float
    vx: float
    vy: float
    scale: float
    alpha: float
    lifespan_ms: int
    created_at: float = field(default_factory=time.time)


@dataclass
class ParticleSpawnEvent:
    effect_type: str
    particle_count: int
    anchor_zone: str
    active_particles: List[AnimeParticle]
    timestamp: float = field(default_factory=time.time)


class AnimeParticleEngine:
    """
    Sub-millisecond Procedural Anime Particle Generator & PAD Coupling Controller.
    """

    ANCHOR_OFFSETS = {
        "forehead_right": (320.0, 180.0),
        "temple_left": (210.0, 170.0),
        "temple_right": (430.0, 170.0),
        "eye_left": (270.0, 220.0),
        "eye_right": (370.0, 220.0),
    }

    def __init__(self):
        self.active_particles: List[AnimeParticle] = []
        self._particle_counter = 0

    def spawn_effect(self, effect_type: str) -> ParticleSpawnEvent:
        """Generates a batch of anime particles with physics initial vectors."""
        eff = effect_type.upper()
        new_particles = []

        if eff == "SWEAT_DROP":
            ox, oy = self.ANCHOR_OFFSETS["forehead_right"]
            p = AnimeParticle(
                particle_id=f"sweat_{self._particle_counter}",
                effect_type=eff,
                anchor_zone="forehead_right",
                x=ox,
                y=oy,
                vx=0.0,
                vy=2.5,
                scale=1.0,
                alpha=1.0,
                lifespan_ms=1200,
            )
            self._particle_counter += 1
            new_particles.append(p)
            zone = "forehead_right"

        elif eff == "ANGRY_STEAM":
            # Dual ear steam puffs
            for side in ("temple_left", "temple_right"):
                ox, oy = self.ANCHOR_OFFSETS[side]
                dir_x = -1.8 if "left" in side else 1.8
                for i in range(3):
                    p = AnimeParticle(
                        particle_id=f"steam_{self._particle_counter}",
                        effect_type=eff,
                        anchor_zone=side,
                        x=ox,
                        y=oy,
                        vx=dir_x + random.uniform(-0.5, 0.5),
                        vy=-2.2 - random.uniform(0.2, 0.8),
                        scale=random.uniform(0.8, 1.4),
                        alpha=0.95,
                        lifespan_ms=850,
                    )
                    self._particle_counter += 1
                    new_particles.append(p)
            zone = "dual_temples"

        elif eff == "COMEDIC_TEARS":
            # Twin waterfalls from left & right eyes
            for side in ("eye_left", "eye_right"):
                ox, oy = self.ANCHOR_OFFSETS[side]
                dir_x = -1.2 if "left" in side else 1.2
                for i in range(4):
                    p = AnimeParticle(
                        particle_id=f"tear_{self._particle_counter}",
                        effect_type=eff,
                        anchor_zone=side,
                        x=ox,
                        y=oy,
                        vx=dir_x + random.uniform(-0.3, 0.3),
                        vy=3.0 + random.uniform(0.5, 1.5),
                        scale=random.uniform(1.0, 1.6),
                        alpha=0.9,
                        lifespan_ms=900,
                    )
                    self._particle_counter += 1
                    new_particles.append(p)
            zone = "dual_eyes"

        elif eff == "SPARKLE_EYES":
            # Star sparkles in eyes
            for side in ("eye_left", "eye_right"):
                ox, oy = self.ANCHOR_OFFSETS[side]
                p = AnimeParticle(
                    particle_id=f"sparkle_{self._particle_counter}",
                    effect_type=eff,
                    anchor_zone=side,
                    x=ox + random.uniform(-6, 6),
                    y=oy + random.uniform(-6, 6),
                    vx=random.uniform(-0.2, 0.2),
                    vy=random.uniform(-0.2, 0.2),
                    scale=random.uniform(1.2, 2.0),
                    alpha=1.0,
                    lifespan_ms=1500,
                )
                self._particle_counter += 1
                new_particles.append(p)
            zone = "dual_eyes"

        else:
            logger.warning(f"Unknown particle effect '{effect_type}'")
            return ParticleSpawnEvent(effect_type=eff, particle_count=0, anchor_zone="none", active_particles=[])

        self.active_particles.extend(new_particles)
        logger.info(f"[Particle FX] Triggered '{eff}' ({len(new_particles)} particles at {zone})")
        return ParticleSpawnEvent(
            effect_type=eff,
            particle_count=len(new_particles),
            anchor_zone=zone,
            active_particles=new_particles,
        )

    def evaluate_pad_emotion(self, valence: float, arousal: float, dominance: float) -> Optional[str]:
        """
        Maps PAD emotional coordinates [-1.0, 1.0] to classic anime tropes.
        """
        # Angry Steam: Negative valence, high arousal, high dominance
        if valence < -0.35 and arousal > 0.60 and dominance > 0.10:
            return "ANGRY_STEAM"

        # Comedic Tears: Very negative valence, low dominance (feeling defeated/hopeless)
        if valence < -0.45 and dominance < -0.20:
            return "COMEDIC_TEARS"

        # Starry Eye Sparkles: High valence, high arousal (triumphant, ecstatic)
        if valence > 0.50 and arousal > 0.45:
            return "SPARKLE_EYES"

        # Flustered Sweat: Negative valence, high arousal, low dominance (nervous panic)
        if valence < -0.10 and arousal > 0.40 and dominance < -0.10:
            return "SWEAT_DROP"

        return None

    def update_physics(self, delta_time: float = 0.033) -> List[AnimeParticle]:
        """Steps particle positions and decays alphas."""
        now = time.time()
        surviving = []
        for p in self.active_particles:
            age_ms = (now - p.created_at) * 1000.0
            if age_ms < p.lifespan_ms:
                p.x += p.vx
                p.y += p.vy
                p.alpha = max(0.0, 1.0 - (age_ms / p.lifespan_ms))
                surviving.append(p)

        self.active_particles = surviving
        return self.active_particles


if __name__ == "__main__":
    fx = AnimeParticleEngine()
    print("Testing Anime Particle Expressiveness & PAD Emotion Coupling...")

    # Test PAD mapping for Rage/Tilt
    tilted_fx = fx.evaluate_pad_emotion(valence=-0.7, arousal=0.85, dominance=0.4)
    print(f"PAD State (V:-0.7, A:0.85, D:0.4) -> Recommended Particle FX: {tilted_fx}")
    event_tilt = fx.spawn_effect(tilted_fx)
    print(f"Spawned: {event_tilt.particle_count} particles at {event_tilt.anchor_zone}")

    # Test PAD mapping for Ecstatic Victory
    victory_fx = fx.evaluate_pad_emotion(valence=0.8, arousal=0.75, dominance=0.6)
    print(f"\nPAD State (V:0.8, A:0.75, D:0.6) -> Recommended Particle FX: {victory_fx}")
    event_win = fx.spawn_effect(victory_fx)
    print(f"Spawned: {event_win.particle_count} particles at {event_win.anchor_zone}")

    # Physics step
    surviving = fx.update_physics(delta_time=0.033)
    print(f"\nActive particles after physics step: {len(surviving)}")
