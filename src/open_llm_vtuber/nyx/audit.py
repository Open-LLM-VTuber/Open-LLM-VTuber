from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class AuditEvent:
    timestamp: str
    action: str
    details: Dict[str, Any] = field(default_factory=dict)
    allowed: bool = True


class AuditLog:
    """Stores actions in a separate log from the chat history."""

    def __init__(self) -> None:
        self.events: List[AuditEvent] = []

    def record(self, action: str, details: Dict[str, Any] | None = None, allowed: bool = True) -> AuditEvent:
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            details=details or {},
            allowed=allowed,
        )
        self.events.append(event)
        return event

    def last_events(self, limit: int = 10) -> List[AuditEvent]:
        return list(reversed(self.events[-limit:]))
