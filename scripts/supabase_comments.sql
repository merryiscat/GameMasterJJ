-- ============================================================
-- GMJJ 테이블/컬럼 설명 (COMMENT ON)
-- Supabase SQL Editor에서 실행하세요.
-- Dashboard Table Editor에서 설명이 바로 보입니다.
-- ============================================================

-- ============================================================
-- 1. games
-- ============================================================
COMMENT ON TABLE games IS '보드게임 마스터 정보. 자체 PK 사용, 외부 소스와 독립적.';

COMMENT ON COLUMN games.id IS '자체 고유 ID (serial)';
COMMENT ON COLUMN games.name_ko IS '한국어 게임 이름 (필수)';
COMMENT ON COLUMN games.name_en IS '영어 게임 이름';
COMMENT ON COLUMN games.year_published IS '출판 연도';
COMMENT ON COLUMN games.min_players IS '최소 인원';
COMMENT ON COLUMN games.max_players IS '최대 인원';
COMMENT ON COLUMN games.playtime IS '플레이 시간 (분)';
COMMENT ON COLUMN games.rating IS '종합 평점 (10점 만점)';
COMMENT ON COLUMN games.difficulty IS '난이도/무게 (1~5)';
COMMENT ON COLUMN games.language_dependency IS '언어 의존도: 없음/약간/보통/많음';
COMMENT ON COLUMN games.mechanisms IS '게임 메카니즘 배열 (핸드관리, 워커플레이스먼트 등)';

COMMENT ON COLUMN games.categories IS '카테고리 배열 (전략, 경제 등)';
COMMENT ON COLUMN games.designers IS '디자이너 이름 배열';
COMMENT ON COLUMN games.publishers IS '퍼블리셔 이름 배열';
COMMENT ON COLUMN games.description_ko IS '한국어 게임 설명 (크롤링 원문)';
COMMENT ON COLUMN games.one_liner IS '한줄 소개 (설명 첫 문장)';

-- ============================================================
-- 2. game_sources
-- ============================================================
COMMENT ON TABLE game_sources IS '게임 수집처 매핑. 하나의 게임에 여러 소스 연결 가능. FK: games.id';

COMMENT ON COLUMN game_sources.game_id IS 'games.id FK';
COMMENT ON COLUMN game_sources.source IS '수집처: boardlife | bgg | manual';
COMMENT ON COLUMN game_sources.source_id IS '수집처의 고유 ID (예: 보드라이프 게임번호)';
COMMENT ON COLUMN game_sources.source_url IS '원본 페이지 URL';
COMMENT ON COLUMN game_sources.source_rating IS '수집처에서의 평점';
COMMENT ON COLUMN game_sources.raw_data IS '원본 크롤링 데이터 전체 (JSONB)';
COMMENT ON COLUMN game_sources.crawled_at IS '크롤링 시점';

-- ============================================================
-- 3. game_images
-- ============================================================
COMMENT ON TABLE game_images IS '게임 이미지. 커버/썸네일. FK: games.id';

COMMENT ON COLUMN game_images.game_id IS 'games.id FK';
COMMENT ON COLUMN game_images.image_type IS '이미지 타입: cover | thumbnail';
COMMENT ON COLUMN game_images.source_url IS '원본 이미지 URL (보드라이프 등)';
COMMENT ON COLUMN game_images.local_path IS '로컬 저장 경로 (다운로드 후)';

-- ============================================================
-- 9. game_rules
-- ============================================================
COMMENT ON TABLE game_rules IS '게임 룰북/룰 텍스트. PDF 수집 → 파싱 → ChromaDB 동기화. FK: games.id';

