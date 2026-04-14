"""
Step 6: 벡터화 - 섹션 청크 + QA 쌍 → ChromaDB 임베딩

정리된 섹션 텍스트와 QA 쌍을 ChromaDB에 임베딩하여
유사도 검색이 가능하도록 한다.
"""

import os
import time

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv

from scripts.rules.config import CHROMA_DIR, EMBEDDING_MODEL, BATCH_SIZE
from scripts.rules import SECTIONS, SECTION_TO_COLUMN, SECTION_TO_EXTRA, db

load_dotenv()


def get_chroma_collection():
    """ChromaDB game_rules 컬렉션 반환"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 .env에 없습니다.")

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    openai_ef = OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name=EMBEDDING_MODEL,
    )

    # 컬렉션 가져오기 (없으면 생성)
    return client.get_or_create_collection(
        name="game_rules",
        embedding_function=openai_ef,
        metadata={"hnsw:space": "cosine"},
    )


def build_section_chunks(
    game_id: int, game_name: str, rule: dict
) -> list[tuple[str, str, dict]]:
    """
    섹션 데이터를 벡터화용 청크로 변환

    Returns:
        [(chunk_id, document, metadata), ...] 리스트
    """
    chunks = []
    extra = rule.get("extra_sections") or {}
    preprocessed_items = extra.get("preprocessed_items", {})

    for section_name in SECTIONS:
        # 섹션 텍스트 가져오기
        if section_name in SECTION_TO_COLUMN:
            col = SECTION_TO_COLUMN[section_name]
            text = rule.get(col, "") or ""
        else:
            text = extra.get(section_name, "") or ""

        if not text.strip():
            continue

        # 구조화 섹션: items가 있으면 항목별로 분리
        items = preprocessed_items.get(section_name, [])

        if items:
            # 항목별 청크 생성
            for i, item in enumerate(items):
                # 항목에서 제목 추출 (":"앞 부분)
                sub_section = item.split(":")[0].strip() if ":" in item else f"item_{i}"

                chunk_id = f"rule_{game_id}_{section_name}_{i}"
                document = (
                    f"게임: {game_name} | 섹션: {section_name} | 항목: {sub_section}\n\n"
                    f"{item}"
                )
                metadata = {
                    "game_id": game_id,
                    "game_name": game_name,
                    "section": section_name,
                    "sub_section": sub_section,
                    "chunk_type": "section",
                    "chunk_index": i,
                }
                chunks.append((chunk_id, document, metadata))
        else:
            # 짧은/서술형 섹션: 통째로 1청크
            chunk_id = f"rule_{game_id}_{section_name}_0"
            document = (
                f"게임: {game_name} | 섹션: {section_name}\n\n"
                f"{text}"
            )
            metadata = {
                "game_id": game_id,
                "game_name": game_name,
                "section": section_name,
                "sub_section": "",
                "chunk_type": "section",
                "chunk_index": 0,
            }
            chunks.append((chunk_id, document, metadata))

    return chunks


def build_qa_chunks(
    game_id: int, game_name: str, qa_pairs: list[dict]
) -> list[tuple[str, str, dict]]:
    """
    QA 쌍을 벡터화용 청크로 변환

    Returns:
        [(chunk_id, document, metadata), ...] 리스트
    """
    chunks = []
    for i, qa in enumerate(qa_pairs):
        q = qa.get("question", "")
        a = qa.get("answer", "")
        section = qa.get("section", "")

        if not q or not a:
            continue

        chunk_id = f"rule_{game_id}_qa_{i}"
        document = f"게임: {game_name}\nQ: {q}\nA: {a}"
        metadata = {
            "game_id": game_id,
            "game_name": game_name,
            "section": section,
            "sub_section": "",
            "chunk_type": "qa",
            "chunk_index": i,
        }
        chunks.append((chunk_id, document, metadata))

    return chunks


def batch_add_to_collection(
    collection, chunks: list[tuple[str, str, dict]], label: str
):
    """배치 단위로 ChromaDB에 추가 (load_to_chroma_v2.py 패턴)"""
    total = len(chunks)
    if total == 0:
        print(f"    {label}: 0개 (건너뜀)")
        return

    start_time = time.time()

    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]

        ids = [c[0] for c in batch]
        documents = [c[1] for c in batch]
        metadatas = [c[2] for c in batch]

        collection.add(ids=ids, documents=documents, metadatas=metadatas)

        # 진행률 표시
        done = min(i + BATCH_SIZE, total)
        elapsed = time.time() - start_time
        pct = (done / total) * 100
        print(f"\r    {label}: {done}/{total} ({pct:.0f}%, {elapsed:.1f}s)",
              end="", flush=True)

    print()  # 줄바꿈


def process_vectorize(rule_id: int):
    """
    game_rule 1건에 대해 벡터화 실행

    1. 기존 game_id 관련 청크 삭제 (중복 방지)
    2. 섹션 청크 생성 + 임베딩
    3. QA 청크 생성 + 임베딩
    """
    db.start_step(rule_id, "vectorize")

    try:
        rule = db.get_rule(rule_id)
        game_id = rule["game_id"]

        # 게임 이름 조회
        sb = db.get_client()
        game = sb.table("games").select("name_ko").eq("id", game_id).execute()
        game_name = game.data[0]["name_ko"] if game.data else f"game_{game_id}"

        print(f"  [벡터화] {game_name} - ChromaDB 임베딩 중...")

        collection = get_chroma_collection()

        # 기존 해당 game_id 청크 삭제 (중복 방지)
        try:
            existing = collection.get(
                where={"game_id": game_id},
            )
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
                print(f"    기존 청크 {len(existing['ids'])}개 삭제")
        except Exception:
            pass  # 기존 데이터 없으면 무시

        # 섹션 청크 생성
        section_chunks = build_section_chunks(game_id, game_name, rule)

        # QA 청크 생성
        extra = rule.get("extra_sections") or {}
        qa_pairs = extra.get("qa_pairs", [])
        qa_chunks = build_qa_chunks(game_id, game_name, qa_pairs)

        # ChromaDB에 추가
        batch_add_to_collection(collection, section_chunks, "섹션")
        batch_add_to_collection(collection, qa_chunks, "QA")

        # 상태 업데이트
        db.update_rule(rule_id, {"status": "vectorized"})

        total = len(section_chunks) + len(qa_chunks)
        log_msg = f"성공: 섹션 {len(section_chunks)}청크 + QA {len(qa_chunks)}청크 = 총 {total}청크"
        print(f"  [벡터화] {log_msg}")
        db.finish_step(rule_id, "vectorize", log_msg)

    except Exception as e:
        error_msg = f"벡터화 실패: {e}"
        print(f"  [벡터화] [ERROR] {error_msg}")
        db.fail_step(rule_id, "vectorize", error_msg)
        raise
