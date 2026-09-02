"""Doc-accuracy tests for the OpenAI-compatible engine sample configs.

The ``doc/sample_conf/openai_compat_*.yaml`` files are the user-facing
documentation for how to configure these engines in ``conf.yaml``. These
tests guarantee the documented keys can NEVER silently drift from the
engines' real constructors: if ``TTSEngine`` or ``VoiceRecognition`` gains
or loses a parameter, the matching sample config must be updated or this
test fails.

Fully offline — parses YAML only, no network, no running server.
"""

import inspect
import os

import pytest
import ruamel.yaml

import open_llm_vtuber.asr.openai_compat_asr
import open_llm_vtuber.tts.openai_compat_tts  # noqa: F401  (ensure importable)
from open_llm_vtuber.asr.openai_compat_asr import VoiceRecognition
from open_llm_vtuber.tts.openai_compat_tts import TTSEngine

_YAML = ruamel.yaml.YAML(typ="safe")

SAMPLES = {
    "doc/sample_conf/openai_compat_tts.yaml": TTSEngine,
    "doc/sample_conf/openai_compat_asr.yaml": VoiceRecognition,
}


def _constructor_args(cls) -> set[str]:
    sig = inspect.signature(cls.__init__)
    return {name for name in sig.parameters if name != "self"}


@pytest.mark.parametrize("path,cls", list(SAMPLES.items()))
def test_sample_conf_matches_engine_constructor(path: str, cls) -> None:
    here = os.path.dirname(__file__)
    full = os.path.join(here, "..", path)
    assert os.path.exists(full), f"sample config missing: {full}"
    with open(full) as f:
        conf = _YAML.load(f)

    assert isinstance(conf, dict), f"{path} must be a flat mapping of options"
    documented = set(conf.keys())
    actual = _constructor_args(cls)
    assert documented == actual, (
        f"{path} documents {sorted(documented)} but "
        f"{cls.__name__}.__init__ expects {sorted(actual)}"
    )


def test_sample_conf_values_are_plausible() -> None:
    """Sanity: the documented defaults look like real endpoints/params."""
    here = os.path.dirname(__file__)

    with open(os.path.join(here, "..", "doc/sample_conf/openai_compat_tts.yaml")) as f:
        tts = _YAML.load(f)
    with open(os.path.join(here, "..", "doc/sample_conf/openai_compat_asr.yaml")) as f:
        asr = _YAML.load(f)

    assert tts["base_url"].endswith("/v1")
    assert asr["base_url"].endswith("/v1")
    assert tts["file_extension"] in {"mp3", "wav", "ogg", "opus", "aac", "flac"}
    assert isinstance(asr["timeout"], int) and asr["timeout"] > 0
