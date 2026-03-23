"""
ChromaDB 보드게임 데이터 웹 뷰어

브라우저에서 ChromaDB에 저장된 보드게임 데이터를 검색/조회할 수 있는 웹 앱.
FastAPI + Jinja2 HTML 템플릿 사용.

사용법:
    uv run python -m app.web_viewer
    → http://localhost:8000 에서 확인
"""

import os
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# .env 로드
load_dotenv()

# ============================================================
# 경로 설정
# ============================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DIR = os.path.join(PROJECT_ROOT, "chroma_db")
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "app", "templates")

# ============================================================
# ChromaDB 연결
# ============================================================
client = chromadb.PersistentClient(path=CHROMA_DIR)

# 임베딩 함수 설정
# OpenAI 키가 있고 OpenAI로 저장된 DB면 OpenAI 사용, 아니면 기본(MiniLM) 사용
api_key = os.getenv("OPENAI_API_KEY")

try:
    # OpenAI 임베딩으로 시도
    if api_key:
        openai_ef = OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name="text-embedding-3-small"
        )
        collection = client.get_or_create_collection(
            name="boardgames",
            embedding_function=openai_ef,
            metadata={"hnsw:space": "cosine"}
        )
        print("   OpenAI 임베딩 모드로 연결")
    else:
        raise ValueError("OpenAI 키 없음")
except (ValueError, Exception):
    # 기본 임베딩(MiniLM)으로 폴백
    collection = client.get_or_create_collection(
        name="boardgames",
        metadata={"hnsw:space": "cosine"}
    )
    print("   기본 임베딩(MiniLM) 모드로 연결")

# ============================================================
# FastAPI 앱
# ============================================================
app = FastAPI(title="GMJJ 보드게임 뷰어")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """메인 페이지 - 전체 통계 + 검색 폼"""
    total_count = collection.count()

    # 인기 게임 Top 10 (소유자 수 기준)
    top_games = collection.get(
        limit=10,
        include=["metadatas"],
        where={"rank_boardgame": {"$lte": 10}}
    )

    return templates.TemplateResponse("index.html", {
        "request": request,
        "total_count": total_count,
        "top_games": top_games["metadatas"] if top_games["metadatas"] else [],
    })


@app.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    q: str = Query(default="", description="검색어"),
    min_players: int = Query(default=0, description="최소 인원"),
    max_weight: float = Query(default=5.0, description="최대 난이도"),
    min_rating: float = Query(default=0.0, description="최소 평점"),
    category: str = Query(default="all", description="카테고리"),
    limit: int = Query(default=20, description="결과 수"),
):
    """유사도 검색 + 필터"""
    results = {"metadatas": [[]], "distances": [[]], "documents": [[]]}

    if q:
        # 필터 조건 구성
        where_conditions = []

        if min_players > 0:
            where_conditions.append({"max_players": {"$gte": min_players}})

        if max_weight < 5.0:
            where_conditions.append({"game_weight": {"$lte": max_weight}})

        if min_rating > 0:
            where_conditions.append({"avg_rating": {"$gte": min_rating}})

        # 카테고리 필터
        category_map = {
            "strategy": {"is_strategy": {"$eq": 1}},
            "family": {"is_family": {"$eq": 1}},
            "party": {"is_party": {"$eq": 1}},
            "thematic": {"is_thematic": {"$eq": 1}},
            "war": {"is_war": {"$eq": 1}},
            "abstract": {"is_abstract": {"$eq": 1}},
            "childrens": {"is_childrens": {"$eq": 1}},
        }
        if category in category_map:
            where_conditions.append(category_map[category])

        # where 조건 조합
        where = None
        if len(where_conditions) == 1:
            where = where_conditions[0]
        elif len(where_conditions) > 1:
            where = {"$and": where_conditions}

        # ChromaDB 유사도 검색 실행
        results = collection.query(
            query_texts=[q],
            n_results=limit,
            where=where,
            include=["metadatas", "distances", "documents"],
        )

    # 검색 결과를 보기 좋게 가공
    games = []
    if results["metadatas"] and results["metadatas"][0]:
        for i, meta in enumerate(results["metadatas"][0]):
            dist = results["distances"][0][i] if results["distances"][0] else 0
            # cosine distance → similarity (1 - distance)
            similarity = round((1 - dist) * 100, 1)
            meta["similarity"] = similarity
            games.append(meta)

    return templates.TemplateResponse("search.html", {
        "request": request,
        "query": q,
        "games": games,
        "min_players": min_players,
        "max_weight": max_weight,
        "min_rating": min_rating,
        "category": category,
        "result_count": len(games),
    })


