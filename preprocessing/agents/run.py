"""
LangGraph 기반 룰 전처리 파이프라인 CLI

사용법:
    uv run python -m preprocessing.agents.run                          # 전체 실행
    uv run python -m preprocessing.agents.run --rule-id 1              # 특정 룰만
    uv run python -m preprocessing.agents.run --rule-id 1 --verbose    # 상세 출력
    uv run python -m preprocessing.agents.run --visualize              # 그래프 시각화
    uv run python -m preprocessing.agents.run --list                   # 대상 목록
"""

import argparse
import asyncio

from preprocessing.agents.graph import build_graph
from preprocessing.agents.state import PipelineState
from preprocessing.pipeline import db


async def run_pipeline(rule_id: int, verbose: bool = False):
    """단일 rule에 대해 LangGraph 파이프라인 실행"""
    graph = build_graph()

    # 초기 state
    initial_state: PipelineState = {
        "rule_id": rule_id,
        "game_id": 0,          # init_node에서 채움
        "game_name": "",       # init_node에서 채움
        "player_range": "",    # init_node에서 채움
        "pdf_file_path": None,
        "sources": [],
        "errors": [],
        "component_images": [],
        "merged_sections": {},
        "review_feedback": None,
        "review_count": 0,
        "playbook": [],
        "qa_pairs": [],
        "status": "running",
    }

    config = {"recursion_limit": 30}

    print(f"\n{'='*60}")
    print(f"LangGraph 파이프라인 시작 (rule_id={rule_id})")
    print(f"{'='*60}")

    if verbose:
        # 스트리밍 모드: 각 노드 완료 시 출력
        async for event in graph.astream(initial_state, config=config):
            for node_name, node_output in event.items():
                if node_name == "__end__":
                    continue
                status_info = ""
                if isinstance(node_output, dict):
                    if "sources" in node_output:
                        status_info = f" (+{len(node_output['sources'])} 소스)"
                    if "errors" in node_output:
                        errs = node_output["errors"]
                        if errs:
                            status_info += f" ({len(errs)} 에러)"
                print(f"  >>> [{node_name}] 완료{status_info}")
    else:
        # 일반 모드: 최종 결과만
        result = await graph.ainvoke(initial_state, config=config)
        errors = result.get("errors", [])
        sources = result.get("sources", [])
        merged = result.get("merged_sections", {})
        filled = sum(1 for v in merged.values() if v.strip())

        print(f"\n{'='*60}")
        print(f"결과: {result.get('status', '?')}")
        print(f"  소스: {len(sources)}개")
        print(f"  섹션: {filled}/12")
        print(f"  플레이북: {len(result.get('playbook', []))}단계")
        print(f"  QA: {len(result.get('qa_pairs', []))}쌍")
        print(f"  이미지: {len(result.get('component_images', []))}개")
        if errors:
            print(f"  에러: {len(errors)}건")
            for e in errors:
                print(f"    - {e}")
        print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="LangGraph 룰 전처리 파이프라인")
    parser.add_argument("--rule-id", type=int, help="특정 rule만 실행")
    parser.add_argument("--verbose", action="store_true", help="상세 출력 (노드별)")
    parser.add_argument("--visualize", action="store_true", help="그래프 시각화 (Mermaid)")
    parser.add_argument("--list", action="store_true", help="대상 rule 목록")
    args = parser.parse_args()

    # 그래프 시각화
    if args.visualize:
        graph = build_graph()
        print(graph.get_graph().draw_mermaid())
        return

    # 대상 목록
    if args.list:
        rules = db.get_all_rules()
        print(f"전체 {len(rules)}건:")
        for r in rules:
            sb = db.get_client()
            game = sb.table("games").select("name_ko").eq("id", r["game_id"]).execute()
            name = game.data[0]["name_ko"] if game.data else "?"
            print(f"  rule_id={r['id']}, game_id={r['game_id']}, "
                  f"status={r.get('status', '?')}, game={name}")
        return

    # 파이프라인 실행
    if args.rule_id:
        asyncio.run(run_pipeline(args.rule_id, verbose=args.verbose))
    else:
        rules = db.get_all_rules()
        print(f"전체 {len(rules)}건 실행")
        for r in rules:
            asyncio.run(run_pipeline(r["id"], verbose=args.verbose))


if __name__ == "__main__":
    main()
