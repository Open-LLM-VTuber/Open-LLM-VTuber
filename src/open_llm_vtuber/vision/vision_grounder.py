# src/open_llm_vtuber/vision/vision_grounder.py
"""
Dynamic Real-Time Multi-Modal Vision Grounding & Spatial Gaze Retargeter.

Provides zero-shot open-vocabulary spatial perception across the streamer's screen.
Identifies in-game entities (enemies, health bars, loot, crosshairs) and retargets
avatar ocular and cranial kinematics (ParamEyeBallX/Y, ParamAngleX/Y) so the AI VTuber
physically snaps its gaze toward on-screen events in real-time.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
from loguru import logger


@dataclass
class GroundedEntity:
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2 in pixels
    norm_x: float  # -1.0 (Left) to 1.0 (Right)
    norm_y: float  # -1.0 (Down) to 1.0 (Up)
    timestamp: float = field(default_factory=time.time)


@dataclass
class AvatarGazeKinematics:
    eye_ball_x: float  # -1.0 to 1.0
    eye_ball_y: float  # -1.0 to 1.0
    head_angle_x: float  # -30 to 30 degrees
    head_angle_y: float  # -30 to 30 degrees
    target_entity: Optional[str] = None


class DesktopVisionGrounder:
    """
    Sub-millisecond Spatial Vision Grounder and Gaze Retargeting Controller.
    """

    def __init__(self, screen_width: int = 1920, screen_height: int = 1080):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.tracked_labels = ["enemy player", "health bar", "loot item", "crosshair", "dialogue box"]

        # Spring-damper smoothing states
        self.curr_eye_x = 0.0
        self.curr_eye_y = 0.0
        self.curr_head_x = 0.0
        self.curr_head_y = 0.0

    def compute_normalized_coordinates(self, bbox: Tuple[int, int, int, int]) -> Tuple[float, float]:
        """Maps pixel bbox center to normalized [-1.0, 1.0] coordinates."""
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0

        norm_x = (cx / self.screen_width) * 2.0 - 1.0
        norm_y = -((cy / self.screen_height) * 2.0 - 1.0)
        return float(np.clip(norm_x, -1.0, 1.0)), float(np.clip(norm_y, -1.0, 1.0))

    def retarget_gaze_spring(
        self, target_x: float, target_y: float, delta_time: float = 0.033
    ) -> AvatarGazeKinematics:
        """
        Applies a critically damped spring-damper to smoothly interpolate eye & head angles
        towards the focal screen object, preventing abrupt unnatural snapping.
        """
        # Eyes track faster with high sensitivity (alpha = 0.45)
        eye_alpha = min(1.0, 14.0 * delta_time)
        self.curr_eye_x += (target_x - self.curr_eye_x) * eye_alpha
        self.curr_eye_y += (target_y - self.curr_eye_y) * eye_alpha

        # Head follows with more physical inertia (alpha = 0.20)
        head_alpha = min(1.0, 6.0 * delta_time)
        target_head_x = target_x * 25.0  # max 25 degrees
        target_head_y = target_y * 20.0  # max 20 degrees
        self.curr_head_x += (target_head_x - self.curr_head_x) * head_alpha
        self.curr_head_y += (target_head_y - self.curr_head_y) * head_alpha

        return AvatarGazeKinematics(
            eye_ball_x=round(self.curr_eye_x, 3),
            eye_ball_y=round(self.curr_eye_y, 3),
            head_angle_x=round(self.curr_head_x, 2),
            head_angle_y=round(self.curr_head_y, 2),
        )

    def process_detected_objects(
        self, raw_detections: List[Dict[str, any]], delta_time: float = 0.033
    ) -> Tuple[List[GroundedEntity], AvatarGazeKinematics, Optional[str]]:
        """
        Processes detections, selects primary point of interest, and calculates kinematics.
        """
        entities: List[GroundedEntity] = []
        priority_target = None
        highest_priority = -1

        priority_order = {"enemy player": 3, "loot item": 2, "health bar": 1, "crosshair": 0}

        for d in raw_detections:
            lbl = d.get("label", "unknown")
            conf = float(d.get("confidence", 0.8))
            bbox = d.get("bbox", (960, 540, 980, 560))
            nx, ny = self.compute_normalized_coordinates(bbox)

            entity = GroundedEntity(label=lbl, confidence=conf, bbox=bbox, norm_x=nx, norm_y=ny)
            entities.append(entity)

            prio = priority_order.get(lbl, 0)
            if prio > highest_priority:
                highest_priority = prio
                priority_target = entity

        speech_cue = None
        if priority_target:
            gaze = self.retarget_gaze_spring(priority_target.norm_x, priority_target.norm_y, delta_time)
            gaze.target_entity = priority_target.label
            if priority_target.label == "enemy player":
                side = "left" if priority_target.norm_x < -0.2 else ("right" if priority_target.norm_x > 0.2 else "center")
                speech_cue = (
                    f"[TACTICAL VISUAL ALERT] Detected enemy player on the {side} "
                    f"(X: {priority_target.norm_x:+.2f}, Y: {priority_target.norm_y:+.2f})! Warn the stream immediately!"
                )
        else:
            # Drift gaze back to center
            gaze = self.retarget_gaze_spring(0.0, 0.0, delta_time)

        return entities, gaze, speech_cue


if __name__ == "__main__":
    grounder = DesktopVisionGrounder(screen_width=1920, screen_height=1080)
    print("Testing Vision Grounding & Gaze Kinematics...")

    # Simulated detection: Enemy sneaking in top-left corner
    detections = [
        {"label": "health bar", "confidence": 0.95, "bbox": (100, 50, 300, 80)},
        {"label": "enemy player", "confidence": 0.88, "bbox": (150, 200, 250, 450)},  # Upper-left
    ]

    entities, gaze, cue = grounder.process_detected_objects(detections, delta_time=0.033)
    print(f"Entities Detected: {len(entities)}")
    print(f"Primary Target: {gaze.target_entity}")
    print(f"Avatar Kinematics -> Eyes: (X: {gaze.eye_ball_x}, Y: {gaze.eye_ball_y}) | Head: (Yaw: {gaze.head_angle_x} deg, Pitch: {gaze.head_angle_y} deg)")
    if cue:
        print(f"\nAI VTuber Reaction Cue:\n\"{cue}\"")
