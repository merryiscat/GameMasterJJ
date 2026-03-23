"""
BGG 보드게임 데이터를 ChromaDB에 로드하는 스크립트

CSV 파일들(games, mechanics, themes, subcategories)을 읽어서
ChromaDB 벡터 데이터베이스에 저장합니다.
OpenAI text-embedding-3-small 모델을 사용합니다.

사용법:
    uv run python scripts/load_to_chroma.py
"""

import pandas as pd
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv
import time
import os

# .env 파일에서 API 키 로드
load_dotenv()

# ============================================================
# 경로 설정
# ============================================================
# 프로젝트 루트 기준으로 경로 설정
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "reference", "archive")
CHROMA_DIR = os.path.join(PROJECT_ROOT, "chroma_db")

# CSV 파일 경로
GAMES_CSV = os.path.join(DATA_DIR, "games.csv")
MECHANICS_CSV = os.path.join(DATA_DIR, "mechanics.csv")
THEMES_CSV = os.path.join(DATA_DIR, "themes.csv")
SUBCATEGORIES_CSV = os.path.join(DATA_DIR, "subcategories.csv")


def load_games_df() -> pd.DataFrame:
    """games.csv 로드 및 기본 전처리"""
    print("📂 games.csv 로딩...")
    df = pd.read_csv(GAMES_CSV)
    print(f"   → 총 {len(df)}개 게임 로드됨")
    return df


def load_mechanics_df() -> pd.DataFrame:
    """mechanics.csv에서 게임별 메카니즘 목록 추출"""
    print("📂 mechanics.csv 로딩...")
    df = pd.read_csv(MECHANICS_CSV)

    # binary flag 컬럼들 → 해당하는 메카니즘 이름 리스트로 변환
    # 첫 번째 컬럼(BGGId) 제외한 나머지가 메카니즘 이름
    mechanic_cols = df.columns[1:]  # BGGId 제외

    # 각 게임마다 값이 1인 메카니즘 이름들을 쉼표로 연결
    def get_mechanics(row):
        return ", ".join([col for col in mechanic_cols if row[col] == 1])

    result = pd.DataFrame({
        "BGGId": df["BGGId"],
        "mechanics": df.apply(get_mechanics, axis=1)
    })
    print(f"   → 메카니즘 데이터 처리 완료")
    return result


def load_themes_df() -> pd.DataFrame:
    """themes.csv에서 게임별 테마 목록 추출"""
    print("📂 themes.csv 로딩...")
    df = pd.read_csv(THEMES_CSV)
    theme_cols = df.columns[1:]

    def get_themes(row):
        # "Theme_" 접두사 제거해서 깔끔하게
        themes = []
        for col in theme_cols:
            if row[col] == 1:
                clean_name = col.replace("Theme_", "")
                themes.append(clean_name)
        return ", ".join(themes)

    result = pd.DataFrame({
        "BGGId": df["BGGId"],
        "themes": df.apply(get_themes, axis=1)
    })
    print(f"   → 테마 데이터 처리 완료")
    return result


def load_subcategories_df() -> pd.DataFrame:
    """subcategories.csv에서 게임별 서브카테고리 추출"""
    print("📂 subcategories.csv 로딩...")
    df = pd.read_csv(SUBCATEGORIES_CSV)
    subcat_cols = df.columns[1:]

    def get_subcategories(row):
        return ", ".join([col for col in subcat_cols if row[col] == 1])

    result = pd.DataFrame({
        "BGGId": df["BGGId"],
        "subcategories": df.apply(get_subcategories, axis=1)
    })
    print(f"   → 서브카테고리 데이터 처리 완료")
    return result


def merge_all_data() -> pd.DataFrame:
    """모든 CSV 데이터를 하나의 DataFrame으로 병합"""
    games = load_games_df()
    mechanics = load_mechanics_df()
    themes = load_themes_df()
    subcategories = load_subcategories_df()

    # BGGId 기준으로 전부 합치기
    merged = games.merge(mechanics, on="BGGId", how="left")
    merged = merged.merge(themes, on="BGGId", how="left")
    merged = merged.merge(subcategories, on="BGGId", how="left")

    # 빈 값 채우기
    merged["mechanics"] = merged["mechanics"].fillna("")
    merged["themes"] = merged["themes"].fillna("")
    merged["subcategories"] = merged["subcategories"].fillna("")

    print(f"\n✅ 데이터 병합 완료: {len(merged)}개 게임")
    return merged


