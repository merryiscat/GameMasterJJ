"""
Step 1: 수집 - 소스별 텍스트 수집

game_rule_sources에 등록된 각 소스에 대해 적절한 collector를 실행하고,
추출된 텍스트를 raw_content에 저장.
대표 소스(PDF, priority=1)의 텍스트는 game_rules.raw_text에도 저장.
"""

from scripts.rules import db
from scripts.rules.collectors import pdf_collector, namuwiki_collector, youtube_collector, blog_collector

# 소스 타입별 collector 매핑
COLLECTORS = {
    "pdf": pdf_collector.collect,
    "namuwiki": namuwiki_collector.collect,
    "youtube": youtube_collector.collect,
    "blog": blog_collector.collect,
}


def process_collect(rule_id: int):
    """
    game_rule 1건에 대해 모든 소스 수집

    1. game_rule_sources에서 해당 rule의 소스 목록 조회
    2. 아직 수집 안 된 소스(status='raw')에 대해 collector 실행
    3. 결과를 game_rule_sources.raw_content에 저장
    4. PDF 소스 텍스트는 game_rules.raw_text에도 저장 (기존 호환)
    """
    db.start_step(rule_id, "collect")

    try:
        sources = db.get_rule_sources(rule_id)

        if not sources:
            raise ValueError(f"rule_id={rule_id}: 등록된 소스가 없음")

        success_count = 0
        error_count = 0

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

                # 메타데이터가 있으면 저장
                if "metadata" in result:
                    update_data["metadata"] = result.get("metadata")

                # 언어 정보가 있으면 업데이트
                if "language" in result:
                    update_data["language"] = result["language"]

                db.update_rule_source(source_id, update_data)
                success_count += 1

                # PDF 소스는 game_rules.raw_text에도 저장 + 부가 정보
                if source_type == "pdf":
                    rule_update = {"raw_text": result["raw_content"]}
                    if "page_count" in result:
                        rule_update["page_count"] = result["page_count"]
                    db.update_rule(rule_id, rule_update)

                    # OCR elements는 extra_sections에 저장
                    if "elements" in result:
                        rule = db.get_rule(rule_id)
                        extra = rule.get("extra_sections") or {}
                        extra["ocr_elements"] = result["elements"]
                        db.update_rule(rule_id, {"extra_sections": extra})

            except Exception as e:
                print(f"    [ERROR] {source_type} 수집 실패: {e}")
                db.update_rule_source(source_id, {
                    "status": "error",
                    "metadata": {"error": str(e)},
                })
                error_count += 1

        log_msg = f"성공: {success_count}건, 실패: {error_count}건 (총 {len(sources)}소스)"
        print(f"  [수집] {log_msg}")
        db.finish_step(rule_id, "collect", log_msg)

    except Exception as e:
        error_msg = f"수집 실패: {e}"
        print(f"  [수집] [ERROR] {error_msg}")
        db.fail_step(rule_id, "collect", error_msg)
        raise
