# src/open_llm_vtuber/studio/minigame_engine.py
"""
Interactive Stream Minigame & Audience Betting Engine.

Coordinates real-time transparent WebGL minigames (Boss Raids, Prediction Wagers, Chat Battles)
on the stream canvas. Parses viewer chat commands, calculates combat physics, updates health bars,
and triggers reactive commentary cues for the AI VTuber.
"""

import math
import random
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple
from loguru import logger


@dataclass
class RaidBossState:
    name: str = "Shadow Dragon Vorok"
    max_hp: int = 10000
    current_hp: int = 10000
    phase: int = 1
    is_defeated: bool = False
    active_shield: int = 0
    top_damage_dealers: Dict[str, int] = field(default_factory=dict)


@dataclass
class PredictionWager:
    question: str = "Will Mili defeat the Boss before the 5-minute timer?"
    pool_yes: int = 0
    pool_no: int = 0
    bettors: Dict[str, Tuple[str, int]] = field(default_factory=dict)  # user -> (side, points)
    is_open: bool = True


class StreamMinigameEngine:
    """
    Manages live stream audience minigames and betting markets.
    """

    def __init__(self):
        self.boss = RaidBossState()
        self.wager = PredictionWager()
        self.total_attacks = 0

    def parse_chat_command(self, username: str, message: str) -> Optional[Dict[str, any]]:
        """
        Parses viewer action commands like !attack, !shield, !bet.
        """
        parts = message.strip().split()
        if not parts:
            return None

        cmd = parts[0].lower()

        if cmd in ("!attack", "!hit", "!strike"):
            power = 100
            if len(parts) > 1 and parts[1].isdigit():
                power = min(500, max(50, int(parts[1])))
            return self.execute_boss_attack(username, power)

        elif cmd in ("!shield", "!defend"):
            return self.execute_party_shield(username)

        elif cmd == "!bet":
            if len(parts) >= 3:
                side = parts[1].lower()
                amount = int(parts[2]) if parts[2].isdigit() else 50
                return self.place_bet(username, side, amount)

        return None

    def execute_boss_attack(self, username: str, power: int) -> Dict[str, any]:
        """Calculates critical strike, applies damage to boss, updates leaderboard."""
        if self.boss.is_defeated:
            return {
                "action": "rejected",
                "attacker": username,
                "damage": 0,
                "is_critical": False,
                "boss_hp": 0,
                "boss_hp_ratio": 0.0,
                "boss_phase": self.boss.phase,
                "phase_changed": False,
                "is_defeated": True,
                "reason": "Boss already defeated!",
            }

        is_crit = random.random() < 0.20
        multiplier = 2.5 if is_crit else 1.0
        final_dmg = int(power * multiplier)

        # Apply damage
        self.boss.current_hp = max(0, self.boss.current_hp - final_dmg)
        self.boss.top_damage_dealers[username] = self.boss.top_damage_dealers.get(username, 0) + final_dmg
        self.total_attacks += 1

        # Check phase shift
        hp_ratio = self.boss.current_hp / self.boss.max_hp
        old_phase = self.boss.phase
        if hp_ratio <= 0.25:
            self.boss.phase = 3
        elif hp_ratio <= 0.60:
            self.boss.phase = 2

        if self.boss.current_hp == 0:
            self.boss.is_defeated = True

        return {
            "action": "attack",
            "attacker": username,
            "damage": final_dmg,
            "is_critical": is_crit,
            "boss_hp": self.boss.current_hp,
            "boss_hp_ratio": round(hp_ratio, 3),
            "boss_phase": self.boss.phase,
            "phase_changed": self.boss.phase != old_phase,
            "is_defeated": self.boss.is_defeated,
        }

    def execute_party_shield(self, username: str) -> Dict[str, any]:
        self.boss.active_shield += 250
        return {"action": "shield", "user": username, "total_shield": self.boss.active_shield}

    def place_bet(self, username: str, side: str, points: int) -> Dict[str, any]:
        if not self.wager.is_open:
            return {"action": "bet_failed", "reason": "Prediction market closed"}

        if side in ("yes", "win"):
            self.wager.pool_yes += points
            self.wager.bettors[username] = ("yes", points)
        else:
            self.wager.pool_no += points
            self.wager.bettors[username] = ("no", points)

        return {
            "action": "bet_placed",
            "user": username,
            "side": side,
            "points": points,
            "pool_yes": self.wager.pool_yes,
            "pool_no": self.wager.pool_no,
        }

    def generate_commentary_prompt(self, event: Dict[str, any]) -> Optional[str]:
        """
        Generates in-character hype or panic prompt for the AI VTuber
        when major battle events occur.
        """
        if event.get("action") != "attack":
            return None

        if event.get("is_defeated"):
            top_user = max(self.boss.top_damage_dealers.items(), key=lambda x: x[1])[0]
            return (
                f"[MINIGAME VICTORY] The chat defeated {self.boss.name}! "
                f"MVP attacker was @{top_user} with {self.boss.top_damage_dealers[top_user]} damage! "
                f"Celebrate excitedly with chat!"
            )

        if event.get("phase_changed"):
            return (
                f"[MINIGAME PHASE SHIFT] Boss has entered ENRAGED PHASE {event['boss_phase']}! "
                f"Boss HP is down to {int(event['boss_hp_ratio'] * 100)}%! "
                f"Shout at chat to keep attacking or deploy shields!"
            )

        if event.get("is_critical") and event.get("damage", 0) >= 300:
            return (
                f"[MINIGAME CRIT] Chatter @{event['attacker']} just landed a MASSIVE CRITICAL HIT "
                f"for {event['damage']} damage! Give them a quick shoutout!"
            )

        return None


if __name__ == "__main__":
    engine = StreamMinigameEngine()
    print("--- Simulating Live Stream Boss Raid Commands ---")

    # Viewer 1 attacks
    res1 = engine.parse_chat_command("DragonSlayer", "!attack 200")
    print(f"Attack 1: {res1['attacker']} dealt {res1['damage']} dmg (Crit={res1['is_critical']}) | Boss HP: {res1['boss_hp']}")

    # Viewer 2 bets
    res2 = engine.parse_chat_command("LuckyGamer", "!bet yes 150")
    print(f"Bet: {res2['user']} bet {res2['points']} on {res2['side']} | Pool Yes: {res2['pool_yes']}")

    # Mass attacks leading to phase change
    for i in range(12):
        engine.parse_chat_command(f"Chatter_{i}", "!attack 250")

    res_phase = engine.parse_chat_command("HeroAlex", "!attack 500")
    print(f"\nHero Attack: dealt {res_phase['damage']} dmg | Boss Phase: {res_phase['boss_phase']} | HP: {res_phase['boss_hp']}")
    cue = engine.generate_commentary_prompt(res_phase)
    if cue:
        print(f"\nAI VTuber Reaction Cue:\n\"{cue}\"")
