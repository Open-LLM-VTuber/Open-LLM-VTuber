from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..config_manager.main import Config
from ..config_manager.utils import read_yaml, validate_config
from ..service_context import ServiceContext
from .runtime import NyxRuntime


@dataclass
class NyxSession:
    """Bridge between Nyx runtime and Open-LLM-VTuber ServiceContext."""

    runtime: NyxRuntime
    service_context: Optional[ServiceContext] = None

    @classmethod
    def from_service_context(cls, service_context: ServiceContext) -> "NyxSession":
        runtime = NyxRuntime(allowed_roots=["."])
        runtime.perception = runtime.perception.__class__(
            asr_engine=getattr(service_context, "asr_engine", None),
            tts_engine=getattr(service_context, "tts_engine", None),
            live2d_model=getattr(service_context, "live2d_model", None),
        )
        return cls(runtime=runtime, service_context=service_context)

    @staticmethod
    async def from_config_file(config_path: str) -> "NyxSession":
        config_data = read_yaml(config_path)
        config = validate_config(config_data)
        service_context = ServiceContext()
        await service_context.load_from_config(config)
        return NyxSession.from_service_context(service_context)

    async def listen(self, audio: Any | None = None, text: str | None = None) -> str:
        return await self.runtime.listen(audio=audio, text=text)

    async def speak(self, text: str) -> str:
        return await self.runtime.speak(text)

    def update_avatar_state(self, state: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = self.runtime.set_avatar_state(state, details)
        if self.service_context and self.service_context.live2d_model is not None:
            model = self.service_context.live2d_model
            if hasattr(model, "extract_emotion") and "emotion" in payload:
                payload["emotion_values"] = model.extract_emotion(f"[{payload['emotion']}]")
        return payload

    def snapshot(self) -> Dict[str, Any]:
        return self.runtime.snapshot()