@app.get("/game/{bgg_id}", response_class=HTMLResponse)
async def game_detail(request: Request, bgg_id: int):
    """개별 게임 상세 페이지"""
    result = collection.get(
        ids=[f"game_{bgg_id}"],
        include=["metadatas", "documents"],
    )

    if not result["metadatas"]:
        return HTMLResponse("<h1>게임을 찾을 수 없습니다</h1>", status_code=404)

    game = result["metadatas"][0]
    document = result["documents"][0] if result["documents"] else ""

    return templates.TemplateResponse("detail.html", {
        "request": request,
        "game": game,
        "document": document,
    })


@app.get("/browse", response_class=HTMLResponse)
async def browse(
    request: Request,
    page: int = Query(default=1, description="페이지"),
    sort_by: str = Query(default="rank", description="정렬 기준"),
):
    """전체 게임 목록 브라우징"""
    per_page = 50
    offset = (page - 1) * per_page

    # ChromaDB get으로 전체 조회 (페이징)
    all_games = collection.get(
        limit=per_page,
        offset=offset,
        include=["metadatas"],
    )

    games = all_games["metadatas"] if all_games["metadatas"] else []

    # 정렬
    if sort_by == "rank":
        games.sort(key=lambda x: x.get("rank_boardgame", 99999))
    elif sort_by == "rating":
        games.sort(key=lambda x: x.get("avg_rating", 0), reverse=True)
    elif sort_by == "weight":
        games.sort(key=lambda x: x.get("game_weight", 0), reverse=True)
    elif sort_by == "name":
        games.sort(key=lambda x: x.get("name", ""))

    total = collection.count()
    total_pages = (total + per_page - 1) // per_page

    return templates.TemplateResponse("browse.html", {
        "request": request,
        "games": games,
        "page": page,
        "total_pages": total_pages,
        "total_count": total,
        "sort_by": sort_by,
    })


@app.get("/table", response_class=HTMLResponse)
async def table_view(
    request: Request,
    page: int = Query(default=1, description="페이지"),
    per_page: int = Query(default=50, description="페이지당 행 수"),
    name_filter: str = Query(default="", description="이름 필터"),
):
    """DB 테이블 뷰 - 스프레드시트처럼 메타데이터 전체를 테이블로 보여줌"""
    total = collection.count()
    offset = (page - 1) * per_page

    if name_filter:
        # 이름 필터가 있으면 전체에서 검색 후 필터링
        # ChromaDB where 조건은 문자열 부분매칭을 지원하지 않으므로
        # 유사도 검색으로 이름 필터링 대체
        all_results = collection.query(
            query_texts=[name_filter],
            n_results=min(per_page, 200),
            include=["metadatas"],
        )
        games = all_results["metadatas"][0] if all_results["metadatas"] else []
        filtered_total = len(games)
        total_pages = 1
    else:
        result = collection.get(
            limit=per_page,
            offset=offset,
            include=["metadatas"],
        )
        games = result["metadatas"] if result["metadatas"] else []
        filtered_total = total
        total_pages = (total + per_page - 1) // per_page

    # 메타데이터 필드 목록 (테이블 컬럼 정보용)
    fields = []
    if games:
        fields = list(games[0].keys())

    return templates.TemplateResponse("table.html", {
        "request": request,
        "games": games,
        "page": page,
        "per_page": per_page,
        "total_count": filtered_total,
        "total_pages": total_pages,
        "fields": fields,
        "offset": offset,
        "name_filter": name_filter,
    })


@app.get("/stats", response_class=HTMLResponse)
async def stats(request: Request):
    """DB 통계 페이지"""
    total = collection.count()

    # 카테고리별 개수 조회
    categories = {}
    for cat_name, cat_field in [
        ("전략", "is_strategy"), ("가족", "is_family"),
        ("파티", "is_party"), ("테마틱", "is_thematic"),
        ("워게임", "is_war"), ("추상", "is_abstract"),
        ("어린이", "is_childrens"),
    ]:
        result = collection.get(
            where={cat_field: {"$eq": 1}},
            limit=1,
            include=["metadatas"],
        )
        # count를 직접 가져오기 어려우므로 get으로 확인
        count_result = collection.count()
        categories[cat_name] = cat_name  # 카테고리 존재 확인용

    return templates.TemplateResponse("stats.html", {
        "request": request,
        "total": total,
    })


# ============================================================
# 실행
# ============================================================
if __name__ == "__main__":
    import uvicorn
    print(f"🌐 웹 뷰어 시작: http://localhost:8000")
    print(f"   ChromaDB: {CHROMA_DIR}")
    print(f"   게임 수: {collection.count()}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
