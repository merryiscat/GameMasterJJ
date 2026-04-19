"""
Supabase DB 헬퍼

파이프라인 상태 관리, game_rules 섹션 저장, 플레이북 저장 등
Supabase와 통신하는 함수들을 모아놓은 모듈.
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client, Client

from preprocessing.pipeline import STEPS, SECTION_TO_COLUMN, SECTION_TO_EXTRA

load_dotenv()

# ============================================================
# Supabase 클라이언트
# ============================================================
_client: Client | None = None


def get_client() -> Client:
    """Supabase 클라이언트 반환 (싱글톤)"""
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL 또는 SUPABASE_KEY가 .env에 없습니다."
            )
        _client = create_client(url, key)
    return _client


# ============================================================
# game_rules 조회/수정
# ============================================================
def get_rule(rule_id: int) -> dict:
    """game_rules 1건 조회"""
    sb = get_client()
    result = sb.table("game_rules").select("*").eq("id", rule_id).execute()
    if not result.data:
        raise ValueError(f"game_rules id={rule_id} 없음")
    return result.data[0]


def get_all_rules() -> list[dict]:
    """game_rules 전체 조회"""
    sb = get_client()
    result = sb.table("game_rules").select("*").order("id").execute()
    return result.data


def update_rule(rule_id: int, data: dict):
    """game_rules 1건 업데이트"""
    sb = get_client()
    sb.table("game_rules").update(data).eq("id", rule_id).execute()


def update_rule_sections(rule_id: int, sections: dict):
    """
    12개 섹션을 game_rules에 저장

    - 기존 칼럼에 매핑되는 9개 → 해당 칼럼에 직접 저장
    - 나머지 3개 (setup_by_player, actions, keywords) → extra_sections jsonb에 저장
    """
    # 기존 칼럼 업데이트 데이터
    column_data = {}
    for section_name, column_name in SECTION_TO_COLUMN.items():
        if section_name in sections:
            column_data[column_name] = sections[section_name]

    # extra_sections jsonb 업데이트 데이터
    # 기존 extra_sections 값을 먼저 가져와서 merge
    rule = get_rule(rule_id)
    extra = rule.get("extra_sections") or {}
    for section_name in SECTION_TO_EXTRA:
        if section_name in sections:
            extra[section_name] = sections[section_name]

    column_data["extra_sections"] = extra
    update_rule(rule_id, column_data)


# ============================================================
# rule_pipeline 상태 관리
# ============================================================
def init_pipeline(rule_id: int):
    """
    game_rule 1건에 대해 6개 스텝의 pipeline 레코드 생성

    이미 존재하면 건너뛴다 (중복 방지).
    """
    sb = get_client()

    # 이미 있는지 확인
    existing = (
        sb.table("rule_pipeline")
        .select("step")
        .eq("game_rule_id", rule_id)
        .execute()
    )
    existing_steps = {r["step"] for r in existing.data}

    # 없는 스텝만 추가
    for step in STEPS:
        if step not in existing_steps:
            sb.table("rule_pipeline").insert({
                "game_rule_id": rule_id,
                "step": step,
                "status": "pending",
            }).execute()


def get_pipeline_status(rule_id: int) -> list[dict]:
    """특정 rule의 파이프라인 전체 상태 조회"""
    sb = get_client()
    result = (
        sb.table("rule_pipeline")
        .select("*")
        .eq("game_rule_id", rule_id)
        .order("id")
        .execute()
    )
    return result.data


def get_step_status(rule_id: int, step: str) -> str:
    """특정 rule의 특정 step 상태 반환 ('pending', 'done', 'error' 등)"""
    sb = get_client()
    result = (
        sb.table("rule_pipeline")
        .select("status")
        .eq("game_rule_id", rule_id)
        .eq("step", step)
        .execute()
    )
    if not result.data:
        return "not_found"
    return result.data[0]["status"]


def _now() -> str:
    """현재 시각 ISO 문자열 (UTC)"""
    return datetime.now(timezone.utc).isoformat()


def start_step(rule_id: int, step: str):
    """스텝 시작 → status='running', started_at 기록"""
    sb = get_client()
    sb.table("rule_pipeline").update({
        "status": "running",
        "started_at": _now(),
    }).eq("game_rule_id", rule_id).eq("step", step).execute()


def finish_step(rule_id: int, step: str, log: str = ""):
    """스텝 완료 → status='done', finished_at 기록"""
    sb = get_client()
    sb.table("rule_pipeline").update({
        "status": "done",
        "finished_at": _now(),
        "log": log,
    }).eq("game_rule_id", rule_id).eq("step", step).execute()


def fail_step(rule_id: int, step: str, error: str):
    """스텝 실패 → status='error', log에 에러 기록"""
    sb = get_client()
    sb.table("rule_pipeline").update({
        "status": "error",
        "finished_at": _now(),
        "log": error,
    }).eq("game_rule_id", rule_id).eq("step", step).execute()


def skip_step(rule_id: int, step: str, reason: str = ""):
    """스텝 스킵 → status='skipped', log에 사유 기록"""
    sb = get_client()
    sb.table("rule_pipeline").update({
        "status": "skipped",
        "finished_at": _now(),
        "log": reason,
    }).eq("game_rule_id", rule_id).eq("step", step).execute()


# ============================================================
# game_playbooks 저장
# ============================================================
def save_playbook(game_id: int, rule_id: int, steps: list[dict]):
    """
    플레이북 저장 (기존 데이터 삭제 후 재삽입)

    steps 형식:
    [
        {
            "step_order": 1,
            "phase": "setup",
            "title": "구성품 배치",
            "content": "...",
            "player_variants": {"2p": "...", "3p": "..."},
            "tips": "..."
        },
        ...
    ]
    """
    sb = get_client()

    # 기존 플레이북 삭제
    sb.table("game_playbooks").delete().eq("game_id", game_id).execute()

    # 새로 삽입
    for step in steps:
        sb.table("game_playbooks").insert({
            "game_id": game_id,
            "game_rule_id": rule_id,
            "step_order": step["step_order"],
            "phase": step.get("phase", ""),
            "title": step["title"],
            "content": step["content"],
            "player_variants": step.get("player_variants"),
            "tips": step.get("tips"),
        }).execute()


# ============================================================
# QA 쌍 저장
# ============================================================
def save_qa_pairs(rule_id: int, qa_pairs: list[dict]):
    """
    QA 쌍을 game_rules.extra_sections.qa_pairs에 저장

    qa_pairs 형식:
    [{"question": "...", "answer": "..."}, ...]
    """
    rule = get_rule(rule_id)
    extra = rule.get("extra_sections") or {}
    extra["qa_pairs"] = qa_pairs
    update_rule(rule_id, {"extra_sections": extra})


# ============================================================
# game_rule_sources CRUD
# ============================================================
def get_rule_sources(rule_id: int) -> list[dict]:
    """특정 rule의 모든 소스 조회 (우선순위 순)"""
    sb = get_client()
    result = (
        sb.table("game_rule_sources")
        .select("*")
        .eq("game_rule_id", rule_id)
        .order("priority")
        .execute()
    )
    return result.data


def get_rule_sources_by_type(rule_id: int, source_type: str) -> list[dict]:
    """특정 rule의 특정 타입 소스 조회"""
    sb = get_client()
    result = (
        sb.table("game_rule_sources")
        .select("*")
        .eq("game_rule_id", rule_id)
        .eq("source_type", source_type)
        .execute()
    )
    return result.data


def add_rule_source(
    rule_id: int,
    source_type: str,
    priority: int,
    source_url: str = None,
    source_file: str = None,
    language: str = "ko",
) -> dict:
    """소스 1건 등록"""
    sb = get_client()
    data = {
        "game_rule_id": rule_id,
        "source_type": source_type,
        "priority": priority,
        "language": language,
    }
    if source_url:
        data["source_url"] = source_url
    if source_file:
        data["source_file"] = source_file

    result = sb.table("game_rule_sources").insert(data).execute()
    return result.data[0]


def update_rule_source(source_id: int, data: dict):
    """game_rule_sources 1건 업데이트"""
    sb = get_client()
    sb.table("game_rule_sources").update(data).eq("id", source_id).execute()
