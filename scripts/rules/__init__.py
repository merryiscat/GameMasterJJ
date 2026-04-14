"""
룰 전처리 파이프라인 공통 상수

보드게임 룰북을 표준화된 섹션으로 분리하고,
QA 쌍 생성 + 벡터화까지 진행하는 파이프라인에서 사용하는 상수들.
"""

# ============================================================
# 12개 표준 섹션 이름
# 보드게임 룰북을 이 12개 섹션으로 나눠서 저장한다.
# ============================================================
SECTIONS = [
    "overview",         # 게임 소개 (테마, 목표, 한줄 요약)
    "components",       # 구성품 목록
    "setup",            # 기본 준비 과정
    "setup_by_player",  # 인원별 세팅 차이 (2인/3인/4인...)
    "turn_structure",   # 차례 구조 (턴/라운드/페이즈)
    "actions",          # 턴에 할 수 있는 행동 목록
    "keywords",         # 키워드/용어 정의 (카드 능력, 특수 효과 등)
    "end_condition",    # 게임 종료 조건
    "scoring",          # 점수 계산 방법
    "win_condition",    # 승리 조건
    "special_rules",    # 변형/선택 규칙, 확장 규칙
    "faq",              # FAQ, 자주 헷갈리는 상황
]

# ============================================================
# 6개 파이프라인 스텝 (실행 순서대로)
# ============================================================
STEPS = [
    "collect",          # 멀티소스 수집 (PDF OCR, 나무위키, 유튜브, 블로그)
    "translate",        # 외국어 → 한국어 번역 (ko면 skip)
    "parse",            # 멀티소스 취합 → 12개 섹션 분리 (VLM)
    "llm_preprocess",   # 섹션 정리 + 플레이북 생성 (LLM)
    "llm_qa",           # Q&A 쌍 생성 (LLM)
    "vectorize",        # ChromaDB 임베딩
]

# ============================================================
# 섹션 → game_rules 테이블 칼럼 매핑
# 기존 칼럼에 매핑되는 9개 섹션
# ============================================================
SECTION_TO_COLUMN = {
    "overview": "intro",
    "components": "components",
    "setup": "setup",
    "turn_structure": "gameplay",
    "end_condition": "end_condition",
    "scoring": "scoring",
    "win_condition": "win_condition",
    "special_rules": "special_rules",
    "faq": "faq",
}

# ============================================================
# extra_sections(jsonb)에 저장되는 섹션 3개
# game_rules 테이블에 칼럼이 없어서 jsonb로 저장
# ============================================================
SECTION_TO_EXTRA = [
    "setup_by_player",
    "actions",
    "keywords",
]
