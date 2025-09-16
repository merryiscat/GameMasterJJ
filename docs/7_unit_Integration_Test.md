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

### **7.2.1 데이터 모델 테스트**

**테스트 파일**: `tests/unit/test_models.py`

```python
import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from src.models import Debate, Agent, Message
from src.database import get_session

class TestDebateModel:
    """토론 모델 단위 테스트"""

    def test_debate_creation_with_valid_data(self, db_session):
        """유효한 데이터로 토론 생성 테스트"""
        # Arrange
        query = "이직을 해야 할까요? 현재 회사는 안정적이지만 성장성이 제한적입니다."

        # Act
        debate = Debate(
            user_query=query,
            status="created",
            estimated_duration=180
        )
        db_session.add(debate)
        db_session.commit()

        # Assert
        assert debate.debate_id is not None
        assert debate.user_query == query
        assert debate.status == "created"
        assert debate.created_at is not None
        assert debate.updated_at is not None

    def test_debate_query_length_validation(self, db_session):
        """질문 길이 제약조건 테스트"""
        # Arrange
        short_query = "짧음"  # 10자 미만
        long_query = "a" * 1001  # 1000자 초과

        # Act & Assert - 너무 짧은 질문
        with pytest.raises(IntegrityError):
            debate = Debate(user_query=short_query)
            db_session.add(debate)
            db_session.commit()

        # Act & Assert - 너무 긴 질문
        with pytest.raises(IntegrityError):
            debate = Debate(user_query=long_query)
            db_session.add(debate)
            db_session.commit()

    def test_debate_status_constraint(self, db_session):
        """토론 상태 제약조건 테스트"""
        # Arrange
        query = "유효한 질문입니다. 테스트를 위한 질문"
        invalid_status = "invalid_status"

        # Act & Assert
        with pytest.raises(IntegrityError):
            debate = Debate(user_query=query, status=invalid_status)
            db_session.add(debate)
            db_session.commit()

class TestAgentModel:
    """에이전트 모델 단위 테스트"""

    def test_agent_creation_with_valid_data(self, db_session, sample_debate):
        """유효한 데이터로 에이전트 생성 테스트"""
        # Arrange
        agent_data = {
            "debate_id": sample_debate.debate_id,
            "hat_type": "white",
            "mbti_type": "ISTJ",
            "role_description": "객관적 정보와 사실 제공",
            "system_prompt": {
                "base_prompt": "You are the white hat agent...",
                "persona_modifier": "ISTJ style...",
                "constraints": ["Be objective", "Stick to facts"],
                "output_format": "JSON"
            }
        }

        # Act
        agent = Agent(**agent_data)
        db_session.add(agent)
        db_session.commit()

        # Assert
        assert agent.agent_id is not None
        assert agent.hat_type == "white"
        assert agent.mbti_type == "ISTJ"
        assert isinstance(agent.system_prompt, dict)

    def test_unique_hat_type_per_debate(self, db_session, sample_debate):
        """토론별 모자 유형 고유성 제약조건 테스트"""
        # Arrange - 첫 번째 하얀 모자 에이전트
        agent1 = Agent(
            debate_id=sample_debate.debate_id,
            hat_type="white",
            mbti_type="ISTJ",
            role_description="First white hat",
            system_prompt={"prompt": "test"}
        )
        db_session.add(agent1)
        db_session.commit()

        # Act & Assert - 같은 토론에 또 다른 하얀 모자 생성 시도
        with pytest.raises(IntegrityError):
            agent2 = Agent(
                debate_id=sample_debate.debate_id,
                hat_type="white",  # 중복된 모자 유형
                mbti_type="ISFJ",
                role_description="Second white hat",
                system_prompt={"prompt": "test"}
            )
            db_session.add(agent2)
            db_session.commit()

    def test_mbti_type_validation(self, db_session, sample_debate):
        """MBTI 유형 형식 검증 테스트"""
        # Act & Assert
        invalid_mbti_types = ["ABC", "INTJJ", "int", "12", ""]

        for invalid_mbti in invalid_mbti_types:
            with pytest.raises(IntegrityError):
                agent = Agent(
                    debate_id=sample_debate.debate_id,
                    hat_type="red",
                    mbti_type=invalid_mbti,
                    role_description="Test agent",
                    system_prompt={"prompt": "test"}
                )
                db_session.add(agent)
                db_session.commit()
                db_session.rollback()

class TestMessageModel:
    """메시지 모델 단위 테스트"""

    def test_message_creation_with_valid_data(self, db_session, sample_agent):
        """유효한 데이터로 메시지 생성 테스트"""
        # Arrange
        content = "이 문제에 대해 객관적으로 분석해보겠습니다."
        turn_number = 1

        # Act
        message = Message(
            debate_id=sample_agent.debate_id,
            agent_id=sample_agent.agent_id,
            content=content,
            turn_number=turn_number,
            metadata={
                "word_count": 25,
                "processing_time_ms": 1500,
                "llm_model": "gpt-4"
            }
        )
        db_session.add(message)
        db_session.commit()

        # Assert
        assert message.message_id is not None
        assert message.content == content
        assert message.turn_number == turn_number
        assert message.is_final_in_turn is True
        assert message.metadata["llm_model"] == "gpt-4"

    def test_message_turn_number_validation(self, db_session, sample_agent):
        """메시지 턴 번호 검증 테스트"""
        # Act & Assert - 0 이하의 턴 번호
        with pytest.raises(IntegrityError):
            message = Message(
                debate_id=sample_agent.debate_id,
                agent_id=sample_agent.agent_id,
                content="Test content",
                turn_number=0  # 1보다 작은 값
            )
            db_session.add(message)
            db_session.commit()

    def test_empty_content_validation(self, db_session, sample_agent):
        """빈 내용 검증 테스트"""
        # Act & Assert
        with pytest.raises(IntegrityError):
            message = Message(
                debate_id=sample_agent.debate_id,
                agent_id=sample_agent.agent_id,
                content="",  # 빈 문자열
                turn_number=1
            )
            db_session.add(message)
            db_session.commit()
```

