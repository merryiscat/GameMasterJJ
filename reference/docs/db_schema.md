# GMJJ DB 스키마 명세서

## 아키텍처 개요

```
보드라이프 크롤링 → JSONL → Supabase(마스터) → ChromaDB(검색 인덱스)
```

- **Supabase**: 관계형 마스터 DB (11개 테이블)
- **ChromaDB**: 벡터 검색 인덱스 (3개 컬렉션, Supabase에서 파생)

---

## Supabase 테이블 (11개)

### 1. `games` — 보드게임 마스터 정보

자체 PK 사용. 외부 소스(보드라이프, BGG 등)와 독립적인 고유 ID.

```sql
CREATE TABLE games (
    id              serial PRIMARY KEY,
    name_ko         text NOT NULL,          -- 한국어 이름 (필수)
    name_en         text,                   -- 영어 이름
    year_published  int,                    -- 출판 연도
    min_players     int,                    -- 최소 인원
    max_players     int,                    -- 최대 인원
    playtime        int,                    -- 플레이 시간 (분)
    rating          float,                  -- 자체 종합 평점
    difficulty      float,                  -- 난이도 (1~5)
    language_dependency text,               -- 언어 의존도
    mechanisms      text[],                 -- 메카니즘 배열

    categories      text[],                 -- 카테고리 배열
    designers       text[],                 -- 디자이너 배열
    publishers      text[],                 -- 퍼블리셔 배열
    description_ko  text,                   -- 한국어 설명
    one_liner       text,                   -- 한줄 소개
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);
```

### 2. `game_sources` — 수집처 매핑

하나의 게임에 여러 소스를 연결. 원본 데이터 보존.

```sql
CREATE TABLE game_sources (
    id              serial PRIMARY KEY,
    game_id         int REFERENCES games(id),   -- games 테이블 FK
    source          text NOT NULL,              -- 'boardlife' | 'bgg' | 'manual'
    source_id       text NOT NULL,              -- 수집처의 고유 ID
    source_url      text,                       -- 원본 페이지 URL
    source_rating   float,                      -- 수집처의 평점
    raw_data        jsonb,                      -- 원본 크롤링 데이터 전체 보존
    crawled_at      timestamptz DEFAULT now(),   -- 크롤링 시점
    UNIQUE(source, source_id)                   -- 소스+ID 조합 유니크
);
```

### 3. `game_images` — 게임 이미지

```sql
CREATE TABLE game_images (
    id              serial PRIMARY KEY,
    game_id         int REFERENCES games(id),
    image_type      text NOT NULL,              -- 'cover' | 'thumbnail'
    source_url      text,                       -- 원본 이미지 URL
    local_path      text,                       -- 로컬 저장 경로 (추후)
    created_at      timestamptz DEFAULT now(),
    UNIQUE(game_id, image_type)                 -- 게임당 타입별 1개
);
```

### 4. `users` — 유저 정보

Supabase Auth 연동. UUID PK.

```sql
CREATE TABLE users (
    id              uuid PRIMARY KEY,           -- Supabase Auth uid
    email           text,
    nickname        text,
    avatar_url      text,
    role            text DEFAULT 'user',         -- 'user' | 'admin' | 'creator'
    token_balance   int DEFAULT 0,               -- TRPG 토큰 잔액
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);
```

### 5. `game_sessions` — 보드게임 세션

```sql
CREATE TABLE game_sessions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES users(id),
    game_id         int REFERENCES games(id),
    status          text DEFAULT 'active',       -- 'active' | 'paused' | 'completed'
    player_count    int,
    current_phase   text,                        -- 현재 게임 단계
    game_state      jsonb,                       -- 턴, 점수 등 상태
    chat_history    jsonb,                       -- LLM 대화 기록
    started_at      timestamptz DEFAULT now(),
    ended_at        timestamptz
);
```

### 6. `trpg_sessions` — TRPG 세션

