"""Unit tests for the phase 3 stage-update contract and the OBS controller.

Standalone on purpose (same approach as ``scripts/test_audio_hardening.py``):
a bare interpreter may miss ``loguru`` and ``websockets``, so both are shimmed
before importing the modules under test. The OBS peer is a fake socket that
speaks OBS WebSocket v5; nothing here opens a network connection.

    python scripts/test_stage_obs.py
    python scripts/test_stage_obs.py -v OBSControllerTests
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import sys
import types
import unittest
from unittest import mock

# Add project root to path to enable imports (same as the live scripts).
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def _install_loguru_shim() -> None:
    """Allow modules that only use ``loguru`` for logging to import."""
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

        def debug(self, msg, *a, **k):
            self._log.debug(msg, *a, **k)

        def info(self, msg, *a, **k):
            self._log.info(msg, *a, **k)

        def warning(self, msg, *a, **k):
            self._log.warning(msg, *a, **k)

        def error(self, msg, *a, **k):
            self._log.error(msg, *a, **k)

        def critical(self, msg, *a, **k):
            self._log.critical(msg, *a, **k)

        def exception(self, msg, *a, **k):
            self._log.exception(msg, *a, **k)

    module = types.ModuleType("loguru")
    module.logger = _ShimLogger()
    sys.modules["loguru"] = module


def _install_websockets_shim() -> None:
    """Provide ``websockets.connect``/``exceptions`` when the runtime lacks them."""
    try:
        import websockets  # noqa: F401

        return
    except ImportError:
        pass

    exceptions = types.ModuleType("websockets.exceptions")

    class ConnectionClosed(Exception):
        """Stand-in for ``websockets.exceptions.ConnectionClosed``."""

    exceptions.ConnectionClosed = ConnectionClosed

    module = types.ModuleType("websockets")
    module.exceptions = exceptions
    module.ConnectionClosed = ConnectionClosed
    module.connect = None  # replaced by every test that needs a fake peer

    sys.modules["websockets"] = module
    sys.modules["websockets.exceptions"] = exceptions


_install_loguru_shim()
_install_websockets_shim()

from src.open_llm_vtuber.scheduler import obs as obs_module  # noqa: E402
from src.open_llm_vtuber.scheduler import service as service_module  # noqa: E402
from src.open_llm_vtuber.utils.stage import (  # noqa: E402
    MAX_LABEL,
    MAX_SUBLABEL,
    build_stage_payload,
    select_stage_targets,
)


def _documented_auth(password: str, salt: str, challenge: str) -> str:
    """Independent implementation of OBS's authentication algorithm."""
    secret = base64.b64encode(
        hashlib.sha256((password + salt).encode("utf-8")).digest()
    )
    return base64.b64encode(
        hashlib.sha256(secret + challenge.encode("utf-8")).digest()
    ).decode("ascii")


