"""
크롤링된 JSONL 데이터를 Supabase에 적재하는 스크립트

data/boardlife_games.jsonl → Supabase games + game_sources + game_images 테이블

사용법:
    uv run python scripts/load_to_supabase.py              # 전체 적재
    uv run python scripts/load_to_supabase.py --dry-run    # 미리보기 (실제 저장 안 함)
    uv run python scripts/load_to_supabase.py --limit 10   # 10개만 테스트

필수 환경변수 (.env):
    SUPABASE_URL=https://xxx.supabase.co
    SUPABASE_KEY=eyJ...  (service_role key 권장)
"""

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# ============================================================
# 경로 설정
# ============================================================
PROJECT_ROOT = Path(__file__).parent.parent
GAMES_JSONL = PROJECT_ROOT / "data" / "boardlife_games.jsonl"

# ============================================================
# Supabase 연결
# ============================================================
def get_supabase_client() -> Client:
    """Supabase 클라이언트 생성"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        print("SUPABASE_URL과 SUPABASE_KEY를 .env에 설정하세요!")
        print("  SUPABASE_URL=https://xxx.supabase.co")
        print("  SUPABASE_KEY=eyJ... (service_role key)")
        sys.exit(1)

    return create_client(url, key)


# ============================================================
# JSONL 로드
# ============================================================
def load_jsonl(limit: int = 0) -> list[dict]:
    """JSONL 파일에서 게임 데이터 로드"""
    if not GAMES_JSONL.exists():
        print(f"파일 없음: {GAMES_JSONL}")
        print("먼저 fetch_boardlife.py를 실행하세요.")
        sys.exit(1)

    games = []
    seen_ids = set()  # boardlife_id 기준 중복 제거
    skip = 0
    with open(GAMES_JSONL, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                game = json.loads(line)
            except json.JSONDecodeError:
                skip += 1
                continue
            # boardlife_id 기준 중복 제거 (마지막 크롤링 결과 사용)
            bid = game.get("boardlife_id", "")
            if bid in seen_ids:
                skip += 1
                continue
            seen_ids.add(bid)
            games.append(game)
            if limit and len(games) >= limit:
                break

    if skip:
        print(f"   건너뜀 (중복/파싱에러): {skip}줄")
    return games


# ============================================================
# 데이터 변환 (크롤링 데이터 → Supabase 테이블 형식)
# ============================================================
def to_games_row(game: dict) -> dict:
    """크롤링 데이터 → games 테이블 row"""
    return {
        "name_ko": game.get("name_ko", ""),
        "name_en": game.get("name_en"),
        "year_published": game.get("year_published"),
        "min_players": game.get("min_players"),
        "max_players": game.get("max_players"),
        "playtime": game.get("playtime"),

        "rating": game.get("rating"),
        "difficulty": game.get("difficulty"),
        "language_dependency": game.get("language_dependency"),
        "mechanisms": game.get("mechanisms", []),

        "categories": game.get("categories", []),
        "designers": game.get("designers", []),
        "publishers": game.get("publishers", []),
        "description_ko": game.get("description_ko"),
        "one_liner": game.get("one_liner"),
    }


def to_game_sources_row(game: dict, game_id: int) -> dict:
    """크롤링 데이터 → game_sources 테이블 row"""
    # 원본 크롤링 데이터 전체를 raw_data에 보존
    raw_data = {k: v for k, v in game.items()}

    return {
        "game_id": game_id,
        "source": "boardlife",
        "source_id": game.get("boardlife_id", ""),
        "source_url": game.get("source_url"),
        "source_rating": game.get("rating"),
        "raw_data": raw_data,
    }


def to_game_images_rows(game: dict, game_id: int) -> list[dict]:
    """크롤링 데이터 → game_images 테이블 rows"""
    rows = []

    # 커버 이미지
    if game.get("image_url"):
        rows.append({
            "game_id": game_id,
            "image_type": "cover",
            "source_url": game["image_url"],
        })

    # 썸네일
    if game.get("thumbnail_url"):
        rows.append({
            "game_id": game_id,
            "image_type": "thumbnail",
            "source_url": game["thumbnail_url"],
        })

    return rows


# ============================================================
# Supabase 적재
# ============================================================
def load_to_supabase(games: list[dict], dry_run: bool = False):
    """
    게임 데이터를 Supabase에 적재

    1. games 테이블에 삽입 → 자체 PK(id) 발급
    2. game_sources 테이블에 소스 매핑 삽입
    3. game_images 테이블에 이미지 URL 삽입
    """
    if dry_run:
        print("\n[DRY RUN] 실제 저장하지 않습니다.")
        for i, game in enumerate(games[:5]):
            print(f"\n  게임 {i+1}: {game.get('name_ko', '?')}")
            row = to_games_row(game)
            for k, v in row.items():
                if v is not None and v != [] and v != "":
                    print(f"    {k}: {v}")
        print(f"\n  ... 총 {len(games)}개 게임")
        return

    sb = get_supabase_client()

    total = len(games)
    success = 0
    skip = 0
    fail = 0
    start_time = time.time()

    print(f"\n{'=' * 60}")
    print(f"Supabase 적재 시작 ({total}개 게임)")
    print(f"{'=' * 60}")

    for i, game in enumerate(games):
        boardlife_id = game.get("boardlife_id", "")
        name = game.get("name_ko", "?")

        try:
            # 중복 체크: 같은 boardlife_id가 이미 있는지
            existing = sb.table("game_sources").select("id, game_id").eq(
                "source", "boardlife"
            ).eq("source_id", boardlife_id).execute()

            if existing.data:
                skip += 1
                continue

            # 1. games 테이블 삽입
            games_row = to_games_row(game)
            result = sb.table("games").insert(games_row).execute()

            if not result.data:
                print(f"\n   games 삽입 실패: {name}")
                fail += 1
                continue

            # 발급된 자체 PK
            game_id = result.data[0]["id"]

            # 2. game_sources 테이블 삽입
            source_row = to_game_sources_row(game, game_id)
            sb.table("game_sources").insert(source_row).execute()

            # 3. game_images 테이블 삽입
            image_rows = to_game_images_rows(game, game_id)
            for img_row in image_rows:
                try:
                    sb.table("game_images").insert(img_row).execute()
                except Exception:
                    pass  # 이미지 중복은 무시

            success += 1

        except Exception as e:
            print(f"\n   오류 [{name}]: {e}")
            fail += 1
            continue

        # 진행률 출력 (50개마다)
        if (i + 1) % 50 == 0 or i == total - 1:
            elapsed = time.time() - start_time
            pct = ((i + 1) / total) * 100
            print(f"\r   {pct:5.1f}% [{i+1}/{total}] "
                  f"성공:{success} 건너뜀:{skip} 실패:{fail} "
                  f"({elapsed:.0f}초)",
                  end="", flush=True)

    # 결과
    elapsed = time.time() - start_time
    print(f"\n\n{'=' * 60}")
    print(f"Supabase 적재 완료!")
    print(f"   성공: {success}개")
    print(f"   건너뜀 (중복): {skip}개")
    print(f"   실패: {fail}개")
    print(f"   소요: {elapsed:.1f}초")
    print(f"{'=' * 60}")


# ============================================================
# 메인 실행
# ============================================================
def main():
    dry_run = "--dry-run" in sys.argv
    limit = 0

    # --limit N 옵션 파싱
    for i, arg in enumerate(sys.argv):
        if arg == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])

    print("=" * 60)
    print("JSONL → Supabase 적재")
    print("=" * 60)

    # 1. JSONL 로드
    print(f"\n   JSONL 로드: {GAMES_JSONL}")
    games = load_jsonl(limit=limit)
    print(f"   로드 완료: {len(games)}개 게임")

    if not games:
        print("   데이터 없음!")
        return

    # 2. Supabase 적재
    load_to_supabase(games, dry_run=dry_run)


if __name__ == "__main__":
    main()
