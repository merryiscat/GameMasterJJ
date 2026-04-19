"""
수집 노드 4개 (병렬 실행)

기존 collectors/ 모듈을 래핑하여 LangGraph 노드로 변환.
각 노드는 sources 리스트에 SourceData를 추가하여 반환한다.
operator.add 리듀서로 병렬 결과가 자동 합산된다.
"""

from preprocessing.pipeline import db
from preprocessing.pipeline.config import PROJECT_ROOT
from preprocessing.pipeline.collectors import SOURCE_PRIORITY
from preprocessing.pipeline.collectors import (
    pdf_collector,
    namuwiki_collector,
    youtube_collector,
    youtube_search,
    web_search,
)
from preprocessing.agents.state import PipelineState, SourceData


def collect_pdf(state: PipelineState) -> dict:
    """PDF 소스 수집 (Upstage OCR)"""
    rule_id = state["rule_id"]
    game_name = state["game_name"]

    print(f"  [collect_pdf] {game_name}")

    # DB에서 PDF 소스 조회
    pdf_sources = db.get_rule_sources_by_type(rule_id, "pdf")
    if not pdf_sources:
        print(f"  [collect_pdf] PDF 소스 없음 (skip)")
        return {"sources": [], "errors": []}

    results: list[SourceData] = []
    errors: list[str] = []

    for src in pdf_sources:
        # 이미 수집된 소스는 raw_content 그대로 사용
        if src.get("status") == "processed" and src.get("raw_content"):
            print(f"  [collect_pdf] 이미 수집됨 (재사용)")
            results.append({
                "source_type": "pdf",
                "source_id": src["id"],
                "raw_content": src["raw_content"],
                "language": src.get("language", "ko"),
                "metadata": src.get("metadata") or {},
                "parsed_sections": {},
            })
            continue

        try:
            result = pdf_collector.collect(src)
            # DB에 저장
            db.update_rule_source(src["id"], {
                "raw_content": result["raw_content"],
                "status": "processed",
                "metadata": result.get("metadata"),
            })
            # game_rules.raw_text에도 저장 (PDF 원본)
            rule_update = {"raw_text": result["raw_content"]}
            if "page_count" in result:
                rule_update["page_count"] = result["page_count"]
            db.update_rule(rule_id, rule_update)

            results.append({
                "source_type": "pdf",
                "source_id": src["id"],
                "raw_content": result["raw_content"],
                "language": src.get("language", "en"),
                "metadata": result.get("metadata") or {},
                "parsed_sections": {},
            })
            print(f"  [collect_pdf] {len(result['raw_content'])}자 수집 완료")
        except Exception as e:
            errors.append(f"PDF 수집 실패: {e}")
            print(f"  [collect_pdf] 실패: {e}")

    return {"sources": results, "errors": errors}


def collect_namuwiki(state: PipelineState) -> dict:
    """나무위키 소스 수집 (Playwright 크롤링)"""
    rule_id = state["rule_id"]
    game_name = state["game_name"]

    print(f"  [collect_namuwiki] {game_name}")

    namu_sources = db.get_rule_sources_by_type(rule_id, "namuwiki")
    if not namu_sources:
        print(f"  [collect_namuwiki] 나무위키 소스 없음 (skip)")
        return {"sources": [], "errors": []}

    results: list[SourceData] = []
    errors: list[str] = []

    for src in namu_sources:
        if src.get("status") == "processed" and src.get("raw_content"):
            print(f"  [collect_namuwiki] 이미 수집됨 (재사용)")
            results.append({
                "source_type": "namuwiki",
                "source_id": src["id"],
                "raw_content": src["raw_content"],
                "language": "ko",
                "metadata": src.get("metadata") or {},
                "parsed_sections": {},
            })
            continue

        try:
            result = namuwiki_collector.collect(src)
            db.update_rule_source(src["id"], {
                "raw_content": result["raw_content"],
                "status": "processed",
            })
            results.append({
                "source_type": "namuwiki",
                "source_id": src["id"],
                "raw_content": result["raw_content"],
                "language": "ko",
                "metadata": {},
                "parsed_sections": {},
            })
            print(f"  [collect_namuwiki] {len(result['raw_content'])}자 수집 완료")
        except Exception as e:
            errors.append(f"나무위키 수집 실패: {e}")
            print(f"  [collect_namuwiki] 실패: {e}")

    return {"sources": results, "errors": errors}


