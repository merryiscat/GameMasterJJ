"""
ChromaDB 검색 서비스

어드민 검색 테스트 페이지에서 사용하는 벡터 검색 함수들.
"""

import os
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()

# ChromaDB 경로
CHROMA_DIR = str(Path(__file__).parent.parent.parent / "chroma_db")


def _get_collection():
    """game_rules ChromaDB 컬렉션 반환"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    ef = OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name="text-embedding-3-small",
    )
    return client.get_collection("game_rules", embedding_function=ef)


@dataclass
class SearchResult:
    """검색 결과 1건"""
    document: str
    game_name: str
    section: str
    sub_section: str
    chunk_type: str
    similarity: float


def search_chromadb(
    query: str,
    n_results: int = 5,
    chunk_type: str | None = None,
    game_id: int | None = None,
) -> list[SearchResult]:
    """
    ChromaDB 벡터 검색

    Args:
        query: 검색 쿼리
        n_results: 반환할 결과 수
        chunk_type: 'section' 또는 'qa' 필터 (None이면 전체)
        game_id: 특정 게임만 필터 (None이면 전체)

    Returns:
        SearchResult 리스트 (유사도 높은 순)
    """
    col = _get_collection()

    # where 필터 구성
    where_filter = None
    conditions = []

    if chunk_type:
        conditions.append({"chunk_type": chunk_type})
    if game_id:
        conditions.append({"game_id": game_id})

    if len(conditions) == 1:
        where_filter = conditions[0]
    elif len(conditions) > 1:
        where_filter = {"$and": conditions}

    # 검색 실행
    kwargs = {"query_texts": [query], "n_results": n_results}
    if where_filter:
        kwargs["where"] = where_filter

    raw = col.query(**kwargs)

    # 결과 변환
    results = []
    for i in range(len(raw["ids"][0])):
        meta = raw["metadatas"][0][i]
        dist = raw["distances"][0][i]
        doc = raw["documents"][0][i]

        results.append(SearchResult(
            document=doc,
            game_name=meta.get("game_name", ""),
            section=meta.get("section", ""),
            sub_section=meta.get("sub_section", ""),
            chunk_type=meta.get("chunk_type", ""),
            similarity=round(1 - dist, 3),
        ))

    return results


def get_collection_count() -> int:
    """game_rules 컬렉션의 전체 청크 수"""
    col = _get_collection()
    return col.count()


def get_playbook(game_id: int) -> tuple[list[dict], str]:
    """
    특정 게임의 플레이북 조회

    Returns:
        (플레이북 스텝 리스트, 게임 이름)
    """
    from supabase import create_client

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    sb = create_client(url, key)

    # 플레이북 조회
    result = (
        sb.table("game_playbooks")
        .select("*")
        .eq("game_id", game_id)
        .order("step_order")
        .execute()
    )

    # 게임 이름
    game = sb.table("games").select("name_ko").eq("id", game_id).execute()
    game_name = game.data[0]["name_ko"] if game.data else ""

    return result.data, game_name
