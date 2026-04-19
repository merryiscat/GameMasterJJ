"""
번역 노드

수집된 소스 중 language != "ko"인 것만 한국어로 번역.
기존 step2_translate.py의 translate_text() 재사용.
"""

from preprocessing.pipeline.step2_translate import translate_text
from preprocessing.agents.state import PipelineState


def translate_node(state: PipelineState) -> dict:
    """
    sources를 순회하며 비한국어 소스 번역.
    sources는 불변이므로 새 리스트를 만들어 반환한다.
    """
    sources = state.get("sources", [])
    if not sources:
        print("  [translate] 소스 없음 (skip)")
        return {}

    # 번역 필요한 소스 확인
    need_translate = [s for s in sources if s.get("language", "ko") != "ko"]
    if not need_translate:
        print("  [translate] 모든 소스가 한국어 (skip)")
        return {}

    # 번역 실행 - sources를 새 리스트로 재구성
    updated_sources = []
    for src in sources:
        if src.get("language", "ko") != "ko" and src.get("raw_content"):
            lang = src["language"]
            content = src["raw_content"]
            print(f"  [translate] {src['source_type']} ({lang} -> ko, {len(content)}자)")

            translated = translate_text(content, lang)

            # 새 SourceData 생성 (원본 보존)
            new_src = {**src}
            new_src["raw_content"] = translated
            new_src["language"] = "ko"
            new_src["metadata"] = {
                **src.get("metadata", {}),
                "original_language": lang,
                "original_length": len(content),
            }
            updated_sources.append(new_src)
            print(f"  [translate] 번역 완료 ({len(translated)}자)")
        else:
            updated_sources.append(src)

    # sources를 완전히 교체해야 하므로, 기존 것을 빼고 새 것을 넣는다
    # Annotated[list, operator.add] 때문에 직접 교체 불가
    # 대신 전체 sources를 덮어쓰는 방식 사용
    # LangGraph에서는 리듀서가 아닌 필드로 변경하거나,
    # 노드에서 반환 시 __replace__ 패턴 사용

    # 주의: operator.add 리듀서는 "추가"만 가능하므로,
    # 번역 결과는 sources를 직접 수정하는 대신
    # 각 소스의 raw_content를 in-place로 갱신한다
    for i, src in enumerate(sources):
        if src.get("language", "ko") != "ko" and src.get("raw_content"):
            sources[i]["raw_content"] = updated_sources[i]["raw_content"]
            sources[i]["language"] = "ko"
            sources[i]["metadata"] = updated_sources[i]["metadata"]

    return {}
