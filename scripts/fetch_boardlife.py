"""
보드라이프 보드게임 데이터 크롤링 스크립트

1단계: 랭킹 페이지를 순회하며 전체 게임 ID 수집
2단계: 각 게임 상세 페이지를 크롤링하여 JSONL로 저장

결과물: data/boardlife_games.jsonl (한 줄에 게임 하나)

사용법:
    uv run python scripts/fetch_boardlife.py              # 처음부터 크롤링
    uv run python scripts/fetch_boardlife.py --resume     # 이어서 크롤링
    uv run python scripts/fetch_boardlife.py --ids-only   # ID 수집만

주의:
    - 서버 부하 방지를 위해 요청 간 2초 대기
    - 중간 저장(체크포인트)으로 중단 후 이어서 가능
    - 예상 시간: ID 수집 ~5분, 상세 크롤링 ~10시간 (10,000개 기준)
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import httpx

from boardlife_parser import parse_game_detail, parse_rank_page

# ============================================================
# 경로 설정
# ============================================================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHECKPOINT_DIR = DATA_DIR / "checkpoint"

# 출력 파일
GAMES_JSONL = DATA_DIR / "boardlife_games.jsonl"
IDS_FILE = CHECKPOINT_DIR / "boardlife_ids.json"
PROGRESS_FILE = CHECKPOINT_DIR / "boardlife_progress.json"

# ============================================================
# 크롤링 설정
# ============================================================
BASE_URL = "https://boardlife.co.kr"

# 요청 간 대기 시간 (초) — 서버 부하 방지
REQUEST_DELAY = 2.0

# 동시 요청 수 (너무 높이면 차단될 수 있음)
MAX_CONCURRENT = 3

# 재시도 설정
MAX_RETRIES = 3
RETRY_DELAY = 10

# HTTP 클라이언트 설정
HEADERS = {
    "User-Agent": "GMJJ-BoardGameCrawler/1.0 (educational project)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


# ============================================================
# 1단계: 게임 ID 수집
# ============================================================
async def collect_game_ids(client: httpx.AsyncClient) -> list[str]:
    """
    랭킹 페이지를 순회하며 전체 게임 ID 수집

    /rank/all/1 → /rank/all/2 → ... → 빈 페이지까지
    """
    all_ids = []
    seen_ids = set()
    page = 1
    empty_count = 0  # 연속 빈 페이지 카운터

    print("=" * 60)
    print("1단계: 게임 ID 수집")
    print("=" * 60)

    while True:
        url = f"{BASE_URL}/rank/all/{page}"

        try:
            resp = await _fetch_with_retry(client, url)
            if resp is None:
                empty_count += 1
                if empty_count >= 3:
                    print(f"\n   연속 {empty_count}회 실패 — 수집 종료")
                    break
                page += 1
                continue

            games = parse_rank_page(resp.text)

            if not games:
                empty_count += 1
                if empty_count >= 3:
                    print(f"\n   연속 {empty_count}회 빈 페이지 — 수집 종료")
                    break
                page += 1
                await asyncio.sleep(REQUEST_DELAY)
                continue

            # 중복 제거하며 추가
            new_count = 0
            for g in games:
                gid = g["boardlife_id"]
                if gid not in seen_ids:
                    seen_ids.add(gid)
                    all_ids.append(gid)
                    new_count += 1

            # 신규 게임이 없으면 빈 페이지로 간주
            # (사이드바의 고정 링크만 잡히는 경우 대비)
            if new_count == 0:
                empty_count += 1
                if empty_count >= 3:
                    print(f"\n   연속 {empty_count}회 신규 게임 없음 — 수집 종료")
                    break
            else:
                empty_count = 0

            # 진행률 출력
            print(f"\r   페이지 {page:>4d} | "
                  f"이 페이지: {len(games):>3d}개 (신규 {new_count}) | "
                  f"누적: {len(all_ids):>6d}개",
                  end="", flush=True)

        except Exception as e:
            print(f"\n   페이지 {page} 오류: {e}")
            empty_count += 1
            if empty_count >= 3:
                break

        page += 1
        await asyncio.sleep(REQUEST_DELAY)

    print(f"\n\n   ID 수집 완료: {len(all_ids)}개 게임")

    # 저장
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    with open(IDS_FILE, "w", encoding="utf-8") as f:
        json.dump({"ids": all_ids, "total": len(all_ids),
                    "collected_at": time.strftime("%Y-%m-%d %H:%M:%S")}, f,
                   ensure_ascii=False, indent=2)
    print(f"   저장: {IDS_FILE}")

    return all_ids


# ============================================================
# 2단계: 게임 상세 크롤링
# ============================================================
async def crawl_game_details(client: httpx.AsyncClient, game_ids: list[str],
                              start_idx: int = 0):
    """
    게임 ID 목록을 순회하며 상세 페이지 크롤링 → JSONL 저장

    - 한 번에 MAX_CONCURRENT개씩 동시 요청
    - 각 배치 후 REQUEST_DELAY만큼 대기
    - 주기적으로 체크포인트 저장
    """
    total = len(game_ids)
    success = 0
    fail = 0
    start_time = time.time()

    print(f"\n{'=' * 60}")
    print(f"2단계: 게임 상세 크롤링")
    print(f"   전체: {total}개 | 시작 인덱스: {start_idx}")
    print(f"   동시 요청: {MAX_CONCURRENT}개 | 요청 간격: {REQUEST_DELAY}초")
    print(f"={'=' * 59}")

    # JSONL 파일 열기 (이어쓰기 모드)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    mode = "a" if start_idx > 0 else "w"

    # 세마포어로 동시 요청 수 제한
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def fetch_one(idx: int, game_id: str) -> dict | None:
        """게임 1개 크롤링"""
        async with semaphore:
            url = f"{BASE_URL}/game/{game_id}"
            try:
                resp = await _fetch_with_retry(client, url)
                if resp is None:
                    return None

                result = parse_game_detail(resp.text, game_id)
                await asyncio.sleep(REQUEST_DELAY)
                return result
            except Exception as e:
                print(f"\n   게임 {game_id} 오류: {e}")
                return None

    # 배치 단위로 처리 (체크포인트 저장을 위해)
    batch_size = 50  # 50개마다 체크포인트 저장
    with open(GAMES_JSONL, mode, encoding="utf-8") as f:
        for batch_start in range(start_idx, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_ids = game_ids[batch_start:batch_end]

            # 배치 내 동시 크롤링
            tasks = [
                fetch_one(batch_start + i, gid)
                for i, gid in enumerate(batch_ids)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 저장
            for result in results:
                if isinstance(result, Exception):
                    fail += 1
                    continue
                if result:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                    success += 1
                else:
                    fail += 1

            f.flush()  # 디스크에 즉시 반영

            # 체크포인트 저장
            _save_progress(batch_end, success, fail)

            # 진행률 출력
            elapsed = time.time() - start_time
            done = batch_end - start_idx
            if done > 0:
                rate = elapsed / done  # 게임당 소요 시간
                remaining = (total - batch_end) * rate
                eta_min = remaining / 60
            else:
                eta_min = 0

            pct = (batch_end / total) * 100
            bar_width = 30
            filled = int(bar_width * batch_end / total)
            bar = "█" * filled + "░" * (bar_width - filled)
            print(f"\r   {bar} {pct:5.1f}% [{batch_end}/{total}] "
                  f"성공:{success} 실패:{fail} "
                  f"ETA:{eta_min:.0f}분",
                  end="", flush=True)

    # 최종 결과
    elapsed = time.time() - start_time
    print(f"\n\n{'=' * 60}")
    print(f"크롤링 완료!")
    print(f"   성공: {success}개")
    print(f"   실패: {fail}개")
    print(f"   소요: {elapsed/60:.1f}분")
    print(f"   출력: {GAMES_JSONL}")
    print(f"={'=' * 59}")


# ============================================================
# 유틸리티
# ============================================================
async def _fetch_with_retry(client: httpx.AsyncClient, url: str,
                             retries: int = MAX_RETRIES) -> httpx.Response | None:
    """재시도 포함 HTTP GET 요청"""
    for attempt in range(retries):
        try:
            resp = await client.get(url, headers=HEADERS, follow_redirects=True)

            # 429 Too Many Requests
            if resp.status_code == 429:
                wait = RETRY_DELAY * (attempt + 1)
                print(f"\n   429 Rate Limited — {wait}초 대기")
                await asyncio.sleep(wait)
                continue

            # 404는 해당 게임이 없는 것
            if resp.status_code == 404:
                return None

            resp.raise_for_status()
            return resp

        except httpx.TimeoutException:
            print(f"\n   타임아웃 (시도 {attempt + 1}/{retries})")
            await asyncio.sleep(RETRY_DELAY)
        except httpx.HTTPError as e:
            print(f"\n   HTTP 오류: {e} (시도 {attempt + 1}/{retries})")
            await asyncio.sleep(RETRY_DELAY)

    return None


def _save_progress(completed: int, success: int, fail: int):
    """체크포인트 저장"""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump({
            "completed_idx": completed,
            "success": success,
            "fail": fail,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, f)


def _load_progress() -> dict:
    """체크포인트 로드"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"completed_idx": 0, "success": 0, "fail": 0}