class FakeOBSSocket:
    """Fake OBS v5 peer: sends Hello, validates Identify and answers requests."""

    SALT = "salt123"
    CHALLENGE = "challenge456"

    def __init__(self, password: str = "", fail_with: dict | None = None):
        self.password = password
        self.fail_with = fail_with or {}
        self.sent = []
        self.requests = []
        self.closed = False
        self.identified = False
        self._inbox = asyncio.Queue()
        # OBS always speaks first: the Hello message is waiting in the inbox.
        hello = {"obsWebSocketVersion": "5.4.2", "rpcVersion": 1}
        if password:
            hello["authentication"] = {
                "challenge": self.CHALLENGE,
                "salt": self.SALT,
            }
        self._inbox.put_nowait(json.dumps({"op": obs_module.OP_HELLO, "d": hello}))

    async def recv(self):
        """Next queued server message."""
        return await self._inbox.get()

    def _queue(self, message: dict) -> None:
        """Queue a server message without leaving the current task."""
        self._inbox.put_nowait(json.dumps(message))

    async def send(self, raw: str) -> None:
        """Handle what the client wrote to the socket."""
        message = json.loads(raw)
        self.sent.append(message)
        op = message.get("op")
        data = message.get("d") or {}

        if op == obs_module.OP_IDENTIFY:
            auth = data.get("authentication")
            expected = (
                _documented_auth(self.password, self.SALT, self.CHALLENGE)
                if self.password
                else None
            )
            if (self.password and auth != expected) or (
                not self.password and auth is not None
            ):
                # Wrong password: OBS closes the socket without Identified.
                # A non-Identified op models that close from the client side.
                self._queue({"op": 9, "d": {"error": "authentication failed"}})
                return
            self.identified = True
            self._queue(
                {"op": obs_module.OP_IDENTIFIED, "d": {"negotiatedRpcVersion": 1}}
            )
            # Unrelated event: the client must skip it while awaiting a reply.
            self._queue({"op": 5, "d": {"eventType": "Heartbeat"}})
            return

        if op == obs_module.OP_REQUEST:
            request_type = data["requestType"]
            self.requests.append(request_type)
            failure = self.fail_with.get(request_type)
            if failure:
                status = {"result": False, "code": 600, "comment": failure}
                response_data = {}
            else:
                status = {"result": True, "code": 100}
                response_data = {}
                if request_type == "GetSceneList":
                    response_data = {
                        "scenes": [
                            {"sceneName": "tarot_main"},
                            {"sceneName": "ending"},
                        ]
                    }
            self._queue(
                {
                    "op": obs_module.OP_REQUEST_RESPONSE,
                    "d": {
                        "requestType": request_type,
                        # A foreign response arrives first on purpose.
                        "requestId": "not-ours",
                        "requestStatus": {"result": True, "code": 100},
                        "responseData": {},
                    },
                }
            )
            self._queue(
                {
                    "op": obs_module.OP_REQUEST_RESPONSE,
                    "d": {
                        "requestType": request_type,
                        "requestId": data["requestId"],
                        "requestStatus": status,
                        "responseData": response_data,
                    },
                }
            )

    async def close(self) -> None:
        """Record the close; the client may call it several times."""
        self.closed = True


def _run(coro):
    """Run a coroutine on a fresh loop (no pytest-asyncio in this repo)."""
    return asyncio.run(coro)


