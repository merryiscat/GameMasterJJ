# **4. API 명세 (API Specification)**

**참조 문서**: docs/0_architecture.md, docs/3_ui_design_system.md
**작성일**: 2025-09-17
**버전**: 1.0

## **4.1 API 개요**

**Base URL**: `http://localhost:8000/api/v1`
**프로토콜**: HTTP/HTTPS with WebSocket for real-time features
**인증**: API Key based authentication
**데이터 형식**: JSON (application/json)

### **4.1.1 공통 응답 구조**

**성공 응답**
```json
{
  "success": true,
  "data": {
    // 실제 응답 데이터
  },
  "message": "Operation completed successfully",
  "timestamp": "2025-09-17T10:30:00Z",
  "requestId": "uuid-v4-string"
}
```

**오류 응답**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      // 추가 오류 정보
    }
  },
  "timestamp": "2025-09-17T10:30:00Z",
  "requestId": "uuid-v4-string"
}
```

### **4.1.2 공통 오류 코드**

```json
{
  "INVALID_INPUT": "입력 데이터가 유효하지 않습니다",
  "AUTHENTICATION_FAILED": "인증에 실패했습니다",
  "AUTHORIZATION_DENIED": "권한이 없습니다",
  "RESOURCE_NOT_FOUND": "요청한 리소스를 찾을 수 없습니다",
  "RATE_LIMIT_EXCEEDED": "API 호출 한도를 초과했습니다",
  "LLM_API_ERROR": "LLM API 호출 중 오류가 발생했습니다",
  "AGENT_ERROR": "에이전트 처리 중 오류가 발생했습니다",
  "VOICE_PROCESSING_ERROR": "음성 처리 중 오류가 발생했습니다",
  "DATABASE_ERROR": "데이터베이스 오류가 발생했습니다",
  "INTERNAL_SERVER_ERROR": "서버 내부 오류가 발생했습니다"
}
```

## **4.2 게임 세션 관리 API**

### **4.2.1 세션 생성**
```http
POST /sessions
```

**Request Body**
```json
{
  "storyId": "story-uuid",
  "characterData": {
    "name": "Character Name",
    "class": "Fighter",
    "level": 1,
    "stats": {
      "strength": 16,
      "dexterity": 14,
      "constitution": 15,
      "intelligence": 10,
      "wisdom": 12,
      "charisma": 8
    }
  },
  "settings": {
    "voiceEnabled": true,
    "autoSave": true,
    "difficulty": "normal"
  }
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "sessionId": "session-uuid",
    "character": {
      "id": "character-uuid",
      "name": "Character Name",
      "level": 1,
      "currentHp": 12,
      "maxHp": 12
    },
    "gameState": {
      "currentLocation": "Starting Village",
      "activeStorylets": [],
      "worldState": {}
    }
  }
}
```

### **4.2.2 세션 조회**
```http
GET /sessions/{sessionId}
```

**Response**
```json
{
  "success": true,
  "data": {
    "sessionId": "session-uuid",
    "character": { /* 캐릭터 정보 */ },
    "gameState": { /* 게임 상태 */ },
    "chatHistory": [
      {
        "id": "message-uuid",
        "sender": "gm",
        "content": "Welcome to the adventure!",
        "timestamp": "2025-09-17T10:30:00Z"
      }
    ],
    "lastActivity": "2025-09-17T10:30:00Z"
  }
}
```

### **4.2.3 세션 저장**
```http
PUT /sessions/{sessionId}/save
```

**Request Body**
```json
{
  "saveSlot": "auto_save_1",
  "description": "Before entering the dungeon"
}
```

### **4.2.4 세션 로드**
```http
POST /sessions/{sessionId}/load
```

**Request Body**
```json
{
  "saveSlot": "auto_save_1"
}
```

## **4.3 에이전트 상호작용 API**

### **4.3.1 플레이어 액션 처리**
```http
POST /sessions/{sessionId}/actions
```

**Request Body**
```json
{
  "type": "text" | "voice",
  "content": "I want to attack the goblin",
  "voiceData": {
    "audioFormat": "wav",
    "sampleRate": 16000,
    "audioData": "base64-encoded-audio"
  }
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "agentResponse": {
      "agent": "triage_gm",
      "handoffTo": "rules_keeper",
      "context": {
        "action": "attack",
        "target": "goblin",
        "skillCheck": "melee_attack"
      }
    },
    "gameStateChanges": {
      "diceRolls": [
        {
          "formula": "1d20+3",
          "result": 15,
          "success": true
        }
      ],
      "characterUpdates": {
        "currentHp": 10
      }
    },
    "narrative": {
      "text": "Your sword strikes true! The goblin staggers back.",
      "voiceText": "Your sword strikes true! The goblin staggers back.",
      "audioUrl": "/audio/response-uuid.mp3"
    }
  }
}
```

### **4.3.2 에이전트별 직접 호출**

#### **Triage GM Agent**
```http
POST /agents/triage
```

**Request Body**
```json
{
  "sessionId": "session-uuid",
  "playerInput": "I want to talk to the innkeeper",
  "context": {
    "currentLocation": "The Prancing Pony",
    "availableNpcs": ["innkeeper", "bard", "merchant"]
  }
}
```

#### **Rules Keeper Agent**
```http
POST /agents/rules-keeper
```

**Request Body**
```json
{
  "sessionId": "session-uuid",
  "action": "skill_check",
  "parameters": {
    "skill": "persuasion",
    "difficulty": 15,
    "characterId": "character-uuid"
  }
}
```

#### **Narrator Agent**
```http
POST /agents/narrator
```

**Request Body**
```json
{
  "sessionId": "session-uuid",
  "scene": {
    "location": "Dark Forest",
    "event": "encounter_wolves",
    "mood": "tense"
  },
  "context": {
    "previousActions": ["moved_north", "stealth_check_failed"]
  }
}
```

#### **NPC Interaction Agent**
```http
POST /agents/npc-interaction
```

**Request Body**
```json
{
  "sessionId": "session-uuid",
  "npcId": "innkeeper-001",
  "playerMessage": "Do you have any rooms available?",
  "context": {
    "relationship": "neutral",
    "previousInteractions": []
  }
}
```

#### **Lore Keeper Agent**
```http
POST /agents/lore-keeper
```

**Request Body**
```json
{
  "sessionId": "session-uuid",
  "query": "Tell me about the history of this kingdom",
  "context": {
    "currentLocation": "Royal Library",
    "playerKnowledge": ["basic_geography", "recent_events"]
  }
}
```

## **4.4 게임 규칙 API**

### **4.4.1 주사위 굴리기**
```http
POST /game/dice/roll
```

**Request Body**
```json
{
  "formula": "2d6+3",
  "reason": "Attack roll against goblin",
  "sessionId": "session-uuid"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "formula": "2d6+3",
    "rolls": [4, 6],
    "modifier": 3,
    "total": 13,
    "breakdown": "4 + 6 + 3 = 13",
    "timestamp": "2025-09-17T10:30:00Z"
  }
}
```

### **4.4.2 캐릭터 상태 조회**
```http
GET /game/characters/{characterId}
```

**Response**
```json
{
  "success": true,
  "data": {
    "id": "character-uuid",
    "name": "Aragorn",
    "class": "Ranger",
    "level": 3,
    "experience": 900,
    "stats": {
      "strength": 16,
      "dexterity": 18,
      "constitution": 14,
      "intelligence": 12,
      "wisdom": 15,
      "charisma": 10
    },
    "derivedStats": {
      "armorClass": 15,
      "hitPoints": {
        "current": 24,
        "max": 28,
        "temporary": 0
      },
      "speed": 30,
      "proficiencyBonus": 2
    },
    "skills": {
      "survival": 7,
      "stealth": 6,
      "perception": 5
    },
    "equipment": {
      "worn": [
        {
          "id": "leather-armor",
          "name": "Leather Armor",
          "type": "armor",
          "acBonus": 2
        }
      ],
      "weapons": [
        {
          "id": "longsword",
          "name": "Longsword",
          "damage": "1d8+3",
          "type": "slashing"
        }
      ]
    },
    "inventory": [
      {
        "id": "healing-potion",
        "name": "Potion of Healing",
        "quantity": 2,
        "description": "Restores 2d4+2 hit points"
      }
    ],
    "statusEffects": []
  }
}
```

### **4.4.3 캐릭터 상태 업데이트**
```http
PUT /game/characters/{characterId}
```

**Request Body**
```json
{
  "updates": {
    "hitPoints": {
      "current": 20
    },
    "experience": 950,
    "statusEffects": [
      {
        "name": "Blessed",
        "duration": 600,
        "effect": "advantage on saving throws"
      }
    ]
  },
  "reason": "Healed by cleric"
}
```

### **4.4.4 인벤토리 관리**
```http
POST /game/characters/{characterId}/inventory
```

**아이템 추가**
```json
{
  "action": "add",
  "item": {
    "id": "magic-sword",
    "name": "Flame Tongue",
    "type": "weapon",
    "rarity": "rare",
    "properties": ["magical", "fire_damage"]
  },
  "quantity": 1
}
```

**아이템 제거**
```json
{
  "action": "remove",
  "itemId": "healing-potion",
  "quantity": 1
}
```

**아이템 사용**
```json
{
  "action": "use",
  "itemId": "healing-potion",
  "target": "self"
}
```

## **4.5 음성 처리 API**

### **4.5.1 음성-텍스트 변환 (STT)**
```http
POST /voice/stt
```

**Request Headers**
```
Content-Type: multipart/form-data
```

**Request Body (Form Data)**
```
audioFile: [binary audio file]
format: wav | mp3 | m4a
sampleRate: 16000 | 44100
language: ko-KR | en-US
```

**Response**
```json
{
  "success": true,
  "data": {
    "transcription": "고블린을 공격하고 싶어요",
    "confidence": 0.95,
    "alternatives": [
      {
        "text": "고블린을 공격하고 싶어",
        "confidence": 0.89
      }
    ],
    "language": "ko-KR",
    "duration": 2.5
  }
}
```

### **4.5.2 텍스트-음성 변환 (TTS)**
```http
POST /voice/tts
```

**Request Body**
```json
{
  "text": "당신의 검이 고블린을 정확히 맞췄습니다!",
  "voice": {
    "gender": "neutral",
    "language": "ko-KR",
    "speed": 1.0,
    "pitch": 1.0
  },
  "format": "mp3",
  "quality": "high"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "audioUrl": "/audio/tts-uuid.mp3",
    "duration": 3.2,
    "format": "mp3",
    "size": 45632
  }
}
```

### **4.5.3 실시간 음성 처리 (WebSocket)**
```
ws://localhost:8000/voice/realtime/{sessionId}
```

**연결 시 메시지**
```json
{
  "type": "connection",
  "sessionId": "session-uuid",
  "settings": {
    "audioFormat": "wav",
    "sampleRate": 16000,
    "enableVoiceActivity": true
  }
}
```

**음성 데이터 전송**
```json
{
  "type": "audio_data",
  "data": "base64-encoded-audio-chunk",
  "timestamp": 1634567890000
}
```

**STT 결과 수신**
```json
{
  "type": "stt_result",
  "text": "I want to cast a fireball",
  "isFinal": true,
  "confidence": 0.92
}
```

**TTS 오디오 수신**
```json
{
  "type": "tts_audio",
  "audioData": "base64-encoded-audio",
  "isComplete": false
}
```

## **4.6 스토리렛 관리 API**

### **4.6.1 스토리렛 조회**
```http
GET /storylets
```

**Query Parameters**
- `active`: boolean - 활성화 가능한 스토리렛만 조회
- `location`: string - 특정 위치의 스토리렛
- `tags`: string[] - 태그로 필터링

**Response**
```json
{
  "success": true,
  "data": {
    "storylets": [
      {
        "id": "tavern-encounter-001",
        "title": "Mysterious Stranger",
        "description": "A hooded figure sits alone in the corner",
        "preconditions": {
          "location": "tavern",
          "timeOfDay": "evening",
          "flags": ["!met_stranger"]
        },
        "postconditions": {
          "flags": ["met_stranger"],
          "relationships": {
            "stranger": "acquainted"
          }
        },
        "content": {
          "opening": "As you enter the tavern...",
          "choices": [
            {
              "text": "Approach the stranger",
              "consequences": ["start_conversation"]
            },
            {
              "text": "Ignore and order a drink",
              "consequences": ["missed_opportunity"]
            }
          ]
        },
        "tags": ["social", "mystery", "optional"]
      }
    ]
  }
}
```

### **4.6.2 스토리렛 실행**
```http
POST /sessions/{sessionId}/storylets/{storyletId}/execute
```

**Request Body**
```json
{
  "choice": "approach_stranger",
  "context": {
    "playerState": {
      "charisma": 14,
      "reputation": "unknown"
    }
  }
}
```

### **4.6.3 추상적 행동 구체화**
```http
POST /storylets/abstract-actions/resolve
```

**Request Body**
```json
{
  "sessionId": "session-uuid",
  "abstractAction": {
    "type": "betrayal",
    "target": "ally",
    "severity": "major",
    "timing": "dramatic_moment"
  },
  "currentContext": {
    "allies": ["wizard", "rogue", "cleric"],
    "location": "final_battle",
    "tension": "high"
  }
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "concreteEvent": {
      "betrayer": "rogue",
      "method": "backstab_during_combat",
      "motivation": "secretly_working_for_villain",
      "timing": "when_wizard_is_vulnerable"
    },
    "narrativeDescription": "Just as the wizard begins to cast the final spell...",
    "gameplayConsequences": {
      "removeAlly": "rogue",
      "addEnemy": "rogue_betrayer",
      "moraleDamage": -2
    }
  }
}
```

## **4.7 LLM 통합 API**

### **4.7.1 LLM 모델 상태**
```http
GET /llm/status
```

**Response**
```json
{
  "success": true,
  "data": {
    "model": "gpt-4o-mini",
    "status": "online",
    "latency": 1250,
    "tokensUsed": {
      "today": 15420,
      "thisMonth": 450000
    },
    "rateLimit": {
      "requestsPerMinute": 60,
      "tokensPerMinute": 40000,
      "remainingRequests": 45,
      "remainingTokens": 35000,
      "resetTime": "2025-09-17T10:31:00Z"
    }
  }
}
```

### **4.7.2 직접 LLM 호출**
```http
POST /llm/chat
```

**Request Body**
```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful D&D dungeon master."
    },
    {
      "role": "user",
      "content": "Describe a mysterious forest clearing."
    }
  ],
  "temperature": 0.7,
  "maxTokens": 500,
  "stream": false
}
```

### **4.7.3 스트리밍 응답**
```http
POST /llm/chat/stream
```

**Response (Server-Sent Events)**
```
data: {"type": "start", "id": "response-uuid"}

