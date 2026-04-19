"""
통합 편집 노드 (Merger)

여러 소스의 12섹션 파싱 결과를 하나로 통합.
리뷰 피드백이 있으면 반영하여 재작성.
컴포넌트 이미지 정보도 components 섹션에 반영.
"""

import os
import time

from dotenv import load_dotenv
from openai import OpenAI

from preprocessing.pipeline.config import MERGE_MODEL
from preprocessing.pipeline import SECTIONS
from preprocessing.pipeline.collectors import SOURCE_PRIORITY
from preprocessing.agents.state import PipelineState

load_dotenv()

# 소스 타입별 라벨 (머지 프롬프트에서 소스 구분용)
SOURCE_LABELS = {
    "pdf": "PDF 룰북 (공식)",
    "namuwiki": "나무위키 (커뮤니티)",
    "youtube": "유튜브 자막 (실전)",
    "web": "웹 검색 (블로그/게시판)",
}


def _merge_section(
    client: OpenAI,
    game_name: str,
    section_name: str,
    source_texts: list[tuple[str, str]],
    feedback_for_section: dict | None = None,
) -> str:
    """
    하나의 섹션에 대해 여러 소스를 통합.

    Args:
        source_texts: [(소스라벨, 텍스트), ...] 우선순위 순
        feedback_for_section: 리뷰 피드백 (있으면 반영)
    Returns:
        통합된 섹션 텍스트
    """
    # 비어있지 않은 소스만
    valid = [(label, text) for label, text in source_texts if text.strip()]
    if not valid:
        return ""

    # 소스 1개면 그대로 반환 (피드백 없으면)
    if len(valid) == 1 and not feedback_for_section:
        return valid[0][1]

    # 소스 텍스트 구성
    sources_text = ""
    for i, (label, text) in enumerate(valid):
        sources_text += f"\n[소스 {i+1} - {label}]\n{text}\n"

    # 기본 프롬프트
    prompt = (
        f"게임 '{game_name}'의 '{section_name}' 섹션에 대해 여러 소스가 있습니다.\n"
        f"이 소스들을 하나로 취합하여 가장 완전한 내용을 만들어 주세요.\n\n"
        f"규칙:\n"
        f"- 소스 1이 최우선 (공식 룰북). 정보 충돌 시 소스 1 기준.\n"
        f"- 소스 1에 없는 유용한 정보(팁, 예시, 자주 하는 실수 등)는 하위 소스에서 보충.\n"
        f"- 모호하거나 불명확한 표현은 구체적으로 풀어서 작성.\n"
        f"- 최대한 상세하게. 요약하지 말 것.\n"
        f"- 결과는 마크다운 텍스트로 출력 (JSON 아님).\n"
    )

    # 리뷰 피드백이 있으면 추가
    if feedback_for_section:
        issue = feedback_for_section.get("issue", "")
        suggestion = feedback_for_section.get("suggestion", "")
        prompt += (
            f"\n## 리뷰어 피드백 (반드시 반영)\n"
            f"- 문제점: {issue}\n"
            f"- 제안: {suggestion}\n"
            f"위 피드백을 반영하여 내용을 보완/수정하세요.\n"
        )

    prompt += sources_text

    response = client.chat.completions.create(
        model=MERGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return response.choices[0].message.content.strip()


def merge_node(state: PipelineState) -> dict:
    """
    모든 소스의 parsed_sections를 12섹션별로 통합.
    리뷰 피드백(revise 후 재진입)이 있으면 해당 섹션만 재작성.
    """
    sources = state.get("sources", [])
    if not sources:
        print("  [merge] 소스 없음 (skip)")
        return {"merged_sections": {}}

    game_name = state["game_name"]
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # 리뷰 피드백 확인 (revise_node에서 재진입한 경우)
    review_feedback = state.get("review_feedback")
    feedback_by_section = {}
    if review_feedback and not review_feedback.get("passed", True):
        for issue in review_feedback.get("issues", []):
            section = issue.get("section", "")
            if section:
                feedback_by_section[section] = issue

    # 소스를 우선순위 순으로 정렬
    sorted_sources = sorted(
        sources,
        key=lambda s: SOURCE_PRIORITY.get(s["source_type"], 99),
    )

    # 컴포넌트 이미지 정보 (components 섹션에 반영)
    component_images = state.get("component_images", [])
    image_text = ""
    if component_images:
        image_lines = []
        for img in component_images:
            image_lines.append(
                f"- {img.get('label', '?')}: {img.get('description', '')} "
                f"(카테고리: {img.get('category', '?')})"
            )
        image_text = "\n".join(image_lines)

    print(f"  [merge] {game_name} - {len(sorted_sources)}소스 통합")

    merged_sections = {}

    for section_name in SECTIONS:
        # 각 소스에서 해당 섹션 텍스트 수집
        source_texts = []
        for src in sorted_sources:
            parsed = src.get("parsed_sections", {})
            text = parsed.get(section_name, "")
            if text.strip():
                label = SOURCE_LABELS.get(src["source_type"], src["source_type"])
                source_texts.append((label, text))

        # components 섹션에 이미지 정보 추가
        if section_name == "components" and image_text:
            source_texts.append(("컴포넌트 이미지 분석", image_text))

        if not source_texts:
            merged_sections[section_name] = ""
            continue

        # 리뷰 피드백이 있는 섹션만 재작성, 없으면 기존 결과 유지
        existing = state.get("merged_sections", {}).get(section_name, "")
        feedback = feedback_by_section.get(section_name)

        if existing and not feedback:
            # 이미 머지 완료 + 피드백 없음 → 기존 결과 유지
            merged_sections[section_name] = existing
            continue

        print(f"    {section_name} ({len(source_texts)}소스)...", end=" ", flush=True)
        merged = _merge_section(
            client, game_name, section_name, source_texts,
            feedback_for_section=feedback,
        )
        merged_sections[section_name] = merged
        print(f"{len(merged)}자 [OK]")
        time.sleep(0.3)

    filled = sum(1 for v in merged_sections.values() if v.strip())
    total_chars = sum(len(v) for v in merged_sections.values())
    print(f"  [merge] 완료: {filled}/12 섹션, {total_chars}자")

    return {"merged_sections": merged_sections}
