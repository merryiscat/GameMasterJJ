-- ============================================================
-- GMJJ Supabase DDL
-- Supabase SQL Editor에서 실행하세요.
-- ============================================================

-- 1. games: 보드게임 마스터 정보
CREATE TABLE IF NOT EXISTS games (
    id              serial PRIMARY KEY,
    name_ko         text NOT NULL,
    name_en         text,
    year_published  int,
    min_players     int,
    max_players     int,
    playtime        int,
    rating          float,
    difficulty      float,
    language_dependency text,
    mechanisms      text[],

    categories      text[],
    designers       text[],
    publishers      text[],
    description_ko  text,
    one_liner       text,
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

-- 2. game_sources: 수집처 매핑
CREATE TABLE IF NOT EXISTS game_sources (
    id              serial PRIMARY KEY,
    game_id         int REFERENCES games(id) ON DELETE CASCADE,
    source          text NOT NULL,
    source_id       text NOT NULL,
    source_url      text,
    source_rating   float,
    raw_data        jsonb,
    crawled_at      timestamptz DEFAULT now(),
    UNIQUE(source, source_id)
);

-- 3. game_images: 게임 이미지
CREATE TABLE IF NOT EXISTS game_images (
    id              serial PRIMARY KEY,
    game_id         int REFERENCES games(id) ON DELETE CASCADE,
    image_type      text NOT NULL,
    source_url      text,
    local_path      text,
    created_at      timestamptz DEFAULT now(),
    UNIQUE(game_id, image_type)
);

-- 4. users: 유저 정보 (Supabase Auth 연동)
CREATE TABLE IF NOT EXISTS users (
    id              uuid PRIMARY KEY,
    email           text,
    nickname        text,
    avatar_url      text,
    role            text DEFAULT 'user',
    token_balance   int DEFAULT 0,
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

-- 5. game_sessions: 보드게임 세션
CREATE TABLE IF NOT EXISTS game_sessions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES users(id),
    game_id         int REFERENCES games(id),
    status          text DEFAULT 'active',
    player_count    int,
    current_phase   text,
    game_state      jsonb,
    chat_history    jsonb,
    started_at      timestamptz DEFAULT now(),
    ended_at        timestamptz
);

-- 6. trpg_scenarios: TRPG 시나리오 (trpg_sessions보다 먼저 생성, FK 참조)
CREATE TABLE IF NOT EXISTS trpg_scenarios (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id       uuid REFERENCES users(id),
    title           text NOT NULL,
    description     text,
    genre           text,
    rulebook        text,
    player_count_min int,
    player_count_max int,
    estimated_time  int,
    difficulty      int,
    content         jsonb,
    is_published    bool DEFAULT false,
    price           int DEFAULT 0,
    rating          float,
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

-- 7. trpg_sessions: TRPG 세션
CREATE TABLE IF NOT EXISTS trpg_sessions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES users(id),
    scenario_id     uuid REFERENCES trpg_scenarios(id),
    title           text,
    rulebook        text,
    status          text DEFAULT 'active',
    player_count    int,
    story_log       jsonb,
    chat_history    jsonb,
    world_state     jsonb,
    tokens_used     int DEFAULT 0,
    started_at      timestamptz DEFAULT now(),
    ended_at        timestamptz
);

-- 8. trpg_characters: TRPG 캐릭터 시트
CREATE TABLE IF NOT EXISTS trpg_characters (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES users(id),
    session_id      uuid REFERENCES trpg_sessions(id),
    name            text,
    class           text,
    level           int DEFAULT 1,
    stats           jsonb,
    skills          jsonb,
    inventory       jsonb,
    status_effects  jsonb,
    hp_current      int,
    hp_max          int,
    backstory       text,
    notes           text,
    created_at      timestamptz DEFAULT now()
);

-- 9. game_rules: 게임 룰북/룰 텍스트
CREATE TABLE IF NOT EXISTS game_rules (
    id              serial PRIMARY KEY,
    game_id         int REFERENCES games(id) ON DELETE CASCADE,

    -- 수집 정보
    source_type     text NOT NULL,
    source_url      text,
    source_file     text,
    language        text DEFAULT 'ko',
    version         text,

    -- 원본 텍스트
    raw_text        text,
    page_count      int,

    -- 파싱된 섹션
    intro           text,
    components      text,
    setup           text,
    gameplay        text,
    end_condition   text,
    scoring         text,
    win_condition   text,
    special_rules   text,
    faq             text,
    extra_sections  jsonb,

    -- 파이프라인 상태
    status          text DEFAULT 'raw',
    parse_log       text,

    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now(),

    UNIQUE(game_id, language, version)
);

-- 10. game_relations: 게임 간 관계 (확장판, 리임플 등)
CREATE TABLE IF NOT EXISTS game_relations (
    id              serial PRIMARY KEY,
    game_id         int REFERENCES games(id) ON DELETE CASCADE,
    related_id      int REFERENCES games(id) ON DELETE CASCADE,
    relation        text NOT NULL,           -- 'expansion' | 'base' | 'reimplementation' | 'standalone' | 'combinable'
    UNIQUE(game_id, related_id)
);

-- 11. crawl_sources: 크롤링 소스 관리
CREATE TABLE IF NOT EXISTS crawl_sources (
    id              serial PRIMARY KEY,
    name            text NOT NULL UNIQUE,        -- 'boardlife', 'bgg' 등
    display_name    text,                        -- '보드라이프', 'BoardGameGeek'
    base_url        text,                        -- 'https://boardlife.co.kr'
    crawl_type      text DEFAULT 'scraping',     -- 'scraping' | 'api'
    schedule        text DEFAULT 'weekly',       -- 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'manual'
    schedule_day    int,                          -- 요일(0=월) 또는 일(1~28)
    last_crawled_at timestamptz,
    total_games     int DEFAULT 0,
    is_active       boolean DEFAULT true,
    config          jsonb,                       -- 소스별 설정 (헤더, 딜레이 등)
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

-- 11. crawl_jobs: 크롤링 배치 실행 기록
CREATE TABLE IF NOT EXISTS crawl_jobs (
    id              serial PRIMARY KEY,
    source_id       int REFERENCES crawl_sources(id),
    job_type        text NOT NULL,               -- 'new' | 'update' | 'manual'
    status          text DEFAULT 'pending',      -- 'pending' | 'running' | 'completed' | 'failed'
    started_at      timestamptz,
    finished_at     timestamptz,
    total           int DEFAULT 0,
    success         int DEFAULT 0,
    fail            int DEFAULT 0,
    new_games       int DEFAULT 0,
    updated_games   int DEFAULT 0,
    log             text,
    created_at      timestamptz DEFAULT now()
);

-- ============================================================
-- 인덱스
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_games_name_ko ON games(name_ko);
CREATE INDEX IF NOT EXISTS idx_games_rating ON games(rating DESC);
CREATE INDEX IF NOT EXISTS idx_game_sources_source ON game_sources(source, source_id);
CREATE INDEX IF NOT EXISTS idx_game_sources_game_id ON game_sources(game_id);
CREATE INDEX IF NOT EXISTS idx_game_images_game_id ON game_images(game_id);
CREATE INDEX IF NOT EXISTS idx_game_sessions_user ON game_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_trpg_sessions_user ON trpg_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_trpg_characters_session ON trpg_characters(session_id);
CREATE INDEX IF NOT EXISTS idx_trpg_scenarios_published ON trpg_scenarios(is_published) WHERE is_published = true;
CREATE INDEX IF NOT EXISTS idx_game_rules_game_id ON game_rules(game_id);
CREATE INDEX IF NOT EXISTS idx_game_rules_status ON game_rules(status);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_source ON crawl_jobs(source_id);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_status ON crawl_jobs(status);
CREATE INDEX IF NOT EXISTS idx_game_relations_game ON game_relations(game_id);
CREATE INDEX IF NOT EXISTS idx_game_relations_related ON game_relations(related_id);

-- ============================================================
-- updated_at 자동 갱신 트리거
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_games_updated_at
    BEFORE UPDATE ON games
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_trpg_scenarios_updated_at
    BEFORE UPDATE ON trpg_scenarios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_game_rules_updated_at
    BEFORE UPDATE ON game_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_crawl_sources_updated_at
    BEFORE UPDATE ON crawl_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