COMMENT ON COLUMN game_rules.game_id IS 'games.id FK';
COMMENT ON COLUMN game_rules.source_type IS '수집 방식: pdf | web | manual | ocr';
COMMENT ON COLUMN game_rules.source_url IS '원본 URL (PDF 다운로드 링크 등)';
COMMENT ON COLUMN game_rules.source_file IS '로컬 PDF/파일 경로';
COMMENT ON COLUMN game_rules.language IS '언어: ko | en';
COMMENT ON COLUMN game_rules.version IS '판본 (예: 2판, 2024 개정)';
COMMENT ON COLUMN game_rules.raw_text IS '전체 룰 원문 (PDF 파싱 결과)';
COMMENT ON COLUMN game_rules.page_count IS 'PDF 페이지 수';
COMMENT ON COLUMN game_rules.intro IS '게임 소개/배경';
COMMENT ON COLUMN game_rules.components IS '구성품 목록';
COMMENT ON COLUMN game_rules.setup IS '게임 준비/셋업';
COMMENT ON COLUMN game_rules.gameplay IS '게임 진행 방법 (턴 구조)';
COMMENT ON COLUMN game_rules.end_condition IS '게임 종료 조건';
COMMENT ON COLUMN game_rules.scoring IS '점수 계산';
COMMENT ON COLUMN game_rules.win_condition IS '승리 조건';
COMMENT ON COLUMN game_rules.special_rules IS '특수 규칙/변형 규칙';
COMMENT ON COLUMN game_rules.faq IS 'FAQ/에러타';
COMMENT ON COLUMN game_rules.extra_sections IS '추가 섹션 (확장용) JSONB';
COMMENT ON COLUMN game_rules.status IS '파이프라인 상태: raw | parsed | vectorized | error';
COMMENT ON COLUMN game_rules.parse_log IS '파싱 에러/로그';

-- ============================================================
-- 4. users
-- ============================================================
COMMENT ON TABLE users IS '유저 정보. Supabase Auth 연동, uuid PK.';

COMMENT ON COLUMN users.id IS 'Supabase Auth uid (uuid)';
COMMENT ON COLUMN users.role IS '역할: user | admin | creator';
COMMENT ON COLUMN users.token_balance IS 'TRPG 토큰 잔액';

-- ============================================================
-- 5. game_sessions
-- ============================================================
COMMENT ON TABLE game_sessions IS '보드게임 진행 세션. FK: users.id, games.id';

COMMENT ON COLUMN game_sessions.status IS '상태: active | paused | completed';
COMMENT ON COLUMN game_sessions.current_phase IS '현재 게임 단계';
COMMENT ON COLUMN game_sessions.game_state IS '게임 상태 (턴, 점수 등) JSONB';
COMMENT ON COLUMN game_sessions.chat_history IS 'LLM 대화 기록 JSONB';

-- ============================================================
-- 6. trpg_scenarios
-- ============================================================
COMMENT ON TABLE trpg_scenarios IS 'TRPG 시나리오 (마켓 거래 대상). FK: users.id';

COMMENT ON COLUMN trpg_scenarios.genre IS '장르: horror | fantasy | sci-fi 등';
COMMENT ON COLUMN trpg_scenarios.rulebook IS '사용 룰북: D&D 5e | CoC 7e | custom';
COMMENT ON COLUMN trpg_scenarios.content IS '시나리오 본문 (챕터/씬) JSONB';
COMMENT ON COLUMN trpg_scenarios.is_published IS '마켓 공개 여부';
COMMENT ON COLUMN trpg_scenarios.price IS '가격 (원)';

-- ============================================================
-- 7. trpg_sessions
-- ============================================================
COMMENT ON TABLE trpg_sessions IS 'TRPG 진행 세션. FK: users.id, trpg_scenarios.id';

COMMENT ON COLUMN trpg_sessions.rulebook IS '사용 룰북: D&D 5e | CoC 7e | custom';
COMMENT ON COLUMN trpg_sessions.story_log IS '스토리 진행 기록 JSONB';
COMMENT ON COLUMN trpg_sessions.world_state IS 'NPC, 장소, 이벤트 상태 JSONB';
COMMENT ON COLUMN trpg_sessions.tokens_used IS '사용한 토큰 수';

