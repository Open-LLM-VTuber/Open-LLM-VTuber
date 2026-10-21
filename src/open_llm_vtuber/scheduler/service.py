"""Scripted live broadcast scheduler.

Emits ``ai-speak-signal`` messages into an already connected client (the OBS
overlay) at fixed times, so the show can start, take a break and close without
an operator.  Implemented with the standard library only: adding APScheduler
would force a ``uv.lock`` refresh and break the ``uv sync --frozen`` Docker
build, and the project only needs 5-field crontab expressions and fixed
intervals.

Turn serialization is delegated to
``WebSocketHandler.trigger_proactive_speak``, which refuses to start a segment
while another turn is running (see audit A14).
"""

import asyncio
import contextlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Set

from loguru import logger

from ..utils.stage import build_stage_payload
from ..utils.tarot import build_draw_props, build_tarot_brief, draw_cards
from .obs import OBSController


_FIELD_RANGES = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))


def _parse_field(field: str, low: int, high: int) -> Set[int]:
    """Expand one crontab field (``*``, ``5``, ``1-3``, ``*/15``, ``1,4,6``)."""
    values: Set[int] = set()
    for chunk in field.split(","):
        chunk = chunk.strip()
        if not chunk:
            raise ValueError(f"Empty element in crontab field '{field}'")

        has_step = "/" in chunk
        step = 1
        base = chunk
        if has_step:
            base, step_text = chunk.split("/", 1)
            step = int(step_text)
            if step <= 0:
                raise ValueError(f"Invalid step in crontab field '{field}'")

        if base == "*":
            start, end = low, high
        elif "-" in base:
            start_text, end_text = base.split("-", 1)
            start, end = int(start_text), int(end_text)
        else:
            start = int(base)
            # "5/15" means "from 5 to the end, every 15"
            end = high if has_step else start

        if start < low or end > high or start > end:
            raise ValueError(
                f"Crontab value out of range ({low}-{high}) in field '{field}'"
            )
        values.update(range(start, end + 1, step))

    return values


class CronExpression:
    """Minimal 5-field crontab matcher (minute granularity, local wall clock)."""

    def __init__(self, expression: str):
        parts = expression.split()
        if len(parts) != 5:
            raise ValueError(
                f"Expected 5 crontab fields, got {len(parts)}: '{expression}'"
            )

        self.expression = expression
        self.minutes = _parse_field(parts[0], *_FIELD_RANGES[0])
        self.hours = _parse_field(parts[1], *_FIELD_RANGES[1])
        self.days = _parse_field(parts[2], *_FIELD_RANGES[2])
        self.months = _parse_field(parts[3], *_FIELD_RANGES[3])
        weekdays = _parse_field(parts[4], *_FIELD_RANGES[4])
        self.weekdays = {0 if day == 7 else day for day in weekdays}
        self._day_wildcard = parts[2].strip().startswith("*")
        self._weekday_wildcard = parts[4].strip().startswith("*")

    def _day_matches(self, moment: datetime) -> bool:
        day_ok = moment.day in self.days
        # Python: Monday=0, crontab: Sunday=0
        weekday_ok = (moment.isoweekday() % 7) in self.weekdays
        if self._day_wildcard and self._weekday_wildcard:
            return True
        if self._day_wildcard:
            return weekday_ok
        if self._weekday_wildcard:
            return day_ok
        # Classic cron semantics: either field may match
        return day_ok or weekday_ok

    def matches(self, moment: datetime) -> bool:
        """True when ``moment`` (minute precision) satisfies the expression."""
        return (
            moment.minute in self.minutes
            and moment.hour in self.hours
            and moment.month in self.months
            and self._day_matches(moment)
        )

    def next_after(self, moment: datetime) -> datetime:
        """First matching minute strictly after ``moment``.

        Raises:
            ValueError: if there is no match within a year (e.g. ``0 0 30 2 *``).
        """
        candidate = moment.replace(second=0, microsecond=0) + timedelta(minutes=1)
        limit = moment + timedelta(days=366)
        for _ in range(366 * 24 * 60 + 60):
            if candidate > limit:
                # Year bound: expressions such as "0 0 30 2 *" never match
                raise ValueError(
                    f"No run scheduled within a year for crontab '{self.expression}'"
                )
            if candidate.month not in self.months:
                # Jump to the first minute of the next month
                candidate = (candidate.replace(day=1) + timedelta(days=32)).replace(
                    day=1, hour=0, minute=0
                )
                continue
            if not self._day_matches(candidate):
                candidate = (candidate + timedelta(days=1)).replace(hour=0, minute=0)
                continue
            if candidate.hour not in self.hours:
                candidate = (candidate + timedelta(hours=1)).replace(minute=0)
                continue
            if candidate.minute not in self.minutes:
                candidate += timedelta(minutes=1)
                continue
            return candidate

        raise ValueError(
            f"No run scheduled within a year for crontab '{self.expression}'"
        )


