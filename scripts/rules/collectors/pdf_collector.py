"""
PDF 수집기 - Upstage Document Parse API

기존 step1_ocr.py 로직을 collector 모듈로 이동.
PDF/이미지 파일을 Upstage API로 OCR 처리하여 마크다운 텍스트 반환.
"""

import os

import requests
from dotenv import load_dotenv

from scripts.rules.config import (
    PROJECT_ROOT,
    UPSTAGE_API_URL,
    UPSTAGE_OCR_MODE,
    UPSTAGE_MODEL,
)

load_dotenv()


def call_upstage_api(file_path: str) -> dict:
    """
    Upstage Document Parse API 호출

    Args:
        file_path: 업로드할 파일의 절대 경로

    Returns:
        API 응답 JSON
    """
    api_key = os.getenv("UPSTAGE_API_KEY", "")
    if not api_key:
        raise RuntimeError("UPSTAGE_API_KEY가 .env에 없습니다.")

    headers = {"Authorization": f"Bearer {api_key}"}

    with open(file_path, "rb") as f:
        files = {"document": f}
        data = {
            "ocr": UPSTAGE_OCR_MODE,
            "output_formats": "['text', 'markdown']",
            "model": UPSTAGE_MODEL,
        }
        response = requests.post(
            UPSTAGE_API_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=300,
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Upstage API 에러 {response.status_code}: {response.text}"
        )

    return response.json()


def collect(source_row: dict) -> dict:
    """
    PDF/이미지 파일에서 텍스트 추출

    Args:
        source_row: game_rule_sources 테이블의 1행

    Returns:
        {"raw_content": str, "page_count": int, "elements": list}
    """
    source_file = source_row.get("source_file", "")
    if not source_file:
        raise ValueError("source_file이 비어있음")

    file_path = PROJECT_ROOT / source_file
    if not file_path.exists():
        raise FileNotFoundError(f"파일 없음: {file_path}")

    print(f"    [PDF] {file_path.name} -> Upstage API 호출 중...")

    result = call_upstage_api(str(file_path))

    content = result.get("content", {})
    markdown_text = content.get("markdown", "")
    plain_text = content.get("text", "")
    raw_content = markdown_text or plain_text

    if not raw_content.strip():
        raise ValueError("Upstage API에서 텍스트 추출 실패 (빈 결과)")

    page_count = result.get("usage", {}).get("pages", 0)
    elements = result.get("elements", [])

    print(f"    [PDF] {len(raw_content)}자 추출, {page_count}페이지")

    return {
        "raw_content": raw_content,
        "page_count": page_count,
        "elements": elements,
    }