-- ============================================================
-- 8. trpg_characters
-- ============================================================
COMMENT ON TABLE trpg_characters IS 'TRPG 캐릭터 시트. FK: users.id, trpg_sessions.id';

COMMENT ON COLUMN trpg_characters.stats IS '능력치 (STR, DEX, CON 등) JSONB';
COMMENT ON COLUMN trpg_characters.skills IS '기술 목록 JSONB';
COMMENT ON COLUMN trpg_characters.inventory IS '인벤토리 JSONB';
COMMENT ON COLUMN trpg_characters.status_effects IS '상태 효과 JSONB';
COMMENT ON COLUMN trpg_characters.backstory IS '캐릭터 배경 스토리';

-- ============================================================
-- 10. game_relations
-- ============================================================
COMMENT ON TABLE game_relations IS '게임 간 관계. 확장판, 리임플, 결합 가능 등. FK: games.id 양방향';

COMMENT ON COLUMN game_relations.game_id IS '기준 게임 (games.id FK)';
COMMENT ON COLUMN game_relations.related_id IS '관련 게임 (games.id FK)';
COMMENT ON COLUMN game_relations.relation IS '관계 유형: expansion | base | reimplementation | standalone | combinable';

-- ============================================================
-- 11. crawl_sources
-- ============================================================
COMMENT ON TABLE crawl_sources IS '크롤링 소스 관리. 수집 사이트별 설정/주기/상태.';

COMMENT ON COLUMN crawl_sources.id IS '자체 고유 ID (serial)';
COMMENT ON COLUMN crawl_sources.name IS '소스 식별자: boardlife | bgg 등 (UNIQUE)';
COMMENT ON COLUMN crawl_sources.display_name IS '표시용 이름: 보드라이프, BoardGameGeek';
COMMENT ON COLUMN crawl_sources.base_url IS '소스 기본 URL';
COMMENT ON COLUMN crawl_sources.crawl_type IS '수집 방식: scraping | api';
COMMENT ON COLUMN crawl_sources.schedule IS '수집 주기: daily | weekly | monthly | quarterly | manual';
COMMENT ON COLUMN crawl_sources.schedule_day IS '수집 요일(0=월) 또는 일(1~28)';
COMMENT ON COLUMN crawl_sources.last_crawled_at IS '마지막 크롤링 시점';
COMMENT ON COLUMN crawl_sources.total_games IS '해당 소스의 총 게임 수';
COMMENT ON COLUMN crawl_sources.is_active IS '활성화 여부';
COMMENT ON COLUMN crawl_sources.config IS '소스별 설정 (헤더, 딜레이 등) JSONB';

-- ============================================================
-- 11. crawl_jobs
-- ============================================================
COMMENT ON TABLE crawl_jobs IS '크롤링 배치 실행 기록. FK: crawl_sources.id';

COMMENT ON COLUMN crawl_jobs.id IS '자체 고유 ID (serial)';
COMMENT ON COLUMN crawl_jobs.source_id IS 'crawl_sources.id FK';
COMMENT ON COLUMN crawl_jobs.job_type IS '작업 유형: new | update | manual';
COMMENT ON COLUMN crawl_jobs.status IS '상태: pending | running | completed | failed';
COMMENT ON COLUMN crawl_jobs.started_at IS '작업 시작 시각';
COMMENT ON COLUMN crawl_jobs.finished_at IS '작업 완료 시각';
COMMENT ON COLUMN crawl_jobs.total IS '총 처리 대상 수';
COMMENT ON COLUMN crawl_jobs.success IS '성공 건수';
COMMENT ON COLUMN crawl_jobs.fail IS '실패 건수';
COMMENT ON COLUMN crawl_jobs.new_games IS '신규 등록 게임 수';
COMMENT ON COLUMN crawl_jobs.updated_games IS '업데이트된 게임 수';
COMMENT ON COLUMN crawl_jobs.log IS '실행 로그/에러 메시지';
