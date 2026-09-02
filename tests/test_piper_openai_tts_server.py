"""Offline tests for the standalone Piper OpenAI-compatible TTS server.

These use a fake `piper` binary (copies stdin to the output file) so no model
or network is required. The server's audio-rendering logic is isolated in
``synthesize()`` and the request mapping in ``resolve_model``/``response_ext``.
"""

import importlib.util
import os
import stat
import tempfile

import pytest

_FAKE_PIPER = """#!/bin/sh
cat > "$4"
"""

_FAKE_PIPER_FAIL = """#!/bin/sh
echo "boom" >&2
exit 3
"""


def _load(mod_rel, fake_piper_src, piper_bin_env):
    d = tempfile.mkdtemp()
    script = os.path.join(d, "piper")
    with open(script, "w") as f:
        f.write(fake_piper_src)
    os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC)
    os.environ["PIPER_BIN"] = script
    spec = importlib.util.spec_from_file_location(
        "piper_srv_ut", os.path.join(os.path.dirname(__file__), "..", mod_rel)
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def mod():
    return _load("piper_openai_tts_server.py", _FAKE_PIPER, "PIPER_BIN")


def test_resolve_model_fallback(mod):
    assert mod.resolve_model("glados").endswith("glados.onnx")
    assert mod.resolve_model("zzz").endswith("hal.onnx")  # unknown -> hal


def test_response_ext(mod):
    assert mod.response_ext("mp3") == "mp3"
    assert mod.response_ext("wav") == "wav"
    assert mod.response_ext(None) == "wav"


def test_synthesize_wav(mod):
    audio = mod.synthesize("hello world", mod.resolve_model("glados"), "wav")
    assert audio == b"hello world"


def test_synthesize_mp3_ext(mod):
    audio = mod.synthesize("abc", mod.resolve_model("hal"), "mp3")
    assert audio == b"abc"


def test_synthesize_piper_failure_raises(tmp_path, monkeypatch):
    d = str(tmp_path)
    script = os.path.join(d, "piper_fail")
    with open(script, "w") as f:
        f.write(_FAKE_PIPER_FAIL)
    os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PIPER_BIN", script)
    spec = importlib.util.spec_from_file_location(
        "piper_srv_fail",
        os.path.join(os.path.dirname(__file__), "..", "piper_openai_tts_server.py"),
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    with pytest.raises(RuntimeError):
        m.synthesize("x", m.resolve_model("glados"), "wav")
