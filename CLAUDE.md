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
# 서버 실행 (어드민 페이지: http://localhost:8000/admin/)
uv run uvicorn main:app --reload

# 의존성 추가
uv add <패키지명>

# 크롤링 스크립트 실행 (scripts/ 디렉토리에서)
uv run python scripts/fetch_boardlife.py
uv run python scripts/load_to_supabase.py
uv run python scripts/load_to_chroma.py
```

## 기술 스택

- **백엔드**: FastAPI + Python 3.12+
- **패키지 관리**: uv (pip 대신 uv add / uv run 사용)
- **DB**: Supabase (관계형 마스터) + ChromaDB (벡터 검색)
- **AI**: OpenAI Agents SDK + RAG
- **프론트엔드**: Flutter (예정)
- **템플릿**: Jinja2 (어드민 페이지)

## 아키텍처

### 데이터 파이프라인
```
크롤링(scripts/) → JSONL(data/) → Supabase(마스터DB) → ChromaDB(벡터검색)
```

### 주요 디렉토리 역할
- `app/admin/` — 어드민 웹 (FastAPI + Jinja2). router.py(라우트), service.py(비즈니스 로직)
- `scripts/` — 크롤링/데이터 파이프라인 스크립트 (보드라이프, BGG 수집 → Supabase/ChromaDB 적재)
- `scripts/rules/` — 룰북 PDF 수집 파이프라인 (discover → download → DB 업데이트)
- `data/` — 크롤링 결과 JSONL, 체크포인트 파일, 이미지
- `docs/db_schema.md` — Supabase 12테이블 + ChromaDB 3컬렉션 전체 스키마 명세

### DB 구조 요약
- **Supabase 12테이블**: games(마스터), game_sources(수집처매핑), game_images, game_rules(룰텍스트), users, game_sessions, trpg_sessions, trpg_characters, trpg_scenarios, game_relations, crawl_sources, crawl_jobs
- **ChromaDB 3컬렉션**: game_search(게임검색), game_rules(룰QA/RAG), game_playbook(진행가이드)
- 상세 스키마는 `docs/db_schema.md` 참조

### 어드민 웹 구조
`main.py`에서 FastAPI 앱 생성 → `app/admin/router.py` 마운트. 어드민에서 크롤링 소스 관리, 배치 실행, 게임 CRUD 가능. 크롤링 실행 시 `subprocess.Popen`으로 스크립트를 백그라운드 실행.

## 환경 변수

`.env` 파일 필요 (dotenv 로드). Supabase URL/키, OpenAI API 키 등 포함.
