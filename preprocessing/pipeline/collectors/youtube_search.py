"""
유튜브 자동 검색 + 자막 수집

게임 이름으로 YouTube Data API v3 검색 → 룰 설명 영상 찾기 → 자막 추출.
기존 youtube_collector.py는 URL이 있어야 동작하지만,
이 모듈은 게임 이름만으로 자동 검색한다.
"""

import os
import re

import httpx
from dotenv import load_dotenv

from preprocessing.pipeline.config import YOUTUBE_WHITELIST_CHANNELS

load_dotenv()


def search_videos(game_name: str, max_results: int = 5) -> list[dict]:
    """
    YouTube Data API v3으로 게임 룰 설명 영상 검색

    Args:
        game_name: 게임 이름 (한국어)
        max_results: 최대 검색 결과 수

    Returns:
        [{"video_id": str, "title": str, "channel": str, "url": str}, ...]
    """
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY가 .env에 없습니다.")

    # 검색어: 게임 이름 + 룰/규칙 키워드
    query = f"{game_name} 보드게임 룰 설명"

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "relevanceLanguage": "ko",
        "key": api_key,
    }

    response = httpx.get(url, params=params, timeout=15)

    if response.status_code != 200:
        raise RuntimeError(
            f"YouTube API 검색 실패 {response.status_code}: {response.text[:200]}"
        )

    data = response.json()
    results = []

    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        video_id = item["id"]["videoId"]
        results.append({
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "url": f"https://www.youtube.com/watch?v={video_id}",
        })

    return results


def _is_rule_video(title: str, channel: str) -> bool:
    """룰 설명 영상인지 판별 (제목/채널 기반)"""
    # 화이트리스트 채널이면 바로 통과
    for wl in YOUTUBE_WHITELIST_CHANNELS:
        if wl in channel:
            return True

    # 제목에 룰 관련 키워드 포함 여부
    rule_keywords = ["룰", "규칙", "하는법", "하는 법", "설명", "가이드", "how to play", "rules"]
    title_lower = title.lower()
    return any(kw in title_lower for kw in rule_keywords)


def _extract_transcript(video_id: str) -> dict | None:
    """유튜브 자막 추출 (한국어 우선, 자동생성 포함)"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        raise RuntimeError(
            "youtube-transcript-api 패키지가 필요합니다. "
            "uv add youtube-transcript-api 로 설치하세요."
        )

    api = YouTubeTranscriptApi()

    # 사용 가능한 자막 목록 조회
    try:
        transcript_list = api.list(video_id)
    except Exception:
        return None

    # 수동 자막 > 자동생성 자막, 한국어 > 영어 우선순위로 선택
    best = None
    lang = "ko"

    for t in transcript_list:
        if t.language_code == "ko" and not t.is_generated:
            best = t
            break
        elif t.language_code == "ko" and t.is_generated and best is None:
            best = t
        elif t.language_code == "en" and not t.is_generated and best is None:
            best = t
            lang = "en"
        elif t.language_code == "en" and t.is_generated and best is None:
            best = t
            lang = "en"

    if best is None:
        return None

    lang = best.language_code

    # 자막 텍스트 가져오기
    try:
        result = api.fetch(video_id, languages=[lang])
        snippets = list(result)
        raw_text = " ".join(s.text for s in snippets)
    except Exception:
        return None

    # 타임스탬프 제거 + 정리
    raw_text = re.sub(r"\[?\d{1,2}:\d{2}(:\d{2})?\]?\s*", "", raw_text)
    raw_text = re.sub(r"\n{3,}", "\n\n", raw_text)
    raw_text = re.sub(r"[ \t]+", " ", raw_text)

    return {"text": raw_text.strip(), "language": lang}


def search_and_collect(game_name: str, max_results: int = 5) -> dict | None:
    """
    게임 이름으로 유튜브 검색 → 최적 영상 선택 → 자막 수집

    Args:
        game_name: 게임 한국어 이름
        max_results: 검색할 최대 영상 수

    Returns:
        {"raw_content": str, "language": str, "metadata": dict} 또는 None
    """
    print(f"    [유튜브검색] '{game_name}' 검색 중...")

    videos = search_videos(game_name, max_results=max_results)

    if not videos:
        print("    [유튜브검색] 검색 결과 없음")
        return None

    # 룰 관련 영상 필터링 + 화이트리스트 채널 우선
    rule_videos = [v for v in videos if _is_rule_video(v["title"], v["channel"])]

    # 화이트리스트 채널 먼저, 나머지는 원래 순서
    def priority(v):
        for i, wl in enumerate(YOUTUBE_WHITELIST_CHANNELS):
            if wl in v["channel"]:
                return i
        return 100

    rule_videos.sort(key=priority)

    # 룰 영상이 없으면 전체 결과에서 시도
    candidates = rule_videos if rule_videos else videos

    # 자막 있는 첫 번째 영상 선택
    for video in candidates:
        print(f"    [유튜브검색] 시도: {video['title']} ({video['channel']})")
        result = _extract_transcript(video["video_id"])

        if result and len(result["text"]) > 100:
            print(f"    [유튜브검색] {len(result['text'])}자 추출 ({result['language']})")
            return {
                "raw_content": result["text"],
                "language": result["language"],
                "metadata": {
                    "video_id": video["video_id"],
                    "video_title": video["title"],
                    "channel": video["channel"],
                    "source_url": video["url"],
                },
            }

    print("    [유튜브검색] 자막 있는 영상을 찾지 못함")
    return None
