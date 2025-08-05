# Open-LLM-VTuber プロジェクト仕様書

## プロジェクト概要

Open-LLM-VTuberは、リアルタイム音声対話と視覚認識機能を備えたAI VTuberシステムです。Live2Dアバターを通じてユーザーと対話し、完全オフラインでの動作も可能な、プライバシーを重視した設計となっています。

### 主な特徴
- クロスプラットフォーム対応（Windows、macOS、Linux）
- 完全オフライン動作可能
- Live2Dアバターによる感情表現
- リアルタイム音声認識・合成
- 視覚認識機能（カメラ、スクリーンショット対応）
- MCP（Model Context Protocol）によるツール統合

## システムアーキテクチャ

### 技術スタック

#### バックエンド
- **言語**: Python 3.10-3.12
- **フレームワーク**: FastAPI (WebSocketサポート)
- **非同期処理**: asyncio
- **パッケージ管理**: uv, pixi (conda環境)

#### フロントエンド
- **フレームワーク**: 不明（ビルド済みアセットのみ）
- **Live2D**: Live2D Cubism SDK
- **通信**: WebSocket

#### 主要な依存関係
- anthropic: Claude AI統合
- openai: OpenAI API互換インターフェース
- torch: 機械学習モデル実行
- onnxruntime: ONNX モデル推論
- sherpa-onnx: 音声認識・合成
- mcp: Model Context Protocol統合

### プロジェクト構造

```
Open-LLM-VTuber/
├── src/open_llm_vtuber/       # メインソースコード
│   ├── agent/                 # AI エージェントシステム
│   ├── asr/                   # 音声認識モジュール
│   ├── tts/                   # 音声合成モジュール
│   ├── vad/                   # 音声アクティビティ検出
│   ├── mcpp/                  # MCP統合
│   ├── translate/             # 翻訳サービス
│   ├── conversations/         # 会話管理
│   ├── config_manager/        # 設定管理
│   └── live/                  # ライブ配信統合
├── frontend/                  # フロントエンドアセット
├── live2d-models/            # Live2Dモデルファイル
├── characters/               # キャラクター設定
├── prompts/                  # プロンプトテンプレート
├── models/                   # AIモデルファイル
└── conf.yaml                 # メイン設定ファイル
```

## コンポーネント詳細

### 1. エージェントシステム (`agent/`)

AI VTuberの中核となる会話エンジンです。

#### 主要コンポーネント
- **AgentInterface**: エージェントの基本インターフェース
- **BasicMemoryAgent**: 標準的な会話エージェント実装
- **HumeAIAgent**: Hume AI感情認識統合
- **LettaAgent**: Letta（旧MemGPT）メモリ管理
- **Mem0LLM**: 長期記憶機能

#### LLMプロバイダー対応
- OpenAI互換API（OpenAI、Gemini、Zhipu、DeepSeek、Groq、Mistral等）
- Anthropic Claude
- Ollama（ローカルモデル）
- llama.cpp
- カスタムテンプレート対応

### 2. 音声認識システム (`asr/`)

音声入力をテキストに変換します。

#### 対応エンジン
- **Faster Whisper**: 最適化されたWhisper実装
- **Whisper.cpp**: C++実装版
- **OpenAI Whisper**: 公式実装
- **FunASR**: Alibabaの音声認識
- **Azure ASR**: Microsoft Azure Cognitive Services
- **Groq Whisper**: 高速化Whisper
- **Sherpa ONNX**: ONNXベース音声認識

#### 共通インターフェース
- 入力: 16kHz、モノラル、16bit PCM音声
- 出力: 認識されたテキスト
- 非同期処理対応

### 3. 音声合成システム (`tts/`)

テキストを音声に変換します。

#### 対応エンジン
- **Azure TTS**: Microsoft Azure
- **Edge TTS**: Microsoft Edge
- **OpenAI TTS**: OpenAI音声合成
- **Bark TTS**: オープンソース神経TTS
- **MeloTTS**: 多言語TTS
- **CosyVoice/CosyVoice2**: 高度な音声クローニング
- **GPT-SoVITS**: 高品質音声合成
- **Coqui TTS**: オープンソースTTSツールキット
- その他多数

### 4. 音声アクティビティ検出 (`vad/`)

音声の開始・終了を検出します。

- **Silero VAD**: 最先端の音声アクティビティ検出
- リアルタイム処理対応
- 設定可能な感度とタイミング

