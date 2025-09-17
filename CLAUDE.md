# **GameMasterJJ 프로젝트 문서 요약 및 참조 가이드**

**최종 업데이트**: 2025-09-17
**전체 문서 수**: 9개 (docs/0~8.md)
**아키텍처 기반 문서**: docs/0_architecture.md

## **📑 목차 (Table of Contents)**

1. [프로젝트 개요](#📋-프로젝트-개요)
2. [구현 단계별 빠른 참조](#🚀-구현-단계별-빠른-참조)
3. [문서 구조 및 상호 참조](#📚-문서-구조-및-상호-참조)
4. [기술 스택 요약](#🔧-기술-스택-요약)
5. [핵심 구현 포인트](#🎯-핵심-구현-포인트)
6. [성능 및 품질 기준](#📈-성능-및-품질-기준)
7. [개발자 가이드](#📖-개발자-가이드)

---

## **📋 프로젝트 개요**

**GameMasterJJ**는 AI 기반 TRPG (테이블탑 롤플레잉 게임) 게임 마스터 시스템으로, 멀티-에이전트 아키텍처를 통해 몰입감 있는 게임 경험을 제공합니다.

### **핵심 특징**
- 🤖 **멀티-에이전트 AI GM 시스템**: 5개 전문 에이전트 (Triage, Narrator, Rules Keeper, NPC Interaction, Lore Keeper)
- 🎤 **실시간 음성 통합**: STT/TTS 기반 자연스러운 음성 상호작용
- 📱 **크로스 플랫폼 지원**: React Native 기반 iOS/Android 앱
- 🎲 **도구 기반 규칙 적용**: AI 환각 방지를 위한 엄격한 게임 규칙 시스템
- 📖 **스토리렛 시스템**: 모듈식 서사 구조로 동적 스토리 생성

---

## **🚀 구현 단계별 빠른 참조**

### **📋 개발 시작 전 필수 확인**
- **프로젝트 목표**: [docs/1_goal_scope_definition.md](docs/1_goal_scope_definition.md) → 타겟 사용자, MVP 범위, 성공 지표
- **핵심 아키텍처**: [docs/0_architecture.md](docs/0_architecture.md) → 멀티-에이전트 시스템, 음성 통합, 기술 스택
- **기능 명세**: [docs/2_detailed_functional_specification.md](docs/2_detailed_functional_specification.md) → FEAT-001~020 상세 기능

### **⚙️ 백엔드 개발 시 참조**
- **API 설계**: [docs/4_api_specification.md](docs/4_api_specification.md) → RESTful API, WebSocket, 인증
- **데이터 모델**: [docs/5_data_model_schema.md](docs/5_data_model_schema.md) → SQLite 스키마, Pydantic 모델
- **LLM 에이전트 구조**: [docs/0_architecture.md](docs/0_architecture.md) → 섹션 1 (에이전트 시스템), 섹션 2 (핸드오프)

### **🎨 프론트엔드 개발 시 참조**
- **UI 디자인 시스템**: [docs/3_ui_design_system.md](docs/3_ui_design_system.md) → 디자인 토큰, 컴포넌트, 테마
- **사용자 플로우**: [docs/2_detailed_functional_specification.md](docs/2_detailed_functional_specification.md) → FEAT-001~020
- **API 연동**: [docs/4_api_specification.md](docs/4_api_specification.md) → 엔드포인트, 요청/응답 형식

### **🧪 테스트 및 디버깅 시 참조**
- **테스트 전략**: [docs/7_unit_Integration_Test.md](docs/7_unit_Integration_Test.md) → 단위/통합/E2E 테스트
- **버그 추적**: [docs/8_bug_report.md](docs/8_bug_report.md) → 버그 분류, 추적 워크플로우, 예방
- **실행 계획**: [docs/6_master_execution_plan.md](docs/6_master_execution_plan.md) → 7주 개발 로드맵

### **📱 주요 구현 포인트**
| 기능 | 파일 참조 | 핵심 섹션 |
|------|-----------|-----------|
| 멀티-에이전트 시스템 | [docs/0_architecture.md](docs/0_architecture.md) | 섹션 1.1, 표 1 (에이전트 역할) |
| 음성 처리 파이프라인 | [docs/2_detailed_functional_specification.md](docs/2_detailed_functional_specification.md) | FEAT-002 (STT/TTS 통합) |
| 실시간 WebSocket | [docs/4_api_specification.md](docs/4_api_specification.md) | 4.2.2 (WebSocket 명세) |
| 스토리렛 엔진 | [docs/5_data_model_schema.md](docs/5_data_model_schema.md) | 5.4 (JSON 컨텐츠 스키마) |
| 주사위 굴리기 시스템 | [docs/3_ui_design_system.md](docs/3_ui_design_system.md) | 3.3.3 (DiceRoller 컴포넌트) |

---

## **📚 문서 구조 및 상호 참조**

### **문서 작성 방법론**
각 문서는 다음 참조 패턴을 따릅니다:
- **1번 파일**: 0번 파일 참조
- **2번 파일**: 0번 + 1번 파일 참조
- **3번 파일**: 0번 + 2번 파일 참조
- **...이하 동일 패턴**

### **문서 목록 및 핵심 내용**

#### **1. 목표 및 범위 정의 (docs/1_goal_scope_definition.md)**
**참조**: docs/0_architecture.md
**핵심 내용**:
- **주요 목표**: AI 기반 TRPG GM 시스템으로 몰입감 높은 게임 경험 제공
- **타겟 사용자**: TRPG 경험자, 신규 입문자, 온라인 게임 그룹
- **MVP 범위**: 멀티-에이전트 시스템, 음성 통합, 기본 게임 세션 관리
- **성공 지표**: DAU 1,000명, 세션당 평균 2시간, 사용자 만족도 4.2점

#### **2. 상세 기능 명세 (docs/2_detailed_functional_specification.md)**
**참조**: docs/0_architecture.md, docs/1_goal_scope_definition.md
**핵심 내용**:
- **20개 주요 기능** (FEAT-001~020): 에이전트 시스템, 음성 처리, 게임 규칙, UI 컴포넌트
- **사용자 스토리**: 세션 생성부터 캐릭터 관리까지 전체 플레이 플로우
- **기술적 요구사항**: OpenAI Agents SDK, WebSocket 실시간 통신, RAG 시스템

#### **3. UI 디자인 시스템 (docs/3_ui_design_system.md)**
**참조**: docs/0_architecture.md, docs/2_detailed_functional_specification.md
**핵심 내용**:
- **디자인 토큰**: 색상, 타이포그래피, 스페이싱 시스템
- **TRPG 특화 컴포넌트**: DiceRoller, CharacterStat, HealthBar, VoiceRecorder
- **테마 시스템**: 라이트/다크 모드, 접근성 가이드라인

#### **4. API 명세 (docs/4_api_specification.md)**
**참조**: docs/0_architecture.md, docs/3_ui_design_system.md
**핵심 내용**:
- **RESTful API**: 게임 세션, 캐릭터 관리, 사용자 인증
- **WebSocket API**: 실시간 음성 스트리밍, 채팅, 게임 이벤트
- **에러 처리**: 표준화된 에러 응답, 재시도 로직, 레이트 리밋

#### **5. 데이터 모델 스키마 (docs/5_data_model_schema.md)**
**참조**: docs/0_architecture.md, docs/4_api_specification.md
**핵심 내용**:
- **SQLite 테이블**: users, game_sessions, characters, chat_messages 등
- **JSON 스키마**: 스토리렛, NPC, 룰북 데이터 구조
- **Pydantic 모델**: API 요청/응답 검증, 타입 안전성

#### **6. 마스터 실행 계획 (docs/6_master_execution_plan.md)**
**참조**: docs/0_architecture.md, docs/5_data_model_schema.md
**핵심 내용**:
- **7주 개발 로드맵**: 5단계 (기반 구축→음성 통합→UI→스토리렛→테스트)
- **13개 구체적 TASK**: 각 작업별 입력, 출력, 성공 기준 정의
- **리스크 관리**: 기술적 위험도 평가 및 완화 전략

#### **7. 단위/통합 테스트 (docs/7_unit_Integration_Test.md)**
**참조**: docs/0_architecture.md, docs/6_master_execution_plan.md
**핵심 내용**:
- **테스트 피라미드**: 단위 70%, 통합 25%, E2E 5%
- **Agent 시스템 테스트**: 핸드오프 로직, LLM API 통합, 음성 처리
- **자동화 도구**: pytest, Jest, Detox, CI/CD 파이프라인

#### **8. 버그 리포트 및 이슈 추적 (docs/8_bug_report.md)**
**참조**: docs/0_architecture.md, docs/7_unit_Integration_Test.md
**핵심 내용**:
- **버그 분류 체계**: 심각도(CRITICAL~TRIVIAL), 우선순위(P0~P4)
- **특화 패턴**: LLM Agent, 음성 처리, React Native 관련 버그
- **자동화 시스템**: 에러 모니터링, 성능 감지, 예측 분석

---

## **🔧 기술 스택 요약**

### **백엔드**
- **프레임워크**: FastAPI (Python 3.11+)
- **AI/LLM**: OpenAI Agents SDK, GPT-4o-mini
- **데이터베이스**: SQLite (개발), PostgreSQL (프로덕션)
- **음성 처리**: OpenAI Whisper (STT), ElevenLabs (TTS)
- **실시간 통신**: WebSocket, Server-Sent Events
- **데이터 검증**: Pydantic, SQLAlchemy

### **프론트엔드**
- **프레임워크**: React Native 0.72+
- **언어**: TypeScript
- **상태 관리**: Zustand
- **UI 라이브러리**: React Native Elements, Styled Components
- **음성 통합**: react-native-audio-recorder-player
- **테스트**: Jest, React Native Testing Library, Detox

### **인프라**
- **개발환경**: Docker, Docker Compose
- **CI/CD**: GitHub Actions
- **모니터링**: Sentry (에러 추적), Firebase Analytics
- **배포**: 미정 (AWS/Azure/GCP)

---

## **🎯 핵심 구현 포인트**

### **🤖 멀티-에이전트 아키텍처**
- **핸드오프 시스템**: Triage Agent가 사용자 입력을 적절한 전문 Agent로 라우팅
- **도구 기반 규칙 적용**: Rules_Keeper_Agent가 명확한 게임 규칙을 적용하여 AI 환각 방지
- **컨텍스트 관리**: 각 Agent 간 게임 상태와 대화 히스토리 공유

### **🎤 음성 통합 시스템**
- **실시간 STT**: OpenAI Whisper를 통한 음성→텍스트 변환
- **다중 TTS**: ElevenLabs API로 GM, NPC별 고유 음성 생성
- **WebSocket 스트리밍**: 음성 데이터 실시간 전송 및 처리

### **📖 스토리렛 기반 서사**
- **조건부 콘텐츠**: 게임 상태에 따른 동적 스토리 분기
- **모듈식 구조**: 재사용 가능한 서사 요소들의 조합
- **RAG 시스템**: 기존 룰북과 설정 정보를 바탕으로 한 일관된 세계관

### **⚡ 성능 최적화**
- **에이전트 응답 캐싱**: 반복되는 질의에 대한 빠른 응답
- **음성 스트리밍**: 청크 단위 음성 처리로 지연시간 최소화
- **컴포넌트 최적화**: React Native의 메모이제이션 및 가상화 활용

---

## **📈 성능 및 품질 기준**

### **응답 시간 목표**
- **Agent 응답**: 평균 < 3초 (GPT API 호출 포함)
- **음성 전사 (STT)**: < 1초
- **음성 합성 (TTS)**: < 2초
- **API 엔드포인트**: 평균 < 200ms

### **품질 지표**
- **코드 커버리지**: 80% 이상 (단위 테스트 85%, 통합 테스트 70%)
- **사용자 만족도**: 4.2/5.0 이상
- **세션 완료율**: 85% 이상 (중도 이탈 15% 미만)
- **음성 인식 정확도**: 95% 이상

### **확장성 목표**
- **동시 세션**: 100개 (MVP), 1,000개 (목표)
- **동시 사용자**: 500명 (MVP), 5,000명 (목표)
- **응답 시간 유지**: 사용자 증가에도 SLA 기준 유지
- **데이터베이스**: 10만 세션, 100만 메시지 처리 가능

---

## **🚀 배포 및 운영**

### **개발 환경**
- **로컬 개발**: Docker Compose로 백엔드, 데이터베이스 통합 실행
- **React Native**: Metro bundler, iOS Simulator/Android Emulator
- **API 테스트**: Postman, Thunder Client
- **개발 서버**: FastAPI 개발 모드 (auto-reload 활성화)

### **프로덕션 배포**
- **컨테이너화**: Docker 멀티스테이지 빌드
- **CI/CD**: GitHub Actions (테스트→빌드→배포)
- **앱 배포**: App Store, Google Play Store
- **백엔드 배포**: 클라우드 플랫폼 (AWS/Azure/GCP 중 선택)

### **모니터링**
- **에러 추적**: Sentry (백엔드/프론트엔드 통합)
- **성능 모니터링**: APM 도구, 커스텀 메트릭스
- **사용자 분석**: Firebase Analytics, 게임 플레이 지표
- **알림 시스템**: Slack/Discord 웹훅, 이메일 알림


---

## **📖 개발자 가이드**

### **📋 docs 기반 개발 워크플로우**

#### **1. 개발 진행 프로세스**
1. **TASK 선택**: [docs/6_master_execution_plan.md](docs/6_master_execution_plan.md)에서 다음 TASK 확인
2. **상태 업데이트**: 해당 TASK 상태를 "준비됨" → "진행 중"으로 변경
3. **관련 문서 참조**: TASK에 명시된 입력 문서들 확인
4. **개발 진행**: 실제 구현 작업
5. **변경사항 기록**: 개발 중 변경/추가사항을 해당 docs 파일에 직접 업데이트
6. **TASK 완료**: 성공 기준 달성 시 상태를 "완료"로 변경

#### **2. 변경사항 기록 원칙**
- **API 변경** → [docs/4_api_specification.md](docs/4_api_specification.md) 직접 수정
- **기능 추가/변경** → [docs/2_detailed_functional_specification.md](docs/2_detailed_functional_specification.md) 업데이트
- **UI 컴포넌트 변경** → [docs/3_ui_design_system.md](docs/3_ui_design_system.md) 업데이트
- **데이터 스키마 변경** → [docs/5_data_model_schema.md](docs/5_data_model_schema.md) 업데이트
- **버그 발견** → [docs/8_bug_report.md](docs/8_bug_report.md)에 기록
- **테스트 케이스 추가** → [docs/7_unit_Integration_Test.md](docs/7_unit_Integration_Test.md) 업데이트

#### **3. 토큰 효율적 개발**
- 필요한 특정 docs 파일만 선택적으로 참조
- CLAUDE.md는 네비게이션 용도로만 사용
- 실제 상세 정보는 항상 docs 파일에서 최신 상태 유지

### **새 기능 추가 시**
1. **기능 명세서 작성** → [docs/2_detailed_functional_specification.md](docs/2_detailed_functional_specification.md)
2. **API 설계** → [docs/4_api_specification.md](docs/4_api_specification.md)
3. **데이터 모델 수정** → [docs/5_data_model_schema.md](docs/5_data_model_schema.md)
4. **UI 컴포넌트 구현** → [docs/3_ui_design_system.md](docs/3_ui_design_system.md)
5. **테스트 작성** → [docs/7_unit_Integration_Test.md](docs/7_unit_Integration_Test.md)
6. **버그 추적 설정** → [docs/8_bug_report.md](docs/8_bug_report.md)

---

## **🔍 트러블슈팅 가이드**

### **일반적인 문제**
- **Agent 핸드오프 실패**: Triage Agent 분류 로직 확인, 핸드오프 체인 로그 분석
- **음성 처리 지연**: WebSocket 연결 상태, 오디오 버퍼 크기 점검
- **LLM API 응답 오류**: 토큰 수 확인, 프롬프트 엔지니어링 검토
- **참조**: [docs/8_bug_report.md](docs/8_bug_report.md) → 8.3 특화 버그 패턴

### **디버깅 도구**
- **백엔드**: FastAPI 자동 문서화 (/docs), Pydantic 검증 로그
- **프론트엔드**: Flipper, React Developer Tools, Metro bundler 로그
- **음성 처리**: 오디오 웨이브폼 분석, WebSocket 트래픽 모니터링
- **Agent 시스템**: 핸드오프 체인 시각화, 컨텍스트 상태 추적

## **📋 체크리스트**

### **개발 완료 체크리스트**
- [ ] 모든 FEAT-001~020 기능 구현 완료
- [ ] 단위/통합 테스트 80% 이상 커버리지 달성
- [ ] Agent 핸드오프 정상 동작 확인
- [ ] 음성 STT/TTS 통합 테스트 통과
- [ ] API 문서화 완료 및 검증
- [ ] UI/UX 디자인 시스템 일관성 확인

### **배포 전 체크리스트**
- [ ] 성능 기준 충족 (응답시간, 메모리 사용량)
- [ ] 보안 스캔 및 취약점 점검 완료
- [ ] 에러 모니터링 시스템 설정 완료
- [ ] 백업 및 복구 계획 수립
- [ ] 사용자 가이드 및 도움말 준비
- [ ] 롤백 계획 및 긴급 대응 절차 확정

---

## **🔗 외부 리소스**

### **참고 문서**
- [OpenAI Agents SDK 문서](https://platform.openai.com/docs/agents)
- [React Native 공식 가이드](https://reactnative.dev/docs/getting-started)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [TRPG 게임 디자인 참고서](https://www.rpg-design-patterns.com/)

### **개발 도구**
- **IDE**: VSCode, WebStorm
- **API 테스트**: Postman, Insomnia
- **디자인**: Figma, Sketch
- **협업**: GitHub, Slack/Discord
- **프로젝트 관리**: Linear, Notion

---

## **📞 연락처 및 지원**

- **프로젝트 저장소**: [GitHub 링크 추가 예정]
- **이슈 트래킹**: GitHub Issues 활용
- **개발팀 연락처**: [연락처 정보 추가 예정]
- **사용자 지원**: [고객지원 채널 정보 추가 예정]

**최종 검토**: 2025-09-17 - 모든 문서 확장 완료, 개발 착수 준비 완료 


##긴급하게 적용해야하는 사항
● 감사합니다! 명확한 답변을 주셔서 프로젝트 방향성이 훨씬 구체화되었습니다. 이 정보를 바탕으로 문서 업데이트 방향과    
   개발 우선순위를 재정리해드리겠습니다.

  📋 답변 기반 프로젝트 방향성 재정리

  1. 기술 스택 확정

  ✅ 확정된 기술 선택

  - LLM: OpenAI GPT-4o-mini (로컬 LLM 제외)
  - 음성 처리: OpenAI Agents SDK 음성 도구 (구현 용이성 우선)
  - 아키텍처: 온라인 기반 (오프라인 모드 제외)

  🔍 상태 관리 선택 가이드 (Zustand vs Redux)

  Zustand 추천 이유:
  - 학습 곡선: Redux보다 훨씬 단순함
  - 보일러플레이트: 최소한의 코드로 상태 관리
  - TypeScript 지원: 기본 내장
  - 번들 크기: Redux Toolkit보다 작음

  // Zustand 예시 (간단함)
  const useGameStore = create((set) => ({
    character: null,
    messages: [],
    setCharacter: (character) => set({ character }),
    addMessage: (message) => set((state) => ({
      messages: [...state.messages, message]
    })),
  }))

  2. 로컬 저장소 필요성 설명

  왜 로컬 저장소가 필요한가?
  1. 게임 세션 데이터: 캐릭터 정보, 진행 상황, 채팅 히스토리
  2. 사용자 설정: 음성 설정, UI 선호도, 게임 옵션
  3. 오프라인 대비: 네트워크 끊김 시 임시 데이터 보관
  4. 성능 최적화: 자주 사용하는 데이터 캐싱

  제안: 하이브리드 저장 방식
  - 클라우드: 주요 게임 데이터 (동기화)
  - 로컬: 임시 데이터, 캐시, 사용자 설정

  3. DLC 기반 수익화 모델 설계

  📦 콘텐츠 구조 제안

  Base Game (무료)
  ├── 튜토리얼 스토리렛
  ├── 기본 캐릭터 클래스 (3개)
  └── 샘플 캠페인 (2-3시간)

  DLC Packs (유료)
  ├── 스토리 팩: "용의 던전" ($2.99)
  ├── 캐릭터 팩: "마법사 클래스" ($1.99)
  └── 시스템 팩: "고급 규칙" ($3.99)

  🔧 DLC 시스템 구현 필요사항

  1. 콘텐츠 관리 시스템: DLC 스토리렛 로딩
  2. 결제 연동: App Store/Google Play 인앱 결제
  3. 라이센스 검증: DLC 소유권 확인
  4. 콘텐츠 배포: 스토리렛 다운로드 시스템

  ---
  🔄 문서 업데이트 권장사항

  수정이 필요한 문서들

  docs/0_architecture.md

  - Section 6 수정: 로컬 LLM 부분 제거, OpenAI API 중심으로 재작성
  - 오프라인 모드 언급 제거: 온라인 기반 아키텍처로 단순화

  docs/1_goal_scope_definition.md

  - MVP 범위 수정: 오프라인 기능 제거
  - 수익화 모델 추가: DLC 기반 콘텐츠 판매 전략
  - 타겟 사용자 조정: 초기 100명 → 확장 계획

  docs/4_api_specification.md

  - DLC 관리 API 추가: 콘텐츠 구매, 다운로드, 라이센스 검증
  - 결제 시스템 API: 인앱 결제 연동

  docs/6_master_execution_plan.md

  - Phase 추가: DLC 시스템 구현 단계
  - 일정 조정: 개인 프로젝트 특성 반영

  새로 추가할 문서

  9_dlc_content_system.md

  # DLC 콘텐츠 시스템 설계
  - 콘텐츠 패키징 방식
  - 결제 연동 구현
  - 라이센스 검증 시스템
  - 콘텐츠 배포 파이프라인

  10_monetization_strategy.md

  # 수익화 전략 및 구현
  - DLC 가격 정책
  - 콘텐츠 제작 가이드라인
  - 사용자 구매 분석
  - A/B 테스트 계획

  ---
  🚀 개발 우선순위 재조정

  Phase 1: 핵심 기능 (변경 없음)

  - 다중 에이전트 시스템
  - 기본 게임 규칙 엔진

  Phase 2: 음성 통합 (OpenAI 중심)

  - OpenAI Agents SDK 음성 도구 활용
  - 연결형 아키텍처 구현

  Phase 3: React Native + Zustand

  - Zustand 상태 관리 구현
  - 클라우드 기반 데이터 동기화

  Phase 4: DLC 시스템 (신규 추가)

  - 콘텐츠 관리 시스템
  - 인앱 결제 연동
  - 라이센스 검증

  Phase 5: 테스트 및 최적화

  - 100명 동시 사용자 대응
  - 모바일 성능 최적화

  ---
  ❓ 추가 확인이 필요한 사항

  1. 첫 번째 DLC 콘텐츠: 어떤 스토리를 먼저 제작할 계획인가요?
  2. 결제 시스템: App Store/Google Play 개발자 계정 준비 상황은?
  3. 콘텐츠 제작 도구: 스토리렛 제작을 위한 에디터 도구가 필요한가요?
  4. 베타 테스트: 초기 100명 사용자 모집 계획이 있나요?

  이제 더욱 실현 가능하고 명확한 방향성을 가진 프로젝트가 되었습니다! 🎯