### **7.2.2 비즈니스 로직 테스트**

**테스트 파일**: `tests/unit/test_services.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.services.debate_service import DebateService
from src.services.agent_service import AgentService
from src.services.llm_service import LLMService
from src.schemas import CreateDebateRequest

class TestDebateService:
    """토론 서비스 단위 테스트"""

    @pytest.fixture
    def debate_service(self, db_session):
        return DebateService(db_session)

    @pytest.fixture
    def mock_agent_service(self):
        return Mock(spec=AgentService)

    async def test_create_debate_success(self, debate_service, mock_agent_service):
        """토론 생성 성공 테스트"""
        # Arrange
        request = CreateDebateRequest(
            query="새로운 직장으로 이직을 고려하고 있습니다.",
            metadata={"source": "mobile_app_v1.0"}
        )

        # Mock agent creation
        mock_agent_service.create_six_agents.return_value = [
            Mock(agent_id="agent1", hat_type="white"),
            Mock(agent_id="agent2", hat_type="red"),
            # ... 6개 에이전트
        ]

        with patch.object(debate_service, 'agent_service', mock_agent_service):
            # Act
            result = await debate_service.create_debate(request)

            # Assert
            assert result.success is True
            assert result.debate_id is not None
            assert len(result.participants) == 6
            assert result.status == "created"

    async def test_create_debate_with_short_query_fails(self, debate_service):
        """짧은 질문으로 토론 생성 실패 테스트"""
        # Arrange
        request = CreateDebateRequest(query="짧음")

        # Act & Assert
        with pytest.raises(ValueError, match="질문이 너무 짧습니다"):
            await debate_service.create_debate(request)

    async def test_finalize_debate_success(self, debate_service, sample_debate):
        """토론 종료 성공 테스트"""
        # Arrange
        debate_id = sample_debate.debate_id

        with patch.object(debate_service, 'start_result_processing') as mock_processing:
            mock_processing.return_value = AsyncMock()

            # Act
            result = await debate_service.finalize_debate(debate_id)

            # Assert
            assert result.success is True
            assert result.status == "finalizing"
            mock_processing.assert_called_once()

    async def test_finalize_nonexistent_debate_fails(self, debate_service):
        """존재하지 않는 토론 종료 실패 테스트"""
        # Arrange
        nonexistent_id = "00000000-0000-0000-0000-000000000000"

        # Act & Assert
        with pytest.raises(ValueError, match="토론을 찾을 수 없습니다"):
            await debate_service.finalize_debate(nonexistent_id)

class TestAgentService:
    """에이전트 서비스 단위 테스트"""

    @pytest.fixture
    def agent_service(self, db_session):
        return AgentService(db_session)

    def test_assign_mbti_with_constraints(self, agent_service):
        """제한된 무작위성 MBTI 할당 테스트"""
        # Act
        white_mbti = agent_service.assign_mbti_for_hat("white")
        red_mbti = agent_service.assign_mbti_for_hat("red")

        # Assert - T/F 제약조건 확인
        assert white_mbti[2] == 'T'  # 세 번째 문자는 T여야 함
        assert red_mbti[2] == 'F'    # 세 번째 문자는 F여야 함

    def test_create_six_agents_success(self, agent_service, sample_debate):
        """6개 에이전트 생성 성공 테스트"""
        # Act
        agents = agent_service.create_six_agents(sample_debate.debate_id)

        # Assert
        assert len(agents) == 6
        hat_types = {agent.hat_type for agent in agents}
        expected_hats = {"white", "red", "black", "yellow", "green", "blue"}
        assert hat_types == expected_hats

        # 각 에이전트가 고유한 MBTI를 가지는지 확인
        mbti_types = [agent.mbti_type for agent in agents]
        assert len(set(mbti_types)) >= 4  # 최소한 4가지는 달라야 함

    def test_generate_system_prompt(self, agent_service):
        """시스템 프롬프트 생성 테스트"""
        # Arrange
        hat_type = "white"
        mbti_type = "ISTJ"

        # Act
        prompt = agent_service.generate_system_prompt(hat_type, mbti_type)

        # Assert
        assert isinstance(prompt, dict)
        assert "base_prompt" in prompt
        assert "persona_modifier" in prompt
        assert "constraints" in prompt
        assert "output_format" in prompt
        assert "white hat" in prompt["base_prompt"].lower()
        assert "istj" in prompt["persona_modifier"].lower()

class TestLLMService:
    """LLM 서비스 단위 테스트"""

    @pytest.fixture
    def llm_service(self):
        return LLMService()

    @pytest.fixture
    def mock_openai_client(self):
        with patch('openai.AsyncOpenAI') as mock:
            client = Mock()
            mock.return_value = client
            yield client

    async def test_generate_response_success(self, llm_service, mock_openai_client):
        """LLM 응답 생성 성공 테스트"""
        # Arrange
        system_prompt = "You are a helpful assistant."
        user_message = "안녕하세요!"
        model = "gpt-4"

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "안녕하세요! 도움이 필요하시면 말씀해 주세요."
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 15

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Act
        result = await llm_service.generate_response(
            system_prompt=system_prompt,
            user_message=user_message,
            model=model
        )

        # Assert
        assert result.success is True
        assert result.content == "안녕하세요! 도움이 필요하시면 말씀해 주세요."
        assert result.metadata["prompt_tokens"] == 10
        assert result.metadata["completion_tokens"] == 15

    async def test_generate_response_with_api_error(self, llm_service, mock_openai_client):
        """LLM API 에러 처리 테스트"""
        # Arrange
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API rate limit exceeded")
        )

        # Act
        result = await llm_service.generate_response(
            system_prompt="Test prompt",
            user_message="Test message",
            model="gpt-4"
        )

        # Assert
        assert result.success is False
        assert "rate limit" in result.error_message.lower()

    async def test_retry_logic_on_failure(self, llm_service, mock_openai_client):
        """실패 시 재시도 로직 테스트"""
        # Arrange
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")

            # 세 번째 시도에서 성공
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Success after retries"
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 5
            return mock_response

        mock_openai_client.chat.completions.create = AsyncMock(side_effect=side_effect)

        # Act
        result = await llm_service.generate_response(
            system_prompt="Test",
            user_message="Test",
            model="gpt-4"
        )

        # Assert
        assert result.success is True
        assert call_count == 3  # 2번 실패 후 3번째에 성공
        assert result.content == "Success after retries"
```

