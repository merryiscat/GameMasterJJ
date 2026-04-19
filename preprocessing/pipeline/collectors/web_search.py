"""
웹 검색 수집기 (Tavily API)

게임 이름으로 웹 검색 → 룰 설명 페이지 찾기 → 본문 텍스트 추출.
Tavily는 검색 + 본문 추출을 한번에 해준다.
"""

import os
import re

from dotenv import load_dotenv

load_dotenv()


def search_and_collect(game_name: str, max_results: int = 5) -> dict | None:
    """
    게임 이름으로 웹 검색 → 룰 관련 페이지 본문 수집

    Tavily API의 search_depth="advanced"를 사용하면
    검색 결과의 전체 본문(raw_content)까지 가져올 수 있다.

    Args:
        game_name: 게임 한국어 이름
        max_results: 최대 검색 결과 수

    Returns:
        {"raw_content": str, "metadata": dict} 또는 None
    """
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY가 .env에 없습니다.")

    try:
        from tavily import TavilyClient
    except ImportError:
        raise RuntimeError(
            "tavily-python 패키지가 필요합니다. "
            "uv add tavily-python 로 설치하세요."
        )

    print(f"    [웹검색] '{game_name}' 검색 중...")

    client = TavilyClient(api_key=api_key)

    # 검색어: 게임 이름 + 룰 키워드
    query = f"{game_name} 보드게임 룰 규칙"

    try:
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",      # 본문 전체 추출
            include_raw_content=True,      # raw_content 포함
            include_domains=[],            # 모든 도메인
            exclude_domains=[              # 쇼핑/판매 사이트 제외
                "coupang.com",
                "gmarket.co.kr",
                "11st.co.kr",
                "auction.co.kr",
            ],
        )
    except Exception as e:
        print(f"    [웹검색] API 호출 실패: {e}")
        return None

    results = response.get("results", [])

    if not results:
        print("    [웹검색] 검색 결과 없음")
        return None

    # 룰 관련 페이지 필터링
    rule_keywords = ["룰", "규칙", "하는법", "하는 법", "설명", "가이드", "rule", "how to play"]
    collected_texts = []
    collected_sources = []

    for r in results:
        title = r.get("title", "").lower()
        content = r.get("raw_content") or r.get("content", "")
        url = r.get("url", "")

        # 제목이나 URL에 룰 관련 키워드가 있는지
        is_rule = any(kw in title for kw in rule_keywords)

        # 키워드 없어도 내용이 충분하면 포함
        if not is_rule and len(content) < 500:
            continue

        if content and len(content) > 100:
            # 텍스트 정리
            cleaned = _clean_text(content)
            if len(cleaned) > 100:
                collected_texts.append(cleaned)
                collected_sources.append({
                    "title": r.get("title", ""),
                    "url": url,
                    "score": r.get("score", 0),
                })

    if not collected_texts:
        print("    [웹검색] 유의미한 룰 페이지를 찾지 못함")
        return None

    # 여러 페이지의 텍스트를 합침 (소스별 구분)
    combined = []
    for i, (text, src) in enumerate(zip(collected_texts, collected_sources)):
        combined.append(f"--- 출처 {i+1}: {src['title']} ({src['url']}) ---\n{text}")

    raw_content = "\n\n".join(combined)

    print(f"    [웹검색] {len(collected_texts)}개 페이지에서 {len(raw_content)}자 추출")

    return {
        "raw_content": raw_content,
        "metadata": {
            "sources": collected_sources,
            "query": query,
            "total_results": len(results),
            "collected_results": len(collected_texts),
        },
    }


def _clean_text(text: str) -> str:
    """텍스트 정리"""
    # 연속 빈 줄 정리
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 연속 공백 정리
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()
