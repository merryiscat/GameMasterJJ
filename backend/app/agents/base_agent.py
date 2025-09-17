"""
Base agent class for all GameMasterJJ agents
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.core.config import settings

class AgentMessage(BaseModel):
    """Message structure for agent communication"""
    content: str
    sender: str
    message_type: str = "text"
    metadata: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    """Response structure from agents"""
    content: str
    agent_type: str
    confidence: float = 1.0
    needs_handoff: bool = False
    handoff_target: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tools_used: Optional[List[str]] = None

class BaseAgent(ABC):
    """Base class for all AI agents"""

    def __init__(self, agent_type: str, system_prompt: str):
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        self.model = settings.OPENAI_MODEL
        self.conversation_history: List[AgentMessage] = []
        self.tools: List[Dict[str, Any]] = []

    @abstractmethod
    async def process_message(self, message: AgentMessage, context: Dict[str, Any]) -> AgentResponse:
        """Process incoming message and return response"""
        pass

    async def _call_openai(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Make API call to OpenAI"""
        try:
            from openai import AsyncOpenAI

            # Create async client
            async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }

            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = await async_client.chat.completions.create(**kwargs)
            return {
                "content": response.choices[0].message.content,
                "tool_calls": getattr(response.choices[0].message, 'tool_calls', None),
                "usage": response.usage.model_dump() if response.usage else {}
            }
        except Exception as e:
            # Return a fallback response for development/testing
            if "API key" in str(e) or "authentication" in str(e).lower():
                return {
                    "content": f"[{self.agent_type.upper()} AGENT - API KEY NOT CONFIGURED] This would be the AI response to your input. Please configure your OpenAI API key to see real responses.",
                    "tool_calls": None,
                    "usage": {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
                }
            else:
                raise Exception(f"OpenAI API call failed for {self.agent_type}: {str(e)}")

    def add_to_history(self, message: AgentMessage):
        """Add message to conversation history"""
        self.conversation_history.append(message)

        # Keep only last 20 messages to manage token usage
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    def get_system_message(self) -> Dict[str, str]:
        """Get system message for OpenAI API"""
        return {"role": "system", "content": self.system_prompt}

    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """Format context information for inclusion in prompts"""
        formatted_context = []

        if context.get("character"):
            char = context["character"]
            formatted_context.append(f"CHARACTER: {char.get('name', 'Unknown')} (Level {char.get('level', 1)} {char.get('character_class', 'Unknown')})")

        if context.get("game_state"):
            game_state = context["game_state"]
            if game_state.get("current_location"):
                formatted_context.append(f"LOCATION: {game_state['current_location']}")

        if context.get("active_storylets"):
            storylets = context["active_storylets"]
            if storylets:
                formatted_context.append(f"AVAILABLE STORYLETS: {len(storylets)} available")

        return "\n".join(formatted_context) if formatted_context else "No additional context available."

    def should_handoff(self, message_content: str, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Determine if this message should be handed off to another agent"""
        # Base implementation - subclasses should override
        return False, None