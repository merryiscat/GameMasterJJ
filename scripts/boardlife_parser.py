"""
보드라이프(boardlife.co.kr) 게임 상세 페이지 파서

게임 상세 페이지(/game/{id})의 HTML을 파싱해서
구조화된 딕셔너리로 변환합니다.

사용법:
    # 단일 페이지 테스트
    uv run python scripts/boardlife_parser.py

    # 모듈로 import
    from boardlife_parser import parse_game_detail, parse_rank_page
"""

import re
import json
from bs4 import BeautifulSoup


# ============================================================
# 랭킹 페이지 파서 (/rank/all/{page})
# ============================================================
def parse_rank_page(html: str) -> list[dict]:
    """
    랭킹 페이지에서 게임 ID + 기본 정보 추출

    반환값: [{"boardlife_id": "8569", "name_ko": "브라스: 버밍엄", ...}, ...]
    """
    soup = BeautifulSoup(html, "html.parser")
    games = []

    # JSON-LD (Schema.org) 데이터에서 게임 목록 추출
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)

            # ItemList 타입 찾기 (게임 목록)
            if data.get("@type") == "ItemList":
                for item in data.get("itemListElement", []):
                    game_item = item.get("item", {})
                    url = game_item.get("url", "")

                    # URL에서 게임 ID 추출: /game/8569 → 8569
                    match = re.search(r"/game/(\d+)", url)
                    if match:
                        games.append({
                            "boardlife_id": match.group(1),
                            "name": game_item.get("name", ""),
                            "url": url,
                        })
        except (json.JSONDecodeError, TypeError):
            continue

    # HTML에서 /game/{id} 링크 패턴으로 게임 ID 추출 (더 많은 게임 포함)
    # JSON-LD는 사이드바 탑 10만 포함하므로, HTML 링크를 우선 사용
    html_games = []
    seen = set()
    for link in soup.find_all("a", href=re.compile(r"/game/\d+")):
        match = re.search(r"/game/(\d+)", link.get("href", ""))
        if match:
            game_id = match.group(1)
            name = link.get_text(strip=True)
            # 중복 제거 + 이름이 있는 것만
            if game_id not in seen and name and len(name) > 1:
                seen.add(game_id)
                html_games.append({
                    "boardlife_id": game_id,
                    "name": name,
                    "url": f"/game/{game_id}",
                })

    # HTML에서 더 많이 찾았으면 HTML 결과 사용
    return html_games if len(html_games) >= len(games) else games


