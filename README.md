![](./assets/banner.jpg)

<h1 align="center">Open-LLM-VTuber</h1>
<h3 align="center">

[![GitHub release](https://img.shields.io/github/v/release/t41372/Open-LLM-VTuber)](https://github.com/t41372/Open-LLM-VTuber/releases) 
[![license](https://img.shields.io/github/license/t41372/Open-LLM-VTuber)](https://github.com/t41372/Open-LLM-VTuber/blob/master/LICENSE) 
[![CodeQL](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/actions/workflows/codeql.yml/badge.svg)](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/actions/workflows/codeql.yml)
[![Ruff](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/actions/workflows/ruff.yml/badge.svg)](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/actions/workflows/ruff.yml)
[![Docker](https://img.shields.io/badge/t41372%2FOpen--LLM--VTuber-%25230db7ed.svg?logo=docker&logoColor=blue&labelColor=white&color=blue)](https://hub.docker.com/r/t41372/open-llm-vtuber) 
[![QQ Group](https://img.shields.io/badge/QQ_Group-792615362-white?style=flat&logo=qq&logoColor=white)](https://qm.qq.com/q/ngvNUQpuKI)
[![QQ Channel](https://img.shields.io/badge/QQ_Channel_(dev)-pd93364606-white?style=flat&logo=qq&logoColor=white)](https://pd.qq.com/s/tt54r3bu)


[![BuyMeACoffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/yi.ting)
[![](https://dcbadge.limes.pink/api/server/3UDA8YFDXx)](https://discord.gg/3UDA8YFDXx)

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Open-LLM-VTuber/Open-LLM-VTuber)

ENGLISH README | [中文 README](https://github.com/t41372/Open-LLM-VTuber/blob/main/README.CN.md) | [한국어 README](https://github.com/t41372/Open-LLM-VTuber/blob/main/README.KR.md) | [日本語 README](https://github.com/t41372/Open-LLM-VTuber/blob/main/README.JP.md)

[Documentation](https://open-llm-vtuber.github.io/docs/quick-start) | [![Roadmap](https://img.shields.io/badge/Roadmap-GitHub_Project-yellow)](https://github.com/orgs/Open-LLM-VTuber/projects/2)

<a href="https://trendshift.io/repositories/12358" target="_blank"><img src="https://trendshift.io/api/badge/repositories/12358" alt="t41372%2FOpen-LLM-VTuber | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

</h3>


> 常见问题 Common Issues doc (Written in Chinese): https://docs.qq.com/pdf/DTFZGQXdTUXhIYWRq
>
> User Survey: https://forms.gle/w6Y6PiHTZr1nzbtWA
>
> 调查问卷(中文): https://wj.qq.com/s2/16150415/f50a/



> :warning: This project is in its early stages and is currently under **active development**.

> :warning: If you want to run the server remotely and access it on a different machine, such as running the server on your computer and access it on your phone, you will need to configure `https`, because the microphone on the front end will only launch in a secure context (a.k.a. https or localhost). See [MDN Web Doc](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia). Therefore, you should configure https with a reverse proxy to access the page on a remote machine (non-localhost).



## ⭐️ What is this project?


**Open-LLM-VTuber** is a unique **voice-interactive AI companion** that not only supports **real-time voice conversations**  and **visual perception** but also features a lively **Live2D avatar**. All functionalities can run completely offline on your computer!

You can treat it as your personal AI companion — whether you want a `virtual girlfriend`, `boyfriend`, `cute pet`, or any other character, it can meet your expectations. The project fully supports `Windows`, `macOS`, and `Linux`, and offers two usage modes: web version and desktop client (with special support for **transparent background desktop pet mode**, allowing the AI companion to accompany you anywhere on your screen).

Although the long-term memory feature is temporarily removed (coming back soon), thanks to the persistent storage of chat logs, you can always continue your previous unfinished conversations without losing any precious interactive moments.

In terms of backend support, we have integrated a rich variety of LLM inference, text-to-speech, and speech recognition solutions. If you want to customize your AI companion, you can refer to the [Character Customization Guide](https://open-llm-vtuber.github.io/docs/user-guide/live2d) to customize your AI companion's appearance and persona.

The reason it's called `Open-LLM-Vtuber` instead of `Open-LLM-Companion` or `Open-LLM-Waifu` is because the project's initial development goal was to use open-source solutions that can run offline on platforms other than Windows to recreate the closed-source AI Vtuber `neuro-sama`.

This project underwent code refactoring after version `v1.0.0` and is currently in active development, with many exciting features coming soon! 🚀 Check out our [Roadmap](https://github.com/users/t41372/projects/1/views/5) to learn about update plans.


### 👀 Demo
| ![](assets/i1.jpg) | ![](assets/i2.jpg) |
|:---:|:---:|
| ![](assets/i3.jpg) | ![](assets/i4.jpg) |


## ✨ Features & Highlights

- 🖥️ **Cross-platform support**: Perfect compatibility with macOS, Linux, and Windows. We support NVIDIA and non-NVIDIA GPUs, with options to run on CPU or use cloud APIs for resource-intensive tasks. Some components support GPU acceleration on macOS.

- 🔒 **Offline mode support**: Run completely offline using local models - no internet required. Your conversations stay on your device, ensuring privacy and security.

- 💻 **Attractive and powerful web and desktop clients**: Offers both web version and desktop client usage modes, supporting rich interactive features and personalization settings. The desktop client can switch freely between window mode and desktop pet mode, allowing the AI companion to be by your side at all times.

- 🎯 **Advanced interaction features**:
  - 👁️ Visual perception, supporting camera, screen recording and screenshots, allowing your AI companion to see you and your screen
  - 🎤 Voice interruption without headphones (AI won't hear its own voice)
  - 🫱 Touch feedback, interact with your AI companion through clicks or drags
  - 😊 Live2D expressions, set emotion mapping to control model expressions from the backend
  - 🐱 Pet mode, supporting transparent background, global top-most, and mouse click-through - drag your AI companion anywhere on the screen
  - 💭 Display AI's inner thoughts, allowing you to see AI's expressions, thoughts and actions without them being spoken
  - 🗣️ AI proactive speaking feature
  - 💾 Chat log persistence, switch to previous conversations anytime
  - 🌍 TTS translation support (e.g., chat in Chinese while AI uses Japanese voice)

- 🧠 **Extensive model support**:
  - 🤖 Large Language Models (LLM): Ollama, OpenAI (and any OpenAI-compatible API), Gemini, Claude, Mistral, DeepSeek, Zhipu AI, GGUF, LM Studio, vLLM, etc.
  - 🎙️ Automatic Speech Recognition (ASR): sherpa-onnx, FunASR, Faster-Whisper, Whisper.cpp, Whisper, Groq Whisper, Azure ASR, etc.
  - 🔊 Text-to-Speech (TTS): sherpa-onnx, pyttsx3, MeloTTS, Coqui-TTS, GPTSoVITS, Bark, CosyVoice, Edge TTS, Fish Audio, Azure TTS, etc.

- 🔧 **Highly customizable**:
  - ⚙️ **Simple module configuration**: Switch various functional modules through simple configuration file modifications, without delving into the code
  - 🎨 **Character customization**: Import custom Live2D models to give your AI companion a unique appearance. Shape your AI companion's persona by modifying the Prompt. Perform voice cloning to give your AI companion the voice you desire
  - 🧩 **Flexible Agent implementation**: Inherit and implement the Agent interface to integrate any Agent architecture, such as HumeAI EVI, OpenAI Her, Mem0, etc.
  - 🔌 **Good extensibility**: Modular design allows you to easily add your own LLM, ASR, TTS, and other module implementations, extending new features at any time


## 👥 User Reviews
> Thanks to the developer for open-sourcing and sharing the girlfriend for everyone to use
> 
> This girlfriend has been used over 100,000 times


## 🚀 Quick Start

Please refer to the [Quick Start](https://open-llm-vtuber.github.io/docs/quick-start) section in our documentation for installation.


## Running Open-LLM-VTuber in Web Mode

- **Command to start the web server:** `uv run run_server.py` (append `--verbose` for debug-level console logs).
- **Local URL:** http://localhost:12393 by default, derived from `system_config.host` and `system_config.port` in `conf.yaml` (generated from `config_templates/conf.default.yaml`).
- **Microphone availability:** The browser microphone works only on `https` origins or `localhost`; remote access requires configuring HTTPS (for example, via a reverse proxy).
- **Log files:** Runtime logs are written to `logs/debug_<date>.log` with daily rotation; console logs mirror the selected log level (`INFO` by default or `DEBUG` when `--verbose` is used).

## Demo Walkthrough (No Extra Code)

1. Start the backend with your valid `conf.yaml` (LLM/ASR/TTS keys set) using `uv run run_server.py --verbose` so you can see live logs.
2. Open `http://localhost:12393` in a desktop browser on the same machine as the server.
3. When prompted, allow microphone access (use the default input; there is no device picker) and wait for the connection indicator to show you are connected.
4. If the mic is idle, click the microphone button, then say “Oi, tudo bem?” to send a Portuguese voice message and hear the spoken reply.
5. In the text box, type “Responda em inglês” and send to get an English answer from the agent.
6. Send “Agora responda em japonês” to receive a Japanese reply, keeping the voice output flowing through the same session.


### Activating the Akira Cohost Persona (optional)

1. Confirm `persona/cohost_vtuber.yaml` is present (it ships with the repo).
2. In `conf.yaml`, set `system_config.active_persona_id: ${ACTIVE_PERSONA_ID}` and export `ACTIVE_PERSONA_ID=cohost_vtuber` (or hardcode `cohost_vtuber`).
3. Start the server normally; if no ID is set the existing persona remains unchanged.



## Configuration Touchpoints (Where to Set Keys, Models, Audio, Language, Persona)

| File (examples) | Field / Path | Function / How It Is Used |
| --- | --- | --- |
| `conf.yaml` (from `config_templates/conf.default.yaml` or `conf.ZH.default.yaml`) and overrides in `characters/*.yaml` | `character_config.agent_config.llm_configs.<provider>.(llm_api_key/base_url/model)` | Loaded via `ServiceContext.init_agent`, then passed into `AgentFactory.create_agent` to build the active LLM client (keys, endpoints, and model identifiers). |
| `conf.yaml` or `characters/*.yaml` | `character_config.persona_prompt` plus `system_config.tool_prompts` | Combined into the system prompt by `ServiceContext.construct_system_prompt`, which appends tool prompts (Live2D, MCP, etc.) before the agent starts. |
| `conf.yaml` | `system_config.active_persona_id` | `ServiceContext.load_from_config` + `utils.persona_loader` | Optional override to pick a persona YAML from `/persona` (e.g., `cohost_vtuber`). Leave `null` to keep existing persona behavior. |
| `conf.yaml` | `character_config.asr_config.asr_model` and the matching engine block (e.g., `groq_whisper_asr.api_key/model/lang`, `faster_whisper.model_path/language/prompt`) | Initialized by `ServiceContext.init_asr`, which calls `ASRFactory.get_asr_system` with the chosen model and credentials to decode microphone audio. |
| `conf.yaml` | `character_config.tts_config.tts_model` and its engine section (voices, `api_key`, `model`, speed/volume knobs) | Wired through `ServiceContext.init_tts` to `TTSFactory.get_tts_engine`, controlling synthesized voice output parameters and credentials. |
| `conf.yaml` | `character_config.vad_config` (e.g., `vad_model`, thresholds) | Passed to `ServiceContext.init_vad` to enable/disable voice-activity gating on the captured microphone stream. |
| `conf.yaml` | `character_config.tts_preprocessor_config.translator_config` (e.g., `translate_audio`, `deeplx_target_lang`, provider API settings) | Routed by `ServiceContext.init_translate` to `TranslateFactory.get_translator` to handle language conversion before TTS. |
| `config_manager/utils.py` | Environment variables referenced as `${VAR}` inside YAML values | Substituted by `read_yaml`, allowing keys like `${GROQ_API_KEY}` to be injected without hardcoding secrets. |


## Configuring Groq as the LLM (OpenAI-Compatible)

- **Where to configure:** `conf.yaml` (generated from `config_templates/conf.default.yaml` or `config_templates/conf.ZH.default.yaml`) under `character_config -> agent_config`. The active agent points to an entry in `llm_configs`, which holds provider credentials and endpoints.
- **Required fields for Groq:** `base_url`, `llm_api_key`, and `model` in the `groq_llm` block. `base_url` must remain `https://api.groq.com/openai/v1` for OpenAI-compatible requests.
- **Safe example (uses environment variables):**

```yaml
character_config:
  agent_config:
    agent_settings:
      basic_memory_agent:
        llm_provider: 'groq_llm'
    llm_configs:
      groq_llm:
        base_url: 'https://api.groq.com/openai/v1'
        llm_api_key: '${GROQ_API_KEY}'
        model: 'llama-3.1-70b-versatile'
        temperature: 1.0
```


## Speech-to-Text (ASR) – Known Good Setup

- **Supported engines:** Select one of `faster_whisper`, `whisper_cpp`, `whisper`, `azure_asr`, `fun_asr`, `groq_whisper_asr`, or `sherpa_onnx_asr` via `character_config -> asr_config -> asr_model` in `conf.yaml`. Each engine’s configuration block (API keys, model paths, language hints, etc.) sits under `character_config -> asr_config`.
- **Simple Windows setup:** For a minimal, no-extra-download option, set `asr_model` to `groq_whisper_asr` and provide `GROQ_API_KEY` as an environment variable; the service calls Groq’s hosted Whisper model without local dependencies:

  ```yaml
  character_config:
    asr_config:
      asr_model: 'groq_whisper_asr'
      groq_whisper_asr:
        api_key: '${GROQ_API_KEY}'
        model: 'whisper-large-v3-turbo'
        lang: ''  # leave blank for auto
  ```

- **Microphone selection:** The web client starts the default browser microphone automatically (no per-device selector in the current UI) when the backend sends a `start-mic` control message on connection.
- **Where audio is captured:** The browser uses `navigator.mediaDevices.getUserMedia` with a mono 16 kHz stream; audio chunks are recorded via `MediaRecorder` and converted to WAV before upload.


## Text-to-Speech (TTS) Configuration

- **Supported engines:** Choose any of the engines exposed by `tts_config.tts_model` in `conf.yaml`: `azure_tts`, `bark_tts`, `edge_tts`, `pyttsx3_tts`, `cosyvoice_tts`, `cosyvoice2_tts`, `melo_tts`, `x_tts`, `gpt_sovits_tts`, `siliconflow_tts`, `coqui_tts`, `fish_api_tts`, `minimax_tts`, `sherpa_onnx_tts`, `openai_tts`, `spark_tts`, `elevenlabs_tts`, `cartesia_tts`, or `piper_tts`. The factory at runtime loads the matching block from `character_config -> tts_config` and initializes the corresponding engine.
- **Where to configure:** `conf.yaml` (from `config_templates/conf.default.yaml` or `config_templates/conf.ZH.default.yaml`) under `character_config -> tts_config`. Each engine has its own nested block for credentials, URLs, and voice/model choices; the server binds them through `service_context.init_tts`.
- **Local model / voice paths:** Examples in the template show local paths where you place downloads: Piper expects an ONNX model such as `models/piper/zh_CN-huayan-medium.onnx`; Sherpa-ONNX uses explicit paths for `vits_model`, `vits_tokens`, and `vits_lexicon`; Coqui can reference local speaker WAVs; GPT-SoVITS can point `ref_audio_path` to a prompt clip. Update those paths to where you store models on disk.
- **Tuning voice, speed, and volume:** Adjust per-engine fields in `conf.yaml`:
  - Azure: `voice`, `pitch`, and `rate`.
  - Edge: `voice` selection.
  - Piper: `length_scale` (speed), `noise_scale`/`noise_w` (style), and `volume`.
  - CosyVoice2/Melo/Cartesia/SiliconFlow: `speed` plus voice or emotion fields; Cartesia also supports `volume`.
  - OpenAI-compatible and Minimax: choose `voice`/`voice_id` and `model` values expected by the provider.
- **Safe example (Edge TTS, no API keys):**

  ```yaml
  character_config:
    tts_config:
      tts_model: 'edge_tts'
      edge_tts:
        voice: 'en-US-AvaMultilingualNeural'
  ```


## Memory, History and Persistence

- **Where history is stored:** Each conversation is written as JSON under `chat_history/<conf_uid>/<history_uid>.json` (created on demand), so transcripts persist across restarts unless the files are removed manually.
- **User/persona preferences:** The active persona, prompts, model choices, and identifiers live in `conf.yaml` (see `character_config.conf_uid` and `persona_prompt`) and can be overridden per persona via the `characters/` YAML files referenced by `system_config.config_alts_dir`.
- **Viewing/clearing history from the UI:** The WebSocket backend exposes `history-list`, `history-data`, `new-history-created`, and `history-deleted` message types so a frontend can list, load, create, or delete histories; the shipped code does not bundle a standalone UI panel in this repo, but any compatible client can call these actions.
- **Long-term memory:** No vector or database-backed long-term memory is implemented; the agent rebuilds its working memory from the selected chat history file at session start and otherwise retains messages in-memory only for the current run.


## Live2D Setup (Web Mode)

- **Browser support:** The web server mounts the `live2d-models` directory and sends the selected model metadata (`set-model-and-conf` with `model_info`) as soon as the WebSocket client connects, so a Live2D-capable frontend can load the model in the browser.
- **Where to place assets:** Drop each Live2D model folder under the project root `live2d-models/` with a matching `<name>/<name>.model3.json` (and optional `<name>.png` avatar). The `/live2d-models/info` endpoint enumerates these folders for the UI.
- **Choosing the active model:** Set `character_config.live2d_model_name` in `conf.yaml` (default `mao_pro` in the template). The backend looks up that name in `model_dict.json` to find the model URL, scale, and emotion map pushed to the client.
- **How the avatar reacts:** During generation, the backend extracts emotion tags into `actions.expressions` and attaches per-chunk normalized volume data in each audio payload. A Live2D frontend can consume those cues for expressions or lip sync; the backend does not render Live2D itself.


## ☝ Update
> :warning: `v1.0.0` has breaking changes and requires re-deployment. You *may* still update via the method below, but the `conf.yaml` file is incompatible and most of the dependencies needs to be reinstalled with `uv`. For those who came from versions before `v1.0.0`, I recommend deploy this project again with the [latest deployment guide](https://open-llm-vtuber.github.io/docs/quick-start).

Please use `uv run update.py` to update if you installed any versions later than `v1.0.0`.

## 😢 Uninstall  
Most files, including Python dependencies and models, are stored in the project folder.

However, models downloaded via ModelScope or Hugging Face may also be in `MODELSCOPE_CACHE` or `HF_HOME`. While we aim to keep them in the project's `models` directory, it's good to double-check.  

Review the installation guide for any extra tools you no longer need, such as `uv`, `ffmpeg`, or `deeplx`.  

## 🤗 Want to contribute?
Checkout the [development guide](https://docs.llmvtuber.com/docs/development-guide/overview).


# 🎉🎉🎉 Related Projects

[ylxmf2005/LLM-Live2D-Desktop-Assitant](https://github.com/ylxmf2005/LLM-Live2D-Desktop-Assitant)
- Your Live2D desktop assistant powered by LLM! Available for both Windows and MacOS, it senses your screen, retrieves clipboard content, and responds to voice commands with a unique voice. Featuring voice wake-up, singing capabilities, and full computer control for seamless interaction with your favorite character.






## 📜 Third-Party Licenses

### Live2D Sample Models Notice

This project includes Live2D sample models provided by Live2D Inc. These assets are licensed separately under the Live2D Free Material License Agreement and the Terms of Use for Live2D Cubism Sample Data. They are not covered by the MIT license of this project.

This content uses sample data owned and copyrighted by Live2D Inc. The sample data are utilized in accordance with the terms and conditions set by Live2D Inc. (See [Live2D Free Material License Agreement](https://www.live2d.jp/en/terms/live2d-free-material-license-agreement/) and [Terms of Use](https://www.live2d.com/eula/live2d-sample-model-terms_en.html)).

Note: For commercial use, especially by medium or large-scale enterprises, the use of these Live2D sample models may be subject to additional licensing requirements. If you plan to use this project commercially, please ensure that you have the appropriate permissions from Live2D Inc., or use versions of the project without these models.


## Contributors
Thanks our contributors and maintainers for making this project possible.

<a href="https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Open-LLM-VTuber/Open-LLM-VTuber" />
</a>


## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=t41372/open-llm-vtuber&type=Date)](https://star-history.com/#t41372/open-llm-vtuber&Date)





