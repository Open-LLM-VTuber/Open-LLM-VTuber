## LLM  VTuber
https://docs.llmvtuber.com/en/docs/quick-start/

1. brew install ffmepg
2. brew install uv
  ※ 未インストールの場合
```
source ~/.bashrc
```
3. GITのリリースより、zipをDL
~~http://github.com/Open-LLM-VTuber/Open-LLM-VTuber/releases~~

今回はgit cloneしてバージョンだけ1.2.1に変更

4. zip解凍しプロジェクトルートでuv syncしインストール
uv sync

5. メインプログラムを実行して構成ファイルを生成
uv run run_server.py

6. ollama dl
https://ollama.com/download/mac

7. qwen2.5 install
ollama run qwen2.5:latest
ollama --version
ollama list

ollama run gemma3:12b
8. 起動
uv run run_server.py
※ リソースホームで

9. whisper 
※ リソースディレクトリで
uv venv
source .venv/bin/activate
uv pip install faster-whisper
# 無音検出
uv pip install silero-vad
<!-- wget https://huggingface.co/kotoba-tech/kotoba-whisper-v1.0-ggml/resolve/main/sample_ja_speech.wav -->



# モデルカスタム
# 1. Modelfileを作成
cat <<EOF > gemma2:9b-num_ctx_8192
FROM gemma2:9b
PARAMETER num_ctx 8192
EOF

ollama create gemma2:9b-num_ctx_8192 -f gemma2:9b-num_ctx_8192

# チャンク改善
日本語弱いのでjaのチャンク改善したい