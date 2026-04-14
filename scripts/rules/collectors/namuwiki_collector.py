"""
나무위키 수집기

나무위키는 클라이언트 사이드 렌더링이라 Playwright로 페이지를 로드한 뒤
렌더링된 HTML에서 본문 텍스트를 추출한다.
"""

import re

from playwright.sync_api import sync_playwright


def _clean_text(text: str) -> str:
    """추출된 텍스트 정리"""
    # 연속 빈 줄 정리
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 앞뒤 공백 정리
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def collect(source_row: dict) -> dict:
    """
    나무위키에서 게임 문서 수집 (Playwright 사용)

    Args:
        source_row: game_rule_sources 테이블의 1행
                    source_url 형식: "https://namu.wiki/w/게임이름"

    Returns:
        {"raw_content": str}
    """
    source_url = source_row.get("source_url", "")
    if not source_url:
        raise ValueError("source_url이 비어있음")

    print(f"    [나무위키] {source_url} 크롤링 중 (Playwright)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 페이지 로드 + JS 렌더링 대기
        page.goto(source_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)  # 나무위키 JS 렌더링 대기

        # 본문 추출 (여러 셀렉터 시도)
        raw_text = ""
        for selector in [".wiki-inner-content", "article", ".content"]:
            el = page.query_selector(selector)
            if el:
                raw_text = el.inner_text()
                if len(raw_text) > 100:
                    break

        # 폴백: body 전체
        if len(raw_text) < 100:
            raw_text = page.inner_text("body")

        browser.close()

    raw_content = _clean_text(raw_text)

    if not raw_content.strip() or len(raw_content) < 50:
        raise ValueError("나무위키에서 유의미한 텍스트 추출 실패")

    print(f"    [나무위키] {len(raw_content)}자 추출")

    return {"raw_content": raw_content}
