"""Donation follow-ups: who owes a question, and the frames to ask and draw.

A gift cannot be read in the same breath: the vtuber thanks the donor and asks
what they want to know, and the answer arrives later as a comment. This module
keeps that promise:

* ``PendingDonors`` remembers the donor (per username) for a while.
* ``build_gift_thanks`` composes the thank-you + question turn.
* ``build_donor_draw_payload`` composes the ``tarot-draw`` frame for the reply.

Standard library only: the TikTok connector, the server and the tests share it.
"""

import time
from typing import Callable, Dict, Optional

#: How long a "thanks, what do you need?" stays armed. A gift at 19:00 must not
#: turn a random 23:30 comment into a paid reading.
DEFAULT_TTL_SECONDS = 600.0
MAX_USERNAME = 64
MAX_GIFT_NAME = 64


def normalize_username(name: object) -> str:
    """Lower-case, drop a leading ``@`` and cap the length."""
    if not isinstance(name, str):
        return ""
    return name.strip().lstrip("@").lower()[:MAX_USERNAME]


class PendingDonors:
    """Remember which donors still owe a question (one comment each).

    One-shot by design: answering consumes the entry, so one gift cannot buy
    unlimited readings, and stale entries expire.
    """

    def __init__(
        self,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._ttl = max(1.0, float(ttl_seconds))
        self._clock = clock
        self._entries: Dict[str, dict] = {}

    def remember(
        self, username: object, *, gift: str = "", coins: int = 0
    ) -> Optional[str]:
        """Store a pending question for ``username``; returns its key."""
        key = normalize_username(username)
        if not key:
            return None
        self._entries[key] = {
            "username": key,
            "gift": (gift or "")[:MAX_GIFT_NAME],
            "coins": max(0, int(coins or 0)),
            "at": self._clock(),
        }
        return key

    def consume(self, username: object) -> Optional[dict]:
        """Pop the pending entry of ``username`` if it is still fresh."""
        key = normalize_username(username)
        if not key:
            return None
        self._prune()
        return self._entries.pop(key, None)

    def __len__(self) -> int:
        self._prune()
        return len(self._entries)

    def clear(self) -> None:
        """Forget every pending donor (new show, new session)."""
        self._entries.clear()

    def _prune(self) -> None:
        now = self._clock()
        for key in [k for k, v in self._entries.items() if now - v["at"] > self._ttl]:
            del self._entries[key]


def build_gift_thanks(
    username: object,
    gift: str = "",
    count: int = 1,
    coins: int = 0,
    ask_question: bool = True,
) -> str:
    """Turn for the gift: thank, ask what they need, and do **not** read yet.

    The last sentence matters: without it the LLM tends to invent a spread
    before the donor has said what they want. With ``ask_question=False``
    (``gift_reading`` off) it only thanks.
    """
    name = str(username or "alguien").strip().lstrip("@") or "alguien"
    item = (gift or "").strip()[:MAX_GIFT_NAME] or "un regalo"
    times = max(1, int(count or 1))
    extra = f" ({int(coins)} monedas)" if coins else ""
    thanks = f"{name} te envió {item} x{times}{extra}. Dale las gracias en una frase."
    if not ask_question:
        return f"{thanks} Sigue con la lectura."

    return (
        f"{thanks} Pregúntale a {name} qué quiere saber del tarot y dile que "
        "escriba su pregunta en un comentario. No leas cartas todavía: espera "
        "su pregunta."
    )


def build_donor_draw_payload(
    username: object, question: str = "", count: int = 1
) -> dict:
    """Frame that asks the server to draw for this donor (``tarot-draw``)."""
    return {
        "type": "tarot-draw",
        "asker": str(username or "").strip().lstrip("@"),
        "question": str(question or "").strip(),
        "count": 1 if count is None else int(count),
    }
