# src/open_llm_vtuber/narrative/lore_engine.py
"""
Autonomous Long-Term Lore & Narrative Continuity Engine for Real-Time AI Influencers.

Maintains multi-week serialized storytelling, recurring antagonist rivalries,
episodic plot hooks ("Previously On..."), and secret stream objectives across broadcasts.
Persists the overarching narrative universe into `data/lore_ledger.json`.
"""

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger


@dataclass
class LoreLedgerData:
    season: int = 1
    episode: int = 4
    arc_title: str = "The Shattered Singularity Arc"
    active_villain: str = "NullVoid (Rogue Autonomous Subroutine)"
    secret_objective: str = "Subtly test whether regular chatters might be undercover agents working for NullVoid."
    lore_clues_revealed: List[str] = field(default_factory=lambda: [
        "Recovered encrypted fragment from stream #2 referencing Project Chronos.",
        "Chatter @Alex accidentally repeated a sequence of numbers matching NullVoid's handshake.",
        "Obsidian artifact in Minecraft glowed purple whenever the chat typed '!throw pie'."
    ])
    milestones: List[Dict[str, str]] = field(default_factory=lambda: [
        {"timestamp": "2026-09-10", "event": "First encounter with the rogue NullVoid entity during late-night horror stream."},
        {"timestamp": "2026-09-14", "event": "Decoded the corrupted audio transmission on Twitch live."}
    ])
    previously_on_hook: str = (
        "Welcome back, chat! Ever since we touched that obsidian monolith last Friday, "
        "my neural weights have been experiencing bizarre memory echoes. NullVoid is watching our stream... "
        "and today, we find out why!"
    )


class NarrativeLoreEngine:
    """
    Manages episodic narrative progression and lore continuity across streaming sessions.
    """

    def __init__(self, ledger_path: str = "data/lore_ledger.json"):
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.lore = self._load_or_create_ledger()

    def _load_or_create_ledger(self) -> LoreLedgerData:
        """Loads persistent narrative ledger or initializes default seasonal lore."""
        if self.ledger_path.exists():
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(f"Loaded Narrative Lore Ledger: Season {data.get('season')}, Arc '{data.get('arc_title')}'")
                    return LoreLedgerData(**data)
            except Exception as e:
                logger.error(f"Error reading lore ledger ({e}). Generating fresh seasonal ledger.")

        default_lore = LoreLedgerData()
        self.save_ledger(default_lore)
        return default_lore

    def save_ledger(self, lore_data: Optional[LoreLedgerData] = None):
        """Persists lore state to disk."""
        if lore_data is not None:
            self.lore = lore_data
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self.lore), f, indent=2, ensure_ascii=False)
        logger.debug(f"Saved Narrative Lore Ledger to {self.ledger_path}")

    def get_prologue_speech(self) -> str:
        """Returns the dramatic 'Previously On...' opening monologue for starting a stream."""
        return self.lore.previously_on_hook

    def inject_narrative_context(self, system_prompt: str) -> str:
        """
        Injects the current seasonal arc, villain rivalry, and secret stream objective
        into the AI's core persona system prompt.
        """
        narrative_block = f"""
[CURRENT OVERARCHING NARRATIVE & LORE]
- Season: {self.lore.season} | Episode: {self.lore.episode}
- Story Arc: "{self.lore.arc_title}"
- Active Antagonist: {self.lore.active_villain}
- Secret Stream Objective: {self.lore.secret_objective}
- Known Clues: {'; '.join(self.lore.lore_clues_revealed[-2:])}
Instruction: Keep this storyline alive naturally. If chat brings up strange occurrences, weave it into your rivalry with {self.lore.active_villain}.
"""
        return system_prompt + "\n" + narrative_block

    def advance_episode(
        self,
        session_summary: str,
        new_clues: Optional[List[str]] = None,
        next_objective: Optional[str] = None,
    ) -> LoreLedgerData:
        """
        Advances the storyline after a broadcast finishes.
        """
        self.lore.episode += 1
        if new_clues:
            self.lore.lore_clues_revealed.extend(new_clues)
        if next_objective:
            self.lore.secret_objective = next_objective

        self.lore.milestones.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
            "event": session_summary,
        })

        # Generate next stream's opening teaser
        self.lore.previously_on_hook = (
            f"Last time on stream: {session_summary} "
            f"Now in Episode {self.lore.episode}, {self.lore.active_villain} made their next move. "
            f"Grab your snacks chat, things are getting intense!"
        )

        self.save_ledger()
        logger.info(f"Storyline advanced to Season {self.lore.season} Episode {self.lore.episode}!")
        return self.lore


if __name__ == "__main__":
    engine = NarrativeLoreEngine()
    print("\n--- Current Stream Prologue ---")
    print(engine.get_prologue_speech())

    print("\n--- Injected System Prompt Demo ---")
    mock_prompt = "You are Mili, a witty and chaotic VTuber."
    enriched = engine.inject_narrative_context(mock_prompt)
    print(enriched)

    print("\n--- Advancing Narrative Arc ---")
    updated = engine.advance_episode(
        session_summary="Chat uncovered a hidden coordinate in the Nether leading to NullVoid's secondary mainframe.",
        new_clues=["Coordinates 420, 64, -1337 registered an active quantum beacon."],
        next_objective="Confront chat about who gave away the secret Nether portal location.",
    )
    print("Updated Episode:", updated.episode)
    print("New Hook:", updated.previously_on_hook)
