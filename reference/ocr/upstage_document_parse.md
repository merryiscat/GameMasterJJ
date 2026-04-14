# Upstage Document Parse API

> 출처: https://console.upstage.ai/api/parse/document-parsing

## 개요

Upstage Document Parse는 문서(PDF, 이미지)를 구조화된 텍스트로 변환하는 API.
OCR + 레이아웃 분석 + 표 추출을 한번에 처리하며, 마크다운/HTML/텍스트 출력 지원.

## API 엔드포인트

```
POST https://api.upstage.ai/v1/document-digitization
```

## 인증

```
Authorization: Bearer {UPSTAGE_API_KEY}
```

## 요청 파라미터 (form-data)

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| document | file | O | 업로드할 문서 파일 (PDF, 이미지) |
| ocr | string | X | OCR 모드: `"force"` (강제), `"auto"` (자동 판별) |
| output_formats | list | X | 출력 형식: `["html", "text", "markdown"]` |
| base64_encoding | list | X | base64 이미지 포함 대상: `["table"]` 등 |
| coordinates | bool | X | 바운딩박스 좌표 포함 여부 |
| model | string | X | 모델 지정: `"document-parse"` |

## 응답 JSON 구조

```json
{
  "api": "API 버전",
  "model": "모델 버전",
  "content": {
    "text": "전체 문서 텍스트 (plain text)",
    "html": "전체 문서 HTML",
    "markdown": "전체 문서 마크다운"
  },
  "elements": [
    {
      "id": 0,
      "category": "paragraph | table | figure | chart | header | ...",
      "page": 1,
      "content": {
        "text": "요소 텍스트",
        "html": "요소 HTML",
        "markdown": "요소 마크다운"
      },
      "coordinates": { ... },
      "base64_encoding": "..."
    }
  ],
  "usage": {
    "pages": 12
  }
}
```

### elements.category 종류
- `paragraph` — 일반 텍스트
- `table` — 표
- `figure` — 그림/이미지
- `chart` — 차트
- `header` — 제목/헤딩

## Python 예시

```python
import requests

api_key = "YOUR_UPSTAGE_API_KEY"
url = "https://api.upstage.ai/v1/document-digitization"

headers = {"Authorization": f"Bearer {api_key}"}
files = {"document": open("rulebook.pdf", "rb")}
data = {
    "ocr": "force",
    "output_formats": "['text', 'markdown']",
    "model": "document-parse",
}

response = requests.post(url, headers=headers, files=files, data=data)
result = response.json()

# 전체 마크다운 텍스트
print(result["content"]["markdown"])

# 요소별 순회
for elem in result["elements"]:
    print(f"[{elem['category']}] p.{elem['page']}: {elem['content']['text'][:100]}")
```

## 제한사항

- 표준 문서(200단어 이상): 약 3초 소요
- 긴 문서: 수십 초 소요
- 서버 타임아웃: 5분
- 미인식 문자: `�` 기호로 표시

## 가격

- 무료 티어: 월 100페이지
- 유료: 페이지당 과금 (공식 사이트 참조)

## GMJJ 프로젝트 적용 메모

### 왜 Upstage인가?
- **한국어 특화**: 한국 회사, 한국어 OCR 품질 우수
- **레이아웃 보존**: 보드게임 룰북의 표, 다단 레이아웃, 아이콘 설명 등 구조 파악에 강점
- **마크다운 출력**: parse 단계에서 LLM이 섹션 분리하기 수월
- **elements 단위 분리**: 표/그림/문단이 이미 분리되어 나옴 → 후처리 용이

### 파이프라인 적용 방식
1. `step1_ocr.py`에서 Upstage API 호출
2. 응답의 `content.markdown`을 `game_rules.raw_text`에 저장
3. `elements` 배열은 `extra_sections.ocr_elements`에 저장 (후처리용)
4. 텍스트 PDF도 `ocr: "force"`로 통일 처리 가능

### 환경변수
```
UPSTAGE_API_KEY=up_xxxxxxxxxxxxxxxx
```
