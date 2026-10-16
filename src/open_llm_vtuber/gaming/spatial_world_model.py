# src/open_llm_vtuber/gaming/spatial_world_model.py
"""
Persistent 3D Spatial Coordinate World Model for Gaming & Virtual Environments.

Maintains an indexed spatial memory of landmarks, chests, hazards, and player locations
in games like Minecraft, Elden Ring, or open-world RPGs. Computes real-time vector
distances, compass bearings, and proximity alerts to inject rich situational awareness
into the LLM context with zero computer-vision overhead.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger


@dataclass
class SpatialPoint:
    name: str
    category: str       # "base", "resource", "hazard", "boss", "npc", "waypoint"
    x: float
    y: float
    z: float
    dimension: str = "overworld"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class ProximityAlert:
    landmark_name: str
    category: str
    distance_meters: float
    bearing_compass: str
    relative_height: str  # "above", "below", "level"
    alert_level: str      # "info", "warning", "critical"


class SpatialWorldModel:
    """
    Sub-millisecond 3D Coordinate Memory and Proximity Engine.
    """

    COMPASS_SECTORS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

    def __init__(self, proximity_threshold: float = 30.0):
        self.landmarks: Dict[str, SpatialPoint] = {}
        self.proximity_threshold = proximity_threshold
        self.last_player_pos: Optional[Tuple[float, float, float]] = None
        self.current_dimension: str = "overworld"

    def record_landmark(
        self,
        name: str,
        category: str,
        x: float,
        y: float,
        z: float,
        dimension: str = "overworld",
        **metadata,
    ) -> SpatialPoint:
        """Saves or updates a 3D coordinate in spatial memory."""
        pt = SpatialPoint(
            name=name,
            category=category,
            x=x,
            y=y,
            z=z,
            dimension=dimension,
            metadata=metadata,
        )
        self.landmarks[name] = pt
        logger.info(f"[SpatialWorldModel] Recorded landmark '{name}' ({category}) at ({x}, {y}, {z}) [{dimension}]")
        return pt

    def remove_landmark(self, name: str) -> bool:
        if name in self.landmarks:
            del self.landmarks[name]
            return True
        return False

    def update_player_position(
        self, x: float, y: float, z: float, dimension: str = "overworld"
    ) -> List[ProximityAlert]:
        """
        Updates the current player/avatar location and checks for proximity triggers.
        Returns a list of active proximity alerts within `proximity_threshold`.
        """
        self.last_player_pos = (x, y, z)
        self.current_dimension = dimension
        alerts: List[ProximityAlert] = []

        for pt in self.landmarks.values():
            if pt.dimension != dimension:
                continue

            dx = pt.x - x
            dy = pt.y - y
            dz = pt.z - z
            distance = math.sqrt(dx * dx + dy * dy + dz * dz)

            if distance <= self.proximity_threshold:
                bearing = self._calc_compass_bearing(dx, dz)
                rel_h = "level"
                if dy > 3.0:
                    rel_h = f"{round(dy, 1)}m above"
                elif dy < -3.0:
                    rel_h = f"{round(abs(dy), 1)}m below"

                alert_level = "critical" if pt.category == "hazard" else "warning" if distance < 10.0 else "info"

                alerts.append(
                    ProximityAlert(
                        landmark_name=pt.name,
                        category=pt.category,
                        distance_meters=round(distance, 1),
                        bearing_compass=bearing,
                        relative_height=rel_h,
                        alert_level=alert_level,
                    )
                )

        # Sort alerts by closest first
        alerts.sort(key=lambda a: a.distance_meters)
        return alerts

    def get_spatial_context_prompt(self, max_items: int = 5) -> str:
        """
        Generates situational spatial context string for inclusion in LLM system prompt.
        """
        if not self.last_player_pos:
            return "Current location: Unknown"

        px, py, pz = self.last_player_pos
        lines = [f"[SPATIAL SITUATION] Position: ({px:.1f}, {py:.1f}, {pz:.1f}) in {self.current_dimension}"]

        alerts = self.update_player_position(px, py, pz, self.current_dimension)
        if alerts:
            lines.append("Nearby Landmarks / Hazards:")
            for a in alerts[:max_items]:
                lines.append(f" - {a.landmark_name} ({a.category}): {a.distance_meters}m {a.bearing_compass} ({a.relative_height}) [{a.alert_level.upper()}]")
        else:
            lines.append("No immediate landmarks within sensor range.")

        return "\n".join(lines)

    @staticmethod
    def _calc_compass_bearing(dx: float, dz: float) -> str:
        """Calculates 8-way compass bearing from 2D delta (X = East/West, Z = North/South)."""
        angle_rad = math.atan2(dx, -dz)  # In Minecraft/standard games, negative Z is North
        angle_deg = math.degrees(angle_rad) % 360.0
        idx = int((angle_deg + 22.5) / 45.0) % 8
        return SpatialWorldModel.COMPASS_SECTORS[idx]


if __name__ == "__main__":
    world = SpatialWorldModel(proximity_threshold=50.0)

    # Populate sample world points
    world.record_landmark("Home Base & Bed", "base", x=100.0, y=64.0, z=200.0)
    world.record_landmark("Ancient Deep Dark Pit", "hazard", x=125.0, y=12.0, z=215.0)
    world.record_landmark("Diamond Mine Shaft", "resource", x=80.0, y=15.0, z=190.0)

    # Simulate player moving close to base and hazard
    alerts = world.update_player_position(x=115.0, y=60.0, z=210.0)
    print("Proximity Alerts:", alerts)
    print("\nLLM Spatial Context Prompt:\n" + world.get_spatial_context_prompt())
