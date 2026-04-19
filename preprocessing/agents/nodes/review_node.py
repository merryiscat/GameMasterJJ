"""
검증 노드 (Reviewer)

통합된 12섹션 룰북의 품질을 검증.
완전성, 일관성, 명확성, 실용성을 평가하고
이슈 목록과 점수를 반환한다.
"""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from preprocessing.pipeline.config import REVIEW_MODEL, AGENT_PROMPTS_DIR
from preprocessing.pipeline import SECTIONS
from preprocessing.agents.state import PipelineState

load_dotenv()


def review_node(state: PipelineState) -> dict:
    """
    merged_sections 전체를 검토하여 ReviewFeedback 생성.
    review_count를 1 증가시킨다.
    """
    merged = state.get("merged_sections", {})
    game_name = state["game_name"]
    review_count = state.get("review_count", 0)

    print(f"  [review] {game_name} - 룰북 품질 검증 (#{review_count + 1})")

    # 12섹션 텍스트 구성
    sections_text = ""
    for section_name in SECTIONS:
        text = merged.get(section_name, "")
        if text.strip():
            sections_text += f"\n### {section_name}\n{text}\n"
        else:
            sections_text += f"\n### {section_name}\n(내용 없음)\n"

    # 리뷰 프롬프트 로드
    template = (AGENT_PROMPTS_DIR / "review_rulebook.txt").read_text(encoding="utf-8")
    prompt = (
        template
        .replace("{game_name}", game_name)
        .replace("{sections_text}", sections_text)
    )

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=REVIEW_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    result = json.loads(response.choices[0].message.content)

    # ReviewFeedback 구성
    feedback = {
        "passed": result.get("passed", True),
        "overall_score": result.get("overall_score", 0.8),
        "issues": result.get("issues", []),
    }

    summary = result.get("summary", "")
    score = feedback["overall_score"]
    issue_count = len(feedback["issues"])
    critical_count = sum(1 for i in feedback["issues"] if i.get("severity") == "critical")

    status = "PASS" if feedback["passed"] else "FAIL"
    print(f"  [review] {status} (점수: {score:.2f}, 이슈: {issue_count}건, critical: {critical_count}건)")
    if summary:
        print(f"  [review] {summary}")

    return {
        "review_feedback": feedback,
        "review_count": review_count + 1,
    }
