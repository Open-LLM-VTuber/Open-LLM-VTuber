# Open-LLM-VTuber

[中文](https://github.com/t41372/Open-LLM-VTuber/blob/main/README.CN.md)

[![GitHub release](https://img.shields.io/github/v/release/t41372/Open-LLM-VTuber)](https://github.com/t41372/Open-LLM-VTuber/releases) 
[![license](https://img.shields.io/github/license/t41372/Open-LLM-VTuber)](https://github.com/t41372/Open-LLM-VTuber/blob/master/LICENSE) 
[![](https://img.shields.io/badge/t41372%2FOpen--LLM--VTuber-%25230db7ed.svg?logo=docker&logoColor=blue&labelColor=white&color=blue)](https://hub.docker.com/r/t41372/open-llm-vtuber) 
[![](https://img.shields.io/badge/todo_list-GitHub_Project-blue)](https://github.com/users/t41372/projects/1/views/1)

[![BuyMeACoffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/yi.ting) [![](https://dcbadge.limes.pink/api/server/3UDA8YFDXx)](https://discord.gg/3UDA8YFDXx) <- (Clickable links)


(QQ群: 792615362）<- way more active than Discord group with over 700 population and majority of the contributors
> 常见问题 Common Issues doc (Written in Chinese): https://docs.qq.com/doc/DTHR6WkZ3aU9JcXpy
>
> User Survey: https://forms.gle/w6Y6PiHTZr1nzbtWA
>
> 调查问卷(中文)(现在不用登入了): https://wj.qq.com/s2/16150415/f50a/



> :warning: This project is in its early stages and is currently under **active development**. Features are unstable, code is messy, and breaking changes will occur. The main goal of this stage is to build a minimum viable prototype using technologies that are easy to integrate.

> :warning: This project is **NOT** easy to install. Join the Discord server or QQ group if you need help or to get updates about this project.

> :warning: If you want to run this program on a server and access it remotely on your laptop, the microphone on the front end will only launch in a secure context (a.k.a. https or localhost). See [MDN Web Doc](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia). Therefore, you should configure https with a reverse proxy to access the page on a remote machine (non-localhost).

> You are right if you think this README and the docs are super duper messy! A complete refactoring of the documentation is planned. In the meantime, you can watch the installation videos if you speak Chinese.


### ❓ What is this project?


Open-LLM-VTuber allows you to talk to (and interrupt!) any LLM locally by voice (hands-free) with a Live2D talking face. The LLM inference backend, speech recognition, and speech synthesizer are all designed to be swappable. This project can be configured to run offline on macOS, Linux, and Windows. Online LLM/ASR/TTS options are also supported.

Long-term memory with MemGPT can be configured to achieve perpetual chat, infinite* context length, and external data source.

This project started as an attempt to recreate the closed-source AI VTuber `neuro-sama` with open-source alternatives that can run offline on platforms other than Windows.


<img width="500" alt="demo-image" src="https://github.com/t41372/Open-LLM-VTuber/assets/36402030/fa363492-7c01-47d8-915f-f12a3a95942c"/>



### Demo

English demo:





https://github.com/user-attachments/assets/f13b2f8e-160c-4e59-9bdb-9cfb6e57aca9


English Demo:
[YouTube](https://youtu.be/gJuPM_2qEZc)


中文 demo:

[BiliBili](https://www.bilibili.com/video/BV1krHUeRE98/), [YouTube](https://youtu.be/cb5anPTNklw)



### Why this project and not other similar projects on GitHub?
- It works on macOS
  - Many existing solutions display Live2D models with VTube Studio and achieve lip sync by routing desktop internal audio into VTube Studio and controlling the lips with that. On macOS, however, there is no easy way to let VTuber Studio listen to internal audio on the desktop.
  - Many existing solutions lack support for GPU acceleration on macOS, which makes them run slow on Mac.
- This project supports [MemGPT](https://github.com/cpacker/MemGPT) for perpetual chat. The chatbot remembers what you've said.
- No data leaves your computer if you wish to
  - You can choose local LLM/voice recognition/speech synthesis solutions; everything works offline. Tested on macOS.
- You can interrupt the LLM anytime with your voice without wearing headphones.






### Basic Features
- [x] Chat with any LLM by voice
- [x] Interrupt LLM with voice at any time
- [x] Choose your own LLM backend
- [x] Choose your own Speech Recognition & Text to Speech provider
- [x] Long-term memory
- [x] Live2D frontend

### Target Platform
- macOS
- Linux
- Windows

### Recent Feature Updates
Check out the GitHub Release for updated notes.

## Implemented Features

- Talk to LLM with voice. Offline.
- ~~RAG on chat history~~ *(temporarily removed)*
- **Externalized Persona Prompts**: Customize your VTuber's personality easily by editing `prompts/persona/persona_prompt.md` (or any file specified in `conf.yaml`).
- **Email Sending via SMTP**: Configure the application to send emails (e.g., notifications, chat logs) using your own SMTP server.
- **Enhanced Conversation Recording**:
    - Text transcripts of conversations are saved in `CHAT_HISTORY_DIR/session_id/transcript.txt`.
    - User voice input can be recorded and saved (default: WAV format).
    - AI TTS output audio can also be recorded and saved.
- **Internet Access Module**:
    - Fetch content from web pages.
    - Perform web searches (currently using DuckDuckGo).

Currently supported LLM backend
- Any OpenAI-API-compatible backend, such as Ollama, Groq, LM Studio, OpenAI, and more.
- Claude
- llama.cpp local inference within this project
- MemGPT (broken)
- Mem0 (not great)

Currently supported Speech recognition backend
- [FunASR](https://github.com/modelscope/FunASR), which support [SenseVoiceSmall](https://github.com/FunAudioLLM/SenseVoice) and many other models. (~~Local~~ Currently requires an internet connection for loading. Compute locally)
- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) (Local)
- [Whisper-CPP](https://github.com/ggerganov/whisper.cpp) using the python binding [pywhispercpp](https://github.com/abdeladim-s/pywhispercpp) (Local, mac GPU acceleration can be configured)
- [Whisper](https://github.com/openai/whisper) (local)
- [Groq Whisper](https://groq.com/) (API Key required). This is a hosted Whisper endpoint. It's fast and has a generous free limit every day.
- [Azure Speech Recognition](https://azure.microsoft.com/en-us/products/ai-services/speech-to-text) (API Key required)
- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) (Local, fast, supports various models including transducer, Paraformer, NeMo CTC, WeNet CTC, Whisper, TDNN CTC, and SenseVoice models.)
- The microphone in the server terminal will be used by default. You can change the setting `MIC_IN_BROWSER` in the `conf.yaml` to move the microphone (and voice activation detection) to the browser (at the cost of latency, for now). You might want to use the microphone on your client (the browser) rather than the one on your server if you run the backend on a different machine or inside a VM or docker.

Currently supported Text to Speech backend
- [py3-tts](https://github.com/thevickypedia/py3-tts) (Local, it uses your system's default TTS engine)
- [meloTTS](https://github.com/myshell-ai/MeloTTS) (Local, fast)
- [Coqui-TTS](https://github.com/idiap/coqui-ai-TTS) (Local, speed depends on the model you run.)
- [bark](https://github.com/suno-ai/bark) (Local, very resource-consuming)
- [CosyVoice](https://github.com/FunAudioLLM/CosyVoice) (Local, very resource-consuming)
- [xTTSv2](https://github.com/daswer123/xtts-api-server) (Local, very resource-consuming)
- [Edge TTS](https://github.com/rany2/edge-tts) (online, no API key required)
- [Azure Text-to-Speech](https://azure.microsoft.com/en-us/products/ai-services/text-to-speech) (online, API Key required)
- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) (Local, fast, supports various models. For English, piper models are recommended. For pure Chinese, consider using [sherpa-onnx-vits-zh-ll.tar.bz2](https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/sherpa-onnx-vits-zh-ll.tar.bz2). For a mix of Chinese and English, [vits-melo-tts-zh_en.tar.bz2](https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-melo-tts-zh_en.tar.bz2) can be used, though the English pronunciation might not be ideal.)
- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) (checkout doc [here](https://docs.qq.com/doc/DTHR6WkZ3aU9JcXpy))

Fast Text Synthesis
- Synthesize sentences as soon as they arrive, so there is no need to wait for the entire LLM response.
- Producer-consumer model with multithreading: Audio will be continuously synthesized in the background. They will be played one by one whenever the new audio is ready. The audio player will not block the audio synthesizer.

Live2D Talking face
- Change Live2D model with `config.yaml` (model needs to be listed in model_dict.json)
- Load local Live2D models. Check `doc/live2d.md` for documentation.
- Uses expression keywords in LLM response to control facial expression, so there is no additional model for emotion detection. The expression keywords are automatically loaded into the system prompt and excluded from the speech synthesis output.

live2d technical details
- Uses [guansss/pixi-live2d-display](https://github.com/guansss/pixi-live2d-display) to display live2d models in *browser*
- Uses WebSocket to control facial expressions and talking state between the server and the front end
- All the required packages are locally available, so the front end works offline. 
- You can load live2d models from a URL or the one stored locally in the `live2d-models` directory. The default `shizuku-local` is stored locally and works offline. If the URL property of the model in the model_dict.json is a URL rather than a path starting with `/live2d-models`, they will need to be fetched from the specified URL whenever the front end is opened. Read `doc/live2d.md` for documentation on loading your live2D model from local.
- Run the `server.py` to run the WebSocket communication server, open the `index.html` in the `./static` folder to open the front end, and run ~~`launch.py`~~ `main.py` to run the backend for LLM/ASR/TTS processing.

## Quick Start

If you speak Chinese, there are two installation videos for you.
- (preferred 🎉) `v0.4.3` [Complete Tutorial with auto-install script for Windows users](https://www.bilibili.com/video/BV1UDz4YcEr8/)
- `v0.2.4` [manual installation tutorial on macOS](https://www.bilibili.com/video/BV1GYSrYKE8i/)

If you don't speak Chinese, good luck. Let me know if you create on in other languages so I can put it here.

> **New installation instruction is being created [here](https://github.com/t41372/Open-LLM-VTuber/wiki)**



### One-click gogo script
A new quick start script (experimental) was added in `v0.4.0`.
This script allows you to get this project running without worrying (too much) about the dependencies.
The only thing you need for this script is Python, a good internet connection, and enough disk space.

This script will do the following:
- download miniconda in the project directory
- create a conda environment in the project directory
- install all the dependencies you need for the configuration of `FunASR` + `edgeTTS` (you still need to get an ollama or some OpenAI compatible backend)
- run this project inside the conda environment

Run the script with `python start_webui.py`. Note that you should always use `start_webui.py` as the entry point if you decide to use the auto-installation script because `server.py` doesn't start the conda environment for you.

Also note that if you want to install other dependencies, you need to enter the auto-configured conda environment first by running `python activate_conda.py`


## Manual installation

In general, there are 4 steps involved in getting this project running:
1. basic setup
2. Get the LLM (large language model)
3. Get the TTS (text-to-speech)
4. Get the ASR (speech recognition)

### Requirements:
- ffmpeg
- Python >= 3.10, < 3.13 (3.13 doesn't work for now)

Clone this repository.

Virtual Python environment like conda or venv is strongly recommended! (because the dependencies are a mess!). 

Run the following in the terminal to install the basic dependencies.

~~~shell
pip install -r requirements.txt # Run this in the project directory 
# Install Speech recognition dependencies and text-to-speech dependencies according to the instructions below
# Ensure new dependencies for recently added features are also installed:
# pip install beautifulsoup4 duckduckgo-search
# scipy is used for audio saving and should be covered by requirements.txt
~~~


Edit the `conf.yaml` for configurations. You can follow the configuration used in the demo video.
Key configuration sections to review include:
- `LLM_PROVIDER`, `ASR_MODEL`, `TTS_MODEL` for core functionality.
- `PERSONA_PROMPT_FILE`: Specifies the Markdown file for the persona prompt, located in the `prompts/persona/` directory (default: `persona_prompt.md`).
- `RECORDING`:
    - `RECORD_CONVERSATIONS`: Master switch to enable/disable saving of text transcripts, user audio, and AI TTS audio.
    - `AUDIO_RECORDING_FORMAT`: Format for saved audio (e.g., "wav"). Recordings are stored under `CHAT_HISTORY_DIR/session_id/`.
- `SMTP` (for Email Sending):
    - Configure `HOST`, `PORT`, `USE_TLS`, `USE_SSL`, `USERNAME`, `PASSWORD`, and `SENDER_EMAIL`. **Important**: Replace placeholder credentials with your actual SMTP server details.
- `INTERNET_ACCESS`:
    - `ENABLED`: Master switch for web fetching and search.
    - `USER_AGENT`: User-Agent for web requests.
    - `SEARCH_ENGINE_API`: Currently supports "duckduckgo".
    - `MAX_SEARCH_RESULTS`: Default number of search results.
    - `MAX_PAGE_CONTENT_LENGTH`: Max characters of text to extract from a webpage.
Refer to the detailed comments within `conf.yaml` for each setting.

Once the live2D model appears on the screen, it's ready to talk to you.

Once the live2D model appears on the screen, it's ready to talk to you.

~~If you don't want the live2d, you can run `main.py` with Python for cli mode. ~~ (CLI mode is deprecated now and will be removed in `v1.0.0`. If some still want the cli mode, maybe we can make a cli client in the future, but the current architecture will be refactored very soon)

Some models will be downloaded on your first launch, which may require an internet connection and may take a while.



### Update
🎉 A new experimental update script was added in `v0.3.0`. Run `python upgrade.py` to update to the latest version.

Back up the configuration files `conf.yaml` if you've edited them, and then update the repo.
Or just clone the repo again and make sure to transfer your configurations. The configuration file will sometimes change because this project is still in its early stages. Be cautious when updating the program.


## Configure LLM

### OpenAI compatible LLM such as Ollama, LM Studio, vLLM, groq, ZhiPu, Gemini, OpenAI, and more
Put `ollama` into `LLM_PROVIDER` option in `conf.yaml` and fill the settings.

If you use the official OpenAI API, the base_url is `https://api.openai.com/v1`.


### Claude

Claude support was added in `v0.3.1` in https://github.com/t41372/Open-LLM-VTuber/pull/35

Change the `LLM_PROVIDER` to `claude` and complete the settings under `claude`


### LLama CPP (added in `v0.5.0-alpha.2`)

Provides a way to run LLM **within** this project without any external tools like ollama. A `.gguf` model file is all you need.

#### Requirements

According to the [project repo](https://github.com/abetlen/llama-cpp-python)

Requirements:

- Python 3.8+
- C compiler
  - Linux: gcc or clang
  - Windows: Visual Studio or MinGW
  - MacOS: Xcode

This will also build `llama.cpp` from the source and install it alongside this Python package.

If this fails, add `--verbose` to the `pip install` see the full cmake build log.



### Installation

Find the `pip install llama-cpp-python` command for your platform [here](https://github.com/abetlen/llama-cpp-python?tab=readme-ov-file#supported-backends). 

For example:

if you use an Nvidia GPU, run this.

`CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python`

If you use an apple silicon Mac (like I do), do this:

`CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python`

If you use an AMD GPU that supports ROCm:

`CMAKE_ARGS="-DGGML_HIPBLAS=on" pip install llama-cpp-python`

If you want to use CPU (OpenBlas):

`CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS" pip install llama-cpp-python`



For more options, check [here](https://github.com/abetlen/llama-cpp-python?tab=readme-ov-file#supported-backends).





### MemGPT (Broken and will probably be removed rather than fixed)

> :warning: MemGPT was renamed to Letta, and they changed their API. Currently, the integration of MemGPT in this project has not been updated with the latest changes, so the integration is broken.
> It probably won't get fixed because MemGPT (or Letta now) is quite slow and unstable for local LLMs. A new long-term memory solution is planned.

However, you can still get the old version of MemGPT and try it out. Here is the documentation.

> MemGPT integration is very experimental and requires quite a lot of setup. In addition, MemGPT requires a powerful LLM (larger than 7b and quantization above Q5) with a lot of token footprint, which means it's a lot slower.
> MemGPT does have its own LLM endpoint for free, though. You can test things with it. Check their docs.

This project can use [MemGPT](https://github.com/cpacker/MemGPT) as its LLM backend. MemGPT enables LLM with long-term memory.

To use MemGPT, you need to have the MemGPT server configured and running. You can install it using `pip` or `docker` or run it on a different machine. Check their [GitHub repo](https://github.com/cpacker/MemGPT) and [official documentation](https://memgpt.readme.io/docs/index).

> :warning:
> I recommend you install MemGPT either in a separate Python virtual environment or in docker because there is currently a dependency conflict between this project and MemGPT (on fast API, it seems). You can check this issue [Can you please upgrade typer version in your dependancies #1382](https://github.com/cpacker/MemGPT/issues/1382).



Here is a checklist:
- Install memgpt
- Configure memgpt
- Run `memgpt` using `memgpt server` command. Remember to have the server running before launching Open-LLM-VTuber.
- Set up an agent either through its cli or web UI. Add your system prompt with the Live2D Expression Prompt and the expression keywords you want to use (find them in `model_dict.json`) into MemGPT
- Copy the `server admin password` and the `Agent id` into `./llm/memgpt_config.yaml`. *By the way, `agent id` is not the agent's name*.
- Set the `LLM_PROVIDER` to `memgpt` in `conf.yaml`. 
- Remember, if you use `memgpt`, all LLM-related configurations in `conf.yaml` will be ignored because `memgpt` doesn't work that way.



### Mem0 (it turns out it's not very good for our use case, but the code is here...)

Another long-term memory solution. Still in development. Highly experimental.

Pro

- It's easier to set up compared to MemGPT
- It's a bit faster than MemGPT (but still would take quite a lot more LLM tokens to process)

Cons

- It remembers your preferences and thoughts, nothing else. It doesn't remember what the LLM said.
- It doesn't always put stuff into memory.
- It sometimes remembers wrong stuff
- It requires an LLM with very good function calling capability, which is quite difficult for smaller models
- 


## Install Speech Recognition (ASR)
Edit the ASR_MODEL settings in the `conf.yaml` to change the provider.

Here are the options you have for speech recognition:

`sherpa-onnx` (local, runs very fast) (added in `v0.5.0-alpha.1` in https://github.com/t41372/Open-LLM-VTuber/pull/50)
- Install with `pip install sherpa-onnx`. (~20MB)
- Download your desired model from [sherpa-onnx ASR models](https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models).
- Refer to `config_alts` in the repository for configuration examples and modify the model path in your `conf.yaml` accordingly.
- It offers great performance and is significantly lighter than FunASR.


`FunASR` (~~local~~) (Runs very fast even on CPU. Not sure how they did it)
- [FunASR](https://github.com/modelscope/FunASR?tab=readme-ov-file) is a Fundamental End-to-End Speech Recognition Toolkit from ModelScope that runs many ASR models. The result and speed are pretty good with the SenseVoiceSmall from [FunAudioLLM](https://github.com/FunAudioLLM/SenseVoice) at Alibaba Group.
- Install with `pip install -U funasr modelscope huggingface_hub`. Also, ensure you have torch (torch>=1.13) and torchaudio. Install them with `pip install torch torchaudio onnx` (FunASR now requires `onnx` as well)
- It requires an internet connection on launch _even if the models are locally available_. See https://github.com/modelscope/FunASR/issues/1897

`Faster-Whisper` (local)
- Whisper, but faster. On macOS, it runs on CPU only, which is not so fast, but it's easy to use.
- For Nvidia GPU users, to use GPU acceleration, you need the following NVIDIA libraries to be installed:
  - [cuBLAS for CUDA 12](https://developer.nvidia.com/cublas)
  - [cuDNN 8 for CUDA 12](https://developer.nvidia.com/cudnn)
- Or if you don't need the speed, you can set the `device` setting under `Faster-Whisper` in `conf.yaml` to `cpu` to reduce headaches.


`WhisperCPP` (local) (runs super fast on a Mac if configured correctly)
- If you are on a Mac, read below for instructions on setting up WhisperCPP with coreML support. If you want to use CPU or Nvidia GPU, install the package by running `pip install pywhispercpp`.
- The whisper cpp python binding. It can run on coreML with configuration, which makes it very fast on macOS.
- On CPU or Nvidia GPU, it's probably slower than Faster-Whisper

WhisperCPP coreML configuration:
- Uninstall the original `pywhispercpp` if you have already installed it. We are building the package.
- Run `install_coreml_whisper.py` with Python to automatically clone and build the coreML-supported `pywhispercpp` for you.
- Prepare the appropriate coreML models.
  - You can either convert models to coreml according to the documentation on Whisper.cpp repo
  - ...or you can find some [magical huggingface repo](https://huggingface.co/chidiwilliams/whisper.cpp-coreml/tree/main) that happens to have those converted models. Just remember to decompress them. If the program fails to load the model, it will produce a segmentation fault.
  - You don't need to include those weird prefixes in the model name in the `conf.yaml`. For example, if the coreML model's name looks like `ggml-base-encoder.mlmodelc`, just put `base` into the `model_name` under `WhisperCPP` settings in the `conf.yaml`.

`Whisper` (local)
- Original Whisper from OpenAI. Install it with `pip install -U openai-whisper`
- The slowest of all. Added as an experiment to see if it can utilize macOS GPU. It didn't.

`GroqWhisperASR` (online, API Key required)

- Whisper endpoint from Groq. It's very fast and has a lot of free usage every day. It's pre-installed. Get an API key from [groq](https://console.groq.com/keys) and add it into the GroqWhisper setting in the `conf.yaml`.
- API key and internet connection are required.

`AzureASR` (online, API Key required)

- Azure Speech Recognition. Install with `pip install azure-cognitiveservices-speech`.
- API key and internet connection are required.
- **⚠️ ‼️ The `api_key.py` was deprecated in `v0.2.5`. Please set api keys in `conf.yaml`.**

## Install Speech Synthesis (text to speech) (TTS)
Install the respective package and turn it on using the `TTS_MODEL` option in `conf.yaml`.

`sherpa-onnx` (local) (added in `v0.5.0-alpha.1` in https://github.com/t41372/Open-LLM-VTuber/pull/50)
- Install with `pip install sherpa-onnx`.
- Download your desired model from [sherpa-onnx TTS models](https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models).
- Refer to `config_alts` in the repository for configuration examples and modify the model path in your `conf.yaml` accordingly.

`pyttsx3TTS` (local, fast)
- Install with the command `pip install py3-tts`.
- This package will use the default TTS engine on your system. It uses `sapi5` on Windows, `nsss` on Mac, and `espeak` on other platforms.
- `py3-tts` is used instead of the more famous `pyttsx3` because `pyttsx3` seems unmaintained, and I couldn't get the latest version of `pyttsx3` working.

`meloTTS` (local, fast)
- I recommend using `sherpa-onnx` to do MeloTTS inferencing. MeloTTS implementation here is **very difficult** to install.
- Install MeloTTS according to their [documentation](https://github.com/myshell-ai/MeloTTS/blob/main/docs/install.md) (don't install via docker) (A nice place to clone the repo is the submodule folder, but you can put it wherever you want). If you encounter a problem related to `mecab-python`, try this [fork](https://github.com/polm/MeloTTS) (hasn't been merging into the main as of July 16, 2024).
- It's not the best, but it's definitely better than pyttsx3TTS, and it's pretty fast on my mac. I would choose this for now if I can't access the internet (and I would use edgeTTS if I have the internet).

`coquiTTS` (local, can be fast or slow depending on the model you run)

- Seems easy to install
- Install with the command `pip install "coqui-tts[languages]" `
- Support many different TTS models. List all supported models with `tts --list_models` command.
- The default model is an english only model.
- Use `tts_models/zh-CN/baker/tacotron2-DDC-GST` for Chinese model. (but the consistency is weird...)
- If you found some good model to use, let me know! There are too many models I don't even know where to start...

`GPT_Sovits` (local, medium fast) (added in `v0.4.0` in https://github.com/t41372/Open-LLM-VTuber/pull/40)
- Please checkout [this doc](https://docs.qq.com/doc/DTHR6WkZ3aU9JcXpy) for installation instructions. 

`barkTTS` (local, slow)

- Install the pip package with this command `pip install git+https://github.com/suno-ai/bark.git` and turn it on in `conf.yaml`.
- The required models will be downloaded on the first launch.

`cosyvoiceTTS` (local, slow)
- Configure [CosyVoice](https://github.com/FunAudioLLM/CosyVoice) and launch the WebUI demo according to their documentation. 
- Edit `conf.yaml` to match your desired configurations. Check their WebUI and the API documentation on the WebUI to see the meaning of the configurations under the setting `cosyvoiceTTS` in the `conf.yaml`.

`xTTSv2` (local, slow) (added in `v0.2.4` in https://github.com/t41372/Open-LLM-VTuber/pull/23)
- Recommend to use xtts-api-server, it has clear api docs and relative easy to deploy.

`edgeTTS` (online, no API key required)
- Install the pip package with this command `pip install edge-tts` and turn it on in `conf.yaml`.
- It sounds pretty good. Runs pretty fast.
- Remember to connect to the internet when using edge tts.

`fishAPITTS` (online, API key required) `(added in v0.3.0-beta)`

- Install with `pip install fish-audio-sdk`
- Register an account, get an API key, find a voice you want to use, and copy the reference id on [Fish Audio](https://fish.audio/).
- In `conf.yaml` file, set the `TTS_MODEL` to `fishAPITTS`, and  under the `fishAPITTS` setting, set the `api_key` and `reference_id`.

`AzureTTS` (online, API key required) (This is the exact same TTS used by neuro-sama)

- Install the Azure SDK with the command'pip install azure-cognitiveservices-speech`.
- Get an API key (for text to speech) from Azure.
- **⚠️ ‼️ The `api_key.py` was deprecated in `v0.2.5`. Please set api keys in `conf.yaml`.**
- The default setting in the `conf.yaml` is the voice used by neuro-sama.



If you're using macOS, you need to enable the microphone permission of your terminal emulator (you run this program inside your terminal, right? Enable the microphone permission for your terminal). If you fail to do so, the speech recognition will not be able to hear you because it does not have permission to use your microphone.


## VAD Tuning

For web interface, this project utilizes client-side Voice Activity Detection (VAD) using the [ricky0123/vad-web](https://github.com/ricky0123/vad) library for efficient speech detection.

**Web Interface Controls:**

The following settings are available in the web interface to fine-tune the VAD:

*   **Speech Prob. Threshold:** Controls the minimum speech probability for initial speech detection. Higher values require stronger speech input to trigger detection.
*   **Negative Speech Threshold:** The probability threshold below which a frame is considered to not contain speech (i.e., part of a silence).
*   **Redemption Frames:** Specifies how many consecutive frames of silence are required to end a speech segment. Higher values allow for more pause tolerance.

**Tuning Tips:**

Experiment with these parameters to find the optimal balance between sensitivity and accuracy for your environment and speaking style.

## Some other things

### Translation

Translation was implemented to let the program speak in a language different from the conversation language. For example, the LLM might be thinking in English, the subtitle is in English, and you are speaking English, but the voice of the LLM is in Japanese. This is achieved by translating the sentence before it's sent for audio generation.

[DeepLX](https://github.com/OwO-Network/DeepLX) is the only supported translation backend for now. You will need to deploy the deeplx service and set the configuration in `conf.yaml` to use it.

If you want to add more translation providers, they are in the `translate` directory, and the steps are very similar to adding new TTS or ASR providers.


### Enable Audio Translation

1. Set `TRANSLATE_AUDIO` in `conf.yaml` to True
2. Set `DEEPLX_TARGET_LANG` to your desired language. Make sure this language matches the language of the TTS speaker (for example, if the `DEEPLX_TARGET_LANG` is "JA", which is Japanese, the TTS should also be speaking Japanese.).




# Issues

`PortAudio` Missing
- Install `libportaudio2` to your computer via your package manager like apt



# Running in a Container [highly experimental]

:warning: This is highly experimental, but I think it works. Most of the time.

You can either build the image yourself or pull it from the docker hub. [![](https://img.shields.io/badge/t41372%2FOpen--LLM--VTuber-%25230db7ed.svg?logo=docker&logoColor=blue&labelColor=white&color=blue)](https://hub.docker.com/r/t41372/open-llm-vtuber)

- (but the image size is crazy large)
- The image on the docker hub might not updated as regularly as it can be. GitHub action can't build an image as big as this. I might look into other options.



Current issues:

- Large image size (~13GB) and will require more space because some models are optional and will be downloaded only when used.
- Nvidia GPU required (GPU passthrough limitation)
- [Nvidia Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) needs to be configured for GPU passthrough.
- Some models will have to be downloaded again if you stop the container. (will be fixed)
- Don't build the image on an Arm machine. One of the dependencies (grpc, to be exact) will fail for some reason https://github.com/grpc/grpc/issues/34998. 
- As mentioned before, you can't run it on a remote server unless the web page has https. That's because the web mic on the front end will only launch in a secure context (which means localhost or https environment only). 

Most of the ASR and TTS will be pre-installed. However, bark TTS and the original OpenAI Whisper (`Whisper`, not WhisperCPP) are NOT included in the default build process because they are huge (~8GB, which makes the whole container about 25GB). In addition, they don't deliver the best performance either. To include bark and/or whisper in the image, add the argument `--build-arg INSTALL_ORIGINAL_WHISPER=true --build-arg INSTALL_BARK=true` to the image build command.

Setup guide:

1. Review `conf.yaml` before building (currently burned into the image, I'm sorry):

2. Build the image:

 ```
 docker build -t open-llm-vtuber .
 ```

 (Grab a drink, this will take a while)

3. Grab a `conf.yaml` configuration file.
 Grab a `conf.yaml` file from this repo. Or you can get it directly from this [link](https://raw.githubusercontent.com/t41372/Open-LLM-VTuber/main/conf.yaml).

4. Run the container:

`$(pwd)/conf.yaml` should be the path of your `conf.yaml` file.

 ```
 docker run -it --net=host --rm -v $(pwd)/conf.yaml:/app/conf.yaml -p 12393:12393 open-llm-vtuber
 ```

5. Open localhost:12393 to test


# 🎉🎉🎉 Related Projects

[ylxmf2005/LLM-Live2D-Desktop-Assitant](https://github.com/ylxmf2005/LLM-Live2D-Desktop-Assitant)
- Your Live2D desktop assistant powered by LLM! Available for both Windows and MacOS, it senses your screen, retrieves clipboard content, and responds to voice commands with a unique voice. Featuring voice wake-up, singing capabilities, and full computer control for seamless interaction with your favorite character.



# 🛠️ Development
(this project is in the active prototyping stage, so many things will change)

Some abbreviations used in this project:

- LLM: Large Language Model
- TTS: Text-to-speech, Speech Synthesis, Voice Synthesis
- ASR: Automatic Speech Recognition, Speech recognition, Speech to text, STT
- VAD: Voice Activation Detection

### Regarding sample rates

You can assume that the sample rate is `16000` throughout this project.
The frontend stream chunks of `Float32Array` with a sample rate of `16000` to the backend.

### Add support for new TTS providers
1. Implement `TTSInterface` defined in `tts/tts_interface.py`.
1. Add your new TTS provider into `tts_factory`: the factory to instantiate and return the tts instance.
1. Add configuration to `conf.yaml`. The dict with the same name will be passed into the constructor of your TTSEngine as kwargs.

### Add support for new Speech Recognition provider
1. Implement `ASRInterface` defined in `asr/asr_interface.py`.
2. Add your new ASR provider into `asr_factory`: the factory to instantiate and return the ASR instance.
3. Add configuration to `conf.yaml`. The dict with the same name will be passed into the constructor of your class as kwargs.

### Add support for new LLM provider
1. Implement `LLMInterface` defined in `llm/llm_interface.py`.
2. Add your new LLM provider into `llm_factory`: the factory to instantiate and return the LLM instance.
3. Add configuration to `conf.yaml`. The dict with the same name will be passed into the constructor of your class as kwargs.

### Add support for new Translation providers
1. Implement `TranslateInterface` defined in `translate/translate_interface.py`.
1. Add your new TTS provider into `translate_factory`: the factory to instantiate and return the tts instance.
1. Add configuration to `conf.yaml`. The dict with the same name will be passed into the constructor of your translator as kwargs.


# Acknowledgement
Awesome projects I learned from

- https://github.com/dnhkng/GlaDOS
- https://github.com/SchwabischesBauernbrot/unsuperior-ai-waifu
- https://codepen.io/guansss/pen/oNzoNoz
- https://github.com/Ikaros-521/AI-Vtuber
- https://github.com/zixiiu/Digital_Life_Server



## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=t41372/open-llm-vtuber&type=Date)](https://star-history.com/#t41372/open-llm-vtuber&Date)





