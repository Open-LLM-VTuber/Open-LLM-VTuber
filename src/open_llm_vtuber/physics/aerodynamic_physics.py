# src/open_llm_vtuber/physics/aerodynamic_physics.py
"""
Physically-Based Wind, Gravity & Cloth/Hair Aerodynamics Engine.

Simulates second-order underdamped harmonic oscillator physics for Live2D/VRM hair,
clothing, ribbons, and accessories driven by audience chat weather commands
(!wind left 75, !blizzard, !gravity 0.2).
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import numpy as np
from loguru import logger


@dataclass
class EnvironmentalState:
    wind_force: float = 0.0      # -100.0 (Left) to +100.0 (Right)
    target_wind: float = 0.0
    gravity_ratio: float = 1.0   # 1.0 = Earth, 0.16 = Moon, 0.0 = Zero-G
    turbulence: float = 0.15     # Gustiness


@dataclass
class AerodynamicKinematics:
    hair_side_x: float           # -1.0 to 1.0 (ParamHairSide)
    hair_front_y: float          # -1.0 to 1.0 (ParamHairFront)
    ribbon_sway: float           # -1.0 to 1.0
    body_lean_z: float           # -10.0 to 10.0 degrees against the wind
    current_wind_mph: float
    gravity_name: str


class AerodynamicPhysicsEngine:
    """
    Sub-millisecond Second-Order Aerodynamic Harmonic Oscillator.
    """

    def __init__(self):
        self.state = EnvironmentalState()
        # Physics state vectors: [displacement, velocity]
        self.hair_pos = 0.0
        self.hair_vel = 0.0
        self.ribbon_pos = 0.0
        self.ribbon_vel = 0.0

        # Physical constants
        self.omega = 16.0  # Natural resonant angular frequency (rad/s)
        self.zeta = 0.55   # Damping ratio (underdamped for natural fluid swaying)

    def parse_chat_weather_command(self, message: str) -> Optional[str]:
        """
        Parses viewer chat commands like:
          !wind left 60, !wind right 100, !storm, !calm, !gravity 0.2
        """
        parts = message.strip().lower().split()
        if not parts:
            return None

        cmd = parts[0]
        if cmd == "!wind":
            direction = parts[1] if len(parts) > 1 else "right"
            speed = 50.0
            if len(parts) > 2 and parts[2].isdigit():
                speed = float(parts[2])

            force = speed if direction in ("right", "east") else -speed
            self.set_weather(wind_force=force)
            return f"Wind gust set to {force:+.1f} towards {direction.upper()}!"

        elif cmd in ("!storm", "!blizzard"):
            self.set_weather(wind_force=90.0, gravity=0.9, turbulence=0.4)
            return "🌪️ Severe Blizzard storm summoned! Strong crosswinds active!"

        elif cmd == "!calm":
            self.set_weather(wind_force=0.0, gravity=1.0, turbulence=0.05)
            return "Calm weather restored."

        elif cmd == "!gravity":
            g = 1.0
            if len(parts) > 1:
                try:
                    g = float(parts[1])
                except ValueError:
                    g = 1.0
            self.set_weather(gravity=g)
            return f"Gravity ratio set to {g:.2f}x standard earth gravity!"

        return None

    def set_weather(
        self,
        wind_force: Optional[float] = None,
        gravity: Optional[float] = None,
        turbulence: Optional[float] = None,
    ):
        """Sets target atmospheric parameters."""
        if wind_force is not None:
            self.state.target_wind = max(-100.0, min(100.0, float(wind_force)))
        if gravity is not None:
            self.state.gravity_ratio = max(0.0, min(2.5, float(gravity)))
        if turbulence is not None:
            self.state.turbulence = max(0.0, min(1.0, float(turbulence)))

    def update_physics(self, delta_time: float = 0.033) -> AerodynamicKinematics:
        """
        Numerically integrates the 2nd-order ODE for hair & cloth displacement.
        """
        # 1. Smooth wind velocity approach with turbulent gusts
        dt = min(0.1, delta_time)
        self.state.wind_force += (self.state.target_wind - self.state.wind_force) * 4.0 * dt

        gust = np.random.normal(0, abs(self.state.wind_force) * self.state.turbulence + 1.0)
        total_aero_force = self.state.wind_force + gust

        # In lower gravity, hair floats higher and experiences less restoring force
        eff_omega = self.omega * math.sqrt(max(0.05, self.state.gravity_ratio))

        # 2. Integrate Hair Physics: x'' + 2*zeta*omega*x' + omega^2*x = F_ext
        spring_f = -(eff_omega ** 2) * self.hair_pos
        damping_f = -2.0 * self.zeta * eff_omega * self.hair_vel
        accel = spring_f + damping_f + (total_aero_force * 0.9)

        self.hair_vel += accel * dt
        self.hair_pos += self.hair_vel * dt

        # 3. Integrate Ribbon Physics (lighter mass, higher frequency)
        ribbon_omega = eff_omega * 1.3
        r_spring = -(ribbon_omega ** 2) * self.ribbon_pos
        r_damping = -2.0 * 0.45 * ribbon_omega * self.ribbon_vel
        r_accel = r_spring + r_damping + (total_aero_force * 1.2)

        self.ribbon_vel += r_accel * dt
        self.ribbon_pos += self.ribbon_vel * dt

        # Normalize to Live2D ranges [-1.0, 1.0]
        norm_hair = float(np.clip(self.hair_pos / 100.0, -1.0, 1.0))
        norm_front = float(np.clip((abs(self.hair_pos) / 100.0) * (2.0 - self.state.gravity_ratio), 0.0, 1.0))
        norm_ribbon = float(np.clip(self.ribbon_pos / 100.0, -1.0, 1.0))

        # Body lean against wind (subtle natural compensation)
        body_lean = float(np.clip(-self.state.wind_force * 0.08, -8.0, 8.0))

        g_name = "Earth (1.0G)"
        if self.state.gravity_ratio <= 0.05:
            g_name = "Zero-G Floating"
        elif self.state.gravity_ratio < 0.4:
            g_name = "Moon Gravity"

        return AerodynamicKinematics(
            hair_side_x=round(norm_hair, 3),
            hair_front_y=round(norm_front, 3),
            ribbon_sway=round(norm_ribbon, 3),
            body_lean_z=round(body_lean, 2),
            current_wind_mph=round(abs(total_aero_force) * 0.65, 1),
            gravity_name=g_name,
        )


if __name__ == "__main__":
    engine = AerodynamicPhysicsEngine()
    print("Testing Aerodynamic Physics & Weather Simulation...")

    # Set gale storm from left
    msg = "!wind left 80"
    ack = engine.parse_chat_weather_command(msg)
    print(f"Chat: '{msg}' -> {ack}")

    # Step simulation 15 frames
    for i in range(15):
        k = engine.update_physics(delta_time=0.033)

    print(f"\nKinematics after storm gust:")
    print(f"  ParamHairSide: {k.hair_side_x} | ParamRibbon: {k.ribbon_sway} | Lean AngleZ: {k.body_lean_z} deg")
    print(f"  Effective Wind: {k.current_wind_mph} mph | Gravity: {k.gravity_name}")

    # Set Zero-G
    engine.parse_chat_weather_command("!gravity 0.0")
    k_zero = engine.update_physics(delta_time=0.033)
    print(f"\nZero-G Mode Activated: Hair Float: {k_zero.hair_front_y} | State: {k_zero.gravity_name}")