def collect_youtube(state: PipelineState) -> dict:
    """
    유튜브 소스 수집
    - URL 등록됨: youtube_collector.collect()
    - URL 없음: youtube_search.search_and_collect() 자동검색
    """
    rule_id = state["rule_id"]
    game_name = state["game_name"]

    print(f"  [collect_youtube] {game_name}")

    yt_sources = db.get_rule_sources_by_type(rule_id, "youtube")

    # 등록된 유튜브 소스가 있으면 URL 기반 수집
    if yt_sources:
        results: list[SourceData] = []
        errors: list[str] = []

        for src in yt_sources:
            if src.get("status") == "processed" and src.get("raw_content"):
                print(f"  [collect_youtube] 이미 수집됨 (재사용)")
                results.append({
                    "source_type": "youtube",
                    "source_id": src["id"],
                    "raw_content": src["raw_content"],
                    "language": src.get("language", "ko"),
                    "metadata": src.get("metadata") or {},
                    "parsed_sections": {},
                })
                continue

            try:
                result = youtube_collector.collect(src)
                db.update_rule_source(src["id"], {
                    "raw_content": result["raw_content"],
                    "status": "processed",
                    "language": result.get("language", "ko"),
                    "metadata": result.get("metadata"),
                })
                results.append({
                    "source_type": "youtube",
                    "source_id": src["id"],
                    "raw_content": result["raw_content"],
                    "language": result.get("language", "ko"),
                    "metadata": result.get("metadata") or {},
                    "parsed_sections": {},
                })
                print(f"  [collect_youtube] {len(result['raw_content'])}자 수집 완료")
            except Exception as e:
                errors.append(f"유튜브 수집 실패: {e}")
                print(f"  [collect_youtube] 실패: {e}")

        return {"sources": results, "errors": errors}

    # 등록된 소스 없으면 자동검색
    print(f"  [collect_youtube] 등록된 소스 없음 → 자동검색")
    try:
        result = youtube_search.search_and_collect(game_name)
        if not result:
            print(f"  [collect_youtube] 자동검색 결과 없음")
            return {"sources": [], "errors": []}

        # DB에 소스 등록
        source = db.add_rule_source(
            rule_id=rule_id,
            source_type="youtube",
            priority=SOURCE_PRIORITY["youtube"],
            source_url=result["metadata"].get("source_url", ""),
            language=result.get("language", "ko"),
        )
        db.update_rule_source(source["id"], {
            "raw_content": result["raw_content"],
            "status": "processed",
            "metadata": result.get("metadata"),
        })

        print(f"  [collect_youtube] 자동검색 {len(result['raw_content'])}자 수집 완료")
        return {
            "sources": [{
                "source_type": "youtube",
                "source_id": source["id"],
                "raw_content": result["raw_content"],
                "language": result.get("language", "ko"),
                "metadata": result.get("metadata") or {},
                "parsed_sections": {},
            }],
            "errors": [],
        }
    except Exception as e:
        print(f"  [collect_youtube] 자동검색 실패: {e}")
        return {"sources": [], "errors": [f"유튜브 자동검색 실패: {e}"]}


def collect_web(state: PipelineState) -> dict:
    """
    웹 소스 수집 (Tavily API 자동검색)
    항상 자동검색으로 동작.
    """
    rule_id = state["rule_id"]
    game_name = state["game_name"]

    print(f"  [collect_web] {game_name}")

    # 이미 등록된 웹 소스가 있으면 재사용
    web_sources = db.get_rule_sources_by_type(rule_id, "web")
    if web_sources:
        for src in web_sources:
            if src.get("status") == "processed" and src.get("raw_content"):
                print(f"  [collect_web] 이미 수집됨 (재사용)")
                return {
                    "sources": [{
                        "source_type": "web",
                        "source_id": src["id"],
                        "raw_content": src["raw_content"],
                        "language": "ko",
                        "metadata": src.get("metadata") or {},
                        "parsed_sections": {},
                    }],
                    "errors": [],
                }

    # 자동검색
    try:
        result = web_search.search_and_collect(game_name)
        if not result:
            print(f"  [collect_web] 검색 결과 없음")
            return {"sources": [], "errors": []}

        # 대표 URL 추출
        web_sources_meta = result.get("metadata", {}).get("sources", [])
        source_url = web_sources_meta[0]["url"] if web_sources_meta else ""

        # DB에 소스 등록
        source = db.add_rule_source(
            rule_id=rule_id,
            source_type="web",
            priority=SOURCE_PRIORITY.get("web", 4),
            source_url=source_url,
            language="ko",
        )
        db.update_rule_source(source["id"], {
            "raw_content": result["raw_content"],
            "status": "processed",
            "metadata": result.get("metadata"),
        })

        print(f"  [collect_web] {len(result['raw_content'])}자 수집 완료")
        return {
            "sources": [{
                "source_type": "web",
                "source_id": source["id"],
                "raw_content": result["raw_content"],
                "language": "ko",
                "metadata": result.get("metadata") or {},
                "parsed_sections": {},
            }],
            "errors": [],
        }
    except Exception as e:
        print(f"  [collect_web] 실패: {e}")
        return {"sources": [], "errors": [f"웹 수집 실패: {e}"]}
