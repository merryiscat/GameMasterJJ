# GMJJ 디자인 핸드오프

## 프로젝트 개요
LLM 에이전트 기반 보드게임 룰 안내/진행 + TRPG 게임마스터 모바일 앱.
현재 Jinja2 웹 프로토타입으로 6페이지 구현 완료, Flutter 전환 예정.

## 현재 페이지 구성 (6페이지)

### 1. 홈 (`home.html`)
- 중앙 GMJJ 로고 + 보드게임/TRPG 2개 대형 카드 버튼
- 보드게임: 에메랄드~틸 그라데이션 카드
- TRPG: 시안 계열 아웃라인 카드
- 하단 네비: 커뮤니티 | 홈 | 설정

### 2. 게임 목록 (`games.html`)
- 상단 sticky 탭: 보드게임 / 추천 / 이벤트
- 검색바 (아이콘 + 인풋)
- 게임 카드 리스트 (72x72 썸네일 + 이름/한줄소개/메타정보 + 즐겨찾기 별)
- 페이지네이션
- 하단 네비: Mygame | 홈 | 설정

### 3. ��임 상세 (`game_detail.html`)
- 상단 뒤로가기 헤더
- 커버 이미지 (220px 높이)
- 게임명 + 영문명
- 메타 그리드 3열: 인원 / 시간 / 평점
- 한줄 소개 (이탤릭, 틸 컬러)
- 게임 설명 (더보기/접기)
- 카테고리/메카니즘 태그
- "게임마스터 안내" 진입 버튼 (에메랄드 그라데이션)

### 4. 룰 챗 (`game_chat.html`)
- 채팅 레이아웃 (헤더 + 메시지 영역 + 입력)
- 헤더: 뒤로가기 + 게임명/서브타이틀 + "게임 진행" 버튼
- 룰 카드: 섹션별 접기/펼치기 (intro, components, setup, gameplay, 종료/승리, 특수규칙)
- GM 메시지: 좌측 정렬, bg-card 배경, "게임마스터 JJ" 라벨
- 유저 메시지: 우측 정렬, teal 배경
- 마크다운 렌더링 지원 (테이블, 리스트, 볼드)
- 로딩: 타이핑 도트 애니메이션

### 5. 게임 진행 (`game_play.html`)
- 상하 분할: 상단 45% 이미지 + 하단 대화 로그/입력
- 채팅/음성 모드 전환 토글 (헤더 우측)
- 채팅 모드: 텍스트 입력 + 전송 버튼
- 음성 모드: 마이크 버튼 (녹음/중지) + 침묵 자동 감지
  - 녹음 중: 빨간 펄스 애니메이션
  - GM 응답 중: 웨이브 애니메이션
  - STT -> LLM -> TTS 파이��라인

### 6. Mygame (`mygame.html`)
- 즐겨찾기한 게임 리스트 (localStorage 기반)
- 게임 카드는 games.html과 동일 레이아웃
- 빈 상태 안내 (별 아이콘 + 게임 목록 링크)

## 디자인 시스템

### 색상 팔레트
```
--emerald-deep: #065F46    (버튼/카드 그라데이션 시작)
--emerald-mid: #047857     (버튼 hover)
--teal: #0D9488            (주 강조색, 버튼 배경)
--teal-light: #2DD4BF      (텍스트 강조, 라벨, 링크)
--cyan: #0E7490            (TRPG 영역)
--cyan-light: #67E8F9      (TRPG 텍스트)
--rose: #E11D48            (액티브 네비, 녹음 중)
--rose-light: #FB7185      (로즈 텍스트)
--bg-primary: #0B1120      (메인 배경 - 다크 네이비)
--bg-secondary: #111B2E    (헤더/입력영역 배경)
--bg-card: #152238          (카드/메시지 배경)
--text-primary: #E2E8F0    (본문 텍스트)
--text-secondary: #94A3B8  (서브 텍스트)
--text-muted: #64748B      (비활성 텍스트)
--border: rgba(255,255,255,0.06) (테두리)
```

### 폰트
- 제목: Jua (Google Fonts) - 둥근 한글 제목 폰트
- 본문: Pretendard - 한글 시스템 폰트

### 레이아웃
- 모바일 퍼스트 (max-width: 430px, 센터 정렬)
- 하단 고정 네비게이션 (64px)
- 카드 라운딩: 12~16px
- 메시지 버블: 16px 라운딩 (꼬리 쪽만 4px)

### 아이콘
- Material Design SVG inline 사용 (외부 라이브러리 없음)
- 22px (네비), 20px (버튼), 12px (메타정보)

## 네비게이션 구조
- 메인 (홈): 커뮤니티 | 홈(active) | 설정
- 게임 내부: Mygame | 홈 | 설정
- Mygame 내부: Mygame(active) | Gamelist | 설정

## API 엔드포인트 (프론트에서 호출)
- `POST /api/chat` - 룰 Q&A (game_id, message, history)
- `POST /api/play` - 게임 진행 (game_id, message, history, player_count)
- `POST /api/stt` - 음성->텍스트 (audio file)
- `POST /api/tts` - 텍스트->음성 (text, voice, instructions)
- `GET /api/mygames?ids=1,2,3` - 즐겨찾기 게임 조회

## 현재 스크린샷 (00_old/screenshots/)
페이지별 대표 스크린샷:
- `test_home.png` - 홈 화면
- `test_games.png` - 게임 목록
- `test_search.png` - 검색 결과
- `test_brass_detail.png` - 게임 상세 (브라스 버밍엄)
- `test_chat.png` / `test_chat_answer.png` - 룰 챗
- `test_citadels_play.png` ~ `test_citadels_play4.png` - 게임 진행 (시타델)
- `test_voice_final.png` - ���성 모드
- `test_wingspan_table.png` - 테이블 렌더링

## 소스 파일 목록
```
web/frontend/templates/base.html       - 공통 레이아웃 + CSS 변수 + 하단 네비 + 마크다운 파서
web/frontend/templates/home.html       - 홈 화면
web/frontend/templates/games.html      - 게임 목록
web/frontend/templates/game_detail.html - 게임 상세
web/frontend/templates/game_chat.html  - 룰 챗
web/frontend/templates/game_play.html  - ��임 진행 (채팅/음성)
web/frontend/templates/mygame.html     - Mygame (즐겨찾기)
web/frontend/router.py                 - 라우터 + API 엔드포인트
web/frontend/service.py                - 데이터 조회 서비스
```
