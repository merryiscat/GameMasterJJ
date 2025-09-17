# **7. 단위/통합 테스트 (Unit & Integration Test)**

## **7.1 테스트 전략 개요**

### **7.1.1 테스트 계층 구조**
```
E2E 테스트 (5%)
├─ 전체 사용자 시나리오 검증
└─ 실제 환경에서의 통합 동작 확인

통합 테스트 (25%)
├─ API 엔드포인트 테스트
├─ 데이터베이스 연동 테스트
├─ LLM API 목업 테스트
└─ SSE 스트림 테스트

단위 테스트 (70%)
├─ 개별 함수/메서드 테스트
├─ 컴포넌트 단위 테스트
├─ 비즈니스 로직 검증
└─ 에러 케이스 처리
```

### **7.1.2 테스트 도구 및 프레임워크**

**백엔드 (Python)**
- **pytest**: 메인 테스트 프레임워크
- **pytest-asyncio**: 비동기 테스트 지원
- **httpx**: HTTP 클라이언트 테스트
- **pytest-mock**: 목업 및 스텁 생성
- **factory-boy**: 테스트 데이터 생성
- **pytest-cov**: 코드 커버리지 측정

**프론트엔드 (React Native)**
- **Jest**: 단위 테스트 프레임워크
- **React Native Testing Library**: 컴포넌트 테스트
- **Detox**: E2E 테스트
- **MSW**: API 목업 서버

## **7.2 백엔드 단위 테스트**

### **7.2.1 Agent 시스템 테스트**

**Triage_GM_Agent 테스트**
```python
# tests/agents/test_triage_agent.py
import pytest
from unittest.mock import Mock, patch
from agents.triage_gm_agent import TriageGMAgent

class TestTriageGMAgent:
    @pytest.fixture
    def triage_agent(self):
        return TriageGMAgent()

    @pytest.mark.asyncio
    async def test_classify_user_input_combat(self, triage_agent):
        user_input = "I attack the orc with my sword!"
        session_context = {"current_scene": "combat", "characters": ["player1"]}

        result = await triage_agent.classify_input(user_input, session_context)

        assert result["target_agent"] == "rules_keeper"
        assert result["action_type"] == "combat_action"
        assert result["urgency"] == "high"

    @pytest.mark.asyncio
    async def test_classify_user_input_dialogue(self, triage_agent):
        user_input = "Hello, what's your name?"
        session_context = {"current_scene": "dialogue", "npc_present": True}

        result = await triage_agent.classify_input(user_input, session_context)

        assert result["target_agent"] == "npc_interaction"
        assert result["action_type"] == "dialogue"

    def test_validate_handoff_rules(self, triage_agent):
        # 핸드오프 규칙 검증
        handoff_data = {
            "target_agent": "narrator",
            "context": {"scene": "exploration"},
            "priority": "medium"
        }

        is_valid = triage_agent.validate_handoff(handoff_data)
        assert is_valid == True
```

**Rules_Keeper_Agent 테스트**
```python
# tests/agents/test_rules_keeper.py
import pytest
from agents.rules_keeper_agent import RulesKeeperAgent
from models.character import Character

class TestRulesKeeperAgent:
    @pytest.fixture
    def rules_agent(self):
        return RulesKeeperAgent()

    @pytest.fixture
    def sample_character(self):
        return Character(
            id="char1",
            name="TestHero",
            attributes={"strength": 15, "dexterity": 12, "health": 100}
        )

    def test_dice_roll_mechanics(self, rules_agent):
        # D20 시스템 테스트
        result = rules_agent.roll_dice("1d20+5")
        assert 6 <= result <= 25

        # 복수 주사위 테스트
        result = rules_agent.roll_dice("3d6")
        assert 3 <= result <= 18

    def test_combat_calculation(self, rules_agent, sample_character):
        attack_roll = 15
        target_ac = 12
        damage = rules_agent.calculate_damage("1d8+3")

        result = rules_agent.resolve_attack(
            attacker=sample_character,
            attack_roll=attack_roll,
            target_ac=target_ac,
            damage=damage
        )

        assert result["hit"] == True
        assert 4 <= result["damage"] <= 11

    def test_attribute_check(self, rules_agent, sample_character):
        # 능력치 판정 테스트
        result = rules_agent.attribute_check(
            character=sample_character,
            attribute="strength",
            difficulty_class=10
        )

        assert "success" in result
        assert "roll_result" in result
```

### **7.2.2 음성 처리 테스트**

