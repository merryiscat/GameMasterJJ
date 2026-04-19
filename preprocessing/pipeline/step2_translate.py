"""
Step 2: 번역 - 외국어 → 한국어

language가 'ko'가 아닌 경우에만 실행.
한국어 룰북은 이 단계를 skip한다.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

from preprocessing.pipeline.config import TRANSLATE_MODEL, TRANSLATE_CHUNK_SIZE
from preprocessing.pipeline import db

load_dotenv()


def get_openai_client() -> OpenAI:
    """OpenAI 클라이언트 반환"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 .env에 없습니다.")
    return OpenAI(api_key=api_key)


def translate_text(text: str, source_lang: str) -> str:
    """
    텍스트를 한국어로 번역

    긴 텍스트는 TRANSLATE_CHUNK_SIZE 단위로 분할하여 순차 번역.
    마크다운 서식은 유지한다.

    Args:
        text: 번역할 텍스트
        source_lang: 원본 언어 코드 (예: 'en')

    Returns:
        한국어로 번역된 텍스트
    """
    client = get_openai_client()

    # 짧은 텍스트는 한번에 번역
    if len(text) <= TRANSLATE_CHUNK_SIZE:
        return _translate_chunk(client, text, source_lang)

    # 긴 텍스트는 분할 번역
    # 더블 줄바꿈(\n\n) 기준으로 문단 분리 후, 청크 단위로 묶기
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # 현재 청크에 문단 추가했을 때 크기 초과하면 새 청크 시작
        if len(current_chunk) + len(para) > TRANSLATE_CHUNK_SIZE and current_chunk:
            chunks.append(current_chunk)
            current_chunk = para
        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para

    if current_chunk:
        chunks.append(current_chunk)

    # 청크별 번역
    translated_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"    번역 중... ({i + 1}/{len(chunks)})")
        translated = _translate_chunk(client, chunk, source_lang)
        translated_chunks.append(translated)

    return "\n\n".join(translated_chunks)


def _translate_chunk(client: OpenAI, text: str, source_lang: str) -> str:
    """텍스트 1개 청크를 한국어로 번역"""
    response = client.chat.completions.create(
        model=TRANSLATE_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 보드게임 룰북 전문 번역가입니다. "
                    "원문의 마크다운 서식(제목, 표, 리스트 등)을 그대로 유지하면서 "
                    "자연스러운 한국어로 번역하세요. "
                    "보드게임 용어는 한국에서 통용되는 표현을 사용하세요."
                ),
            },
            {
                "role": "user",
                "content": f"다음 {source_lang} 텍스트를 한국어로 번역하세요:\n\n{text}",
            },
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def process_translate(rule_id: int):
    """
    game_rule 1건에 대해 번역 실행

    language가 'ko'이면 skip.
    번역 후 원본은 extra_sections.original_raw_text에 백업.
    """
    # 멀티소스: 각 소스별로 번역 필요 여부 확인
    sources = db.get_rule_sources(rule_id)
    need_translate = [
        s for s in sources
        if s.get("status") == "processed"
        and s.get("language", "ko") != "ko"
        and s.get("raw_content", "").strip()
    ]

    if not need_translate:
        print(f"  [번역] skip (모든 소스가 한국어)")
        db.skip_step(rule_id, "translate", "모든 소스가 한국어")
        return

    db.start_step(rule_id, "translate")

    try:
        translated_count = 0

        for source in need_translate:
            src_lang = source.get("language", "en")
            raw_content = source["raw_content"]
            src_type = source["source_type"]

            print(f"  [번역] {src_type} ({src_lang} -> ko, {len(raw_content)}자)")

            # 번역 실행
            translated = translate_text(raw_content, src_lang)

            # game_rule_sources 업데이트
            db.update_rule_source(source["id"], {
                "raw_content": translated,
                "language": "ko",
                "metadata": {
                    **(source.get("metadata") or {}),
                    "original_language": src_lang,
                    "original_length": len(raw_content),
                },
            })

            # PDF 소스면 game_rules.raw_text도 업데이트
            if src_type == "pdf":
                rule = db.get_rule(rule_id)
                extra = rule.get("extra_sections") or {}
                extra["original_raw_text"] = raw_content
                extra["original_language"] = src_lang
                db.update_rule(rule_id, {
                    "raw_text": translated,
                    "language": "ko",
                    "extra_sections": extra,
                })

            translated_count += 1

        log_msg = f"성공: {translated_count}건 번역"
        print(f"  [번역] {log_msg}")
        db.finish_step(rule_id, "translate", log_msg)

    except Exception as e:
        error_msg = f"번역 실패: {e}"
        print(f"  [번역] [ERROR] {error_msg}")
        db.fail_step(rule_id, "translate", error_msg)
        raise
