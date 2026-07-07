import base64
from pydub import AudioSegment
from pydub.utils import make_chunks
from ..agent.output_types import Actions
from ..agent.output_types import DisplayText

# Payload types for chunked TTS audio streaming. A streamed sentence is
# delivered as one "audio-stream-start" (carrying display text/actions like
# the legacy "audio" payload), N "audio-stream-chunk" messages of raw int16
# PCM, and a closing "audio-stream-end".


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
            "volumes": [],
            "slice_length": chunk_length_ms,
            "display_text": display_text,
            "actions": actions.to_dict() if actions else None,
            "forwarded": forwarded,
        }

    try:
        audio = AudioSegment.from_file(audio_path)
        audio_bytes = audio.export(format="wav").read()
    except Exception as e:
        raise ValueError(
            f"Error loading or converting generated audio file to wav file '{audio_path}': {e}"
        )
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    volumes = _get_volume_by_chunks(audio, chunk_length_ms)

    payload = {
        "type": "audio",
        "audio": audio_base64,
        "volumes": volumes,
        "slice_length": chunk_length_ms,
        "display_text": display_text,
        "actions": actions.to_dict() if actions else None,
        "forwarded": forwarded,
    }

    return payload


def prepare_stream_start_payload(
    stream_id: str,
    sample_rate: int,
    display_text: DisplayText = None,
    actions: Actions = None,
    forwarded: bool = False,
) -> dict[str, any]:
    """
    Prepare the payload announcing a new streamed-audio sentence.

    Carries the same display/action metadata as the legacy "audio" payload
    so the frontend can show subtitles and expressions when playback starts.
    """
    if isinstance(display_text, DisplayText):
        display_text = display_text.to_dict()

    return {
        "type": "audio-stream-start",
        "stream_id": stream_id,
        "sample_rate": sample_rate,
        "display_text": display_text,
        "actions": actions.to_dict() if actions else None,
        "forwarded": forwarded,
    }


def prepare_stream_chunk_payload(stream_id: str, chunk) -> tuple[dict[str, any], int]:
    """
    Convert one TTS chunk into an "audio-stream-chunk" payload.

    Accepts ``(data, sample_rate)`` where ``data`` is either raw little-endian
    int16 PCM bytes or a numpy float32 array in [-1.0, 1.0] (mono).

    Returns:
        (payload, sample_rate)
    """
    data, sample_rate = chunk
    if isinstance(data, (bytes, bytearray)):
        pcm_bytes = bytes(data)
    else:
        import numpy as np

        arr = np.clip(np.asarray(data, dtype=np.float32), -1.0, 1.0)
        pcm_bytes = (arr * 32767.0).astype(np.int16).tobytes()

    payload = {
        "type": "audio-stream-chunk",
        "stream_id": stream_id,
        "chunk": base64.b64encode(pcm_bytes).decode("utf-8"),
    }
    return payload, int(sample_rate)


def prepare_stream_end_payload(stream_id: str) -> dict[str, any]:
    """Prepare the payload closing a streamed-audio sentence."""
    return {
        "type": "audio-stream-end",
        "stream_id": stream_id,
    }


# Example usage:
# payload, duration = prepare_audio_payload("path/to/audio.mp3", display_text="Hello", expression_list=[0,1,2])