### **7.2.3 유틸리티 함수 테스트**

**테스트 파일**: `tests/unit/test_utils.py`

```python
import pytest
from datetime import datetime, timezone
from src.utils.mbti_utils import MBTIAssigner
from src.utils.prompt_utils import PromptGenerator
from src.utils.validation import validate_debate_query, validate_mbti_type

class TestMBTIAssigner:
    """MBTI 할당 유틸리티 테스트"""

    def test_get_compatible_types_for_thinking_hats(self):
        """사고형(T) 모자에 대한 호환 MBTI 반환 테스트"""
        # Act
        white_types = MBTIAssigner.get_compatible_types("white")
        black_types = MBTIAssigner.get_compatible_types("black")

        # Assert
        for mbti in white_types:
            assert mbti[2] == 'T'  # Thinking

        for mbti in black_types:
            assert mbti[2] == 'T'  # Thinking

    def test_get_compatible_types_for_feeling_hats(self):
        """감정형(F) 모자에 대한 호환 MBTI 반환 테스트"""
        # Act
        red_types = MBTIAssigner.get_compatible_types("red")
        yellow_types = MBTIAssigner.get_compatible_types("yellow")

        # Assert
        for mbti in red_types:
            assert mbti[2] == 'F'  # Feeling

        for mbti in yellow_types:
            assert mbti[2] == 'F'  # Feeling

    def test_get_all_types_for_neutral_hats(self):
        """중립 모자에 대한 전체 MBTI 반환 테스트"""
        # Act
        green_types = MBTIAssigner.get_compatible_types("green")
        blue_types = MBTIAssigner.get_compatible_types("blue")

        # Assert
        assert len(green_types) == 16  # 모든 MBTI 유형
        assert len(blue_types) == 16   # 모든 MBTI 유형

    def test_random_assignment_distribution(self):
        """무작위 할당 분포 테스트"""
        # Act - 100번 할당하여 분포 확인
        assignments = []
        for _ in range(100):
            mbti = MBTIAssigner.assign_random_mbti("white")
            assignments.append(mbti)

        # Assert - 다양한 MBTI가 할당되었는지 확인
        unique_types = set(assignments)
        assert len(unique_types) >= 3  # 최소 3가지 이상의 서로 다른 유형

class TestPromptGenerator:
    """프롬프트 생성기 테스트"""

    def test_generate_base_prompt_for_each_hat(self):
        """각 모자별 기본 프롬프트 생성 테스트"""
        hat_types = ["white", "red", "black", "yellow", "green", "blue"]

        for hat_type in hat_types:
            # Act
            prompt = PromptGenerator.generate_base_prompt(hat_type)

            # Assert
            assert isinstance(prompt, str)
            assert len(prompt) > 50  # 충분한 길이
            assert hat_type in prompt.lower()

    def test_generate_mbti_modifier(self):
        """MBTI 수정자 생성 테스트"""
        # Act
        modifier = PromptGenerator.generate_mbti_modifier("ENTJ")

        # Assert
        assert isinstance(modifier, str)
        assert "ENTJ" in modifier
        assert len(modifier) > 20

    def test_combine_prompt_components(self):
        """프롬프트 구성요소 결합 테스트"""
        # Arrange
        base = "You are a white hat agent."
        modifier = "Act like an INTJ personality."
        constraints = ["Be objective", "Stick to facts"]

        # Act
        result = PromptGenerator.combine_components(base, modifier, constraints)

        # Assert
        assert isinstance(result, dict)
        assert result["base_prompt"] == base
        assert result["persona_modifier"] == modifier
        assert result["constraints"] == constraints
        assert "output_format" in result

class TestValidation:
    """검증 함수 테스트"""

    def test_validate_debate_query_success(self):
        """토론 질문 검증 성공 테스트"""
        # Arrange
        valid_queries = [
            "이직을 해야 할까요? 현재 상황을 고려해 주세요.",
            "새로운 프로젝트에 참여하는 것에 대한 의견을 듣고 싶습니다.",
            "a" * 500  # 적당한 길이
        ]

        for query in valid_queries:
            # Act & Assert
            assert validate_debate_query(query) is True

    def test_validate_debate_query_failure(self):
        """토론 질문 검증 실패 테스트"""
        # Arrange
        invalid_queries = [
            "짧음",        # 너무 짧음
            "a" * 1001,    # 너무 김
            "",            # 빈 문자열
            "   ",         # 공백만
            None           # None 값
        ]

        for query in invalid_queries:
            # Act & Assert
            assert validate_debate_query(query) is False

    def test_validate_mbti_type_success(self):
        """MBTI 유형 검증 성공 테스트"""
        # Arrange
        valid_types = [
            "INTJ", "ENTP", "ISFP", "ESTJ",
            "INFJ", "ENFP", "ISTP", "ESFJ",
            "INTP", "ENTJ", "ISFJ", "ESTP",
            "INFP", "ENFJ", "ISTJ", "ESFP"
        ]

        for mbti_type in valid_types:
            # Act & Assert
            assert validate_mbti_type(mbti_type) is True

    def test_validate_mbti_type_failure(self):
        """MBTI 유형 검증 실패 테스트"""
        # Arrange
        invalid_types = [
            "ABCD", "intj", "INT", "INTJJ",
            "1234", "", None, "XYZ"
        ]

        for mbti_type in invalid_types:
            # Act & Assert
            assert validate_mbti_type(mbti_type) is False
```