```sql
CREATE TABLE trpg_sessions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES users(id),
    scenario_id     uuid REFERENCES trpg_scenarios(id),
    title           text,
    rulebook        text,                        -- 'D&D 5e' | 'CoC 7e' | 'custom'
    status          text DEFAULT 'active',
    player_count    int,
    story_log       jsonb,                       -- 스토리 진행 기록
    chat_history    jsonb,                       -- LLM 대화 기록
    world_state     jsonb,                       -- NPC, 장소, 이벤트 상태
    tokens_used     int DEFAULT 0,               -- 사용한 토큰 수
    started_at      timestamptz DEFAULT now(),
    ended_at        timestamptz
);
```

### 7. `trpg_characters` — TRPG 캐릭터 시트

```sql
CREATE TABLE trpg_characters (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES users(id),
    session_id      uuid REFERENCES trpg_sessions(id),
    name            text,
    class           text,
    level           int DEFAULT 1,
    stats           jsonb,                       -- STR, DEX, CON 등
    skills          jsonb,                       -- 기술 목록
    inventory       jsonb,                       -- 인벤토리
    status_effects  jsonb,                       -- 상태 효과
    hp_current      int,
    hp_max          int,
    backstory       text,                        -- 배경 스토리
    notes           text,                        -- 메모
    created_at      timestamptz DEFAULT now()
);
```

### 8. `trpg_scenarios` — TRPG 시나리오

```sql
CREATE TABLE trpg_scenarios (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id       uuid REFERENCES users(id),
    title           text NOT NULL,
    description     text,
    genre           text,                        -- 'horror' | 'fantasy' | 'sci-fi' ...
    rulebook        text,                        -- 사용 룰북
    player_count_min int,
    player_count_max int,
    estimated_time  int,                         -- 예상 시간 (분)
    difficulty      int,                         -- 난이도 1~5
    content         jsonb,                       -- 시나리오 본문 (챕터/씬)
    is_published    bool DEFAULT false,           -- 마켓 공개 여부
    price           int DEFAULT 0,               -- 가격 (원)
    rating          float,                       -- 평균 평점
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);
```

### 9. `game_rules` — 게임 룰북/룰 텍스트

PDF 다운로드 → 텍스트 추출 → 섹션 파싱 → ChromaDB 동기화.

```sql
CREATE TABLE game_rules (
    id              serial PRIMARY KEY,
    game_id         int REFERENCES games(id) ON DELETE CASCADE,

    -- 수집 정보
    source_type     text NOT NULL,              -- 'pdf' | 'web' | 'manual' | 'ocr'
    source_url      text,                       -- 원본 URL
    source_file     text,                       -- 로컬 PDF/파일 경로
    language        text DEFAULT 'ko',          -- 'ko' | 'en'
    version         text,                       -- 판본

    -- 원본 텍스트
    raw_text        text,                       -- 전체 룰 원문
    page_count      int,                        -- PDF 페이지 수

    -- 파싱된 섹션 (핵심 구조)
    intro           text,                       -- 게임 소개/배경
    components      text,                       -- 구성품 목록
    setup           text,                       -- 게임 준비/셋업
    gameplay        text,                       -- 게임 진행 방법
    end_condition   text,                       -- 게임 종료 조건
    scoring         text,                       -- 점수 계산
    win_condition   text,                       -- 승리 조건
    special_rules   text,                       -- 특수/변형 규칙
    faq             text,                       -- FAQ/에러타
    extra_sections  jsonb,                      -- 추가 섹션 (확장용)

    -- 파이프라인 상태
    status          text DEFAULT 'raw',         -- 'raw' | 'parsed' | 'vectorized' | 'error'
    parse_log       text,                       -- 파싱 에러/로그

    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now(),

    UNIQUE(game_id, language, version)
);
```

### 10. `game_relations` — 게임 간 관계

확장판, 리임플, 결합 가능 등 게임 간 관계를 저장.

```sql
CREATE TABLE game_relations (
    id              serial PRIMARY KEY,
    game_id         int REFERENCES games(id) ON DELETE CASCADE,   -- 기준 게임
    related_id      int REFERENCES games(id) ON DELETE CASCADE,   -- 관련 게임
    relation        text NOT NULL,           -- 'expansion' | 'base' | 'reimplementation' | 'standalone' | 'combinable'
    UNIQUE(game_id, related_id)
);
```

