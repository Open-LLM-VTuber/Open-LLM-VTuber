"""
2차 작업: 텍스트 정제 스크립트
- 띄어쓰기 제거
- 영어 제거
- 특수문자 제거
- 한자 제거
- 기호 제거
- 동화와 상관없는 텍스트 제거
"""

import json
import os
import re
from typing import Dict

# 입력/출력 폴더 설정
INPUT_FOLDER = 'origin_json'
OUTPUT_FOLDER = 'cleaned_json'


def remove_unwanted_text(text: str) -> str:
    """
    동화와 상관없는 텍스트를 제거합니다.
    예: "동화 읽고 →", 번역 안내, 링크 등
    """
    # "동화 읽고 →" 같은 패턴 제거
    text = re.sub(r'동화\s*읽고\s*[→>]', '', text)
    
    # 이메일 주소 제거
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', text)
    
    # URL 제거
    text = re.sub(r'https?://[^\s]+', '', text)
    
    # "번역을 환영합니다" 같은 안내 문구 제거
    text = re.sub(r'번역을\s*환영합니다', '', text)
    text = re.sub(r'이메일로\s*보내세요', '', text)
    
    # 언어 코드 제거 (ZH, VI, TR, RU 등)
    text = re.sub(r'\b(ZH|VI|TR|RU|RO|PT|PL|NL|KO|JA|IT|HU|FR|FI|ES|EN|DE|DA)\b', '', text)
    
    # "그림 형제 →" 같은 패턴 제거
    text = re.sub(r'그림\s*형제\s*[→>]', '', text)
    
    return text


def clean_text(text: str) -> str:
    """
    텍스트를 정제합니다.
    1. 영어 제거
    2. 특수문자 제거
    3. 한자 제거
    4. 기호 제거
    (띄어쓰기와 줄바꿈은 유지)
    """
    if not text:
        return ""
    
    # 1단계: 동화와 상관없는 텍스트 제거
    text = remove_unwanted_text(text)
    
    # 1.5단계: 괄호와 그 안의 내용 제거 (설명, 주석 등)
    # 예: "라푼첼(초롱꽃속의 식물)" → "라푼첼"
    text = re.sub(r'\([^)]*\)', '', text)  # 소괄호
    text = re.sub(r'\[[^\]]*\]', '', text)  # 대괄호
    text = re.sub(r'\{[^}]*\}', '', text)   # 중괄호
    
    # 2단계: 영어 제거 (알파벳만, 공백은 유지)
    text = re.sub(r'[a-zA-Z]+', '', text)
    
    # 3단계: 한자 제거 (CJK 통합 한자 범위: \u4E00-\u9FFF)
    text = re.sub(r'[\u4E00-\u9FFF]', '', text)
    
    # 4단계: 특수문자 및 기호 제거
    # 한글, 숫자, 기본 구두점(마침표, 쉼표, 물음표, 느낌표), 공백, 줄바꿈만 남김
    # 한글: \uAC00-\uD7A3 (완성형), \u1100-\u11FF (초성), \u3130-\u318F (호환 자모)
    # 숫자: 0-9
    # 기본 구두점: . , ? ! 
    # 공백 및 줄바꿈: \s (공백, 탭, 줄바꿈 등)
    text = re.sub(r'[^\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F0-9.,?!\s]', '', text)
    
    # 5단계: 연속된 구두점 정리
    text = re.sub(r'[.,?!]{2,}', lambda m: m.group()[0], text)
    
    # 6단계: 연속된 공백을 하나로 정리 (띄어쓰기는 유지하되 여러 개는 하나로)
    text = re.sub(r'[ \t]+', ' ', text)  # 공백과 탭만 정리
    # 줄바꿈은 그대로 유지 (\n\n도 유지)
    
    return text.strip()


def count_sentences(text: str) -> int:
    """
    문장 개수를 세는 함수 (마침표, 물음표, 느낌표 기준)
    """
    if not text:
        return 0
    # 마침표, 물음표, 느낌표로 문장 구분
    sentences = re.split(r'[.!?]', text)
    # 빈 문자열 제거
    sentences = [s.strip() for s in sentences if s.strip()]
    return len(sentences)


