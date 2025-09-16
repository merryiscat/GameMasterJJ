# **GameMasterJJ 프로젝트 문서 요약 및 참조 가이드**

**최종 업데이트**: 
**전체 문서 수**: 
**아키텍처 기반 문서**: docs/0_architecture.md

## **📑 목차 (Table of Contents)**

1. 
2.
3.

---

## **📋 프로젝트 개요**


### **핵심 특징**

---

## **🚀 구현 단계별 빠른 참조**

### **📋 개발 시작 전 필수 확인**
- **프로젝트 목표**: [docs/1_goal_scope_definition.md](docs/1_goal_scope_definition.md)
- **핵심 아키텍처**: [docs/0_architecture.md](docs/0_architecture.md)
- **기능 명세**: [docs/2_detailed_functional_specification.md](docs/2_detailed_functional_specification.md)

### **⚙️ 백엔드 개발 시 참조**
- **API 설계**: [docs/4_api_specification.md](docs/4_api_specification.md)
- **데이터 모델**: [docs/5_data_model_schema.md](docs/5_data_model_schema.md)
- **LLM 에이전트 구조**: [docs/0_architecture.md](docs/0_architecture.md) → 섹션 1, 2

### **🎨 프론트엔드 개발 시 참조**
- **UI 디자인 시스템**: [docs/3_ui_design_system.md](docs/3_ui_design_system.md)
- **사용자 플로우**: [docs/2_detailed_functional_specification.md](docs/2_detailed_functional_specification.md) → FEAT-001~012
- **API 연동**: [docs/4_api_specification.md](docs/4_api_specification.md)

### **🧪 테스트 및 디버깅 시 참조**
- **테스트 전략**: [docs/7_unit_Integration_Test.md](docs/7_unit_Integration_Test.md)
- **버그 추적**: [docs/8_bug_report.md](docs/8_bug_report.md)
- **실행 계획**: [docs/6_master_execution_plan.md](docs/6_master_execution_plan.md)

### **📱 주요 구현 포인트**
예시_
| 기능 | 파일 참조 | 핵심 섹션 |
|------|-----------|-----------|
| 기능예시1 | [docs/0_architecture.md](docs/0_architecture.md) | 섹션 1.1, 표 1 |
| 기능예시2 | [docs/2_detailed_functional_specification.md](docs/2_detailed_functional_specification.md) | FEAT-002 |
| 기능예시3 | [docs/4_api_specification.md](docs/4_api_specification.md) | 4.2.2 |

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
- **주요 목표**: 
- **타겟 사용자**: 
- **MVP 범위**: 
- **성공 지표**: 

#### **2. 상세 기능 명세 (docs/2_detailed_functional_specification.md)**
**참조**: docs/0_architecture.md, docs/1_goal_scope_definition.md
**핵심 내용**:

#### **3. UI 디자인 시스템 (docs/3_ui_design_system.md)**
**참조**: docs/0_architecture.md, docs/2_detailed_functional_specification.md
**핵심 내용**:

#### **4. API 명세 (docs/4_api_specification.md)**
**참조**: docs/0_architecture.md, docs/3_ui_design_system.md
**핵심 내용**:

#### **5. 데이터 모델 스키마 (docs/5_data_model_schema.md)**
**참조**: docs/0_architecture.md, docs/4_api_specification.md
**핵심 내용**:

#### **6. 마스터 실행 계획 (docs/6_master_execution_plan.md)**
**참조**: docs/0_architecture.md, docs/5_data_model_schema.md
**핵심 내용**:


#### **7. 단위/통합 테스트 (docs/7_unit_Integration_Test.md)**
**참조**: docs/0_architecture.md, docs/6_master_execution_plan.md
**핵심 내용**:


#### **8. 버그 리포트 및 이슈 추적 (docs/8_bug_report.md)**
**참조**: docs/0_architecture.md, docs/7_unit_Integration_Test.md
**핵심 내용**:

---

## **🔧 기술 스택 요약**

### **백엔드**


### **프론트엔드**


### **인프라**

---

## **🎯 핵심 구현 포인트**

---

## **📈 성능 및 품질 기준**

### **응답 시간 목표**


### **품질 지표**


### **확장성 목표**

---

## **🚀 배포 및 운영**

### **개발 환경**


### **프로덕션 배포**


### **모니터링**


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
- **원인**: 
- **해결**: 
- **참조**: 


### **디버깅 도구**


## **📋 체크리스트**

### **개발 완료 체크리스트**


### **배포 전 체크리스트**


---

## **🔗 외부 리소스**

### **참고 문서**


### **개발 도구**


---

## **📞 연락처 및 지원**


**최종 검토**: 