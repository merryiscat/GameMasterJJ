"""
룰 전처리 파이프라인 오케스트레이터

전체 파이프라인을 순서대로 실행하거나, 특정 스텝만 실행할 수 있다.

사용법:
    uv run python -m preprocessing.pipeline.run_pipeline --init              # 파이프라인 레코드 초기화
    uv run python -m preprocessing.pipeline.run_pipeline                     # 전체 실행
    uv run python -m preprocessing.pipeline.run_pipeline --rule-id 1         # 특정 룰만
    uv run python -m preprocessing.pipeline.run_pipeline --step ocr          # 특정 스텝만
    uv run python -m preprocessing.pipeline.run_pipeline --rule-id 1 --step parse  # 특정 룰의 특정 스텝
"""

import argparse
import sys

from preprocessing.pipeline import STEPS, db
from preprocessing.pipeline.step1_collect import process_collect
from preprocessing.pipeline.step2_translate import process_translate
from preprocessing.pipeline.step3_parse import process_parse
from preprocessing.pipeline.step4_llm_preprocess import process_llm_preprocess
from preprocessing.pipeline.step5_llm_qa import process_llm_qa
from preprocessing.pipeline.step6_vectorize import process_vectorize

# 스텝 이름 -> 실행 함수 매핑
STEP_RUNNERS = {
    "collect": process_collect,
    "translate": process_translate,
    "parse": process_parse,
    "llm_preprocess": process_llm_preprocess,
    "llm_qa": process_llm_qa,
    "vectorize": process_vectorize,
}


def init_all_pipelines():
    """모든 game_rules에 대해 pipeline 레코드 초기화"""
    rules = db.get_all_rules()
    print(f"파이프라인 초기화: {len(rules)}건")

    for rule in rules:
        db.init_pipeline(rule["id"])
        print(f"  rule_id={rule['id']} (game_id={rule['game_id']}): 6스텝 생성")

    print("초기화 완료!")


def run_step_for_rule(rule_id: int, step: str):
    """특정 rule의 특정 step 실행"""
    # 이미 완료된 스텝인지 확인
    status = db.get_step_status(rule_id, step)
    if status == "done":
        print(f"  [{step}] 이미 완료 (skip)")
        return True
    if status == "skipped":
        print(f"  [{step}] 이미 스킵됨")
        return True

    # 실행
    runner = STEP_RUNNERS.get(step)
    if not runner:
        print(f"  [ERROR] 알 수 없는 스텝: {step}")
        return False

    try:
        runner(rule_id)
        return True
    except Exception as e:
        print(f"  [ERROR] {step} 실패: {e}")
        return False


def run_pipeline_for_rule(rule_id: int, target_step: str | None = None):
    """
    rule 1건에 대해 파이프라인 실행

    target_step이 지정되면 해당 스텝만 실행.
    지정하지 않으면 pending/error 상태인 스텝을 순서대로 실행.
    """
    rule = db.get_rule(rule_id)
    game_id = rule["game_id"]

    # 게임 이름
    sb = db.get_client()
    game = sb.table("games").select("name_ko").eq("id", game_id).execute()
    game_name = game.data[0]["name_ko"] if game.data else f"game_{game_id}"

    print(f"\n{'='*50}")
    print(f"[rule_id={rule_id}] {game_name}")
    print(f"{'='*50}")

    if target_step:
        # 특정 스텝만 실행
        run_step_for_rule(rule_id, target_step)
    else:
        # 전체 파이프라인 순서대로 실행
        for step in STEPS:
            status = db.get_step_status(rule_id, step)

            # pending이나 error만 실행 (done/skipped은 건너뜀)
            if status in ("done", "skipped"):
                print(f"  [{step}] {status} (건너뜀)")
                continue

            success = run_step_for_rule(rule_id, step)

            # 실패하면 이후 스텝 중단
            if not success:
                print(f"  [WARN] {step} 실패로 이후 스텝 중단")
                break


def add_source(rule_id: int, source_type: str, url: str = None, file: str = None):
    """소스 수동 등록"""
    from preprocessing.pipeline.collectors import SOURCE_PRIORITY

    priority = SOURCE_PRIORITY.get(source_type, 99)
    source = db.add_rule_source(
        rule_id=rule_id,
        source_type=source_type,
        priority=priority,
        source_url=url,
        source_file=file,
    )
    print(f"소스 등록: rule_id={rule_id}, type={source_type}, priority={priority}, id={source['id']}")


def main():
    parser = argparse.ArgumentParser(description="룰 전처리 파이프라인")
    parser.add_argument("--init", action="store_true", help="파이프라인 레코드 초기화")
    parser.add_argument("--rule-id", type=int, help="특정 rule만 실행")
    parser.add_argument("--step", choices=STEPS, help="특정 스텝만 실행")
    parser.add_argument("--add-source", action="store_true", help="소스 등록")
    parser.add_argument("--type", type=str, help="소스 타입 (pdf/namuwiki/youtube/blog)")
    parser.add_argument("--url", type=str, help="소스 URL")
    parser.add_argument("--file", type=str, help="소스 파일 경로")
    args = parser.parse_args()

    # 초기화 모드
    if args.init:
        init_all_pipelines()
        return

    # 소스 등록 모드
    if args.add_source:
        if not args.rule_id or not args.type:
            print("[ERROR] --add-source 는 --rule-id 와 --type 이 필요합니다.")
            return
        add_source(args.rule_id, args.type, url=args.url, file=args.file)
        return

    # 대상 rule 목록
    if args.rule_id:
        rule_ids = [args.rule_id]
    else:
        rules = db.get_all_rules()
        rule_ids = [r["id"] for r in rules]

    print(f"파이프라인 실행: {len(rule_ids)}건")
    if args.step:
        print(f"대상 스텝: {args.step}")

    for rule_id in rule_ids:
        run_pipeline_for_rule(rule_id, target_step=args.step)

    print(f"\n{'='*50}")
    print("파이프라인 실행 완료!")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
