from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .actions import resolve_safe_command
from .audit import AuditLog
from .security import NyxSecurityGuard, PermissionDeniedError, SecurityPolicy


@dataclass
class AllowedAction:
    name: str
    description: str
    handler: Any
    allow_write: bool = False
    allow_shell: bool = False


@dataclass
class LocalActionRuntime:
    """Action runtime aligned with the Nyx governance model."""

    allowed_roots: List[str] = field(default_factory=lambda: ["."])
    audit: AuditLog = field(default_factory=AuditLog)
    guard: NyxSecurityGuard = field(default_factory=NyxSecurityGuard)
    actions: Dict[str, AllowedAction] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.guard = NyxSecurityGuard(SecurityPolicy(allowed_roots=self.allowed_roots))

    def register(self, action: AllowedAction) -> None:
        self.actions[action.name] = action

    def read_text(self, target: str) -> str:
        try:
            target_path = self.guard.resolve_target(target, "read_text")
        except PermissionDeniedError:
            self.audit.record("read_text", {"target": target, "allowed": False}, allowed=False)
            raise
        self.audit.record("read_text", {"target": str(target_path), "allowed": True})
        return target_path.read_text(encoding="utf-8")

    def write_text(self, target: str, content: str) -> str:
        try:
            target_path = self.guard.resolve_target(target, "write_text")
        except PermissionDeniedError:
            self.audit.record("write_text", {"target": target, "allowed": False}, allowed=False)
            raise
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        self.audit.record("write_text", {"target": str(target_path), "length": len(content), "allowed": True})
        return str(target_path)

    def run_shell(self, command: str) -> str:
        try:
            argv = resolve_safe_command(command)
        except (PermissionError, ValueError):
            self.audit.record("run_shell", {"command": command, "allowed": False}, allowed=False)
            raise
        result = subprocess.run(argv, shell=False, capture_output=True, text=True)
        output = result.stdout.strip() or result.stderr.strip() or ""
        self.audit.record("run_shell", {"command": command, "output": output[:200], "allowed": True})
        return output

    def run(self, action_name: str, **kwargs: Any) -> Any:
        action = self.actions.get(action_name)
        if action is None:
            raise KeyError(f"Unknown action '{action_name}'")

        if "target" in kwargs:
            validated_target = self.guard.resolve_target(str(kwargs["target"]), action_name)
            kwargs["target"] = str(validated_target)

        if action.allow_shell:
            return action.handler(**kwargs)
        if action.allow_write:
            return action.handler(**kwargs)
        return action.handler(**kwargs)
