# Open-LLM-VTuber — Local Offline Pipeline

This directory documents the **fully-offline** speech pipeline used by this
Open-LLM-VTuber deployment. All three legs (LLM, TTS, ASR) run on
`localhost` with **zero cloud dependency**.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Open-LLM-VTuber                            │
│  conf.yaml:                                                   │
│    llm_provider: openai_compatible_llm  -> http://localhost:8890/v1   │
│    tts_model:    openai_tts              -> http://localhost:8880/v1   │
│    asr_model:    openai_compat_asr       -> http://localhost:8733/v1   │
└───────────────┬───────────────────────┬───────────────────┘
                │                       │                   │
        :8890   ▼               :8880   ▼           :8733   ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│ a2a_openai_proxy.py   │ │ piper_openai_tts_     │ │ glados-asr.service   │
│ (this repo root)      │ │ server.py (root)      │ │ (OpenAI-compat       │
│                      │ │                       │ │  faster-whisper)     │
│ A2A JSON-RPC ->      │ │ Piper CLI -> wav      │ │                      │
│ OpenAI /chat/        │ │                       │ │                      │
│ completions SSE      │ │                       │ │                      │
└──────────┬───────────┘ └──────────────────────┘ └──────────────────────┘
           │
   ┌───────┴───────────────────────────────┐
   │ glados   -> Hermes   A2A :9900         │
   │ wheatley -> OpenClaw A2A :18800        │
   └─────────────────────────────────────────┘
```

## Components

| Port | Service | Provided by | Drives |
|------|---------|-------------|--------|
| 8890 | `a2a_openai_proxy.py` | this repo | LLM: translates OpenAI `/v1/chat/completions` ↔ A2A `message/send` to Hermes/OpenClaw |
| 8880 | `piper_openai_tts_server.py` | this repo | TTS: OpenAI `/v1/audio/speech` → local Piper (GLaDOS/HAL voices) |
| 8733 | `glados-asr.service` | `~/.local/bin/asr_glados_server.py` | ASR: OpenAI `/v1/audio/transcriptions` → local faster-whisper |

The `openai_compat_asr` engine (added in this repo) is the ASR client that
speaks the OpenAI protocol to `:8733`. `openai_tts` and
`openai_compatible_llm` are built-in OLVT engines that already speak it.

## Running the backing servers

Both scripts are stdlib-only and read their configuration from environment
variables (with defaults that match this deployment):

```bash
# LLM proxy (A2A -> OpenAI)
A2A_PROXY_PORT=8890 python3 a2a_openai_proxy.py

# TTS (Piper)
PIPER_TTS_PORT=8880 PIPER_BIN=~/.local/bin/piper VOICES_DIR=~/voices \
    python3 piper_openai_tts_server.py

# ASR (run via systemd)
systemctl --user start glados-asr.service
```

### Environment variables

**`a2a_openai_proxy.py`**
- `A2A_PROXY_PORT` (8890) — listen port
- `A2A_PROXY_CONTEXT_PREFIX` (ollvtuber) — A2A contextId prefix
- `OPENCLAW_CONFIG` (~/.openclaw/openclaw.json) — source of the A2A token
- `HERMES_A2A_URL` (http://localhost:9900/a2a/jsonrpc)
- `OPENCLAW_A2A_URL` (http://localhost:18800/a2a/jsonrpc)

**`piper_openai_tts_server.py`**
- `PIPER_TTS_PORT` — listen port (8880)
- `PIPER_BIN` (~/.local/bin/piper) — piper CLI path
- `VOICES_DIR` (~/voices) — base dir for `glados/glados.onnx`, `hal/hal.onnx`
- `PIPER_TTS_MODELS` — optional JSON dict overriding the model registry

## Notes

- The two Python servers are launched and supervised by systemd user units
  (`a2a-openai-proxy.service`, `piper-openai-tts.service`); ASR by
  `glados-asr.service`.
- All paths above are environment-overridable so a fresh clone can run the
  pipeline without the original machine's absolute paths baked in.
