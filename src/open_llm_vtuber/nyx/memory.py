from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class MemoryEntry:
    """Generic memory record stored in one of Nyx's memory tiers."""

    tier: str
    content: str
    metadata: dict = field(default_factory=dict)


class NyxMemory:
    """Stores working, episodic and semantic memory for the local agent."""

    def __init__(self) -> None:
        self.working: List[MemoryEntry] = []
        self.episodic: List[MemoryEntry] = []
        self.semantic: List[MemoryEntry] = []

    def add_working(self, content: str, **metadata) -> None:
        self.working.append(MemoryEntry("working", content, metadata))

    def add_episodic(self, content: str, **metadata) -> None:
        self.episodic.append(MemoryEntry("episodic", content, metadata))

    def add_semantic(self, content: str, **metadata) -> None:
        self.semantic.append(MemoryEntry("semantic", content, metadata))

    def relevant_context(self, query: str, limit: int = 5) -> List[str]:
        if limit == 0:
            return []
        if limit < 0:
            raise ValueError("limit must be non-negative")

        haystacks = [self.working, self.episodic, self.semantic]
        matches: List[str] = []
        query_lower = query.lower()
        for tier in haystacks:
            for item in tier:
                if query_lower in item.content.lower():
                    matches.append(f"[{item.tier}] {item.content}")
                    if len(matches) >= limit:
                        return matches
        return matches