def _load_ids() -> list[str]:
    """저장된 ID 목록 로드"""
    if IDS_FILE.exists():
        with open(IDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("ids", [])
    return []


# ============================================================
# 메인 실행
# ============================================================
async def main():
    is_resume = "--resume" in sys.argv
    ids_only = "--ids-only" in sys.argv

    print("=" * 60)
    print("보드라이프 보드게임 크롤러")
    print("=" * 60)

    # HTTP 클라이언트 (타임아웃 30초)
    async with httpx.AsyncClient(timeout=30) as client:

        # 1단계: 게임 ID 수집
        if is_resume and IDS_FILE.exists():
            game_ids = _load_ids()
            print(f"\n   저장된 ID 목록 로드: {len(game_ids)}개")
        else:
            game_ids = await collect_game_ids(client)

        if not game_ids:
            print("   수집된 게임 ID가 없습니다!")
            return

        if ids_only:
            print(f"\n   ID 수집 완료 ({len(game_ids)}개). --ids-only 플래그로 종료.")
            return

        # 2단계: 게임 상세 크롤링
        start_idx = 0
        if is_resume:
            progress = _load_progress()
            start_idx = progress.get("completed_idx", 0)
            if start_idx > 0:
                print(f"   이전 진행 이어서 시작: {start_idx}/{len(game_ids)}")

        await crawl_game_details(client, game_ids, start_idx)


if __name__ == "__main__":
    asyncio.run(main())
