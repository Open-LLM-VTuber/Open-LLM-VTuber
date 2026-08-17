"""Nyx runtime package.

This package defines the core local agent scaffolding for Nyx in the
Open-LLM-VTuber codebase. The implementation is intentionally conservative and
security-first so it can evolve from perception to autonomous operation in a
controlled order.
"""

from .actions import ActionContext, ActionRegistry, LocalAction
from .audit import AuditEvent, AuditLog
from .action_runtime import AllowedAction, LocalActionRuntime
from .evolution import PatchCandidate, SelfReview
from .memory import MemoryEntry, NyxMemory
from .perception import NyxPerception, VoiceTurn
from .runtime import NyxRuntime
from .security import PermissionDeniedError, SecurityPolicy
from .service_bridge import NyxSession
from .state import NyxState, NyxStatus

__all__ = [
    "ActionContext",
    "ActionRegistry",
    "AllowedAction",
    "AuditEvent",
    "AuditLog",
    "LocalAction",
    "LocalActionRuntime",
    "MemoryEntry",
    "NyxMemory",
    "NyxPerception",
    "NyxRuntime",
    "NyxSession",
    "NyxState",
    "NyxStatus",
    "PatchCandidate",
    "PermissionDeniedError",
    "SecurityPolicy",
    "SelfReview",
    "VoiceTurn",
]
