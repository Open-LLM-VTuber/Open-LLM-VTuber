from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


class PermissionDeniedError(RuntimeError):
    """Raised when an action is attempted outside the authorized scope."""


@dataclass
class SecurityPolicy:
    allowed_roots: Sequence[str] = field(default_factory=lambda: ["."])
    blocked_patterns: Sequence[str] = field(default_factory=lambda: ["..", "/etc", "/System32"])

    def is_allowed(self, target: str) -> bool:
        normalized = str(Path(target)).replace("\\", "/")
        if any(block in normalized for block in self.blocked_patterns):
            return False

        candidate = Path(target).expanduser()
        resolved = candidate.resolve(strict=False)
        for root in self.allowed_roots:
            root_path = Path(root).expanduser().resolve(strict=False)
            try:
                resolved.relative_to(root_path)
                return True
            except ValueError:
                continue
        return False

    def require_allowed(self, target: str, action_name: str) -> Path:
        candidate = Path(target).expanduser().resolve(strict=False)
        if not self.is_allowed(str(candidate)):
            raise PermissionDeniedError(f"Action '{action_name}' denied for target '{target}'")
        return candidate


class NyxSecurityGuard:
    def __init__(self, policy: SecurityPolicy | None = None) -> None:
        self.policy = policy or SecurityPolicy()

    def validate_target(self, target: str, action_name: str) -> Path:
        return self.policy.require_allowed(target, action_name)

    def resolve_target(self, target: str, action_name: str) -> Path:
        candidate = Path(target).expanduser()
        resolved = candidate.resolve(strict=False)
        if candidate.exists() and candidate.is_symlink():
            raise PermissionDeniedError(f"Action '{action_name}' denied for unsafe symlink target '{target}'")
        return self.validate_target(str(resolved), action_name)
