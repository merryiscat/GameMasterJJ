"""
유튜브 수집기

유튜브 영상의 자막(caption)을 추출하여 텍스트로 변환.
source_url이 이미 등록된 경우에 사용한다.
(자동검색은 youtube_search.py 참고)
"""

import re

from preprocessing.pipeline.config import YOUTUBE_WHITELIST_CHANNELS


def _clean_transcript(text: str) -> str:
    """자막 텍스트 정리 (타임스탬프 제거, 줄바꿈 정리)"""
    text = re.sub(r"\[?\d{1,2}:\d{2}(:\d{2})?\]?\s*", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def collect(source_row: dict) -> dict:
    """
    유튜브 영상에서 자막 추출 (URL이 등록된 경우)

    한국어 자막 우선, 없으면 영어 자막. 수동/자동생성 모두 시도.

    Args:
        source_row: game_rule_sources 테이블의 1행
                    source_url: 유튜브 영상 URL

    Returns:
        {"raw_content": str, "language": str, "metadata": dict}
    """
    source_url = source_row.get("source_url", "")
    if not source_url:
        raise ValueError("source_url이 비어있음")

    video_id = _extract_video_id(source_url)
    print(f"    [유튜브] {video_id} 자막 추출 중...")

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        raise RuntimeError(
            "youtube-transcript-api 패키지가 필요합니다. "
            "uv add youtube-transcript-api 로 설치하세요."
        )

    api = YouTubeTranscriptApi()

    # 사용 가능한 자막 목록 조회
    transcript_list = api.list(video_id)

    # 수동 자막 > 자동생성, 한국어 > 영어 우선순위
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
        raise ValueError(f"자막을 찾을 수 없음: {video_id}")

    lang = best.language_code

    # 자막 텍스트 가져오기
    result = api.fetch(video_id, languages=[lang])
    snippets = list(result)
    raw_text = " ".join(s.text for s in snippets)
    raw_content = _clean_transcript(raw_text)

    if not raw_content.strip():
        raise ValueError("자막 텍스트가 비어있음")

    print(f"    [유튜브] {len(raw_content)}자 추출 ({lang})")

    return {
        "raw_content": raw_content,
        "language": lang,
        "metadata": {
            "video_id": video_id,
            "source_url": source_url,
            "transcript_language": lang,
            "is_generated": best.is_generated,
        },
    }


def _extract_video_id(url: str) -> str:
    """유튜브 URL에서 video ID 추출"""
    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"유튜브 video ID를 추출할 수 없음: {url}")