## **7.3 백엔드 통합 테스트**

### **7.3.1 API 엔드포인트 테스트**

**테스트 파일**: `tests/integration/test_api_endpoints.py`

```python
import pytest
import json
from httpx import AsyncClient
from fastapi.testclient import TestClient
from src.main import app
from src.database import get_session, engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestDebateAPI:
    """토론 API 통합 테스트"""

    @pytest.fixture
    async def client(self):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    async def test_create_debate_success(self, client):
        """토론 생성 API 성공 테스트"""
        # Arrange
        request_data = {
            "query": "새로운 직장으로 이직을 고려하고 있습니다. 조언을 부탁드립니다.",
            "metadata": {
                "source": "test_client",
                "language": "ko"
            }
        }

        # Act
        response = await client.post("/debate", json=request_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "debate_id" in data["data"]
        assert data["data"]["status"] == "created"
        assert len(data["data"]["participants"]) == 6

        # 참여자 검증
        hat_types = {p["hat_type"] for p in data["data"]["participants"]}
        expected_hats = {"white", "red", "black", "yellow", "green", "blue"}
        assert hat_types == expected_hats

    async def test_create_debate_with_short_query(self, client):
        """짧은 질문으로 토론 생성 실패 테스트"""
        # Arrange
        request_data = {"query": "짧음"}

        # Act
        response = await client.post("/debate", json=request_data)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "질문이 너무 짧습니다" in data["error"]["message"]

    async def test_create_debate_with_missing_query(self, client):
        """질문 누락 시 토론 생성 실패 테스트"""
        # Arrange
        request_data = {}

        # Act
        response = await client.post("/debate", json=request_data)

        # Assert
        assert response.status_code == 422  # Validation error

    async def test_finalize_debate_success(self, client, sample_debate_id):
        """토론 종료 API 성공 테스트"""
        # Act
        response = await client.post(f"/debate/{sample_debate_id}/finalize")

        # Assert
        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "finalizing"
        assert "estimated_completion_time" in data["data"]

    async def test_finalize_nonexistent_debate(self, client):
        """존재하지 않는 토론 종료 시도 테스트"""
        # Arrange
        fake_id = "00000000-0000-0000-0000-000000000000"

        # Act
        response = await client.post(f"/debate/{fake_id}/finalize")

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "DEBATE_NOT_FOUND" in data["error"]["code"]

    async def test_get_debate_result_success(self, client, completed_debate_id):
        """토론 결과 조회 성공 테스트"""
        # Act
        response = await client.get(f"/debate/{completed_debate_id}/result")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "summary" in data["data"]
        assert "statistics" in data["data"]
        assert "visualization_data" in data["data"]

        # 요약 데이터 검증
        summary = data["data"]["summary"]
        assert "title" in summary
        assert "overview" in summary
        assert "key_insights" in summary
        assert isinstance(summary["key_insights"], list)

    async def test_get_debate_result_processing(self, client, processing_debate_id):
        """처리 중인 토론 결과 조회 테스트"""
        # Act
        response = await client.get(f"/debate/{processing_debate_id}/result")

        # Assert
        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "processing"
        assert "retry_after" in data["data"]

class TestSSEStream:
    """SSE 스트림 통합 테스트"""

    async def test_sse_stream_connection(self, client, active_debate_id):
        """SSE 연결 테스트"""
        # Act
        async with client.stream(
            "GET",
            f"/debate/{active_debate_id}/stream",
            headers={"Accept": "text/event-stream"}
        ) as response:
            # Assert
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"

    async def test_sse_message_format(self, client, active_debate_id):
        """SSE 메시지 형식 테스트"""
        message_count = 0

        async with client.stream(
            "GET",
            f"/debate/{active_debate_id}/stream",
            headers={"Accept": "text/event-stream"}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    # JSON 파싱 테스트
                    data_str = line[6:]  # "data: " 제거
                    data = json.loads(data_str)

                    # 메시지 구조 검증
                    if "message_id" in data:
                        assert "hat_type" in data
                        assert "content" in data
                        assert "timestamp" in data
                        assert "turn_number" in data
                        message_count += 1

                # 테스트용으로 3개 메시지만 확인
                if message_count >= 3:
                    break

        assert message_count >= 1

class TestHealthCheck:
    """헬스체크 API 테스트"""

    async def test_health_check_success(self, client):
        """헬스체크 성공 테스트"""
        # Act
        response = await client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "services" in data

        # 서비스 상태 검증
        services = data["services"]
        assert "database" in services
        assert "redis" in services
```

### **7.3.2 데이터베이스 통합 테스트**

**테스트 파일**: `tests/integration/test_database.py`

