"""
유튜브 수집기

유튜브 영상의 자막(caption)을 추출하여 텍스트로 변환.
채널 화이트리스트 기반으로 품질 높은 룰 설명 영상만 수집.
"""

import re

from scripts.rules.config import YOUTUBE_WHITELIST_CHANNELS


def _extract_video_id(url: str) -> str:
    """유튜브 URL에서 video ID 추출"""
    # https://www.youtube.com/watch?v=VIDEO_ID
    # https://youtu.be/VIDEO_ID
    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"유튜브 video ID를 추출할 수 없음: {url}")


def _clean_transcript(text: str) -> str:
    """자막 텍스트 정리 (타임스탬프 제거, 줄바꿈 정리)"""
    # 타임스탬프 패턴 제거: [00:00:00] 또는 00:00
    text = re.sub(r"\[?\d{1,2}:\d{2}(:\d{2})?\]?\s*", "", text)
    # 연속 공백/줄바꿈 정리
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def collect(source_row: dict) -> dict:
    """
    유튜브 영상에서 자막 추출

    youtube-transcript-api 패키지를 사용하여 자막을 가져온다.
    한국어 자막 우선, 없으면 영어 자막 + 자동 생성 자막도 시도.

    Args:
        source_row: game_rule_sources 테이블의 1행
                    source_url: 유튜브 영상 URL

    Returns:
        {"raw_content": str, "metadata": dict}
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

    # 자막 가져오기 (한국어 우선 → 영어 → 자동생성)
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

    transcript = None
    lang = "ko"

    # 수동 자막 우선
    try:
        transcript = transcript_list.find_manually_created_transcript(["ko"])
    except Exception:
        try:
            transcript = transcript_list.find_manually_created_transcript(["en"])
            lang = "en"
        except Exception:
            pass

    # 수동 자막 없으면 자동 생성 자막
    if transcript is None:
        try:
            transcript = transcript_list.find_generated_transcript(["ko"])
        except Exception:
            try:
                transcript = transcript_list.find_generated_transcript(["en"])
                lang = "en"
            except Exception:
                raise ValueError(f"자막을 찾을 수 없음: {video_id}")

    # 자막 텍스트 추출
    entries = transcript.fetch()
    raw_lines = [entry["text"] for entry in entries]
    raw_text = "\n".join(raw_lines)
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
        },
    }
