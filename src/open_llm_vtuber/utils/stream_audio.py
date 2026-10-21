import base64
from pydub import AudioSegment
from pydub.utils import make_chunks
from ..agent.output_types import Actions
from ..agent.output_types import DisplayText

# A23: container used when the TTS audio is re-encoded for the client.
# - "wav" (default): no transcoding on the hot path; best for LAN/OBS on the
#   same machine. A 24 kHz mono stream is ~48 KB/s, ~64 KB/s once base64'd.
# - "mp3": ~10x less traffic (64 kbps by default); needs ffmpeg/libmp3lame.
AUDIO_EXPORT_FORMATS = ("wav", "mp3")
DEFAULT_AUDIO_EXPORT_FORMAT = "wav"
DEFAULT_AUDIO_EXPORT_BITRATE = "64k"

_audio_export_format = DEFAULT_AUDIO_EXPORT_FORMAT
_audio_export_bitrate = DEFAULT_AUDIO_EXPORT_BITRATE


def configure_audio_export(
    audio_format: str = DEFAULT_AUDIO_EXPORT_FORMAT,
    bitrate: str | None = None,
) -> str:
    """Select the container used by :func:`prepare_audio_payload` (A23).

    The server calls this once at startup with ``system_config.audio_export``.
    The value is process-wide because every consumer (TTS manager, direct audio
    output, silent payloads) has to agree on the same format.

    Parameters:
        audio_format (str): "wav" (default) or "mp3".
        bitrate (str | None): MP3 bitrate such as "64k"; ignored for WAV.

    Returns:
        str: the normalized format that is now active.

    Raises:
        ValueError: if the format is not supported.
    """
    global _audio_export_format, _audio_export_bitrate

    normalized = (audio_format or DEFAULT_AUDIO_EXPORT_FORMAT).strip().lower()
    if normalized not in AUDIO_EXPORT_FORMATS:
        raise ValueError(
            f"Unsupported audio export format '{audio_format}'. "
            f"Use one of {AUDIO_EXPORT_FORMATS}."
        )
    _audio_export_format = normalized
    _audio_export_bitrate = (
        bitrate or DEFAULT_AUDIO_EXPORT_BITRATE
    ).strip() or DEFAULT_AUDIO_EXPORT_BITRATE
    return _audio_export_format


def get_audio_export_format() -> str:
    """Return the container currently used for audio payloads ("wav"/"mp3")."""
    return _audio_export_format


def _export_audio(audio: AudioSegment) -> bytes:
    """Encode the segment in the configured container."""
    if _audio_export_format == "mp3":
        return audio.export(format="mp3", bitrate=_audio_export_bitrate).read()
    return audio.export(format="wav").read()


def _get_volume_by_chunks(audio: AudioSegment, chunk_length_ms: int) -> list:
    """
    Calculate the normalized volume (RMS) for each chunk of the audio.

    Parameters:
        audio (AudioSegment): The audio segment to process.
        chunk_length_ms (int): The length of each audio chunk in milliseconds.

    Returns:
        list: Normalized volumes for each chunk.
    """
    chunks = make_chunks(audio, chunk_length_ms)
    volumes = [chunk.rms for chunk in chunks]
    max_volume = max(volumes)
    if max_volume == 0:
        raise ValueError("Audio is empty or all zero.")
    return [volume / max_volume for volume in volumes]


def prepare_audio_payload(
    audio_path: str | None,
    chunk_length_ms: int = 20,
    display_text: DisplayText = None,
    actions: Actions = None,
    forwarded: bool = False,
) -> dict[str, any]:
    """
    Prepares the audio payload for sending to a broadcast endpoint.
    If audio_path is None, returns a payload with audio=None for silent display.

    Parameters:
        audio_path (str | None): The path to the audio file to be processed, or None for silent display
        chunk_length_ms (int): The length of each audio chunk in milliseconds
        display_text (DisplayText, optional): Text to be displayed with the audio
        actions (Actions, optional): Actions associated with the audio

    Returns:
        dict: The audio payload to be sent
    """
    if isinstance(display_text, DisplayText):
        display_text = display_text.to_dict()

    if not audio_path:
        # Return payload for silent display
        return {
            "type": "audio",
            "audio": None,
            "audio_format": _audio_export_format,
            "volumes": [],
            "slice_length": chunk_length_ms,
            "display_text": display_text,
            "actions": actions.to_dict() if actions else None,
            "forwarded": forwarded,
        }

    try:
        audio = AudioSegment.from_file(audio_path)
        audio_bytes = _export_audio(audio)
    except Exception as e:
        raise ValueError(
            f"Error loading or converting generated audio file to "
            f"{_audio_export_format} file '{audio_path}': {e}"
        )
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    volumes = _get_volume_by_chunks(audio, chunk_length_ms)

    payload = {
        "type": "audio",
        "audio": audio_base64,
        # A23: lets clients that build a data: URL pick the right MIME type.
        # Players based on WebAudio (decodeAudioData) detect the container
        # themselves and can ignore this field.
        "audio_format": _audio_export_format,
        "volumes": volumes,
        "slice_length": chunk_length_ms,
        "display_text": display_text,
        "actions": actions.to_dict() if actions else None,
        "forwarded": forwarded,
    }

    return payload


# Example usage:
# payload, duration = prepare_audio_payload("path/to/audio.mp3", display_text="Hello", expression_list=[0,1,2])
