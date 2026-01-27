![](./assets/banner.kr.jpg)

<h1 align="center">Open-LLM-VTuber</h1>
<h3 align="center">

[![GitHub release](https://img.shields.io/github/v/release/Open-LLM-VTuber/Open-LLM-VTuber)](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/releases) 
[![license](https://img.shields.io/github/license/Open-LLM-VTuber/Open-LLM-VTuber)](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/blob/master/LICENSE) 
[![CodeQL](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/actions/workflows/codeql.yml/badge.svg)](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/actions/workflows/codeql.yml)
[![Ruff](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/actions/workflows/ruff.yml/badge.svg)](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/actions/workflows/ruff.yml)
[![Docker](https://img.shields.io/badge/Open-LLM-VTuber%2FOpen--LLM--VTuber-%25230db7ed.svg?logo=docker&logoColor=blue&labelColor=white&color=blue)](https://hub.docker.com/r/Open-LLM-VTuber/open-llm-vtuber) 
[![QQ User Group](https://img.shields.io/badge/QQ_User_Group-792615362-white?style=flat&logo=qq&logoColor=white)](https://qm.qq.com/q/ngvNUQpuKI)
[![Static Badge](https://img.shields.io/badge/Join%20Chat-Zulip?style=flat&logo=zulip&label=Zulip(dev-community)&color=blue&link=https%3A%2F%2Folv.zulipchat.com)](https://olv.zulipchat.com)

> **📢 v2.0 개발 중**: 현재 Open-LLM-VTuber v2.0 개발에 집중하고 있습니다 — 이는 코드베이스의 전면 재작성입니다. v2.0은 현재 초기 논의 및 기획 단계에 있습니다. v1에 대한 기능 요청 관련 새로운 issue나 pull request 제출은 자제해 주세요. v2 논의에 참여하거나 기여하고 싶으시다면, [Zulip](https://olv.zulipchat.com) 개발자 커뮤니티에 참여해 주세요. 주간 미팅 일정은 Zulip에서 공지됩니다. v1의 버그 수정과 기존 pull request 처리는 계속됩니다.


[![BuyMeACoffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/yi.ting)
[![](https://dcbadge.limes.pink/api/server/3UDA8YFDXx)](https://discord.gg/3UDA8YFDXx)

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Open-LLM-VTuber/Open-LLM-VTuber)

[ENGLISH README](./README.md) | [中文 README](./README.CN.md) | 한국어 README | [日本語 README](./README.JP.md)

[문서](https://open-llm-vtuber.github.io/docs/quick-start) | [![Roadmap](https://img.shields.io/badge/Roadmap-GitHub_Project-yellow)](https://github.com/orgs/Open-LLM-VTuber/projects/2)

<a href="https://trendshift.io/repositories/12358" target="_blank"><img src="https://trendshift.io/api/badge/repositories/12358" alt="Open-LLM-VTuber%2FOpen-LLM-VTuber | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

</h3>


> 자주 발생하는 문제 문서 (중국어로 작성됨): https://docs.qq.com/pdf/DTFZGQXdTUXhIYWRq
>
> 사용자 설문조사: https://forms.gle/w6Y6PiHTZr1nzbtWA
>
> 调查问卷(中文): https://wj.qq.com/s2/16150415/f50a/



> :warning: 이 프로젝트는 아직 초기 단계에 있으며, 현재 **활발히 개발 중**입니다.

> :warning: 서버를 원격으로 실행하고 다른 기기(예: 컴퓨터에서 서버를 실행하고 휴대폰에서 접속)를 통해 접근하려면 `https` 설정이 필요합니다. 이는 프론트엔드의 마이크 기능이 보안된 환경(https 또는 localhost) 에서만 동작하기 때문입니다. 자세한 내용-> [MDN Web Doc](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).따라서 원격 기기(즉, localhost가 아닌 환경)에서 페이지에 접근하려면 리버스 프록시를 사용해 https를 설정해야 합니다.


## ⭐️ 이 프로젝트는 무엇인가요?


**Open-LLM-VTuber**는 **실시간 음성 대화**와 **시각적 인식**을 지원할 뿐만 아니라, 생동감 있는 **Live2D 아바타**를 갖춘 **음성 상호작용 AI 동반자**입니다. 모든 기능은 컴퓨터에서 완전히 오프라인으로 실행할 수 있습니다!

개인적인 AI 동반자로 활용할 수 있습니다 — `virtual girlfriend`, `boyfriend`, `cute pet` 등 원하는 어떤 캐릭터든 기대에 맞출 수 있습니다. 이 프로젝트는 `Windows`, `macOS`, `Linux`를 완전히 지원하며, **웹 버전**과 **데스크톱 클라이언트**의 두 가지 사용 모드를 제공합니다. 특히 **투명 배경 데스크톱 펫 모드**를 지원하여, AI 동반자가 화면 어디에서든 함께할 수 있습니다.

장기 메모리 기능은 일시적으로 제거되었지만(곧 다시 제공될 예정), 채팅 로그의 **지속 저장** 덕분에 이전에 끝내지 못한 대화를 **중단 없이 이어갈 수 있으며**, 소중한 상호작용 순간을 잃지 않을 수 있습니다.

백엔드 지원 측면에서, 다양한 LLM 추론, 텍스트-투-스피치, 음성 인식 솔루션을 통합했습니다. AI 동반자를 맞춤 설정하고 싶다면, [Character Customization Guide](https://open-llm-vtuber.github.io/docs/user-guide/live2d)를 참고하여 AI 동반자의 외형과 성격을 커스터마이즈할 수 있습니다.

이 프로젝트가 `Open-LLM-Companion`이나 `Open-LLM-Waifu`가 아닌 `Open-LLM-Vtuber`라는 이름을 가진 이유는, 초기 개발 목표가 **Windows 외 플랫폼에서도 오프라인으로 실행 가능한 오픈소스 솔루션을 활용**하여 **폐쇄형 AI Vtuber인 `neuro-sama`를 재현**하는 것이었기 때문입니다.

### 👀 데모
| ![](assets/i1.jpg) | ![](assets/i2.jpg) |
|:---:|:---:|
| ![](assets/i3.jpg) | ![](assets/i4.jpg) |


## ✨ 기능 & 주요 특징

- 🖥️ **크로스 플랫폼 지원**: `macOS`, `Linux`, `Windows`와 완벽하게 호환됩니다. NVIDIA GPU와 비-NVIDIA GPU 모두 지원하며, CPU 실행이나 클라우드 API를 활용한 고사양 작업 수행 옵션도 제공합니다. 일부 구성 요소는 macOS에서 GPU 가속을 지원합니다.

- 🔒 **오프라인 모드 지원**: 로컬 모델을 사용하여 완전히 오프라인에서 실행할 수 있으며, 인터넷 연결이 필요하지 않습니다. 대화 내용은 사용자의 기기에만 저장되어 개인 정보와 보안이 보호됩니다.

- 💻 **매력적이고 강력한 웹 및 데스크톱 클라이언트**: 웹 버전과 데스크톱 클라이언트 두 가지 사용 모드를 제공하며, 풍부한 상호작용 기능과 개인화 설정을 지원합니다. 데스크톱 클라이언트는 창 모드와 데스크톱 펫 모드를 자유롭게 전환할 수 있어, AI 동반자가 항상 곁에 함께할 수 있습니다.

- 🎯 **고급 상호작용 기능**:
  - 👁️ 시각 인식 : 카메라, 화면 녹화, 스크린샷을 지원하여 AI 동반자가 사용자의 모습과 화면을 볼 수 있습니다.
  - 🎤 헤드폰 없이도 음성 인식 가능: AI가 자신의 목소리를 듣지 않고, 음성을 처리할 수 있습니다.
  - 🫱 터치 피드백: 클릭이나 드래그로 AI 동반자와 상호작용할 수 있습니다.
  - 😊 Live2D 표정: 백엔드에서 감정 매핑을 설정하여 모델의 표정을 제어할 수 있습니다.
  - 🐱 펫 모드: 투명 배경, 항상 위, 마우스 클릭 통과를 지원하며, AI 동반자를 화면 어디로든 자유롭게 이동할 수 있습니다.
  - 💭 AI의 내면 표현: AI가 말하지 않아도 AI의 표정, 생각, 행동을 확인할 수 있습니다.
  - 🗣️ AI 능동 발화 기능 (사용자가 말하지 않아도 AI 가 먼저 발화)
  - 💾 채팅 로그 지속 저장: 언제든 이전 대화로 전환할 수 있습니다.
  - 🌍 TTS 번역 지원: (예 AI는 일본어 음성으로 말하면서 중국어로 채팅할 수 있습니다.)

- 🧠 **광범위한 모델 지원**:
  - 🤖 Large Language Models (LLM): Ollama, OpenAI (and any OpenAI-compatible API), Gemini, Claude, Mistral, DeepSeek, Zhipu AI, GGUF, LM Studio, vLLM, etc.
  - 🎙️ Automatic Speech Recognition (ASR): sherpa-onnx, FunASR, Faster-Whisper, Whisper.cpp, Whisper, Groq Whisper, Azure ASR, etc.
  - 🔊 Text-to-Speech (TTS): sherpa-onnx, pyttsx3, MeloTTS, Coqui-TTS, GPTSoVITS, Bark, CosyVoice, Edge TTS, Fish Audio, Azure TTS, etc.

- 🔧 **높은 커스터마이징 자유도**:
  - ⚙️ **간단한 모듈 구성**: 간단한 설정 파일 수정만으로 다양한 기능 모듈을 전환할 수 있으며, 코드 수정은 필요하지 않습니다.
  - 🎨 ***캐릭터 커스터마이징**: 커스텀 Live2D 모델을 가져와 AI 동반자에게 고유한 외형을 부여할 수 있습니다. Prompt를 수정하여 AI 동반자의 성격을 설정하고, **음성 클로닝**을 통해 원하는 목소리를 입힐 수 있습니다.
  - 🧩 **유연한 Agent 구현**: Agent 인터페이스를 상속하고 구현하여 HumeAI EVI, OpenAI Her, Mem0 등 다양한 Agent 아키텍처를 통합할 수 있습니다.
  - 🔌 우수한 확장성: 모듈식 설계를 통해 자신만의 LLM, ASR, TTS 등 모듈을 쉽게 추가할 수 있으며, 언제든 새로운 기능을 확장할 수 있습니다.


## 👥 사용자 리뷰
> 개발자분께 감사드리며, 모든 사람이 사용할 수 있도록 파트너를 오픈소스로 공유해주셔서 감사합니다.
> 
> 이 파트너는 10만 회 이상 사용되었습니다.


## 🚀 빠른 시작

설치는 문서의 [Quick Start](https://open-llm-vtuber.github.io/docs/quick-start) 섹션을 참고하세요.




## ☝ 업데이트
> :warning: `v1.0.0` 버전은 **호환되지 않는 변경 사항**이 있어 재배포가 필요합니다. 아래 방법으로 업데이트**할 수는** 있으나, `conf.yaml` 파일이 호환되지 않으며 대부분의 의존성을 `uv`로 다시 설치해야 합니다. `v1.0.0` 이전 버전에서 업그레이드하는 경우, [최신 배포 가이드](https://open-llm-vtuber.github.io/docs/quick-start)를 참고하여 프로젝트를 다시 배포하는 것을 권장합니다.

`v1.0.0` 이후 버전을 설치한 경우, 업데이트는 `uv run update.py`를 사용하세요.

## 😢 삭제 (Uninstall)
대부분의 파일은 Python 의존성과 모델을 포함하여 프로젝트 폴더에 저장됩니다.

다만, ModelScope나 Hugging Face를 통해 다운로드한 모델은 `MODELSCOPE_CACHE` 또는 `HF_HOME`에 저장될 수도 있습니다. 프로젝트의 `models` 디렉토리에 보관하는 것이 목표이지만, 한 번 확인해보는 것이 좋습니다.

또한 설치 가이드를 참고하여 더 이상 필요 없는 추가 도구(`uv`, `ffmpeg`, `deeplx` 등)가 있는지 점검하세요.


## 🤗 기여하고 싶으시다면?
[Development Guide](https://docs.llmvtuber.com/docs/development-guide/overview)를 참고하세요.


# 🎉🎉🎉 관련된 프로젝트

[ylxmf2005/LLM-Live2D-Desktop-Assitant](https://github.com/ylxmf2005/LLM-Live2D-Desktop-Assitant)
- LLM으로 구동되는 **Live2D 데스크톱 어시스턴트**입니다! Windows와 MacOS에서 모두 사용 가능하며, 화면을 감지하고 클립보드 내용을 가져오며, 고유한 음성으로 음성 명령에 반응합니다. **음성 깨우기, 노래 기능**, 전체 컴퓨터 제어를 지원하여 좋아하는 캐릭터와 매끄럽게 상호작용할 수 있습니다.







## 📜 써드 파티 라이센스들 (Third-Party Licenses)

### Live2D 샘플 모델 고지 (Live2D Sample Models Notice)

이 프로젝트에는 **Live2D Inc.에서 제공한 Live2D 샘플 모델**이 포함되어 있습니다. 해당 자산은 **Live2D Free Material License Agreement** 및 **Live2D Cubism Sample Data 이용 약관**에 따라 별도로 라이선스가 부여되며, 이 프로젝트의 MIT 라이선스에는 포함되지 않습니다.

이 콘텐츠는 Live2D Inc.가 소유하고 저작권을 가진 샘플 데이터를 사용하며, Live2D Inc.에서 정한 **약관과 조건**에 따라 활용됩니다. (자세한 내용은 [Live2D Free Material License Agreement](https://www.live2d.jp/en/terms/live2d-free-material-license-agreement/) 및 [Terms of Use](https://www.live2d.com/eula/live2d-sample-model-terms_en.html) 참고)

참고: 특히 중견·대규모 기업에서 **상업적 사용** 시, 이 Live2D 샘플 모델의 사용은 추가 라이선스 요구 사항이 적용될 수 있습니다. 프로젝트를 상업적으로 활용할 계획이라면, 반드시 Live2D Inc.로부터 적절한 허가를 받거나, 해당 모델이 포함되지 않은 버전을 사용하시기 바랍니다.



## 기여자분들
이 프로젝트가 가능하도록 해주신 **기여자와 유지보수자분들께 감사드립니다.**

<a href="https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Open-LLM-VTuber/Open-LLM-VTuber" />
</a>


## 스타 기록 (Star History)

[![Star History Chart](https://api.star-history.com/svg?repos=Open-LLM-VTuber/open-llm-vtuber&type=Date)](https://star-history.com/#Open-LLM-VTuber/open-llm-vtuber&Date)