def build_document(row) -> str:
    """
    ChromaDB에 저장할 document 텍스트 생성

    이 텍스트가 임베딩(벡터)으로 변환되어 유사도 검색에 사용됨.
    게임 이름, 설명, 메카니즘, 테마 등을 조합해서
    "이런 느낌의 게임 추천해줘"라는 질문에 잘 매칭되도록 구성
    """
    parts = []

    # 게임 이름
    name = row.get("Name", "")
    if name:
        parts.append(f"게임 이름: {name}")

    # 게임 설명 (description은 이미 lemmatized 되어있음)
    desc = row.get("Description", "")
    if desc:
        # 설명이 너무 길면 500자로 자르기 (임베딩 효율)
        parts.append(f"설명: {str(desc)[:500]}")

    # 인원
    min_p = row.get("MinPlayers", "")
    max_p = row.get("MaxPlayers", "")
    if min_p and max_p:
        parts.append(f"인원: {min_p}~{max_p}명")

    # 메카니즘 (게임의 핵심 시스템)
    mechanics = row.get("mechanics", "")
    if mechanics:
        parts.append(f"메카니즘: {mechanics}")

    # 테마 (게임의 배경/세계관)
    themes = row.get("themes", "")
    if themes:
        parts.append(f"테마: {themes}")

    # 서브카테고리
    subcategories = row.get("subcategories", "")
    if subcategories:
        parts.append(f"카테고리: {subcategories}")

    return "\n".join(parts)


def build_metadata(row) -> dict:
    """
    ChromaDB 메타데이터 생성

    메타데이터는 필터링에 사용됨.
    예: "2인 이상 플레이 가능한 전략 게임" → where 조건으로 필터
    주의: ChromaDB 메타데이터는 str, int, float, bool만 지원
    """
    def safe_float(val, default=0.0):
        """안전하게 float 변환 (빈값/에러 방지)"""
        try:
            result = float(val)
            # NaN 체크
            if result != result:
                return default
            return result
        except (ValueError, TypeError):
            return default

    def safe_int(val, default=0):
        """안전하게 int 변환"""
        try:
            result = int(float(val))
            return result
        except (ValueError, TypeError):
            return default

    return {
        "bgg_id": safe_int(row.get("BGGId")),
        "name": str(row.get("Name", "")),
        "year_published": safe_int(row.get("YearPublished")),
        "game_weight": safe_float(row.get("GameWeight")),       # 난이도 1~5
        "avg_rating": safe_float(row.get("AvgRating")),         # 평균 평점
        "min_players": safe_int(row.get("MinPlayers")),
        "max_players": safe_int(row.get("MaxPlayers")),
        "playtime": safe_int(row.get("MfgPlaytime")),           # 플레이 시간(분)
        "num_owned": safe_int(row.get("NumOwned")),             # 소유자 수 (인기도)
        "rank_boardgame": safe_int(row.get("Rank:boardgame")),  # BGG 전체 랭킹
        "mechanics": str(row.get("mechanics", "")),
        "themes": str(row.get("themes", "")),
        "subcategories": str(row.get("subcategories", "")),
        "image_url": str(row.get("ImagePath", "")),
        # 카테고리 플래그 (필터링용)
        "is_strategy": safe_int(row.get("Cat:Strategy")),
        "is_family": safe_int(row.get("Cat:Family")),
        "is_party": safe_int(row.get("Cat:Party")),
        "is_thematic": safe_int(row.get("Cat:Thematic")),
        "is_war": safe_int(row.get("Cat:War")),
        "is_abstract": safe_int(row.get("Cat:Abstract")),
        "is_childrens": safe_int(row.get("Cat:Childrens")),
    }


