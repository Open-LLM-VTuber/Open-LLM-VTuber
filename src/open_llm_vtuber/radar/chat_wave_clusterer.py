# src/open_llm_vtuber/radar/chat_wave_clusterer.py
"""
Multi-Platform Chat Semantic Wave Clustering Engine.

Designed for high-traffic live streams (1,000 - 5,000+ msgs/min across Twitch, YouTube, and TikTok).
Groups incoming chat message torrents into dominant crowd sentiment waves in <15ms on CPU,
distilling raw chaotic chat spam into structured consensus signals for LLM reasoning.
"""

import math
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from loguru import logger


@dataclass
class ChatMessage:
    username: str
    text: str
    platform: str = "twitch"
    timestamp: float = field(default_factory=time.time)


@dataclass
class ChatSentimentWave:
    wave_id: int
    label: str  # e.g., "Humor / KEKW Surge", "Danger Warning", "Hype / GG"
    percentage: float
    message_count: int
    exemplars: List[str]
    representative_summary: str


class ChatWaveClusterer:
    """
    Sub-15ms Density-Based Semantic Chat Wave Clusterer.
    Ingests sliding time-window chat buffers and outputs top sentiment waves.
    """

    # Pre-compiled semantic topic anchors for ultra-fast zero-cost matching
    SEMANTIC_ANCHORS = {
        "laughter_humor": {
            "keywords": ["lmao", "lol", "kekw", "hahaha", "haha", "omega", "rofl", "xd", "cringe", "dead", "skull"],
            "label": "Humor / KEKW Surge",
            "summary": "Chat is erupting in laughter and finding the situation hilarious."
        },
        "danger_warning": {
            "keywords": ["behind", "watch out", "look out", "danger", "creeper", "ambush", "run", "trap", "back", "left", "right"],
            "label": "Urgent Danger Warning",
            "summary": "Chat is panicking and shouting warnings about an imminent threat."
        },
        "victory_hype": {
            "keywords": ["gg", "w", "huge", "pog", "poggers", "lets go", "clutch", "goat", "insane", "clean", "ez"],
            "label": "Triumph & Hype",
            "summary": "Chat is celebrating a victory, cheering, and chanting GG."
        },
        "defeat_sadness": {
            "keywords": ["f", "rip", "nooo", "sad", "oof", "unlucky", "choke", "thrown", "scammed", "pain"],
            "label": "Sympathy & Defeat (RIP / F)",
            "summary": "Chat is paying respects and commiserating over a failed play."
        },
        "confusion_query": {
            "keywords": ["what", "how", "why", "wait", "huh", "???", "?", "confused", "bug", "hax", "glitch"],
            "label": "Bewilderment & Questions",
            "summary": "Chat is thoroughly confused by what just happened."
        }
    }

    def __init__(self, window_seconds: float = 4.0, max_buffer_size: int = 300):
        self.window_seconds = window_seconds
        self.max_buffer_size = max_buffer_size
        self.buffer: List[ChatMessage] = []

    def add_message(self, username: str, text: str, platform: str = "twitch"):
        """Appends a new chatter message to the rolling buffer."""
        self.buffer.append(ChatMessage(username=username, text=text, platform=platform))
        if len(self.buffer) > self.max_buffer_size:
            self.buffer.pop(0)

    def _prune_buffer(self, now: float):
        cutoff = now - self.window_seconds
        self.buffer = [m for m in self.buffer if m.timestamp >= cutoff]

    def cluster_current_wave(self) -> List[ChatSentimentWave]:
        """
        Groups rolling messages into semantic waves.
        Returns sorted list of dominant sentiment waves.
        """
        t0 = time.perf_counter()
        now = time.time()
        self._prune_buffer(now)

        total_msgs = len(self.buffer)
        if total_msgs < 3:
            return []

        # Tokenize and score against semantic anchors
        wave_buckets: Dict[str, List[ChatMessage]] = defaultdict(list)
        unclustered: List[ChatMessage] = []

        for msg in self.buffer:
            tokens = set(re.findall(r"\b\w+\b", msg.text.lower()))
            matched_category = None

            for cat, meta in self.SEMANTIC_ANCHORS.items():
                if any(kw in tokens or kw in msg.text.lower() for kw in meta["keywords"]):
                    matched_category = cat
                    break

            if matched_category:
                wave_buckets[matched_category].append(msg)
            else:
                unclustered.append(msg)

        # Build output waves
        results: List[ChatSentimentWave] = []
        wave_idx = 1

        for cat, msgs in wave_buckets.items():
            count = len(msgs)
            if count == 0:
                continue
            pct = (count / total_msgs) * 100.0
            meta = self.SEMANTIC_ANCHORS[cat]
            exemplars = [m.text for m in msgs[:3]]

            results.append(ChatSentimentWave(
                wave_id=wave_idx,
                label=meta["label"],
                percentage=round(pct, 1),
                message_count=count,
                exemplars=exemplars,
                representative_summary=meta["summary"]
            ))
            wave_idx += 1

        # Sort by percentage descending
        results.sort(key=lambda w: w.percentage, reverse=True)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        logger.debug(f"Clustered {total_msgs} messages into {len(results)} waves in {latency_ms:.2f} ms")
        return results

    def format_crowd_consensus_prompt(self, waves: List[ChatSentimentWave]) -> str:
        """
        Formats top waves into a distilled LLM prompt injection.
        """
        if not waves:
            return ""

        top_wave = waves[0]
        summary_parts = [f"{w.percentage}% {w.label}" for w in waves[:2]]
        prompt = (
            f"[LIVE CHAT CROWD CONSENSUS ({', '.join(summary_parts)})]\n"
            f"Audience Sentiment: {top_wave.representative_summary}\n"
            f"Sample Chatter Reaction: \"{top_wave.exemplars[0]}\"\n"
            f"Instruction: React organically to this collective audience wave rather than answering individual chatters."
        )
        return prompt


if __name__ == "__main__":
    clusterer = ChatWaveClusterer(window_seconds=10.0)

    # Simulate an intense Minecraft creeper jump-scare death stream wave (50 messages)
    spam_batch = [
        ("alex99", "LMAO HE DIED"),
        ("pixel_queen", "KEKW NO WAY"),
        ("turbo_guy", "HAHAHAHA SO BAD"),
        ("chatter_4", "LOOK BEHIND YOU BRO"),
        ("gamer_x", "CREEPER BEHIND YOU RUN"),
        ("vibe_master", "WATCH OUT WATCH OUT"),
        ("lolz", "skull emoji xdddd"),
        ("steve", "F in the chat boys"),
        ("shadow", "RIP 50 levels of XP"),
        ("meme_lord", "KEKW classic"),
    ] * 5

    for user, text in spam_batch:
        clusterer.add_message(user, text)

    waves = clusterer.cluster_current_wave()
    print("\n--- Identified Chat Sentiment Waves ---")
    for w in waves:
        print(f"Wave #{w.wave_id} [{w.percentage}% - {w.message_count} msgs]: {w.label}")
        print(f"  Summary: {w.representative_summary}")
        print(f"  Exemplars: {w.exemplars}")

    print("\n--- Formatted LLM Prompt Injection ---")
    print(clusterer.format_crowd_consensus_prompt(waves))
