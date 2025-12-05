"""
Grimm 동화 웹 크롤러
메인 페이지에서 모든 동화책 링크를 수집하고, 각 동화의 본문 내용을 JSON 파일로 저장합니다.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re
from typing import List, Dict

# 기본 URL 설정
BASE_URL = "https://www.grimmstories.com"
MAIN_PAGE_URL = "https://www.grimmstories.com/ko/grimm_donghwa/index"


def get_story_links() -> List[Dict[str, str]]:
    """
    메인 페이지에서 모든 동화책 링크와 제목을 가져옵니다.
    
    Returns:
        List[Dict[str, str]]: 동화 제목과 URL을 담은 딕셔너리 리스트
    """
    print("메인 페이지에서 동화 목록을 가져오는 중...")
    
    # HTTP GET 요청으로 메인 페이지 HTML 가져오기
    response = requests.get(MAIN_PAGE_URL)
    response.encoding = 'utf-8'  # 인코딩 설정
    
    # BeautifulSoup으로 HTML 파싱
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 동화 링크들을 저장할 리스트
    story_links = []
    
    # 동화 링크 찾기 (웹사이트 구조에 따라 선택자 조정 필요)
    # 일반적으로 목록 페이지에서 링크들을 찾습니다
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link.get('href', '')
        # 동화 페이지 링크인지 확인 (패턴: /ko/grimm_donghwa/동화이름)
        if '/ko/grimm_donghwa/' in href and 'index' not in href and 'list' not in href:
            full_url = BASE_URL + href if not href.startswith('http') else href
            title = link.get_text(strip=True)
            
            # 중복 방지
            if title and not any(s['title'] == title for s in story_links):
                story_links.append({
                    'title': title,
                    'url': full_url
                })
    
    print(f"총 {len(story_links)}개의 동화를 찾았습니다.")
    return story_links


def extract_story_content(url: str) -> Dict[str, str]:
    """
    개별 동화 페이지에서 본문 내용을 추출합니다.
    
    Args:
        url (str): 동화 페이지 URL
    
    Returns:
        Dict[str, str]: 제목과 본문 내용을 담은 딕셔너리
    """
    print(f"페이지 크롤링 중: {url}")
    
    # HTTP GET 요청
    response = requests.get(url)
    response.encoding = 'utf-8'
    
    # HTML 파싱
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 제목 추출 (itemprop='name' 속성 사용)
    title = ""
    title_tag = soup.find(attrs={'itemprop': 'name'})
    if not title_tag:
        title_tag = soup.find('h2')
    if title_tag:
        title = title_tag.get_text(strip=True)
    
    # 본문 내용 추출
    # 방법 1: itemprop='text' 속성을 가진 div 찾기 (가장 정확)
    content = ""
    story_div = soup.find(attrs={'itemprop': 'text'})
    
    # 방법 2: ID='plainText' 찾기
    if not story_div:
        story_div = soup.find('div', id='plainText')
    
    # 방법 3: main 클래스에서 불필요한 요소 제거 후 추출
    if not story_div:
        story_div = soup.find('div', class_='main')
        if story_div:
            # 불필요한 요소 제거
            for unwanted in story_div.find_all(['header', 'footer', 'nav']):
                unwanted.decompose()
    
    if story_div:
        content = story_div.get_text(separator='\n\n', strip=True)
    
    return {
        'title': title,
        'url': url,
        'content': content
    }


def sanitize_filename(title: str) -> str:
    """
    파일명으로 사용할 수 없는 특수문자를 제거하고 안전한 파일명을 만듭니다.
    
    Args:
        title (str): 원본 제목
    
    Returns:
        str: 안전한 파일명
    """
    # Windows에서 파일명으로 사용할 수 없는 문자들 제거
    invalid_chars = r'[<>:"/\\|?*]'
    safe_title = re.sub(invalid_chars, '', title)
    
    # 앞뒤 공백 제거 및 여러 공백을 하나로
    safe_title = ' '.join(safe_title.split())
    
    # 파일명이 비어있으면 기본값 사용
    if not safe_title:
        safe_title = 'untitled'
    
    return safe_title


def save_story_to_json(story: Dict, output_folder: str = 'origin_json'):
    """
    개별 동화를 JSON 파일로 저장합니다.
    
    Args:
        story (Dict): 동화 데이터 (title, url, content 포함)
        output_folder (str): 저장할 폴더명
    """
    # 출력 폴더가 없으면 생성
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"'{output_folder}' 폴더를 생성했습니다.")
    
    # 안전한 파일명 생성
    safe_filename = sanitize_filename(story['title'])
    filepath = os.path.join(output_folder, f"{safe_filename}.json")
    
    # JSON 파일로 저장
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(story, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 저장 완료: {safe_filename}.json")


def main():
    """
    메인 실행 함수
    """
    print("=" * 60)
    print("Grimm 동화 크롤러 시작")
    print("=" * 60)
    
    # 1단계: 모든 동화 링크 수집
    story_links = get_story_links()
    
    if not story_links:
        print("동화 링크를 찾을 수 없습니다. 웹사이트 구조를 확인해주세요.")
        return
    
    # 2단계: 각 동화 페이지에서 본문 추출 및 개별 저장
    success_count = 0
    output_folder = 'origin_json'
    
    for i, story_info in enumerate(story_links, 1):
        print(f"\n[{i}/{len(story_links)}] {story_info['title']}")
        
        try:
            # 동화 내용 추출
            story_data = extract_story_content(story_info['url'])
            
            # 개별 JSON 파일로 저장
            save_story_to_json(story_data, output_folder)
            success_count += 1
            
            # 서버에 부담을 주지 않기 위해 요청 사이에 대기
            time.sleep(1)
            
        except Exception as e:
            print(f"  ⚠ 오류 발생: {e}")
            continue
    
    # 3단계: 완료 메시지
    print("\n" + "=" * 60)
    print("크롤링 완료!")
    print(f"총 수집된 동화: {success_count}개")
    print(f"저장 위치: ./{output_folder}/ 폴더")
    print("=" * 60)


if __name__ == "__main__":
    main()