class StagePayloadTests(unittest.TestCase):
    """The overlay contract documented in AUDITORIA-MVP-TAROT.md §2.4."""

    def test_minimal_payload(self):
        payload = build_stage_payload(stage="tarot_main", background="/bg/table.png")
        self.assertEqual(payload["type"], "stage-update")
        self.assertEqual(payload["stage"], "tarot_main")
        self.assertEqual(payload["background"], "/bg/table.png")
        self.assertEqual(payload["transition"], "fade")
        self.assertEqual(payload["duration_ms"], 800)
        self.assertNotIn("props", payload)

    def test_stage_is_trimmed_and_truncated(self):
        payload = build_stage_payload(stage="  " + "x" * 90 + "  ")
        self.assertEqual(payload["stage"], "x" * 64)

    def test_props_are_normalised(self):
        payload = build_stage_payload(
            stage="reading",
            props=[
                {"id": "card_1", "src": "/bg/death.png", "x": 0.7, "y": -3},
                "not-a-dict",
                {"id": "no-src"},
                {"src": "  /bg/moon.png  ", "opacity": 2},
            ],
        )
        props = payload["props"]
        self.assertEqual(len(props), 2)
        self.assertEqual(props[0]["id"], "card_1")
        self.assertEqual(props[0]["x"], 0.7)
        self.assertEqual(props[0]["y"], 0.0)  # clamped to the 0..1 range
        self.assertEqual(props[1]["src"], "/bg/moon.png")
        self.assertEqual(props[1]["id"], "prop_3")  # index-based fallback
        self.assertEqual(props[1]["opacity"], 1.0)

    def test_props_are_capped(self):
        props = [{"src": f"/bg/{i}.png"} for i in range(50)]
        payload = build_stage_payload(props=props)
        self.assertEqual(len(payload["props"]), 32)

    def test_transition_falls_back_to_fade(self):
        payload = build_stage_payload(stage="x", transition="wipe")
        self.assertEqual(payload["transition"], "fade")

    def test_duration_is_clamped(self):
        self.assertEqual(
            build_stage_payload(stage="x", duration_ms=-50)["duration_ms"], 0
        )
        self.assertEqual(
            build_stage_payload(stage="x", duration_ms="999999")["duration_ms"], 10000
        )
        self.assertEqual(
            build_stage_payload(stage="x", duration_ms="nope")["duration_ms"], 800
        )

    def test_empty_payload_is_rejected(self):
        with self.assertRaises(ValueError):
            build_stage_payload()
        with self.assertRaises(ValueError):
            build_stage_payload(stage="   ", background="  ", props=[{"id": "x"}])

    def test_label_props_need_no_art(self):
        payload = build_stage_payload(
            stage="card_of_the_day",
            props=[
                {"id": "card_1", "label": "La Torre", "sublabel": "ruptura · verdad"},
                {"label": "El Sol"},
            ],
        )
        self.assertNotIn("background", payload)
        self.assertEqual(len(payload["props"]), 2)
        first = payload["props"][0]
        self.assertEqual(first["label"], "La Torre")
        self.assertEqual(first["sublabel"], "ruptura · verdad")
        self.assertNotIn("src", first)
        self.assertEqual(payload["props"][1]["id"], "prop_1")
        self.assertNotIn("sublabel", payload["props"][1])

    def test_label_is_trimmed_and_capped(self):
        payload = build_stage_payload(
            props=[{"label": "  " + "x" * 120 + "  ", "sublabel": "y" * 200}]
        )
        prop = payload["props"][0]
        self.assertEqual(prop["label"], "x" * MAX_LABEL)
        self.assertEqual(prop["sublabel"], "y" * MAX_SUBLABEL)

    def test_src_wins_over_label(self):
        payload = build_stage_payload(props=[{"src": "/bg/a.png", "label": "La Torre"}])
        prop = payload["props"][0]
        self.assertEqual(prop["src"], "/bg/a.png")
        self.assertNotIn("label", prop)

    def test_blank_label_is_dropped(self):
        payload = build_stage_payload(stage="x", props=[{"id": "a", "label": "   "}])
        self.assertNotIn("props", payload)

    def test_target_selection(self):
        uids = ["overlay", "guest"]
        self.assertEqual(select_stage_targets(uids), ["overlay"])
        self.assertEqual(select_stage_targets(uids, "first"), ["overlay"])
        self.assertEqual(select_stage_targets(uids, "all"), uids)
        self.assertEqual(select_stage_targets(uids, "guest"), ["guest"])
        self.assertEqual(select_stage_targets(uids, "ghost"), [])
        self.assertEqual(select_stage_targets([], "first"), [])


class OBSAuthTests(unittest.TestCase):
    """The authentication string must match OBS's documented algorithm."""

    def test_matches_manual_computation(self):
        expected = _documented_auth("secret", "salt", "challenge")
        actual = obs_module.build_auth_string("secret", "salt", "challenge")
        self.assertEqual(actual, expected)

    def test_known_vector(self):
        # Independent, byte-level implementation of the documented algorithm.
        secret = base64.b64encode(hashlib.sha256(b"passwordsalt").digest())
        expected = base64.b64encode(
            hashlib.sha256(secret + b"challenge").digest()
        ).decode("ascii")
        self.assertEqual(
            obs_module.build_auth_string("password", "salt", "challenge"), expected
        )

    def test_salt_and_challenge_change_the_result(self):
        base = obs_module.build_auth_string("pw", "salt", "challenge")
        self.assertNotEqual(
            base, obs_module.build_auth_string("pw", "other", "challenge")
        )
        self.assertNotEqual(base, obs_module.build_auth_string("pw", "salt", "other"))


