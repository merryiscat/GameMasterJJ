"""
파싱 노드

각 소스를 12섹션으로 파싱.
PDF는 VLM(이미지+텍스트), 텍스트 소스는 텍스트만.
기존 step3_parse.py의 파싱 함수 재사용.
"""

import os
import time

from dotenv import load_dotenv
from openai import OpenAI

from preprocessing.pipeline.config import PROJECT_ROOT
from preprocessing.pipeline.step3_parse import (
    parse_source_text,
    parse_source_vlm,
    pdf_pages_to_images,
)
from preprocessing.pipeline import db
from preprocessing.agents.state import PipelineState

load_dotenv()


def parse_node(state: PipelineState) -> dict:
    """
    모든 소스를 12섹션으로 개별 파싱.
    결과는 각 소스의 parsed_sections에 저장 (in-place 수정).
    """
    sources = state.get("sources", [])
    if not sources:
        print("  [parse] 소스 없음 (skip)")
        return {}

    game_name = state["game_name"]
    rule_id = state["rule_id"]
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    print(f"  [parse] {game_name} - {len(sources)}개 소스 파싱")

    for src in sources:
        stype = src["source_type"]
        raw_content = src.get("raw_content", "")

        if not raw_content.strip():
            print(f"    {stype}: 내용 없음 (skip)")
            continue

        print(f"    {stype} ({len(raw_content)}자)...", end=" ", flush=True)

        try:
            # PDF는 VLM 파싱 (이미지 포함)
            if stype == "pdf" and state.get("pdf_file_path"):
                pdf_path = state["pdf_file_path"]
                page_images = pdf_pages_to_images(pdf_path)
                parsed = parse_source_vlm(client, game_name, raw_content, page_images)
            else:
                parsed = parse_source_text(client, game_name, raw_content)

            src["parsed_sections"] = parsed
            filled = sum(1 for v in parsed.values() if v.strip())
            print(f"{filled}/12 [OK]")
        except Exception as e:
            print(f"[ERROR] {e}")
            src["parsed_sections"] = {}

        time.sleep(0.5)  # API rate limit 방지

    return {}
