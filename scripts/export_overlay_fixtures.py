"""Export the exact frames the backend puts on the wire, for the overlay tests.

``scripts/test_stage_obs.py`` checks the Python producers and
``scripts/test_overlay_protocol.js`` checks the JavaScript consumer, but each
one asserts its own idea of the contract. This script closes that gap: it
drives the *real* builders (``build_stage_payload``, ``prepare_audio_payload``,
``send_conversation_start_signals`` and ``finalize_conversation_turn``) and
writes the resulting ``json.dumps`` strings to
``tests/fixtures/overlay-wire.json``. ``scripts/test_overlay_wire.js`` then
replays exactly those strings through ``web_tool/overlay-protocol.js``.

    python scripts/export_overlay_fixtures.py            # rewrite the fixture
    python scripts/export_overlay_fixtures.py --check    # exit 1 when stale

Only the *audio bytes* are synthetic: ``pydub``/ffmpeg are replaced by a
deterministic fake segment, so the fixture is identical with or without the
runtime dependencies installed. Everything else (field names, ordering, ``None``
vs ``""``, clamping, number formatting) comes from the backend code.

The shims below exist for the same reason as in ``scripts/test_stage_obs.py``:
a bare interpreter may miss ``loguru``/``numpy``/``pydantic``/``pydub``. A real
module always wins when it is installed.
"""

import argparse
import asyncio
import contextlib
import json
import logging
import os
import sys
import types
from unittest import mock

# Add project root to path to enable imports (same as the live scripts).
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

FIXTURE_PATH = os.path.join(project_root, "tests", "fixtures", "overlay-wire.json")
SCHEMA_VERSION = 1
GENERATOR = "scripts/export_overlay_fixtures.py"


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

        @property
        def opt(self):
            return self

        def _noop(self, *_args, **_kwargs):
            return None

        debug = info = warning = error = critical = exception = success = _noop

        def add(self, *_a, **_k):
            return 0

        def remove(self, *_a, **_k):
            return None

    module = types.ModuleType("loguru")
    module.logger = _ShimLogger()
    sys.modules["loguru"] = module


def _install_numpy_shim() -> None:
    """``conversation_utils`` only needs ``np.ndarray`` for annotations."""
    try:
        import numpy  # noqa: F401

        return
    except ImportError:
        pass

    class _FakeArray:
        pass

    module = types.ModuleType("numpy")
    module.ndarray = _FakeArray
    module.float32 = float
    module.float64 = float
    sys.modules["numpy"] = module


def _install_pydantic_shim() -> None:
    """``conversations/types.py`` only uses ``BaseModel`` for a config class."""
    try:
        import pydantic  # noqa: F401

        return
    except ImportError:
        pass

    class _BaseModel:
        def __init__(self, **data):
            annotations = {}
            for klass in reversed(type(self).__mro__):
                annotations.update(getattr(klass, "__annotations__", {}))
            for name in annotations:
                if name.startswith("_"):
                    continue
                if name in data:
                    setattr(self, name, data[name])
                elif hasattr(type(self), name):
                    setattr(self, name, getattr(type(self), name))

        def model_dump(self, *_args, **_kwargs):
            return dict(vars(self))

        def dict(self):  # pydantic v1 compatibility
            return self.model_dump()

    module = types.ModuleType("pydantic")
    module.BaseModel = _BaseModel
    module.Field = lambda default=None, **_kwargs: default
    module.ConfigDict = dict
    sys.modules["pydantic"] = module


def _install_pydub_shim() -> None:
    """Let ``utils.stream_audio`` import when pydub is not installed."""
    try:
        import pydub  # noqa: F401

        return
    except ImportError:
        pass

    module = types.ModuleType("pydub")
    module.AudioSegment = type("AudioSegment", (), {})
    utils = types.ModuleType("pydub.utils")
    utils.make_chunks = lambda *_args, **_kwargs: []
    module.utils = utils
    sys.modules["pydub"] = module
    sys.modules["pydub.utils"] = utils


for _shim in (
    _install_loguru_shim,
    _install_numpy_shim,
    _install_pydantic_shim,
    _install_pydub_shim,
):
    _shim()


def _stub_unless_importable(module_name: str, **attributes) -> bool:
    """Install a stub only when the real module cannot be imported.

    ``conversation_utils``/``tts_manager`` import ``Live2dModel`` and
    ``TTSInterface`` for type annotations only. In a full environment the real
    modules are used; in a bare interpreter the two small stubs avoid pulling
    torch/onnxruntime just to build a JSON string.
    """
    try:
        __import__(module_name, fromlist=list(attributes))
        return False
    except Exception:  # noqa: BLE001 - any import failure falls back to the stub
        module = types.ModuleType(module_name)
        for name, value in attributes.items():
            setattr(module, name, value)
        sys.modules[module_name] = module
        return True


