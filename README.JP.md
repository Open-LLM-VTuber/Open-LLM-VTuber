![](./assets/banner.jpg)

<h1 align="center">Open-LLM-VTuber</h1>
<h3 align="center">

[![GitHub release](https://img.shields.io/github/v/release/Open-LLM-VTuber/Open-LLM-VTuber)](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/releases) 
[![license](https://img.shields.io/github/license/Open-LLM-VTuber/Open-LLM-VTuber)](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/blob/master/LICENSE) 
[![CodeQL](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/actions/workflows/codeql.yml/badge.svg)](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/actions/workflows/codeql.yml)
[![Ruff](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/actions/workflows/ruff.yml/badge.svg)](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/actions/workflows/ruff.yml)
[![Docker](https://img.shields.io/badge/Open-LLM-VTuber%2FOpen--LLM--VTuber-%25230db7ed.svg?logo=docker&logoColor=blue&labelColor=white&color=blue)](https://hub.docker.com/r/Open-LLM-VTuber/open-llm-vtuber) 
[![QQ User Group](https://img.shields.io/badge/QQ_User_Group-792615362-white?style=flat&logo=qq&logoColor=white)](https://qm.qq.com/q/ngvNUQpuKI)
[![Static Badge](https://img.shields.io/badge/Join%20Chat-Zulip?style=flat&logo=zulip&label=Zulip(dev-community)&color=blue&link=https%3A%2F%2Folv.zulipchat.com)](https://olv.zulipchat.com)

> **📢 v2.0 開発中**: 現在、Open-LLM-VTuber v2.0の開発に注力しています — これはコードベースの完全な書き直しです。v2.0は現在、初期の議論と計画段階にあります。v1への機能リクエストに関する新しいissueやpull requestの提出はお控えください。v2の議論に参加したい、または貢献したい場合は、[Zulip](https://olv.zulipchat.com)の開発者コミュニティにご参加ください。週次ミーティングのスケジュールはZulipで発表されます。v1のバグ修正と既存のpull requestの対応は継続します。


[![BuyMeACoffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/yi.ting)
[![](https://dcbadge.limes.pink/api/server/3UDA8YFDXx)](https://discord.gg/3UDA8YFDXx)

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Open-LLM-VTuber/Open-LLM-VTuber)

[English README](./README.md) | [中文 README](./README.CN.md) | [한국어 README](./README.KR.md) | 日本語 README

[ドキュメント](https://open-llm-vtuber.github.io/docs/quick-start) | [![Roadmap](https://img.shields.io/badge/Roadmap-GitHub_Project-yellow)](https://github.com/orgs/Open-LLM-VTuber/projects/2)

<a href="https://trendshift.io/repositories/12358" target="_blank"><img src="https://trendshift.io/api/badge/repositories/12358" alt="Open-LLM-VTuber%2FOpen-LLM-VTuber | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

</h3>


> よくある質問 (中国語で作成): https://docs.qq.com/pdf/DTFZGQXdTUXhIYWRq
>
> ユーザーアンケート: https://forms.gle/w6Y6PiHTZr1nzbtWA
>
> アンケート(中国語): https://wj.qq.com/s2/16150415/f50a/

> :warning: このプロジェクトはまだ初期段階にあり、現在 **活発に開発中** です。

> :warning: サーバーをリモートで実行し、他のデバイス（例：PCでサーバーを実行し、スマホからアクセス）を通じてアクセスするには、`https` 設定が必要です。これはフロントエンドのマイク機能がセキュアな環境（https または localhost）でのみ動作するためです。詳細はこちら-\> [MDN Web Doc](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)。したがって、リモートデバイス（つまりlocalhost以外の環境）からページにアクセスするには、リバースプロキシを使用してhttpsを設定する必要があります。

## ⭐️ このプロジェクトは何ですか？

**Open-LLM-VTuber** は、**リアルタイム音声会話** と **視覚認識** をサポートするだけでなく、生き生きとした **Live2Dアバター** を備えた **音声対話型AIコンパニオン** です。すべての機能はコンピュータ上で完全にオフラインで実行できます！

個人的なAIコンパニオンとして活用できます — `virtual girlfriend`、`boyfriend`、`cute pet` など、期待に合わせてどのようなキャラクターにもなれます。このプロジェクトは `Windows`、`macOS`、`Linux` を完全にサポートしており、**Webバージョン** と **デスクトップクライアント** の2つの使用モードを提供します。特に **透明背景のデスクトップマスコットモード** をサポートしており、AIコンパニオンが画面上のどこにでも一緒にいることができます。

長期記憶機能は一時的に削除されましたが（まもなく再提供予定）、チャットログの **永続保存** のおかげで、以前に終わらなかった会話を **中断することなく続けることができ**、貴重なインタラクションの瞬間を失うことはありません。

バックエンドサポートの面では、様々なLLM推論、テキスト読み上げ（TTS）、音声認識ソリューションを統合しました。AIコンパニオンをカスタマイズしたい場合は、[Character Customization Guide](https://open-llm-vtuber.github.io/docs/user-guide/live2d)を参照して、AIコンパニオンの外見や性格をカスタマイズできます。

このプロジェクトが `Open-LLM-Companion` や `Open-LLM-Waifu` ではなく `Open-LLM-Vtuber` という名前である理由は、初期の開発目標が **Windows以外のプラットフォームでもオフラインで実行可能なオープンソースソリューションを活用** し、**クローズドなAI Vtuberである `neuro-sama` を再現** することだったためです。

### 👀 効果実証
| ![](assets/i1.jpg) | ![](assets/i2.jpg) |
|:---:|:---:|
| ![](assets/i3.jpg) | ![](assets/i4.jpg) |


## ✨ 機能 & 主な特徴

  - 🖥️ **クロスプラットフォーム対応**: `macOS`、`Linux`、`Windows` と完全に互換性があります。NVIDIA GPUおよび非NVIDIA GPUの両方をサポートし、CPU実行やクラウドAPIを活用した高負荷作業の実行オプションも提供します。一部のコンポーネントはmacOSでのGPUアクセラレーションをサポートしています。

  - 🔒 **オフラインモード対応**: ローカルモデルを使用して完全にオフラインで実行でき、インターネット接続は必要ありません。会話内容はユーザーのデバイスにのみ保存され、プライバシーとセキュリティが保護されます。

  - 💻 **魅力的で強力なWebおよびデスクトップクライアント**: Webバージョンとデスクトップクライアントの2つの使用モードを提供し、豊富なインタラクション機能とパーソナライズ設定をサポートします。デスクトップクライアントはウィンドウモードとデスクトップマスコットモードを自由に切り替えることができ、AIコンパニオンが常にそばにいることができます。

  - 🎯 **高度なインタラクション機能**:

      - 👁️ 視覚認識: カメラ、画面録画、スクリーンショットをサポートし、AIコンパニオンがユーザーの姿や画面を見ることができます。
      - 🎤 ヘッドフォンなしでの音声認識: AIが自分の声を聞かずに、音声を処理できます。
      - 🫱 タッチフィードバック: クリックやドラッグでAIコンパニオンと対話できます。
      - 😊 Live2D 表情: バックエンドで感情マッピングを設定し、モデルの表情を制御できます。
      - 🐱 ペットモード: 透明背景、常に手前に表示、マウスクリック透過をサポートし、AIコンパニオンを画面のどこへでも自由に移動できます。
      - 💭 AIの内面表現: AIが話さなくても、AIの表情、思考、行動を確認できます。
      - 🗣️ AI能動発話機能: ユーザーが話さなくてもAIが先に話しかける機能。
      - 💾 チャットログの永続保存: いつでも以前の会話に切り替えることができます。
      - 🌍 TTS翻訳サポート: 例：AIは日本語の音声で話しながら、中国語でチャットすることができます。

  - 🧠 **広範なモデルサポート**:

      - 🤖 Large Language Models (LLM): Ollama, OpenAI (およびOpenAI互換API), Gemini, Claude, Mistral, DeepSeek, Zhipu AI, GGUF, LM Studio, vLLM, etc.
      - 🎙️ Automatic Speech Recognition (ASR): sherpa-onnx, FunASR, Faster-Whisper, Whisper.cpp, Whisper, Groq Whisper, Azure ASR, etc.
      - 🔊 Text-to-Speech (TTS): sherpa-onnx, pyttsx3, MeloTTS, Coqui-TTS, GPTSoVITS, Bark, CosyVoice, Edge TTS, Fish Audio, Azure TTS, etc.

  - 🔧 **高いカスタマイズの自由度**:

      - ⚙️ **簡単なモジュール構成**: 簡単な設定ファイルの修正だけで様々な機能モジュールを切り替えることができ、コードの修正は必要ありません。
      - 🎨 **キャラクターカスタマイズ**: カスタムLive2Dモデルを取り込み、AIコンパニオンに固有の外見を与えることができます。Promptを修正してAIコンパニオンの性格を設定し、**ボイスクローニング** を通じて希望の声を与えることができます。
      - 🧩 **柔軟なAgent実装**: Agentインターフェースを継承・実装し、HumeAI EVI、OpenAI Her、Mem0など、様々なAgentアーキテクチャを統合できます。
      - 🔌 優れた拡張性: モジュール式設計により、独自のLLM、ASR、TTSなどのモジュールを簡単に追加でき、いつでも新しい機能を拡張できます。

## 👥 ユーザーレビュー

> 開発者の方に感謝します。すべての人が使用できるようにパートナーをオープンソースで共有していただきありがとうございます。
>
> このパートナーは10万回以上使用されました。

## 🚀 クイックスタート

インストールについては、ドキュメントの [Quick Start](https://open-llm-vtuber.github.io/docs/quick-start) セクションを参照してください。



## ☝ アップデート

> :warning: `v1.0.0` バージョンには **互換性のない変更** があり、再デプロイが必要です。以下の方法でアップデート **することは可能ですが**、`conf.yaml` ファイルに互換性がなく、ほとんどの依存関係を `uv` で再インストールする必要があります。`v1.0.0` 以前のバージョンからアップグレードする場合は、[最新のデプロイガイド](https://open-llm-vtuber.github.io/docs/quick-start)を参照してプロジェクトを再デプロイすることを推奨します。

`v1.0.0` 以降のバージョンをインストールしている場合、アップデートは `uv run update.py` を使用してください。

## 😢 アンインストール (Uninstall)

ほとんどのファイルは、Pythonの依存関係とモデルを含め、プロジェクトフォルダに保存されます。

ただし、ModelScopeやHugging Faceを通じてダウンロードしたモデルは `MODELSCOPE_CACHE` または `HF_HOME` に保存されている可能性があります。プロジェクトの `models` ディレクトリに保管することが目標ですが、一度確認してみることをお勧めします。

また、インストールガイドを参照して、不要になった追加ツール（`uv`、`ffmpeg`、`deeplx` など）がないか確認してください。

## 🤗 貢献したいですか？

[Development Guide](https://docs.llmvtuber.com/docs/development-guide/overview)を参照してください。

# 🎉🎉🎉 関連プロジェクト

[ylxmf2005/LLM-Live2D-Desktop-Assitant](https://github.com/ylxmf2005/LLM-Live2D-Desktop-Assitant)

  - LLMで駆動する **Live2D デスクトップアシスタント** です！ WindowsとMacOSの両方で使用可能で、画面を検出し、クリップボードの内容を取得し、固有の声で音声コマンドに反応します。**ウェイクワード、歌唱機能**、コンピュータ全体の制御をサポートし、好きなキャラクターとスムーズに対話できます。





## 📜 サードパーティライセンス (Third-Party Licenses)

### Live2D サンプルモデルに関する通知 (Live2D Sample Models Notice)

このプロジェクトには、**Live2D Inc.から提供されたLive2Dサンプルモデル** が含まれています。当該資産は **Live2D Free Material License Agreement** および **Live2D Cubism Sample Data 利用規約** に基づき別途ライセンスが付与されており、このプロジェクトのMITライセンスには含まれません。

このコンテンツはLive2D Inc.が所有し著作権を持つサンプルデータを使用しており、Live2D Inc.が定めた **規約と条件** に従って活用されます。（詳細は [Live2D Free Material License Agreement](https://www.live2d.jp/en/terms/live2d-free-material-license-agreement/) および [Terms of Use](https://www.live2d.com/eula/live2d-sample-model-terms_en.html) を参照）

注：特に中堅・大規模企業での **商用利用** の際、このLive2Dサンプルモデルの使用には追加のライセンス要件が適用される場合があります。プロジェクトを商用利用する計画がある場合は、必ずLive2D Inc.から適切な許可を得るか、当該モデルが含まれていないバージョンを使用してください。

## コントリビューター

このプロジェクトを可能にしてくださった **コントリビューターとメンテナの方々に感謝いたします。**

<a href="https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/graphs/contributors">
<img src="https://contrib.rocks/image?repo=Open-LLM-VTuber/Open-LLM-VTuber" />
</a>

## スター履歴 (Star History)

[![Star History Chart](https://api.star-history.com/svg?repos=Open-LLM-VTuber/open-llm-vtuber&type=Date)](https://star-history.com/#Open-LLM-VTuber/open-llm-vtuber&Date)
