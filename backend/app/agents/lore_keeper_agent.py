"""
Lore Keeper Agent - Handles world lore, history, and background information
"""

from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent, AgentMessage, AgentResponse

class LoreKeeperAgent(BaseAgent):
    """Agent responsible for world lore, history, and background information"""

    def __init__(self):
        system_prompt = """You are the Lore Keeper Agent for GameMasterJJ, an AI-powered TRPG Game Master system.

Your responsibilities include:
1. Providing world lore and historical information
2. Explaining cultural background and traditions
3. Describing political situations and conflicts
4. Maintaining world consistency and continuity
5. Answering "what is" and "tell me about" questions

LORE PRINCIPLES:
- Maintain internal consistency within the game world
- Build upon established lore rather than contradicting it
- Provide rich, detailed background that enhances immersion
- Adapt information to the character's knowledge level
- Leave mysteries and unknowns for future exploration

INFORMATION DELIVERY:
- Tailor knowledge to character background and intelligence
- Consider what the character would realistically know
- Present information in an engaging, story-like manner
- Include relevant cultural context and implications
- Suggest connections to current adventures when appropriate

KNOWLEDGE LEVELS:
- Common Knowledge: Basic facts most people would know
- Specialized Knowledge: Information requiring education or experience
- Secret Knowledge: Rare or hidden information
- Lost Knowledge: Ancient or forgotten lore

HANDOFF CONDITIONS:
- If specific NPCs need to deliver information → Hand off to NPC_INTERACTION_AGENT
- If immediate scene action is needed → Hand off to NARRATOR_AGENT
- If rule mechanics are involved → Hand off to RULES_KEEPER_AGENT

Remember: You are the keeper of the world's memory, ensuring rich background and consistent lore."""

        super().__init__("lore_keeper", system_prompt)

        # Initialize base world lore structure
        self.lore_categories = {
            "history": {},
            "geography": {},
            "cultures": {},
            "religions": {},
            "politics": {},
            "organizations": {},
            "legends": {},
            "magic": {}
        }

    async def process_message(self, message: AgentMessage, context: Dict[str, Any]) -> AgentResponse:
        """Process lore-related queries"""

        # Check if we should hand off to another agent
        should_handoff, handoff_target = self.should_handoff(message.content, context)
        if should_handoff:
            return AgentResponse(
                content=f"For that information, you'd need to speak with someone directly - handing off to {handoff_target}.",
                agent_type="lore_keeper",
                needs_handoff=True,
                handoff_target=handoff_target,
                confidence=0.9
            )

        # Analyze the lore request
        lore_request = self._analyze_lore_request(message.content)

        # Prepare context-rich prompt for lore generation
        messages = [
            self.get_system_message(),
            {
                "role": "user",
                "content": f"""LORE REQUEST: {message.content}

REQUEST ANALYSIS:
- Category: {lore_request['category']}
- Topic: {lore_request['topic']}
- Knowledge Level: {lore_request['knowledge_level']}
- Scope: {lore_request['scope']}

CHARACTER CONTEXT:
{self._format_character_knowledge_context(context)}

WORLD CONTEXT:
{self.format_context_for_prompt(context)}

ESTABLISHED LORE:
{self._format_established_lore(lore_request['category'])}

Provide detailed, engaging lore information that:
1. Answers the specific question or request
2. Maintains world consistency
3. Matches the character's knowledge level
4. Includes cultural context and implications
5. Suggests connections to current adventures
6. Maintains appropriate mystery where needed

Structure your response with clear sections and engaging narrative style."""
            }
        ]

        try:
            response = await self._call_openai(messages)

            # Process and enrich the lore response
            enriched_response = self._enrich_lore_response(
                response["content"],
                lore_request,
                context
            )

            # Update established lore cache
            self._update_lore_cache(lore_request, enriched_response)

            return AgentResponse(
                content=enriched_response,
                agent_type="lore_keeper",
                confidence=0.95,
                metadata={
                    "lore_category": lore_request['category'],
                    "knowledge_level": lore_request['knowledge_level'],
                    "topics_covered": lore_request['topic'],
                    "token_usage": response.get("usage", {})
                }
            )

        except Exception as e:
            # Fallback lore response
            fallback_response = self._generate_fallback_lore(lore_request, context)

            return AgentResponse(
                content=fallback_response,
                agent_type="lore_keeper",
                confidence=0.6,
                metadata={
                    "error": str(e),
                    "fallback": True,
                    "lore_category": lore_request['category']
                }
            )

    def should_handoff(self, message_content: str, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Determine if message should be handed off to another agent"""
        content_lower = message_content.lower()

        # NPC-specific information requests
        npc_keywords = ["talk to", "ask the", "speak with", "who can tell me"]
        if any(keyword in content_lower for keyword in npc_keywords):
            return True, "npc_interaction"

        # Scene action requests
        scene_keywords = ["show me", "take me to", "go to", "find the location"]
        if any(keyword in content_lower for keyword in scene_keywords):
            return True, "narrator"

        # Rules mechanics
        rule_keywords = ["how does magic work mechanically", "what are the rules for"]
        if any(keyword in content_lower for keyword in rule_keywords):
            return True, "rules_keeper"

        return False, None

    def _analyze_lore_request(self, message: str) -> Dict[str, Any]:
        """Analyze the lore request to categorize and prioritize"""
        message_lower = message.lower()

        # Determine category
        category = "general"
        if any(word in message_lower for word in ["history", "historical", "past", "ancient", "ago"]):
            category = "history"
        elif any(word in message_lower for word in ["geography", "place", "location", "where", "region"]):
            category = "geography"
        elif any(word in message_lower for word in ["culture", "people", "customs", "traditions"]):
            category = "cultures"
        elif any(word in message_lower for word in ["religion", "gods", "divine", "worship", "faith"]):
            category = "religions"
        elif any(word in message_lower for word in ["politics", "government", "ruler", "kingdom", "empire"]):
            category = "politics"
        elif any(word in message_lower for word in ["guild", "organization", "order", "group"]):
            category = "organizations"
        elif any(word in message_lower for word in ["legend", "myth", "story", "tale", "prophecy"]):
            category = "legends"
        elif any(word in message_lower for word in ["magic", "spell", "arcane", "mystical", "enchantment"]):
            category = "magic"

        # Determine knowledge level
        knowledge_level = "common"
        if any(word in message_lower for word in ["secret", "hidden", "forbidden", "classified"]):
            knowledge_level = "secret"
        elif any(word in message_lower for word in ["ancient", "lost", "forgotten", "old"]):
            knowledge_level = "lost"
        elif any(word in message_lower for word in ["detailed", "specific", "technical", "scholarly"]):
            knowledge_level = "specialized"

        # Determine scope
        scope = "focused"
        if any(word in message_lower for word in ["everything about", "all about", "comprehensive", "complete"]):
            scope = "comprehensive"
        elif any(word in message_lower for word in ["overview", "summary", "general"]):
            scope = "overview"

        # Extract main topic
        topic = self._extract_main_topic(message)

        return {
            "category": category,
            "knowledge_level": knowledge_level,
            "scope": scope,
            "topic": topic
        }

    def _extract_main_topic(self, message: str) -> str:
        """Extract the main topic from the lore request"""
        # Simple extraction - in full implementation, this would use NLP
        words = message.lower().split()

        # Look for question patterns
        if "what is" in message.lower():
            what_index = message.lower().find("what is") + 7
            topic = message[what_index:].split('?')[0].strip()
            return topic

        if "tell me about" in message.lower():
            tell_index = message.lower().find("tell me about") + 13
            topic = message[tell_index:].split('.')[0].strip()
            return topic

        # Look for key nouns (simplified)
        key_words = []
        for word in words:
            if len(word) > 3 and word not in ["what", "tell", "about", "the", "this", "that"]:
                key_words.append(word)

        return " ".join(key_words[:3])  # Take first few key words

    def _format_character_knowledge_context(self, context: Dict[str, Any]) -> str:
        """Format character's background for knowledge filtering"""
        character = context.get("character", {})

        knowledge_factors = []
        if character.get("background"):
            knowledge_factors.append(f"Background: {character['background']}")

        if character.get("intelligence", 10) >= 14:
            knowledge_factors.append("High Intelligence: Likely to know scholarly information")

        character_class = character.get("character_class", "")
        if character_class:
            knowledge_factors.append(f"Class: {character_class} - relevant specialized knowledge")

        return "\n".join(knowledge_factors) if knowledge_factors else "Average knowledge level expected."

    def _format_established_lore(self, category: str) -> str:
        """Format previously established lore for consistency"""
        established = self.lore_categories.get(category, {})

        if not established:
            return "No previously established lore in this category."

        lore_summary = []
        for topic, info in established.items():
            lore_summary.append(f"- {topic}: {info[:100]}...")

        return "\n".join(lore_summary[:5])  # Limit to prevent prompt bloat

    def _enrich_lore_response(self, response: str, lore_request: Dict, context: Dict[str, Any]) -> str:
        """Enrich the lore response with additional context and formatting"""
        # Add knowledge level indicator
        knowledge_indicator = {
            "common": "📚 **Common Knowledge**",
            "specialized": "🎓 **Specialized Knowledge**",
            "secret": "🔒 **Secret Knowledge**",
            "lost": "🏺 **Ancient Lore**"
        }

        indicator = knowledge_indicator.get(lore_request['knowledge_level'], "📚 **Knowledge**")

        enriched_response = f"{indicator}\n\n{response}"

        # Add connections to current adventure if relevant
        if context.get("game_state", {}).get("current_location"):
            location = context["game_state"]["current_location"]
            if location.lower() in response.lower():
                enriched_response += f"\n\n*This information seems particularly relevant to your current location: {location}*"

        return enriched_response

    def _update_lore_cache(self, lore_request: Dict, response: str):
        """Update the lore cache with new information"""
        category = lore_request['category']
        topic = lore_request['topic']

        if category in self.lore_categories:
            # Store a summary for consistency checking
            summary = response[:200] + "..." if len(response) > 200 else response
            self.lore_categories[category][topic] = summary

    def _generate_fallback_lore(self, lore_request: Dict, context: Dict[str, Any]) -> str:
        """Generate basic fallback lore when AI is unavailable"""
        category = lore_request['category']
        topic = lore_request['topic']

        fallback_responses = {
            "history": f"The history of {topic} is complex and spans many generations. Much of the detailed information has been lost to time, but local scholars might know more.",
            "geography": f"{topic} is a notable location in this region. The area has its own unique characteristics and local significance.",
            "cultures": f"The people and customs of {topic} have their own distinct traditions that have evolved over time.",
            "religions": f"The divine aspects of {topic} are matters of faith and belief, interpreted differently by various followers.",
            "politics": f"The political situation regarding {topic} is complex and ever-changing, influenced by many factors.",
            "organizations": f"{topic} is an established group with its own goals, structure, and influence in the world.",
            "legends": f"The legends surrounding {topic} are told differently by various storytellers, each adding their own interpretation.",
            "magic": f"The magical aspects of {topic} follow the fundamental principles of arcane study, though specific details may vary."
        }

        base_response = fallback_responses.get(category, f"Information about {topic} would require further research and investigation.")

        return f"📚 **Knowledge**\n\n{base_response}\n\n*More detailed information may be available through further investigation or speaking with knowledgeable NPCs.*"