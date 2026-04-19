# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

**GMJJ** - LLM 에이전트 기반 보드게임 룰 안내/진행 + TRPG 게임마스터 + 시나리오 마켓 애플리케이션

### 핵심 기능
1. **보드게임 어시스턴트**: RAG 기반 룰 안내, 상황 판정, 게임 진행
2. **TRPG 게임마스터**: 대화형 서사 진행, 룰북 기반 수치 계산, 캐릭터 시트/플레이 로그 관리
3. **시나리오 마켓**: 유저 제작 TRPG 시나리오 등록/매매

## 개발 환경 및 명령어

```bash
# 서버 실행 (프론트: http://localhost:8000/ / 어드민: http://localhost:8000/admin/)
uv run uvicorn main:app --reload

# 의존성 추가
uv add <패키지명>

# 크롤링 파이프라인 (순서대로 실행)
uv run python scripts/fetch_boardlife.py      # 1) 보드라이프 크롤링 → JSONL
uv run python scripts/load_to_supabase.py     # 2) JSONL → Supabase 적재
uv run python scripts/load_to_chroma_v2.py    # 3) Supabase → ChromaDB 동기화

# 룰 전처리 파이프라인 (기존 순차)
uv run python -m preprocessing.pipeline.run_pipeline                     # 전체 실행
uv run python -m preprocessing.pipeline.run_pipeline --rule-id 1         # 특정 룰만
uv run python -m preprocessing.pipeline.run_pipeline --step collect      # 특정 스텝만
uv run python -m preprocessing.pipeline.run_pipeline --init              # 파이프라인 레코드 초기화

# 룰 전처리 파이프라인 (LangGraph 멀티에이전트)
uv run python -m preprocessing.agents.run                                # 전체 실행
uv run python -m preprocessing.agents.run --rule-id 1                    # 특정 룰만
uv run python -m preprocessing.agents.run --rule-id 1 --verbose          # 상세 출력
uv run python -m preprocessing.agents.run --visualize                    # 그래프 시각화
uv run python -m preprocessing.agents.run --list                         # 대상 목록
```

## 기술 스택

- **백엔드**: FastAPI + Python 3.12+
- **패키지 관리**: uv (pip 대신 uv add / uv run 사용)
- **DB**: Supabase (관계형 마스터) + ChromaDB (벡터 검색, 임베딩: text-embedding-3-small)
- **AI**: OpenAI API (채팅: gpt-4.1-mini, 임베딩: text-embedding-3-small)
- **프론트엔드**: Jinja2 웹 프로토타입 (Flutter 전환 예정)

## 아키텍처

### 데이터 파이프라인
```
크롤링(scripts/) → JSONL(data/) → Supabase(마스터DB) → ChromaDB(벡터검색)
룰북(PDF/나무위키) → preprocessing/pipeline step1~6 → game_rules 테이블 → ChromaDB(game_rules 컬렉션)
```

### 주요 디렉토리 역할
- `web/admin/` — 어드민 웹. router.py(라우트), service.py(Supabase CRUD), search_service.py(ChromaDB 검색)
- `web/frontend/` — 유저용 웹 프로토타입. router.py(라우트+Chat API), service.py(게임/룰 조회)
- `preprocessing/` — 룰 전처리 전용 폴더
  - `pipeline/` — 6단계 파이프라인 (collect → translate → parse → preprocess → QA → vectorize)
  - `pipeline/collectors/` — 소스별 수집기 (pdf, namuwiki, youtube, blog)
  - `rulebooks/` — 룰북 원본 파일 (PDF, 이미지)
  - `reference/` — 외부 API 레퍼런스 (Upstage OCR 등)
- `scripts/` — 크롤링/데이터 파이프라인 (보드라이프, BGG 수집 → Supabase/ChromaDB 적재)
- `data/` — 크롤링 결과 JSONL, 체크포인트 파일, 이미지
- `docs/db_schema.md` — Supabase 테이블 + ChromaDB 컬렉션 전체 스키마 명세
- `00_old/` — 폐기/이관 파일 보관소 (INDEX.md로 관리)

### 앱 라우팅 구조
`main.py`에서 FastAPI 앱 생성 → 두 개 라우터 마운트:
- `/admin/*` → `web/admin/router.py` (대시보드, 소스/잡/게임 CRUD, ChromaDB 검색 테스트)
- `/` → `web/frontend/router.py` (홈, 게임 목록/상세, 룰 챗, 플레이)
- `/static/images` → `data/images/` 정적 파일 서빙

### Chat API
`POST /api/chat` — 프론트엔드에서 사용하는 룰 Q&A 엔드포인트. game_id로 룰 조회 후 OpenAI gpt-4.1-mini 호출. 요청: `{game_id, message, history}`, 응답: `{reply}`.

### DB 구조 요약
- **Supabase**: games(마스터), game_sources(수집처매핑), game_images, game_rules(룰텍스트), users, game_sessions, trpg_sessions, trpg_characters, trpg_scenarios, game_relations, crawl_sources, crawl_jobs
- **ChromaDB 3컬렉션**: game_search(게임검색), game_rules(룰QA/RAG), game_playbook(진행가이드)
- 상세 스키마는 `docs/db_schema.md` 참조

### 룰 파이프라인 12개 섹션
intro, components, setup, gameplay, end_condition, scoring, win_condition, special_rules, faq, variants, expansions, related_games

## 환경 변수

`.env` 파일 필요 (dotenv 로드): SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY, BGG_API_TOKEN 등.
