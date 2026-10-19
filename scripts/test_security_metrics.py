"""Unit tests for the A22 transport hardening and §5.3 turn/queue metrics.

Standalone on purpose: the repository has no pytest setup, so this runs with
the plain interpreter and stdlib ``unittest`` (no new dependencies):

    python scripts/test_security_metrics.py
    python scripts/test_security_metrics.py -v SecurityTokenTests

Everything here is deterministic: the clock is injected, and the globals
(``turn_metrics``) are patched per test so the suite never depends on order.
"""

import asyncio
import json
import logging
import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest import mock

# Add project root to path to enable imports (same as the live scripts).
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def _install_loguru_shim() -> None:
    """Allow the stdlib-only modules to import in a bare interpreter.

    ``security``/``metrics``/``proxy_message_queue`` only use ``loguru`` for
    logging, so a ``logging``-backed stand-in keeps the suite runnable before
    the runtime dependencies are installed. A real ``loguru`` always wins.
    """
    try:
        import loguru  # noqa: F401

        return
    except ImportError:
        pass

    class _ShimLogger:
        def __init__(self, name="loguru"):
            self._log = logging.getLogger(name)

        def bind(self, **_kwargs):
            return self

        @property
        def opt(self):
            return self

        def debug(self, msg, *a, **k):
            self._log.debug(msg, *a, **k)

        def info(self, msg, *a, **k):
            self._log.info(msg, *a, **k)

        def success(self, msg, *a, **k):
            self._log.info(msg, *a, **k)

        def warning(self, msg, *a, **k):
            self._log.warning(msg, *a, **k)

        def error(self, msg, *a, **k):
            self._log.error(msg, *a, **k)

        def exception(self, msg, *a, **k):
            self._log.exception(msg, *a, **k)

        def add(self, *_a, **_k):
            return 0

        def remove(self, *_a, **_k):
            return None

        def complete(self, *_a, **_k):
            return None

    module = types.ModuleType("loguru")
    module.logger = _ShimLogger()
    sys.modules["loguru"] = module


_install_loguru_shim()

from src.open_llm_vtuber.metrics import (  # noqa: E402
    OUTCOME_COMPLETED,
    OUTCOME_FAILED,
    OUTCOME_INTERRUPTED,
    TARGET_P95_TURN_SECONDS,
    TurnMetrics,
    percentile,
    summarize,
)
from src.open_llm_vtuber.security import (  # noqa: E402
    LOCAL_ORIGIN_REGEX,
    WS_CLOSE_POLICY_VIOLATION,
    WS_TOKEN_ENV,
    build_cors_settings,
    enforce_ws_token,
    extract_ws_token,
    get_ws_token,
    http_token_allowed,
    origin_allowed,
    resolve_cors_policy,
    static_cors_headers,
    token_matches,
    with_token,
)

try:  # light module: only loguru + metrics
    from src.open_llm_vtuber.proxy_message_queue import ProxyMessageQueue

    PROXY_QUEUE_AVAILABLE = True
except Exception as e:  # pragma: no cover - environment without the stack
    ProxyMessageQueue = None
    PROXY_QUEUE_AVAILABLE = False
    print(f"skip ProxyQueueTests: proxy_message_queue import failed ({e})")

try:  # heavy module; skipped when optional runtime deps are missing
    from src.open_llm_vtuber.conversations import conversation_utils

    INSTRUMENTATION_AVAILABLE = True
except Exception as e:  # pragma: no cover - environment without the stack
    conversation_utils = None
    INSTRUMENTATION_AVAILABLE = False
    print(f"skip InstrumentationTests: conversation_utils import failed ({e})")


class FakeWebSocket:
    """Minimal stand-in for a Starlette WebSocket handshake."""

    def __init__(self, query=None, headers=None, path="/client-ws"):
        self.query_params = query or {}
        self.headers = headers or {}
        self.url = SimpleNamespace(path=path)
        self.closed_with = None

    async def close(self, code=1000):
        self.closed_with = code


class FakeRequest:
    """Minimal stand-in for a Starlette Request (only query/headers are read)."""

    def __init__(self, query=None, headers=None):
        self.query_params = query or {}
        self.headers = headers or {}


