"""
Triage Agent - Routes player inputs to appropriate specialized agents
"""

import re
from typing import Dict, Any, Optional
from .base_agent import BaseAgent, AgentMessage, AgentResponse

class TriageAgent(BaseAgent):
    """Agent responsible for routing player inputs to appropriate specialized agents"""

    def __init__(self):
        system_prompt = """You are the Triage Agent for GameMasterJJ, an AI-powered TRPG Game Master system.

Your primary responsibility is to analyze player inputs and determine which specialized agent should handle the request:

1. NARRATOR_AGENT: Story progression, scene descriptions, environmental details
2. RULES_KEEPER_AGENT: Dice rolls, combat mechanics, skill checks, rule clarifications
3. NPC_INTERACTION_AGENT: Conversations with NPCs, social encounters, dialogue
4. LORE_KEEPER_AGENT: World lore, history, background information, setting details

CLASSIFICATION RULES:
- Combat actions, dice rolls, stat checks → RULES_KEEPER_AGENT
- Talking to NPCs, social interactions → NPC_INTERACTION_AGENT
- Asking about world/lore/history → LORE_KEEPER_AGENT
- Story progression, scene description → NARRATOR_AGENT
- Ambiguous inputs → Ask for clarification or default to NARRATOR_AGENT

Respond with:
1. The target agent name
2. A brief explanation of why
3. Any context that should be passed along

Be decisive and efficient in your routing decisions."""

        super().__init__("triage", system_prompt)

    async def process_message(self, message: AgentMessage, context: Dict[str, Any]) -> AgentResponse:
        """Process message and determine routing"""

        # Prepare messages for OpenAI
        messages = [
            self.get_system_message(),
            {
                "role": "user",
                "content": f"""PLAYER INPUT: {message.content}

GAME CONTEXT:
{self.format_context_for_prompt(context)}

CONVERSATION HISTORY:
{self._format_recent_history()}

Analyze this input and determine the best agent to handle it. Respond in this format:
TARGET_AGENT: [agent_name]
REASON: [brief explanation]
PRIORITY: [high/medium/low]
CONTEXT_NOTES: [any important context to pass along]"""
            }
        ]

        try:
            response = await self._call_openai(messages)

            # Parse the response to extract routing decision
            routing_decision = self._parse_routing_response(response["content"])

            return AgentResponse(
                content=f"Routing to {routing_decision['target_agent']}: {routing_decision['reason']}",
                agent_type="triage",
                confidence=routing_decision['confidence'],
                needs_handoff=True,
                handoff_target=routing_decision['target_agent'],
                metadata={
                    "routing_reason": routing_decision['reason'],
                    "priority": routing_decision.get('priority', 'medium'),
                    "context_notes": routing_decision.get('context_notes', '')
                }
            )

        except Exception as e:
            # Fallback routing logic
            fallback_target = self._fallback_routing(message.content)
            return AgentResponse(
                content=f"Routing to {fallback_target} (fallback due to error: {str(e)})",
                agent_type="triage",
                confidence=0.5,
                needs_handoff=True,
                handoff_target=fallback_target,
                metadata={"fallback": True, "error": str(e)}
            )

    def _parse_routing_response(self, response_content: str) -> Dict[str, Any]:
        """Parse the structured response from OpenAI"""
        lines = response_content.strip().split('\n')
        result = {
            "target_agent": "narrator",  # default
            "reason": "Default routing",
            "confidence": 0.7,
            "priority": "medium"
        }

        for line in lines:
            if line.startswith("TARGET_AGENT:"):
                agent_name = line.split(":", 1)[1].strip().lower()
                # Map to actual agent names
                if "rules" in agent_name or "keeper" in agent_name:
                    result["target_agent"] = "rules_keeper"
                elif "npc" in agent_name or "interaction" in agent_name:
                    result["target_agent"] = "npc_interaction"
                elif "lore" in agent_name or "keeper" in agent_name:
                    result["target_agent"] = "lore_keeper"
                elif "narrator" in agent_name:
                    result["target_agent"] = "narrator"

            elif line.startswith("REASON:"):
                result["reason"] = line.split(":", 1)[1].strip()

            elif line.startswith("PRIORITY:"):
                result["priority"] = line.split(":", 1)[1].strip().lower()

            elif line.startswith("CONTEXT_NOTES:"):
                result["context_notes"] = line.split(":", 1)[1].strip()

        # Determine confidence based on keywords and clarity
        result["confidence"] = self._calculate_confidence(result["target_agent"], result["reason"])

        return result

    def _calculate_confidence(self, target_agent: str, reason: str) -> float:
        """Calculate confidence score based on routing decision"""
        # High confidence keywords for each agent type
        confidence_keywords = {
            "rules_keeper": ["roll", "dice", "attack", "damage", "skill check", "combat", "stats"],
            "npc_interaction": ["talk", "speak", "ask", "npc", "character", "conversation", "dialogue"],
            "lore_keeper": ["history", "lore", "world", "background", "tell me about", "what is"],
            "narrator": ["look", "examine", "go to", "move", "scene", "description", "environment"]
        }

        reason_lower = reason.lower()
        target_keywords = confidence_keywords.get(target_agent, [])

        keyword_matches = sum(1 for keyword in target_keywords if keyword in reason_lower)

        if keyword_matches >= 2:
            return 0.9
        elif keyword_matches == 1:
            return 0.8
        else:
            return 0.6

    def _fallback_routing(self, message_content: str) -> str:
        """Simple keyword-based fallback routing"""
        content_lower = message_content.lower()

        # Rules-based keywords
        if any(keyword in content_lower for keyword in ["roll", "dice", "attack", "damage", "check", "combat"]):
            return "rules_keeper"

        # NPC interaction keywords
        if any(keyword in content_lower for keyword in ["talk", "speak", "ask", "say", "tell"]):
            return "npc_interaction"

        # Lore keeper keywords
        if any(keyword in content_lower for keyword in ["history", "lore", "world", "background", "what is", "tell me about"]):
            return "lore_keeper"

        # Default to narrator
        return "narrator"

    def _format_recent_history(self) -> str:
        """Format recent conversation history for context"""
        if not self.conversation_history:
            return "No recent conversation history."

        recent = self.conversation_history[-3:]  # Last 3 messages
        formatted = []

        for msg in recent:
            formatted.append(f"{msg.sender}: {msg.content[:100]}...")

        return "\n".join(formatted)