class OBSControllerTests(unittest.IsolatedAsyncioTestCase):
    """Protocol behaviour against a fake OBS v5 peer (no sockets involved).

    ``IsolatedAsyncioTestCase`` gives every test its own event loop, which is
    required because the fake socket uses an ``asyncio.Queue``.
    """

    def _controller(self, peer, **kwargs):
        patcher = mock.patch.object(
            obs_module.websockets, "connect", _fake_connect(peer)
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return obs_module.OBSController(**kwargs)

    async def test_connect_without_password(self):
        peer = FakeOBSSocket()
        controller = self._controller(peer)
        self.assertTrue(await controller.connect())
        self.assertTrue(controller.connected)
        identify = peer.sent[0]
        self.assertEqual(identify["op"], obs_module.OP_IDENTIFY)
        self.assertEqual(identify["d"]["rpcVersion"], 1)
        self.assertNotIn("authentication", identify["d"])

    async def test_connect_with_password(self):
        peer = FakeOBSSocket(password="secret")
        controller = self._controller(peer, password="secret")
        self.assertTrue(await controller.connect())
        identify = peer.sent[0]
        self.assertEqual(
            identify["d"]["authentication"],
            _documented_auth("secret", FakeOBSSocket.SALT, FakeOBSSocket.CHALLENGE),
        )

    async def test_missing_password_fails_without_crashing(self):
        peer = FakeOBSSocket(password="secret")
        controller = self._controller(peer)
        self.assertFalse(await controller.connect())
        self.assertFalse(controller.connected)

    async def test_wrong_password_fails_without_crashing(self):
        peer = FakeOBSSocket(password="secret")
        controller = self._controller(peer, password="wrong")
        self.assertFalse(await controller.connect())
        self.assertFalse(controller.connected)

    async def test_unreachable_obs_returns_false(self):
        def boom(*_args, **_kwargs):
            raise OSError("connection refused")

        patcher = mock.patch.object(obs_module.websockets, "connect", boom)
        patcher.start()
        self.addCleanup(patcher.stop)

        controller = obs_module.OBSController(port=1)
        self.assertFalse(await controller.connect())
        self.assertFalse(controller.connected)
        # Public actions stay safe when OBS is down.
        self.assertFalse(await controller.set_scene("tarot_main"))
        self.assertFalse(await controller.start_stream())
        self.assertEqual(await controller.list_scenes(), [])

    async def test_set_scene_switches_the_program_scene(self):
        peer = FakeOBSSocket()
        controller = self._controller(peer)
        await controller.connect()
        self.assertTrue(await controller.set_scene("ending"))
        self.assertEqual(peer.requests, ["SetCurrentProgramScene"])
        request = peer.sent[-1]["d"]
        self.assertEqual(request["requestData"], {"sceneName": "ending"})

    async def test_set_scene_reports_obs_errors(self):
        peer = FakeOBSSocket(fail_with={"SetCurrentProgramScene": "no such scene"})
        controller = self._controller(peer)
        await controller.connect()
        self.assertFalse(await controller.set_scene("ghost"))
        self.assertTrue(controller.connected)  # a rejected request keeps the link

    async def test_list_scenes(self):
        peer = FakeOBSSocket()
        controller = self._controller(peer)
        await controller.connect()
        self.assertEqual(await controller.list_scenes(), ["tarot_main", "ending"])

    async def test_stream_actions(self):
        peer = FakeOBSSocket()
        controller = self._controller(peer)
        await controller.connect()
        self.assertTrue(await controller.start_stream())
        self.assertTrue(await controller.stop_stream())
        self.assertEqual(peer.requests, ["StartStream", "StopStream"])

    async def test_unknown_op_while_waiting_is_ignored(self):
        # The fake queues a Heartbeat event plus a foreign requestId before the
        # real response; the client must keep waiting and resolve the request.
        peer = FakeOBSSocket()
        controller = self._controller(peer)
        await controller.connect()
        self.assertTrue(await controller.set_scene("tarot_main"))


def _fake_connect(peer):
    """Return an async ``websockets.connect`` replacement bound to ``peer``."""

    async def connect(*_args, **_kwargs):
        return peer

    return connect


class _FakeOBS:
    """Records the controller calls made by the scheduler."""

    def __init__(self, connected: bool = True):
        self.connected = connected
        self.scenes = []

    async def connect(self) -> bool:
        return self.connected

    async def list_scenes(self):
        return ["tarot_main", "ending"]

    async def start_stream(self) -> bool:
        self.scenes.append("__start_stream__")
        return True

    async def stop_stream(self) -> bool:
        self.scenes.append("__stop_stream__")
        return True

    async def set_scene(self, scene_name: str) -> bool:
        self.scenes.append(scene_name)
        return True

    async def close(self) -> None:
        self.scenes.append("__close__")


class _FakeWSHandler:
    """Minimal ``WebSocketHandler`` surface used by ``_prepare_stage``/``_fire``."""

    def __init__(self):
        self.client_connections = {"overlay-1": object()}
        self.current_stage = None
        self.stage_updates = []
        self.spoken = []

    async def broadcast_stage_update(self, payload, target_client="first"):
        self.stage_updates.append((payload, target_client))
        self.current_stage = payload
        return 1

    async def trigger_proactive_speak(self, client_uid, text):
        self.spoken.append((client_uid, text))
        return True


def _scheduler_config(obs_enabled: bool = False, switch_scenes: bool = True):
    """Build the subset of ``SchedulerConfig`` the scheduler service reads."""
    return types.SimpleNamespace(
        enabled=True,
        timezone="Europe/Madrid",
        target_client="first",
        obs=types.SimpleNamespace(
            enabled=obs_enabled,
            host="127.0.0.1",
            port=4455,
            password="",
            timeout=1.0,
            start_stream=False,
            stop_stream_on_shutdown=False,
            switch_scenes=switch_scenes,
        ),
        jobs=[],
    )


def _job(**overrides):
    """Build a job with the same fields as ``ScheduledJob``."""
    base = {
        "name": "card_of_the_day",
        "cron": "",
        "interval_minutes": 0,
        "text": "",
        "scene": "",
        "background": "",
        "transition": "fade",
        "duration_ms": 800,
        "draw": 0,
        "draw_seed": 0,
        "question": "",
        "enabled": True,
    }
    base.update(overrides)
    return types.SimpleNamespace(**base)


class SchedulerStageTests(unittest.TestCase):
    """``_prepare_stage`` ties the OBS scene to the overlay stage-update."""

    def _service(self, obs_enabled: bool = True, switch_scenes: bool = True):
        ws = _FakeWSHandler()
        service = service_module.SchedulerService(
            ws, _scheduler_config(obs_enabled, switch_scenes)
        )
        return service, ws

    def test_disabled_obs_creates_no_controller(self):
        service, _ = self._service(obs_enabled=False)
        self.assertIsNone(service._obs)

    def test_enabled_obs_creates_a_controller(self):
        service, _ = self._service(obs_enabled=True)
        self.assertIsInstance(service._obs, obs_module.OBSController)

    def test_scene_and_background_are_applied(self):
        service, ws = self._service()
        service._obs = _FakeOBS()

        _run(
            service._prepare_stage(
                _job(scene="tarot_main", background="/bg/tarot_table.png")
            )
        )

        self.assertEqual(service._obs.scenes, ["tarot_main"])
        self.assertEqual(len(ws.stage_updates), 1)
        payload, target = ws.stage_updates[0]
        self.assertEqual(payload["type"], "stage-update")
        self.assertEqual(payload["stage"], "card_of_the_day")
        self.assertEqual(payload["background"], "/bg/tarot_table.png")
        self.assertEqual(target, "first")

    def test_switch_scenes_can_be_disabled(self):
        service, ws = self._service(switch_scenes=False)
        service._obs = _FakeOBS()

        _run(service._prepare_stage(_job(scene="ending", background="/bg/end.png")))

        self.assertEqual(service._obs.scenes, [])
        self.assertEqual(len(ws.stage_updates), 1)

    def test_missing_obs_only_logs_the_scene(self):
        # obs.enabled is false: the scene change is skipped, the overlay still
        # receives its background so a manual OBS setup keeps working.
        service, ws = self._service(obs_enabled=False)

        _run(service._prepare_stage(_job(scene="ending", background="/bg/end.png")))

        self.assertEqual(len(ws.stage_updates), 1)
        self.assertEqual(ws.stage_updates[0][0]["background"], "/bg/end.png")

    def test_job_without_background_does_not_touch_the_overlay(self):
        service, ws = self._service()
        service._obs = _FakeOBS()

        _run(service._prepare_stage(_job(scene="tarot_main")))

        self.assertEqual(service._obs.scenes, ["tarot_main"])
        self.assertEqual(ws.stage_updates, [])


class SchedulerDrawTests(unittest.TestCase):
    """A job with ``draw`` puts the spread on screen and in the prompt."""

    def _service(self):
        ws = _FakeWSHandler()
        service = service_module.SchedulerService(
            ws, _scheduler_config(obs_enabled=False)
        )
        return service, ws

    def test_draw_becomes_art_props(self):
        service, ws = self._service()

        _run(service._fire(_job(draw=3, draw_seed=11, scene="tarot_main")))

        self.assertEqual(len(ws.stage_updates), 1)
        payload, _ = ws.stage_updates[0]
        self.assertEqual(payload["stage"], "card_of_the_day")
        self.assertNotIn("background", payload)
        self.assertEqual(
            [prop["id"] for prop in payload["props"]],
            ["card_1", "card_2", "card_3"],
        )
        for prop in payload["props"]:
            self.assertRegex(prop["src"], r"^/bg/cards/major_\d\d\.svg$")
            self.assertEqual(prop["scale"], 0.55)
            self.assertNotIn("label", prop, "the deck has art, so no text cards")

    def test_the_spoken_text_mentions_the_cards(self):
        service, ws = self._service()
        job = _job(draw=1, draw_seed=11, question="¿Me cambio de trabajo?")

        _run(service._fire(job))

        _, text = ws.spoken[0]
        drawn = service._draw(job)
        self.assertIn(drawn[0].card.name, text)
        self.assertIn("¿Me cambio de trabajo?", text)

    def test_seed_replays_the_same_spread(self):
        service, ws = self._service()
        job = _job(draw=3, draw_seed=4242)

        _run(service._fire(job))
        _run(service._fire(job))

        self.assertEqual(
            ws.stage_updates[0][0]["props"], ws.stage_updates[1][0]["props"]
        )

    def test_invalid_draw_still_speaks(self):
        # pydantic caps draw at 3; a bad value from elsewhere must not kill the
        # segment: it is logged and the job is spoken without cards.
        service, ws = self._service()

        _run(service._fire(_job(draw=9, text="Sigue leyendo.")))

        self.assertEqual(ws.stage_updates, [])
        self.assertIn("Sigue leyendo.", ws.spoken[0][1])

    def test_no_draw_keeps_the_old_behaviour(self):
        service, ws = self._service()

        _run(service._fire(_job(text="Hola.")))

        self.assertEqual(ws.stage_updates, [])
        self.assertEqual(ws.spoken[0][1], "Hola.")

    def test_compose_text(self):
        self.assertEqual(service_module.SchedulerService._compose_text(_job(), []), "")
        self.assertEqual(
            service_module.SchedulerService._compose_text(_job(text="Hola."), []),
            "Hola.",
        )

    def test_compose_text_puts_the_brief_first(self):
        with mock.patch.object(
            service_module, "build_tarot_brief", return_value="BRIEF"
        ):
            text = service_module.SchedulerService._compose_text(
                _job(text="Hola."), [object()]
            )
        self.assertEqual(text, "BRIEF\n\nHola.")


if __name__ == "__main__":
    unittest.main()
