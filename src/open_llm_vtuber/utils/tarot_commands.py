"""On-demand tarot draws: chat commands and the shared presenter.

The scheduler draws on a timetable (``scheduler_config.jobs[].draw``); this
module lets the **operator** (``POST /api/tarot/draw``) and the **chat**
(``!carta``, ``!tirada 3``) trigger the same spread without duplicating any
payload logic.

Standard library only, so the HTTP route, the WebSocket handler and the tests
share exactly one implementation (no pydantic, no fastapi).
"""

from dataclasses import dataclass
from typing import List, Optional

from .stage import build_stage_payload
from .tarot import (
    MAX_CARDS,
    DrawnCard,
    build_draw_props,
    build_tarot_brief,
    draw_cards,
)

#: First word that turns a chat message into a draw (case-insensitive).
CHAT_COMMANDS = ("!carta", "!tirada", "!tarot", "/carta", "/tirada")
#: A question goes to the LLM inside the brief, so it must stay short.
MAX_QUESTION = 200
#: Stage id used for on-demand draws (the scheduler uses the job name).
DRAW_STAGE = "tarot_draw"


@dataclass(frozen=True)
class DrawRequest:
    """What the chat asked for."""

    count: int = 1
    question: str = ""


@dataclass
class DrawResult:
    """Everything one draw produces: overlay payload, LLM brief, summary."""

    cards: List[DrawnCard]
    payload: dict
    brief: str
    question: str = ""
    #: Filled in by the caller that actually sends the payload.
    delivered: int = 0
    spoken: bool = False

    def summary(self) -> dict:
        """JSON-friendly view for ``GET /api/tarot`` (no audio, no brief)."""
        return {
            "question": self.question,
            "stage": self.payload.get("stage"),
            "cards": [
                {
                    "id": drawn.card.id,
                    "name": drawn.card.name,
                    "reversed": drawn.reversed,
                    "position": drawn.position,
                    "keywords": list(drawn.card.keywords),
                }
                for drawn in self.cards
            ],
        }


def parse_draw_command(text: object) -> Optional[DrawRequest]:
    """Return the draw a chat message asks for, or ``None``.

    Accepted forms (first word, case-insensitive)::

        !carta                    -> 1 card
        !tirada 3                 -> 3 cards
        !carta ¿me cambiaré?      -> 1 card + question for the LLM
        !tirada 2 ¿y el amor?     -> 2 cards + question

    Raises:
        ValueError: when the message **is** a command but the count is not
            between 1 and ``MAX_CARDS``. The caller decides whether to answer
            or to fall back to a normal turn.
    """
    if not isinstance(text, str):
        return None

    cleaned = text.strip()
    if not cleaned:
        return None

    head, _, rest = cleaned.partition(" ")
    if head.lower() not in CHAT_COMMANDS:
        return None

    rest = rest.strip()
    count = 1
    if rest:
        first, _, tail = rest.partition(" ")
        if first.isdigit():
            count = int(first)
            rest = tail.strip()

    if count < 1 or count > MAX_CARDS:
        raise ValueError(f"a spread is 1 to {MAX_CARDS} cards, got {count}")

    return DrawRequest(count=count, question=rest[:MAX_QUESTION])


def build_draw_result(
    count: int = 1,
    question: str = "",
    seed: Optional[int] = None,
    stage: str = DRAW_STAGE,
) -> DrawResult:
    """Draw, build the overlay payload and the brief for the LLM.

    The three outputs come from the same ``DrawnCard`` list on purpose: the
    overlay and the vtuber can never disagree about which cards came out.

    Raises:
        ValueError: when ``count`` is out of range (``1..MAX_CARDS``).
    """
    cleaned = (question or "").strip()[:MAX_QUESTION]
    drawn = draw_cards(count, seed=seed)
    payload = build_stage_payload(stage=stage, props=build_draw_props(drawn))
    return DrawResult(
        cards=drawn,
        payload=payload,
        brief=build_tarot_brief(drawn, cleaned),
        question=cleaned,
    )
