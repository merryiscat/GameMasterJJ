"""
수정 노드

리뷰어 피드백을 반영하여 문제 있는 섹션만 재작성.
revise 후 merge_node로 복귀하지 않고,
merged_sections를 직접 수정하여 다음 단계로 진행한다.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

from preprocessing.pipeline.config import REVISE_MODEL, AGENT_PROMPTS_DIR
from preprocessing.agents.state import PipelineState

load_dotenv()


def revise_node(state: PipelineState) -> dict:
    """
    review_feedback의 issues를 반영하여 해당 섹션만 LLM으로 재작성.
    """
    feedback = state.get("review_feedback")
    merged = state.get("merged_sections", {})
    game_name = state["game_name"]

    if not feedback or feedback.get("passed", True):
        print("  [revise] 피드백 없음 또는 통과 (skip)")
        return {}

    issues = feedback.get("issues", [])
    if not issues:
        print("  [revise] 이슈 없음 (skip)")
        return {}

    print(f"  [revise] {game_name} - {len(issues)}건 이슈 수정")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    template = (AGENT_PROMPTS_DIR / "revise_section.txt").read_text(encoding="utf-8")

    # 같은 섹션에 여러 이슈가 있으면 합쳐서 한 번에 수정
    # (개별 수정하면 이전 수정이 덮어써지는 문제 방지)
    issues_by_section: dict[str, list[dict]] = {}
    for issue in issues:
        section_name = issue.get("section", "")
        if section_name and section_name in merged:
            issues_by_section.setdefault(section_name, []).append(issue)

    updated_sections = {**merged}

    for section_name, section_issues in issues_by_section.items():
        current_text = updated_sections.get(section_name, "")
        if not current_text.strip():
            continue

        # 이슈 목록을 하나의 피드백 텍스트로 합침
        feedback_lines = []
        for i, issue in enumerate(section_issues, 1):
            severity = issue.get("severity", "minor")
            issue_text = issue.get("issue", "")
            suggestion = issue.get("suggestion", "")
            feedback_lines.append(
                f"{i}. [{severity}] {issue_text}\n   제안: {suggestion}"
            )
        combined_feedback = "\n".join(feedback_lines)

        severity_summary = ", ".join(
            f"{iss.get('severity', 'minor')}" for iss in section_issues
        )
        print(f"    {section_name} [{severity_summary}]...", end=" ", flush=True)

        prompt = (
            template
            .replace("{game_name}", game_name)
            .replace("{section_name}", section_name)
            .replace("{severity}", severity_summary)
            .replace("{issue}", combined_feedback)
            .replace("{suggestion}", "위 모든 피드백을 종합적으로 반영하세요.")
            .replace("{section_text}", current_text)
        )

        response = client.chat.completions.create(
            model=REVISE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        revised = response.choices[0].message.content.strip()
        updated_sections[section_name] = revised
        print(f"{len(revised)}자 [OK]")

    return {"merged_sections": updated_sections}