```python
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.database import Base, get_session
from src.models import Debate, Agent, Message

class TestDatabaseIntegration:
    """데이터베이스 통합 테스트"""

    def test_database_connection(self, db_session):
        """데이터베이스 연결 테스트"""
        # Act
        result = db_session.execute(text("SELECT 1"))

        # Assert
        assert result.scalar() == 1

    def test_table_creation(self, db_session):
        """테이블 생성 확인 테스트"""
        # Act - 각 테이블에 대한 조회 시도
        tables = ['debates', 'agents', 'messages', 'debate_summaries',
                 'visualization_data', 'debate_statistics']

        for table in tables:
            # Assert - 에러 없이 조회되어야 함
            result = db_session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            assert result.scalar() >= 0

    def test_foreign_key_constraints(self, db_session):
        """외래 키 제약조건 테스트"""
        # Arrange
        debate = Debate(
            user_query="테스트를 위한 질문입니다. 외래 키 제약조건을 확인합니다.",
            status="created"
        )
        db_session.add(debate)
        db_session.commit()

        agent = Agent(
            debate_id=debate.debate_id,
            hat_type="white",
            mbti_type="ISTJ",
            role_description="테스트 에이전트",
            system_prompt={"prompt": "test"}
        )
        db_session.add(agent)
        db_session.commit()

        # Act
        message = Message(
            debate_id=debate.debate_id,
            agent_id=agent.agent_id,
            content="테스트 메시지입니다.",
            turn_number=1
        )
        db_session.add(message)
        db_session.commit()

        # Assert - 모든 관계가 올바르게 설정되었는지 확인
        assert message.debate_id == debate.debate_id
        assert message.agent_id == agent.agent_id

    def test_cascade_deletion(self, db_session):
        """계단식 삭제 테스트"""
        # Arrange - 토론, 에이전트, 메시지 생성
        debate = Debate(
            user_query="계단식 삭제 테스트용 질문입니다.",
            status="created"
        )
        db_session.add(debate)
        db_session.commit()

        agent = Agent(
            debate_id=debate.debate_id,
            hat_type="white",
            mbti_type="ISTJ",
            role_description="테스트 에이전트",
            system_prompt={"prompt": "test"}
        )
        db_session.add(agent)
        db_session.commit()

        message = Message(
            debate_id=debate.debate_id,
            agent_id=agent.agent_id,
            content="테스트 메시지",
            turn_number=1
        )
        db_session.add(message)
        db_session.commit()

        # Act - 토론 삭제
        db_session.delete(debate)
        db_session.commit()

        # Assert - 관련 에이전트와 메시지도 함께 삭제되었는지 확인
        remaining_agents = db_session.query(Agent).filter_by(
            debate_id=debate.debate_id
        ).count()
        remaining_messages = db_session.query(Message).filter_by(
            debate_id=debate.debate_id
        ).count()

        assert remaining_agents == 0
        assert remaining_messages == 0

    def test_triggers_execution(self, db_session):
        """트리거 실행 테스트"""
        # Arrange
        debate = Debate(
            user_query="트리거 테스트용 질문입니다.",
            status="created"
        )
        db_session.add(debate)
        db_session.commit()

        original_updated_at = debate.updated_at

        # Act - 토론 상태 업데이트
        debate.status = "in_progress"
        db_session.commit()

        # Assert - updated_at이 자동으로 갱신되었는지 확인
        db_session.refresh(debate)
        assert debate.updated_at > original_updated_at
```

## **7.4 프론트엔드 테스트**

### **7.4.1 컴포넌트 단위 테스트**

**테스트 파일**: `__tests__/components/HatAvatar.test.tsx`

```typescript
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { HatAvatar } from '../../src/components/HatAvatar';

describe('HatAvatar Component', () => {
  const defaultProps = {
    hatType: 'white' as const,
    mbtiType: 'ISTJ',
    isActive: false,
    size: 'md' as const,
  };

  test('renders correctly with default props', () => {
    const { getByTestId } = render(<HatAvatar {...defaultProps} />);

    const avatar = getByTestId('hat-avatar');
    expect(avatar).toBeTruthy();
  });

  test('applies correct style for each hat type', () => {
    const hatTypes = ['white', 'red', 'black', 'yellow', 'green', 'blue'] as const;

    hatTypes.forEach(hatType => {
      const { getByTestId } = render(
        <HatAvatar {...defaultProps} hatType={hatType} />
      );

      const avatar = getByTestId('hat-avatar');
      // 각 모자 타입별 스타일 적용 확인
      expect(avatar.props.style).toContainEqual(
        expect.objectContaining({
          borderColor: expect.any(String)
        })
      );
    });
  });

  test('shows active state correctly', () => {
    const { getByTestId } = render(
      <HatAvatar {...defaultProps} isActive={true} />
    );

    const avatar = getByTestId('hat-avatar');
    expect(avatar.props.style).toContainEqual(
      expect.objectContaining({
        opacity: 1,
        transform: expect.arrayContaining([
          expect.objectContaining({ scale: expect.any(Number) })
        ])
      })
    );
  });

  test('displays MBTI type correctly', () => {
    const { getByText } = render(
      <HatAvatar {...defaultProps} mbtiType="ENFP" />
    );

    expect(getByText('ENFP')).toBeTruthy();
  });

  test('handles different sizes correctly', () => {
    const sizes = ['sm', 'md', 'lg'] as const;

    sizes.forEach(size => {
      const { getByTestId } = render(
        <HatAvatar {...defaultProps} size={size} />
      );

      const avatar = getByTestId('hat-avatar');
      expect(avatar.props.style).toContainEqual(
        expect.objectContaining({
          width: expect.any(Number),
          height: expect.any(Number)
        })
      );
    });
  });

  test('shows tooltip when enabled', () => {
    const { getByText } = render(
      <HatAvatar {...defaultProps} showTooltip={true} />
    );

    // 툴팁 텍스트 확인
    expect(getByText(/객관적 정보/)).toBeTruthy();
  });
});
```

**테스트 파일**: `__tests__/components/MessageBubble.test.tsx`

