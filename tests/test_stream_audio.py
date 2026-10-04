"""Tests for :mod:`open_llm_vtuber.utils.stream_audio`.

``prepare_audio_payload`` converts a generated audio file into the payload the
frontend receives (base64 audio plus per-chunk volumes for the mouth animation),
and returns a silent payload when there is nothing to play.  The test audio is
written with the standard library, so no ffmpeg install is required.
"""

from __future__ import annotations

import base64
import math
import wave
from array import array

import pytest
from pydub import AudioSegment

from open_llm_vtuber.agent.output_types import Actions, DisplayText
from open_llm_vtuber.utils import stream_audio as sa


def write_wav(
    path, *, amplitude: int = 12000, duration_ms: int = 200, freq: float = 440.0
):
    """Write a mono 16-bit PCM sine wave (amplitude 0 == silence)."""
    rate = 44100
    frames = int(rate * duration_ms / 1000)
    samples = array(
        "h",
        (
            int(amplitude * math.sin(2 * math.pi * freq * i / rate))
            for i in range(frames)
        ),
    )
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(samples.tobytes())
    return str(path)


@pytest.fixture
def tone_wav(tmp_path):
    return write_wav(tmp_path / "tone.wav")


@pytest.fixture
def silent_wav(tmp_path):
    return write_wav(tmp_path / "silent.wav", amplitude=0)


# --------------------------------------------------------------------------- #
# Silent payload
# --------------------------------------------------------------------------- #
def test_payload_without_audio_is_a_silent_display():
    payload = sa.prepare_audio_payload(None)
    assert payload == {
        "type": "audio",
        "audio": None,
        "volumes": [],
        "slice_length": 20,
        "display_text": None,
        "actions": None,
        "forwarded": False,
    }


def test_payload_without_audio_uses_the_default_chunk_length():
    assert sa.prepare_audio_payload(None, chunk_length_ms=50)["slice_length"] == 50


def test_payload_without_audio_serialises_display_text():
    payload = sa.prepare_audio_payload(None, display_text=DisplayText(text="hi"))
    assert payload["display_text"] == {"text": "hi", "name": "AI", "avatar": None}


def test_payload_without_audio_serialises_actions():
    payload = sa.prepare_audio_payload(None, actions=Actions(expressions=["smile"]))
    assert payload["actions"] == {"expressions": ["smile"]}


def test_payload_without_audio_propagates_the_forwarded_flag():
    assert sa.prepare_audio_payload(None, forwarded=True)["forwarded"] is True


# --------------------------------------------------------------------------- #
# Volume calculation
# --------------------------------------------------------------------------- #
def test_volumes_are_normalised_to_the_loudest_chunk(tone_wav):
    audio = AudioSegment.from_file(tone_wav)
    volumes = sa._get_volume_by_chunks(audio, 20)
    assert len(volumes) == 10  # 200 ms of audio in 20 ms chunks
    assert max(volumes) == pytest.approx(1.0)
    assert all(0 < volume <= 1 for volume in volumes)


def test_chunk_length_changes_the_number_of_volumes(tone_wav):
    audio = AudioSegment.from_file(tone_wav)
    assert len(sa._get_volume_by_chunks(audio, 50)) == 4


def test_volumes_of_silent_audio_raise(silent_wav):
    with pytest.raises(ValueError, match="Audio is empty or all zero"):
        sa._get_volume_by_chunks(AudioSegment.from_file(silent_wav), 20)


# --------------------------------------------------------------------------- #
# Payload from a real audio file
# --------------------------------------------------------------------------- #
def test_payload_embeds_base64_wav_audio(tone_wav):
    payload = sa.prepare_audio_payload(tone_wav, chunk_length_ms=20)

    assert payload["type"] == "audio"
    assert payload["slice_length"] == 20
    assert payload["forwarded"] is False
    assert len(payload["volumes"]) == 10

    audio_bytes = base64.b64decode(payload["audio"])
    assert audio_bytes[:4] == b"RIFF"
    assert audio_bytes[8:12] == b"WAVE"


def test_payload_includes_display_text_and_actions(tone_wav):
    payload = sa.prepare_audio_payload(
        tone_wav,
        display_text=DisplayText(text="hello", name="AI", avatar="mao.png"),
        actions=Actions(expressions=[1], pictures=["a.png"]),
        forwarded=True,
    )
    assert payload["display_text"] == {
        "text": "hello",
        "name": "AI",
        "avatar": "mao.png",
    }
    assert payload["actions"] == {"expressions": [1], "pictures": ["a.png"]}
    assert payload["forwarded"] is True


def test_payload_raises_for_silent_audio(silent_wav):
    with pytest.raises(ValueError, match="Audio is empty or all zero"):
        sa.prepare_audio_payload(silent_wav)


def test_payload_raises_for_a_missing_file(tmp_path):
    missing = tmp_path / "missing.wav"
    with pytest.raises(
        ValueError, match="Error loading or converting generated audio file"
    ):
        sa.prepare_audio_payload(str(missing))
