"""
Step 3: 멀티소스 섹션별 취합 파싱

1단계: 각 소스를 개별 파싱하여 12섹션으로 분리
2단계: 섹션별로 소스 간 취합 (PDF > 나무위키 > 유튜브 > 블로그 우선순위)

PDF 소스는 VLM(이미지+텍스트)으로 파싱하여 시각 정보도 활용.
"""

import base64
import json
import os
import time
from pathlib import Path

import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import OpenAI

from scripts.rules.config import PARSE_MODEL, PARSE_VLM_MODEL, PROMPTS_DIR, PROJECT_ROOT
from scripts.rules import SECTIONS, db

load_dotenv()


# ============================================================
# 이미지 유틸
# ============================================================
def pdf_pages_to_images(file_path: str, dpi: int = 150) -> list[str]:
    """PDF 각 페이지를 base64 PNG로 변환"""
    doc = fitz.open(file_path)
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        png_bytes = pix.tobytes("png")
        images.append(base64.b64encode(png_bytes).decode("utf-8"))
    doc.close()
    return images


def image_file_to_base64(file_path: str) -> str:
    """이미지 파일을 base64로 인코딩"""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ============================================================
# 1단계: 소스별 개별 파싱
# ============================================================
def _get_section_prompt() -> str:
    """12섹션 분리 프롬프트 (소스 1개용)"""
    return (
        "당신은 보드게임 룰북 분석 전문가입니다.\n"
        "아래 텍스트를 읽고 12개 표준 섹션으로 분류하여 JSON으로 출력하세요.\n"
        "각 섹션을 최대한 상세하게 작성하세요. 요약하지 말고 원문의 디테일을 보존하세요.\n"
        "해당 없는 섹션은 빈 문자열로 채우세요.\n\n"
        "12개 섹션:\n"
        "1. overview - 게임 소개 (테마, 목표)\n"
        "2. components - 구성품 목록\n"
        "3. setup - 기본 준비 과정\n"
        "4. setup_by_player - 인원별 세팅 차이\n"
        "5. turn_structure - 차례 구조 (턴/라운드/페이즈)\n"
        "6. actions - 턴에 할 수 있는 행동\n"
        "7. keywords - 키워드/용어 정의\n"
        "8. end_condition - 게임 종료 조건\n"
        "9. scoring - 점수 계산\n"
        "10. win_condition - 승리 조건\n"
        "11. special_rules - 변형/선택 규칙\n"
        "12. faq - FAQ, 자주 헷갈리는 상황\n"
    )


def parse_source_text(client: OpenAI, game_name: str, text: str) -> dict:
    """텍스트 소스 1개를 12섹션으로 파싱"""
    prompt = (
        _get_section_prompt()
        + f"\n## 게임: {game_name}\n\n## 텍스트:\n\n{text}"
    )

    response = client.chat.completions.create(
        model=PARSE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    result = json.loads(response.choices[0].message.content)
    for section in SECTIONS:
        if section not in result:
            result[section] = ""
    return result


def parse_source_vlm(
    client: OpenAI, game_name: str, text: str, page_images: list[str]
) -> dict:
    """PDF 소스를 VLM으로 파싱 (이미지+텍스트)"""
    content = []

    # VLM 안내
    content.append({
        "type": "text",
        "text": (
            "아래에 보드게임 룰북 페이지 이미지와 OCR 텍스트가 제공됩니다.\n"
            "이미지를 직접 확인하여 보드 배치도, 다이어그램 등 시각 정보를 반영하세요.\n"
            "특히 setup 섹션은 보드 배치 다이어그램을 참고하여 상세하게 작성하세요.\n\n"
        ),
    })

    # 페이지 이미지 (최대 20장)
    for i, img_b64 in enumerate(page_images[:20]):
        content.append({"type": "text", "text": f"--- 페이지 {i + 1} ---"})
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}", "detail": "high"},
        })

    # 텍스트 + 파싱 지시
    content.append({
        "type": "text",
        "text": _get_section_prompt() + f"\n## 게임: {game_name}\n\n## OCR 텍스트:\n\n{text}",
    })

    response = client.chat.completions.create(
        model=PARSE_VLM_MODEL,
        messages=[{"role": "user", "content": content}],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_completion_tokens=16000,
    )

    result = json.loads(response.choices[0].message.content)
    for section in SECTIONS:
        if section not in result:
            result[section] = ""
    return result