```typescript
import React from 'react';
import { render } from '@testing-library/react-native';
import { MessageBubble } from '../../src/components/MessageBubble';

describe('MessageBubble Component', () => {
  const defaultProps = {
    hatType: 'white' as const,
    content: '테스트 메시지입니다.',
    timestamp: new Date('2024-01-15T10:30:00Z'),
    mbtiType: 'ISTJ',
    isStreaming: false,
  };

  test('renders message content correctly', () => {
    const { getByText } = render(<MessageBubble {...defaultProps} />);

    expect(getByText('테스트 메시지입니다.')).toBeTruthy();
  });

  test('applies correct background color for each hat type', () => {
    const hatTypes = ['white', 'red', 'black', 'yellow', 'green', 'blue'] as const;

    hatTypes.forEach(hatType => {
      const { getByTestId } = render(
        <MessageBubble {...defaultProps} hatType={hatType} />
      );

      const bubble = getByTestId('message-bubble');
      expect(bubble.props.style).toContainEqual(
        expect.objectContaining({
          backgroundColor: expect.any(String)
        })
      );
    });
  });

  test('shows streaming animation when isStreaming is true', () => {
    const { getByTestId } = render(
      <MessageBubble {...defaultProps} isStreaming={true} />
    );

    const streamingIndicator = getByTestId('streaming-indicator');
    expect(streamingIndicator).toBeTruthy();
  });

  test('displays timestamp correctly', () => {
    const { getByText } = render(<MessageBubble {...defaultProps} />);

    // 타임스탬프 형식 확인 (HH:MM)
    expect(getByText(/\d{2}:\d{2}/)).toBeTruthy();
  });

  test('shows MBTI badge', () => {
    const { getByText } = render(
      <MessageBubble {...defaultProps} mbtiType="ENFP" />
    );

    expect(getByText('ENFP')).toBeTruthy();
  });

  test('handles long content with proper wrapping', () => {
    const longContent = '매우 긴 메시지 내용입니다. '.repeat(20);

    const { getByTestId } = render(
      <MessageBubble {...defaultProps} content={longContent} />
    );

    const textElement = getByTestId('message-content');
    expect(textElement.props.children).toBe(longContent);
  });
});
```

### **7.4.2 화면 통합 테스트**

**테스트 파일**: `__tests__/screens/HomeScreen.test.tsx`

```typescript
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { NavigationContainer } from '@react-navigation/native';
import { HomeScreen } from '../../src/screens/HomeScreen';

// API 목업
jest.mock('../../src/services/api', () => ({
  createDebate: jest.fn(),
}));

import { createDebate } from '../../src/services/api';

describe('HomeScreen', () => {
  const mockNavigation = {
    navigate: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderHomeScreen = () => {
    return render(
      <NavigationContainer>
        <HomeScreen navigation={mockNavigation} />
      </NavigationContainer>
    );
  };

  test('renders all essential elements', () => {
    const { getByText, getByPlaceholderText, getByTestId } = renderHomeScreen();

    // 제목과 설명
    expect(getByText('여섯 색깔 모자와 함께 생각해보세요')).toBeTruthy();
    expect(getByText(/복잡한 문제를 다양한 관점에서/)).toBeTruthy();

    // 입력 필드
    expect(getByPlaceholderText(/어떤 문제로 고민/)).toBeTruthy();

    // 시작 버튼
    expect(getByTestId('start-debate-button')).toBeTruthy();

    // 6개 모자 미리보기
    expect(getByTestId('hat-preview-container')).toBeTruthy();
  });

  test('validates input and shows error for short query', async () => {
    const { getByPlaceholderText, getByTestId, getByText } = renderHomeScreen();

    const input = getByPlaceholderText(/어떤 문제로 고민/);
    const button = getByTestId('start-debate-button');

    // 짧은 질문 입력
    fireEvent.changeText(input, '짧음');
    fireEvent.press(button);

    await waitFor(() => {
      expect(getByText(/질문을 좀 더 자세히/)).toBeTruthy();
    });

    // API 호출되지 않아야 함
    expect(createDebate).not.toHaveBeenCalled();
  });

  test('successfully creates debate and navigates', async () => {
    const mockResponse = {
      success: true,
      debate_id: 'test-debate-id',
      status: 'created',
      participants: [
        { hat_type: 'white', mbti_type: 'ISTJ' },
        // ... 6개 참여자
      ]
    };

    (createDebate as jest.Mock).mockResolvedValueOnce({
      data: mockResponse
    });

    const { getByPlaceholderText, getByTestId } = renderHomeScreen();

    const input = getByPlaceholderText(/어떤 문제로 고민/);
    const button = getByTestId('start-debate-button');

    // 유효한 질문 입력
    fireEvent.changeText(input, '새로운 직장으로 이직을 고려하고 있습니다.');
    fireEvent.press(button);

    await waitFor(() => {
      expect(createDebate).toHaveBeenCalledWith({
        query: '새로운 직장으로 이직을 고려하고 있습니다.',
        metadata: expect.any(Object)
      });
    });

    await waitFor(() => {
      expect(mockNavigation.navigate).toHaveBeenCalledWith('Debate', {
        debateId: 'test-debate-id'
      });
    });
  });

  test('shows loading state during debate creation', async () => {
    // API 호출을 지연시켜 로딩 상태 테스트
    (createDebate as jest.Mock).mockImplementation(() =>
      new Promise(resolve => setTimeout(resolve, 1000))
    );

    const { getByPlaceholderText, getByTestId, getByText } = renderHomeScreen();

    const input = getByPlaceholderText(/어떤 문제로 고민/);
    const button = getByTestId('start-debate-button');

    fireEvent.changeText(input, '유효한 질문입니다.');
    fireEvent.press(button);

    // 로딩 상태 확인
    expect(getByText(/토론을 준비하는 중/)).toBeTruthy();
    expect(button.props.disabled).toBe(true);
  });

  test('handles API error gracefully', async () => {
    (createDebate as jest.Mock).mockRejectedValueOnce(
      new Error('네트워크 오류')
    );

    const { getByPlaceholderText, getByTestId, getByText } = renderHomeScreen();

    const input = getByPlaceholderText(/어떤 문제로 고민/);
    const button = getByTestId('start-debate-button');

    fireEvent.changeText(input, '유효한 질문입니다.');
    fireEvent.press(button);

    await waitFor(() => {
      expect(getByText(/연결에 실패했습니다/)).toBeTruthy();
    });
  });
});
```

