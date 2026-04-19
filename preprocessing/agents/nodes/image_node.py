"""
이미지 추출 노드

PDF 룰북에서 컴포넌트 이미지를 개별 추출하고
VLM으로 분류/라벨링한다.

1. PyMuPDF로 PDF 내장 이미지 추출
2. 크기 필터링 (50x50px 이상)
3. data/images/components/game_{id}/ 에 PNG 저장
4. VLM 배치 분류 → ComponentImage 리스트 반환
"""

import base64
import json
import os
from pathlib import Path

import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import OpenAI

from preprocessing.pipeline.config import (
    IMAGE_CLASSIFY_MODEL,
    COMPONENT_IMAGE_MIN_SIZE,
    COMPONENT_IMAGE_DIR,
    COMPONENT_IMAGE_BATCH_SIZE,
    AGENT_PROMPTS_DIR,
)
from preprocessing.agents.state import PipelineState, ComponentImage

load_dotenv()


def _extract_images_from_pdf(pdf_path: str, game_id: int) -> list[dict]:
    """
    PDF에서 내장 이미지를 추출하고 PNG로 저장.

    Returns:
        [{"page_num": int, "image_index": int, "image_path": str,
          "width": int, "height": int, "b64": str}, ...]
    """
    # 저장 디렉토리 생성
    save_dir = COMPONENT_IMAGE_DIR / f"game_{game_id}"
    save_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    extracted = []
    # xref 중복 방지 (같은 이미지가 여러 페이지에 반복 등장)
    seen_xrefs = set()

    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)

        for img_idx, img_info in enumerate(image_list):
            xref = img_info[0]

            # 중복 이미지 건너뛰기
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            try:
                pix = fitz.Pixmap(doc, xref)

                # CMYK → RGB 변환
                if pix.n > 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)

                # 크기 필터링
                if pix.width < COMPONENT_IMAGE_MIN_SIZE or pix.height < COMPONENT_IMAGE_MIN_SIZE:
                    continue

                # PNG로 저장
                filename = f"p{page_num}_i{img_idx}_x{xref}.png"
                save_path = save_dir / filename
                pix.save(str(save_path))

                # base64 인코딩 (VLM 전송용)
                png_bytes = pix.tobytes("png")
                b64 = base64.b64encode(png_bytes).decode("utf-8")

                extracted.append({
                    "page_num": page_num,
                    "image_index": img_idx,
                    "image_path": str(save_path.relative_to(Path.cwd())),
                    "width": pix.width,
                    "height": pix.height,
                    "b64": b64,
                })
            except Exception:
                # 일부 이미지 형식(JBIG2 등)은 추출 불가 → 건너뜀
                continue

    doc.close()
    return extracted


def _classify_images_batch(
    client: OpenAI,
    game_name: str,
    images: list[dict],
) -> list[dict]:
    """
    VLM으로 이미지 배치 분류.

    Args:
        images: [{"b64": str, "page_num": int, ...}, ...]
    Returns:
        [{"index": int, "category": str, "label": str, "description": str, "is_component": bool}, ...]
    """
    template = (AGENT_PROMPTS_DIR / "classify_component.txt").read_text(encoding="utf-8")
    prompt_text = template.replace("{game_name}", game_name)

    # 멀티모달 메시지 구성
    content = [{"type": "text", "text": prompt_text}]

    for i, img in enumerate(images):
        content.append({"type": "text", "text": f"--- 이미지 {i} (p{img['page_num']}, {img['width']}x{img['height']}) ---"})
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img['b64']}", "detail": "low"},
        })

    response = client.chat.completions.create(
        model=IMAGE_CLASSIFY_MODEL,
        messages=[{"role": "user", "content": content}],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_completion_tokens=4000,
    )

    result = json.loads(response.choices[0].message.content)

    # 응답 형태 처리
    if isinstance(result, dict):
        return result.get("images", [])
    if isinstance(result, list):
        return result
    return []


def extract_images_node(state: PipelineState) -> dict:
    """
    PDF에서 컴포넌트 이미지 추출 + VLM 분류.
    PDF가 없으면 빈 리스트 반환.
    """
    pdf_path = state.get("pdf_file_path")
    if not pdf_path:
        print("  [images] PDF 없음 (skip)")
        return {"component_images": []}

    game_id = state["game_id"]
    game_name = state["game_name"]

    print(f"  [images] {game_name} - PDF 이미지 추출 중...")

    # 1. 이미지 추출
    extracted = _extract_images_from_pdf(pdf_path, game_id)
    if not extracted:
        print(f"  [images] 추출된 이미지 없음")
        return {"component_images": []}

    print(f"  [images] {len(extracted)}개 이미지 추출, VLM 분류 중...")

    # 2. VLM 배치 분류
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    all_classifications = []

    for batch_start in range(0, len(extracted), COMPONENT_IMAGE_BATCH_SIZE):
        batch = extracted[batch_start:batch_start + COMPONENT_IMAGE_BATCH_SIZE]
        print(f"    배치 {batch_start // COMPONENT_IMAGE_BATCH_SIZE + 1}...", end=" ", flush=True)

        try:
            classifications = _classify_images_batch(client, game_name, batch)
            all_classifications.extend([
                (batch[c.get("index", i)], c) if c.get("index", i) < len(batch) else (batch[i], c)
                for i, c in enumerate(classifications)
            ])
            print(f"{len(classifications)}개 분류 [OK]")
        except Exception as e:
            print(f"[ERROR] {e}")

    # 3. ComponentImage 리스트 구성 (is_component=true만)
    component_images: list[ComponentImage] = []
    removed = 0

    for img_data, classification in all_classifications:
        if not classification.get("is_component", True):
            # 장식/배경 이미지 → 파일 삭제
            try:
                os.remove(img_data["image_path"])
            except OSError:
                pass
            removed += 1
            continue

        component_images.append({
            "page_num": img_data["page_num"],
            "image_index": img_data["image_index"],
            "image_path": img_data["image_path"],
            "label": classification.get("label", "unknown"),
            "category": classification.get("category", "other"),
            "description": classification.get("description", ""),
            "width": img_data["width"],
            "height": img_data["height"],
        })

    print(f"  [images] 완료: 컴포넌트 {len(component_images)}개, 장식/배경 {removed}개 제거")

    return {"component_images": component_images}
