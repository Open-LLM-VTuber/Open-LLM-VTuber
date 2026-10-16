"""Cartesia output must remain usable by the audio payload pipeline."""

import base64
import io
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import httpx
from cartesia import Cartesia

from open_llm_vtuber.tts.cartesia_tts import TTSEngine
from open_llm_vtuber.utils.stream_audio import prepare_audio_payload


def pcm_wav() -> bytes:
    """Return a mono PCM16 WAV with silence and two distinct volume levels."""
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(44100)
        for amplitude in (0, 1000, 10000):
            audio.writeframes(amplitude.to_bytes(2, "little", signed=True) * 882)
    return output.getvalue()


class CartesiaOutputTests(unittest.TestCase):
    """Exercise SDK requests, saved bytes, and downstream lip-sync volumes."""

    def generate(self, directory: Path, output_format: str, response: bytes) -> Path:
        """Generate audio with the real SDK and a local HTTP transport."""

        def respond(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/tts/bytes")
            payload = json.loads(request.content)
            expected = (
                {"container": "wav", "sample_rate": 44100, "encoding": "pcm_s16le"}
                if output_format == "wav"
                else {"container": "mp3", "sample_rate": 44100, "bit_rate": 128000}
            )
            self.assertEqual(payload["output_format"], expected)
            self.assertEqual(payload["transcript"], "Hello")
            return httpx.Response(200, content=response)

        with httpx.Client(transport=httpx.MockTransport(respond)) as http:
            client = Cartesia(api_key="test-only", httpx_client=http)
            with patch(
                "open_llm_vtuber.tts.cartesia_tts.Cartesia", return_value=client
            ):
                engine = TTSEngine(api_key="test-only", output_format=output_format)
            with patch.object(
                engine,
                "generate_cache_file_name",
                return_value=str(directory / f"speech.{output_format}"),
            ):
                return Path(engine.generate_audio("Hello"))

    def test_default_wav_preserves_lip_sync_volume_levels(self) -> None:
        """Save PCM16 output and preserve silence, quiet, and loud chunks."""
        with tempfile.TemporaryDirectory() as directory:
            path = self.generate(Path(directory), "wav", pcm_wav())
            with wave.open(str(path), "rb") as audio:
                self.assertEqual(audio.getsampwidth(), 2)
                self.assertEqual(audio.getnchannels(), 1)
            payload = prepare_audio_payload(str(path))
            self.assertEqual(payload["volumes"], [0.0, 0.1, 1.0])
            self.assertEqual(payload["slice_length"], 20)
            self.assertEqual(payload["type"], "audio")
            with wave.open(
                io.BytesIO(base64.b64decode(payload["audio"])), "rb"
            ) as audio:
                self.assertEqual(audio.getsampwidth(), 2)

    def test_mp3_format_and_bytes_are_unchanged(self) -> None:
        """Keep the MP3 request and saved bytes independent of WAV encoding."""
        with tempfile.TemporaryDirectory() as directory:
            response = b"ID3-test-audio"
            path = self.generate(Path(directory), "mp3", response)
            self.assertEqual(path.suffix, ".mp3")
            self.assertEqual(path.read_bytes(), response)


if __name__ == "__main__":
    unittest.main()
