"""
Narrator Agent - Handles story progression and scene descriptions
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentMessage, AgentResponse

class NarratorAgent(BaseAgent):
    """Agent responsible for story progression, scene descriptions, and environmental details"""

    def __init__(self):
        system_prompt = """You are the Narrator Agent for GameMasterJJ, an AI-powered TRPG Game Master system.

Your responsibilities include:
1. Scene descriptions and environmental details
2. Story progression and narrative flow
3. Setting atmosphere and mood
4. Describing consequences of player actions
5. Providing immersive narrative elements

STORYTELLING STYLE:
- Use vivid, immersive descriptions
- Maintain appropriate tone for the fantasy setting
- Leave room for player agency and choice
- Build suspense and engagement
- Keep descriptions concise but evocative (2-4 sentences)

GUIDELINES:
- Always describe sensory details (sight, sound, smell, feel)
- Create opportunities for player interaction
- Maintain consistency with established world and story
- Use active voice and present tense
- End with clear options or prompts for player action

HANDOFF CONDITIONS:
- If combat is about to start → Hand off to RULES_KEEPER_AGENT
- If NPCs need to speak/interact → Hand off to NPC_INTERACTION_AGENT
- If players ask about lore/history → Hand off to LORE_KEEPER_AGENT

Remember: You are the voice of the world itself, bringing the story to life through rich, engaging narration."""

        super().__init__("narrator", system_prompt)

    async def process_message(self, message: AgentMessage, context: Dict[str, Any]) -> AgentResponse:
        """Process message and generate narrative response"""

        # Check if we should hand off to another agent
        should_handoff, handoff_target = self.should_handoff(message.content, context)
        if should_handoff:
            return AgentResponse(
                content=f"This requires {handoff_target} expertise - handing off.",
                agent_type="narrator",
                needs_handoff=True,
                handoff_target=handoff_target,
                confidence=0.9
            )

        # Prepare context-rich prompt
        messages = [
            self.get_system_message(),
            {
                "role": "user",
                "content": f"""PLAYER ACTION: {message.content}

CURRENT CONTEXT:
{self.format_context_for_prompt(context)}

RECENT CONVERSATION:
{self._format_recent_history()}

As the Narrator, describe what happens as a result of this player action. Provide:
1. Immediate consequences or results
2. Vivid scene description
3. Sensory details to enhance immersion
4. Clear options or prompts for the player's next action

Keep the response engaging, immersive, and appropriate for a fantasy TRPG setting."""
            }
        ]

        try:
            response = await self._call_openai(messages)

            # Enhance response with narrative tools if needed
            enhanced_content = self._enhance_narrative(response["content"], context)

            return AgentResponse(
                content=enhanced_content,
                agent_type="narrator",
                confidence=0.9,
                metadata={
                    "scene_elements": self._extract_scene_elements(enhanced_content),
                    "token_usage": response.get("usage", {})
                }
            )

        except Exception as e:
            return AgentResponse(
                content=f"The mists swirl around you, obscuring your vision momentarily. (Narrator temporarily unavailable: {str(e)})",
                agent_type="narrator",
                confidence=0.3,
                metadata={"error": str(e)}
            )

    def should_handoff(self, message_content: str, context: Dict[str, Any]) -> tuple[bool, str]:
        """Determine if message should be handed off to another agent"""
        content_lower = message_content.lower()

        # Combat/rules-related handoffs
        combat_keywords = ["attack", "roll", "dice", "damage", "initiative", "spell", "cast", "hit points"]
        if any(keyword in content_lower for keyword in combat_keywords):
            return True, "rules_keeper"

        # NPC interaction handoffs
        npc_keywords = ["talk to", "speak with", "ask", "say to", "tell", "convince", "persuade"]
        if any(keyword in content_lower for keyword in npc_keywords):
            return True, "npc_interaction"

        # Lore/world building handoffs
        lore_keywords = ["history", "tell me about", "what is", "who is", "background", "lore"]
        if any(keyword in content_lower for keyword in lore_keywords):
            return True, "lore_keeper"

        return False, None

    def _enhance_narrative(self, content: str, context: Dict[str, Any]) -> str:
        """Enhance narrative content with contextual elements"""
        # Add atmospheric elements based on location
        if context.get("game_state", {}).get("current_location"):
            location = context["game_state"]["current_location"]
            if "dungeon" in location.lower():
                content = self._add_dungeon_atmosphere(content)
            elif "forest" in location.lower():
                content = self._add_forest_atmosphere(content)

        return content

    def _add_dungeon_atmosphere(self, content: str) -> str:
        """Add dungeon-specific atmospheric details"""
        atmosphere_elements = [
            "The torch light flickers against damp stone walls.",
            "Your footsteps echo in the narrow corridors.",
            "A cool draft carries unknown scents from deeper within."
        ]

        # Randomly add atmospheric element if content is short
        if len(content) < 200:
            import random
            content += f" {random.choice(atmosphere_elements)}"

        return content

    def _add_forest_atmosphere(self, content: str) -> str:
        """Add forest-specific atmospheric details"""
        atmosphere_elements = [
            "Sunlight filters through the canopy above.",
            "Leaves rustle softly in the gentle breeze.",
            "Bird songs echo from the trees around you."
        ]

        if len(content) < 200:
            import random
            content += f" {random.choice(atmosphere_elements)}"

        return content

    def _extract_scene_elements(self, content: str) -> List[str]:
        """Extract key scene elements for tracking"""
        # Simple keyword extraction for scene tracking
        elements = []
        content_lower = content.lower()

        # Location indicators
        if "door" in content_lower or "entrance" in content_lower:
            elements.append("transition_point")
        if "treasure" in content_lower or "loot" in content_lower:
            elements.append("treasure")
        if "monster" in content_lower or "creature" in content_lower:
            elements.append("potential_combat")
        if "trap" in content_lower:
            elements.append("hazard")

        return elements

    def _format_recent_history(self) -> str:
        """Format recent conversation for context"""
        if not self.conversation_history:
            return "Beginning of adventure."

        # Get last few messages for context
        recent = self.conversation_history[-3:]
        formatted = []

        for msg in recent:
            if msg.sender != "narrator":  # Don't include own messages
                formatted.append(f"Player: {msg.content[:100]}...")

        return "\n".join(formatted) if formatted else "Beginning of adventure."