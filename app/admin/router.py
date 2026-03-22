"""
크롤링 어드민 라우터

/admin 하위 페이지들을 관리합니다.
대시보드, 소스 관리, 배치 관리, 게임 관리 기능을 제공합니다.
"""

import os
import subprocess
import sys
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.admin import service

# ============================================================
# 라우터 및 템플릿 설정
# ============================================================
router = APIRouter(prefix="/admin", tags=["admin"])

# 어드민 전용 템플릿 디렉토리
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ============================================================
# 대시보드
# ============================================================
@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """어드민 대시보드 - 전체 현황 요약"""
    try:
        stats = service.get_dashboard_stats()
        error = None
    except Exception as e:
        stats = {"total_games": 0, "sources": [], "recent_jobs": []}
        error = str(e)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "error": error,
    })


# ============================================================
# 소스 관리
# ============================================================
@router.get("/sources", response_class=HTMLResponse)
async def sources_page(request: Request):
    """크롤링 소스 관리 페이지"""
    try:
        sources = service.list_sources()
        error = None
    except Exception as e:
        sources = []
        error = str(e)

    return templates.TemplateResponse("sources.html", {
        "request": request,
        "sources": sources,
        "error": error,
    })


@router.post("/sources")
async def create_source(
    request: Request,
    name: str = Form(...),
    display_name: str = Form(""),
    base_url: str = Form(""),
    crawl_type: str = Form("scraping"),
    schedule: str = Form("weekly"),
):
    """새 크롤링 소스 추가"""
    service.create_source({
        "name": name,
        "display_name": display_name or name,
        "base_url": base_url,
        "crawl_type": crawl_type,
        "schedule": schedule,
    })
    return RedirectResponse(url="/admin/sources", status_code=303)


@router.post("/sources/{source_id}/toggle")
async def toggle_source(source_id: int):
    """소스 활성/비활성 토글"""
    service.toggle_source(source_id)
    return RedirectResponse(url="/admin/sources", status_code=303)


# ============================================================
# 배치(Job) 관리
# ============================================================
@router.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request, page: int = 1):
    """배치 실행 이력 페이지"""
    try:
        sources = service.list_sources()
        result = service.list_jobs(page=page)
        error = None
    except Exception as e:
        sources = []
        result = {"jobs": [], "total": 0, "page": 1}
        error = str(e)

    return templates.TemplateResponse("jobs.html", {
        "request": request,
        "jobs": result["jobs"],
        "total": result["total"],
        "page": result["page"],
        "sources": sources,
        "error": error,
    })


