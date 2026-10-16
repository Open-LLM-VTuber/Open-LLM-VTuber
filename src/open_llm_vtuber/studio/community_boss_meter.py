# src/open_llm_vtuber/studio/community_boss_meter.py
"""
Autonomous Stream Sub-Goal & Community Boss Meter.

Gamifies stream audience engagement by replacing static subscription/tip goals
with an interactive on-screen Community Raid Boss Health Bar:
- Damage inflicted in real time by chat messages, bits, donations, and stream raids
- Dispatches screen shake, particle damage numbers, and boss phase shifts
- Triggers celebratory victory fanfare and community loyalty payouts upon defeat
- Sub-millisecond state execution on pure CPU.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any
from loguru import logger


@dataclass
class BossMeterState:
    boss_name: str
    max_hp: int
    current_hp: int
    hp_percent: float
    is_defeated: bool
    last_attacker: str
    total_attacks: int
    phase: int  # 1: 100-66%, 2: 66-33%, 3: <33% Enrage


@dataclass
class BossDamageEvent:
    attacker: str
    damage: int
    event_type: str
    new_hp: int
    hp_percent: float
    phase_changed: bool
    is_defeated: bool
    screen_fx: Dict[str, Any]
    speech_prompt: Optional[str] = None


class CommunityBossMeterEngine:
    """
    Real-Time Community Boss Health Meter and Victory Director.
    """

    def __init__(self, boss_name: str = "The Lag Shadow Demon", max_hp: int = 5000):
        self.boss_name = boss_name
        self.max_hp = max_hp
        self.current_hp = max_hp
        self.is_defeated = False
        self.total_attacks = 0
        self.current_phase = 1

    def register_damage(
        self, attacker: str, event_type: str, count: int = 1
    ) -> BossDamageEvent:
        """
        Applies damage based on community event type:
        - CHAT_MSG: 1 damage per message
        - BITS: 15 damage per 100 bits
        - SUPERCHAT: 20 damage per dollar ($5 = 100 damage)
        - RAID: 3 damage per viewer
        """
        if self.is_defeated:
            return BossDamageEvent(
                attacker=attacker,
                damage=0,
                event_type=event_type,
                new_hp=0,
                hp_percent=0.0,
                phase_changed=False,
                is_defeated=True,
                screen_fx={"action": "NONE"},
                speech_prompt=None,
            )

        self.total_attacks += 1
        damage = 1
        et = event_type.upper()

        if et == "CHAT_MSG":
            damage = max(1, count)
        elif et == "BITS":
            damage = max(1, int(count * 0.15))
        elif et == "SUPERCHAT":
            damage = max(5, int(count * 20))
        elif et == "RAID":
            damage = max(10, int(count * 3))

        self.current_hp = max(0, self.current_hp - damage)
        hp_pct = round((self.current_hp / float(self.max_hp)) * 100.0, 1)

        # Evaluate Phase
        prev_phase = self.current_phase
        if hp_pct > 66.0:
            self.current_phase = 1
        elif hp_pct > 33.0:
            self.current_phase = 2
        else:
            self.current_phase = 3
        phase_changed = (self.current_phase != prev_phase)

        just_defeated = (self.current_hp == 0 and not self.is_defeated)
        if just_defeated:
            self.is_defeated = True
            logger.info(f"[BossMeter] ★ BOSS DEFEATED! Final blow by @{attacker}!")

        # Screen FX payload
        screen_fx = {
            "action": "BOSS_DEFEAT_FANFARE" if just_defeated else "BOSS_DAMAGE_NUMBER",
            "damage": damage,
            "hp_percent": hp_pct,
            "attacker": attacker,
            "shake_intensity": 8.0 if just_defeated else min(4.0, damage / 20.0),
        }

        # Prompt for LLM
        prompt = None
        if just_defeated:
            prompt = (
                f"[STREAM MILESTONE: RAID BOSS DEFEATED!]\n"
                f"The community just landed the final blow on {self.boss_name}! Final strike by @{attacker}! "
                f"Celebrate with massive hype, cheer with chat, and award everyone 250 loyalty Sparkles!"
            )
        elif phase_changed and self.current_phase == 3:
            prompt = (
                f"[BOSS ENRAGE PHASE 3]\n"
                f"{self.boss_name} is below 33% HP and glowing red! Urge chat to spam attacks and finish it off!"
            )

        return BossDamageEvent(
            attacker=attacker,
            damage=damage,
            event_type=et,
            new_hp=self.current_hp,
            hp_percent=hp_pct,
            phase_changed=phase_changed,
            is_defeated=self.is_defeated,
            screen_fx=screen_fx,
            speech_prompt=prompt,
        )

    def get_state(self) -> BossMeterState:
        return BossMeterState(
            boss_name=self.boss_name,
            max_hp=self.max_hp,
            current_hp=self.current_hp,
            hp_percent=round((self.current_hp / float(self.max_hp)) * 100.0, 1),
            is_defeated=self.is_defeated,
            last_attacker="None",
            total_attacks=self.total_attacks,
            phase=self.current_phase,
        )


if __name__ == "__main__":
    meter = CommunityBossMeterEngine(max_hp=500)
    ev1 = meter.register_damage("ChatSpammer", "CHAT_MSG", count=25)
    print(f"Attack 1: Dmg={ev1.damage} | HP={ev1.new_hp}/{meter.max_hp} ({ev1.hp_percent}%)")

    ev2 = meter.register_damage("MegaDonor", "SUPERCHAT", count=25)  # $25 -> 500 dmg
    print(f"Attack 2 (Fatal): Defeated={ev2.is_defeated} | Prompt:\n{ev2.speech_prompt}")