# ============================================================
# 2단계: 섹션별 취합
# ============================================================
def merge_section(
    client: OpenAI, game_name: str, section_name: str, source_texts: list[tuple[str, str]]
) -> str:
    """
    하나의 섹션에 대해 여러 소스를 우선순위대로 취합

    Args:
        source_texts: [(소스라벨, 텍스트), ...] 우선순위 순
    Returns:
        취합된 섹션 텍스트
    """
    # 비어있지 않은 소스만
    valid = [(label, text) for label, text in source_texts if text.strip()]

    if not valid:
        return ""

    # 소스 1개면 그대로 반환
    if len(valid) == 1:
        return valid[0][1]

    # 여러 소스 취합
    sources_text = ""
    for i, (label, text) in enumerate(valid):
        sources_text += f"\n[소스 {i+1} - {label}]\n{text}\n"

    prompt = (
        f"게임 '{game_name}'의 '{section_name}' 섹션에 대해 여러 소스가 있습니다.\n"
        f"이 소스들을 하나로 취합하여 가장 완전한 내용을 만들어 주세요.\n\n"
        f"규칙:\n"
        f"- 소스 1이 최우선 (공식 룰북). 정보 충돌 시 소스 1 기준.\n"
        f"- 소스 1에 없는 유용한 정보(팁, 예시, 자주 하는 실수 등)는 하위 소스에서 보충.\n"
        f"- 최대한 상세하게. 요약하지 말 것.\n"
        f"- 결과는 마크다운 텍스트로 출력 (JSON 아님).\n"
        f"{sources_text}"
    )

    response = client.chat.completions.create(
        model=PARSE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return response.choices[0].message.content.strip()


# ============================================================
# 메인 프로세스
# ============================================================
SOURCE_LABELS = {
    "pdf": "PDF 룰북 (공식)",
    "namuwiki": "나무위키 (커뮤니티)",
    "youtube": "유튜브 자막 (실전)",
    "blog": "블로그 (개인)",
}


def process_parse(rule_id: int):
    """
    멀티소스 섹션별 취합 파싱

    1단계: 각 소스를 개별 파싱 (12섹션)
    2단계: 섹션별로 소스 간 취합 (우선순위대로)
    """
    db.start_step(rule_id, "parse")

    try:
        rule = db.get_rule(rule_id)
        game_id = rule["game_id"]

        # 게임 이름
        sb = db.get_client()
        game = sb.table("games").select("name_ko").eq("id", game_id).execute()
        game_name = game.data[0]["name_ko"] if game.data else f"game_{game_id}"

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # 소스 목록 (우선순위 순)
        sources = db.get_rule_sources(rule_id)
        processed = [s for s in sources if s.get("status") == "processed" and s.get("raw_content")]

        if not processed:
            raise ValueError("수집된 소스가 없음")

        # ---- 1단계: 소스별 개별 파싱 ----
        print(f"  [파싱] {game_name} - 1단계: {len(processed)}개 소스 개별 파싱")

        parsed_by_source = []  # [(소스타입, 파싱결과dict), ...]

        for src in processed:
            stype = src["source_type"]
            label = SOURCE_LABELS.get(stype, stype)
            raw_content = src["raw_content"]

            print(f"    {stype} ({len(raw_content)}자)...", end=" ", flush=True)

            # PDF는 VLM 파싱 (이미지 포함)
            if stype == "pdf":
                source_file = src.get("source_file", "")
                page_images = []
                if source_file:
                    file_path = PROJECT_ROOT / source_file
                    if file_path.exists():
                        ext = file_path.suffix.lower()
                        if ext == ".pdf":
                            page_images = pdf_pages_to_images(str(file_path))
                        elif ext in (".png", ".jpg", ".jpeg", ".webp"):
                            page_images = [image_file_to_base64(str(file_path))]

                if page_images:
                    parsed = parse_source_vlm(client, game_name, raw_content, page_images)
                else:
                    parsed = parse_source_text(client, game_name, raw_content)
            else:
                parsed = parse_source_text(client, game_name, raw_content)

            filled = sum(1 for v in parsed.values() if v.strip())
            print(f"{filled}/12 [OK]")
            parsed_by_source.append((stype, parsed))
            time.sleep(0.5)

        # ---- 2단계: 섹션별 취합 ----
        print(f"  [파싱] 2단계: 섹션별 취합")

        merged_sections = {}

        for section_name in SECTIONS:
            # 우선순위 순으로 각 소스의 해당 섹션 텍스트 수집
            source_texts = []
            for stype, parsed in parsed_by_source:
                text = parsed.get(section_name, "")
                if text.strip():
                    label = SOURCE_LABELS.get(stype, stype)
                    source_texts.append((label, text))

            if not source_texts:
                merged_sections[section_name] = ""
                continue

            print(f"    {section_name} ({len(source_texts)}소스)...", end=" ", flush=True)

            merged = merge_section(client, game_name, section_name, source_texts)
            merged_sections[section_name] = merged
            print(f"{len(merged)}자 [OK]")
            time.sleep(0.3)

        # 결과 저장
        filled = sum(1 for v in merged_sections.values() if v.strip())
        total_chars = sum(len(v) for v in merged_sections.values())

        db.update_rule_sections(rule_id, merged_sections)
        db.update_rule(rule_id, {"status": "parsed"})

        log_msg = f"성공: {filled}/12 섹션, {total_chars}자, {len(processed)}소스 취합"
        print(f"  [파싱] {log_msg}")
        db.finish_step(rule_id, "parse", log_msg)

    except Exception as e:
        error_msg = f"파싱 실패: {e}"
        print(f"  [파싱] [ERROR] {error_msg}")
        db.fail_step(rule_id, "parse", error_msg)
        raise
