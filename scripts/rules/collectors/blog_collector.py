"""
블로그 수집기

네이버 블로그 등에서 보드게임 규칙 설명 게시글을 크롤링하여 텍스트 추출.
"""

import re

import httpx
from bs4 import BeautifulSoup


def _clean_blog_html(html: str) -> str:
    """블로그 HTML을 텍스트로 변환"""
    soup = BeautifulSoup(html, "html.parser")

    # 스크립트, 스타일 제거
    for tag in soup.find_all(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    # 본문 영역 찾기 (네이버 블로그 패턴)
    # se-main-container 또는 post-view 등
    content_area = (
        soup.find("div", class_="se-main-container")
        or soup.find("div", id="postViewArea")
        or soup.find("div", class_="post-view")
        or soup.find("article")
        or soup.find("div", class_="entry-content")
        or soup.body  # 최후 수단
    )

    if content_area is None:
        content_area = soup

    text = content_area.get_text(separator="\n")

    # 정리
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def collect(source_row: dict) -> dict:
    """
    블로그 URL에서 본문 텍스트 추출

    Args:
        source_row: game_rule_sources 테이블의 1행
                    source_url: 블로그 게시글 URL

    Returns:
        {"raw_content": str, "metadata": dict}
    """
    source_url = source_row.get("source_url", "")
    if not source_url:
        raise ValueError("source_url이 비어있음")

    print(f"    [블로그] {source_url} 크롤링 중...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    # 네이버 블로그는 iframe 구조라 모바일 URL로 변환
    if "blog.naver.com" in source_url:
        # https://blog.naver.com/userId/postId → https://m.blog.naver.com/userId/postId
        source_url = source_url.replace("blog.naver.com", "m.blog.naver.com")

    response = httpx.get(source_url, headers=headers, follow_redirects=True, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(
            f"블로그 요청 실패 {response.status_code}: {source_url}"
        )

    raw_content = _clean_blog_html(response.text)

    if not raw_content.strip() or len(raw_content) < 100:
        raise ValueError("블로그에서 유의미한 텍스트 추출 실패")

    print(f"    [블로그] {len(raw_content)}자 추출")

    return {
        "raw_content": raw_content,
        "metadata": {
            "source_url": source_url,
        },
    }
