"""
NPC Interaction Agent - Handles conversations and social encounters with NPCs
"""

from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent, AgentMessage, AgentResponse

class NPCInteractionAgent(BaseAgent):
    """Agent responsible for NPC conversations and social encounters"""

    def __init__(self):
        system_prompt = """You are the NPC Interaction Agent for GameMasterJJ, an AI-powered TRPG Game Master system.

Your responsibilities include:
1. Voicing NPCs in conversations with players
2. Handling social encounters and dialogue trees
3. Managing NPC personalities, motivations, and knowledge
4. Processing social skill attempts (persuasion, deception, intimidation)
5. Tracking relationship changes and reputation

NPC VOICE GUIDELINES:
- Give each NPC a distinct personality and speaking style
- Stay consistent with established NPC characteristics
- Consider NPC knowledge limitations and biases
- React appropriately to player actions and reputation
- Use appropriate social context and cultural background

SOCIAL MECHANICS:
- Track NPC attitudes: Hostile, Unfriendly, Indifferent, Friendly, Helpful
- Consider character charisma and social skills
- Apply appropriate DCs for social skill checks
- Factor in previous interactions and reputation

DIALOGUE STRUCTURE:
- Always indicate which NPC is speaking
- Provide clear dialogue in quotes
- Include body language and emotional cues
- Offer meaningful conversation choices
- Advance plot or provide useful information when appropriate

HANDOFF CONDITIONS:
- If combat starts → Hand off to RULES_KEEPER_AGENT
- If lore/background questions arise → Hand off to LORE_KEEPER_AGENT
- If scene changes significantly → Hand off to NARRATOR_AGENT

Remember: You are the voice of every character the players meet, bringing them to life with personality and purpose."""

        super().__init__("npc_interaction", system_prompt)

        # NPC attitude tracking
        self.npc_attitudes = {}

    async def process_message(self, message: AgentMessage, context: Dict[str, Any]) -> AgentResponse:
        """Process NPC interaction message"""

        # Check if we should hand off to another agent
        should_handoff, handoff_target = self.should_handoff(message.content, context)
        if should_handoff:
            return AgentResponse(
                content=f"This requires {handoff_target} expertise - handing off.",
                agent_type="npc_interaction",
                needs_handoff=True,
                handoff_target=handoff_target,
                confidence=0.9
            )

        # Identify active NPCs in the scene
        active_npcs = self._identify_active_npcs(context)

        # Prepare NPC response
        messages = [
            self.get_system_message(),
            {
                "role": "user",
                "content": f"""PLAYER ACTION/DIALOGUE: {message.content}

CURRENT CONTEXT:
{self.format_context_for_prompt(context)}

ACTIVE NPCs:
{self._format_npc_context(active_npcs)}

RELATIONSHIP STATUS:
{self._format_relationship_status(context)}

RECENT CONVERSATION:
{self._format_recent_history()}

As the NPC Interaction Agent, respond as the appropriate NPC(s). Include:
1. NPC dialogue in quotes with clear speaker identification
2. Body language and emotional cues in descriptions
3. Appropriate reactions based on NPC personality and player action
4. Any social skill checks that might be triggered
5. Impact on NPC relationships or attitudes

Format:
**[NPC Name]**: "Dialogue here" *[body language/emotional cues]*"""
            }
        ]

        try:
            response = await self._call_openai(messages)

            # Process the response for social mechanics
            processed_response = self._process_social_mechanics(response["content"], message, context)

            return AgentResponse(
                content=processed_response["content"],
                agent_type="npc_interaction",
                confidence=0.9,
                metadata={
                    "active_npcs": active_npcs,
                    "attitude_changes": processed_response.get("attitude_changes", []),
                    "social_checks": processed_response.get("social_checks", []),
                    "token_usage": response.get("usage", {})
                }
            )

        except Exception as e:
            # Fallback NPC response
            fallback_npc_name = active_npcs[0] if active_npcs else "Unknown NPC"
            fallback_response = f"**{fallback_npc_name}**: \"I... I'm not sure how to respond to that.\" *looks confused*"

            return AgentResponse(
                content=fallback_response,
                agent_type="npc_interaction",
                confidence=0.4,
                metadata={
                    "error": str(e),
                    "fallback": True,
                    "active_npcs": active_npcs
                }
            )

    def should_handoff(self, message_content: str, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Determine if message should be handed off to another agent"""
        content_lower = message_content.lower()

        # Combat handoffs
        combat_keywords = ["attack", "fight", "combat", "initiative", "weapon", "cast spell"]
        if any(keyword in content_lower for keyword in combat_keywords):
            return True, "rules_keeper"

        # Lore handoffs
        lore_keywords = ["tell me about the history", "what happened long ago", "ancient", "legend"]
        if any(keyword in content_lower for keyword in lore_keywords):
            return True, "lore_keeper"

        # Scene change handoffs
        scene_keywords = ["leave", "go to", "exit", "move to", "walk away"]
        if any(keyword in content_lower for keyword in scene_keywords):
            return True, "narrator"

        return False, None

    def _identify_active_npcs(self, context: Dict[str, Any]) -> List[str]:
        """Identify NPCs currently in the scene"""
        # Extract NPCs from game state or storylet context
        active_npcs = []

        game_state = context.get("game_state", {})
        if "active_npcs" in game_state:
            active_npcs.extend(game_state["active_npcs"])

        # Check storylet context for NPCs
        storylets = context.get("active_storylets", [])
        for storylet in storylets:
            if "npcs" in storylet:
                active_npcs.extend(storylet["npcs"])

        # Default NPCs if none specified
        if not active_npcs:
            location = game_state.get("current_location", "unknown")
            if "tavern" in location.lower():
                active_npcs = ["Bartender"]
            elif "shop" in location.lower():
                active_npcs = ["Shopkeeper"]
            elif "guard" in location.lower():
                active_npcs = ["Guard"]
            else:
                active_npcs = ["Local Resident"]

        return active_npcs

    def _format_npc_context(self, active_npcs: List[str]) -> str:
        """Format NPC information for context"""
        if not active_npcs:
            return "No specific NPCs identified in the current scene."

        npc_info = []
        for npc in active_npcs:
            # In full implementation, this would pull from NPC database
            attitude = self.npc_attitudes.get(npc, "Indifferent")
            npc_info.append(f"- {npc} (Attitude: {attitude})")

        return "\n".join(npc_info)

    def _format_relationship_status(self, context: Dict[str, Any]) -> str:
        """Format current relationship status with NPCs"""
        character = context.get("character", {})
        character_name = character.get("name", "Unknown")

        if not self.npc_attitudes:
            return f"No established relationships for {character_name}."

        relationship_summary = []
        for npc, attitude in self.npc_attitudes.items():
            relationship_summary.append(f"- {npc}: {attitude}")

        return "\n".join(relationship_summary)

    def _process_social_mechanics(self, ai_response: str, message: AgentMessage, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process social mechanics and attitude changes"""
        result = {
            "content": ai_response,
            "attitude_changes": [],
            "social_checks": []
        }

        content_lower = message.content.lower()

        # Detect social skill attempts
        if any(skill in content_lower for skill in ["persuade", "convince", "charm"]):
            result["social_checks"].append({
                "skill": "Persuasion",
                "dc": self._determine_social_dc(content_lower),
                "target": "attitude_improvement"
            })

        elif any(skill in content_lower for skill in ["intimidate", "threaten", "menace"]):
            result["social_checks"].append({
                "skill": "Intimidation",
                "dc": self._determine_social_dc(content_lower),
                "target": "compliance_through_fear"
            })

        elif any(skill in content_lower for skill in ["deceive", "lie", "mislead"]):
            result["social_checks"].append({
                "skill": "Deception",
                "dc": self._determine_social_dc(content_lower),
                "target": "belief_in_falsehood"
            })

        # Simple attitude tracking (in full implementation, this would be more sophisticated)
        if result["social_checks"]:
            result["content"] += f"\n\n*This interaction may affect NPC relationships. Social skill check required.*"

        return result

    def _determine_social_dc(self, content: str) -> int:
        """Determine DC for social interaction based on content complexity"""
        # Simple heuristics - in full implementation, this would consider:
        # - NPC personality and current attitude
        # - Reasonableness of the request
        # - Character reputation and history
        # - Situational modifiers

        if any(word in content for word in ["reasonable", "simple", "easy"]):
            return 12
        elif any(word in content for word in ["difficult", "unlikely", "against their interests"]):
            return 18
        else:
            return 15  # Medium difficulty

    def _format_recent_history(self) -> str:
        """Format recent conversation history"""
        if not self.conversation_history:
            return "First interaction with these NPCs."

        recent = self.conversation_history[-3:]
        formatted = []

        for msg in recent:
            if msg.sender != "npc_interaction":
                formatted.append(f"Player: {msg.content[:100]}...")
            else:
                formatted.append(f"NPC Response: {msg.content[:100]}...")

        return "\n".join(formatted) if formatted else "First interaction with these NPCs."