from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List


_ALLOWED_COMMANDS: dict[str, list[str]] = {
    "echo": ["echo"],
    "hostname": ["hostname"],
    "whoami": ["whoami"],
}


@dataclass
class LocalAction:
    name: str
    description: str
    handler: Callable[..., Any]


@dataclass
class ActionContext:
    allowed_roots: List[str] = field(default_factory=lambda: ["."])


class ActionRegistry:
    """Very small local runner that keeps actions explicit and auditable."""

    def __init__(self) -> None:
        self._actions: Dict[str, LocalAction] = {}

    def register(self, action: LocalAction) -> None:
        self._actions[action.name] = action

    def run(self, name: str, **kwargs: Any) -> Any:
        if name not in self._actions:
            raise KeyError(f"Unknown action: {name}")
        return self._actions[name].handler(**kwargs)

    def names(self) -> List[str]:
        return sorted(self._actions.keys())


def resolve_safe_command(command: str) -> list[str]:
    parts = shlex.split(command)
    if not parts:
        raise ValueError("Empty command")
    executable = parts[0].lower()
    if executable not in _ALLOWED_COMMANDS:
        raise PermissionError(f"Command '{executable}' is not allowed")
    argv = list(_ALLOWED_COMMANDS[executable])
    argv.extend(parts[1:])
    return argv


def read_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return str(target)


def shell_command(command: str) -> str:
    result = subprocess.run(resolve_safe_command(command), shell=False, capture_output=True, text=True)
    output = result.stdout.strip() or result.stderr.strip() or ""
    return output


def monitor_service(name: str) -> str:
    return f"status-check:{name}"


def mqtt_message(topic: str, payload: str) -> str:
    return f"mqtt:{topic}:{payload}"