### **7.4.3 SSE 클라이언트 테스트**

**테스트 파일**: `__tests__/services/SSEClient.test.ts`

```typescript
import { SSEClient } from '../../src/services/SSEClient';

// EventSource 목업
global.EventSource = jest.fn(() => ({
  addEventListener: jest.fn(),
  close: jest.fn(),
})) as any;

describe('SSEClient', () => {
  let sseClient: SSEClient;
  let mockEventSource: any;

  beforeEach(() => {
    mockEventSource = {
      addEventListener: jest.fn(),
      close: jest.fn(),
      readyState: EventSource.CONNECTING,
    };

    (global.EventSource as jest.Mock).mockReturnValue(mockEventSource);

    sseClient = new SSEClient();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('connects to debate stream successfully', () => {
    const debateId = 'test-debate-id';
    const callbacks = {
      onMessage: jest.fn(),
      onStatus: jest.fn(),
      onError: jest.fn(),
      onComplete: jest.fn(),
    };

    sseClient.connect(debateId, callbacks);

    expect(global.EventSource).toHaveBeenCalledWith(
      `http://localhost:8000/debate/${debateId}/stream`
    );

    // 이벤트 리스너가 등록되었는지 확인
    expect(mockEventSource.addEventListener).toHaveBeenCalledWith('message', expect.any(Function));
    expect(mockEventSource.addEventListener).toHaveBeenCalledWith('status', expect.any(Function));
    expect(mockEventSource.addEventListener).toHaveBeenCalledWith('error', expect.any(Function));
    expect(mockEventSource.addEventListener).toHaveBeenCalledWith('complete', expect.any(Function));
  });

  test('handles message events correctly', () => {
    const callbacks = {
      onMessage: jest.fn(),
      onStatus: jest.fn(),
      onError: jest.fn(),
      onComplete: jest.fn(),
    };

    sseClient.connect('test-id', callbacks);

    // 메시지 이벤트 시뮬레이션
    const messageData = {
      message_id: 'msg-001',
      hat_type: 'white',
      content: '테스트 메시지입니다.',
      timestamp: '2024-01-15T10:30:00Z',
      turn_number: 1
    };

    const mockEvent = {
      data: JSON.stringify(messageData)
    };

    // addEventListener의 두 번째 인자(콜백 함수) 호출
    const messageCallback = mockEventSource.addEventListener.mock.calls
      .find(call => call[0] === 'message')[1];

    messageCallback(mockEvent);

    expect(callbacks.onMessage).toHaveBeenCalledWith(messageData);
  });

  test('handles connection errors', () => {
    const callbacks = {
      onMessage: jest.fn(),
      onStatus: jest.fn(),
      onError: jest.fn(),
      onComplete: jest.fn(),
    };

    sseClient.connect('test-id', callbacks);

    // 에러 이벤트 시뮬레이션
    const errorData = {
      code: 'CONNECTION_ERROR',
      message: '연결에 실패했습니다.',
      recoverable: true
    };

    const mockEvent = {
      data: JSON.stringify(errorData)
    };

    const errorCallback = mockEventSource.addEventListener.mock.calls
      .find(call => call[0] === 'error')[1];

    errorCallback(mockEvent);

    expect(callbacks.onError).toHaveBeenCalledWith(errorData);
  });

  test('disconnects properly', () => {
    sseClient.connect('test-id', {
      onMessage: jest.fn(),
      onStatus: jest.fn(),
      onError: jest.fn(),
      onComplete: jest.fn(),
    });

    sseClient.disconnect();

    expect(mockEventSource.close).toHaveBeenCalled();
  });

  test('handles automatic reconnection', async () => {
    const callbacks = {
      onMessage: jest.fn(),
      onStatus: jest.fn(),
      onError: jest.fn(),
      onComplete: jest.fn(),
    };

    sseClient.connect('test-id', callbacks);

    // 연결 끊김 시뮬레이션
    mockEventSource.readyState = EventSource.CLOSED;

    // onerror 이벤트 트리거
    if (mockEventSource.onerror) {
      mockEventSource.onerror(new Event('error'));
    }

    // 재연결 시도 확인 (setTimeout으로 인한 지연 고려)
    await new Promise(resolve => setTimeout(resolve, 1100));

    expect(global.EventSource).toHaveBeenCalledTimes(2);
  });
});
```

## **7.5 E2E 테스트**

### **7.5.1 전체 사용자 플로우 테스트**

**테스트 파일**: `e2e/fullUserFlow.e2e.js`

```javascript
import { device, element, by, expect } from 'detox';