# ============================================================
# 게임 상세 페이지 파서 (/game/{id})
# ============================================================
def parse_game_detail(html: str, boardlife_id: str) -> dict | None:
    """
    게임 상세 페이지 HTML을 파싱해서 구조화된 딕셔너리로 반환

    반환값:
    {
        "boardlife_id": "8569",
        "name_ko": "브라스: 버밍엄",
        "name_en": "Brass: Birmingham",
        "year_published": 2018,
        "min_players": 2,
        "max_players": 4,
        "playtime": 120,
        "rating": 8.5,
        "rating": 8.5,
        "difficulty": 3.87,
        "language_dependency": "없음",
        "mechanisms": ["핸드 관리", "네트워크 및 경로 구축"],
        "categories": ["산업 / 제조", "경제"],
        "designers": ["Martin Wallace"],
        "publishers": ["Roxley"],
        "description_ko": "...",
        "one_liner": "전략적인 운하와 철도 건설로...",
        "image_url": "https://img.boardlife.co.kr/...",
        "thumbnail_url": "https://img.boardlife.co.kr/...",
        "bgg_id": "224517",
        "bgg_url": "https://boardgamegeek.com/boardgame/224517/...",
        "source_url": "https://boardlife.co.kr/game/8569",
    }
    """
    soup = BeautifulSoup(html, "html.parser")
    game = {
        "boardlife_id": boardlife_id,
        "source_url": f"https://boardlife.co.kr/game/{boardlife_id}",
    }

    # ---- 1. JSON-LD (Schema.org) 데이터 추출 ----
    # 가장 신뢰할 수 있는 구조화 데이터
    json_ld = _extract_json_ld(soup)

    if json_ld:
        # 평점
        agg_rating = json_ld.get("aggregateRating", {})
        if agg_rating:
            game["rating"] = _safe_float(agg_rating.get("ratingValue"))
            game["review_count"] = _safe_int(agg_rating.get("reviewCount"))

        # 인원수 (numberOfPlayers)
        players = json_ld.get("numberOfPlayers", {})
        if players:
            game["min_players"] = _safe_int(players.get("minValue"))
            game["max_players"] = _safe_int(players.get("maxValue"))

        # 플레이 시간
        playtime = json_ld.get("playTime", {})
        if playtime:
            min_time = _safe_int(playtime.get("minValue"))
            max_time = _safe_int(playtime.get("maxValue"))
            # 최대 시간을 대표값으로 사용
            game["playtime"] = max_time or min_time

        # 이미지
        image = json_ld.get("image", "")
        if image and "ImgNoImage" not in image:
            game["image_url"] = image

    # ---- 2. HTML에서 텍스트 기반 데이터 추출 ----
    page_text = soup.get_text(separator="\n", strip=True)

    # 게임 이름 (한국어)
    game["name_ko"] = _extract_title_ko(soup, page_text)

    # 게임 이름 (영어)
    game["name_en"] = _extract_title_en(soup, page_text)

    # 출판 연도
    game["year_published"] = _extract_year(page_text)

    # 난이도 (무게)
    game["difficulty"] = _extract_difficulty(page_text)

    # 언어 의존도
    game["language_dependency"] = _extract_language_dep(page_text)

    # 메카니즘, 카테고리, 테마
    # 보드라이프 URL 패턴: /info/mechanisms/, /info/category/, /info/theme/
    game["mechanisms"] = _extract_info_list(soup, "mechanisms")
    game["categories"] = _extract_info_list(soup, "category")
    # 디자이너, 퍼블리셔
    game["designers"] = _extract_info_list(soup, "designer")
    game["publishers"] = _extract_info_list(soup, "publishers")

    # 게임 설명
    game["description_ko"] = _extract_description(soup, page_text)

    # 한줄 소개: description_ko 첫 문장 사용
    game["one_liner"] = _extract_one_liner(soup, page_text)
    if not game["one_liner"] and game.get("description_ko"):
        # 첫 문장 추출 (마침표/느낌표 기준)
        match = re.match(r"^(.+?[.!?])\s", game["description_ko"])
        if match and len(match.group(1)) <= 150:
            game["one_liner"] = match.group(1)

    # 이미지 URL (JSON-LD에서 못 가져온 경우 HTML에서)
    if not game.get("image_url"):
        game["image_url"] = _extract_image(soup, boardlife_id)

    # 썸네일 URL (이미지 URL에서 _w100 버전)
    if game.get("image_url"):
        game["thumbnail_url"] = re.sub(
            r"_w\d+\.", "_w100.", game["image_url"]
        )

    # BGG 연동 정보
    bgg_link = soup.find("a", href=re.compile(r"boardgamegeek\.com/boardgame/\d+"))
    if bgg_link:
        game["bgg_url"] = bgg_link["href"]
        bgg_match = re.search(r"/boardgame/(\d+)", bgg_link["href"])
        if bgg_match:
            game["bgg_id"] = bgg_match.group(1)

    return game


# ============================================================
# 내부 헬퍼 함수들
# ============================================================
def _extract_json_ld(soup: BeautifulSoup) -> dict | None:
    """페이지에서 Product 타입 JSON-LD 추출"""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            # Product 타입 찾기 (게임 상세 정보)
            if data.get("@type") == "Product":
                return data
            # 배열인 경우
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") == "Product":
                        return item
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def _extract_title_ko(soup: BeautifulSoup, text: str) -> str:
    """한국어 게임 제목 추출"""
    # id="boardgame-title" 또는 class="boardgame-title-text"
    title_el = soup.find(id="boardgame-title")
    if title_el:
        return title_el.get_text(strip=True)

    title_el = soup.find(class_="boardgame-title-text")
    if title_el:
        return title_el.get_text(strip=True)

    # og:title 메타 태그
    og_title = soup.find("meta", property="og:title")
    if og_title:
        title = og_title.get("content", "")
        # "브라스: 버밍엄 보드게임" → "브라스: 버밍엄"
        title = re.sub(r"\s*보드게임\s*$", "", title)
        return title

    return ""


