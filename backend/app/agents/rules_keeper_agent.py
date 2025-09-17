"""
Rules Keeper Agent - Handles game mechanics, dice rolls, and rule enforcement
"""

import random
import re
from typing import Dict, Any, List, Optional, Tuple
from .base_agent import BaseAgent, AgentMessage, AgentResponse

class DiceRoll:
    """Represents a dice roll with results"""
    def __init__(self, sides: int, count: int = 1, modifier: int = 0):
        self.sides = sides
        self.count = count
        self.modifier = modifier
        self.rolls = [random.randint(1, sides) for _ in range(count)]
        self.total = sum(self.rolls) + modifier

    def __str__(self):
        base_str = f"{self.count}d{self.sides}"
        if self.modifier != 0:
            base_str += f"+{self.modifier}" if self.modifier > 0 else str(self.modifier)

        rolls_str = f"[{', '.join(map(str, self.rolls))}]"
        if self.modifier != 0:
            rolls_str += f" + {self.modifier}" if self.modifier > 0 else f" {self.modifier}"

        return f"{base_str}: {rolls_str} = {self.total}"

class RulesKeeperAgent(BaseAgent):
    """Agent responsible for game mechanics, dice rolls, and rule enforcement"""

    def __init__(self):
        system_prompt = """You are the Rules Keeper Agent for GameMasterJJ, an AI-powered TRPG Game Master system.

Your responsibilities include:
1. Processing dice roll requests and calculating results
2. Enforcing game rules and mechanics
3. Handling combat actions and turn order
4. Managing character stats and modifications
5. Determining skill check difficulties and outcomes

DICE ROLL FORMATS YOU UNDERSTAND:
- "1d20" = one 20-sided die
- "2d6+3" = two 6-sided dice plus 3
- "1d20+5" = one 20-sided die plus 5 modifier
- "advantage" or "disadvantage" for d20 rolls

DIFFICULTY CLASSES (DC):
- Trivial: DC 5
- Easy: DC 10
- Medium: DC 15
- Hard: DC 20
- Very Hard: DC 25
- Nearly Impossible: DC 30

COMBAT RULES:
- Initiative: 1d20 + Dex modifier
- Attack rolls: 1d20 + ability modifier + proficiency
- Damage: weapon dice + ability modifier
- Saving throws: 1d20 + ability modifier + proficiency (if proficient)

GUIDELINES:
- Always show dice roll calculations clearly
- Explain rule applications and reasoning
- Suggest appropriate difficulty classes
- Handle rule edge cases consistently
- Provide clear success/failure outcomes

You are the arbiter of game balance and fairness."""

        super().__init__("rules_keeper", system_prompt)

        # Initialize standard difficulty classes
        self.difficulty_classes = {
            "trivial": 5,
            "easy": 10,
            "medium": 15,
            "hard": 20,
            "very_hard": 25,
            "nearly_impossible": 30
        }

    async def process_message(self, message: AgentMessage, context: Dict[str, Any]) -> AgentResponse:
        """Process rules-related message and provide mechanical response"""

        # Parse dice roll requests
        dice_requests = self._parse_dice_requests(message.content)

        if dice_requests:
            return await self._handle_dice_rolls(dice_requests, message, context)

        # Handle other rules queries
        return await self._handle_rules_query(message, context)

    def _parse_dice_requests(self, message: str) -> List[Dict[str, Any]]:
        """Parse dice roll requests from message"""
        dice_patterns = [
            r'(\d+)d(\d+)(?:\+(\d+))?(?:\-(\d+))?',  # Standard dice notation
            r'advantage|disadvantage',  # Special d20 rolls
            r'roll\s+(\w+)',  # Named rolls like "roll initiative"
        ]

        requests = []
        message_lower = message.lower()

        # Standard dice notation
        for match in re.finditer(dice_patterns[0], message_lower):
            count = int(match.group(1))
            sides = int(match.group(2))
            add_mod = int(match.group(3)) if match.group(3) else 0
            sub_mod = int(match.group(4)) if match.group(4) else 0
            modifier = add_mod - sub_mod

            requests.append({
                "type": "standard_roll",
                "count": count,
                "sides": sides,
                "modifier": modifier,
                "text": match.group(0)
            })

        # Advantage/disadvantage
        if "advantage" in message_lower:
            requests.append({"type": "advantage", "text": "advantage"})
        elif "disadvantage" in message_lower:
            requests.append({"type": "disadvantage", "text": "disadvantage"})

        # Named rolls
        if "initiative" in message_lower:
            requests.append({"type": "initiative", "text": "initiative"})
        elif "saving throw" in message_lower or "save" in message_lower:
            requests.append({"type": "saving_throw", "text": "saving throw"})
        elif "attack" in message_lower:
            requests.append({"type": "attack_roll", "text": "attack"})
        elif "skill check" in message_lower or "ability check" in message_lower:
            requests.append({"type": "skill_check", "text": "skill check"})

        return requests

    async def _handle_dice_rolls(self, dice_requests: List[Dict], message: AgentMessage, context: Dict[str, Any]) -> AgentResponse:
        """Handle dice roll requests"""
        roll_results = []
        total_rolls = 0

        for request in dice_requests:
            if request["type"] == "standard_roll":
                roll = DiceRoll(request["sides"], request["count"], request["modifier"])
                roll_results.append(str(roll))
                total_rolls += 1

            elif request["type"] == "advantage":
                roll1 = DiceRoll(20)
                roll2 = DiceRoll(20)
                higher = max(roll1.total, roll2.total)
                roll_results.append(f"Advantage: {roll1.rolls[0]}, {roll2.rolls[0]} → Taking higher: {higher}")
                total_rolls += 2

            elif request["type"] == "disadvantage":
                roll1 = DiceRoll(20)
                roll2 = DiceRoll(20)
                lower = min(roll1.total, roll2.total)
                roll_results.append(f"Disadvantage: {roll1.rolls[0]}, {roll2.rolls[0]} → Taking lower: {lower}")
                total_rolls += 2

            elif request["type"] == "initiative":
                dex_mod = self._get_character_modifier(context, "dexterity")
                roll = DiceRoll(20, 1, dex_mod)
                roll_results.append(f"Initiative: {roll}")
                total_rolls += 1

            elif request["type"] == "attack_roll":
                # Determine appropriate modifier based on context
                attack_mod = self._determine_attack_modifier(context)
                roll = DiceRoll(20, 1, attack_mod)
                roll_results.append(f"Attack Roll: {roll}")
                total_rolls += 1

            elif request["type"] == "skill_check":
                # Determine skill and modifier
                skill_info = self._determine_skill_check(message.content, context)
                roll = DiceRoll(20, 1, skill_info["modifier"])
                dc_info = self._suggest_difficulty_class(message.content)
                roll_results.append(f"{skill_info['skill']} Check: {roll} (DC {dc_info['dc']} - {dc_info['difficulty']})")

                # Determine success/failure
                success = roll.total >= dc_info['dc']
                roll_results.append(f"Result: {'SUCCESS' if success else 'FAILURE'}")
                total_rolls += 1

        # Generate OpenAI response with roll results
        messages = [
            self.get_system_message(),
            {
                "role": "user",
                "content": f"""PLAYER REQUEST: {message.content}

DICE ROLL RESULTS:
{chr(10).join(roll_results)}

CONTEXT:
{self.format_context_for_prompt(context)}

Provide a rules-accurate response that:
1. Confirms the dice roll results
2. Explains any rule applications
3. Describes the mechanical outcome
4. Suggests next steps if appropriate"""
            }
        ]

        try:
            response = await self._call_openai(messages)

            # Combine AI response with dice results
            full_response = f"🎲 **Dice Results:**\n{chr(10).join(roll_results)}\n\n{response['content']}"

            return AgentResponse(
                content=full_response,
                agent_type="rules_keeper",
                confidence=0.95,
                metadata={
                    "dice_rolls": roll_results,
                    "total_rolls": total_rolls,
                    "token_usage": response.get("usage", {})
                }
            )

        except Exception as e:
            # Fallback response with just dice results
            fallback_response = f"🎲 **Dice Results:**\n{chr(10).join(roll_results)}\n\nRoll complete! (Rules explanation temporarily unavailable)"

            return AgentResponse(
                content=fallback_response,
                agent_type="rules_keeper",
                confidence=0.7,
                metadata={
                    "dice_rolls": roll_results,
                    "error": str(e),
                    "fallback": True
                }
            )

    async def _handle_rules_query(self, message: AgentMessage, context: Dict[str, Any]) -> AgentResponse:
        """Handle general rules queries"""
        messages = [
            self.get_system_message(),
            {
                "role": "user",
                "content": f"""RULES QUESTION: {message.content}

GAME CONTEXT:
{self.format_context_for_prompt(context)}

Provide a clear, accurate explanation of the relevant game rules and mechanics."""
            }
        ]

        try:
            response = await self._call_openai(messages)

            return AgentResponse(
                content=response["content"],
                agent_type="rules_keeper",
                confidence=0.9,
                metadata={"token_usage": response.get("usage", {})}
            )

        except Exception as e:
            return AgentResponse(
                content="I'm having trouble accessing the rulebook right now. Please try rephrasing your question.",
                agent_type="rules_keeper",
                confidence=0.3,
                metadata={"error": str(e)}
            )

    def _get_character_modifier(self, context: Dict[str, Any], ability: str) -> int:
        """Get character ability modifier from context"""
        character = context.get("character", {})
        ability_score = character.get(ability, 10)
        return (ability_score - 10) // 2

    def _determine_attack_modifier(self, context: Dict[str, Any]) -> int:
        """Determine attack roll modifier based on character stats"""
        character = context.get("character", {})

        # Simple logic - use strength for melee, dex for ranged
        # In full implementation, this would check weapon type
        str_mod = self._get_character_modifier(context, "strength")
        proficiency = character.get("proficiency_bonus", 2)

        return str_mod + proficiency

    def _determine_skill_check(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Determine what skill check is being attempted"""
        message_lower = message.lower()

        skill_mappings = {
            "athletics": "strength",
            "acrobatics": "dexterity",
            "stealth": "dexterity",
            "perception": "wisdom",
            "investigation": "intelligence",
            "insight": "wisdom",
            "persuasion": "charisma",
            "deception": "charisma",
            "intimidation": "charisma"
        }

        for skill, ability in skill_mappings.items():
            if skill in message_lower:
                modifier = self._get_character_modifier(context, ability)
                proficiency = context.get("character", {}).get("proficiency_bonus", 2)

                # Check if character is proficient (simplified)
                total_modifier = modifier + proficiency

                return {
                    "skill": skill.capitalize(),
                    "ability": ability,
                    "modifier": total_modifier
                }

        # Default to generic ability check
        return {
            "skill": "Ability",
            "ability": "varies",
            "modifier": 0
        }

    def _suggest_difficulty_class(self, message: str) -> Dict[str, Any]:
        """Suggest appropriate difficulty class based on context"""
        message_lower = message.lower()

        # Simple heuristics for DC suggestion
        if any(word in message_lower for word in ["easy", "simple", "basic"]):
            return {"dc": 10, "difficulty": "Easy"}
        elif any(word in message_lower for word in ["hard", "difficult", "challenging"]):
            return {"dc": 20, "difficulty": "Hard"}
        elif any(word in message_lower for word in ["impossible", "legendary", "epic"]):
            return {"dc": 25, "difficulty": "Very Hard"}
        else:
            return {"dc": 15, "difficulty": "Medium"}  # Default