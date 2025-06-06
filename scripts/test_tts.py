import os
import sys
import yaml
import numpy as np
import librosa
import re
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.open_llm_vtuber.tts.tts_factory import TTSFactory
from src.open_llm_vtuber.asr.asr_factory import ASRFactory

def load_config(config_path="conf.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config

def get_tts_instance(tts_config):
    tts_model = tts_config["tts_model"]
    tts_params = tts_config.get(tts_model, {})
    return TTSFactory.get_tts_engine(tts_model, **tts_params)

def get_asr_instance(asr_config):
    asr_model = asr_config["asr_model"]
    asr_params = asr_config.get(asr_model, {})
    return ASRFactory.get_asr_system(asr_model, **asr_params)

def remove_punctuation(text):
    # Remove all punctuation and spaces, keep letters/numbers/Chinese
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", text).lower()

def audio_duration(audio_path):
    y, sr = librosa.load(audio_path, sr=None)
    return len(y) / sr

def wav_to_np(audio_path):
    y, sr = librosa.load(audio_path, sr=16000, mono=True)
    return y

def main():
    config = load_config()
    try:
        tts_config = config["character_config"]["tts_config"]
        asr_config = config["character_config"]["asr_config"]
    except KeyError as e:
        print(f"[ERROR] 配置文件缺少键: {e}")
        print(f"可用顶层键: {list(config.keys())}")
        print("请检查 conf.yaml 结构，确保包含 tts_config 和 asr_config。")
        return

    tts = get_tts_instance(tts_config)
    asr = get_asr_instance(asr_config)

    test_sentences = [
        "Hello, this is a TTS test.",
        "今天天气不错，适合出去散步。",
        "Open-LLM-VTuber 项目正在测试语音合成。",
        "The quick brown fox jumps over the lazy dog.",
        "请说出下面这句话：你好，世界！"
    ]

    print(f"Testing TTS: {tts_config['tts_model']}  |  ASR: {asr_config['asr_model']}")
    print("=" * 60)

    for idx, text in enumerate(test_sentences):
        print(f"Test {idx+1}: \"{text}\"")
        # 生成音频
        audio_path = tts.generate_audio(text, file_name_no_ext=f"test_tts_{idx}")
        # 检查音频长度
        duration = audio_duration(audio_path)
        if duration < 0.5 or duration > 20:
            print(f"  [FAIL] Audio duration abnormal: {duration:.2f}s")
            continue
        # 识别
        audio_np = wav_to_np(audio_path)
        try:
            recognized = asr.transcribe_np(audio_np)
        except Exception as e:
            print(f"  [FAIL] ASR error: {e}")
            continue
        # 对比文本
        ref = remove_punctuation(text)
        hyp = remove_punctuation(recognized)
        # 简单相似度判定
        match = (ref in hyp) or (hyp in ref) or (len(set(ref) & set(hyp)) / max(len(ref), 1) > 0.7)
        if match:
            print(f"  [PASS] ASR: {recognized}  (duration: {duration:.2f}s)")
        else:
            print(f"  [FAIL] ASR: {recognized}  (duration: {duration:.2f}s)")
    print("=" * 60)
    print("TTS/ASR test finished.")

if __name__ == "__main__":
    main()
