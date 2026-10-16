# src/open_llm_vtuber/audio/sfx_conductor.py
"""
Generative Sound FX & Precision Punchline Timing Conductor.

Analyzes outgoing LLM dialogue for comedic cues (<sfx:rimshot>, <sfx:vine_boom>, <sfx:airhorn>,
<sfx:record_scratch>, <sfx:bass_drop>), calculates syllable-level punchline durations,
and schedules sound effects to trigger with talk-show comedic timing while ducking BGM.
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from loguru import logger


@dataclass
class ScheduledSFXEvent:
    cue_name: str
    sfx_asset: str
    trigger_delay_sec: float
    duck_bgm_db: float
    volume: float
    context_phrase: str
    timestamp: float = field(default_factory=time.time)


class DynamicSFXConductor:
    """
    Sub-millisecond Comedic Timing & SFX Conductor.
    """

    SFX_REGISTRY = {
        "rimshot": "assets/audio/sfx/badum_tss.mp3",
        "vine_boom": "assets/audio/sfx/vine_boom.mp3",
        "record_scratch": "assets/audio/sfx/record_scratch.mp3",
        "airhorn": "assets/audio/sfx/airhorn_blast.mp3",
        "bass_drop": "assets/audio/sfx/inception_braam.mp3",
        "crickets": "assets/audio/sfx/awkward_crickets.mp3",
    }

    def __init__(self, words_per_minute: float = 160.0):
        self.wpm = words_per_minute
        self.seconds_per_word = 60.0 / words_per_minute

    def parse_dialogue_cues(self, text: str) -> Tuple[str, List[ScheduledSFXEvent]]:
        """
        Parses inline SFX tags like <sfx:rimshot> or [sfx:vine_boom].
        Calculates the audio timestamp when the preceding phrase ends.
        Returns: (clean_spoken_text, list_of_scheduled_events)
        """
        pattern = r"[<\[]sfx:(\w+)[>\]]"
        events: List[ScheduledSFXEvent] = []

        # Find all occurrences and their word positions
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        if not matches:
            return text, []

        clean_text = text
        offset = 0

        for m in matches:
            cue = m.group(1).lower()
            if cue not in self.SFX_REGISTRY:
                continue

            # Words spoken up to this tag
            preceding_text = text[:m.start()]
            clean_preceding = re.sub(pattern, "", preceding_text)
            words_count = len(clean_preceding.strip().split())

            # Syllable approximation: ~0.375s per English word at 160 WPM
            delay = max(0.1, words_count * self.seconds_per_word)

            event = ScheduledSFXEvent(
                cue_name=cue,
                sfx_asset=self.SFX_REGISTRY[cue],
                trigger_delay_sec=round(delay, 2),
                duck_bgm_db=-8.0,
                volume=0.85,
                context_phrase=clean_preceding.strip().split()[-3:] if words_count >= 3 else [clean_preceding.strip()],
            )
            events.append(event)
            logger.debug(f"[SFX Conductor] Scheduled '{cue}' at T+{event.trigger_delay_sec}s (After phrase: '{event.context_phrase}')")

        # Strip tags from spoken dialogue so TTS does not attempt to vocalize tags
        clean_text = re.sub(pattern, "", text).strip()
        return clean_text, events

    async def execute_timed_dispatch(self, event: ScheduledSFXEvent) -> Dict[str, any]:
        """Asynchronously waits for punchline timing and fires audio event."""
        await asyncio.sleep(event.trigger_delay_sec)
        logger.info(f"🔊 [SFX FIRE] Triggered '{event.cue_name}' ({event.sfx_asset}) with {event.duck_bgm_db}dB BGM ducking!")
        return {
            "type": "audio_sfx_trigger",
            "cue": event.cue_name,
            "asset": event.sfx_asset,
            "volume": event.volume,
            "duck_bgm_db": event.duck_bgm_db,
        }


if __name__ == "__main__":
    conductor = DynamicSFXConductor()
    sample_dialogue = (
        "You really thought I was going to lose that match? <sfx:vine_boom> "
        "Chat, I'm literally an advanced neural network! <sfx:rimshot>"
    )

    clean_speech, events = conductor.parse_dialogue_cues(sample_dialogue)
    print("--- Dynamic SFX Conductor Test ---")
    print(f"Original Input: {sample_dialogue}")
    print(f"Clean TTS Text: {clean_speech}")
    print(f"\nScheduled SFX Cues ({len(events)}):")
    for ev in events:
        print(f"  * Cue '{ev.cue_name}': Fires at T+{ev.trigger_delay_sec}s | Asset: {ev.sfx_asset}")
