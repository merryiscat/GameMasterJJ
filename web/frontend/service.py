"""
사용자 프론트엔드 Supabase 서비스

게임 목록, 검색, 이미지 등 사용자 화면에 필요한 데이터를 조회합니다.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def _get_client() -> Client:
    """Supabase 클라이언트 생성"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL 또는 SUPABASE_KEY가 설정되지 않았습니다.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def list_games_with_images(
    page: int = 1,
    search: str = "",
    per_page: int = 20,
    category: str = "",
) -> dict:
    """
    게임 목록 + 썸네일 이미지를 함께 조회합니다.

    반환값: {
        "games": [게임 리스트 (image_url 포함)],
        "total": 전체 수,
        "page": 현재 페이지,
        "total_pages": 전체 페이지 수,
    }
    """
    sb = _get_client()
    offset = (page - 1) * per_page

    # 게임 + 이미지 조인 쿼리 (local_path 우선)
    query = sb.table("games").select(
        "id, name_ko, name_en, min_players, max_players, "
        "playtime, rating, difficulty, categories, one_liner, "
        "game_images(local_path, image_type)",
        count="exact",
    )

    # 검색 필터
    if search:
        query = query.or_(f"name_ko.ilike.%{search}%,name_en.ilike.%{search}%")

    # 정렬 + 페이지네이션
    query = query.order("rating", desc=True).range(offset, offset + per_page - 1)

    resp = query.execute()
    total = resp.count or 0
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    # 이미지 URL 평탄화 (local_path만 사용, 없으면 빈 문자열)
    games = []
    for game in (resp.data or []):
        images = game.pop("game_images", []) or []
        thumb = next((img for img in images if img["image_type"] == "thumbnail"), None)
        cover = next((img for img in images if img["image_type"] == "cover"), None)
        best = thumb or cover or {}
        game["image_url"] = best.get("local_path") or ""
        games.append(game)

    return {
        "games": games,
        "total": total,
        "page": page,
        "total_pages": total_pages,
    }


def get_games_by_ids(game_ids: list[int]) -> list[dict]:
    """game_id 리스트로 게임 목록 조회 (즐겨찾기용)"""
    if not game_ids:
        return []

    sb = _get_client()
    # Supabase in 필터
    resp = (
        sb.table("games")
        .select(
            "id, name_ko, name_en, min_players, max_players, "
            "playtime, rating, difficulty, categories, one_liner, "
            "game_images(local_path, image_type)",
        )
        .in_("id", game_ids)
        .execute()
    )

    games = []
    for game in (resp.data or []):
        images = game.pop("game_images", []) or []
        thumb = next((img for img in images if img["image_type"] == "thumbnail"), None)
        cover = next((img for img in images if img["image_type"] == "cover"), None)
        game["image_url"] = (thumb or cover or {}).get("local_path") or ""
        games.append(game)

    # 요청 순서 유지
    id_order = {gid: i for i, gid in enumerate(game_ids)}
    games.sort(key=lambda g: id_order.get(g["id"], 999999))
    return games


def get_game_rules(game_id: int) -> dict | None:
    """게임 룰 데이터 조회 (game_rules 테이블)"""
    sb = _get_client()
    resp = (
        sb.table("game_rules")
        .select("intro, components, setup, gameplay, end_condition, scoring, win_condition, special_rules, faq, extra_sections")
        .eq("game_id", game_id)
        .limit(1)
        .execute()
    )
    if not resp.data:
        return None

    rule = resp.data[0]
    # extra_sections에서 setup_by_player를 최상위로 꺼냄
    extra = rule.get("extra_sections") or {}
    rule["setup_by_player"] = extra.get("setup_by_player", "")
    return rule


def get_game_playbook(game_id: int) -> list[dict]:
    """게임 플레이북 조회 (단계별 진행 가이드)"""
    sb = _get_client()
    resp = (
        sb.table("game_playbooks")
        .select("step_order, phase, title, content, player_variants, tips")
        .eq("game_id", game_id)
        .order("step_order")
        .execute()
    )
    return resp.data or []


def get_game_detail(game_id: int) -> dict | None:
    """게임 상세 정보 + 이미지 조회"""
    sb = _get_client()
    resp = (
        sb.table("games")
        .select("*, game_images(local_path, image_type)")
        .eq("id", game_id)
        .execute()
    )
    if not resp.data:
        return None

    game = resp.data[0]
    images = game.pop("game_images", []) or []
    cover = next((img for img in images if img["image_type"] == "cover"), None)
    thumb = next((img for img in images if img["image_type"] == "thumbnail"), None)
    # local_path 우선, 없으면 source_url
    game["cover_url"] = (cover or {}).get("local_path") or ""
    game["thumb_url"] = (thumb or {}).get("local_path") or ""
    return game
