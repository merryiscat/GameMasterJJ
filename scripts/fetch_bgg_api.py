"""
BGG XML API2로 전체 보드게임 데이터 수집 → ChromaDB 저장

기존 CSV의 BGGId 목록을 기반으로 BGG API에서 원본 데이터를 가져와
ChromaDB에 OpenAI 임베딩으로 저장합니다.

특징:
- 중간 저장(checkpoint): JSON으로 진행 상황 저장, 중단 후 이어서 가능
- Rate limit 대응: 요청 간 5초 대기, 202 응답 시 재시도
- OpenAI text-embedding-3-small 임베딩 사용

사용법:
    uv run python scripts/fetch_bgg_api.py          # 처음부터 수집
    uv run python scripts/fetch_bgg_api.py --resume  # 이어서 수집

예상 시간: 약 2~3시간 (21,925개 게임)
예상 비용: OpenAI 임베딩 ~$0.15
"""

import requests
import xml.etree.ElementTree as ET
import json
import time
import os
import sys
import csv

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 설정
# ============================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "reference", "archive")
CHROMA_DIR = os.path.join(PROJECT_ROOT, "chroma_db")

# 체크포인트 파일 (수집 진행 상황 저장)
CHECKPOINT_DIR = os.path.join(PROJECT_ROOT, "reference", "checkpoint")
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, "fetch_progress.json")
GAMES_CACHE_FILE = os.path.join(CHECKPOINT_DIR, "games_cache.jsonl")

# BGG API 설정
BGG_API_BASE = "https://boardgamegeek.com/xmlapi2"
BATCH_SIZE = 20          # BGG API 한번에 최대 20개
REQUEST_DELAY = 5        # 요청 간 대기 시간(초)
MAX_RETRIES = 3          # 실패 시 재시도 횟수
RETRY_DELAY = 30         # 재시도 대기 시간(초) - 202 응답 등

# ChromaDB 배치 크기 (임베딩 API 호출 단위)
CHROMA_BATCH_SIZE = 100


def load_bgg_ids() -> list[int]:
    """CSV에서 BGGId 목록 추출"""
    ids = []
    csv_path = os.path.join(DATA_DIR, "games.csv")
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ids.append(int(row["BGGId"]))
    return sorted(ids)


def load_mechanics_map() -> dict:
    """CSV에서 게임별 메카니즘 매핑 로드 (API에 없는 데이터 보충용)"""
    csv_path = os.path.join(DATA_DIR, "mechanics.csv")
    result = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames[1:]  # BGGId 제외
        for row in reader:
            bgg_id = int(row["BGGId"])
            mechs = [col for col in cols if row[col] == "1"]
            result[bgg_id] = ", ".join(mechs)
    return result


def load_themes_map() -> dict:
    """CSV에서 게임별 테마 매핑 로드"""
    csv_path = os.path.join(DATA_DIR, "themes.csv")
    result = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames[1:]
        for row in reader:
            bgg_id = int(row["BGGId"])
            themes = [col.replace("Theme_", "") for col in cols if row[col] == "1"]
            result[bgg_id] = ", ".join(themes)
    return result


def load_subcategories_map() -> dict:
    """CSV에서 게임별 서브카테고리 매핑 로드"""
    csv_path = os.path.join(DATA_DIR, "subcategories.csv")
    result = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames[1:]
        for row in reader:
            bgg_id = int(row["BGGId"])
            subs = [col for col in cols if row[col] == "1"]
            result[bgg_id] = ", ".join(subs)
    return result


def load_csv_extra() -> dict:
    """CSV에서 API에 없는 추가 필드 로드 (카테고리 플래그 등)"""
    csv_path = os.path.join(DATA_DIR, "games.csv")
    result = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bgg_id = int(row["BGGId"])
            result[bgg_id] = {
                "is_strategy": int(row.get("Cat:Strategy", 0)),
                "is_family": int(row.get("Cat:Family", 0)),
                "is_party": int(row.get("Cat:Party", 0)),
                "is_thematic": int(row.get("Cat:Thematic", 0)),
                "is_war": int(row.get("Cat:War", 0)),
                "is_abstract": int(row.get("Cat:Abstract", 0)),
                "is_childrens": int(row.get("Cat:Childrens", 0)),
            }
    return result