### 5. MCP統合 (`mcpp/`)

Model Context Protocolによる外部ツール統合を提供します。

#### コンポーネント
- **MCPClient**: MCPサーバーへの接続管理
- **ToolManager**: ツール情報の管理
- **ToolExecutor**: ツール実行
- **ToolAdapter**: 動的ツール検出

#### 対応形式
- OpenAI関数呼び出し形式
- Claude ツール使用形式

### 6. 会話管理システム (`conversations/`)

会話フローとセッション管理を担当します。

- 個別会話とグループ会話対応
- 割り込み処理
- 履歴管理
- TTS出力管理

### 7. 設定管理 (`config_manager/`)

YAMLベースの階層的設定管理システムです。

- キャラクター設定
- システム設定
- エージェント設定
- ASR/TTS設定
- 国際化対応

## API エンドポイント

### WebSocket エンドポイント

#### `/client-ws`
メインのクライアント接続用WebSocketエンドポイント

**メッセージタイプ**:
- `mic-audio-data`: 音声データストリーミング
- `mic-audio-end`: 音声入力終了
- `text-input`: テキスト入力
- `interrupt-signal`: 割り込み信号
- `fetch-configs`: 設定一覧取得
- `switch-config`: 設定切り替え
- `create-new-history`: 新規履歴作成
- `fetch-history-list`: 履歴一覧取得

#### `/tts-ws`
TTS生成専用WebSocketエンドポイント

#### `/proxy-ws`
プロキシ接続用エンドポイント

### HTTP エンドポイント

#### `GET /live2d-models/info`
利用可能なLive2Dモデル情報を取得

#### `POST /asr`
音声ファイルのテキスト変換

#### `GET /web-tool`
Webツールへのリダイレクト

## データフロー

### 音声会話フロー
1. クライアント → WebSocket → VAD → 音声アクティビティ検出
2. 音声データ → ASR → テキスト変換
3. テキスト → Agent → 応答生成
4. 応答テキスト → TTS → 音声生成
5. 音声データ → WebSocket → クライアント再生

### Live2D制御フロー
1. Agent → 感情キーワード検出
2. キーワード → Live2D表情マッピング
3. 表情データ → WebSocket → クライアント表示

## 設定ファイル構造

### `conf.yaml`
```yaml
system_config:
  host: 'localhost'
  port: 12393
  config_alts_dir: 'characters'
  tool_prompts:
    live2d_expression_prompt: 'live2d_expression_prompt'
    group_conversation_prompt: 'group_conversation_prompt'
    mcp_prompt: 'mcp_prompt'

character_config:
  conf_name: 'mao_pro'
  live2d_model_name: 'mao_pro'
  character_name: 'Mao'
  persona_prompt: |
    キャラクターの性格設定

  agent_config:
    conversation_agent_choice: 'basic_memory_agent'
    agent_settings:
      # エージェント固有の設定
    llm_configs:
      # LLMプロバイダー設定

  asr_config:
    asr_model: 'sherpa_onnx_asr'
    # ASR固有の設定

  tts_config:
    tts_model: 'edge_tts'
    # TTS固有の設定

  vad_config:
    vad_model: 'silero_vad'
    # VAD固有の設定
```

## セキュリティ考慮事項

1. **ローカル実行**: 完全オフライン動作可能
2. **CORS設定**: 適切なCORSヘッダー設定
3. **ファイルアクセス制限**: アバター画像の拡張子制限
4. **WebSocket認証**: クライアントUID管理
5. **設定の検証**: Pydanticによる型安全性

## 拡張性

### プラグイン可能なコンポーネント
- 新しいLLMプロバイダーの追加
- カスタムASR/TTSエンジンの実装
- MCPサーバーの追加
- キャラクター設定の追加

### インターフェース設計
- 抽象基底クラスによる契約定義
- ファクトリーパターンによる実装選択
- 非同期ストリーミング対応
- 設定駆動型アーキテクチャ

## パフォーマンス最適化

1. **非同期処理**: 全コンポーネントで非同期対応
2. **ストリーミング**: リアルタイム応答生成
3. **キャッシング**: TTSキャッシュシステム
4. **並列処理**: 複数クライアント同時接続対応
5. **リソース管理**: 適切なコンテキスト管理

## 今後の開発計画

- 長期記憶機能の再実装
- より高度な感情表現
- マルチモーダル対話の強化
- プラグインシステムの拡張
- パフォーマンスの更なる最適化