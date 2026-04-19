"""
산출물 생성 노드 3개 (병렬 실행)

1. playbook_node: 플레이북 생성 (기존 step4 재사용)
2. qa_node: QA 쌍 생성 (기존 step5 재사용)
3. finalize_images_node: 이미지 메타데이터 DB 저장
"""

import os
import time

from dotenv import load_dotenv
from openai import OpenAI

from preprocessing.pipeline.config import PREPROCESS_MODEL
from preprocessing.pipeline import SECTIONS
from preprocessing.pipeline.step4_llm_preprocess import (
    generate_playbook,
    preprocess_section,
)
from preprocessing.pipeline.step5_llm_qa import generate_qa_for_section
from preprocessing.pipeline import db
from preprocessing.agents.state import PipelineState

load_dotenv()


def playbook_node(state: PipelineState) -> dict:
    """
    정리된 섹션 기반 플레이북 생성.
    기존 step4의 generate_playbook() 재사용.
    """
    merged = state.get("merged_sections", {})
    game_name = state["game_name"]
    player_range = state.get("player_range", "2~4인")

    print(f"  [playbook] {game_name} - 플레이북 생성 중...")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    playbook = generate_playbook(client, game_name, player_range, merged)

    if playbook:
        print(f"  [playbook] {len(playbook)}단계 생성 완료")
    else:
        print(f"  [playbook] 생성 실패 (빈 결과)")

    return {"playbook": playbook or []}


def qa_node(state: PipelineState) -> dict:
    """
    각 섹션별 QA 쌍 생성.
    기존 step5의 generate_qa_for_section() 재사용.
    """
    merged = state.get("merged_sections", {})
    game_name = state["game_name"]

    print(f"  [qa] {game_name} - QA 쌍 생성 중...")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    all_qa_pairs = []

    for section_name in SECTIONS:
        text = merged.get(section_name, "")
        if not text.strip():
            continue

        print(f"    {section_name}...", end=" ", flush=True)
        qa_pairs = generate_qa_for_section(client, game_name, section_name, text)

        # 각 QA에 섹션 정보 추가
        for qa in qa_pairs:
            qa["section"] = section_name

        all_qa_pairs.extend(qa_pairs)
        print(f"{len(qa_pairs)}개 [OK]")
        time.sleep(0.5)

    print(f"  [qa] 총 {len(all_qa_pairs)}개 QA 쌍 생성 완료")

    return {"qa_pairs": all_qa_pairs}


def finalize_images_node(state: PipelineState) -> dict:
    """
    컴포넌트 이미지 메타데이터를 DB에 저장.
    extra_sections.component_images에 저장한다.
    """
    component_images = state.get("component_images", [])
    rule_id = state["rule_id"]

    if not component_images:
        print("  [images_save] 이미지 없음 (skip)")
        return {}

    print(f"  [images_save] {len(component_images)}개 이미지 메타데이터 저장")

    # b64 필드 제거 (DB에 저장할 필요 없음)
    clean_images = []
    for img in component_images:
        clean_img = {k: v for k, v in img.items() if k != "b64"}
        clean_images.append(clean_img)

    rule = db.get_rule(rule_id)
    extra = rule.get("extra_sections") or {}
    extra["component_images"] = clean_images
    db.update_rule(rule_id, {"extra_sections": extra})

    return {}
