"""
Step 1: 수집 - 소스별 텍스트 수집

game_rule_sources에 등록된 각 소스에 대해 적절한 collector를 실행하고,
추출된 텍스트를 raw_content에 저장.

자동검색 모드:
  유튜브/웹 소스가 없으면 게임 이름으로 자동 검색하여
  소스를 등록하고 수집까지 한 번에 진행한다.
"""

from preprocessing.pipeline import db
from preprocessing.pipeline.collectors import (
    pdf_collector,
    namuwiki_collector,
    youtube_collector,
    blog_collector,
    youtube_search,
    web_search,
)

# 소스 타입별 collector 매핑 (URL이 이미 등록된 경우)
COLLECTORS = {
    "pdf": pdf_collector.collect,
    "namuwiki": namuwiki_collector.collect,
    "youtube": youtube_collector.collect,
    "blog": blog_collector.collect,
}


def _auto_search_youtube(rule_id: int, game_name: str) -> bool:
    """
    유튜브 자동검색: 게임 이름으로 검색 → 소스 등록 + 수집

    Returns:
        True: 수집 성공, False: 실패 또는 결과 없음
    """
    result = youtube_search.search_and_collect(game_name)
    if not result:
        return False

    # game_rule_sources에 자동 등록
    source = db.add_rule_source(
        rule_id=rule_id,
        source_type="youtube",
        priority=3,
        source_url=result["metadata"].get("source_url", ""),
        language=result.get("language", "ko"),
    )

    # raw_content 저장
    db.update_rule_source(source["id"], {
        "raw_content": result["raw_content"],
        "status": "processed",
        "metadata": result.get("metadata"),
    })

    return True


def _auto_search_web(rule_id: int, game_name: str) -> bool:
    """
    웹 자동검색: 게임 이름으로 Tavily 검색 → 소스 등록 + 수집

    Returns:
        True: 수집 성공, False: 실패 또는 결과 없음
    """
    result = web_search.search_and_collect(game_name)
    if not result:
        return False

    # 첫 번째 소스의 URL을 대표 URL로
    sources = result.get("metadata", {}).get("sources", [])
    source_url = sources[0]["url"] if sources else ""

    # game_rule_sources에 자동 등록
    source = db.add_rule_source(
        rule_id=rule_id,
        source_type="web",
        priority=4,
        source_url=source_url,
        language="ko",
    )

    # raw_content 저장
    db.update_rule_source(source["id"], {
        "raw_content": result["raw_content"],
        "status": "processed",
        "metadata": result.get("metadata"),
    })

    return True


def process_collect(rule_id: int):
    """
    game_rule 1건에 대해 모든 소스 수집

    1. game_rule_sources에서 해당 rule의 소스 목록 조회
    2. 아직 수집 안 된 소스(status='raw')에 대해 collector 실행
    3. 유튜브/웹 소스가 없으면 자동검색으로 추가
    4. 결과를 game_rule_sources.raw_content에 저장
    """
    db.start_step(rule_id, "collect")

    try:
        # 게임 이름 조회 (자동검색에 필요)
        rule = db.get_rule(rule_id)
        game_id = rule["game_id"]
        sb = db.get_client()
        game = sb.table("games").select("name_ko").eq("id", game_id).execute()
        game_name = game.data[0]["name_ko"] if game.data else ""

        sources = db.get_rule_sources(rule_id)
        success_count = 0
        error_count = 0

        # ---- 1) 기존 등록된 소스 수집 ----
        for source in sources:
            source_id = source["id"]
            source_type = source["source_type"]
            status = source["status"]

            # 이미 처리된 소스는 건너뜀
            if status == "processed":
                print(f"  [{source_type}] 이미 수집됨 (skip)")
                success_count += 1
                continue

            # collector 찾기
            collector_fn = COLLECTORS.get(source_type)
            if not collector_fn:
                print(f"  [{source_type}] [WARN] 지원하지 않는 소스 타입")
                continue

            # 수집 실행
            try:
                result = collector_fn(source)

                # raw_content 저장
                update_data = {
                    "raw_content": result["raw_content"],
                    "status": "processed",
                }

                if "metadata" in result:
                    update_data["metadata"] = result.get("metadata")
                if "language" in result:
                    update_data["language"] = result["language"]

                db.update_rule_source(source_id, update_data)
                success_count += 1

                # PDF 소스는 game_rules.raw_text에도 저장
                if source_type == "pdf":
                    rule_update = {"raw_text": result["raw_content"]}
                    if "page_count" in result:
                        rule_update["page_count"] = result["page_count"]
                    db.update_rule(rule_id, rule_update)

                    if "elements" in result:
                        rule_data = db.get_rule(rule_id)
                        extra = rule_data.get("extra_sections") or {}
                        extra["ocr_elements"] = result["elements"]
                        db.update_rule(rule_id, {"extra_sections": extra})

            except Exception as e:
                print(f"    [ERROR] {source_type} 수집 실패: {e}")
                db.update_rule_source(source_id, {
                    "status": "error",
                    "metadata": {"error": str(e)},
                })
                error_count += 1

        # ---- 2) 자동검색: 유튜브/웹 소스가 없으면 검색 ----
        existing_types = {s["source_type"] for s in db.get_rule_sources(rule_id)}

        if "youtube" not in existing_types and game_name:
            print(f"  [자동검색] 유튜브 소스 없음 → 자동 검색")
            try:
                if _auto_search_youtube(rule_id, game_name):
                    success_count += 1
                    print(f"  [자동검색] 유튜브 수집 성공")
                else:
                    print(f"  [자동검색] 유튜브 결과 없음")
            except Exception as e:
                print(f"  [자동검색] 유튜브 실패: {e}")
                error_count += 1

        if "web" not in existing_types and game_name:
            print(f"  [자동검색] 웹 소스 없음 → 자동 검색")
            try:
                if _auto_search_web(rule_id, game_name):
                    success_count += 1
                    print(f"  [자동검색] 웹 수집 성공")
                else:
                    print(f"  [자동검색] 웹 결과 없음")
            except Exception as e:
                print(f"  [자동검색] 웹 실패: {e}")
                error_count += 1

        log_msg = f"성공: {success_count}건, 실패: {error_count}건"
        print(f"  [수집] {log_msg}")
        db.finish_step(rule_id, "collect", log_msg)

    except Exception as e:
        error_msg = f"수집 실패: {e}"
        print(f"  [수집] [ERROR] {error_msg}")
        db.fail_step(rule_id, "collect", error_msg)
        raise