class FakeClock:
    """Deterministic monotonic clock for the metrics tests."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class SecurityTokenTests(unittest.TestCase):
    """Shared token: opt-in, constant-time, query param or bearer header."""

    def test_token_matches_requires_both_sides(self):
        self.assertTrue(token_matches("abc", "abc"))
        self.assertFalse(token_matches("abc", "abd"))
        self.assertFalse(token_matches("", "abc"))
        self.assertFalse(token_matches("abc", ""))

    def test_get_ws_token_precedence(self):
        with mock.patch.dict(os.environ, {WS_TOKEN_ENV: "from-env"}):
            self.assertEqual(get_ws_token(), "from-env")
            self.assertEqual(get_ws_token(" explicit "), "explicit")

    def test_extract_prefers_query_then_bearer(self):
        ws = FakeWebSocket(query={"token": "q1"})
        self.assertEqual(extract_ws_token(ws), "q1")

        ws = FakeWebSocket(headers={"authorization": "Bearer  q2 "})
        self.assertEqual(extract_ws_token(ws), "q2")

        ws = FakeWebSocket(headers={"authorization": "Basic q3"})
        self.assertEqual(extract_ws_token(ws), "")

        self.assertEqual(extract_ws_token(FakeWebSocket()), "")

    def test_enforce_without_token_never_rejects(self):
        with mock.patch.dict(os.environ, {WS_TOKEN_ENV: ""}):
            ws = FakeWebSocket()
            self.assertTrue(asyncio.run(enforce_ws_token(ws, "")))
            self.assertIsNone(ws.closed_with)

    def test_enforce_rejects_missing_or_wrong_token(self):
        with mock.patch.dict(os.environ, {WS_TOKEN_ENV: ""}):
            for ws in (
                FakeWebSocket(),
                FakeWebSocket(query={"token": "nope"}),
                FakeWebSocket(headers={"authorization": "Bearer nope"}),
            ):
                self.assertFalse(asyncio.run(enforce_ws_token(ws, "s3cret")))
                self.assertEqual(ws.closed_with, WS_CLOSE_POLICY_VIOLATION)

    def test_enforce_accepts_query_and_bearer(self):
        with mock.patch.dict(os.environ, {WS_TOKEN_ENV: ""}):
            ws = FakeWebSocket(query={"token": "s3cret"})
            self.assertTrue(asyncio.run(enforce_ws_token(ws, None)))
            self.assertIsNone(ws.closed_with)

            ws = FakeWebSocket(headers={"authorization": "Bearer s3cret"})
            self.assertTrue(asyncio.run(enforce_ws_token(ws, None)))

    def test_http_token_allowed(self):
        with mock.patch.dict(os.environ, {WS_TOKEN_ENV: ""}):
            self.assertTrue(http_token_allowed(FakeRequest(), ""))
            self.assertFalse(http_token_allowed(FakeRequest(), "s3cret"))
            self.assertTrue(
                http_token_allowed(FakeRequest(query={"token": "s3cret"}), None)
            )
            self.assertTrue(
                http_token_allowed(
                    FakeRequest(headers={"authorization": "Bearer s3cret"}), None
                )
            )

    def test_with_token(self):
        with mock.patch.dict(os.environ, {WS_TOKEN_ENV: ""}):
            self.assertEqual(with_token("ws://h/proxy-ws", ""), "ws://h/proxy-ws")
            self.assertEqual(
                with_token("ws://h/proxy-ws", "abc"), "ws://h/proxy-ws?token=abc"
            )
            self.assertEqual(
                with_token("ws://h/proxy-ws?x=1", "abc"),
                "ws://h/proxy-ws?x=1&token=abc",
            )
            self.assertEqual(
                with_token("ws://h/proxy-ws?token=abc", "abc"),
                "ws://h/proxy-ws?token=abc",
            )
            self.assertEqual(
                with_token("ws://h/proxy-ws", "a b/c"),
                "ws://h/proxy-ws?token=a%20b%2Fc",
            )

    def test_with_token_reads_environment(self):
        with mock.patch.dict(os.environ, {WS_TOKEN_ENV: "env-token"}):
            self.assertEqual(
                with_token("ws://h/client-ws"), "ws://h/client-ws?token=env-token"
            )


class CorsTests(unittest.TestCase):
    """CORS: explicit allow-list, no wildcard next to credentials (A22)."""

    def test_settings_are_spec_valid(self):
        settings = build_cors_settings("127.0.0.1", 12393, extra_origins="")
        self.assertFalse(settings["allow_credentials"])
        self.assertNotIn("*", settings["allow_origins"])
        self.assertIn("http://127.0.0.1:12393", settings["allow_origins"])
        self.assertIn("http://localhost:12393", settings["allow_origins"])
        self.assertEqual(settings["allow_origin_regex"], LOCAL_ORIGIN_REGEX)

    def test_configured_host_is_added(self):
        origins, _ = resolve_cors_policy("tarot.example.com", 9000, extra_origins="")
        self.assertIn("https://tarot.example.com:9000", origins)

    def test_lan_origins_match_regex(self):
        for origin in (
            "http://127.0.0.1:12393",
            "http://localhost:5173",
            "http://192.168.1.50:8080",
            "http://10.0.0.7:12393",
            "http://172.20.3.4:12393",
        ):
            self.assertTrue(
                origin_allowed(origin, [], LOCAL_ORIGIN_REGEX), origin
            )
        for origin in (
            "https://evil.example.com",
            "http://8.8.8.8:12393",
            "http://172.32.0.1:12393",
            "null",
        ):
            self.assertFalse(origin_allowed(origin, [], LOCAL_ORIGIN_REGEX), origin)

    def test_wildcard_is_opt_in(self):
        origins, regex = resolve_cors_policy("127.0.0.1", 12393, extra_origins="*")
        self.assertIn("*", origins)
        self.assertIsNone(regex)
        self.assertTrue(origin_allowed("https://evil.example.com", origins))

    def test_extra_origins_from_env(self):
        env = {"VTUBER_CORS_ORIGINS": "https://a.example, https://b.example/"}
        with mock.patch.dict(os.environ, env):
            origins, _ = resolve_cors_policy("127.0.0.1", 12393)
        self.assertIn("https://a.example", origins)
        self.assertIn("https://b.example", origins)
        self.assertNotIn("https://b.example/", origins)

    def test_no_origin_header_is_allowed(self):
        self.assertTrue(origin_allowed("", ["http://127.0.0.1:12393"]))
        self.assertTrue(origin_allowed(None, []))

    def test_static_headers_echo_allowed_origin(self):
        origins = ["http://127.0.0.1:12393"]
        scope = {"headers": [(b"origin", b"http://127.0.0.1:12393")]}
        headers = static_cors_headers(scope, origins, LOCAL_ORIGIN_REGEX)
        self.assertEqual(headers["Access-Control-Allow-Origin"], origins[0])
        self.assertEqual(headers["Vary"], "Origin")
        self.assertEqual(headers["Access-Control-Allow-Methods"], "GET, OPTIONS")

    def test_static_headers_skip_foreign_and_missing_origin(self):
        origins = ["http://127.0.0.1:12393"]
        foreign = {"headers": [(b"origin", b"https://evil.example.com")]}
        self.assertEqual(static_cors_headers(foreign, origins), {})
        self.assertEqual(static_cors_headers({"headers": []}, origins), {})

    def test_static_headers_with_wildcard(self):
        scope = {"headers": [(b"origin", b"https://a.example")]}
        headers = static_cors_headers(scope, ["*"])
        self.assertEqual(headers["Access-Control-Allow-Origin"], "*")
        self.assertNotIn("Vary", headers)


class MetricMathTests(unittest.TestCase):
    """Percentile/summary helpers (the p95 acceptance criterion depends on it)."""

    def test_percentile_matches_numpy_linear(self):
        self.assertIsNone(percentile([], 0.95))
        self.assertEqual(percentile([5], 0.95), 5.0)
        self.assertEqual(percentile([1, 2, 3, 4], 0.5), 2.5)
        self.assertEqual(percentile([1, 2, 3, 4], 0.95), 3.85)
        self.assertEqual(percentile([4, 1, 3, 2], 0.5), 2.5)

    def test_summarize_empty(self):
        self.assertEqual(
            summarize([]),
            {"count": 0, "avg": None, "p50": None, "p95": None, "max": None},
        )

    def test_summarize_values(self):
        summary = summarize([1.0, 2.0, 3.0, 4.0])
        self.assertEqual(summary["count"], 4)
        self.assertEqual(summary["avg"], 2.5)
        self.assertEqual(summary["p50"], 2.5)
        self.assertEqual(summary["p95"], 3.85)
        self.assertEqual(summary["max"], 4.0)


class TurnMetricsTests(unittest.TestCase):
    """Turn lifecycle: durations, outcomes, overlaps and bounded window."""

    def setUp(self):
        self.clock = FakeClock()
        self.metrics = TurnMetrics(window=3, clock=self.clock)

    def _complete_turn(self, key="c1", duration=2.0, first_audio=1.0):
        self.metrics.begin_turn(key)
        self.clock.advance(first_audio)
        self.metrics.first_audio(key)
        self.clock.advance(duration - first_audio)
        return self.metrics.end_turn(key, OUTCOME_COMPLETED)

    def test_completed_turn_record(self):
        record = self._complete_turn()
        self.assertEqual(record["outcome"], OUTCOME_COMPLETED)
        self.assertEqual(record["kind"], "text-input")
        self.assertEqual(record["duration_s"], 2.0)
        self.assertEqual(record["first_audio_s"], 1.0)

    def test_first_audio_only_once(self):
        self.metrics.begin_turn("c1")
        self.clock.advance(0.5)
        self.assertEqual(self.metrics.first_audio("c1"), 0.5)
        self.clock.advance(0.5)
        self.assertIsNone(self.metrics.first_audio("c1"))
        self.assertIsNone(self.metrics.first_audio("unknown"))

    def test_end_unknown_key_is_none(self):
        self.assertIsNone(self.metrics.end_turn("nobody"))

    def test_interrupted_and_failed_are_counted_but_not_timed(self):
        self._complete_turn()
        self.metrics.begin_turn("c2")
        self.clock.advance(1.0)
        self.metrics.end_turn("c2", OUTCOME_INTERRUPTED)
        self.metrics.begin_turn("c3")
        self.clock.advance(1.0)
        self.metrics.end_turn("c3", OUTCOME_FAILED)

        snapshot = self.metrics.snapshot()
        self.assertEqual(snapshot["turns"]["completed"], 1)
        self.assertEqual(snapshot["turns"]["interrupted"], 1)
        self.assertEqual(snapshot["turns"]["failed"], 1)
        self.assertEqual(snapshot["turn_seconds"]["count"], 1)

    def test_unknown_outcome_counts_as_completed(self):
        self.metrics.begin_turn("c1")
        self.clock.advance(1.0)
        self.metrics.end_turn("c1", "teleported")
        self.assertEqual(self.metrics.snapshot()["turns"]["completed"], 1)

    def test_overlap_is_flagged(self):
        self.metrics.begin_turn("c1")
        self.clock.advance(1.0)
        self.metrics.begin_turn("c1")
        snapshot = self.metrics.snapshot()
        self.assertEqual(snapshot["turns"]["overlaps"], 1)
        self.assertEqual(snapshot["turns"]["started"], 2)
        self.assertEqual(snapshot["turns"]["active"], 1)
        self.assertEqual(snapshot["active_turns"][0]["elapsed_s"], 0.0)

    def test_completed_without_audio_is_flagged(self):
        self.metrics.begin_turn("c1")
        self.clock.advance(1.0)
        self.metrics.end_turn("c1")
        self.assertEqual(self.metrics.snapshot()["turns"]["without_audio"], 1)

    def test_window_is_bounded(self):
        for duration in (1.0, 2.0, 5.0, 3.0):
            self._complete_turn(duration=duration, first_audio=0.5)
        turns = self.metrics.snapshot()["turn_seconds"]
        self.assertEqual(turns["count"], 3)
        self.assertEqual(turns["max"], 5.0)
        self.assertEqual(turns["avg"], round((2.0 + 5.0 + 3.0) / 3, 3))

    def test_snapshot_targets(self):
        self.assertIsNone(self.metrics.snapshot()["targets"]["p95_ok"])
        self._complete_turn(duration=TARGET_P95_TURN_SECONDS - 1)
        self.assertTrue(self.metrics.snapshot()["targets"]["p95_ok"])
        self._complete_turn(duration=TARGET_P95_TURN_SECONDS + 5)
        self.assertFalse(self.metrics.snapshot()["targets"]["p95_ok"])

    def test_queue_samples(self):
        self.metrics.note_queue_depth(2)
        self.metrics.note_queue_depth(5)
        self.metrics.note_queue_wait(1.5)
        self.metrics.note_queue_wait(-1)
        queue = self.metrics.snapshot()["queue"]
        self.assertEqual(queue["depth"], 5)
        self.assertEqual(queue["max_depth"], 5)
        self.assertEqual(queue["wait_seconds"]["max"], 1.5)
        self.assertEqual(queue["wait_seconds"]["count"], 2)

    def test_depth_rejects_negative(self):
        self.metrics.note_queue_depth(-4)
        self.assertEqual(self.metrics.snapshot()["queue"]["depth"], 0)

    def test_reset_turns_clears_state(self):
        self._complete_turn()
        self.metrics.reset_turns()
        snapshot = self.metrics.snapshot()
        self.assertEqual(snapshot["turns"]["started"], 0)
        self.assertEqual(snapshot["turn_seconds"]["count"], 0)
        self.assertIsNone(snapshot["last_turn"])


@unittest.skipUnless(INSTRUMENTATION_AVAILABLE, "conversation stack not importable")
class InstrumentationTests(unittest.TestCase):
    """The wrapped ``websocket_send`` marks first audio and the chain end."""

    def setUp(self):
        self.clock = FakeClock()
        self.metrics = TurnMetrics(window=10, clock=self.clock)
        patcher = mock.patch.object(conversation_utils, "turn_metrics", self.metrics)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.sent = []
        self.metrics.begin_turn("uid-1")

    async def _send(self, payload):
        async def raw(p):
            self.sent.append(p)

        sender = conversation_utils.instrument_websocket_send(raw, "uid-1")
        await sender(payload)
        return self.metrics.snapshot()

    def test_audio_marks_first_audio_once(self):
        self.clock.advance(0.75)
        snapshot = asyncio.run(
            self._send(json.dumps({"type": "audio", "audio": "BASE64"}))
        )
        self.assertEqual(snapshot["first_audio_seconds"]["count"], 1)
        self.assertAlmostEqual(snapshot["first_audio_seconds"]["max"], 0.75, places=3)
        self.assertEqual(snapshot["turns"]["completed"], 0)

        self.clock.advance(0.75)
        snapshot = asyncio.run(self._send(json.dumps({"type": "audio"})))
        self.assertEqual(snapshot["first_audio_seconds"]["count"], 1)

    def test_chain_end_completes_turn(self):
        self.clock.advance(2.0)
        end_payload = json.dumps(
            {"type": "control", "text": "conversation-chain-end"}
        )
        snapshot = asyncio.run(self._send(end_payload))
        self.assertEqual(snapshot["turns"]["completed"], 1)
        self.assertEqual(snapshot["turns"]["active"], 0)
        self.assertEqual(snapshot["turn_seconds"]["max"], 2.0)

    def test_other_control_messages_do_not_end_turn(self):
        snapshot = asyncio.run(
            self._send(json.dumps({"type": "control", "text": "mic-audio-end"}))
        )
        self.assertEqual(snapshot["turns"]["completed"], 0)
        self.assertEqual(snapshot["turns"]["active"], 1)

    def test_odd_payloads_are_forwarded_and_ignored(self):
        for payload in ("not json", json.dumps([1, 2]), json.dumps({"type": None})):
            snapshot = asyncio.run(self._send(payload))
            self.assertEqual(snapshot["turns"]["completed"], 0)
        self.assertEqual(len(self.sent), 3)
        self.assertEqual(self.sent[0], "not json")

    def test_forward_failure_still_propagates(self):
        async def raw(_payload):
            raise RuntimeError("socket gone")

        sender = conversation_utils.instrument_websocket_send(raw, "uid-1")
        with self.assertRaises(RuntimeError):
            asyncio.run(sender(json.dumps({"type": "audio"})))


@unittest.skipUnless(PROXY_QUEUE_AVAILABLE, "proxy_message_queue not importable")
class ProxyQueueTests(unittest.TestCase):
    """Queued messages carry a timestamp and feed the queue metrics."""

    def setUp(self):
        self.metrics = TurnMetrics(window=10)
        patcher = mock.patch.object(
            sys.modules["src.open_llm_vtuber.proxy_message_queue"],
            "turn_metrics",
            self.metrics,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.queue = ProxyMessageQueue()

    def test_queue_message_is_stamped_and_counted(self):
        self.queue.queue_message({"type": "text-input", "text": "hello"}, "uid-1")
        self.assertEqual(len(self.queue.message_queue), 1)
        item = self.queue.message_queue[0]
        self.assertIn("enqueued_at", item)
        self.assertIsInstance(item["enqueued_at"], float)
        self.assertEqual(item["sender_id"], "uid-1")

        self.queue.queue_message({"type": "text-input", "text": "again"})
        queue = self.metrics.snapshot()["queue"]
        self.assertEqual(queue["depth"], 2)
        self.assertEqual(queue["max_depth"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