describe('Full User Flow E2E Test', () => {
  beforeAll(async () => {
    await device.launchApp();
  });

  beforeEach(async () => {
    await device.reloadReactNative();
  });

  test('should complete full debate flow successfully', async () => {
    // 1. 홈 화면에서 질문 입력
    await expect(element(by.text('여섯 색깔 모자와 함께 생각해보세요'))).toBeVisible();

    const queryInput = element(by.id('question-input'));
    await queryInput.typeText('새로운 직장으로 이직을 해야 할지 고민입니다.');

    // 2. 토론 시작
    const startButton = element(by.id('start-debate-button'));
    await startButton.tap();

    // 3. 토론 화면으로 이동 확인
    await expect(element(by.id('debate-screen'))).toBeVisible();

    // 4. 6개 아바타 표시 확인
    await expect(element(by.id('participant-bar'))).toBeVisible();

    const hatTypes = ['white', 'red', 'black', 'yellow', 'green', 'blue'];
    for (const hatType of hatTypes) {
      await expect(element(by.id(`avatar-${hatType}`))).toBeVisible();
    }

    // 5. 실시간 메시지 수신 확인
    await waitFor(element(by.id('message-list')))
      .toHaveAtLeast(3)
      .withTimeout(30000);

    // 6. 토론 종료
    const endButton = element(by.id('end-debate-button'));
    await endButton.tap();

    // 확인 다이얼로그
    const confirmButton = element(by.text('종료'));
    await confirmButton.tap();

    // 7. 결과 화면으로 이동
    await waitFor(element(by.id('result-screen')))
      .toBeVisible()
      .withTimeout(60000);

    // 8. 요약 탭 확인
    await expect(element(by.id('summary-tab'))).toBeVisible();
    await expect(element(by.id('summary-content'))).toBeVisible();

    // 9. 시각화 탭 전환
    const visualizationTab = element(by.id('visualization-tab'));
    await visualizationTab.tap();

    await expect(element(by.id('visualization-webview'))).toBeVisible();

    // 10. 공유 기능 테스트
    const shareButton = element(by.id('share-button'));
    await shareButton.tap();

    // 공유 시트가 나타나는지 확인 (플랫폼별로 다를 수 있음)
    await expect(element(by.text('공유'))).toBeVisible();
  });

  test('should handle network errors gracefully', async () => {
    // 네트워크 오프라인 시뮬레이션
    await device.setURLBlacklist(['*']);

    const queryInput = element(by.id('question-input'));
    await queryInput.typeText('네트워크 에러 테스트');

    const startButton = element(by.id('start-debate-button'));
    await startButton.tap();

    // 에러 메시지 확인
    await expect(element(by.text('연결에 실패했습니다'))).toBeVisible();

    // 네트워크 복구
    await device.setURLBlacklist([]);

    // 재시도 버튼
    const retryButton = element(by.id('retry-button'));
    await retryButton.tap();

    // 성공적인 연결 확인
    await expect(element(by.id('debate-screen'))).toBeVisible();
  });

  test('should validate input correctly', async () => {
    // 너무 짧은 질문
    const queryInput = element(by.id('question-input'));
    await queryInput.typeText('짧음');

    const startButton = element(by.id('start-debate-button'));
    await startButton.tap();

    await expect(element(by.text('질문을 좀 더 자세히 입력해주세요'))).toBeVisible();

    // 유효한 질문으로 수정
    await queryInput.clearText();
    await queryInput.typeText('이제 충분히 긴 질문입니다. 다양한 관점에서 분석해 주세요.');

    await startButton.tap();

    // 성공적인 진행 확인
    await expect(element(by.id('debate-screen'))).toBeVisible();
  });
});
```

## **7.6 테스트 실행 및 자동화**

### **7.6.1 테스트 스크립트 (package.json)**

```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:unit": "jest --testPathPattern=__tests__/unit",
    "test:integration": "jest --testPathPattern=__tests__/integration",
    "test:e2e": "detox test",
    "test:backend": "pytest tests/ -v --cov=src",
    "test:backend:unit": "pytest tests/unit/ -v",
    "test:backend:integration": "pytest tests/integration/ -v",
    "test:all": "npm run test:backend && npm run test && npm run test:e2e"
  }
}
```

### **7.6.2 CI/CD 파이프라인 (GitHub Actions)**

**.github/workflows/test.yml**

```yaml
name: Test Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: sixsortinghat_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt

    - name: Run backend unit tests
      run: pytest tests/unit/ -v --cov=src --cov-report=xml

    - name: Run backend integration tests
      run: pytest tests/integration/ -v
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/sixsortinghat_test
        REDIS_URL: redis://localhost:6379

    - name: Upload coverage reports
      uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'

    - name: Install dependencies
      run: npm ci

    - name: Run frontend unit tests
      run: npm run test:unit -- --coverage --watchAll=false

    - name: Run frontend integration tests
      run: npm run test:integration -- --watchAll=false

  e2e-tests:
    runs-on: macos-latest
    needs: [backend-tests, frontend-tests]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'

    - name: Install dependencies
      run: npm ci

    - name: Set up iOS Simulator
      run: |
        xcrun simctl create "iPhone 14" "iPhone 14" iOS16.0
        xcrun simctl boot "iPhone 14"

    - name: Build iOS app
      run: npm run build:ios

    - name: Run E2E tests
      run: npm run test:e2e
```

### **7.6.3 테스트 커버리지 목표**

**백엔드 커버리지 목표**
- **전체 코드 커버리지**: 85% 이상
- **단위 테스트**: 90% 이상
- **통합 테스트**: 80% 이상
- **중요 비즈니스 로직**: 95% 이상

**프론트엔드 커버리지 목표**
- **컴포넌트 테스트**: 80% 이상
- **유틸리티 함수**: 90% 이상
- **서비스 레이어**: 85% 이상
- **화면 통합 테스트**: 75% 이상

**E2E 테스트 커버리지**
- **핵심 사용자 시나리오**: 100%
- **에러 처리 시나리오**: 80% 이상
- **크로스 플랫폼 호환성**: Android/iOS 모두

이 종합적인 테스트 전략을 통해 SixSortingHat 애플리케이션의 품질과 안정성을 보장할 수 있습니다.