def split_into_scenes(text: str) -> list:
    """
    텍스트를 문맥을 고려하여 장면으로 나눕니다.
    \n\n을 기준으로 문단을 나누되, 적절히 묶어서 장면으로 만듭니다.
    """
    if not text:
        return []
    
    # 1단계: \n\n을 기준으로 문단 분리
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    if not paragraphs:
        return []
    
    scenes = []
    current_scene = []
    current_length = 0
    
    for i, paragraph in enumerate(paragraphs):
        # 문단의 문장 개수와 길이 확인
        sentence_count = count_sentences(paragraph)
        char_count = len(paragraph)
        
        # 현재 장면에 추가
        current_scene.append(paragraph)
        current_length += char_count
        
        # 장면 분리 기준:
        # 1. 문장이 5개 이상이면 분리
        # 2. 문장이 3-4개이고 다음 문단이 있으면 분리 고려
        # 3. 현재 장면이 너무 길면 (2000자 이상) 분리
        should_split = False
        
        if sentence_count >= 5:
            should_split = True
        elif sentence_count >= 3 and current_length >= 800:
            # 다음 문단이 있고, 현재 장면이 적당히 길면 분리
            if i < len(paragraphs) - 1:
                next_sentences = count_sentences(paragraphs[i + 1])
                # 다음 문단이 짧으면(1-2문장) 합치기, 길면 분리
                if next_sentences >= 3:
                    should_split = True
        elif current_length >= 2000:
            should_split = True
        
        # 마지막 문단이면 무조건 현재 장면에 추가
        if i == len(paragraphs) - 1:
            should_split = True
        
        if should_split:
            # 현재 장면을 하나의 텍스트로 합치기
            scene_text = ' '.join(current_scene)
            if scene_text.strip():
                scenes.append(scene_text.strip())
            current_scene = []
            current_length = 0
    
    return scenes


def clean_story_file(input_path: str, output_path: str):
    """
    개별 JSON 파일을 읽어서 정제하고 장면으로 나눠서 저장합니다.
    """
    try:
        # JSON 파일 읽기
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 텍스트 정제
        cleaned_text = clean_text(data.get('content', ''))
        
        # 장면으로 분할
        scenes = split_into_scenes(cleaned_text)
        
        # 순수 장면 배열만 저장 (JSON 구조 없이)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(scenes, f, ensure_ascii=False, indent=2)
        
        total_chars = sum(len(scene) for scene in scenes)
        return True, len(scenes), total_chars
    
    except Exception as e:
        print(f"  ⚠️ 오류 발생: {e}")
        return False, 0, 0


def main():
    """
    메인 실행 함수
    """
    print("=" * 70)
    print("2차 작업: 텍스트 정제 시작")
    print("=" * 70)
    
    # 출력 폴더 생성
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"✓ '{OUTPUT_FOLDER}' 폴더를 생성했습니다.\n")
    
    # 입력 폴더의 모든 JSON 파일 찾기
    json_files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith('.json')]
    
    if not json_files:
        print(f"⚠️ '{INPUT_FOLDER}' 폴더에 JSON 파일이 없습니다.")
        return
    
    print(f"총 {len(json_files)}개의 파일을 정제합니다.\n")
    
    # 각 파일 정제
    success_count = 0
    total_chars = 0
    total_scenes = 0
    
    for i, filename in enumerate(json_files, 1):
        input_path = os.path.join(INPUT_FOLDER, filename)
        output_path = os.path.join(OUTPUT_FOLDER, filename)
        
        print(f"[{i}/{len(json_files)}] {filename}")
        
        success, scene_count, char_count = clean_story_file(input_path, output_path)
        
        if success:
            success_count += 1
            total_chars += char_count
            total_scenes += scene_count
            print(f"  ✓ 완료 (장면: {scene_count}개, 텍스트: {char_count:,} 자)")
        else:
            print(f"  ✗ 실패")
    
    # 결과 요약
    print("\n" + "=" * 70)
    print("정제 완료!")
    print(f"성공: {success_count}/{len(json_files)}개 파일")
    print(f"총 장면 개수: {total_scenes}개")
    print(f"총 정제된 텍스트 길이: {total_chars:,} 자")
    print(f"저장 위치: ./{OUTPUT_FOLDER}/ 폴더")
    print("=" * 70)


if __name__ == "__main__":
    main()

