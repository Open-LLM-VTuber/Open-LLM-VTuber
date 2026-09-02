#!/usr/bin/env python3
"""
Minimal OpenAI-compatible TTS server that drives the Piper CLI on one or more
local models. Exposes the OpenAI audio.speech shape Open-LLM-VTuber's
`openai_tts` engine expects:

    POST /v1/audio/speech   {model, voice, input, response_format}
        -> synthesizes `input` with Piper (model chosen by `voice`/`model`)
           and returns raw audio/wav

Model registry (voice/model name -> onnx path):
    glados  -> $VOICES_DIR/glados/glados.onnx   (GLaDOS)
    hal     -> $VOICES_DIR/hal/hal.onnx          (HAL-9000, Wheatley)

Configuration is via environment variables (current values are defaults, so
existing deployments keep working unchanged):
    PIPER_TTS_PORT    listen port            (default 8880)
    PIPER_BIN         path to the piper CLI  (~/.local/bin/piper)
    VOICES_DIR        base dir for voice models (~/voices)
    PIPER_TTS_MODELS  optional JSON dict overriding the registry
                      e.g. '{"glados":"/abs/path/glados.onnx"}'

Stdlib only (calls the `piper` binary). Run: python3 piper_openai_tts_server.py
"""
import json
import os
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PIPER_TTS_PORT", "8880"))
PIPER_BIN = os.environ.get("PIPER_BIN", os.path.expanduser("~/.local/bin/piper"))
VOICES_DIR = os.environ.get("VOICES_DIR", os.path.expanduser("~/voices"))

DEFAULT_MODELS = {
    "glados": os.path.join(VOICES_DIR, "glados", "glados.onnx"),
    "hal": os.path.join(VOICES_DIR, "hal", "hal.onnx"),
}

# Allow an explicit override of the model registry.
_env_models = os.environ.get("PIPER_TTS_MODELS")
if _env_models:
    try:
        MODELS = {**DEFAULT_MODELS, **json.loads(_env_models)}
    except Exception:  # noqa: BLE001 (intentional catch-all in standalone server)
        MODELS = dict(DEFAULT_MODELS)
else:
    MODELS = DEFAULT_MODELS


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.rstrip("/") in ("/health", "/v1/health", "/"):
            body = json.dumps({"status": "ok", "models": list(MODELS)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if not self.path.rstrip("/").endswith("/audio/speech"):
            self.send_response(404)
            self._cors()
            self.end_headers()
            return
        n = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(n).decode())
        except Exception:  # noqa: BLE001 (intentional catch-all in standalone server)
            self.send_response(400)
            self._cors()
            self.end_headers()
            return
        text = req.get("input", "")
        ext = response_ext(req.get("response_format"))
        # choose model by voice name, then model name, default hal
        model = resolve_model(req.get("voice") or req.get("model"))
        if not text.strip():
            self.send_response(400)
            self._cors()
            self.end_headers()
            return
        try:
            audio = synthesize(text, model, ext)
        except Exception as e:  # noqa: BLE001 (intentional catch-all in standalone server)
            err = f"TTS error: {e}".encode()
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self._cors()
            self.send_header("Content-Length", str(len(err)))
            self.end_headers()
            self.wfile.write(err)
            return
        ctype = "audio/mpeg" if ext == "mp3" else "audio/wav"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self._cors()
        self.send_header("Content-Length", str(len(audio)))
        self.end_headers()
        self.wfile.write(audio)


def resolve_model(name: str | None) -> str:
    """Map a voice/model request name to an onnx path (fallback: hal)."""
    key = (name or "hal").lower()
    return MODELS.get(key, MODELS["hal"])


def response_ext(fmt: str | None) -> str:
    """Map a requested response_format to a file extension (fallback: wav)."""
    return "mp3" if (fmt or "wav").lower() == "mp3" else "wav"


def synthesize(text: str, model: str, ext: str, timeout: int = 120) -> bytes:
    """Render `text` with the given Piper `model` and return raw audio bytes.

    Runs the Piper CLI to a temp file, reads it back, and removes the temp
    file even on failure. Raises RuntimeError if Piper exits non-zero. The
    caller is responsible for HTTP plumbing (status/headers/body).
    """
    fd, tmppath = tempfile.mkstemp(suffix="." + ext)
    os.close(fd)
    try:
        proc = subprocess.run(  # noqa: PLW1510 (non-zero exit handled by caller)
            [PIPER_BIN, "--model", model, "--output_file", tmppath],
            input=text, capture_output=True, text=True, timeout=timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr[:300])
        with open(tmppath, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(tmppath)
        except Exception:  # noqa: BLE001,S110 (intentional catch-all + swallow in standalone server)
            pass


if __name__ == "__main__":
    print(f"Piper OpenAI-TTS server on :{PORT}")
    for k, v in MODELS.items():
        print(f"  {k} -> {v}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
