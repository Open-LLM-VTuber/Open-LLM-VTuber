"""In-process turn and queue metrics for the live pipeline (A22 / §5.3).

The phase 2 acceptance criterion is "p95 of a full turn below 8 s", so the
numbers have to come from the server instead of a stopwatch in the operator's
hand. This module keeps a bounded, in-memory window of the most recent turns:

* **turn duration**: ``text-input`` accepted -> ``conversation-chain-end`` sent
* **time to first audio**: ``text-input`` -> first ``audio`` payload delivered
* **proxy queue**: depth and how long a ``text-input`` waits before the turn
  is forwarded to ``/client-ws``
* **orphan indicators**: overlapping triggers, turns that ended without audio,
  interrupted and failed turns

It is dependency-free (stdlib only) and side-effect free, so it can be unit
tested in isolation and served as JSON by ``GET /api/metrics``.

Only individual (single-user) turns are instrumented: group conversations
share one turn across several clients and are not part of the live path.
"""

import math
import os
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional

#: Phase 2 target: a whole turn (LLM + TTS + playback ack) under this p95.
TARGET_P95_TURN_SECONDS = 8.0

#: How many completed turns (and queue samples) stay in the window.
DEFAULT_WINDOW = 200

WINDOW_ENV = "VTUBER_METRICS_WINDOW"

OUTCOME_COMPLETED = "completed"
OUTCOME_INTERRUPTED = "interrupted"
OUTCOME_FAILED = "failed"


def _env_window(default: int = DEFAULT_WINDOW) -> int:
    raw = os.environ.get(WINDOW_ENV, "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def percentile(values: Iterable[float], fraction: float) -> Optional[float]:
    """Linear-interpolation percentile (same result as numpy's default)."""
    data = sorted(values)
    if not data:
        return None
    if len(data) == 1:
        return round(data[0], 3)

    position = (len(data) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(data[lower], 3)
    weight = position - lower
    return round(data[lower] * (1 - weight) + data[upper] * weight, 3)


def summarize(values: Iterable[float]) -> Dict[str, Any]:
    """Count/avg/p50/p95/max of a sample; empty values yield ``None``s."""
    data = [value for value in values if value is not None]
    if not data:
        return {"count": 0, "avg": None, "p50": None, "p95": None, "max": None}
    return {
        "count": len(data),
        "avg": round(sum(data) / len(data), 3),
        "p50": percentile(data, 0.50),
        "p95": percentile(data, 0.95),
        "max": round(max(data), 3),
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TurnMetrics:
    """Bounded in-memory aggregator for turn and queue timings."""

    def __init__(
        self,
        window: int = DEFAULT_WINDOW,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self._clock = clock or time.monotonic
        self._window = max(1, int(window))
        self._durations: Deque[float] = deque(maxlen=self._window)
        self._first_audio: Deque[float] = deque(maxlen=self._window)
        self._queue_depths: Deque[int] = deque(maxlen=self._window)
        self._queue_waits: Deque[float] = deque(maxlen=self._window)
        self._turns: Dict[str, Dict[str, Any]] = {}
        self.reset_turns()

    def reset_turns(self) -> None:
        """Forget active turns and counters, keeping the configuration."""
        self._turns.clear()
        self._durations.clear()
        self._first_audio.clear()
        self._queue_depths.clear()
        self._queue_waits.clear()
        self._started_at = time.time()
        self._started = 0
        self._completed = 0
        self._interrupted = 0
        self._failed = 0
        self._overlaps = 0
        self._without_audio = 0
        self._last_turn: Optional[Dict[str, Any]] = None

    def begin_turn(self, key: str, kind: str = "text-input") -> float:
        """Register the start of a turn for ``key`` (a client uid).

        A second trigger while the key is still active is counted as an
        overlap: it is the signature of a hung turn, and the displaced turn is
        deliberately not added to the duration window.
        """
        now = self._clock()
        if key in self._turns:
            self._overlaps += 1
        self._turns[key] = {
            "started_at": now,
            "started_wall": _utc_now(),
            "kind": kind,
            "first_audio_at": None,
        }
        self._started += 1
        return now

    def first_audio(self, key: str) -> Optional[float]:
        """Record the first audio payload of a turn; later calls are no-ops."""
        turn = self._turns.get(key)
        if turn is None or turn.get("first_audio_at") is not None:
            return None

        now = self._clock()
        turn["first_audio_at"] = now
        elapsed = max(0.0, now - turn["started_at"])
        self._first_audio.append(elapsed)
        return elapsed

    def end_turn(
        self, key: str, outcome: str = OUTCOME_COMPLETED
    ) -> Optional[Dict[str, Any]]:
        """Close a turn and return its record (``None`` for unknown keys)."""
        turn = self._turns.pop(key, None)
        if turn is None:
            return None

        if outcome not in (OUTCOME_INTERRUPTED, OUTCOME_FAILED):
            outcome = OUTCOME_COMPLETED

        now = self._clock()
        duration = max(0.0, now - turn["started_at"])
        first_audio_at = turn.get("first_audio_at")

        if outcome == OUTCOME_INTERRUPTED:
            self._interrupted += 1
        elif outcome == OUTCOME_FAILED:
            self._failed += 1
        else:
            # Only complete turns feed the p95: an interrupt ends early and
            # would make the distribution look better than it is.
            self._completed += 1
            self._durations.append(duration)
            if first_audio_at is None:
                self._without_audio += 1

        record = {
            "outcome": outcome,
            "kind": turn.get("kind"),
            "started_at": turn.get("started_wall"),
            "duration_s": round(duration, 3),
            "first_audio_s": (
                round(first_audio_at - turn["started_at"], 3)
                if first_audio_at is not None
                else None
            ),
        }
        self._last_turn = record
        return record

    def note_queue_depth(self, depth: int) -> None:
        """Sample the number of ``text-input`` messages waiting in the proxy."""
        self._queue_depths.append(max(0, int(depth)))

    def note_queue_wait(self, seconds: float) -> None:
        """Record how long a queued message waited before being forwarded."""
        self._queue_waits.append(max(0.0, float(seconds)))

    def snapshot(self) -> Dict[str, Any]:
        """JSON-serialisable view for ``GET /api/metrics``."""
        turns = summarize(self._durations)
        p95 = turns["p95"]
        now = self._clock()
        active: List[Dict[str, Any]] = [
            {
                "key": key,
                "kind": turn.get("kind"),
                "elapsed_s": round(max(0.0, now - turn["started_at"]), 3),
            }
            for key, turn in self._turns.items()
        ]

        return {
            "generated_at": _utc_now(),
            "uptime_s": round(time.time() - self._started_at, 1),
            "window_turns": self._window,
            "turns": {
                "started": self._started,
                "completed": self._completed,
                "interrupted": self._interrupted,
                "failed": self._failed,
                "active": len(self._turns),
                "overlaps": self._overlaps,
                "without_audio": self._without_audio,
            },
            "active_turns": active,
            "turn_seconds": turns,
            "first_audio_seconds": summarize(self._first_audio),
            "queue": {
                "depth": self._queue_depths[-1] if self._queue_depths else 0,
                "max_depth": max(self._queue_depths) if self._queue_depths else 0,
                "wait_seconds": summarize(self._queue_waits),
            },
            "last_turn": self._last_turn,
            "targets": {
                "p95_turn_seconds": TARGET_P95_TURN_SECONDS,
                "p95_ok": None if p95 is None else p95 < TARGET_P95_TURN_SECONDS,
            },
        }


#: Process-wide instance used by the conversation, TTS and proxy code.
turn_metrics = TurnMetrics(window=_env_window())