# ============================================================
# BGG API 호출
# ============================================================
def fetch_batch(game_ids: list[int]) -> list[dict] | None:
    """
    BGG API에서 게임 배치 가져오기

    Returns: 파싱된 게임 딕셔너리 리스트, 실패 시 None
    """
    ids_str = ",".join(str(gid) for gid in game_ids)
    url = f"{BGG_API_BASE}/thing?id={ids_str}&stats=1"

    # BGG API 인증 헤더 (2025년부터 필수)
    bgg_token = os.getenv("BGG_API_TOKEN", "")
    headers = {}
    if bgg_token:
        headers["Authorization"] = f"Bearer {bgg_token}"

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=headers, timeout=60)

            # 202 = "아직 준비 안됨, 나중에 다시 요청하세요"
            if resp.status_code == 202:
                print(f"      202 응답 - {RETRY_DELAY}초 후 재시도 ({attempt+1}/{MAX_RETRIES})")
                time.sleep(RETRY_DELAY)
                continue

            # 429 = Too Many Requests
            if resp.status_code == 429:
                wait = RETRY_DELAY * 2
                print(f"      429 Rate Limited - {wait}초 대기")
                time.sleep(wait)
                continue

            resp.raise_for_status()

            # XML 파싱
            games = parse_api_response(resp.text)
            return games

        except requests.exceptions.RequestException as e:
            print(f"      요청 오류: {e} - {RETRY_DELAY}초 후 재시도")
            time.sleep(RETRY_DELAY)
            continue

    print(f"      !! {MAX_RETRIES}회 시도 실패, 이 배치 건너뜀")
    return None


def parse_api_response(xml_text: str) -> list[dict]:
    """BGG XML API 응답 파싱"""
    root = ET.fromstring(xml_text)
    games = []

    for item in root.findall("item"):
        game = {}

        game["bgg_id"] = int(item.get("id"))
        game["type"] = item.get("type", "boardgame")

        # 이름 (primary + 한국어/기타 alternate)
        primary_name = ""
        alternate_names = []
        korean_name = ""
        for name_el in item.findall("name"):
            name_type = name_el.get("type")
            name_val = name_el.get("value", "")
            if name_type == "primary":
                primary_name = name_val
            elif name_type == "alternate":
                alternate_names.append(name_val)
                # 한국어 이름 감지 (한글 포함 여부)
                if any('\uac00' <= c <= '\ud7a3' for c in name_val):
                    korean_name = name_val

        game["name"] = primary_name
        game["korean_name"] = korean_name
        game["alternate_names"] = alternate_names

        # 기본 수치
        game["year_published"] = _attr_int(item, "yearpublished")
        game["min_players"] = _attr_int(item, "minplayers")
        game["max_players"] = _attr_int(item, "maxplayers")
        game["playing_time"] = _attr_int(item, "playingtime")
        game["min_playtime"] = _attr_int(item, "minplaytime")
        game["max_playtime"] = _attr_int(item, "maxplaytime")
        game["min_age"] = _attr_int(item, "minage")

        # 원본 설명 (핵심! CSV에는 lemmatized된 텍스트만 있었음)
        desc_el = item.find("description")
        game["description"] = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

        # 이미지
        game["thumbnail"] = _elem_text(item, "thumbnail")
        game["image"] = _elem_text(item, "image")

        # 카테고리, 메카니즘 (API에서 직접 가져오기)
        game["api_categories"] = _links(item, "boardgamecategory")
        game["api_mechanics"] = _links(item, "boardgamemechanic")
        game["designers"] = _links(item, "boardgamedesigner")
        game["publishers"] = _links(item, "boardgamepublisher")
        game["families"] = _links(item, "boardgamefamily")

        # 통계
        ratings = item.find(".//ratings")
        if ratings is not None:
            game["avg_rating"] = _attr_float(ratings, "average")
            game["bayes_rating"] = _attr_float(ratings, "bayesaverage")
            game["num_ratings"] = _attr_int(ratings, "usersrated")
            game["game_weight"] = _attr_float(ratings, "averageweight")
            game["num_owned"] = _attr_int(ratings, "owned")
            game["rank_boardgame"] = _get_rank(ratings, "boardgame")

        games.append(game)

    return games