```python
# tests/voice/test_voice_processor.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from voice.voice_processor import VoiceProcessor

class TestVoiceProcessor:
    @pytest.fixture
    def voice_processor(self):
        return VoiceProcessor()

    @pytest.mark.asyncio
    async def test_speech_to_text_conversion(self, voice_processor):
        # 목업 오디오 데이터
        mock_audio_data = b"mock_audio_data"
        expected_text = "Hello, I want to cast a spell"

        with patch('voice.stt_client.transcribe') as mock_stt:
            mock_stt.return_value = expected_text

            result = await voice_processor.process_audio(mock_audio_data)

            assert result["text"] == expected_text
            assert result["confidence"] > 0.8

    @pytest.mark.asyncio
    async def test_text_to_speech_generation(self, voice_processor):
        text = "The dragon breathes fire!"
        voice_id = "narrator_voice"

        with patch('voice.tts_client.synthesize') as mock_tts:
            mock_tts.return_value = b"mock_audio_output"

            result = await voice_processor.generate_speech(text, voice_id)

            assert len(result) > 0
            assert isinstance(result, bytes)

    def test_voice_activity_detection(self, voice_processor):
        # 음성 활동 감지 테스트
        silent_audio = b"\x00" * 1024  # 무음 데이터
        voice_audio = b"mock_voice_data"

        assert voice_processor.detect_voice_activity(silent_audio) == False
        assert voice_processor.detect_voice_activity(voice_audio) == True
```

### **7.2.3 Storylet 시스템 테스트**

```python
# tests/storylet/test_storylet_engine.py
import pytest
from storylet.storylet_engine import StoryletEngine
from models.storylet import Storylet, StoryletCondition

class TestStoryletEngine:
    @pytest.fixture
    def storylet_engine(self):
        return StoryletEngine()

    @pytest.fixture
    def sample_storylet(self):
        return Storylet(
            id="tavern_encounter",
            title="Mysterious Stranger",
            conditions=[
                StoryletCondition("location", "==", "tavern"),
                StoryletCondition("time_of_day", "==", "evening")
            ],
            content={
                "narrator_text": "A hooded figure approaches your table...",
                "choices": [
                    {"text": "Listen to their offer", "consequence": "quest_start"},
                    {"text": "Ignore them", "consequence": "missed_opportunity"}
                ]
            }
        )

    def test_storylet_condition_matching(self, storylet_engine, sample_storylet):
        game_state = {
            "location": "tavern",
            "time_of_day": "evening",
            "player_level": 3
        }

        is_available = storylet_engine.check_availability(sample_storylet, game_state)
        assert is_available == True

        # 조건 불충족 테스트
        game_state["location"] = "forest"
        is_available = storylet_engine.check_availability(sample_storylet, game_state)
        assert is_available == False

    def test_storylet_selection_algorithm(self, storylet_engine):
        # 여러 storylet 중 최적 선택 테스트
        available_storylets = [
            {"id": "common_event", "weight": 0.5, "priority": 1},
            {"id": "rare_event", "weight": 0.1, "priority": 3},
            {"id": "urgent_event", "weight": 0.3, "priority": 5}
        ]

        selected = storylet_engine.select_storylet(available_storylets)
        assert selected["id"] == "urgent_event"  # 최고 우선순위
```

## **7.3 백엔드 통합 테스트**

### **7.3.1 API 엔드포인트 테스트**

```python
# tests/integration/test_api_endpoints.py
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from main import app
from database import get_test_db

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers():
    # 테스트용 인증 토큰
    return {"Authorization": "Bearer test_token"}

class TestGameSessionAPI:
    def test_create_game_session(self, client, auth_headers):
        session_data = {
            "title": "Test Campaign",
            "game_system": "dnd5e",
            "max_players": 4,
            "voice_enabled": True
        }

        response = client.post(
            "/api/v1/sessions",
            json=session_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Campaign"
        assert data["session_id"] is not None

    def test_join_game_session(self, client, auth_headers):
        # 세션 생성
        session_response = client.post(
            "/api/v1/sessions",
            json={"title": "Join Test", "max_players": 2}
        )
        session_id = session_response.json()["session_id"]

        # 세션 참가
        join_response = client.post(
            f"/api/v1/sessions/{session_id}/join",
            headers=auth_headers
        )

        assert join_response.status_code == 200
        assert join_response.json()["status"] == "joined"

    def test_send_chat_message(self, client, auth_headers):
        # 기존 세션에 메시지 전송
        message_data = {
            "message": "I want to investigate the room",
            "message_type": "action"
        }

        response = client.post(
            "/api/v1/sessions/test_session/messages",
            json=message_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["processed"] == True
        assert "agent_response" in data
```

