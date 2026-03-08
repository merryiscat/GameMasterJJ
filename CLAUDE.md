# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

**GMJJ** - LLM 에이전트 기반 보드게임 룰 안내/진행 + TRPG 게임마스터 + 시나리오 마켓 애플리케이션

### 핵심 기능 3가지
1. **보드게임 어시스턴트**: RAG 기반 룰 안내, 상황 판정, 게임 진행
2. **TRPG 게임마스터**: 대화형 서사 진행, 룰북 기반 수치 계산, 캐릭터 시트/플레이 로그 관리
3. **시나리오 마켓**: 유저 제작 TRPG 시나리오 등록/매매

### 타겟 사용자
- **입문자**: 클래식 보드게임 룰 안내 및 진행
- **숙련자**: TRPG GM 제공, 새로운 게임 환경
- **B2B**: 보드게임 카페 체인 (레드버튼 등) 대상 큐레이션

### 수익 모델
- 기본 룰북/클래식 보드게임 무료
- TRPG GM 진행: 토큰제
- 시나리오 마켓 수수료
- B2B 큐레이션

## 기술 스택

- **백엔드**: FastAPI + Python
- **프론트엔드**: Flutter
- **AI**: OpenAI Agents SDK + RAG
- **음성**: STT/TTS (예정)
- **DB**: 미정

## 프로젝트 상태

초기 기획 단계. 기존 코드 전체 초기화 완료.
기획 원본: `C:\Users\minhy\project\obsidian\study\GMJJ 기획안.md`