def _attr_int(parent, tag, default=0):
    el = parent.find(tag)
    if el is not None:
        try:
            return int(el.get("value", default))
        except (ValueError, TypeError):
            return default
    return default


def _attr_float(parent, tag, default=0.0):
    el = parent.find(tag)
    if el is not None:
        try:
            return float(el.get("value", default))
        except (ValueError, TypeError):
            return default
    return default


def _elem_text(parent, tag):
    el = parent.find(tag)
    return el.text.strip() if el is not None and el.text else ""


def _links(item, link_type):
    return [link.get("value", "") for link in item.findall("link") if link.get("type") == link_type]


def _get_rank(ratings, rank_type):
    for rank in ratings.findall(".//rank"):
        if rank.get("name") == rank_type:
            val = rank.get("value")
            if val and val != "Not Ranked":
                return int(val)
    return 0


# ============================================================
# 체크포인트 (중단/재시작 지원)
# ============================================================
def load_checkpoint() -> dict:
    """이전 진행 상황 로드"""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    return {"completed_batches": 0, "total_games_fetched": 0}


def save_checkpoint(batch_idx: int, total_fetched: int):
    """진행 상황 저장"""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({
            "completed_batches": batch_idx,
            "total_games_fetched": total_fetched,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, f)


def append_games_cache(games: list[dict]):
    """수집된 게임을 JSONL 파일에 추가 저장 (원본 보존)"""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    with open(GAMES_CACHE_FILE, "a", encoding="utf-8") as f:
        for game in games:
            # JSON 직렬화 가능하도록 정리
            f.write(json.dumps(game, ensure_ascii=False) + "\n")


def load_games_cache() -> list[dict]:
    """캐시된 게임 데이터 전체 로드"""
    games = []
    if os.path.exists(GAMES_CACHE_FILE):
        with open(GAMES_CACHE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    games.append(json.loads(line))
    return games


# ============================================================
# ChromaDB 저장
# ============================================================
def build_document(game: dict, mechanics_str: str = "", themes_str: str = "") -> str:
    """ChromaDB document 텍스트 생성 (임베딩 대상)"""
    parts = []

    # 게임 이름 (한국어 이름이 있으면 같이)
    name = game.get("name", "")
    korean = game.get("korean_name", "")
    if korean:
        parts.append(f"Game: {name} ({korean})")
    else:
        parts.append(f"Game: {name}")

    # 원본 설명 (최대 800자 - API에서 가져온 깨끗한 텍스트)
    desc = game.get("description", "")
    if desc:
        # HTML 태그 간단 제거
        import re
        clean_desc = re.sub(r'<[^>]+>', '', desc)
        clean_desc = re.sub(r'&[a-zA-Z]+;', ' ', clean_desc)
        parts.append(f"Description: {clean_desc[:800]}")

    # 인원/시간
    min_p = game.get("min_players", 0)
    max_p = game.get("max_players", 0)
    if min_p and max_p:
        parts.append(f"Players: {min_p}-{max_p}")

    playtime = game.get("playing_time", 0)
    if playtime:
        parts.append(f"Play time: {playtime} minutes")

    # API에서 가져온 카테고리/메카니즘
    api_cats = game.get("api_categories", [])
    if api_cats:
        parts.append(f"Categories: {', '.join(api_cats)}")

    api_mechs = game.get("api_mechanics", [])
    if api_mechs:
        parts.append(f"Mechanics: {', '.join(api_mechs)}")

    # CSV 보충 데이터
    if themes_str:
        parts.append(f"Themes: {themes_str}")

    return "\n".join(parts)


def build_metadata(game: dict, csv_extra: dict, mechanics_str: str, themes_str: str, subcats_str: str) -> dict:
    """ChromaDB 메타데이터 생성"""
    return {
        "bgg_id": game.get("bgg_id", 0),
        "name": game.get("name", ""),
        "korean_name": game.get("korean_name", ""),
        "year_published": game.get("year_published", 0),
        "game_weight": game.get("game_weight", 0.0),
        "avg_rating": game.get("avg_rating", 0.0),
        "min_players": game.get("min_players", 0),
        "max_players": game.get("max_players", 0),
        "playtime": game.get("playing_time", 0),
        "num_owned": game.get("num_owned", 0),
        "rank_boardgame": game.get("rank_boardgame", 0),
        "mechanics": mechanics_str or ", ".join(game.get("api_mechanics", [])),
        "themes": themes_str,
        "subcategories": subcats_str,
        "image_url": game.get("image", ""),
        "thumbnail_url": game.get("thumbnail", ""),
        # 카테고리 플래그 (CSV에서)
        "is_strategy": csv_extra.get("is_strategy", 0),
        "is_family": csv_extra.get("is_family", 0),
        "is_party": csv_extra.get("is_party", 0),
        "is_thematic": csv_extra.get("is_thematic", 0),
        "is_war": csv_extra.get("is_war", 0),
        "is_abstract": csv_extra.get("is_abstract", 0),
        "is_childrens": csv_extra.get("is_childrens", 0),
    }


def save_to_chromadb(all_games: list[dict], mechanics_map: dict, themes_map: dict, subcats_map: dict, csv_extras: dict):
    """수집된 전체 게임을 ChromaDB에 저장"""
    print(f"\n{'='*60}")
    print(f"ChromaDB 저장 시작 ({len(all_games)}개 게임)")
    print(f"{'='*60}")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("!! OPENAI_API_KEY가 없습니다. .env 파일을 확인하세요.")
        return

    client = chromadb.PersistentClient(path=CHROMA_DIR)

    openai_ef = OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name="text-embedding-3-small"
    )

    # 기존 컬렉션 삭제 후 새로 생성
    try:
        client.delete_collection("boardgames")
        print("   기존 boardgames 컬렉션 삭제")
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name="boardgames",
        embedding_function=openai_ef,
        metadata={"hnsw:space": "cosine"}
    )

    # 중복 제거 (같은 BGGId가 여러번 캐시에 있을 수 있음)
    seen = set()
    unique_games = []
    for g in all_games:
        bid = g.get("bgg_id")
        if bid and bid not in seen:
            seen.add(bid)
            unique_games.append(g)

    total = len(unique_games)
    start_time = time.time()
    print(f"   중복 제거 후: {total}개 게임")

    for i in range(0, total, CHROMA_BATCH_SIZE):
        batch = unique_games[i:i + CHROMA_BATCH_SIZE]

        ids = []
        documents = []
        metadatas = []

        for game in batch:
            bgg_id = game["bgg_id"]
            ids.append(f"game_{bgg_id}")

            mech_str = mechanics_map.get(bgg_id, "")
            theme_str = themes_map.get(bgg_id, "")
            subcat_str = subcats_map.get(bgg_id, "")
            extra = csv_extras.get(bgg_id, {})

            documents.append(build_document(game, mech_str, theme_str))
            metadatas.append(build_metadata(game, extra, mech_str, theme_str, subcat_str))

        collection.add(ids=ids, documents=documents, metadatas=metadatas)

        done = min(i + CHROMA_BATCH_SIZE, total)
        elapsed = time.time() - start_time
        pct = (done / total) * 100
        bar_width = 30
        filled = int(bar_width * done / total)
        bar = "█" * filled + "░" * (bar_width - filled)
        print(f"\r   {bar} {pct:5.1f}% [{done}/{total}] ({elapsed:.1f}s)    ",
              end="", flush=True)

    print()  # 프로그레스 바 줄바꿈
    elapsed = time.time() - start_time
    print(f"\n   ChromaDB 저장 완료! {collection.count()}개 게임, {elapsed:.1f}s")


