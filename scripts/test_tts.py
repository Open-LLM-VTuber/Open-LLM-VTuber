import os
import sys
import yaml
import librosa
import re
from pathlib import Path
from rapidfuzz import fuzz
import argparse

sys.path.append(str(Path(__file__).parent.parent))

from src.open_llm_vtuber.tts.tts_factory import TTSFactory
from src.open_llm_vtuber.asr.asr_factory import ASRFactory

# 1. Rename 'special' key to 'symbols'
TEST_CASES = {
    "english": [
        "Hello, this is a standard functionality test.",
        "The quick brown fox jumps over the lazy dog.",
        "How much wood would a woodchuck chuck if a woodchuck could chuck wood?",
        "To be, or not to be, that is the question.",
        "The temperature is seventy-two degrees Fahrenheit."
    ],
    "chinese": [
        "你好，这是一个标准的功能性测试。",
        "今天天气不错，适合出去散步。",
        "床前明月光，疑是地上霜。",
        "中华人民共和国的首都是北京。",
        "这是一项测试语音合成流畅度的长句子。"
    ],
    "mixed": [
        "这个 Open-LLM-VTuber 项目真是太酷了！",
        "我今天会给你发一封 email，请注意查收。",
        "我们去 costco 买点 pizza 怎么样？",
        "这个 bug 的复现概率是 50%。",
        "请帮我 search 一下 '人工智能' 的最新进展。"
    ],
    "symbols": [ # <-- RENAMED
        "Okay... let's try this: <a> 'https://example.com' & `code`!",
        "Wow! 🎉 Is this real? 🤯 (50% off!)",
        "She said: \"It's a-m-a-z-i-n-g!\" #blessed",
        "He paid $1,234.56 for the new computer @ Apple Store.",
        "Hi👋，这是一个带有emoji和很多符号的句子，【系统】会卡住吗？"
    ]
}

def load_config(config_path="conf.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_tts_instance(config, tts_model_name):
    """Get a TTS instance based on the specified model name."""
    tts_params = config["character_config"]["tts_config"].get(tts_model_name, {})
    return TTSFactory.get_tts_engine(tts_model_name, **tts_params)

def get_asr_instance(asr_config):
    asr_model = asr_config["asr_model"]
    asr_params = asr_config.get(asr_model, {})
    return ASRFactory.get_asr_system(asr_model, **asr_params)

def remove_punctuation(text):
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", text).lower()

def audio_duration(audio_path):
    try:
        y, sr = librosa.load(audio_path, sr=None)
        return len(y) / sr
    except Exception as e:
        return -1 # Indicates failure to load

def wav_to_np(audio_path):
    y, sr = librosa.load(audio_path, sr=16000, mono=True)
    return y

def calculate_similarity(ref_text, hyp_text):
    return fuzz.ratio(ref_text, hyp_text)

def print_summary_report(results):
    """Print a formatted summary report at the end of the script."""
    print("\n" + "="*30 + " Automated Test Report " + "="*30)
    
    current_tts = ""
    for result in results:
        if result['tts_engine'] != current_tts:
            current_tts = result['tts_engine']
            print(f"\n--- TTS Engine: {current_tts} ---")

        status_icon = "✅" if result['status'] == 'PASS' else "❌"
        print(f"\n{status_icon} Test Case {result['id']}: {result['status']}")
        print(f"  - Original Text: \"{result['original_text']}\"")
        if result['recognized_text'] is not None:
            # For 'symbols', this is for reference only
            label = "Recognized Text" if result['similarity'] is not None else "Recognized Text (for reference)"
            print(f"  - {label}: \"{result['recognized_text']}\"")
        if result['similarity'] is not None:
            print(f"  - Similarity: {result['similarity']:.2f}%")
        print(f"  - Audio File: {result['audio_path']}")
        
    print("\n" + "="*75)
    print("End of Report.")


def main():
    parser = argparse.ArgumentParser(description="Automated testing script for TTS and ASR systems.")
    parser.add_argument(
        '--test_case', 
        type=str, 
        choices=['english', 'chinese', 'mixed', 'symbols'], 
        default='english',
        help='Select the test case category to run (default: english)'
    )
    parser.add_argument(
        '--tts', 
        nargs='+',
        help='Specify one or more TTS engines to test (e.g., edge_tts). If not specified, the default from conf.yaml is used.'
    )
    args = parser.parse_args()

    config = load_config()
    asr_config = config["character_config"]["asr_config"]
    asr = get_asr_instance(asr_config)

    if args.tts:
        tts_engines_to_test = args.tts
    else:
        tts_engines_to_test = [config["character_config"]["tts_config"]["tts_model"]]
        
    selected_cases = TEST_CASES[args.test_case]
    similarity_threshold = 70.0
    all_results = []

    print(f"Starting test... Category: '{args.test_case}', TTS Engines: {tts_engines_to_test}")
    
    for tts_engine_name in tts_engines_to_test:
        print("\n" + "="*60)
        print(f"Testing TTS Engine: {tts_engine_name}")
        print("="*60)
        
        try:
            tts = get_tts_instance(config, tts_engine_name)
        except Exception as e:
            print(f"[ERROR] Failed to initialize TTS engine '{tts_engine_name}': {e}")
            continue

        for idx, text in enumerate(selected_cases):
            test_id = f"{args.test_case}_{idx+1}"
            print(f"\nRunning Test {test_id}: \"{text}\"")
            
            result_data = {
                'tts_engine': tts_engine_name,
                'id': test_id,
                'original_text': text,
                'recognized_text': None,
                'similarity': None,
                'status': 'FAIL',
                'audio_path': 'N/A'
            }

            try:
                filename = f"{tts_engine_name}_{test_id}"
                audio_path = tts.generate_audio(text, file_name_no_ext=filename)
                result_data['audio_path'] = audio_path
                
                duration = audio_duration(audio_path)
                if duration < 0:
                    print(f"  [FAIL] Could not load the generated audio file.")
                    all_results.append(result_data)
                    continue
                
                print(f"  - Audio generated successfully, duration: {duration:.2f}s")

                # 2. Add ASR transcription for all cases, including 'symbols'
                audio_np = wav_to_np(audio_path)
                recognized = asr.transcribe_np(audio_np)
                result_data['recognized_text'] = recognized

                # 3. Logic is now split: 'symbols' case has different pass criteria
                if args.test_case == 'symbols':
                    result_data['status'] = 'PASS' # Generation success is the only criterion
                    print(f"  - ASR (for reference): {recognized}")
                    print("  [PASS] Symbols test passed (only checked for successful generation).")
                else: # Logic for 'english', 'chinese', 'mixed'
                    ref = remove_punctuation(text)
                    hyp = remove_punctuation(recognized)
                    similarity = calculate_similarity(ref, hyp)
                    result_data['similarity'] = similarity

                    if similarity >= similarity_threshold:
                        result_data['status'] = 'PASS'
                        print(f"  [PASS] ASR: {recognized} (Similarity: {similarity:.2f}%)")
                    else:
                        print(f"  [FAIL] ASR: {recognized} (Similarity: {similarity:.2f}%)")

            except Exception as e:
                print(f"  [FAIL] An unexpected error occurred during test execution: {e}")
            
            all_results.append(result_data)

    print_summary_report(all_results)


if __name__ == "__main__":
    main()