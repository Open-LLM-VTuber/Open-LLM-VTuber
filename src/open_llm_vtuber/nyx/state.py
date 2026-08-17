from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class NyxState(str, Enum):
    """High-level runtime states for Nyx."""

    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    ACTING = "acting"
    AWAITING_VALIDATION = "awaiting_validation"
    ERROR = "error"


@dataclass
class NyxStatus:
    """Tracks internal runtime state and guard rails."""

    state: NyxState = NyxState.IDLE
    phase: str = "boot"
    message: str = "Nyx ready"
    last_transition: str = "boot"
    working_directory: Optional[str] = None
    validation_required: bool = False
    locked: bool = False

    def transition(self, new_state: NyxState, message: Optional[str] = None) -> None:
        self.state = new_state
        self.last_transition = f"{self.state.value}:{self.phase}"
        if message is not None:
            self.message = message

    def set_phase(self, phase: str) -> None:
        self.phase = phase

    def request_validation(self, message: str) -> None:
        self.validation_required = True
        self.transition(NyxState.AWAITING_VALIDATION, message)

    def clear_validation(self) -> None:
        self.validation_required = False
