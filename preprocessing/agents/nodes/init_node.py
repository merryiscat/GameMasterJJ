"""
초기화 노드

DB에서 게임/룰/소스 정보를 조회하여
파이프라인 State를 채운다.
"""

from preprocessing.pipeline import db
from preprocessing.pipeline.config import PROJECT_ROOT
from preprocessing.agents.state import PipelineState


def init_node(state: PipelineState) -> dict:
    """
    rule_id로 게임 정보, 소스 목록, PDF 경로 조회.
    조건부 라우팅(route_collectors)에서 사용할 정보를 세팅한다.
    """
    rule_id = state["rule_id"]

    # game_rules 조회
    rule = db.get_rule(rule_id)
    game_id = rule["game_id"]

    # 게임 정보 조회
    sb = db.get_client()
    game = (
        sb.table("games")
        .select("name_ko, min_players, max_players")
        .eq("id", game_id)
        .execute()
    )
    game_info = game.data[0] if game.data else {}
    game_name = game_info.get("name_ko", f"game_{game_id}")
    min_p = game_info.get("min_players", 2)
    max_p = game_info.get("max_players", 4)
    player_range = f"{min_p}~{max_p}인"

    # 등록된 소스 목록 조회
    sources = db.get_rule_sources(rule_id)

    # PDF 파일 경로 확인
    pdf_file_path = None
    for src in sources:
        if src["source_type"] == "pdf" and src.get("source_file"):
            path = PROJECT_ROOT / src["source_file"]
            if path.exists():
                pdf_file_path = str(path)
            break

    # 소스 타입 목록 (collect 라우팅용으로 metadata에 저장)
    registered_source_types = [s["source_type"] for s in sources]

    print(f"[init] {game_name} (rule_id={rule_id}, game_id={game_id})")
    print(f"  등록된 소스: {registered_source_types}")
    print(f"  PDF 경로: {pdf_file_path or '없음'}")

    return {
        "game_id": game_id,
        "game_name": game_name,
        "player_range": player_range,
        "pdf_file_path": pdf_file_path,
        # sources는 아직 빈 리스트 (collect 노드에서 채움)
        # 등록된 소스 정보는 metadata에 임시 저장
        "status": "running",
    }
