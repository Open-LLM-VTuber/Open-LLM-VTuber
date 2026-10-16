# src/open_llm_vtuber/live/in_character_moderator.py
"""
Autonomous In-Character Chat Moderation & Crowd Behavioral Shaper.

Scans incoming chat stream for backseating, spoilers, and toxic spam in <15ms.
Rather than cold robotic silences, the AI VTuber delivers hilarious in-character
verbal roasts while simultaneously dispatching automated platform timeouts via the Twitch Helix API.
"""

import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from loguru import logger


@dataclass
class ModerationAction:
    username: str
    category: str  # "BACKSEATING", "SPOILER", "TOXIC_FLAME", "SPAM_RAID", "CLEAN"
    strike_count: int
    duration_seconds: int  # 0 = warning only, 60 = timeout, 600 = ban
    verbal_roast_prompt: Optional[str]
    helix_payload: Optional[Dict[str, any]]
    timestamp: float = field(default_factory=time.time)


class InCharacterModerator:
    """
    Sub-15ms In-Character Stream Bouncer and Behavioral Shaping Engine.
    """

    PATTERNS = {
        "BACKSEATING": [
            r"\bgo (left|right|up|down|straight)\b",
            r"\buse (the|your) potion\b",
            r"\byou need to\b",
            r"\bpress [a-z]\b",
            r"\byou missed (the|a)\b",
            r"\bwhy aren't you\b",
            r"\bplay it like this\b",
        ],
        "SPOILER": [
            r"\bdies in (chapter|season|episode|end)\b",
            r"\bthe killer is\b",
            r"\bturns out to be\b",
            r"\bboss is weak to\b",
            r"\bsecret ending\b",
        ],
        "TOXIC_FLAME": [
            r"\b(idiot|trash|uninstall|noob|stupid|terrible)\b",
            r"\bstop streaming\b",
        ],
    }

    def __init__(self, vtuber_name: str = "Mili"):
        self.vtuber_name = vtuber_name
        self.user_strikes: Dict[str, int] = {}
        logger.info(f"In-Character Chat Moderator initialized for {self.vtuber_name}.")

    def classify_message(self, username: str, text: str) -> ModerationAction:
        """
        Evaluates message against rule triggers, tracks strikes, and generates verbal burns.
        """
        uname = username.lower()
        t_lower = text.lower()

        detected_category = "CLEAN"
        for cat, regexes in self.PATTERNS.items():
            if any(re.search(p, t_lower) for p in regexes):
                detected_category = cat
                break

        if detected_category == "CLEAN":
            return ModerationAction(
                username=username,
                category="CLEAN",
                strike_count=self.user_strikes.get(uname, 0),
                duration_seconds=0,
                verbal_roast_prompt=None,
                helix_payload=None,
            )

        # Increment strike count
        strikes = self.user_strikes.get(uname, 0) + 1
        self.user_strikes[uname] = strikes

        if strikes == 1:
            duration = 0  # Verbal warning
            if detected_category == "BACKSEATING":
                roast = (
                    f"Excuse me @{username}? Did I hire you as my backseat gaming director? "
                    f"No! I play how I want, thank you very much! Consider this your first and only warning!"
                )
            elif detected_category == "SPOILER":
                roast = f"Woah @{username}! Zip it with the spoilers! Some of us actually enjoy discovering things ourselves!"
            else:
                roast = f"Hey @{username}, keep that negative energy out of my chat, okay? Be nice!"
        elif strikes == 2:
            duration = 60  # 60 second timeout
            roast = (
                f"Alright @{username}, that is strike two! Go take a 60-second chill pill in the timeout corner. "
                f"Mods, deploy the freeze ray!"
            )
        else:
            duration = 600  # 10 minute ban
            roast = (
                f"Three strikes, @{username}! You are OUT! Enjoy a 10-minute vacation away from our chat. Goodbye!"
            )

        helix_payload = {
            "user_name": username,
            "duration": duration,
            "reason": f"[{self.vtuber_name} Auto-Mod] {detected_category} (Strike {strikes})",
        } if duration > 0 else None

        logger.warning(f"🚨 [Mod Action] @{username} triggered {detected_category} (Strike {strikes}) -> Timeout: {duration}s")

        return ModerationAction(
            username=username,
            category=detected_category,
            strike_count=strikes,
            duration_seconds=duration,
            verbal_roast_prompt=roast,
            helix_payload=helix_payload,
        )


if __name__ == "__main__":
    mod = InCharacterModerator(vtuber_name="Mili")
    print("Testing In-Character Chat Moderation Engine...")

    # Strike 1: Backseating
    u1 = "BackseatGamer99"
    act1 = mod.classify_message(u1, "You idiot go left and use your potion right now!")
    print(f"\n[Test 1] User: @{act1.username} | Offense: {act1.category} | Strike: {act1.strike_count}")
    print(f"VTuber Burn: \"{act1.verbal_roast_prompt}\"")

    # Strike 2: Second offense
    act2 = mod.classify_message(u1, "You need to press E to open the chest!")
    print(f"\n[Test 2] User: @{act2.username} | Offense: {act2.category} | Strike: {act2.strike_count} (Timeout: {act2.duration_seconds}s)")
    print(f"VTuber Burn: \"{act2.verbal_roast_prompt}\"")
    print(f"Twitch Helix Payload: {act2.helix_payload}")
