# Multi-Agent AI: Why One Brain Isn't Enough for Streaming

If you've watched a high-level VTuber stream, you've seen multi-agent dynamics in action: the host reacts, the co-host interrupts, the mascot says something random. This isn't scripted — it's emergent behavior from multiple AI personalities interacting.

Open-LLM-VTuber's **CollabSquad** module makes this possible for any creator.

## The Problem with Single-Agent AI

A single LLM behind a VTuber has limitations:
- **Monotone personality** — one mood, one style
- **No comedic timing** — no one to interrupt
- **Unbounded talking** — no conversational floor management
- **Audience boredom** — same perspective, same pace

## How CollabSquad Works

CollabSquad manages multiple AI agents on a "conversational floor":

```python
from src.open_llm_vtuber.agent import CollabAgent, ConversationalFloorArbiter

agents = [
    CollabAgent(id="host", name="Mao", archetype="Host",
                 voice_slot="af_bella", interruption_propensity=0.2),
    CollabAgent(id="cohost", name="Luna", archetype="Tsundere",
                 voice_slot="af_sky", interruption_propensity=0.85),
    CollabAgent(id="mascot", name="Piko", archetype="Mascot",
                 voice_slot="af_sarah", interruption_propensity=0.5),
]

arbiter = ConversationalFloorArbiter(agents, max_consecutive_ai_turns=3)
```

## Key Features

### Turn Budget Enforcement
AI talks too long? After 3 consecutive AI turns, the floor yields to audience chat automatically. Chat stays interactive.

### Comedic Interruption
Luna (tsundere, propensity 0.85) hears Mao say "I'm the best"? She has a 51% chance to cut him off mid-sentence. Spontaneity emerges from personality parameters.

### Gaze Tracking
Each agent's Live2D head turns toward the active speaker:
- Speaker at center → listeners turn head
- Active speaker → looks at chat

### Gaze Calculations
```python
gazes = arbiter.calculate_gaze_orientations(active_speaker_id="cohost")
# {"host": -12.5, "cohost": 0.0, "mascot": 12.5}
```

## Why This Matters for YouTube

Multi-agent content outperforms single-agent content because:

| Metric | Single Agent | Multi-Agent | Improvement |
|---|---|---|---|
| Avg. Watch Time | 4 min | 8 min | +100% |
| Chat Messages/min | 15 | 45 | +200% |
| Clip Creation | 2/hr | 8/hr | +300% |
| Subscriber Conversion | 1% | 3.5% | +250% |

*The metrics above are illustrative based on industry benchmarks for multi-POV content.*

## Integration with Other Systems

CollabSquad integrates with the full Open-LLM-VTuber stack:
- **AffectiveEngine** — each agent has independent emotional state
- **CounterTrollCourtroom** — agents can testify against trolls
- **SocialRadar** — agents react to different trending topics
- **ChatWaveClusterer** — agents respond to different chat waves

## Try It

```bash
pip install open-llm-vtuber
python -c "
from src.open_llm_vtuber.agent import *
agents = [
    CollabAgent('1', 'Host', 'Host', 'af_bella', 0.2),
    CollabAgent('2', 'Co-Host', 'Tsundere', 'af_sky', 0.85),
]
arbiter = ConversationalFloorArbiter(agents)
# You're ready for multi-agent streaming
"
```

## Coming Soon

- **Personality-driven routing** — different LLMs per agent
- **Cross-agent memory** — agents remember shared experiences
- **Audience voting** — chat votes on which agent "wins" the argument

---

*The future of VTubing isn't one perfect AI — it's a cast of AI characters with real dynamics. Open-LLM-VTuber gives you the stage.*