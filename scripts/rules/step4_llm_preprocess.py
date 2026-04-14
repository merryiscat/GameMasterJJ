"""
Step 4: LLM 전처리 - 섹션 정리 + 플레이북 생성

1) 각 섹션을 LLM으로 깔끔하게 다듬고 항목별 분리
2) 전체 섹션을 기반으로 게임 운영용 플레이북 생성
"""

import json
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

from scripts.rules.config import PREPROCESS_MODEL, PROMPTS_DIR
from scripts.rules import SECTIONS, SECTION_TO_COLUMN, SECTION_TO_EXTRA, db

load_dotenv()


def load_preprocess_prompt(game_name: str, section_name: str, section_text: str) -> str:
    """섹션 전처리 프롬프트 로드"""
    template = (PROMPTS_DIR / "preprocess_section.txt").read_text(encoding="utf-8")
    return (
        template
        .replace("{game_name}", game_name)
        .replace("{section_name}", section_name)
        .replace("{section_text}", section_text)
    )


def load_playbook_prompt(game_name: str, player_range: str, sections_json: str) -> str:
    """플레이북 생성 프롬프트 로드"""
    template = (PROMPTS_DIR / "generate_playbook.txt").read_text(encoding="utf-8")
    return (
        template
        .replace("{game_name}", game_name)
        .replace("{player_range}", player_range)
        .replace("{sections_json}", sections_json)
    )


def preprocess_section(
    client: OpenAI, game_name: str, section_name: str, section_text: str
) -> dict:
    """
    섹션 1개를 LLM으로 정리

    Returns:
        {"cleaned": "정리된 텍스트", "items": ["항목1", ...]}
    """
    if not section_text.strip():
        return {"cleaned": "", "items": []}

    prompt = load_preprocess_prompt(game_name, section_name, section_text)

    response = client.chat.completions.create(
        model=PREPROCESS_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    return json.loads(response.choices[0].message.content)


def generate_playbook(
    client: OpenAI, game_name: str, player_range: str, all_sections: dict
) -> list[dict]:
    """
    전체 섹션을 기반으로 플레이북 생성

    Returns:
        [{"step_order": 1, "phase": "setup", "title": "...", ...}, ...]
    """
    # 빈 섹션 제외하고 JSON으로 전달
    sections_for_prompt = {k: v for k, v in all_sections.items() if v.strip()}
    sections_json = json.dumps(sections_for_prompt, ensure_ascii=False, indent=2)

    prompt = load_playbook_prompt(game_name, player_range, sections_json)

    response = client.chat.completions.create(
        model=PREPROCESS_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    result = json.loads(response.choices[0].message.content)

    # 응답 형태에 따라 처리:
    # 1) [...] 배열 → 그대로 반환
    # 2) {"playbook": [...]} → 배열 꺼내기
    # 3) {"step_order": 1, ...} → 단일 객체를 배열로 감싸기
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        # 먼저 배열 값이 있는지 확인
        for v in result.values():
            if isinstance(v, list):
                return v
        # 배열이 없으면 단일 플레이북 스텝 객체일 수 있음
        if "step_order" in result or "title" in result:
            return [result]
    return []


def process_llm_preprocess(rule_id: int):
    """
    game_rule 1건에 대해 LLM 전처리 + 플레이북 생성

    1. 각 섹션을 LLM으로 정리 → game_rules에 덮어쓰기
    2. 정리된 섹션 기반으로 플레이북 생성 → game_playbooks 테이블
    """
    db.start_step(rule_id, "llm_preprocess")

    try:
        rule = db.get_rule(rule_id)
        game_id = rule["game_id"]

        # 게임 정보 조회
        sb = db.get_client()
        game = sb.table("games").select("name_ko, min_players, max_players").eq("id", game_id).execute()
        game_info = game.data[0] if game.data else {}
        game_name = game_info.get("name_ko", f"game_{game_id}")
        min_p = game_info.get("min_players", 2)
        max_p = game_info.get("max_players", 4)
        player_range = f"{min_p}~{max_p}인"

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # ---- 1단계: 섹션별 정리 ----
        print(f"  [전처리] {game_name} - 섹션 정리 중...")

        # 현재 저장된 섹션 데이터 수집
        current_sections = {}
        for section_name in SECTIONS:
            if section_name in SECTION_TO_COLUMN:
                col = SECTION_TO_COLUMN[section_name]
                current_sections[section_name] = rule.get(col, "") or ""
            else:
                extra = rule.get("extra_sections") or {}
                current_sections[section_name] = extra.get(section_name, "") or ""

        # 섹션별 LLM 전처리
        cleaned_sections = {}
        preprocessed_items = {}  # items 저장용

        for section_name in SECTIONS:
            text = current_sections.get(section_name, "")
            if not text.strip():
                cleaned_sections[section_name] = ""
                continue

            print(f"    {section_name}...", end=" ", flush=True)
            result = preprocess_section(client, game_name, section_name, text)
            cleaned_sections[section_name] = result.get("cleaned", text)

            # items가 있으면 저장 (구조화 섹션)
            items = result.get("items", [])
            if items:
                preprocessed_items[section_name] = items

            print("[OK]")
            time.sleep(0.5)  # API rate limit 방지

        # 정리된 섹션 DB 저장
        db.update_rule_sections(rule_id, cleaned_sections)

        # items 정보를 extra_sections에 추가 저장
        if preprocessed_items:
            rule = db.get_rule(rule_id)
            extra = rule.get("extra_sections") or {}
            extra["preprocessed_items"] = preprocessed_items
            db.update_rule(rule_id, {"extra_sections": extra})

        # ---- 2단계: 플레이북 생성 ----
        print(f"  [전처리] 플레이북 생성 중...")

        playbook = generate_playbook(client, game_name, player_range, cleaned_sections)

        if playbook:
            db.save_playbook(game_id, rule_id, playbook)
            print(f"  [전처리] 플레이북 {len(playbook)}단계 생성 완료")
        else:
            print(f"  [전처리] [WARN] 플레이북 생성 실패 (빈 결과)")

        # 완료
        db.update_rule(rule_id, {"status": "preprocessed"})
        log_msg = f"성공: 섹션 정리 + 플레이북 {len(playbook)}단계"
        db.finish_step(rule_id, "llm_preprocess", log_msg)

    except Exception as e:
        error_msg = f"전처리 실패: {e}"
        print(f"  [전처리] [ERROR] {error_msg}")
        db.fail_step(rule_id, "llm_preprocess", error_msg)
        raise
