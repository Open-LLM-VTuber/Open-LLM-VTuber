"""Wiring verification for the openai_compat_tts / openai_compat_asr engines.

Complementary, NON-COLLIDING test for GLaDOS's OLVT kickoff:
- GLaDOS owns the engine unit tests (test_openai_compat_tts.py / test_openai_compat_asr.py).
- This file only verifies that both engines are wired into the TTS/ASR
  FACTORIES and the config_manager, i.e. selectable from conf.yaml.

No network calls: we only construct the engines and validate config parsing.
The TTS engine creates a "cache/" dir in cwd during __init__, so each test
that instantiates it runs inside a temp dir via monkeypatch.chdir.
"""

from __future__ import annotations

import os

from open_llm_vtuber.asr.asr_factory import ASRFactory
from open_llm_vtuber.asr.openai_compat_asr import VoiceRecognition as ExpectedASR
from open_llm_vtuber.config_manager.asr import ASRConfig, OpenAICompatASRConfig
from open_llm_vtuber.config_manager.tts import OpenAICompatTTSConfig, TTSConfig
from open_llm_vtuber.tts.openai_compat_tts import TTSEngine as ExpectedTTS
from open_llm_vtuber.tts.tts_factory import TTSFactory


# --------------------------------------------------------------------------
# Factory wiring
# --------------------------------------------------------------------------
def test_tts_factory_returns_openai_compat_engine(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine = TTSFactory.get_tts_engine(
        "openai_compat_tts",
        base_url="http://example:8880/v1",
        model="kokoro",
        voice="af_sky",
    )
    assert isinstance(engine, ExpectedTTS)
    assert engine.base_url == "http://example:8880/v1"
    assert engine.model == "kokoro"
    assert engine.voice == "af_sky"


def test_asr_factory_returns_openai_compat_engine(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine = ASRFactory.get_asr_system(
        "openai_compat_asr",
        base_url="http://example:8733/v1",
        model="base",
    )
    assert isinstance(engine, ExpectedASR)
    assert engine.base_url == "http://example:8733/v1"
    assert engine.model == "base"


def test_tts_factory_rejects_unknown_engine(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raised = False
    try:
        TTSFactory.get_tts_engine("definitely_not_a_real_engine")
    except ValueError:
        raised = True
    assert raised, "factory should raise ValueError for unknown engine_type"


# --------------------------------------------------------------------------
# config_manager wiring (the conf.yaml schema)
# --------------------------------------------------------------------------
def test_tts_config_supports_openai_compat():
    cfg = OpenAICompatTTSConfig(
        base_url="http://localhost:8880/v1", model="kokoro", voice="af_sky"
    )
    tts_config = TTSConfig(tts_model="openai_compat_tts", openai_compat_tts=cfg)
    assert tts_config.tts_model == "openai_compat_tts"
    dumped = tts_config.openai_compat_tts.model_dump()
    # These keys are exactly what the factory passes as **kwargs to the engine.
    assert {"base_url", "model", "voice", "api_key", "file_extension", "speed", "timeout"} <= set(
        dumped
    )


def test_asr_config_supports_openai_compat():
    cfg = OpenAICompatASRConfig(base_url="http://localhost:8733/v1")
    asr_config = ASRConfig(asr_model="openai_compat_asr", openai_compat_asr=cfg)
    assert asr_config.asr_model == "openai_compat_asr"
    dumped = asr_config.openai_compat_asr.model_dump()
    assert {"base_url", "model", "api_key", "language", "timeout"} <= set(dumped)


# --------------------------------------------------------------------------
# Full bridge: conf.yaml -> config -> factory (mirrors service_context.py)
# --------------------------------------------------------------------------
def test_tts_config_roundtrip_to_factory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = OpenAICompatTTSConfig(
        base_url="http://localhost:9999/v1", model="kokoro", voice="af_sky"
    )
    tts_config = TTSConfig(tts_model="openai_compat_tts", openai_compat_tts=cfg)
    engine = TTSFactory.get_tts_engine(
        tts_config.tts_model,
        **getattr(tts_config, tts_config.tts_model.lower()).model_dump(),
    )
    assert isinstance(engine, ExpectedTTS)
    assert engine.base_url == "http://localhost:9999/v1"


def test_asr_config_roundtrip_to_factory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = OpenAICompatASRConfig(base_url="http://localhost:9998/v1")
    asr_config = ASRConfig(asr_model="openai_compat_asr", openai_compat_asr=cfg)
    engine = ASRFactory.get_asr_system(
        asr_config.asr_model,
        **getattr(asr_config, asr_config.asr_model).model_dump(),
    )
    assert isinstance(engine, ExpectedASR)
    assert engine.base_url == "http://localhost:9998/v1"


if __name__ == "__main__":
    # Allow a quick `python tests/test_openai_compat_wiring.py` sanity run.
    import tempfile

    for fn in (
        test_tts_factory_returns_openai_compat_engine,
        test_asr_factory_returns_openai_compat_engine,
        test_tts_factory_rejects_unknown_engine,
        test_tts_config_supports_openai_compat,
        test_asr_config_supports_openai_compat,
        test_tts_config_roundtrip_to_factory,
        test_asr_config_roundtrip_to_factory,
    ):
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            fn()
    print("all wiring checks passed")
