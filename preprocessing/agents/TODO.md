# TODO - 멀티에이전트 파이프라인 후속 작업

## 완료된 작업
- [x] LangGraph 멀티에이전트 파이프라인 구현 (preprocessing/agents/)
- [x] 5건 테스트 완료 (브라스, 윙스팬, 렉시오, 뱅!, 시타델)
- [x] 벡터화 청크 분할 (토큰 한도 초과 수정)
- [x] revise_node 섹션별 이슈 합산 수정
- [x] 게임 진행 시작 메시지 (인원수 질문 / 세팅 안내 분기)
- [x] /api/play 게임 진행 전용 API (짧은 구어체, 단계별 진행)
- [x] 마크다운 테이블 렌더링 (서버 md_to_html + 클라이언트 formatMarkdown)
- [x] STT: gpt-4o-mini-transcribe (MediaRecorder + 침묵 감지 VAD)
- [x] TTS: gpt-4o-mini-tts (GM 음성 출력)

## 수정 필요 (다음 작업)
- [ ] **RAG 벡터 검색 적용**: /api/chat, /api/play 모두 현재 전체 룰 텍스트를 시스템 프롬프트에 통째로 넣고 있음. ChromaDB game_rules 컬렉션에 이미 임베딩 되어있으므로, 사용자 질문으로 벡터 검색 → 관련 청크만 context로 제공하도록 변경 필요
  - /api/chat: 전체 9개 섹션 → 벡터 검색으로 관련 청크만
  - /api/play: 시스템 프롬프트에는 플레이북만, 사용자 질문은 벡터 검색으로 관련 룰 참조
- [ ] **PDF 이미지 추출 테스트**: source_file이 등록된 룰에서 컴포넌트 이미지 추출 동작 확인