def _extract_title_en(soup: BeautifulSoup, text: str) -> str:
    """영어 게임 제목 추출"""
    # JSON-LD에서 name 필드 확인
    json_ld = _extract_json_ld(soup)
    if json_ld:
        name = json_ld.get("name", "")
        # JSON-LD의 name이 영어인 경우
        if name and re.match(r'^[A-Za-z0-9:&\-\s\'.!,()]+$', name):
            return name

    # og:title에서 추출 시도
    og_title = soup.find("meta", property="og:title")
    if og_title:
        title = og_title.get("content", "")
        # "브라스: 버밍엄 보드게임" 같은 패턴에서 영어 이름 추출은 어려움
        # 영어만 있으면 사용
        clean = re.sub(r"\s*보드게임\s*$", "", title)
        if re.match(r'^[A-Za-z0-9:&\-\s\'.!,()]+$', clean):
            return clean

    # 페이지 텍스트에서 영어 제목 패턴 찾기
    # 한국어 제목 바로 다음에 오는 영어 라인
    lines = text.split("\n")
    for i, line in enumerate(lines):
        line = line.strip()
        # 영어 + 최소 4글자 + 숫자로만 된 것 제외 (평점 등)
        if (re.match(r'^[A-Za-z][A-Za-z0-9:&\-\s\'.!,()]+$', line)
                and len(line) >= 4
                and not re.match(r'^[\d.]+$', line)):
            # 메뉴 항목이나 일반 텍스트 제외
            skip_words = {"home", "login", "menu", "search", "boardlife",
                         "best", "all", "play", "rank", "info", "explore",
                         "record", "advanced", "rate", "bgg", "credits",
                         "share", "save", "like", "view", "edit", "delete",
                         "prev", "next", "page", "top", "bottom", "close"}
            if line.lower() not in skip_words:
                return line

    return ""


def _extract_year(text: str) -> int | None:
    """출판 연도 추출"""
    # "2018년" 패턴
    match = re.search(r"(\d{4})년", text)
    if match:
        year = int(match.group(1))
        if 1900 <= year <= 2030:
            return year
    return None


def _extract_age(text: str) -> int | None:
    """추천 연령 추출"""
    # "14세 이상" 패턴
    match = re.search(r"(\d+)세\s*이상", text)
    if match:
        return int(match.group(1))
    return None


def _extract_difficulty(text: str) -> float | None:
    """난이도 수치 추출 (1.0~5.0 범위)"""
    # 난이도 관련 텍스트 근처의 소수점 숫자
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "난이도" in line or "무게" in line or "weight" in line.lower():
            # 이 줄이나 인접 줄에서 소수점 숫자 찾기
            search_text = "\n".join(lines[max(0, i-1):i+3])
            match = re.search(r"(\d+\.\d+)", search_text)
            if match:
                val = float(match.group(1))
                if 0.5 <= val <= 5.5:
                    return val

    # 전체 텍스트에서 난이도 패턴
    match = re.search(r"난이도[:\s]*(\d+\.?\d*)", text)
    if match:
        return float(match.group(1))

    return None


def _extract_language_dep(text: str) -> str | None:
    """언어 의존도 추출"""
    # "없음", "약간", "보통", "많음" 등
    match = re.search(r"언어\s*의존도[:\s]*(없음|약간|보통|많음|매우 많음)", text)
    if match:
        return match.group(1)

    # 영어 표기
    if "Language Independent" in text:
        return "없음"

    return None


def _extract_info_list(soup: BeautifulSoup, info_type: str) -> list[str]:
    """
    메카니즘/카테고리/테마/디자이너/퍼블리셔 목록 추출

    보드라이프의 링크 패턴: /info/{type}/{value}
    예: /info/mechanisms/핸드 관리
    """
    items = []

    # /info/{type}/ 패턴의 링크에서 텍스트 추출
    for link in soup.find_all("a", href=re.compile(rf"/info/{info_type}/")):
        text = link.get_text(strip=True)
        if text and text not in items:
            items.append(text)

    return items


def _extract_description(soup: BeautifulSoup, text: str) -> str | None:
    """게임 설명 텍스트 추출"""
    # 1. 본문에서 "게임 설명" 또는 "설명글" 섹션 찾기
    for div in soup.find_all(["div", "section", "article"]):
        div_text = div.get_text(strip=True)
        if (len(div_text) > 100
                and "보드게임의 모든 정보를 한눈에" not in div_text
                and ("설명" in div_text[:20] or "소개" in div_text[:20])):
            # "게임 설명설명글" 등 접두사 제거
            desc = re.sub(r"^(게임\s*)?설명(글)?\s*(설명글)?\s*:?\s*", "", div_text).strip()
            # UI 텍스트 잘라내기 ("+ 더보기", "평가 ", "컬렉션" 등)
            desc = _clean_description(desc)
            if len(desc) > 50:
                return desc[:2000]

    # 2. 긴 텍스트 단락 찾기 (p 태그)
    for p in soup.find_all("p"):
        p_text = p.get_text(strip=True)
        if (len(p_text) > 100
                and "보드게임의 모든 정보를 한눈에" not in p_text):
            return _clean_description(p_text)[:2000]

    # 3. og:description 폴백 (마지막 수단)
    og_desc = soup.find("meta", property="og:description")
    if og_desc:
        desc = og_desc.get("content", "").strip()
        if desc and len(desc) > 10:
            return desc

    return None


