"""
Automated Stream Highlight & Viral Moment Detector.
Monitors chat surges, acoustic peaks, and game triggers to log clip windows.
"""
import time
import json
import os
from typing import Dict, Any, Optional
from loguru import logger


class HighlightDetector:
    """
    Evaluates continuous viral moment score:
    Score = w1*(Chat_rate) + w2*(Arousal) + w3*(Game_trigger)
    """
    def __init__(self, output_file: str = "highlights/highlight_log.jsonl"):
        self.output_file = output_file
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
        self.last_clip_time = 0.0
        self.min_clip_spacing = 30.0  # seconds between recorded highlights

    def evaluate_moment(
        self,
        event_name: str,
        arousal: float = 0.0,
        chat_msg_count_last_10s: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        now = time.time()
        if now - self.last_clip_time < self.min_clip_spacing:
            return None

        # Viral moment heuristics
        is_highlight = False
        reason = ""

        if event_name in ["STREAK_DEATH", "JUMPSCARE", "VICTORY"]:
            is_highlight = True
            reason = f"High-impact game trigger: {event_name}"
        elif arousal > 0.70:
            is_highlight = True
            reason = f"Extreme emotional arousal spike ({arousal:.2f})"
        elif chat_msg_count_last_10s >= 8:
            is_highlight = True
            reason = f"Chat velocity surge ({chat_msg_count_last_10s} msgs / 10s)"

        if is_highlight:
            self.last_clip_time = now
            clip_info = {
                "timestamp": now,
                "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
                "reason": reason,
                "event_name": event_name,
                "arousal": arousal,
                "suggested_clip_start": max(0, now - 15.0),
                "suggested_clip_end": now + 15.0,
                "metadata": metadata or {}
            }
            logger.info(f"🔥 VIRAL STREAM MOMENT DETECTED! Reason: {reason}")
            try:
                with open(self.output_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(clip_info) + "\n")
            except Exception as e:
                logger.error(f"Failed to log highlight: {e}")
            return clip_info
        return None