### **7.3.2 데이터베이스 통합 테스트**

```python
# tests/integration/test_database.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from database.models import Character, GameSession, ChatMessage
from database.crud import character_crud, session_crud

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///./test.db")
    async with AsyncSession(engine) as session:
        yield session

class TestCharacterCRUD:
    @pytest.mark.asyncio
    async def test_create_character(self, db_session):
        character_data = {
            "name": "Test Wizard",
            "character_class": "wizard",
            "level": 1,
            "attributes": {"intelligence": 16, "wisdom": 14}
        }

        character = await character_crud.create(db_session, character_data)

        assert character.name == "Test Wizard"
        assert character.character_class == "wizard"
        assert character.attributes["intelligence"] == 16

    @pytest.mark.asyncio
    async def test_character_level_up(self, db_session):
        # 캐릭터 생성
        character = await character_crud.create(
            db_session,
            {"name": "Level Test", "level": 1}
        )

        # 레벨업 처리
        updated = await character_crud.level_up(
            db_session,
            character.id
        )

        assert updated.level == 2
        assert updated.updated_at is not None
```

### **7.3.3 LLM API 통합 테스트**

```python
# tests/integration/test_llm_integration.py
import pytest
from unittest.mock import patch, AsyncMock
from agents.base_agent import BaseAgent
from llm.openai_client import OpenAIClient

class TestLLMIntegration:
    @pytest.fixture
    def openai_client(self):
        return OpenAIClient()

    @pytest.mark.asyncio
    async def test_agent_llm_communication(self, openai_client):
        messages = [
            {"role": "system", "content": "You are a D&D narrator"},
            {"role": "user", "content": "Describe a mysterious forest"}
        ]

        with patch.object(openai_client, 'chat_completion') as mock_chat:
            mock_response = {
                "choices": [{
                    "message": {
                        "content": "The ancient forest whispers with secrets..."
                    }
                }]
            }
            mock_chat.return_value = mock_response

            result = await openai_client.generate_response(messages)

            assert "forest" in result.lower()
            assert len(result) > 50

    @pytest.mark.asyncio
    async def test_llm_error_handling(self, openai_client):
        # API 오류 상황 시뮬레이션
        with patch.object(openai_client, 'chat_completion') as mock_chat:
            mock_chat.side_effect = Exception("API Error")

            with pytest.raises(Exception):
                await openai_client.generate_response([])
```

## **7.4 프론트엔드 테스트**

### **7.4.1 React Native 컴포넌트 테스트**

```javascript
// tests/components/DiceRoller.test.js
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import DiceRoller from '../src/components/DiceRoller';

describe('DiceRoller Component', () => {
  test('renders dice roller with default state', () => {
    const { getByText, getByTestId } = render(<DiceRoller />);

    expect(getByText('Roll Dice')).toBeTruthy();
    expect(getByTestId('dice-display')).toBeTruthy();
  });

  test('rolls dice and displays result', async () => {
    const { getByText, getByTestId } = render(<DiceRoller diceType="d20" />);

    fireEvent.press(getByText('Roll Dice'));

    await waitFor(() => {
      const result = getByTestId('dice-result').props.children;
      expect(result).toBeGreaterThanOrEqual(1);
      expect(result).toBeLessThanOrEqual(20);
    });
  });

  test('supports modifier calculation', async () => {
    const { getByText, getByTestId } = render(
      <DiceRoller diceType="d20" modifier={5} />
    );

    fireEvent.press(getByText('Roll Dice'));

    await waitFor(() => {
      const totalResult = getByTestId('total-result').props.children;
      expect(totalResult).toBeGreaterThanOrEqual(6); // 1 + 5
      expect(totalResult).toBeLessThanOrEqual(25);   // 20 + 5
    });
  });
});
```

### **7.4.2 음성 UI 컴포넌트 테스트**

