"""
벡터화 노드

정리된 섹션 + QA 쌍을 ChromaDB에 임베딩.
긴 섹션은 문단 단위로 분할하여 토큰 한도(8192)를 초과하지 않도록 한다.
"""

from preprocessing.pipeline import SECTIONS, db
from preprocessing.pipeline.step6_vectorize import (
    get_chroma_collection,
    build_qa_chunks,
    batch_add_to_collection,
)
from preprocessing.agents.state import PipelineState

# text-embedding-3-small 토큰 한도가 8192이므로
# 한국어 기준 대략 글자수 4000자 이내로 분할 (안전 마진)
MAX_CHUNK_CHARS = 3500


def _split_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """
    긴 텍스트를 문단(\n\n) 단위로 분할.
    각 청크가 max_chars를 넘지 않도록 한다.
    """
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    for para in paragraphs:
        # 현재 청크 + 새 문단이 한도 초과 → 현재 청크 저장 후 새로 시작
        if current and len(current) + len(para) + 2 > max_chars:
            chunks.append(current.strip())
            current = para
        else:
            current = current + "\n\n" + para if current else para

    if current.strip():
        chunks.append(current.strip())

    return chunks if chunks else [text]


def _build_section_chunks_from_merged(
    game_id: int, game_name: str, merged_sections: dict
) -> list[tuple[str, str, dict]]:
    """
    merged_sections에서 벡터화용 청크 생성.
    긴 섹션은 문단 단위로 분할한다.
    """
    chunks = []

    for section_name in SECTIONS:
        text = merged_sections.get(section_name, "")
        if not text.strip():
            continue

        # 긴 섹션은 분할
        sub_texts = _split_text(text)

        for i, sub_text in enumerate(sub_texts):
            chunk_id = f"rule_{game_id}_{section_name}_{i}"
            document = f"게임: {game_name} | 섹션: {section_name}\n\n{sub_text}"
            metadata = {
                "game_id": game_id,
                "game_name": game_name,
                "section": section_name,
                "sub_section": f"part_{i}" if len(sub_texts) > 1 else "",
                "chunk_type": "section",
                "chunk_index": i,
            }
            chunks.append((chunk_id, document, metadata))

    return chunks


def vectorize_node(state: PipelineState) -> dict:
    """
    merged_sections + qa_pairs를 ChromaDB에 임베딩.
    """
    game_id = state["game_id"]
    game_name = state["game_name"]
    merged = state.get("merged_sections", {})
    qa_pairs = state.get("qa_pairs", [])

    print(f"  [vectorize] {game_name} - ChromaDB 임베딩 중...")

    collection = get_chroma_collection()

    # 기존 해당 game_id 청크 삭제 (중복 방지)
    try:
        existing = collection.get(where={"game_id": game_id})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
            print(f"    기존 청크 {len(existing['ids'])}개 삭제")
    except Exception:
        pass

    # 섹션 청크 생성 (긴 섹션 자동 분할)
    section_chunks = _build_section_chunks_from_merged(game_id, game_name, merged)

    # QA 청크 생성
    qa_chunks = build_qa_chunks(game_id, game_name, qa_pairs)

    # ChromaDB에 추가
    batch_add_to_collection(collection, section_chunks, "섹션")
    batch_add_to_collection(collection, qa_chunks, "QA")

    total = len(section_chunks) + len(qa_chunks)
    print(f"  [vectorize] 완료: 섹션 {len(section_chunks)} + QA {len(qa_chunks)} = 총 {total}청크")

    return {}
