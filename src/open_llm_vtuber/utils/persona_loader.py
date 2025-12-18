import os
from pathlib import Path
from typing import Any, Iterable

from loguru import logger

from ..config_manager.utils import read_yaml


DEFAULT_PERSONA_DIR = Path(__file__).resolve().parents[3] / "persona"


def _join_items(values: Iterable[str]) -> str:
    return ", ".join([v for v in values if v])


def _format_section(title: str, body: str) -> str:
    return f"{title}:\n{body.strip()}" if body else ""


def _format_rules(title: str, rules: Iterable[str] | None) -> str:
    if not rules:
        return ""
    joined = "\n- " + "\n- ".join(rules)
    return f"{title}:{joined}"


def _format_key_values(title: str, values: dict[str, Any]) -> str:
    if not values:
        return ""
    pairs = [f"{k}: {v}" for k, v in values.items() if v is not None]
    if not pairs:
        return ""
    return f"{title}:\n- " + "\n- ".join(pairs)


def build_persona_prompt(persona_data: dict[str, Any]) -> str:
    """Convert structured persona YAML to a flattened system prompt."""

    lines: list[str] = []

    persona = persona_data.get("persona", {})
    persona_id = persona.get("id")
    persona_name = persona.get("name")
    persona_role = persona.get("role")

    identity = persona_data.get("identity", {})
    description = identity.get("description")
    core_traits = identity.get("core_traits") or []

    behavior = persona_data.get("behavior", {})
    general_rules = behavior.get("general_rules") or []
    interaction_style = behavior.get("interaction_style") or {}

    languages = persona_data.get("languages", {})
    supported_langs = languages.get("supported") or []
    language_rules = languages.get("rules") or []

    memory = persona_data.get("memory", {})
    memory_rules = memory.get("rules") or []
    short_term = memory.get("short_term", {})
    long_term = memory.get("long_term", {})

    header_bits = [bit for bit in [persona_name, persona_role, persona_id] if bit]
    if header_bits:
        lines.append("Persona: " + _join_items(header_bits))

    if description:
        lines.append(_format_section("Identity", description))

    if core_traits:
        lines.append(_format_rules("Core traits", core_traits))

    if general_rules:
        lines.append(_format_rules("Behavior rules", general_rules))

    if interaction_style:
        lines.append(_format_key_values("Interaction style", interaction_style))

    if supported_langs:
        lines.append(_format_rules("Supported languages", supported_langs))

    if language_rules:
        lines.append(_format_rules("Language rules", language_rules))

    if short_term:
        lines.append(_format_key_values("Short-term memory", short_term))

    if long_term:
        lines.append(_format_key_values("Long-term memory", long_term))

    if memory_rules:
        lines.append(_format_rules("Memory rules", memory_rules))

    prompt = "\n\n".join([line for line in lines if line])
    if not prompt:
        raise ValueError("Persona YAML did not produce a prompt; check required fields")
    return prompt


def load_persona_prompt_by_id(persona_id: str, persona_dir: str | Path | None = None) -> str:
    """Load a persona YAML by ID and render it as a system prompt."""

    base_dir = Path(persona_dir) if persona_dir else DEFAULT_PERSONA_DIR
    persona_path = base_dir / f"{persona_id}.yaml"

    if not persona_path.exists():
        raise FileNotFoundError(
            f"Persona '{persona_id}' not found in {os.fspath(base_dir)}"
        )

    persona_data = read_yaml(str(persona_path))
    if not isinstance(persona_data, dict):
        raise ValueError(f"Persona '{persona_id}' must be a YAML mapping")

    prompt = build_persona_prompt(persona_data)
    logger.debug(f"Loaded persona '{persona_id}' from {persona_path}")
    return prompt

