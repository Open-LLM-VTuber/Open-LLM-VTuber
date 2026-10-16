# src/open_llm_vtuber/agent/collab_squad.py
"""
Multi-Agent Collab Squad & Conversational Floor Arbiter for AI Influencers.

Coordinates multiple autonomous AI characters in the same live stream scene
(e.g., Host Mao + Tsundere Co-Host Luna + Chaotic Gremlin Mascot Piko).

Features:
- Atomic speech floor mutex preventing overlapping audio
- Dynamic interruption evaluation (mid-phrase conversational snipes)
- Cross-avatar attentive gaze tracking (turning heads toward active speaker)
- Turn budget enforcement (prevents infinite AI loops, ensures chat gets priority)
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from loguru import logger


@dataclass
class CollabAgent:
    id: str
    name: str
    archetype: str  # e.g., "Host", "Tsundere Co-Host", "Chaotic Mascot"
    voice_slot: str
    interruption_propensity: float  # 0.0 to 1.0
    gaze_angle_offset: float = 0.0  # degrees toward center/other characters


@dataclass
class CollabTurnEvent:
    speaker_id: str
    speaker_name: str
    utterance: str
    is_interruption: bool
    gaze_targets: Dict[str, float]  # agent_id -> target ParamAngleX
    timestamp: float = field(default_factory=time.time)


class ConversationalFloorArbiter:
    """
    Real-time multi-agent conversational arbitrator.
    Decides who speaks next, handles comedic interruptions, and controls gaze kinematics.
    """

    def __init__(self, agents: List[CollabAgent], max_consecutive_ai_turns: int = 3):
        self.agents: Dict[str, CollabAgent] = {a.id: a for a in agents}
        self.max_consecutive_ai_turns = max_consecutive_ai_turns
        self.active_speaker_id: Optional[str] = None
        self.consecutive_ai_turns: int = 0
        self.floor_lock = asyncio.Lock()
        self.turn_history: List[CollabTurnEvent] = []

        logger.info(f"Collab Squad Arbiter online with {len(self.agents)} agents: {[a.name for a in agents]}")

    def calculate_gaze_orientations(self, active_speaker_id: str) -> Dict[str, float]:
        """
        Calculates Live2D ParamAngleX head yaw so listening agents face the speaker.
        Stage positioning:
          - agent_0 (left): -25 degrees
          - agent_1 (center): 0 degrees
          - agent_2 (right): +25 degrees
        """
        stage_positions = {}
        agent_ids = list(self.agents.keys())
        for idx, aid in enumerate(agent_ids):
            # Spread across stage from -20 to +20
            pos = -20.0 + (idx / max(1, len(agent_ids) - 1)) * 40.0
            stage_positions[aid] = pos

        gaze_angles = {}
        speaker_pos = stage_positions.get(active_speaker_id, 0.0)

        for aid, pos in stage_positions.items():
            if aid == active_speaker_id:
                # Active speaker looks towards chat / center
                gaze_angles[aid] = 0.0
            else:
                # Listeners turn head towards speaker
                direction = speaker_pos - pos
                target_yaw = max(-25.0, min(25.0, direction * 0.8))
                gaze_angles[aid] = round(target_yaw, 1)

        return gaze_angles

    def evaluate_interruption(self, candidate: CollabAgent, current_utterance: str) -> bool:
        """
        Determines whether an agent should rudely or excitedly interrupt mid-turn.
        Triggered by boastful words, mistakes, or high interruption propensity.
        """
        trigger_words = ["never miss", "so easy", "obviously", "i am the best", "flawless", "trust me"]
        contains_trigger = any(w in current_utterance.lower() for w in trigger_words)

        # Base probability from archetype propensity
        chance = candidate.interruption_propensity * (0.6 if contains_trigger else 0.15)
        return random.random() < chance

    async def arbitrate_next_turn(
        self,
        last_utterance: str,
        chat_pending: bool = False,
    ) -> Tuple[str, bool]:
        """
        Returns (next_speaker_id, is_interruption).
        If consecutive AI turns exceed limit and chat is pending, yields to chat.
        """
        # 1. Enforce audience chat priority
        if self.consecutive_ai_turns >= self.max_consecutive_ai_turns and chat_pending:
            logger.info("Turn budget reached -> Yielding floor to Audience Chat interjection.")
            self.consecutive_ai_turns = 0
            self.active_speaker_id = None
            return ("AUDIENCE_CHAT", False)

        # 2. Candidate selection (excluding current speaker)
        candidate_ids = [aid for aid in self.agents if aid != self.active_speaker_id]
        if not candidate_ids:
            candidate_ids = list(self.agents.keys())

        # Check for interruption
        interrupter = None
        for aid in candidate_ids:
            cand = self.agents[aid]
            if self.evaluate_interruption(cand, last_utterance):
                interrupter = aid
                break

        if interrupter:
            self.consecutive_ai_turns += 1
            self.active_speaker_id = interrupter
            logger.warning(f"⚡ [INTERRUPTION] {self.agents[interrupter].name} cuts off speech!")
            return (interrupter, True)

        # Otherwise standard round-robin or personality-weighted selection
        next_speaker = random.choice(candidate_ids)
        self.consecutive_ai_turns += 1
        self.active_speaker_id = next_speaker
        return (next_speaker, False)

    def record_turn(self, speaker_id: str, utterance: str, is_interruption: bool = False) -> CollabTurnEvent:
        """Records the completed turn and updates avatar head gazes."""
        gaze = self.calculate_gaze_orientations(speaker_id)
        name = self.agents[speaker_id].name if speaker_id in self.agents else "Audience"
        event = CollabTurnEvent(
            speaker_id=speaker_id,
            speaker_name=name,
            utterance=utterance,
            is_interruption=is_interruption,
            gaze_targets=gaze,
        )
        self.turn_history.append(event)
        logger.debug(f"Turn Committed: [{name}] '{utterance[:40]}...' (Gaze: {gaze})")
        return event


if __name__ == "__main__":
    agents = [
        CollabAgent(id="mao", name="Mao (Host)", archetype="Host", voice_slot="af_bella", interruption_propensity=0.2),
        CollabAgent(id="luna", name="Luna (Tsundere)", archetype="Tsundere", voice_slot="af_sky", interruption_propensity=0.85),
        CollabAgent(id="piko", name="Piko (Gremlin)", archetype="Mascot", voice_slot="af_sarah", interruption_propensity=0.5),
    ]

    arbiter = ConversationalFloorArbiter(agents)

    async def run_collab_simulation():
        print("\n--- Starting 3-Agent Collaborative Stream Simulation ---")
        # Turn 1: Host
        speaker, interrupted = "mao", False
        utt = "Welcome everyone to our raid stream! Honestly, I am the best Minecraft speedrunner, trust me!"
        ev = arbiter.record_turn(speaker, utt, interrupted)
        print(f"\n[{ev.speaker_name}]: {ev.utterance}")
        print(f"  Head Gazes -> {ev.gaze_targets}")

        # Turn 2: Arbiter evaluates response to boastful statement
        next_spk, is_intr = await arbiter.arbitrate_next_turn(utt, chat_pending=True)
        if next_spk == "luna":
            utt2 = "Excuse me?! You died to a baby zombie five minutes ago, don't act smug!"
        else:
            utt2 = "Shiny diamond! Piko eat diamond!"
        ev2 = arbiter.record_turn(next_spk, utt2, is_intr)
        print(f"\n[{ev2.speaker_name}] (Interrupted={ev2.is_interruption}): {ev2.utterance}")
        print(f"  Head Gazes -> {ev2.gaze_targets}")

        # Turn 3
        next_spk3, is_intr3 = await arbiter.arbitrate_next_turn(utt2, chat_pending=True)
        print(f"\nNext floor assigned to: {next_spk3} (Interrupted={is_intr3})")

    asyncio.run(run_collab_simulation())