STUBBED = {
    "live2d_model": _stub_unless_importable(
        "src.open_llm_vtuber.live2d_model", Live2dModel=type("Live2dModel", (), {})
    ),
    "tts_interface": _stub_unless_importable(
        "src.open_llm_vtuber.tts.tts_interface",
        TTSInterface=type("TTSInterface", (), {}),
    ),
}

from src.open_llm_vtuber.agent.output_types import Actions, DisplayText  # noqa: E402
from src.open_llm_vtuber.conversations import conversation_utils  # noqa: E402
from src.open_llm_vtuber.utils import stream_audio, tarot  # noqa: E402
from src.open_llm_vtuber.utils.stage import build_stage_payload  # noqa: E402


# --------------------------------------------------------------------------- #
# Deterministic fake audio: the only synthetic part of the fixture
# --------------------------------------------------------------------------- #
#: RMS per fake chunk; ``prepare_audio_payload`` normalises them -> [0.4, 1.0].
CHUNK_RMS = (400, 1000)
RIFF_BYTES = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
MP3_BYTES = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\x00" * 8


class _FakeExport:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data


class _FakeSegment:
    def __init__(self, rms: int):
        self.rms = rms

    def export(self, format: str = "wav", bitrate=None):
        return _FakeExport(MP3_BYTES if format == "mp3" else RIFF_BYTES)


class _FakeAudioSegment:
    """Stands in for ``pydub.AudioSegment``; nothing is decoded from disk."""

    @staticmethod
    def from_file(_path):
        return _FakeSegment(CHUNK_RMS[-1])


def _fake_make_chunks(_audio, _chunk_length_ms):
    return [_FakeSegment(rms) for rms in CHUNK_RMS]


@contextlib.contextmanager
def _synthetic_audio():
    """Make ``prepare_audio_payload`` deterministic in any environment."""
    with (
        mock.patch.object(stream_audio, "AudioSegment", _FakeAudioSegment),
        mock.patch.object(stream_audio, "make_chunks", _fake_make_chunks),
    ):
        yield


# --------------------------------------------------------------------------- #
# Real builders -> wire frames
# --------------------------------------------------------------------------- #
def _audio_frame(
    text: str,
    *,
    audio_path: str | None = "/tmp/overlay-fixture.wav",
    forwarded: bool = False,
) -> str:
    """Build one ``audio`` frame exactly as ``TTSTaskManager`` sends it."""
    payload = stream_audio.prepare_audio_payload(
        audio_path=audio_path,
        display_text=DisplayText(text=text, name="Tarotista"),
        actions=Actions(expressions=["neutral"]),
        forwarded=forwarded,
    )
    return json.dumps(payload)


def _start_frames() -> list[str]:
    """The ``conversation-chain-start`` + ``full-text`` pair of every turn."""
    frames: list[str] = []

    async def send(payload: str) -> None:
        frames.append(payload)

    asyncio.run(conversation_utils.send_conversation_start_signals(send))
    return frames


async def _capture_turn(chunks: list[str]) -> tuple[list[str], list[str]]:
    """Replay a full turn through ``finalize_conversation_turn``.

    Returns ``(before_ack, after_ack)``: the server blocks on
    ``frontend-playback-complete`` before it sends ``force-new-message`` and
    ``conversation-chain-end``, so the split is where the real client answers.
    """
    frames: list[str] = []

    async def send(payload: str) -> None:
        frames.append(payload)

    await conversation_utils.send_conversation_start_signals(send)
    frames.extend(chunks)

    boundary = {"at": len(frames)}

    async def ack_when_asked(*_args, **_kwargs):
        boundary["at"] = len(frames)
        return {"type": "frontend-playback-complete"}

    # ``finalize`` only emits backend-synth-complete when there was TTS work.
    pending = asyncio.ensure_future(asyncio.sleep(0))
    tts_manager = types.SimpleNamespace(task_list=[pending])
    with mock.patch.object(
        conversation_utils.message_handler,
        "wait_for_response",
        new=ack_when_asked,
    ):
        await conversation_utils.finalize_conversation_turn(
            tts_manager, send, "fixture-client", None
        )

    return frames[: boundary["at"]], frames[boundary["at"] :]


def _stage_frames(**kwargs) -> list[str]:
    """Build a ``stage-update`` frame the way ``send_stage_update`` does."""
    return [json.dumps(build_stage_payload(**kwargs))]


def _scenario(name: str, note: str, frames, after_ack: list[str] | None = None) -> dict:
    """One replayable scenario: frames before the ack and, for turns, after it."""
    scenario = {"name": name, "note": note, "frames": list(frames)}
    if after_ack:
        scenario["after_ack"] = list(after_ack)
    return scenario