@router.post("/jobs/run")
async def run_job(
    source_id: int = Form(...),
    job_type: str = Form("manual"),
):
    """
    수동 크롤링 실행

    1) crawl_jobs 레코드 생성
    2) fetch_boardlife.py를 백그라운드 프로세스로 실행
    """
    # 배치 레코드 생성
    service.create_job(source_id=source_id, job_type=job_type)

    # 프로젝트 루트 경로
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    script_path = os.path.join(project_root, "scripts", "fetch_boardlife.py")

    # 백그라운드에서 크롤링 스크립트 실행
    # (Windows: CREATE_NO_WINDOW, Unix: nohup 불필요 — subprocess가 부모와 분리됨)
    try:
        subprocess.Popen(
            [sys.executable, script_path],
            cwd=os.path.join(project_root, "scripts"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass  # 스크립트 실행 실패해도 페이지는 정상 동작

    return RedirectResponse(url="/admin/jobs", status_code=303)


# ============================================================
# 게임 관리
# ============================================================
@router.get("/games", response_class=HTMLResponse)
async def games_list(request: Request, page: int = 1, search: str = ""):
    """게임 목록 (검색 + 페이지네이션)"""
    try:
        result = service.list_games(page=page, search=search)
        error = None
    except Exception as e:
        result = {"games": [], "total": 0, "page": 1, "total_pages": 1}
        error = str(e)

    return templates.TemplateResponse("games_list.html", {
        "request": request,
        "games": result["games"],
        "total": result["total"],
        "page": result["page"],
        "total_pages": result["total_pages"],
        "search": search,
        "error": error,
    })


@router.get("/games/new", response_class=HTMLResponse)
async def game_new_form(request: Request):
    """게임 수동 추가 폼"""
    return templates.TemplateResponse("game_form.html", {
        "request": request,
        "game": None,  # 신규 모드
        "mode": "new",
    })


@router.post("/games")
async def game_create(
    request: Request,
    name_ko: str = Form(...),
    name_en: str = Form(""),
    year_published: str = Form(""),
    min_players: str = Form(""),
    max_players: str = Form(""),
    playtime: str = Form(""),
    rating: str = Form(""),
    difficulty: str = Form(""),
    language_dependency: str = Form(""),
    mechanisms: str = Form(""),
    categories: str = Form(""),
    designers: str = Form(""),
    publishers: str = Form(""),
    description_ko: str = Form(""),
    one_liner: str = Form(""),
):
    """게임 수동 저장"""
    data = _build_game_data(
        name_ko, name_en, year_published, min_players, max_players,
        playtime, rating, difficulty, language_dependency,
        mechanisms, categories, designers, publishers,
        description_ko, one_liner,
    )
    service.create_game(data)
    return RedirectResponse(url="/admin/games", status_code=303)


@router.get("/games/{game_id}/edit", response_class=HTMLResponse)
async def game_edit_form(request: Request, game_id: int):
    """게임 수정 폼"""
    game = service.get_game(game_id)
    if not game:
        return HTMLResponse("<h1>게임을 찾을 수 없습니다</h1>", status_code=404)

    return templates.TemplateResponse("game_form.html", {
        "request": request,
        "game": game,
        "mode": "edit",
    })


@router.post("/games/{game_id}")
async def game_update(
    request: Request,
    game_id: int,
    name_ko: str = Form(...),
    name_en: str = Form(""),
    year_published: str = Form(""),
    min_players: str = Form(""),
    max_players: str = Form(""),
    playtime: str = Form(""),
    rating: str = Form(""),
    difficulty: str = Form(""),
    language_dependency: str = Form(""),
    mechanisms: str = Form(""),
    categories: str = Form(""),
    designers: str = Form(""),
    publishers: str = Form(""),
    description_ko: str = Form(""),
    one_liner: str = Form(""),
):
    """게임 수정 저장"""
    data = _build_game_data(
        name_ko, name_en, year_published, min_players, max_players,
        playtime, rating, difficulty, language_dependency,
        mechanisms, categories, designers, publishers,
        description_ko, one_liner,
    )
    service.update_game(game_id, data)
    return RedirectResponse(url="/admin/games", status_code=303)


# ============================================================
# 유틸리티
# ============================================================
def _build_game_data(
    name_ko, name_en, year_published, min_players, max_players,
    playtime, rating, difficulty, language_dependency,
    mechanisms, categories, designers, publishers,
    description_ko, one_liner,
) -> dict:
    """
    폼 데이터를 DB 저장용 dict로 변환합니다.

    - 숫자 필드: 빈 문자열이면 None
    - 배열 필드: 쉼표로 분리하여 리스트로 변환
    """
    def _int_or_none(v):
        """문자열을 정수로 변환, 실패시 None"""
        try:
            return int(v) if v.strip() else None
        except (ValueError, AttributeError):
            return None

    def _float_or_none(v):
        """문자열을 실수로 변환, 실패시 None"""
        try:
            return float(v) if v.strip() else None
        except (ValueError, AttributeError):
            return None

    def _split_list(v):
        """쉼표로 구분된 문자열을 리스트로 변환 (빈 항목 제거)"""
        if not v or not v.strip():
            return []
        return [item.strip() for item in v.split(",") if item.strip()]

    return {
        "name_ko": name_ko.strip(),
        "name_en": name_en.strip() or None,
        "year_published": _int_or_none(year_published),
        "min_players": _int_or_none(min_players),
        "max_players": _int_or_none(max_players),
        "playtime": _int_or_none(playtime),
        "rating": _float_or_none(rating),
        "difficulty": _float_or_none(difficulty),
        "language_dependency": language_dependency.strip() or None,
        "mechanisms": _split_list(mechanisms),
        "categories": _split_list(categories),
        "designers": _split_list(designers),
        "publishers": _split_list(publishers),
        "description_ko": description_ko.strip() or None,
        "one_liner": one_liner.strip() or None,
    }