data: {"type": "content", "delta": "The clearing"}

data: {"type": "content", "delta": " opens before you"}

data: {"type": "end", "usage": {"tokens": 45}}
```

## **4.8 오류 처리 및 상태 코드**

### **4.8.1 HTTP 상태 코드**
- `200 OK`: 성공적인 조회
- `201 Created`: 리소스 생성 성공
- `202 Accepted`: 비동기 처리 시작
- `400 Bad Request`: 잘못된 요청
- `401 Unauthorized`: 인증 실패
- `403 Forbidden`: 권한 없음
- `404 Not Found`: 리소스를 찾을 수 없음
- `409 Conflict`: 리소스 상태 충돌
- `429 Too Many Requests`: 속도 제한 초과
- `500 Internal Server Error`: 서버 내부 오류
- `503 Service Unavailable`: 서비스 일시적 불가

### **4.8.2 재시도 정책**

**지수 백오프 (Exponential Backoff)**
```python
retry_delays = [1, 2, 4, 8, 16]  # seconds
max_retries = 5
```

**재시도 가능한 상태 코드**
- `429 Too Many Requests`
- `500 Internal Server Error`
- `502 Bad Gateway`
- `503 Service Unavailable`
- `504 Gateway Timeout`

**재시도 불가능한 오류**
- `400 Bad Request`
- `401 Unauthorized`
- `403 Forbidden`
- `404 Not Found`

## **4.9 속도 제한 (Rate Limiting)**

### **4.9.1 제한 정책**

**API 엔드포인트별 제한**
```json
{
  "default": {
    "requestsPerMinute": 60,
    "burstLimit": 10
  },
  "llm": {
    "requestsPerMinute": 20,
    "tokensPerMinute": 40000
  },
  "voice": {
    "requestsPerMinute": 30,
    "audioMinutesPerHour": 60
  },
  "gameActions": {
    "requestsPerSecond": 5,
    "burstLimit": 15
  }
}
```

### **4.9.2 제한 초과 응답**

**Headers**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1634567890
X-RateLimit-Type: requests
```