**relation 값 예시:**
- `expansion` — game_id의 확장판이 related_id
- `base` — game_id의 본판이 related_id
- `reimplementation` — 리메이크/재구현
- `standalone` — 독립 확장
- `combinable` — 결합 플레이 가능

### 11. `crawl_sources` — 크롤링 소스 관리

수집 사이트별 설정, 주기, 상태 관리.

```sql
CREATE TABLE crawl_sources (
    id              serial PRIMARY KEY,
    name            text NOT NULL UNIQUE,        -- 소스 식별자 (boardlife, bgg 등)
    display_name    text,                        -- 표시용 이름 (보드라이프, BoardGameGeek)
    base_url        text,                        -- 소스 기본 URL
    crawl_type      text DEFAULT 'scraping',     -- 'scraping' | 'api'
    schedule        text DEFAULT 'weekly',       -- 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'manual'
    schedule_day    int,                          -- 요일(0=월) 또는 일(1~28)
    last_crawled_at timestamptz,                 -- 마지막 크롤링 시점
    total_games     int DEFAULT 0,               -- 해당 소스의 총 게임 수
    is_active       boolean DEFAULT true,        -- 활성화 여부
    config          jsonb,                       -- 소스별 설정 (헤더, 딜레이 등)
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);
```

### 11. `crawl_jobs` — 크롤링 배치 실행 기록

배치 크롤링 작업의 실행 이력 및 결과 추적.

```sql
CREATE TABLE crawl_jobs (
    id              serial PRIMARY KEY,
    source_id       int REFERENCES crawl_sources(id),  -- crawl_sources FK
    job_type        text NOT NULL,               -- 'new' | 'update' | 'manual'
    status          text DEFAULT 'pending',      -- 'pending' | 'running' | 'completed' | 'failed'
    started_at      timestamptz,                 -- 작업 시작 시각
    finished_at     timestamptz,                 -- 작업 완료 시각
    total           int DEFAULT 0,               -- 총 처리 대상 수
    success         int DEFAULT 0,               -- 성공 건수
    fail            int DEFAULT 0,               -- 실패 건수
    new_games       int DEFAULT 0,               -- 신규 등록 게임 수
    updated_games   int DEFAULT 0,               -- 업데이트된 게임 수
    log             text,                        -- 실행 로그/에러 메시지
    created_at      timestamptz DEFAULT now()
);
```

---

## ChromaDB 컬렉션 (3개)

Supabase `games` 테이블에서 파생. OpenAI `text-embedding-3-small` 임베딩 사용.

### 1. `game_search` — 게임 검색/추천

| 항목 | 내용 |
|------|------|
| **ID** | `game_{games.id}` |
| **document** | 게임명(한/영) + 설명 + 인원 + 메카니즘 + 테마 + 한줄평 |
| **metadata** | game_id, name_ko, name_en, rating, difficulty, players, playtime 등 |
| **용도** | "협력형 던전 게임 추천해줘" 같은 자연어 검색 |

### 2. `game_rules` — 게임 룰 Q&A (RAG)

| 항목 | 내용 |
|------|------|
| **ID** | `rule_{game_id}_{chunk_idx}` |
| **document** | 게임 설명, 한줄평 / 추후 룰북 원문 청크 |
| **metadata** | game_id, game_name, chunk_type |
| **용도** | "이 게임 어떻게 하는 거야?" 같은 룰 질문 |

### 3. `game_playbook` — 게임 진행 가이드

| 항목 | 내용 |
|------|------|
| **ID** | `play_{game_id}_{section}` |
| **document** | LLM 전처리한 진행 가이드 (인원별 셋업, 턴 구조 등) |
| **metadata** | game_id, game_name, section, player_count |
| **section 종류** | setup_2p, setup_3p, components, turn_structure, phases, scoring, end_condition, special_rules, faq |
| **용도** | 실제 게임 진행 시 GM이 참조하는 데이터 |

---

## 데이터 흐름

```
1. 크롤링     : 보드라이프 → JSONL (data/boardlife_games.jsonl)
2. 마스터 적재 : JSONL → Supabase games + game_sources + game_images
3. 검색 동기화 : Supabase games → ChromaDB game_search, game_rules
4. (추후)      : 룰북 추가 → ChromaDB game_rules, game_playbook
```
