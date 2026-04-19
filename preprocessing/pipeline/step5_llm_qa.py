"""
Step 5: QA 생성 - 섹션 기반 Q&A 쌍 생성

정리된 섹션을 읽고, 실제 유저가 물어볼 만한
자연스러운 Q&A 쌍을 LLM으로 생성.
"""

import json
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

from preprocessing.pipeline.config import QA_MODEL, PROMPTS_DIR
from preprocessing.pipeline import SECTIONS, SECTION_TO_COLUMN, db

load_dotenv()


def load_qa_prompt(game_name: str, section_name: str, section_text: str) -> str:
    """QA 생성 프롬프트 로드"""
    template = (PROMPTS_DIR / "generate_qa.txt").read_text(encoding="utf-8")
    return (
        template
        .replace("{game_name}", game_name)
        .replace("{section_name}", section_name)
        .replace("{section_text}", section_text)
    )


def generate_qa_for_section(
    client: OpenAI, game_name: str, section_name: str, section_text: str
) -> list[dict]:
    """
    섹션 1개에 대해 Q&A 쌍 생성

    Returns:
        [{"question": "...", "answer": "..."}, ...]
    """
    if not section_text.strip():
        return []

    prompt = load_qa_prompt(game_name, section_name, section_text)

    response = client.chat.completions.create(
        model=QA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    result = json.loads(response.choices[0].message.content)

    # 응답 형태에 따라 처리:
    # 1) [...] 배열
    # 2) {"qa_pairs": [...]} 딕셔너리 안 배열
    # 3) {"question": "...", "answer": "..."} 단일 객체
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        for v in result.values():
            if isinstance(v, list):
                return v
        # 단일 QA 객체
        if "question" in result and "answer" in result:
            return [result]
    return []


def process_llm_qa(rule_id: int):
    """
    game_rule 1건에 대해 전체 섹션의 Q&A 쌍 생성

    각 섹션별로 Q&A를 생성하고, 전체를 합쳐서
    game_rules.extra_sections.qa_pairs에 저장.
    """
    db.start_step(rule_id, "llm_qa")

    try:
        rule = db.get_rule(rule_id)
        game_id = rule["game_id"]

        # 게임 이름 조회
        sb = db.get_client()
        game = sb.table("games").select("name_ko").eq("id", game_id).execute()
        game_name = game.data[0]["name_ko"] if game.data else f"game_{game_id}"

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        print(f"  [QA] {game_name} - Q&A 쌍 생성 중...")

        # 현재 저장된 섹션 데이터 수집
        all_qa_pairs = []
        extra = rule.get("extra_sections") or {}

        for section_name in SECTIONS:
            # 섹션 텍스트 가져오기
            if section_name in SECTION_TO_COLUMN:
                col = SECTION_TO_COLUMN[section_name]
                text = rule.get(col, "") or ""
            else:
                text = extra.get(section_name, "") or ""

            if not text.strip():
                continue

            print(f"    {section_name}...", end=" ", flush=True)

            qa_pairs = generate_qa_for_section(
                client, game_name, section_name, text
            )

            # 각 QA에 섹션 정보 추가 (나중에 메타데이터로 활용)
            for qa in qa_pairs:
                qa["section"] = section_name

            all_qa_pairs.extend(qa_pairs)
            print(f"{len(qa_pairs)}개 [OK]")
            time.sleep(0.5)  # API rate limit 방지

        # DB 저장
        db.save_qa_pairs(rule_id, all_qa_pairs)
        db.update_rule(rule_id, {"status": "qa_done"})

        log_msg = f"성공: 총 {len(all_qa_pairs)}개 Q&A 쌍 생성"
        print(f"  [QA] {log_msg}")
        db.finish_step(rule_id, "llm_qa", log_msg)

    except Exception as e:
        error_msg = f"QA 생성 실패: {e}"
        print(f"  [QA] [ERROR] {error_msg}")
        db.fail_step(rule_id, "llm_qa", error_msg)
        raise
