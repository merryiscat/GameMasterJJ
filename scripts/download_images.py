"""
게임 커버 이미지 다운로드 스크립트

game_images 테이블에서 source_url이 있고 local_path가 없는 이미지를 다운로드.
추후 배치 크롤링에 통합하여 신규 게임 이미지도 자동 수집.

사용법:
    uv run python scripts/download_images.py              # 전체 다운로드
    uv run python scripts/download_images.py --limit 100   # 100개만 테스트
    uv run python scripts/download_images.py --resume      # 미다운로드분만

결과물: data/images/cover/game_{id}.jpg
DB 업데이트: game_images.local_path = /static/images/cover/game_{id}.jpg
"""

import asyncio
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# ============================================================
# 경로 설정
# ============================================================
PROJECT_ROOT = Path(__file__).parent.parent
IMAGES_DIR = PROJECT_ROOT / "data" / "images" / "cover"

# FastAPI static 서빙 기준 경로
STATIC_PREFIX = "/static/images/cover"

# 동시 다운로드 수
MAX_CONCURRENT = 10
REQUEST_DELAY = 0.5  # 요청 간 대기 (초)


# ============================================================
# Supabase 연결
# ============================================================
def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("SUPABASE_URL, SUPABASE_KEY를 .env에 설정하세요!")
        sys.exit(1)
    return create_client(url, key)


# ============================================================
# 미다운로드 이미지 목록 조회
# ============================================================
def get_pending_images(sb, limit: int = 0) -> list[dict]:
    """
    local_path가 없는 cover 이미지 목록 조회
    추후 배치에서도 이 함수를 호출하면 신규 이미지만 가져옴
    """
    query = (
        sb.table("game_images")
        .select("id, game_id, source_url")
        .eq("image_type", "cover")
        .is_("local_path", "null")
    )

    if limit:
        query = query.limit(limit)

    # 페이지네이션 (Supabase 기본 1000개 제한)
    all_images = []
    offset = 0
    page_size = 1000

    while True:
        result = query.range(offset, offset + page_size - 1).execute()
        if not result.data:
            break
        all_images.extend(result.data)
        if limit and len(all_images) >= limit:
            all_images = all_images[:limit]
            break
        if len(result.data) < page_size:
            break
        offset += page_size

    return all_images


# ============================================================
# 이미지 다운로드
# ============================================================
async def download_images(images: list[dict]):
    """
    이미지 목록을 비동기로 다운로드 + DB 업데이트
    """
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    sb = get_supabase()

    total = len(images)
    success = 0
    fail = 0
    start_time = time.time()

    print(f"\n{'=' * 60}")
    print(f"이미지 다운로드 시작 ({total}개)")
    print(f"저장 경로: {IMAGES_DIR}")
    print(f"동시 요청: {MAX_CONCURRENT}개")
    print(f"{'=' * 60}")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def download_one(client: httpx.AsyncClient, img: dict) -> bool:
        """이미지 1개 다운로드 + DB 업데이트"""
        async with semaphore:
            game_id = img["game_id"]
            source_url = img["source_url"]
            img_id = img["id"]

            if not source_url:
                return False

            # 파일명: game_{id}.jpg
            ext = source_url.split(".")[-1].split("?")[0][:4]
            if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
                ext = "jpg"
            filename = f"game_{game_id}.{ext}"
            filepath = IMAGES_DIR / filename
            static_path = f"{STATIC_PREFIX}/{filename}"

            # 이미 파일이 있으면 DB만 업데이트
            if filepath.exists():
                try:
                    sb.table("game_images").update(
                        {"local_path": static_path}
                    ).eq("id", img_id).execute()
                except Exception:
                    pass
                return True

            try:
                resp = await client.get(source_url, follow_redirects=True)
                if resp.status_code != 200:
                    return False

                # 파일 저장
                with open(filepath, "wb") as f:
                    f.write(resp.content)

                # DB 업데이트
                sb.table("game_images").update(
                    {"local_path": static_path}
                ).eq("id", img_id).execute()

                await asyncio.sleep(REQUEST_DELAY)
                return True

            except Exception:
                return False

    # 배치 단위로 처리
    batch_size = 100
    async with httpx.AsyncClient(timeout=30) as client:
        for i in range(0, total, batch_size):
            batch = images[i:i + batch_size]

            tasks = [download_one(client, img) for img in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in results:
                if isinstance(r, bool) and r:
                    success += 1
                else:
                    fail += 1

            # 진행률
            done = min(i + batch_size, total)
            elapsed = time.time() - start_time
            pct = (done / total) * 100
            bar_width = 25
            filled = int(bar_width * done / total)
            bar = "█" * filled + "░" * (bar_width - filled)

            if done > 0:
                eta = (elapsed / done) * (total - done) / 60
            else:
                eta = 0

            print(f"\r   {bar} {pct:5.1f}% [{done}/{total}] "
                  f"성공:{success} 실패:{fail} ETA:{eta:.0f}분",
                  end="", flush=True)

    elapsed = time.time() - start_time
    print(f"\n\n{'=' * 60}")
    print(f"다운로드 완료!")
    print(f"   성공: {success}개")
    print(f"   실패: {fail}개")
    print(f"   소요: {elapsed / 60:.1f}분")
    print(f"   경로: {IMAGES_DIR}")
    print(f"{'=' * 60}")


# ============================================================
# 메인 실행
# ============================================================
def main():
    limit = 0
    for i, arg in enumerate(sys.argv):
        if arg == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])

    # --resume는 기본 동작 (local_path가 null인 것만 가져오므로)

    sb = get_supabase()

    print("=" * 60)
    print("게임 커버 이미지 다운로드")
    print("=" * 60)

    # 미다운로드 이미지 조회
    print("\n   미다운로드 이미지 조회 중...")
    images = get_pending_images(sb, limit=limit)
    print(f"   대상: {len(images)}개")

    if not images:
        print("   모든 이미지가 이미 다운로드되었습니다!")
        return

    asyncio.run(download_images(images))


if __name__ == "__main__":
    main()
