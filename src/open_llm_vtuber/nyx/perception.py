from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np


@dataclass
class VoiceTurn:
    transcript: str = ""
    interrupted: bool = False
    state: str = "listening"


class NyxPerception:
    """Perception layer for voice, interruption and Live2D state display."""

    def __init__(
        self,
        asr_engine: Any | None = None,
        tts_engine: Any | None = None,
        live2d_model: Any | None = None,
    ) -> None:
        self.asr_engine = asr_engine
        self.tts_engine = tts_engine
        self.live2d_model = live2d_model
        self.avatar_state = "idle"
        self.last_voice_turn = VoiceTurn()

    async def transcribe_audio(self, audio: np.ndarray | None) -> str:
        if audio is None:
            return ""
        if self.asr_engine is None:
            return "[asr not configured]"
        try:
            transcript = await self.asr_engine.async_transcribe_np(audio)
            self.last_voice_turn.transcript = transcript
            return transcript
        except Exception:
            return "[transcription failed]"

    async def speak(self, text: str) -> str:
        if not text:
            return ""
        if self.tts_engine is None:
            return text
        try:
            return await self.tts_engine.async_generate_audio(text)
        except Exception:
            return text

    def set_avatar_state(self, state: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.avatar_state = state
        payload: Dict[str, Any] = {"state": state, "details": details or {}}
        if self.live2d_model is not None and hasattr(self.live2d_model, "emo_map"):
            emotion_candidates = [
                key for key in self.live2d_model.emo_map if key.lower() in str(state).lower()
            ]
            if emotion_candidates:
                payload["emotion"] = emotion_candidates[0]
        return payload

    def handle_interrupt(self, interrupted: bool = True) -> VoiceTurn:
        self.last_voice_turn.interrupted = interrupted
        if interrupted:
            self.set_avatar_state("interrupt")
        else:
            self.set_avatar_state("listening")
        return self.last_voice_turn
