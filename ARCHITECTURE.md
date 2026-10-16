# Open-LLM-VTuber Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                   WebSocket Client                   │
│  (Browser / Desktop App / Mobile PWA)                │
└──────────────────────┬──────────────────────────────┘
                       │ WebSocket / HTTP
                       ▼
┌─────────────────────────────────────────────────────┐
│                  FastAPI Routes                      │
│  /client-ws  /proxy-ws  /asr  /tts-ws  /live2d     │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              WebSocket Handler                       │
│  Message routing · Rate limiting · Session mgmt     │
│  Audio buffering · Conversation triggers            │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
┌──────────────┐ ┌────────────┐ ┌──────────────┐
│  Agent       │ │  Memory    │ │  Security    │
│  Engine      │ │  Engine    │ │  Engine      │
│  · Router    │ │  · CRM     │ │  · Rate Limit│
│  · Affective │ │  · Recall  │ │  · Validator │
│  · Cognitive │ │  · Chat    │ │  · Spoof     │
│    Router    │ │  History   │ │    Defender  │
└──────┬───────┘ └─────┬──────┘ └──────┬───────┘
       │               │               │
       ▼               ▼               ▼
┌──────────────┐ ┌────────────┐ ┌──────────────┐
│  TTS Engine  │ │  ASR       │ │  MCP Client  │
│  · Kokoro    │ │  · Whisper │ │  · Tools     │
│  · Edge      │ │  · FunASR  │ │  · Servers   │
│  · GPT-SoVITS│ │  · Sherpa  │ │  · Registry  │
│  · RVC       │ │            │ │              │
└──────┬───────┘ └─────┬──────┘ └──────┬───────┘
       │               │               │
       ▼               ▼               ▼
┌─────────────────────────────────────────────────────┐
│               Cache · DB · Telemetry                │
│  Redis Cache · SQLite/Alembic · OpenTelemetry       │
└─────────────────────────────────────────────────────┘

Supporting Systems:
┌──────────────┐ ┌────────────┐ ┌──────────────┐
│  Vision      │ │  Radar     │ │  Live        │
│  · Grounder  │ │  · Social  │ │  · Bilibili  │
│  · Screen    │ │  · Chat    │ │  · Twitch    │
│  · Gaze      │ │  · Clust.  │ │  · P2P       │
│  · Convergence│ │            │ │  · AI        │
└──────────────┘ └────────────┘ └──────────────┘
```

## Module Descriptions

### Core

| Module | Purpose |
|---|---|
| `routes.py` | REST + WebSocket endpoints |
| `websocket_handler.py` | Connection management + message routing |
| `lifecycle.py` | Application lifecycle management |
| `live2d_model.py` | Live2D model loading + emotion mapping |

### Agent (AI Brain)

| Module | Purpose |
|---|---|
| `dual_track_router.py` | Routes messages to different LLMs by complexity |
| `cognitive_router.py` | Semantic signal-based response selection |
| `anchor_pipeline.py` | Conversation context extraction |
| `affective_engine.py` | PAD emotional state model → TTS modulation |
| `collab_squad.py` | Multi-agent conversational arbitration |
| `counter_troll_courtroom.py` | Troll detection + trial/verdict system |

### Memory (Long-term)

| Module | Purpose |
|---|---|
| `parasocial_crm.py` | Viewer tracking + inside jokes |
| `fan_memory_engine.py` | Fan relationship management |
| `db/` | SQLAlchemy models + Alembic migrations |

### Audio

| Module | Purpose |
|---|---|
| `karaoke_harmonizer.py` | Singing harmony generation |
| `voice_morpher.py` | Voice modification |
| `vocal_fatigue_engine.py` | Voice degradation over time |
| `audioseal_watermark.py` | Audio watermarking |
| `tts/` | 9+ TTS engine interfaces |

### Vision

| Module | Purpose |
|---|---|
| `vision_grounder.py` | Spatial gaze retargeting |
| `screen_watcher.py` | Screen event detection |
| `gaze_convergence_solver.py` | Webcam gaze + vergence |

### Security

| Module | Purpose |
|---|---|
| `voice_clone_defender.py` | Anti-spoofing via FFT analysis |
| `hardening.py` | Rate limiting + input validation |
| `verifiable_autonomy.py` | Permission verification |

### Infrastructure

| Module | Purpose |
|---|---|
| `cache/` | Redis caching layer |
| `telemetry/` | OpenTelemetry + metrics |
| `mcpp/` | MCP client (tool integration) |
| `radar/` | Social monitoring + chat sentiment |
| `vad/` | Voice activity detection |

## Data Flow (Message Example)

```
User speaks → VAD detects speech → ASR transcribes
     ↓
WebSocket → Handler routes to Agent
     ↓
AffectiveEngine updates emotional state
     ↓
DualTrackRouter selects LLM (Ollama/Groq/OpenAI)
     ↓
LLM generates response → CounterTroll screens for toxicity
     ↓
ParasocialCRM retrieves viewer context
     ↓
SocialRadar provides trending topics
     ↓
ChatWaveClusterer extracts chat sentiment
     ↓
AffectiveEngine modulates TTS (pitch/speed by mood)
     ↓
Selected TTS generates audio → Live2D animation
     ↓
WebSocket sends audio + animation to client
```

## Performance Targets

| Metric | Target | Measurement |
|---|---|---|
| End-to-end latency | <100ms | VAD→Audio output |
| TTS generation | <200ms | Text→Audio chunk |
| ASR transcription | <300ms | Audio→Text |
| Cache hit rate | >70% | Redis metrics |
| WebSocket connections | 500+ | Concurrent |
| CPU usage | <30% | Idle state |
| Memory | <2GB | Typical usage |

## Deployment

| Method | Use Case |
|---|---|
| `uv sync` | Development |
| `docker-compose up` | Production |
| `install_windows.ps1` | Windows one-click |
| `install_linux.sh` | Linux one-click |