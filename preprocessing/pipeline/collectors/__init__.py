"""
소스별 수집 모듈

각 collector는 collect(source_row: dict) -> dict 함수를 제공.
source_row는 game_rule_sources 테이블의 1행.

자동검색 모듈 (youtube_search, web_search)은
search_and_collect(game_name: str) -> dict | None 함수를 제공.
URL 없이 게임 이름만으로 검색+수집한다.
"""

# 소스 타입 → 우선순위 매핑
# 내용 충돌 시 우선순위가 높은(숫자 낮은) 소스를 기준으로 한다
SOURCE_PRIORITY = {
    "pdf": 1,          # 룰북 PDF OCR (가장 정확)
    "namuwiki": 2,     # 나무위키 (커뮤니티 정리, 한국어)
    "youtube": 3,      # 유튜브 자막 (룰 설명 영상)
    "web": 4,          # 웹 검색 (블로그, 웹페이지)
}
