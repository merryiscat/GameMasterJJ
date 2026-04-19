"""
LangGraph 그래프 빌드

멀티에이전트 파이프라인의 전체 실행 흐름을 정의.
병렬 수집 → 번역 → 파싱+이미지 추출 → 통합 → 리뷰 → 산출물 → 벡터화
"""

from langgraph.graph import StateGraph, START, END

from preprocessing.pipeline import db
from preprocessing.agents.state import PipelineState

# 노드 함수 import
from preprocessing.agents.nodes.init_node import init_node
from preprocessing.agents.nodes.collect_nodes import (
    collect_pdf,
    collect_namuwiki,
    collect_youtube,
    collect_web,
)
from preprocessing.agents.nodes.translate_node import translate_node
from preprocessing.agents.nodes.parse_node import parse_node
from preprocessing.agents.nodes.image_node import extract_images_node
from preprocessing.agents.nodes.merge_node import merge_node
from preprocessing.agents.nodes.review_node import review_node
from preprocessing.agents.nodes.revise_node import revise_node
from preprocessing.agents.nodes.output_nodes import (
    playbook_node,
    qa_node,
    finalize_images_node,
)
from preprocessing.agents.nodes.vectorize_node import vectorize_node


def _save_results(state: PipelineState) -> dict:
    """
    최종 결과를 DB에 저장.
    - game_rules 섹션 업데이트
    - game_playbooks 저장
    - QA 쌍 저장
    - 상태 완료 처리
    """
    rule_id = state["rule_id"]
    game_id = state["game_id"]
    game_name = state["game_name"]

    print(f"  [save] {game_name} - 결과 저장 중...")

    merged = state.get("merged_sections", {})
    playbook = state.get("playbook", [])
    qa_pairs = state.get("qa_pairs", [])

    # 1. 섹션 저장
    db.update_rule_sections(rule_id, merged)
    db.update_rule(rule_id, {"status": "vectorized"})

    # 2. 플레이북 저장
    if playbook:
        db.save_playbook(game_id, rule_id, playbook)

    # 3. QA 쌍 저장
    if qa_pairs:
        db.save_qa_pairs(rule_id, qa_pairs)

    # 에러 로그 저장
    errors = state.get("errors", [])
    if errors:
        rule = db.get_rule(rule_id)
        extra = rule.get("extra_sections") or {}
        extra["pipeline_errors"] = errors
        db.update_rule(rule_id, {"extra_sections": extra})

    filled = sum(1 for v in merged.values() if v.strip())
    print(f"  [save] 완료: {filled}/12 섹션, 플레이북 {len(playbook)}단계, QA {len(qa_pairs)}쌍")

    return {"status": "done"}


def _route_collectors(state: PipelineState) -> list[str]:
    """
    초기화 후 어떤 수집 노드를 실행할지 결정.
    등록된 소스 타입에 따라 분기하되, 유튜브/웹은 항상 포함.
    """
    rule_id = state["rule_id"]
    sources = db.get_rule_sources(rule_id)
    source_types = {s["source_type"] for s in sources}

    routes = []

    # PDF 소스가 등록되어 있으면 수집
    if "pdf" in source_types:
        routes.append("collect_pdf")

    # 나무위키 소스가 등록되어 있으면 수집
    if "namuwiki" in source_types:
        routes.append("collect_namuwiki")

    # 유튜브/웹은 자동검색이 있으므로 항상 포함
    routes.append("collect_youtube")
    routes.append("collect_web")

    return routes


def _route_after_review(state: PipelineState) -> list[str]:
    """
    리뷰 결과에 따라 분기.
    - 통과 또는 이미 1회 리뷰 완료 → 산출물 생성 (3개 병렬)
    - 미통과 & 첫 리뷰 → 수정

    리스트를 반환하면 LangGraph가 병렬 Fan-out으로 처리한다.
    """
    feedback = state.get("review_feedback")
    review_count = state.get("review_count", 0)

    # 통과 또는 이미 1회 리뷰 완료 → 산출물 3개 병렬
    if feedback and (feedback.get("passed", True) or review_count >= 2):
        return ["playbook", "qa_gen", "finalize_images"]

    # 미통과 & 첫 리뷰 → 수정
    return ["revise"]


def build_graph() -> StateGraph:
    """LangGraph 파이프라인 그래프 빌드 + 컴파일"""

    builder = StateGraph(PipelineState)

    # ============================================================
    # 노드 등록
    # ============================================================
    builder.add_node("init", init_node)

    # 수집 (병렬)
    builder.add_node("collect_pdf", collect_pdf)
    builder.add_node("collect_namuwiki", collect_namuwiki)
    builder.add_node("collect_youtube", collect_youtube)
    builder.add_node("collect_web", collect_web)

    # 번역
    builder.add_node("translate", translate_node)

    # 파싱 + 이미지 추출 (병렬)
    builder.add_node("parse", parse_node)
    builder.add_node("extract_images", extract_images_node)

    # 통합 + 리뷰
    builder.add_node("merge", merge_node)
    builder.add_node("review", review_node)
    builder.add_node("revise", revise_node)

    # 산출물 (병렬)
    builder.add_node("playbook", playbook_node)
    builder.add_node("qa_gen", qa_node)
    builder.add_node("finalize_images", finalize_images_node)

    # 벡터화 + 저장
    builder.add_node("vectorize", vectorize_node)
    builder.add_node("save_results", _save_results)

    # ============================================================
    # 엣지 정의
    # ============================================================

    # START → init
    builder.add_edge(START, "init")

    # init → 병렬 수집 (조건부 Fan-out)
    builder.add_conditional_edges(
        "init",
        _route_collectors,
        path_map=["collect_pdf", "collect_namuwiki", "collect_youtube", "collect_web"],
    )

    # 병렬 수집 → translate (Fan-in)
    builder.add_edge("collect_pdf", "translate")
    builder.add_edge("collect_namuwiki", "translate")
    builder.add_edge("collect_youtube", "translate")
    builder.add_edge("collect_web", "translate")

    # translate → 파싱 + 이미지 추출 (병렬 Fork)
    builder.add_edge("translate", "parse")
    builder.add_edge("translate", "extract_images")

    # 파싱 + 이미지 → merge (Join)
    builder.add_edge("parse", "merge")
    builder.add_edge("extract_images", "merge")

    # merge → review
    builder.add_edge("merge", "review")

    # review → 조건부 분기
    # 리스트 반환: 통과 시 ["playbook", "qa_gen", "finalize_images"] 병렬
    #              미통과 시 ["revise"] 단독
    builder.add_conditional_edges(
        "review",
        _route_after_review,
        path_map=["playbook", "qa_gen", "finalize_images", "revise"],
    )

    # revise → review (피드백 1회 루프)
    builder.add_edge("revise", "review")

    # 산출물 → vectorize (Join)
    builder.add_edge("playbook", "vectorize")
    builder.add_edge("qa_gen", "vectorize")
    builder.add_edge("finalize_images", "vectorize")

    # vectorize → save → END
    builder.add_edge("vectorize", "save_results")
    builder.add_edge("save_results", END)

    # ============================================================
    # 컴파일
    # ============================================================
    return builder.compile()
