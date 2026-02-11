# Web Tool


## Why?
The Open-LLM-VTuber project leverages TTS and ASR (speech recognition) models to deliver an immersive, voice-to-voice AI companion experience.

While ASR and TTS technologies are powerful on their own, setting them up can be challenging. Previously, although our users installed the TTS and ASR models into our project, they were exclusively accessible as a part of the Open-LLM-VTuber's AI companion feature, preventing their use for other purposes like transcription or speech generation.

## What is Web Tool?

This is a dedicated web page within the Open-LLM-VTuber backend that provides direct access to the ASR and TTS models initialized by the Open-LLM-VTuber server.

Access the web page at: http://localhost:12393/web-tool. Note that the ASR and TTS models are the same ones you've set in the `conf.yaml` file, and switching models at runtime is not possible at this point.

## Direct Control (Sessions, Speak, System, Respond)

The web tool also exposes a minimal panel to directly control the active chat sessions:

- **Sessions**: list connected `client_uid`s and optionally apply actions to all.
- **Speak**: make the avatar speak a provided text via TTS-only flow (no memory).
- **System**: apply an invisible system instruction with mode `append` | `prepend` | `reset`.
- **Respond**: send user-style text to trigger a normal LLM response (with history/memory).

Endpoints called by the panel:

- `GET /v1/sessions`
- `POST /v1/control/speak`
- `POST /v1/control/system`
- `POST /v1/control/respond`

### Usage

1. Open the "Direct Control" section in the page.
2. Click "Refresh Sessions" and pick a session, or enable "Apply to all".
3. Use one of the tabs:
   - Speak: enter text and press "Send Speak".
   - System: enter instruction, choose mode, press "Apply System".
   - Respond: enter text and press "Trigger Respond".

### Notes

- Speak uses the same TTS pipeline as the app but does not write to chat history.
- Respond routes to the standard conversation pipeline and persists history.
- When a Live2D model is present, expressions are always extracted from tags like `[happy]` and those tags are removed from the text sent to TTS.
