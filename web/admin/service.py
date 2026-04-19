"""
크롤링 어드민 Supabase 연동 서비스

Supabase 클라이언트를 통해 crawl_sources, crawl_jobs, games 테이블을 조회/수정합니다.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# .env에서 Supabase 연결 정보 로드
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def _get_client() -> Client:
    """Supabase 클라이언트 생성 (매번 새로 만들지 않고 캐싱)"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL 또는 SUPABASE_KEY가 설정되지 않았습니다. "
            ".env 파일을 확인하세요."
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ============================================================
# 대시보드 통계
# ============================================================
def get_dashboard_stats() -> dict:
    """
    대시보드에 표시할 통계 데이터를 가져옵니다.

    반환값:
        {
            "total_games": 전체 게임 수,
            "sources": [소스별 정보 리스트],
            "recent_jobs": [최근 배치 5건],
        }
    """
    sb = _get_client()

    # 전체 게임 수
    games_resp = sb.table("games").select("id", count="exact").execute()
    total_games = games_resp.count or 0

    # 소스 목록 (게임 수 포함)
    sources_resp = sb.table("crawl_sources").select("*").order("id").execute()
    sources = sources_resp.data or []

    # 최근 배치 실행 5건 (소스 이름도 함께)
    jobs_resp = (
        sb.table("crawl_jobs")
        .select("*, crawl_sources(display_name)")
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    recent_jobs = jobs_resp.data or []

    return {
        "total_games": total_games,
        "sources": sources,
        "recent_jobs": recent_jobs,
    }


# ============================================================
# 소스 관리
# ============================================================
def list_sources() -> list[dict]:
    """크롤링 소스 전체 목록을 가져옵니다."""
    sb = _get_client()
    resp = sb.table("crawl_sources").select("*").order("id").execute()
    return resp.data or []


def create_source(data: dict) -> dict:
    """
    새 크롤링 소스를 추가합니다.

    data 예시:
        {"name": "boardlife", "display_name": "보드라이프",
         "base_url": "https://...", "crawl_type": "scraping",
         "schedule": "weekly"}
    """
    sb = _get_client()
    resp = sb.table("crawl_sources").insert(data).execute()
    return resp.data[0] if resp.data else {}


def toggle_source(source_id: int) -> dict:
    """소스의 활성/비활성 상태를 토글합니다."""
    sb = _get_client()

    # 현재 상태 조회
    current = sb.table("crawl_sources").select("is_active").eq("id", source_id).execute()
    if not current.data:
        return {}

    # 반전 후 업데이트
    new_active = not current.data[0]["is_active"]
    resp = (
        sb.table("crawl_sources")
        .update({"is_active": new_active})
        .eq("id", source_id)
        .execute()
    )
    return resp.data[0] if resp.data else {}


# ============================================================
# 배치(Job) 관리
# ============================================================
def list_jobs(page: int = 1, per_page: int = 20) -> dict:
    """
    배치 실행 이력을 페이지 단위로 가져옵니다.

    반환값: {"jobs": [...], "total": 전체 수, "page": 현재 페이지}
    """
    sb = _get_client()
    offset = (page - 1) * per_page

    # 전체 수
    count_resp = sb.table("crawl_jobs").select("id", count="exact").execute()
    total = count_resp.count or 0

    # 목록 조회
    resp = (
        sb.table("crawl_jobs")
        .select("*, crawl_sources(display_name)")
        .order("created_at", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )

    return {
        "jobs": resp.data or [],
        "total": total,
        "page": page,
    }


def create_job(source_id: int, job_type: str = "manual") -> dict:
    """
    새 배치 작업 레코드를 생성합니다 (상태: pending).

    크롤링 실행 전에 먼저 레코드를 만들고,
    실제 크롤링은 백그라운드에서 별도 실행합니다.
    """
    sb = _get_client()
    data = {
        "source_id": source_id,
        "job_type": job_type,
        "status": "running",
        "started_at": datetime.now().isoformat(),
    }
    resp = sb.table("crawl_jobs").insert(data).execute()
    return resp.data[0] if resp.data else {}


# ============================================================
# 게임 관리
# ============================================================
def list_games(page: int = 1, search: str = "", per_page: int = 50) -> dict:
    """
    게임 목록을 페이지 단위로 가져옵니다.

    search가 있으면 name_ko 또는 name_en에서 검색합니다.

    반환값: {"games": [...], "total": 전체 수, "page": 현재 페이지, "total_pages": ...}
    """
    sb = _get_client()
    offset = (page - 1) * per_page

    # 기본 쿼리
    query = sb.table("games").select("*", count="exact")

    # 검색 필터
    if search:
        # name_ko 또는 name_en에서 ILIKE 검색
        query = query.or_(f"name_ko.ilike.%{search}%,name_en.ilike.%{search}%")

    # 정렬 + 페이지네이션
    query = query.order("id", desc=True).range(offset, offset + per_page - 1)

    resp = query.execute()
    total = resp.count or 0
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    return {
        "games": resp.data or [],
        "total": total,
        "page": page,
        "total_pages": total_pages,
    }


def get_game(game_id: int) -> dict | None:
    """게임 1건 조회"""
    sb = _get_client()
    resp = sb.table("games").select("*").eq("id", game_id).execute()
    return resp.data[0] if resp.data else None


def create_game(data: dict) -> dict:
    """게임 추가"""
    sb = _get_client()
    resp = sb.table("games").insert(data).execute()
    return resp.data[0] if resp.data else {}


def update_game(game_id: int, data: dict) -> dict:
    """게임 수정"""
    sb = _get_client()
    resp = sb.table("games").update(data).eq("id", game_id).execute()
    return resp.data[0] if resp.data else {}
