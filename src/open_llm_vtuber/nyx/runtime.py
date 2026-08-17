from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .actions import ActionRegistry, LocalAction, monitor_service, mqtt_message, read_file, shell_command, write_file
from .audit import AuditLog
from .memory import NyxMemory
from .perception import NyxPerception
from .security import NyxSecurityGuard, PermissionDeniedError, SecurityPolicy
from .state import NyxState, NyxStatus


@dataclass
class NyxRuntime:
    """Main runtime orchestrating the Nyx local agent."""

    allowed_roots: List[str] = field(default_factory=lambda: ["."])
    memory: NyxMemory = field(default_factory=NyxMemory)
    audit: AuditLog = field(default_factory=AuditLog)
    security: NyxSecurityGuard = field(default_factory=NyxSecurityGuard)
    registry: ActionRegistry = field(default_factory=ActionRegistry)
    status: NyxStatus = field(default_factory=NyxStatus)
    perception: NyxPerception = field(default_factory=NyxPerception)

    def __post_init__(self) -> None:
        self.security = NyxSecurityGuard(SecurityPolicy(allowed_roots=self.allowed_roots))
        self.registry.register(LocalAction("read_file", "Read a local file", read_file))
        self.registry.register(LocalAction("write_file", "Write a local file", write_file))
        self.registry.register(LocalAction("run_command", "Run a whitelisted command", shell_command))
        self.registry.register(LocalAction("monitor_service", "Check a local service status", monitor_service))
        self.registry.register(LocalAction("send_message", "Send a local message to another agent", mqtt_message))
        self.perception = NyxPerception()
        self.status.working_directory = "."
        self.status.transition(NyxState.LISTENING, "Nyx is ready to listen and act under policy")

    def remember(self, content: str, tier: str = "working", **metadata) -> None:
        if tier == "working":
            self.memory.add_working(content, **metadata)
        elif tier == "episodic":
            self.memory.add_episodic(content, **metadata)
        elif tier == "semantic":
            self.memory.add_semantic(content, **metadata)
        else:
            raise ValueError(f"Unsupported memory tier '{tier}'")

    def search_context(self, query: str, limit: int = 5) -> List[str]:
        return self.memory.relevant_context(query, limit=limit)

    async def listen(self, audio: Any | None = None, text: str | None = None) -> str:
        self.status.transition(NyxState.LISTENING, "Nyx is listening")
        transcript = text or ""
        if audio is not None:
            transcript = await self.perception.transcribe_audio(audio)
        if transcript:
            self.memory.add_working(transcript, source="voice")
        return transcript

    async def speak(self, text: str) -> str:
        self.status.transition(NyxState.THINKING, "Nyx is generating a response")
        audio_path = await self.perception.speak(text)
        self.memory.add_episodic(f"Spoke: {text}", source="assistant")
        self.status.transition(NyxState.LISTENING, "Nyx is ready again")
        return audio_path

    def set_avatar_state(self, state: str, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return self.perception.set_avatar_state(state, details)

    def execute_action(self, name: str, **kwargs: Any) -> Any:
        if self.status.locked or self.status.validation_required:
            raise PermissionDeniedError(
                f"Action '{name}' denied while Nyx is locked or awaiting validation"
            )
        self.status.transition(NyxState.ACTING, f"Executing action: {name}")
        if "path" in kwargs and name in {"read_file", "write_file"}:
            resolved_path = self.security.resolve_target(str(kwargs["path"]), name)
            kwargs["path"] = str(resolved_path)

        try:
            result = self.registry.run(name, **kwargs)
        except Exception:
            self.status.transition(NyxState.ERROR, f"Action failed: {name}")
            self.audit.record(name, {"kwargs": kwargs, "result": "error", "allowed": False}, allowed=False)
            raise

        self.status.transition(NyxState.LISTENING, "Nyx is ready again")
        self.audit.record(name, {"kwargs": kwargs, "result": str(result)[:200], "allowed": True})
        return result

    def request_review(self, reason: str) -> None:
        self.status.request_validation(reason)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "state": self.status.state.value,
            "phase": self.status.phase,
            "message": self.status.message,
            "validation_required": self.status.validation_required,
            "avatar_state": self.perception.avatar_state,
            "memories": {
                "working": len(self.memory.working),
                "episodic": len(self.memory.episodic),
                "semantic": len(self.memory.semantic),
            },
        }
