# LangGraph 멀티에이전트 룰 전처리 파이프라인

## 그래프 구조

```
START → init
         ↓
    ┌────┼────┬────┐
 collect  collect  collect  collect     ← 병렬 Fan-out (PDF/나무위키/유튜브/웹)
    └────┼────┴────┘
         ↓ (Fan-in)
     translate
         ↓
    ┌────┴────┐
 parse    extract_images               ← 병렬 Fork
    └────┬────┘
         ↓ (Join)
       merge                           ← 통합 편집자
         ↓
       review                          ← 검증자
         ↓
    ┌─ passed? ─┐
    Yes         No (1회만)
    ↓            ↓
    │         revise → review (복귀)
    ↓
 ┌──┼──┬──┐
 pb  qa  img_save                      ← 병렬 (플레이북/QA/이미지 저장)
 └──┼──┴──┘
    ↓ (Join)
 vectorize
    ↓
 save_results → END
```

## 파일 구조

```
preprocessing/agents/
├── __init__.py
├── state.py                 ← PipelineState (TypedDict + operator.add 리듀서)
├── graph.py                 ← StateGraph 빌드 (15개 노드, 조건부 엣지)
├── run.py                   ← CLI 진입점
├── nodes/
│   ├── init_node.py         ← DB 조회, 초기 상태 설정
│   ├── collect_nodes.py     ← PDF/나무위키/유튜브/웹 수집 (병렬 4개)
│   ├── translate_node.py    ← 비한국어 소스 번역
│   ├── parse_node.py        ← 소스별 12섹션 파싱 (VLM/텍스트)
│   ├── image_node.py        ← PDF 컴포넌트 이미지 추출 + VLM 분류
│   ├── merge_node.py        ← 멀티소스 통합 편집
│   ├── review_node.py       ← 품질 검증 (완전성/일관성/명확성)
│   ├── revise_node.py       ← 피드백 기반 섹션 재작성
│   ├── output_nodes.py      ← 플레이북 + QA 생성 + 이미지 DB 저장
│   └── vectorize_node.py    ← ChromaDB 임베딩
└── prompts/
    ├── review_rulebook.txt  ← 리뷰어 프롬프트
    ├── revise_section.txt   ← 수정 프롬프트
    └── classify_component.txt ← 이미지 분류 프롬프트
```

## 노드 상세

| 노드 | 역할 | 재사용 모듈 |
|------|------|-----------|
| init | DB 조회, 초기 상태 설정 | pipeline/db.py |
| collect_pdf | PDF OCR 수집 | collectors/pdf_collector.py |
| collect_namuwiki | 나무위키 크롤링 | collectors/namuwiki_collector.py |
| collect_youtube | 유튜브 자막 (URL 또는 자동검색) | collectors/youtube_collector.py, youtube_search.py |
| collect_web | 웹 검색 (Tavily) | collectors/web_search.py |
| translate | 비한국어 소스 번역 | step2_translate.py |
| parse | 소스별 12섹션 파싱 (VLM/텍스트) | step3_parse.py |
| extract_images | PDF 컴포넌트 이미지 추출 + VLM 분류 | PyMuPDF + OpenAI VLM |
| merge | 멀티소스 통합 편집 (우선순위 + 교차검증) | step3_parse.py merge_section() 확장 |
| review | 품질 검증 (완전성/일관성/명확성/실용성) | 신규 |
| revise | 피드백 기반 섹션 재작성 | 신규 |
| playbook | 플레이북 생성 | step4_llm_preprocess.py |
| qa_gen | QA 쌍 생성 | step5_llm_qa.py |
| finalize_images | 이미지 메타데이터 DB 저장 | pipeline/db.py |
| vectorize | ChromaDB 임베딩 | step6_vectorize.py |
| save_results | 최종 DB 저장 | pipeline/db.py |

## 기존 대비 개선점

| 항목 | 기존 (순차 6단계) | 멀티에이전트 (LangGraph) |
|------|----------------|----------------------|
| 수집 | 순차 실행 | 4개 병렬 Fan-out |
| 머지 | 우선순위 단순 머지 | 교차 검증 + 피드백 반영 |
| 검증 | 없음 | Reviewer 1회 리뷰 (완전성/일관성/명확성) |
| 이미지 | 없음 | PDF 컴포넌트 추출 + VLM 분류 |
| 산출물 | 순차 | 3개 병렬 (플레이북/QA/이미지 저장) |

## 실행 방법

```bash
# 전체 실행
uv run python -m preprocessing.agents.run

# 특정 룰만
uv run python -m preprocessing.agents.run --rule-id 1

# 상세 출력
uv run python -m preprocessing.agents.run --rule-id 1 --verbose

# 그래프 시각화 (Mermaid)
uv run python -m preprocessing.agents.run --visualize

# 대상 목록
uv run python -m preprocessing.agents.run --list
```

## State 스키마

- `sources`: `Annotated[list[SourceData], operator.add]` - 병렬 수집 결과 자동 합산
- `errors`: `Annotated[list[str], operator.add]` - 에러 로그 자동 합산
- `merged_sections`: `dict[str, str]` - 12섹션 통합 결과
- `component_images`: `list[ComponentImage]` - 추출된 컴포넌트 이미지
- `review_feedback`: `ReviewFeedback` - 리뷰 결과 (passed, score, issues)
- `review_count`: `int` - 리뷰 횟수 (최대 1회 피드백)

## 모델 설정 (config.py)

- 파싱/머지/리뷰/수정/QA/플레이북: `gpt-5.4-mini`
- 번역: `gpt-4.1`
- 임베딩: `text-embedding-3-small`
- 이미지 분류: `gpt-5.4-mini` (VLM)