@dataclass
class _PlannedJob:
    """A job plus the next time it must fire."""

    job: object
    cron: Optional[CronExpression] = None
    next_run: datetime = field(default_factory=datetime.now)


def _load_timezone(name: str):
    """Return a tzinfo, or None to fall back to the machine's local time."""
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception as e:  # missing tzdata on Windows, unknown zone, ...
        logger.warning(
            f"Scheduler: timezone '{name}' unavailable ({e}); using local time"
        )
        return None


class SchedulerService:
    """Owns the asyncio task that fires the configured jobs."""

    MAX_ATTEMPTS = 3
    RETRY_DELAY = 10.0  # seconds between attempts when the overlay is busy
    MAX_SLEEP = 30.0  # wake up periodically to notice shutdown

    def __init__(self, ws_handler, config):
        """
        Args:
            ws_handler: ``WebSocketHandler`` with ``client_connections`` and
                ``trigger_proactive_speak``.
            config: ``SchedulerConfig`` instance.
        """
        self._ws = ws_handler
        self._config = config
        self._timezone = None
        self._jobs: List[_PlannedJob] = []
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        # OBS is optional: without it the show runs with manual scene changes.
        self._obs: Optional[OBSController] = None
        obs_config = getattr(config, "obs", None)
        if obs_config is not None and getattr(obs_config, "enabled", False):
            self._obs = OBSController(
                host=getattr(obs_config, "host", "127.0.0.1"),
                port=getattr(obs_config, "port", 4455),
                password=getattr(obs_config, "password", ""),
                timeout=getattr(obs_config, "timeout", 3.0),
            )

    # ------------------------------------------------------------------ setup
    async def start(self) -> None:
        """Plan the enabled jobs and start the background loop."""
        if not self._config.enabled:
            logger.info("Scheduler disabled")
            return
        if self._task and not self._task.done():
            return

        self._timezone = _load_timezone(self._config.timezone)
        now = self._now()
        self._jobs = []
        for job in self._config.jobs:
            if not job.enabled:
                continue
            try:
                if job.cron:
                    cron = CronExpression(job.cron)
                    next_run = cron.next_after(now)
                elif job.interval_minutes > 0:
                    cron = None
                    next_run = now + timedelta(minutes=job.interval_minutes)
                else:
                    logger.warning(
                        f"Scheduler: job '{job.name}' has no cron nor interval; skipped"
                    )
                    continue
            except ValueError as e:
                logger.error(f"Scheduler: job '{job.name}' is invalid: {e}")
                continue

            self._jobs.append(_PlannedJob(job=job, cron=cron, next_run=next_run))
            logger.info(
                f"Scheduler: job '{job.name}' armed for "
                f"{next_run.strftime('%Y-%m-%d %H:%M')}"
            )

        if not self._jobs:
            logger.info("Scheduler: no active jobs")
            return

        if self._obs is not None:
            await self._connect_obs()

        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="scheduler")
        logger.info(
            f"Scheduler started with {len(self._jobs)} job(s) "
            f"(timezone: {self._config.timezone})"
        )

    async def shutdown(self) -> None:
        """Stop the loop; safe to call even if the scheduler never started."""
        self._stop.set()
        task = self._task
        self._task = None
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        if self._jobs:
            logger.info("Scheduler stopped")
        self._jobs.clear()

        if self._obs is not None:
            if getattr(self._config.obs, "stop_stream_on_shutdown", False):
                await self._obs.stop_stream()
            await self._obs.close()

    # ------------------------------------------------------------------- loop
    def _now(self) -> datetime:
        return datetime.now(self._timezone)

    async def _run(self) -> None:
        while True:
            if not self._jobs:
                return
            planned = min(self._jobs, key=lambda item: item.next_run)
            delay = (planned.next_run - self._now()).total_seconds()
            if delay > 0:
                try:
                    await asyncio.wait_for(
                        self._stop.wait(), timeout=min(delay, self.MAX_SLEEP)
                    )
                except asyncio.TimeoutError:
                    pass
                if self._stop.is_set():
                    return
                continue

            # Re-arm before firing: a slow turn must not cause a double shot
            now = self._now()
            if planned.cron:
                planned.next_run = planned.cron.next_after(now)
            else:
                planned.next_run = now + timedelta(minutes=planned.job.interval_minutes)

            try:
                await self._fire(planned.job)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Scheduler: job '{planned.job.name}' failed: {e}")

    def _pick_client(self) -> Optional[str]:
        target = self._config.target_client
        if target and target != "first":
            return target if target in self._ws.client_connections else None
        return next(iter(self._ws.client_connections), None)

    async def _connect_obs(self) -> None:
        """Connect to OBS once at startup and log the available scenes."""
        obs_config = self._config.obs
        if not await self._obs.connect():
            logger.warning(
                f"Scheduler: OBS unreachable at {obs_config.host}:{obs_config.port}; "
                "scene changes will retry on demand"
            )
            return

        scenes = await self._obs.list_scenes()
        if scenes:
            logger.info(f"Scheduler: OBS scenes available: {', '.join(scenes)}")

        if getattr(obs_config, "start_stream", False):
            await self._obs.start_stream()

    async def _prepare_stage(self, job, drawn=None) -> None:
        """Switch the OBS scene and broadcast the overlay stage for ``job``.

        ``drawn`` is the spread of this fire (see ``_draw``) and becomes the
        ``props`` of the payload, so the cards appear on screen while the turn
        is being spoken. Both steps are best-effort: a closed OBS or an absent
        overlay must not cancel the spoken segment.
        """
        if job.scene:
            if self._obs is None:
                logger.debug(
                    f"Scheduler: job '{job.name}' scene '{job.scene}' ignored "
                    "(scheduler_config.obs.enabled is false)"
                )
            elif getattr(self._config.obs, "switch_scenes", True):
                await self._obs.set_scene(job.scene)

        props = build_draw_props(drawn) if drawn else []
        if not job.background and not props:
            return

        payload = build_stage_payload(
            stage=job.name,
            background=job.background,
            props=props or None,
            transition=job.transition,
            duration_ms=job.duration_ms,
        )
        delivered = await self._ws.broadcast_stage_update(
            payload, self._config.target_client
        )
        detail = job.background or f"{len(props)} card(s)"
        logger.info(
            f"Scheduler: stage '{job.name}' -> {detail} ({delivered} client(s))"
        )

    def _draw(self, job):
        """Draw the cards of a job, once per fire.

        The spread is drawn before the stage update and before the turn, so the
        overlay and the LLM always see the same cards. A bad configuration is
        logged and treated as "no draw": the segment is still spoken.
        """
        count = int(getattr(job, "draw", 0) or 0)
        if count <= 0:
            return []
        seed = int(getattr(job, "draw_seed", 0) or 0)
        try:
            drawn = draw_cards(count, seed=seed or None)
        except ValueError as e:
            logger.error(f"Scheduler: job '{job.name}' has an invalid draw: {e}")
            return []
        logger.info(
            f"Scheduler: job '{job.name}' drew "
            + ", ".join(card.describe() for card in drawn)
        )
        return drawn

    @staticmethod
    def _compose_text(job, drawn) -> str:
        """Brief for the LLM plus the job text (empty keeps the default prompt)."""
        parts = []
        if drawn:
            parts.append(build_tarot_brief(drawn, getattr(job, "question", "") or ""))
        text = (job.text or "").strip()
        if text:
            parts.append(text)
        return "\n\n".join(parts)

    async def _fire(self, job) -> None:
        """Send one segment, retrying while the overlay is busy."""
        drawn = self._draw(job)
        # The scene change is useful even without an overlay: OBS keeps showing
        # the right camera/board while the chat is answered by the connector.
        await self._prepare_stage(job, drawn)

        if not self._pick_client():
            logger.warning(f"Scheduler: job '{job.name}' skipped, no overlay connected")
            return

        text = self._compose_text(job, drawn)
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            client_uid = self._pick_client()
            if not client_uid:
                break
            try:
                triggered = await self._ws.trigger_proactive_speak(client_uid, text)
            except Exception as e:
                logger.error(
                    f"Scheduler: failed to reach {client_uid} for job '{job.name}': {e}"
                )
                triggered = False

            if triggered:
                logger.info(
                    f"Scheduler: job '{job.name}' fired on {client_uid} "
                    f"(attempt {attempt}/{self.MAX_ATTEMPTS})"
                )
                return
            if attempt < self.MAX_ATTEMPTS:
                await asyncio.sleep(self.RETRY_DELAY)

        logger.warning(f"Scheduler: job '{job.name}' dropped, overlay busy or absent")
