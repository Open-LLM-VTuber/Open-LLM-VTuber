"""
Interactive Chat Physics & Virtual Object Collision Engine.
Handles thrown objects (!throw pie, !gift flower, !drop anvil) from stream chat,
calculating ballistic trajectory recoil and emotional impact.
"""
import time
import random
from typing import Dict, Any, Optional, Tuple
from loguru import logger


class StreamPhysicsEngine:
    """
    Manages rigid-body collisions and kinematic recoil for Live2D/VRM avatars.
    """
    def __init__(self):
        self.item_properties = {
            "pie": {"recoil_y": -25.0, "recoil_z": 15.0, "valence_delta": -0.4, "arousal_delta": 0.5, "sound": "splat.mp3", "prompt": "A viewer threw a whipped-cream pie directly at your face! You are covered in cream. React with outrage and sarcasm!"},
            "tomato": {"recoil_y": -18.0, "recoil_z": 10.0, "valence_delta": -0.3, "arousal_delta": 0.4, "sound": "splat.mp3", "prompt": "A viewer threw a rotten tomato at you! Tell them their aim was lucky and roast them!"},
            "flower": {"recoil_y": -5.0, "recoil_z": -5.0, "valence_delta": 0.5, "arousal_delta": 0.2, "sound": "twinkle.mp3", "prompt": "A viewer tossed a bouquet of beautiful flowers at your feet! Act slightly flustered, flattered, and tsundere."},
            "anvil": {"recoil_y": -45.0, "recoil_z": 30.0, "valence_delta": -0.7, "arousal_delta": 0.8, "sound": "clang.mp3", "prompt": "A heavy cartoon ACME anvil dropped straight onto your head! You have bird stars circling your head. Speak with dizzy, cartoonish groaning!"},
            "cookie": {"recoil_y": -8.0, "recoil_z": 2.0, "valence_delta": 0.4, "arousal_delta": 0.1, "sound": "crunch.mp3", "prompt": "A viewer tossed a freshly baked chocolate chip cookie at you. Catch it and enjoy it!"}
        }
        self.last_throw_time = 0.0
        self.throw_cooldown = 4.0  # seconds between physical throws

    def parse_chat_command(self, text: str, sender: str = "Viewer") -> Optional[Dict[str, Any]]:
        """Parses chat messages like '!throw pie' or '!gift flower'."""
        parts = text.strip().split()
        if not parts:
            return None

        cmd = parts[0].lower()
        if cmd in ["!throw", "!gift", "!drop", "!toss"] and len(parts) > 1:
            item_name = parts[1].lower().rstrip("!,.")
            return self.execute_throw(item_name, sender=sender)
        return None

    def execute_throw(self, item_name: str, sender: str = "Viewer") -> Optional[Dict[str, Any]]:
        now = time.time()
        if now - self.last_throw_time < self.throw_cooldown:
            return None

        prop = self.item_properties.get(item_name)
        if not prop:
            prop = self.item_properties["pie"]  # Fallback to pie

        self.last_throw_time = now
        impact_payload = {
            "item": item_name,
            "sender": sender,
            "recoil": {
                "ParamAngleY": prop["recoil_y"],
                "ParamAngleZ": prop["recoil_z"]
            },
            "sound_effect": prop["sound"],
            "pad_delta": (prop["valence_delta"], prop["arousal_delta"]),
            "reaction_prompt": f"[PHYSICAL COLLISION EVENT]: @{sender} threw a {item_name} at you!\n{prop['prompt']}"
        }
        logger.info(f"Physics Impact: @{sender} threw {item_name}! Recoil: {impact_payload['recoil']}")
        return impact_payload
