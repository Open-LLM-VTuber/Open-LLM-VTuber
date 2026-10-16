"""
Nova AI Influencer — Persistent Fan Memory Engine
===================================================
Zero-cost SQLite-based episodic memory for recognizing regular viewers,
remembering conversation topics across sessions, and building parasocial depth.
Uses keyword extraction without external APIs or vector databases.
"""

import sqlite3
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger


DB_PATH = Path("data/nova_fan_memory.db")


@dataclass
class FanMemory:
    user_id: str
    username: str
    facts: List[str]
    last_seen: float
    total_interactions: int
    emotional_tone: str  # 'hype', 'chill', 'salty', 'academic', 'friendly'
    memorable_moments: List[str]


class FanMemoryEngine:
    """
    Lightweight SQLite fan memory system.
    Remembers facts about regular users across stream sessions.
    Zero external API cost — fully local.
    """

    def __init__(self, db_path: Path = DB_PATH):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._init_schema()
        logger.info(f"FanMemoryEngine initialized at {db_path}")

    def _init_schema(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS fan_memories (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    facts TEXT DEFAULT '[]',
                    last_seen REAL DEFAULT 0,
                    total_interactions INTEGER DEFAULT 0,
                    emotional_tone TEXT DEFAULT 'friendly',
                    memorable_moments TEXT DEFAULT '[]',
                    created_at REAL DEFAULT 0
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS stream_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    description TEXT,
                    timestamp REAL,
                    user_id TEXT
                )
            """)

    def get_or_create_fan(self, user_id: str, username: str = "") -> FanMemory:
        """Retrieve or create a fan profile."""
        row = self.conn.execute(
            "SELECT * FROM fan_memories WHERE user_id = ?", (user_id,)
        ).fetchone()

        if row:
            return FanMemory(
                user_id=row[0],
                username=row[1],
                facts=json.loads(row[2]),
                last_seen=row[3],
                total_interactions=row[4],
                emotional_tone=row[5],
                memorable_moments=json.loads(row[6])
            )
        else:
            now = time.time()
            with self.conn:
                self.conn.execute(
                    """INSERT INTO fan_memories 
                    (user_id, username, facts, last_seen, total_interactions, 
                     emotional_tone, memorable_moments, created_at)
                    VALUES (?, ?, '[]', ?, 0, 'friendly', '[]', ?)""",
                    (user_id, username or user_id, now, now)
                )
            return FanMemory(
                user_id=user_id,
                username=username or user_id,
                facts=[],
                last_seen=now,
                total_interactions=0,
                emotional_tone="friendly",
                memorable_moments=[]
            )

    def record_interaction(
        self,
        user_id: str,
        username: str,
        message: str,
        ai_response: str
    ) -> None:
        """Record an interaction and extract memorable facts."""
        fan = self.get_or_create_fan(user_id, username)
        new_facts = self._extract_facts(message, fan.facts)

        # Detect tone from message
        tone = self._detect_tone(message)

        with self.conn:
            self.conn.execute(
                """UPDATE fan_memories 
                SET last_seen = ?, total_interactions = total_interactions + 1,
                    facts = ?, emotional_tone = ?
                WHERE user_id = ?""",
                (time.time(), json.dumps((fan.facts + new_facts)[-20:]), tone, user_id)
            )

    def _extract_facts(self, message: str, existing_facts: List[str]) -> List[str]:
        """Lightweight keyword-based fact extraction without AI APIs."""
        new_facts = []
        lower = message.lower()

        # Occupation/interest patterns
        patterns = [
            (r"i (?:am|'m) (?:a|an) ([\w\s]+)", "occupation"),
            (r"i (?:work|study) (?:as|in|at) ([\w\s]+)", "work/study"),
            (r"i (?:love|hate|play|use|watch|like) ([\w\s]+)", "preference"),
            (r"my (?:name|username|nickname) is ([\w\s]+)", "name"),
            (r"i'm from ([\w\s,]+)", "location"),
            (r"i've been (?:watching|following) (?:you|nova) (?:for|since) ([\w\s]+)", "loyalty"),
        ]

        for pattern, category in patterns:
            match = re.search(pattern, lower)
            if match:
                fact = f"{category}: {match.group(1).strip()}"
                if fact not in existing_facts and len(fact) < 80:
                    new_facts.append(fact)

        return new_facts[:3]  # Max 3 new facts per message

    def _detect_tone(self, message: str) -> str:
        """Detect fan tone from message."""
        lower = message.lower()
        if any(w in lower for w in ["pog", "hype", "lets go", "poggers", "w"]):
            return "hype"
        elif any(w in lower for w in ["actually", "technically", "according to", "research"]):
            return "academic"
        elif any(w in lower for w in ["ugh", "lag", "bad", "hate", "annoying"]):
            return "salty"
        elif any(w in lower for w in ["chill", "relaxing", "nice", "cozy"]):
            return "chill"
        return "friendly"

    def add_memorable_moment(self, user_id: str, moment: str) -> None:
        """Record a notable moment involving this fan."""
        fan = self.get_or_create_fan(user_id)
        moments = (fan.memorable_moments + [moment])[-10:]  # Keep last 10
        with self.conn:
            self.conn.execute(
                "UPDATE fan_memories SET memorable_moments = ? WHERE user_id = ?",
                (json.dumps(moments), user_id)
            )

    def get_context_for_user(self, user_id: str, username: str = "") -> str:
        """
        Returns an injectable context string for the LLM system prompt.
        Call this before generating a response to inject fan recognition.
        """
        fan = self.get_or_create_fan(user_id, username)

        if fan.total_interactions == 0:
            return f"[NEW VIEWER: @{username or user_id} — first time chatting with you]"

        days_since = (time.time() - fan.last_seen) / 86400

        context_parts = [f"[RETURNING FAN: @{fan.username}"]
        context_parts.append(f"Visits: {fan.total_interactions}")

        if days_since > 7:
            context_parts.append(f"Last seen: {int(days_since)} days ago")

        if fan.facts:
            context_parts.append(f"Known facts: {'; '.join(fan.facts[:5])}")

        if fan.memorable_moments:
            context_parts.append(f"Shared history: {fan.memorable_moments[-1]}")

        context_parts.append(f"Vibe: {fan.emotional_tone}]")

        return " | ".join(context_parts)

    def get_top_fans(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Returns the most engaged fans for loyalty recognition."""
        rows = self.conn.execute(
            "SELECT user_id, username, total_interactions, emotional_tone FROM fan_memories ORDER BY total_interactions DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [{"user_id": r[0], "username": r[1], "interactions": r[2], "tone": r[3]} for r in rows]

    def log_stream_event(self, event_type: str, description: str, user_id: str = "") -> None:
        """Log significant stream events (raids, donations, milestones)."""
        with self.conn:
            self.conn.execute(
                "INSERT INTO stream_events (event_type, description, timestamp, user_id) VALUES (?, ?, ?, ?)",
                (event_type, description, time.time(), user_id)
            )

    def close(self):
        self.conn.close()


# Global singleton for easy access
_fan_engine: Optional[FanMemoryEngine] = None


def get_fan_engine() -> FanMemoryEngine:
    """Get or create the global fan memory engine."""
    global _fan_engine
    if _fan_engine is None:
        _fan_engine = FanMemoryEngine()
    return _fan_engine