```javascript
// tests/components/VoiceRecorder.test.js
import React from 'react';
import { render, fireEvent, act } from '@testing-library/react-native';
import VoiceRecorder from '../src/components/VoiceRecorder';
import * as VoiceService from '../src/services/VoiceService';

// VoiceService 목업
jest.mock('../src/services/VoiceService');

describe('VoiceRecorder Component', () => {
  beforeEach(() => {
    VoiceService.startRecording = jest.fn();
    VoiceService.stopRecording = jest.fn();
  });

  test('starts recording when record button pressed', async () => {
    const { getByTestId } = render(<VoiceRecorder />);

    await act(async () => {
      fireEvent.press(getByTestId('record-button'));
    });

    expect(VoiceService.startRecording).toHaveBeenCalled();
  });

  test('displays recording status correctly', async () => {
    const { getByTestId, getByText } = render(<VoiceRecorder />);

    await act(async () => {
      fireEvent.press(getByTestId('record-button'));
    });

    expect(getByText('Recording...')).toBeTruthy();
    expect(getByTestId('recording-indicator')).toBeTruthy();
  });

  test('processes voice input correctly', async () => {
    const mockOnTranscription = jest.fn();
    VoiceService.stopRecording.mockResolvedValue({
      text: 'I cast magic missile',
      confidence: 0.95
    });

    const { getByTestId } = render(
      <VoiceRecorder onTranscription={mockOnTranscription} />
    );

    // 녹음 시작
    await act(async () => {
      fireEvent.press(getByTestId('record-button'));
    });

    // 녹음 중지
    await act(async () => {
      fireEvent.press(getByTestId('stop-button'));
    });

    expect(mockOnTranscription).toHaveBeenCalledWith('I cast magic missile');
  });
});
```

### **7.4.3 게임 상태 관리 테스트**

```javascript
// tests/store/gameStore.test.js
import { renderHook, act } from '@testing-library/react-hooks';
import { useGameStore } from '../src/store/gameStore';

describe('Game Store', () => {
  test('initializes with default state', () => {
    const { result } = renderHook(() => useGameStore());

    expect(result.current.sessionId).toBeNull();
    expect(result.current.characters).toEqual([]);
    expect(result.current.messages).toEqual([]);
    expect(result.current.isVoiceEnabled).toBe(false);
  });

  test('updates session state correctly', () => {
    const { result } = renderHook(() => useGameStore());

    act(() => {
      result.current.setSession({
        sessionId: 'test-session-123',
        title: 'Test Campaign'
      });
    });

    expect(result.current.sessionId).toBe('test-session-123');
    expect(result.current.sessionTitle).toBe('Test Campaign');
  });

  test('adds chat messages correctly', () => {
    const { result } = renderHook(() => useGameStore());

    act(() => {
      result.current.addMessage({
        id: 'msg-1',
        sender: 'player',
        content: 'Hello world',
        timestamp: new Date()
      });
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toBe('Hello world');
  });
});
```

## **7.5 E2E 테스트**

### **7.5.1 게임 세션 전체 플로우 테스트**

```javascript
// e2e/gameSession.e2e.js
import { device, element, by, expect } from 'detox';

describe('Game Session E2E Flow', () => {
  beforeAll(async () => {
    await device.launchApp();
  });

  beforeEach(async () => {
    await device.reloadReactNative();
  });

  it('should complete full game session creation and play', async () => {
    // 1. 홈 화면에서 새 세션 생성
    await element(by.id('create-session-button')).tap();

    // 2. 세션 설정 입력
    await element(by.id('session-title-input')).typeText('E2E Test Session');
    await element(by.id('max-players-input')).typeText('4');
    await element(by.id('voice-toggle')).tap();
    await element(by.id('create-button')).tap();

    // 3. 세션 생성 확인
    await expect(element(by.text('E2E Test Session'))).toBeVisible();
    await expect(element(by.id('session-code'))).toBeVisible();

    // 4. 캐릭터 생성
    await element(by.id('create-character-button')).tap();
    await element(by.id('character-name-input')).typeText('Test Hero');
    await element(by.id('character-class-picker')).tap();
    await element(by.text('Fighter')).tap();
    await element(by.id('confirm-character-button')).tap();

    // 5. 게임 시작
    await element(by.id('start-game-button')).tap();

    // 6. 채팅 메시지 전송
    await element(by.id('chat-input')).typeText('I look around the room');
    await element(by.id('send-button')).tap();

    // 7. GM 응답 확인
    await waitFor(element(by.id('gm-response')))
      .toBeVisible()
      .withTimeout(5000);

    // 8. 주사위 굴리기
    await element(by.id('dice-roller-button')).tap();
    await element(by.text('d20')).tap();
    await element(by.id('roll-button')).tap();

    // 9. 주사위 결과 확인
    await expect(element(by.id('dice-result'))).toBeVisible();
  });

  it('should handle voice input correctly', async () => {
    // 음성 입력 테스트 (목업 사용)
    await element(by.id('voice-record-button')).tap();

    // 녹음 상태 확인
    await expect(element(by.id('recording-indicator'))).toBeVisible();

    // 녹음 중지
    await element(by.id('voice-stop-button')).tap();

    // 전사 결과 확인 (목업 데이터)
    await waitFor(element(by.text('I cast fireball at the goblin')))
      .toBeVisible()
      .withTimeout(3000);
  });
});
```

