"""
소스별 수집 모듈

각 collector는 collect(source_row: dict) -> str 함수를 제공.
source_row는 game_rule_sources 테이블의 1행.
반환값은 추출된 텍스트.
"""

# 소스 타입 → 우선순위 매핑
SOURCE_PRIORITY = {
    "pdf": 1,
    "namuwiki": 2,
    "youtube": 3,
    "blog": 4,
}
