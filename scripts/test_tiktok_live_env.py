"""Unit tests for the optional TikTokLive environment knobs.

`_env_client_options()` is the only place where a room abroad (a French room
read from LatAm) is configured: webcast region, Euler Stream signing key and
proxy. TikTokLive is not installed in this environment, so its modules are
stubbed before import; nothing here opens a network connection.

    python scripts/test_tiktok_live_env.py
"""

import asyncio
import logging
import os
import sys
import types
import unittest
from unittest import mock

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def _module(name, **attrs):
    """Create and register a stub module (packages need ``__path__``)."""
    module = types.ModuleType(name)
    module.__path__ = []
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _install_loguru_stub():
    class _Logger:
        def __init__(self):
            self._log = logging.getLogger("loguru")

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

        def exception(self, msg, *a, **k):
            self._log.exception(msg, *a, **k)

    _module("loguru", logger=_Logger())


def _install_websockets_stub():
    class ConnectionClosed(Exception):
        """Stand-in for websockets.ConnectionClosed."""

    _module("websockets", connect=None, ConnectionClosed=ConnectionClosed)


def _install_tiktoklive_stub():
    class TikTokLiveClient:
        last_kwargs = None

        def __init__(self, **kwargs):
            type(self).last_kwargs = kwargs

        def on(self, _event):
            def decorator(fn):
                return fn

            return decorator

    class _Event:
        pass

    tiktok = _module(
        "TikTokLive",
        TikTokLiveClient=TikTokLiveClient,
    )
    _module(
        "TikTokLive.events",
        CommentEvent=_Event,
        FollowEvent=_Event,
        GiftEvent=_Event,
    )
    client_pkg = _module("TikTokLive.client")
    web_pkg = _module("TikTokLive.client.web")
    defaults = types.SimpleNamespace(
        web_client_params={"region": "GB", "priority_region": "GB"},
        tiktok_sign_api_key=None,
    )
    settings = _module("TikTokLive.client.web.web_settings", WebDefaults=defaults)
    tiktok.events = sys.modules["TikTokLive.events"]
    tiktok.client = client_pkg
    client_pkg.web = web_pkg
    web_pkg.web_settings = settings
    return TikTokLiveClient, defaults


def _install_httpx_stub():
    class Proxy:
        def __init__(self, url):
            if "://" not in url:
                raise ValueError("invalid proxy URL")
            self.url = url

    _module("httpx", Proxy=Proxy)


_install_loguru_stub()
_install_websockets_stub()
TikTokLiveClient, WebDefaults = _install_tiktoklive_stub()
_install_httpx_stub()

from src.open_llm_vtuber.live import tiktok_live as connector  # noqa: E402


class EnvClientOptionsTests(unittest.TestCase):
    """The environment is the only configuration surface of the connector."""

    def setUp(self):
        patcher = mock.patch.dict(os.environ, {}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        WebDefaults.web_client_params = {"region": "GB", "priority_region": "GB"}
        WebDefaults.tiktok_sign_api_key = None
        TikTokLiveClient.last_kwargs = None

    def test_empty_environment_keeps_defaults(self):
        self.assertEqual(connector._env_client_options(), {})
        self.assertEqual(WebDefaults.web_client_params["region"], "GB")
        self.assertIsNone(WebDefaults.tiktok_sign_api_key)

    def test_region_is_uppercased_and_applied(self):
        with mock.patch.dict(os.environ, {"TIKTOKLIVE_REGION": " fr "}):
            options = connector._env_client_options()
        self.assertEqual(options, {})
        self.assertEqual(WebDefaults.web_client_params["region"], "FR")
        self.assertEqual(WebDefaults.web_client_params["priority_region"], "FR")

    def test_signing_key_is_applied(self):
        with mock.patch.dict(os.environ, {"TIKTOKLIVE_SIGN_API_KEY": " key-123 "}):
            options = connector._env_client_options()
        self.assertEqual(options, {})
        self.assertEqual(WebDefaults.tiktok_sign_api_key, "key-123")

    def test_proxy_is_used_for_both_legs(self):
        url = "http://user:pass@127.0.0.1:3128"
        with mock.patch.dict(os.environ, {"TIKTOKLIVE_PROXY": url}):
            options = connector._env_client_options()
        self.assertEqual(set(options), {"web_proxy", "ws_proxy"})
        self.assertIs(options["web_proxy"], options["ws_proxy"])
        self.assertEqual(options["web_proxy"].url, url)

    def test_invalid_proxy_is_ignored(self):
        with mock.patch.dict(os.environ, {"TIKTOKLIVE_PROXY": "not-a-url"}):
            self.assertEqual(connector._env_client_options(), {})

    def test_all_knobs_together(self):
        env = {
            "TIKTOKLIVE_REGION": "fr",
            "TIKTOKLIVE_SIGN_API_KEY": "k",
            "TIKTOKLIVE_PROXY": "http://127.0.0.1:3128",
        }
        with mock.patch.dict(os.environ, env):
            options = connector._env_client_options()
        self.assertEqual(WebDefaults.web_client_params["region"], "FR")
        self.assertEqual(WebDefaults.tiktok_sign_api_key, "k")
        self.assertIn("web_proxy", options)

    def test_run_forwards_the_options_to_the_client(self):
        """The single call site in ``run()`` must pass the env options."""

        class StopRun(RuntimeError):
            pass

        def fake_start(_self):
            raise StopRun("stop before connecting")

        TikTokLiveClient.start = fake_start

        platform = connector.TikTokLivePlatform(unique_id="@someone")

        async def fake_connect(*_args, **_kwargs):
            return True

        async def never_ends():
            await asyncio.Event().wait()

        platform.connect = fake_connect
        platform.start_receiving = never_ends

        env = {
            "TIKTOKLIVE_REGION": "FR",
            "TIKTOKLIVE_PROXY": "http://127.0.0.1:3128",
        }
        with mock.patch.dict(os.environ, env):
            with self.assertRaises(StopRun):
                asyncio.run(platform.run())

        kwargs = TikTokLiveClient.last_kwargs
        self.assertEqual(kwargs["unique_id"], "@someone")
        self.assertEqual(WebDefaults.web_client_params["region"], "FR")
        self.assertIn("web_proxy", kwargs)
        self.assertIn("ws_proxy", kwargs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
