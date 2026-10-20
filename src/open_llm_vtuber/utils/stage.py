"""Stage-update contract shared by the scheduler, the HTTP route and the overlay.

The payload is documented in ``AUDITORIA-MVP-TAROT.md`` §2.4: the server tells
the Ruta B overlay which background/props to show. It is deliberately
dependency-free so the scheduler can build it without importing FastAPI.

A prop is either an image (``src``) or a text card (``label``/``sublabel``), so a
tarot draw can be shown before the card art exists::

    build_stage_payload(
        stage="tarot_main",
        background="/bg/tarot_table.png",
        props=[{"id": "card_1", "src": "/bg/cards/death.png", "x": 0.7, "y": 0.5}],
    )
    build_stage_payload(
        stage="card_of_the_day",
        props=[{"id": "card_1", "label": "La Torre", "sublabel": "ruptura · verdad"}],
    )
"""

from typing import Any, Dict, Iterable, List, Optional

MAX_PROPS = 32
TRANSITIONS = ("fade", "none")
#: A label is drawn on stream, so it must fit in a card without wrapping wildly.
MAX_LABEL = 64
MAX_SUBLABEL = 96


def _number(value: Any, low: float, high: float, default: float) -> float:
    """Coerce ``value`` to a float inside ``[low, high]`` (``default`` if invalid)."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:  # NaN
        return default
    return max(low, min(high, number))


def _normalise_prop(raw: Any, index: int) -> Optional[Dict[str, Any]]:
    """Return a sanitised prop, or ``None`` when it has neither ``src`` nor ``label``.

    An image prop keeps ``src``; a text prop keeps ``label`` (title) and the
    optional ``sublabel`` (keywords). Numbers below are shared by both.
    """
    if not isinstance(raw, dict):
        return None

    src = raw.get("src")
    label = raw.get("label")
    prop: Dict[str, Any] = {"id": str(raw.get("id") or f"prop_{index}")}

    if isinstance(src, str) and src.strip():
        prop["src"] = src.strip()
    elif isinstance(label, str) and label.strip():
        prop["label"] = label.strip()[:MAX_LABEL]
        sublabel = raw.get("sublabel")
        if isinstance(sublabel, str) and sublabel.strip():
            prop["sublabel"] = sublabel.strip()[:MAX_SUBLABEL]
    else:
        return None

    # x/y are normalised (0..1) so the same payload works at any resolution.
    if "x" in raw:
        prop["x"] = _number(raw["x"], 0.0, 1.0, 0.5)
    if "y" in raw:
        prop["y"] = _number(raw["y"], 0.0, 1.0, 0.5)
    if "rot" in raw:
        prop["rot"] = _number(raw["rot"], -360.0, 360.0, 0.0)
    if "scale" in raw:
        prop["scale"] = _number(raw["scale"], 0.01, 10.0, 1.0)
    if "opacity" in raw:
        prop["opacity"] = _number(raw["opacity"], 0.0, 1.0, 1.0)
    return prop


def build_stage_payload(
    *,
    stage: str = "",
    background: str = "",
    props: Optional[Iterable[Any]] = None,
    transition: str = "fade",
    duration_ms: Any = 800,
) -> Dict[str, Any]:
    """Build a ``stage-update`` message for the overlay.

    Args:
        stage: Stage identifier (free-form, truncated to 64 characters).
        background: Image URL/path served by the backend (``/bg/...``).
        props: Optional iterable of ``{"id", "src", "x", "y", "rot", ...}``
            dicts (images) or ``{"id", "label", "sublabel", ...}`` dicts (text
            cards). Entries with neither a usable ``src`` nor a ``label`` are
            dropped.
        transition: ``"fade"`` or ``"none"``; anything else falls back to fade.
        duration_ms: Transition duration, clamped to 0..10000 ms.

    Raises:
        ValueError: when there is nothing to change (no stage, no background
            and no usable prop), so the HTTP layer can answer 400.

    Returns:
        dict: JSON-serialisable payload with ``type`` set to ``stage-update``.
    """
    payload: Dict[str, Any] = {"type": "stage-update"}

    if isinstance(stage, str) and stage.strip():
        payload["stage"] = stage.strip()[:64]
    if isinstance(background, str) and background.strip():
        payload["background"] = background.strip()

    raw_props: List[Any] = list(props) if isinstance(props, (list, tuple)) else []
    cleaned = [
        prop
        for index, raw in enumerate(raw_props[:MAX_PROPS])
        if (prop := _normalise_prop(raw, index)) is not None
    ]
    if cleaned:
        payload["props"] = cleaned

    if len(payload) == 1:
        raise ValueError(
            "stage-update needs 'stage', 'background' or a prop with 'src'/'label'"
        )

    payload["transition"] = transition if transition in TRANSITIONS else "fade"
    payload["duration_ms"] = int(_number(duration_ms, 0.0, 10000.0, 800.0))
    return payload


def select_stage_targets(
    client_uids: Iterable[str], target: str = "first"
) -> List[str]:
    """Resolve the ``target`` field into the clients that must receive the payload.

    ``"first"`` (or empty) picks the first connected socket, which is the OBS
    overlay in the recommended deployment; ``"all"`` broadcasts; anything else
    is treated as a ``client_uid`` and only matches an existing connection.
    """
    uids = list(client_uids)
    if target == "all":
        return uids
    if not target or target == "first":
        return uids[:1]
    return [target] if target in uids else []