# ============================================================
# 메인 실행
# ============================================================
def main():
    is_resume = "--resume" in sys.argv

    print("=" * 60)
    print("BGG XML API2 -> ChromaDB (OpenAI Embedding)")
    print("=" * 60)

    # 0. API 키 확인
    if not os.getenv("BGG_API_TOKEN"):
        print("\n!! BGG_API_TOKEN이 .env에 없습니다.")
        print("   https://boardgamegeek.com/applications 에서 발급 후")
        print("   .env 파일에 BGG_API_TOKEN=발급받은토큰 추가하세요.")
        return

    if not os.getenv("OPENAI_API_KEY"):
        print("\n!! OPENAI_API_KEY가 .env에 없습니다.")
        return

    # 1. BGG ID 목록 로드
    all_ids = load_bgg_ids()
    total_ids = len(all_ids)
    print(f"\n   전체 게임: {total_ids}개")

    # 2. CSV 보충 데이터 로드
    print("   CSV 보충 데이터 로드 중...")
    mechanics_map = load_mechanics_map()
    themes_map = load_themes_map()
    subcats_map = load_subcategories_map()
    csv_extras = load_csv_extra()
    print("   CSV 데이터 로드 완료")

    # 3. 배치 분할
    batches = []
    for i in range(0, total_ids, BATCH_SIZE):
        batches.append(all_ids[i:i + BATCH_SIZE])
    total_batches = len(batches)
    print(f"   배치: {total_batches}개 (배치당 {BATCH_SIZE}개)")

    # 4. 체크포인트 확인
    start_batch = 0
    if is_resume:
        checkpoint = load_checkpoint()
        start_batch = checkpoint.get("completed_batches", 0)
        if start_batch > 0:
            print(f"   이전 진행 이어서 시작: 배치 {start_batch}/{total_batches}")
        else:
            print("   이전 체크포인트 없음, 처음부터 시작")
    else:
        # 처음부터 시작 - 캐시 파일 초기화
        if os.path.exists(GAMES_CACHE_FILE):
            os.remove(GAMES_CACHE_FILE)
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
        print("   처음부터 수집 시작")

    # 예상 시간
    remaining = total_batches - start_batch
    est_minutes = (remaining * REQUEST_DELAY) / 60
    print(f"   예상 소요: ~{est_minutes:.0f}분 ({remaining}개 배치 * {REQUEST_DELAY}s)")
    print(f"\n{'='*60}")

    # 5. API 수집
    total_fetched = 0
    failed_batches = []
    start_time = time.time()

    for batch_idx in range(start_batch, total_batches):
        batch_ids = batches[batch_idx]

        # 진행률 프로그레스 바
        elapsed = time.time() - start_time
        if batch_idx > start_batch:
            avg_time = elapsed / (batch_idx - start_batch)
            eta = avg_time * (total_batches - batch_idx)
            eta_str = f"ETA {eta/60:.0f}m"
        else:
            eta_str = "..."

        pct = ((batch_idx + 1) / total_batches) * 100
        bar_width = 30
        filled = int(bar_width * (batch_idx + 1) / total_batches)
        bar = "█" * filled + "░" * (bar_width - filled)
        print(f"\r   {bar} {pct:5.1f}% [{batch_idx+1}/{total_batches}] "
              f"fetched:{total_fetched} fail:{len(failed_batches)} {eta_str}    ",
              end="", flush=True)

        # API 호출
        games = fetch_batch(batch_ids)

        if games:
            append_games_cache(games)
            total_fetched += len(games)
        else:
            failed_batches.append(batch_idx)

        # 체크포인트 저장
        save_checkpoint(batch_idx + 1, total_fetched)

        # Rate limit 대기
        if batch_idx < total_batches - 1:
            time.sleep(REQUEST_DELAY)

    # 6. 수집 결과
    print()  # 프로그레스 바 줄바꿈
    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"API 수집 완료!")
    print(f"   수집: {total_fetched}개 게임")
    print(f"   실패 배치: {len(failed_batches)}개")
    print(f"   소요: {total_time/60:.1f}분")

    if failed_batches:
        print(f"   실패 배치 인덱스: {failed_batches[:20]}")

    # 7. ChromaDB에 저장
    print("\n   캐시에서 게임 데이터 로드 중...")
    all_games = load_games_cache()
    print(f"   캐시 로드: {len(all_games)}개")

    save_to_chromadb(all_games, mechanics_map, themes_map, subcats_map, csv_extras)

    print(f"\n{'='*60}")
    print("전체 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
