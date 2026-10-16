"""
Nova AI Influencer — Proactive Stream Intelligence Loop
========================================================
Background asyncio loop that:
1. Detects silence and triggers proactive speech after configurable idle time
2. Monitors chat activity patterns for context-aware interjections
3. Tracks stream time for milestone announcements ("we've been streaming for 1 hour!")
4. Optionally polls screen for visual context (game state awareness)
5. Generates time-aware commentary (morning/evening/weekend checks)

Usage: Import and start from server startup. Sends 'ai-speak-signal' via WebSocket.
"""

import asyncio
import json
import time
import datetime
import random
from typing import Optional, Callable
from loguru import logger


# Default thresholds
DEFAULT_IDLE_THRESHOLD_SEC = 45       # Speak proactively after 45s silence
STREAM_MILESTONE_INTERVALS = [        # Minutes at which to inject milestone moments
    30, 60, 90, 120, 180
]


class ProactiveStreamIntelligence:
    """
    Autonomous background intelligence loop for the AI influencer.
    Enables Nova to speak proactively, react to time/context, and maintain
    a live stream presence without waiting for user input.
    """

    def __init__(
        self,
        idle_threshold_sec: float = DEFAULT_IDLE_THRESHOLD_SEC,
        enabled: bool = True
    ):
        self.idle_threshold_sec = idle_threshold_sec
        self.enabled = enabled
        self.stream_start_time = time.time()
        self.last_interaction_time = time.time()
        self.milestones_announced = set()
        self._running = False
        self._trigger_callback: Optional[Callable] = None
        logger.info(
            f"ProactiveStreamIntelligence initialized. "
            f"Idle threshold: {idle_threshold_sec}s, enabled: {enabled}"
        )

    def set_trigger_callback(self, callback: Callable) -> None:
        """
        Set the async callback that will be called to trigger AI speech.
        The callback should accept a reason string.
        """
        self._trigger_callback = callback

    def record_interaction(self) -> None:
        """Call this whenever the user or AI generates speech to reset idle timer."""
        self.last_interaction_time = time.time()

    def get_idle_seconds(self) -> float:
        """Returns how many seconds the stream has been silent."""
        return time.time() - self.last_interaction_time

    def get_stream_minutes(self) -> float:
        """Returns total stream runtime in minutes."""
        return (time.time() - self.stream_start_time) / 60.0

    def _get_time_aware_context(self) -> str:
        """Returns a time-aware context hint for proactive speech generation."""
        now = datetime.datetime.now()
        hour = now.hour
        day = now.strftime("%A")
        stream_mins = int(self.get_stream_minutes())

        if hour < 6:
            time_context = "It's extremely late at night / early morning. The dedicated night owls are here."
        elif hour < 12:
            time_context = f"It's {now.strftime('%I %p')} on {day}. Morning energy."
        elif hour < 17:
            time_context = f"It's {now.strftime('%I %p')} on {day}. Afternoon vibes."
        elif hour < 21:
            time_context = f"It's {now.strftime('%I %p')} on {day}. Peak streaming hours, chat should be active."
        else:
            time_context = "It's late evening. The most dedicated fans are here."

        return f"{time_context} Stream has been running for {stream_mins} minutes."

    def _check_milestone(self, stream_minutes: float) -> Optional[str]:
        """Check if a stream milestone has been reached."""
        for milestone_min in STREAM_MILESTONE_INTERVALS:
            if stream_minutes >= milestone_min and milestone_min not in self.milestones_announced:
                self.milestones_announced.add(milestone_min)
                if milestone_min == 60:
                    return f"ONE HOUR MILESTONE! We've been streaming for exactly one hour."
                elif milestone_min == 30:
                    return f"Thirty minute mark! Stream's warming up."
                else:
                    return f"{milestone_min} minutes of streaming!"
        return None

    async def run_loop(self) -> None:
        """
        Main background loop. Checks for idle time and milestone triggers.
        Should be run as an asyncio task alongside the server.
        """
        self._running = True
        logger.info("ProactiveStreamIntelligence loop started.")

        while self._running:
            await asyncio.sleep(10)  # Check every 10 seconds

            if not self.enabled or not self._trigger_callback:
                continue

            stream_minutes = self.get_stream_minutes()
            idle_seconds = self.get_idle_seconds()

            # Priority 1: Stream milestones
            milestone = self._check_milestone(stream_minutes)
            if milestone:
                logger.info(f"Stream milestone reached: {milestone}")
                reason = f"MILESTONE: {milestone}"
                await self._trigger_callback(reason)
                self.record_interaction()
                continue

            # Priority 2: Idle threshold
            if idle_seconds >= self.idle_threshold_sec:
                time_context = self._get_time_aware_context()

                # Randomize which type of proactive content to generate
                proactive_types = [
                    "hot_take",
                    "chat_callout",
                    "stream_observation",
                    "random_trivia",
                ]
                chosen = random.choice(proactive_types)
                reason = f"IDLE_{chosen.upper()}|{time_context}"
                logger.info(
                    f"Idle threshold reached ({idle_seconds:.0f}s). "
                    f"Triggering proactive speech: {chosen}"
                )
                await self._trigger_callback(reason)
                self.record_interaction()  # Reset timer after triggering

    def stop(self) -> None:
        """Stop the background loop."""
        self._running = False
        logger.info("ProactiveStreamIntelligence loop stopped.")


# Singleton instance
_proactive_intelligence: Optional[ProactiveStreamIntelligence] = None


def get_proactive_intelligence(idle_threshold_sec: float = 45.0) -> ProactiveStreamIntelligence:
    """Get or create the global proactive intelligence instance."""
    global _proactive_intelligence
    if _proactive_intelligence is None:
        _proactive_intelligence = ProactiveStreamIntelligence(
            idle_threshold_sec=idle_threshold_sec
        )
    return _proactive_intelligence