def load_to_chromadb(df: pd.DataFrame, batch_size: int = 500):
    """
    DataFrame을 ChromaDB에 배치로 저장

    한번에 다 넣으면 메모리 문제가 생길 수 있어서
    batch_size 단위로 나눠서 저장
    """
    print(f"\n🗄️  ChromaDB 초기화 (저장 경로: {CHROMA_DIR})")
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # OpenAI 임베딩 함수 설정
    openai_ef = OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name="text-embedding-3-small"  # 가성비 좋은 모델 ($0.02/1M tokens)
    )

    # 기존 컬렉션 있으면 삭제 후 재생성 (깨끗하게 시작)
    try:
        client.delete_collection("boardgames")
        print("   → 기존 boardgames 컬렉션 삭제")
    except Exception:
        pass

    # 컬렉션 생성 (cosine 유사도 + OpenAI 임베딩)
    collection = client.get_or_create_collection(
        name="boardgames",
        embedding_function=openai_ef,
        metadata={"hnsw:space": "cosine"}
    )

    total = len(df)
    start_time = time.time()

    print(f"\n📥 데이터 저장 시작 ({total}개, 배치 크기: {batch_size})")

    for i in range(0, total, batch_size):
        batch = df.iloc[i:i + batch_size]

        ids = []
        documents = []
        metadatas = []

        for _, row in batch.iterrows():
            # ID는 "game_{BGGId}" 형태
            game_id = f"game_{int(row['BGGId'])}"
            ids.append(game_id)

            # 검색용 document 텍스트
            documents.append(build_document(row))

            # 필터링용 메타데이터
            metadatas.append(build_metadata(row))

        # ChromaDB에 배치 추가
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        # 진행률 표시
        done = min(i + batch_size, total)
        elapsed = time.time() - start_time
        pct = (done / total) * 100
        print(f"   [{done:>6}/{total}] {pct:5.1f}% ({elapsed:.1f}초)")

    elapsed = time.time() - start_time
    print(f"\n✅ ChromaDB 저장 완료!")
    print(f"   → 총 {collection.count()}개 게임")
    print(f"   → 소요 시간: {elapsed:.1f}초")
    print(f"   → 저장 경로: {CHROMA_DIR}")

    return collection


def verify_data(collection):
    """저장된 데이터 간단 검증"""
    print(f"\n🔍 데이터 검증")
    print(f"   → 저장된 게임 수: {collection.count()}")

    # 샘플 조회
    sample = collection.get(limit=3, include=["metadatas"])
    print(f"\n   📋 샘플 3개:")
    for meta in sample["metadatas"]:
        print(f"      - {meta['name']} (BGG #{meta['rank_boardgame']}, "
              f"평점 {meta['avg_rating']:.1f}, 난이도 {meta['game_weight']:.1f})")

    # 유사도 검색 테스트
    print(f"\n   🔎 유사도 검색 테스트: '협력형 판타지 모험 게임'")
    results = collection.query(
        query_texts=["cooperative fantasy adventure game"],
        n_results=5,
    )
    print(f"   검색 결과 Top 5:")
    for i, meta in enumerate(results["metadatas"][0]):
        dist = results["distances"][0][i]
        print(f"      {i+1}. {meta['name']} (유사도: {1-dist:.3f}, "
              f"평점 {meta['avg_rating']:.1f})")

    # 필터 검색 테스트
    print(f"\n   🔎 필터 검색 테스트: 2인 전략게임, 난이도 3.0+")
    results = collection.query(
        query_texts=["strategy game for two players"],
        n_results=5,
        where={
            "$and": [
                {"min_players": {"$lte": 2}},
                {"game_weight": {"$gte": 3.0}},
                {"is_strategy": {"$eq": 1}},
            ]
        }
    )
    print(f"   검색 결과 Top 5:")
    for i, meta in enumerate(results["metadatas"][0]):
        dist = results["distances"][0][i]
        print(f"      {i+1}. {meta['name']} ({meta['min_players']}~{meta['max_players']}명, "
              f"난이도 {meta['game_weight']:.1f}, 유사도: {1-dist:.3f})")


if __name__ == "__main__":
    print("=" * 60)
    print("🎲 BGG 보드게임 데이터 → ChromaDB 로드 (OpenAI 임베딩)")
    print("=" * 60)

    # API 키 확인
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY가 .env에 설정되지 않았습니다!")
        exit(1)

    # 1. 모든 CSV 데이터 병합
    merged_df = merge_all_data()

    # 2. ChromaDB에 저장 (배치 크기 줄임 - OpenAI API 속도 제한 대응)
    collection = load_to_chromadb(merged_df, batch_size=200)

    # 3. 검증
    verify_data(collection)

    print(f"\n{'=' * 60}")
    print("🎉 완료! OpenAI 임베딩으로 ChromaDB 저장 완료.")
    print("=" * 60)
