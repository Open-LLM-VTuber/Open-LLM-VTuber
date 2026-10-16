# src/open_llm_vtuber/studio/studio_director.py
"""
Autonomous Multi-Camera Studio Director via OBS WebSocket v5.

Acts as an automated broadcast television director for solo and AI streams.
Monitors the avatar's real-time PAD Affective State (Valence, Arousal, Dominance)
and gaming telemetry to dynamically cut between cinematic camera angles:
- HERO_CHATTING: Standard face-to-face stream view
- DRAMATIC_CLOSEUP: 1.8x zoom on jumpscares, death, or shocking lore drops
- BATTLE_COMBAT: High-FPS gameplay canvas during intense boss encounters
- VICTORY_PODIUM: Celebratory centered scene during clutch wins
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any
from loguru import logger


@dataclass
class CameraCutEvent:
    from_scene: str
    to_scene: str
    trigger_reason: str
    arousal: float
    valence: float
    timestamp: float = field(default_factory=time.time)


class AutonomousStudioDirector:
    """
    State-Driven Broadcast Production Director.
    """

    SCENES = {
        "HERO": "SCENE_HERO_CHATTING",
        "CLOSEUP": "SCENE_DRAMATIC_CLOSEUP",
        "BATTLE": "SCENE_BATTLE_COMBAT",
        "VICTORY": "SCENE_VICTORY_PODIUM",
    }

    def __init__(self, min_dwell_seconds: float = 6.0, obs_host: str = "localhost", obs_port: int = 4455):
        self.min_dwell = min_dwell_seconds
        self.obs_host = obs_host
        self.obs_port = obs_port
        self.current_scene = self.SCENES["HERO"]
        self.last_switch_time = time.time() - min_dwell_seconds
        self.cut_history: list = []

    def evaluate_camera_cut(
        self,
        valence: float,
        arousal: float,
        in_combat: bool = False,
        is_speaking: bool = True,
        force: bool = False,
    ) -> Optional[CameraCutEvent]:
        """
        Evaluates current affective telemetry against director heuristic matrix.
        Enforces minimum shot dwell time to prevent rapid camera cutting.
        """
        now = time.time()
        if not force and (now - self.last_switch_time < self.min_dwell):
            return None

        target_scene = self.current_scene
        reason = "Normal Pacing"

        # Heuristic Decision Matrix
        if in_combat and arousal > 0.60:
            target_scene = self.SCENES["BATTLE"]
            reason = f"High Combat Intensity (Arousal: {arousal:.2f})"
        elif arousal > 0.75 and valence < -0.25:
            target_scene = self.SCENES["CLOSEUP"]
            reason = f"Intense Shock / Jumpscare / Failure (Arousal: {arousal:.2f}, Valence: {valence:.2f})"
        elif valence > 0.70 and arousal > 0.60:
            target_scene = self.SCENES["VICTORY"]
            reason = f"Clutch Victory / Celebration (Valence: {valence:.2f})"
        elif not in_combat and arousal < 0.40:
            target_scene = self.SCENES["HERO"]
            reason = "Restful Commentary / Conversational Lull"

        if target_scene != self.current_scene:
            prev = self.current_scene
            self.current_scene = target_scene
            self.last_switch_time = now

            event = CameraCutEvent(
                from_scene=prev,
                to_scene=target_scene,
                trigger_reason=reason,
                arousal=round(arousal, 2),
                valence=round(valence, 2),
            )
            self.cut_history.append(event)
            logger.info(f"[StudioDirector] Camera Cut: {prev} -> {target_scene} ({reason})")
            return event

        return None

    def get_obs_switch_payload(self, event: CameraCutEvent) -> Dict[str, Any]:
        """Formats OBS WebSocket v5 SetCurrentProgramScene request."""
        return {
            "op": 6,  # Request
            "d": {
                "requestType": "SetCurrentProgramScene",
                "requestId": f"cut_{int(time.time()*1000)}",
                "requestData": {"sceneName": event.to_scene},
            },
        }


if __name__ == "__main__":
    director = AutonomousStudioDirector(min_dwell_seconds=1.0)
    print("Initial Scene:", director.current_scene)

    # Simulate boss fight starting
    cut1 = director.evaluate_camera_cut(valence=0.1, arousal=0.85, in_combat=True)
    print("Combat Cut:", cut1)

    # Wait dwell time and simulate defeat / jumpscare
    time.sleep(1.05)
    cut2 = director.evaluate_camera_cut(valence=-0.6, arousal=0.92, in_combat=False)
    print("Jumpscare Cut:", cut2)
    print("OBS Payload:", director.get_obs_switch_payload(cut2))
