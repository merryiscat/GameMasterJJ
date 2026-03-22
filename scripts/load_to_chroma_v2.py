"""
Supabase → ChromaDB 동기화 스크립트

Supabase games 테이블의 데이터를 ChromaDB 벡터 검색 인덱스로 변환합니다.
3개 컬렉션: game_search, game_rules, game_playbook

사용법:
    uv run python scripts/load_to_chroma_v2.py                # Supabase에서 동기화
    uv run python scripts/load_to_chroma_v2.py --from-jsonl    # JSONL에서 직접 로드 (Supabase 없이)
    uv run python scripts/load_to_chroma_v2.py --limit 100     # 100개만 테스트

필수 환경변수 (.env):
    OPENAI_API_KEY=sk-...
    SUPABASE_URL=https://xxx.supabase.co    (--from-jsonl 아닌 경우)
    SUPABASE_KEY=eyJ...                      (--from-jsonl 아닌 경우)
"""

import json
import os
import sys
import time
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 경로 설정
# ============================================================
PROJECT_ROOT = Path(__file__).parent.parent
CHROMA_DIR = str(PROJECT_ROOT / "chroma_db")
GAMES_JSONL = PROJECT_ROOT / "data" / "boardlife_games.jsonl"

# 임베딩 배치 크기 (OpenAI API 호출 단위)
BATCH_SIZE = 100


# ============================================================
# 데이터 소스
# ============================================================
def load_from_supabase(limit: int = 0) -> list[dict]:
    """Supabase games 테이블에서 데이터 로드"""
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("SUPABASE_URL, SUPABASE_KEY를 .env에 설정하세요!")
        sys.exit(1)

    sb = create_client(url, key)
    print("   Supabase 연결 완료")

    # 전체 게임 로드 (페이지네이션)
    games = []
    page_size = 1000
    offset = 0

    while True:
        query = sb.table("games").select("*").range(offset, offset + page_size - 1)
        result = query.execute()

        if not result.data:
            break

        games.extend(result.data)
        offset += page_size

        if limit and len(games) >= limit:
            games = games[:limit]
            break

        print(f"\r   로드 중: {len(games)}개", end="", flush=True)

    print(f"\r   Supabase 로드 완료: {len(games)}개 게임")
    return games


