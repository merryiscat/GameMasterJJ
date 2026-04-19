"""
LangGraph 파이프라인 State 정의

모든 노드가 공유하는 상태 객체.
sources, errors는 Annotated[list, operator.add]로
병렬 노드 결과를 자동 합산한다.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class SourceData(TypedDict, total=False):
    """소스 1건의 수집 + 파싱 결과"""
    source_type: str                    # "pdf" | "namuwiki" | "youtube" | "web"
    source_id: int | None               # game_rule_sources.id (DB 저장 후)
    raw_content: str                    # 수집된 텍스트
    language: str                       # "ko" | "en"
    metadata: dict                      # 소스별 메타데이터
    parsed_sections: dict[str, str]     # 12섹션 파싱 결과


class ComponentImage(TypedDict, total=False):
    """추출된 컴포넌트 이미지 1건"""
    page_num: int                       # PDF 페이지 번호
    image_index: int                    # 페이지 내 이미지 인덱스
    image_path: str                     # 저장 경로 (예: "data/images/components/game_1/p0_i3.png")
    label: str                          # VLM 분류 라벨 (예: "coal_token")
    category: str                       # "token" | "card" | "board" | "meeple" | "tile" | "other"
    description: str                    # 한국어 설명
    width: int
    height: int


class ReviewFeedback(TypedDict, total=False):
    """리뷰어 피드백"""
    passed: bool                        # 통과 여부
    overall_score: float                # 0.0 ~ 1.0
    issues: list[dict]                  # [{"section": "...", "severity": "critical|minor", "issue": "...", "suggestion": "..."}]


class PipelineState(TypedDict, total=False):
    """LangGraph 전체 State"""

    # ---- 입력 (init_node에서 설정) ----
    rule_id: int                        # game_rules.id
    game_id: int                        # games.id
    game_name: str                      # games.name_ko
    player_range: str                   # "2~4인"
    pdf_file_path: str | None           # PDF 파일 경로 (이미지 추출용)

    # ---- 수집된 소스 (병렬 노드가 각각 추가, operator.add로 자동 합산) ----
    sources: Annotated[list[SourceData], operator.add]
    errors: Annotated[list[str], operator.add]

    # ---- 이미지 추출 결과 ----
    component_images: list[ComponentImage]

    # ---- 파싱/병합/리뷰 ----
    merged_sections: dict[str, str]     # 12섹션 통합 결과
    review_feedback: ReviewFeedback | None
    review_count: int                   # 리뷰 횟수 (최대 1)

    # ---- 산출물 ----
    playbook: list[dict]                # 플레이북 단계별
    qa_pairs: list[dict]                # QA 쌍

    # ---- 파이프라인 상태 ----
    status: str                         # "running" | "done" | "error"