### **7.5.2 멀티플레이어 시나리오 테스트**

```javascript
// e2e/multiplayer.e2e.js
describe('Multiplayer Scenarios', () => {
  it('should handle multiple players joining session', async () => {
    // Device 1: GM이 세션 생성
    await device.launchApp({newInstance: true});
    await element(by.id('create-session-button')).tap();
    await element(by.id('session-title-input')).typeText('Multiplayer Test');
    await element(by.id('create-button')).tap();

    const sessionCode = await element(by.id('session-code')).getAttributes();

    // Device 2 시뮬레이션: 플레이어 참가
    // (실제로는 별도 기기나 시뮬레이터 필요)
    await element(by.id('join-session-button')).tap();
    await element(by.id('session-code-input')).typeText(sessionCode.text);
    await element(by.id('join-button')).tap();

    // 플레이어 목록 확인
    await expect(element(by.id('player-list'))).toBeVisible();
    await expect(element(by.text('2 players connected'))).toBeVisible();
  });
});
```

## **7.6 테스트 실행 및 자동화**

### **7.6.1 테스트 스크립트 설정**

**package.json**
```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:e2e": "detox test",
    "test:e2e:build": "detox build",
    "test:backend": "cd backend && python -m pytest",
    "test:backend:coverage": "cd backend && python -m pytest --cov=.",
    "test:integration": "cd backend && python -m pytest tests/integration/",
    "test:unit": "cd backend && python -m pytest tests/unit/",
    "test:all": "npm run test:backend && npm run test && npm run test:e2e"
  }
}
```

**pytest.ini**
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --asyncio-mode=auto
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    e2e: marks tests as end-to-end tests
```

### **7.6.2 CI/CD 파이프라인 테스트 자동화**

**GitHub Actions 워크플로우**
```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install -r requirements-test.txt

    - name: Run unit tests
      run: cd backend && python -m pytest tests/unit/ -v

    - name: Run integration tests
      run: cd backend && python -m pytest tests/integration/ -v

    - name: Generate coverage report
      run: cd backend && python -m pytest --cov=. --cov-report=xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'

    - name: Install dependencies
      run: npm ci

    - name: Run unit tests
      run: npm run test -- --coverage --watchAll=false

    - name: Run E2E tests
      run: |
        npm run test:e2e:build
        npm run test:e2e

  performance-tests:
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]
    steps:
    - uses: actions/checkout@v3
    - name: Run load tests
      run: |
        # 성능 테스트 실행 (예: k6, Artillery 등)
        echo "Performance tests placeholder"
```

### **7.6.3 테스트 데이터 관리**

**테스트 픽스처**
```python
# tests/fixtures/game_fixtures.py
import pytest
from factory import Factory, Faker, SubFactory
from models.character import Character
from models.game_session import GameSession

class CharacterFactory(Factory):
    class Meta:
        model = Character

    name = Faker('name')
    character_class = Faker('random_element', elements=['fighter', 'wizard', 'rogue'])
    level = 1
    attributes = {
        'strength': 10,
        'dexterity': 10,
        'constitution': 10,
        'intelligence': 10,
        'wisdom': 10,
        'charisma': 10
    }

class GameSessionFactory(Factory):
    class Meta:
        model = GameSession

    title = Faker('sentence', nb_words=3)
    game_system = 'dnd5e'
    max_players = 4
    voice_enabled = True

@pytest.fixture
def sample_character():
    return CharacterFactory()

@pytest.fixture
def sample_session():
    return GameSessionFactory()
```

### **7.6.4 테스트 메트릭스 및 품질 게이트**

**커버리지 목표**
- **단위 테스트**: 85% 이상
- **통합 테스트**: 70% 이상
- **전체 코드 커버리지**: 80% 이상

**성능 기준**
- **API 응답 시간**: 평균 < 200ms
- **음성 처리 지연**: < 1초
- **동시 사용자**: 100명 지원

**품질 게이트**
```python
# tests/quality_gates.py
import pytest

def test_code_coverage_threshold():
    """코드 커버리지가 임계값 이상인지 확인"""
    # pytest-cov와 연동하여 자동 확인
    pass

def test_performance_benchmarks():
    """성능 벤치마크 테스트"""
    # API 응답 시간, 메모리 사용량 등 확인
    pass

def test_security_scan():
    """보안 취약점 스캔"""
    # bandit, safety 등 보안 도구 실행 결과 확인
    pass
```