**Response Body**
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "API rate limit exceeded",
    "details": {
      "limit": 60,
      "remaining": 0,
      "resetTime": "2025-09-17T10:31:00Z",
      "retryAfter": 60
    }
  }
}
```

## **4.10 개발자 가이드**

### **4.10.1 SDK 및 클라이언트 라이브러리**

**JavaScript/TypeScript**
```typescript
import { GameMasterAPI } from '@gamemaster/api-client';

const api = new GameMasterAPI({
  baseURL: 'http://localhost:8000/api/v1',
  apiKey: 'your-api-key'
});

// 세션 생성
const session = await api.sessions.create({
  storyId: 'story-uuid',
  characterData: { /* ... */ }
});

// 플레이어 액션
const response = await api.sessions.action(sessionId, {
  type: 'text',
  content: 'I attack the goblin'
});
```

**Python**
```python
from gamemaster_api import GameMasterClient

client = GameMasterClient(
    base_url='http://localhost:8000/api/v1',
    api_key='your-api-key'
)

# 세션 생성
session = client.sessions.create(
    story_id='story-uuid',
    character_data={'name': 'Aragorn'}
)

# 주사위 굴리기
result = client.game.roll_dice('1d20+5')
```

### **4.10.2 WebSocket 연결 예제**

```javascript
const ws = new WebSocket('ws://localhost:8000/voice/realtime/session-uuid');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'connection',
    settings: {
      audioFormat: 'wav',
      sampleRate: 16000
    }
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  switch (message.type) {
    case 'stt_result':
      console.log('Transcription:', message.text);
      break;
    case 'tts_audio':
      playAudioData(message.audioData);
      break;
  }
};
```

### **4.10.3 오류 처리 모범 사례**

```typescript
try {
  const response = await api.sessions.action(sessionId, action);
  return response.data;
} catch (error) {
  if (error.status === 429) {
    // 속도 제한 - 재시도
    await sleep(error.retryAfter * 1000);
    return retryAction();
  } else if (error.status >= 500) {
    // 서버 오류 - 지수 백오프 재시도
    return exponentialBackoffRetry(action);
  } else {
    // 클라이언트 오류 - 사용자에게 알림
    throw new UserFriendlyError(error.message);
  }
}
```

### **4.10.4 성능 최적화 팁**

1. **요청 배칭**: 여러 관련 요청을 하나로 묶기
2. **캐싱**: 캐릭터 상태, 스토리렛 데이터 로컬 캐싱
3. **압축**: gzip 압축 활성화
4. **Connection Pooling**: HTTP/2 또는 연결 재사용
5. **WebSocket 사용**: 실시간 기능에 WebSocket 활용

### **4.10.5 API 버전 관리**

- **URL 버전**: `/api/v1/`, `/api/v2/`
- **하위 호환성**: 최소 2개 버전 지원
- **Deprecation**: 6개월 전 공지
- **마이그레이션 가이드**: 버전별 변경사항 문서화