def load_from_jsonl(limit: int = 0) -> list[dict]:
    """JSONL 파일에서 직접 로드 (Supabase 없이 테스트용)"""
    if not GAMES_JSONL.exists():
        print(f"파일 없음: {GAMES_JSONL}")
        sys.exit(1)

    games = []
    with open(GAMES_JSONL, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if line:
                game = json.loads(line)
                # JSONL에는 자체 ID가 없으므로 인덱스 사용
                if "id" not in game:
                    game["id"] = i + 1
                games.append(game)
                if limit and len(games) >= limit:
                    break

    print(f"   JSONL 로드 완료: {len(games)}개 게임")
    return games


# ============================================================
# ChromaDB 문서 빌더
# ============================================================
def build_search_document(game: dict) -> str:
    """
    game_search 컬렉션용 document 생성

    자연어 검색에 최적화된 텍스트.
    "협력형 던전 게임 추천해줘" 같은 질문에 매칭되도록 구성.
    """
    parts = []

    # 게임 이름 (한/영)
    name_ko = game.get("name_ko", "")
    name_en = game.get("name_en", "")
    if name_ko and name_en:
        parts.append(f"게임: {name_ko} ({name_en})")
    elif name_ko:
        parts.append(f"게임: {name_ko}")

    # 한줄 소개
    one_liner = game.get("one_liner", "")
    if one_liner:
        parts.append(f"소개: {one_liner}")

    # 설명 (최대 500자)
    desc = game.get("description_ko", "")
    if desc:
        parts.append(f"설명: {desc[:500]}")

    # 인원/시간
    min_p = game.get("min_players")
    max_p = game.get("max_players")
    if min_p and max_p:
        parts.append(f"인원: {min_p}~{max_p}명")

    playtime = game.get("playtime")
    if playtime:
        parts.append(f"플레이 시간: {playtime}분")

    # 메카니즘
    mechanisms = game.get("mechanisms", [])
    if mechanisms:
        parts.append(f"메카니즘: {', '.join(mechanisms)}")

    # 카테고리
    categories = game.get("categories", [])
    if categories:
        parts.append(f"카테고리: {', '.join(categories)}")

    return "\n".join(parts)


def build_search_metadata(game: dict) -> dict:
    """game_search 컬렉션용 metadata (필터링에 사용)"""

    def _safe(val, default):
        if val is None:
            return default
        try:
            if isinstance(default, float):
                result = float(val)
                return default if result != result else result  # NaN 체크
            return int(float(val))
        except (ValueError, TypeError):
            return default

    return {
        "game_id": _safe(game.get("id"), 0),
        "name_ko": game.get("name_ko", ""),
        "name_en": game.get("name_en", ""),
        "year_published": _safe(game.get("year_published"), 0),
        "rating": _safe(game.get("rating"), 0.0),
        "difficulty": _safe(game.get("difficulty"), 0.0),
        "min_players": _safe(game.get("min_players"), 0),
        "max_players": _safe(game.get("max_players"), 0),
        "playtime": _safe(game.get("playtime"), 0),
        # 배열은 문자열로 변환 (ChromaDB 메타데이터 제한)
        "mechanisms": ", ".join(game.get("mechanisms", [])) if isinstance(game.get("mechanisms"), list) else str(game.get("mechanisms", "")),
        "categories": ", ".join(game.get("categories", [])) if isinstance(game.get("categories"), list) else str(game.get("categories", "")),
    }


def build_rules_document(game: dict) -> str:
    """game_rules 컬렉션용 document (룰 Q&A용)"""
    parts = []

    name = game.get("name_ko", "")
    if name:
        parts.append(f"게임: {name}")

    desc = game.get("description_ko", "")
    if desc:
        parts.append(desc)

    one_liner = game.get("one_liner", "")
    if one_liner:
        parts.append(one_liner)

    mechanisms = game.get("mechanisms", [])
    if mechanisms:
        parts.append(f"메카니즘: {', '.join(mechanisms)}")

    return "\n".join(parts)


# ============================================================
# ChromaDB 저장
# ============================================================
def sync_to_chromadb(games: list[dict]):
    """
    게임 데이터를 ChromaDB 3개 컬렉션에 저장

    1. game_search — 게임 검색/추천
    2. game_rules  — 게임 룰 Q&A (RAG)
    3. game_playbook — (추후 확장, 현재는 빈 컬렉션 생성만)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY를 .env에 설정하세요!")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"ChromaDB 동기화 시작 ({len(games)}개 게임)")
    print(f"저장 경로: {CHROMA_DIR}")
    print(f"{'=' * 60}")

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    openai_ef = OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name="text-embedding-3-small"
    )

    # ---- 컬렉션 1: game_search ----
    print("\n[1/3] game_search 컬렉션")
    _recreate_collection(client, "game_search", openai_ef)
    col_search = client.get_collection("game_search", embedding_function=openai_ef)

    _batch_add(
        collection=col_search,
        games=games,
        id_fn=lambda g: f"game_{g.get('id', 0)}",
        doc_fn=build_search_document,
        meta_fn=build_search_metadata,
        label="game_search",
    )

    # ---- 컬렉션 2: game_rules ----
    print("\n[2/3] game_rules 컬렉션")
    _recreate_collection(client, "game_rules", openai_ef)
    col_rules = client.get_collection("game_rules", embedding_function=openai_ef)

    _batch_add(
        collection=col_rules,
        games=games,
        id_fn=lambda g: f"rule_{g.get('id', 0)}_0",
        doc_fn=build_rules_document,
        meta_fn=lambda g: {
            "game_id": g.get("id", 0) if isinstance(g.get("id"), int) else 0,
            "game_name": g.get("name_ko", ""),
            "chunk_type": "description",
        },
        label="game_rules",
    )

    # ---- 컬렉션 3: game_playbook (빈 컬렉션, 추후 확장) ----
    print("\n[3/3] game_playbook 컬렉션 (빈 컬렉션 생성)")
    _recreate_collection(client, "game_playbook", openai_ef)
    print("   game_playbook: 추후 룰북 데이터 추가 시 사용")

    # ---- 검증 ----
    print(f"\n{'=' * 60}")
    print("컬렉션 현황:")
    for name in ["game_search", "game_rules", "game_playbook"]:
        col = client.get_collection(name)
        print(f"   {name}: {col.count()}개")
    print(f"{'=' * 60}")


def _recreate_collection(client, name: str, ef):
    """기존 컬렉션 삭제 후 재생성"""
    try:
        client.delete_collection(name)
        print(f"   기존 {name} 삭제")
    except Exception:
        pass

    client.get_or_create_collection(
        name=name,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )


def _batch_add(collection, games: list[dict], id_fn, doc_fn, meta_fn, label: str):
    """배치 단위로 ChromaDB에 추가"""
    total = len(games)
    start_time = time.time()

    for i in range(0, total, BATCH_SIZE):
        batch = games[i:i + BATCH_SIZE]

        ids = []
        documents = []
        metadatas = []

        for game in batch:
            doc = doc_fn(game)
            # 빈 document는 건너뜀
            if not doc or len(doc.strip()) < 5:
                continue

            ids.append(id_fn(game))
            documents.append(doc)
            metadatas.append(meta_fn(game))

        if ids:
            collection.add(ids=ids, documents=documents, metadatas=metadatas)

        # 진행률
        done = min(i + BATCH_SIZE, total)
        elapsed = time.time() - start_time
        pct = (done / total) * 100
        bar_width = 25
        filled = int(bar_width * done / total)
        bar = "█" * filled + "░" * (bar_width - filled)
        print(f"\r   {bar} {pct:5.1f}% [{done}/{total}] ({elapsed:.1f}s)",
              end="", flush=True)

    print()  # 줄바꿈


# ============================================================
# 검증
# ============================================================
def verify_chromadb():
    """ChromaDB 데이터 검증 — 한국어 검색 테스트"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    openai_ef = OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name="text-embedding-3-small"
    )

    col = client.get_collection("game_search", embedding_function=openai_ef)

    print(f"\n{'=' * 60}")
    print("검증: 한국어 유사도 검색 테스트")
    print(f"{'=' * 60}")

    # 테스트 쿼리들
    queries = [
        "협력형 던전 탐험 게임",
        "2인용 전략 게임",
        "가족끼리 하기 좋은 쉬운 게임",
    ]

    for query in queries:
        print(f"\n   검색: '{query}'")
        results = col.query(query_texts=[query], n_results=5)

        for i, meta in enumerate(results["metadatas"][0]):
            dist = results["distances"][0][i]
            name = meta.get("name_ko", "?")
            rating = meta.get("rating", 0)
            print(f"      {i+1}. {name} (유사도: {1-dist:.3f}, 평점: {rating})")


# ============================================================
# 메인 실행
# ============================================================
def main():
    from_jsonl = "--from-jsonl" in sys.argv
    limit = 0

    for i, arg in enumerate(sys.argv):
        if arg == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])

    print("=" * 60)
    print("Supabase → ChromaDB 동기화 (v2)")
    print("=" * 60)

    # 데이터 로드
    if from_jsonl:
        print("\n   데이터 소스: JSONL 파일")
        games = load_from_jsonl(limit=limit)
    else:
        print("\n   데이터 소스: Supabase")
        games = load_from_supabase(limit=limit)

    if not games:
        print("   데이터 없음!")
        return

    # ChromaDB 동기화
    sync_to_chromadb(games)

    # 검증
    verify_chromadb()

    print(f"\n{'=' * 60}")
    print("완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