def _clean_description(desc: str) -> str:
    """설명 텍스트에서 페이지 UI 텍스트 제거"""
    # 보드라이프 페이지의 반복되는 UI 패턴들
    cut_markers = [
        "+ 더보기",
        "평가  ",       # "평가  8.5 (630)" 패턴
        "컬렉션보유",
        "관련 게임",
        "정보편집",
        "카테고리전략",
        "카테고리가족",
        "카테고리파티",
        "테마게임테마",   # 카테고리/테마 섹션 시작
    ]
    for marker in cut_markers:
        idx = desc.find(marker)
        if idx > 50:  # 최소 50자 이후에 나타나는 경우만 자름
            desc = desc[:idx].strip()
    return desc


def _extract_one_liner(soup: BeautifulSoup, text: str) -> str | None:
    """한줄 소개 추출 (짧은 설명)"""
    # JSON-LD에서 description 필드 확인
    json_ld = _extract_json_ld(soup)
    if json_ld:
        desc = json_ld.get("description", "")
        # 보일러플레이트 제외 ("모든 정보를 한눈에", "보드게임 종합" 등)
        if (desc and len(desc) > 5
                and "모든 정보를 한눈에" not in desc
                and "보드게임 종합" not in desc):
            match = re.match(r"^([^.!?]+[.!?])", desc)
            if match:
                return match.group(1).strip()
            if len(desc) <= 100:
                return desc

    # 게임 설명의 첫 문장을 한줄 소개로 사용 (description_ko에서 파생)
    # _extract_description가 먼저 호출되므로, 여기서는 None 반환하고
    # parse_game_detail에서 description_ko 첫 문장으로 대체
    return None


def _extract_image(soup: BeautifulSoup, boardlife_id: str) -> str | None:
    """게임 커버 이미지 URL 추출"""
    # og:image 메타 태그
    og_image = soup.find("meta", property="og:image")
    if og_image:
        url = og_image.get("content", "")
        if url and "ImgNoImage" not in url:
            return url

    # img.boardlife.co.kr 도메인의 이미지
    for img in soup.find_all("img", src=re.compile(r"img\.boardlife\.co\.kr")):
        src = img.get("src", "")
        if "ImgNoImage" not in src:
            return src

    return None


def _safe_float(val, default=None):
    """안전한 float 변환"""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=None):
    """안전한 int 변환"""
    if val is None:
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


# ============================================================
# 단일 페이지 테스트
# ============================================================
async def test_single_game():
    """게임 1개를 크롤링해서 파서 테스트"""
    import httpx
    import sys
    import io

    # Windows 콘솔 인코딩 문제 방지
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    test_id = "8569"  # 브라스: 버밍엄
    url = f"https://boardlife.co.kr/game/{test_id}"

    print(f"테스트 대상: {url}")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    result = parse_game_detail(resp.text, test_id)

    if result:
        print("\n파싱 결과:")
        print("-" * 40)
        for key, value in result.items():
            if isinstance(value, list):
                print(f"  {key}: {value}")
            elif isinstance(value, str) and len(value) > 80:
                print(f"  {key}: {value[:80]}...")
            else:
                print(f"  {key}: {value}")

        # 필드 완성도 체크
        print("\n" + "-" * 40)
        print("필드 완성도:")
        fields = ["name_ko", "name_en", "year_published", "min_players",
                   "max_players", "playtime", "rating",
                   "difficulty", "mechanisms", "categories",
                   "designers", "publishers", "description_ko", "image_url"]
        filled = sum(1 for f in fields if result.get(f))
        print(f"  {filled}/{len(fields)} 필드 채워짐")
        empty = [f for f in fields if not result.get(f)]
        if empty:
            print(f"  비어있는 필드: {empty}")
    else:
        print("파싱 실패!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_single_game())