def build_scenarios() -> list[dict]:
    """Every scenario is produced by running backend code, never hand-written."""
    scenarios: list[dict] = []

    with _synthetic_audio():
        before, after = asyncio.run(
            _capture_turn(
                [
                    _audio_frame("La carta de hoy es La Torre."),
                    _audio_frame("Déjame ver qué te dice el tarot."),
                ]
            )
        )
        scenarios.append(
            _scenario(
                "turn_wav_two_chunks",
                "complete WAV turn: chain-start, 2 chunks and synth-complete "
                "before the ack; force-new-message and chain-end after it",
                before,
                after,
            )
        )

        stream_audio.configure_audio_export("mp3", "64k")
        try:
            before, after = asyncio.run(
                _capture_turn(
                    [
                        _audio_frame("Primera frase en mp3."),
                        _audio_frame("Segunda frase en mp3."),
                    ]
                )
            )
            scenarios.append(
                _scenario(
                    "turn_mp3_two_chunks",
                    "same turn with system_config.audio_export = 'mp3' (A23)",
                    before,
                    after,
                )
            )
        finally:
            stream_audio.configure_audio_export("wav")

        before, after = asyncio.run(
            _capture_turn(
                [
                    _audio_frame("Silencio para este cliente.", audio_path=None),
                    _audio_frame(
                        "Aviso de otro cliente del grupo.",
                        audio_path=None,
                        forwarded=True,
                    ),
                ]
            )
        )
        scenarios.append(
            _scenario(
                "turn_silent_and_forwarded",
                "chunks with audio=null and forwarded=true must not block the ack (A21)",
                before,
                after,
            )
        )

        # Interrupt: the audio queue is dropped and no ack is expected (A20).
        scenarios.append(
            _scenario(
                "interrupt_after_chunk",
                "interrupt-signal drops the queue without acking (A20)",
                _start_frames()
                + [
                    _audio_frame("Espera, esta frase se va a cortar."),
                    json.dumps(conversation_utils.build_interrupt_signal()),
                ],
            )
        )

    scenarios.append(
        _scenario(
            "stage_background_only",
            "a scheduler job that only changes the background keeps the props",
            _stage_frames(stage="tarot_main", background="/bg/tarot_table.png"),
        )
    )
    scenarios.append(
        _scenario(
            "stage_with_props",
            "props without src are dropped, x is clamped to 0..1 by the backend",
            _stage_frames(
                stage="tarot_main",
                background="/bg/tarot_table.png",
                props=[
                    {
                        "id": "card_1",
                        "src": "/bg/cards/tower.png",
                        "x": 0.7,
                        "y": 0.5,
                        "rot": -8,
                        "scale": 1.1,
                        "opacity": 0.95,
                    },
                    {"id": "no_src_here", "x": 0.2, "y": 0.2},
                    {"id": "card_2", "src": "/bg/cards/sun.png", "x": 1.4, "y": -0.2},
                ],
                transition="fade",
                duration_ms=800,
            ),
        )
    )
    scenarios.append(
        _scenario(
            "stage_transition_none",
            "transition='none' and duration_ms=0 survive the sanitiser",
            _stage_frames(
                stage="quiet",
                background="/bg/curtain.png",
                transition="none",
                duration_ms=0,
            ),
        )
    )

    # A scheduled job with `draw: 3`: real props pointing at the deck art.
    drawn = tarot.draw_cards(3, seed=2026)
    scenarios.append(
        _scenario(
            "tarot_draw_three_cards",
            "SchedulerService._prepare_stage with a three-card spread: the "
            "overlay gets 'src' props served from /bg/cards",
            _stage_frames(stage="card_of_the_day", props=tarot.build_draw_props(drawn)),
        )
    )
    scenarios.append(
        _scenario(
            "tarot_draw_text_fallback",
            "same spread with art_prefix=None: the overlay draws label cards",
            _stage_frames(
                stage="card_of_the_day",
                props=tarot.build_draw_props(drawn, art_prefix=None),
            ),
        )
    )
    return scenarios


def build_fixtures() -> dict:
    """The whole fixture document, ready to be serialised.

    Nothing environment-specific is included (in particular not which shims
    were needed): the same file must come out of a bare Windows interpreter and
    out of the Docker image, otherwise ``--check`` would be meaningless.
    """
    return {
        "schema": SCHEMA_VERSION,
        "generated_by": GENERATOR,
        "contract": "AUDITORIA-MVP-TAROT.md §1.3 (server -> client) and §2.4 (stage-update)",
        "notes": "each frame is the exact json.dumps() string passed to websocket_send",
        "scenarios": build_scenarios(),
    }


def render() -> str:
    return json.dumps(build_fixtures(), indent=2, ensure_ascii=False) + "\n"


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read().replace("\r\n", "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=FIXTURE_PATH, help="fixture path")
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare with the committed fixture instead of writing it",
    )
    args = parser.parse_args(argv)

    text = render()
    print(f"stubs used: {STUBBED}")
    if args.check:
        try:
            current = _read(args.out)
        except FileNotFoundError:
            print(f"missing fixture: {args.out}")
            return 1
        if current != text:
            print(f"stale fixture: {args.out}")
            print(f"run: python {GENERATOR}")
            return 1
        print(f"overlay fixtures up to date ({len(text)} bytes)")
        return 0

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print(f"wrote {args.out} ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
