"""
Agent Service - Integration layer between API and multi-agent system
"""

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..agents.agent_coordinator import AgentCoordinator
from ..models import GameSession, ChatMessage, Character
from ..models.session import MessageSender
import json

class AgentService:
    """Service layer for agent coordination and game session integration"""

    def __init__(self):
        self.coordinator = AgentCoordinator()

    async def process_player_input(
        self,
        session_id: str,
        player_input: str,
        db_session: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """Process player input through the multi-agent system"""

        try:
            # Load game session and context
            context = await self._build_game_context(session_id, db_session)

            # Process through agent coordinator
            result = await self.coordinator.process_player_message(
                content=player_input,
                session_id=session_id,
                context=context
            )

            if result["success"]:
                # Store the conversation in database
                await self._store_conversation(
                    session_id=session_id,
                    player_input=player_input,
                    agent_response=result["response"],
                    agent_type=result["agent"],
                    handoff_chain=result["handoff_chain"],
                    metadata=result.get("metadata", {}),
                    db_session=db_session
                )

                # Update game state if necessary
                await self._update_game_state(session_id, result, db_session)

                return {
                    "success": True,
                    "message": result["response"],
                    "agent": result["agent"],
                    "processing_info": {
                        "handoff_chain": result["handoff_chain"],
                        "handoff_count": result["handoff_count"],
                        "processing_time": result["processing_time"],
                        "confidence": result["confidence"]
                    }
                }

            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "message": result.get("response", "I'm sorry, I couldn't process your request.")
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Service error: {str(e)}",
                "message": "I encountered an error while processing your request. Please try again."
            }

    async def get_session_status(self, session_id: str, db_session: AsyncSession) -> Dict[str, Any]:
        """Get current session status and agent information"""

        try:
            # Get agent status
            agent_status = await self.coordinator.get_agent_status()

            # Get conversation history
            conversation_history = self.coordinator.get_conversation_history(session_id, limit=10)

            # Get handoff analytics for this session
            handoff_analytics = self.coordinator.get_handoff_analytics(session_id)

            return {
                "success": True,
                "session_id": session_id,
                "agents": agent_status["agents"],
                "recent_conversations": len(conversation_history),
                "analytics": handoff_analytics
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Status error: {str(e)}"
            }

    async def reset_session_agents(self, session_id: str) -> Dict[str, Any]:
        """Reset agent memories for a session"""
        try:
            self.coordinator.reset_session(session_id)
            return {
                "success": True,
                "message": f"Agent memories reset for session {session_id}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Reset error: {str(e)}"
            }

    async def _build_game_context(self, session_id: str, db_session: AsyncSession) -> Dict[str, Any]:
        """Build comprehensive game context for agents"""

        # Load game session from database
        from sqlalchemy import select
        stmt = select(GameSession).where(GameSession.id == session_id)
        result = await db_session.execute(stmt)
        game_session = result.scalar_one_or_none()

        if not game_session:
            return {"error": "Session not found"}

        context = {
            "session_id": session_id,
            "game_state": game_session.game_state or {},
            "world_state": game_session.world_state or {},
            "current_location": game_session.current_location,
            "active_storylets": game_session.active_storylets or []
        }

        # Load character information
        if game_session.character_id:
            stmt = select(Character).where(Character.id == game_session.character_id)
            result = await db_session.execute(stmt)
            character = result.scalar_one_or_none()

            if character:
                context["character"] = {
                    "id": character.id,
                    "name": character.name,
                    "character_class": character.character_class.value,
                    "level": character.level,
                    "experience": character.experience,
                    "strength": character.strength,
                    "dexterity": character.dexterity,
                    "constitution": character.constitution,
                    "intelligence": character.intelligence,
                    "wisdom": character.wisdom,
                    "charisma": character.charisma,
                    "hit_points_max": character.hit_points_max,
                    "hit_points_current": character.hit_points_current,
                    "armor_class": character.armor_class,
                    "proficiency_bonus": character.proficiency_bonus,
                    "background": character.background
                }

        # Load recent conversation history for context
        stmt = (select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.sequence_number.desc())
                .limit(5))
        result = await db_session.execute(stmt)
        recent_messages = result.scalars().all()

        context["recent_messages"] = [
            {
                "content": msg.content,
                "sender": msg.sender.value,
                "sequence": msg.sequence_number
            }
            for msg in reversed(recent_messages)  # Most recent first -> chronological order
        ]

        return context

    async def _store_conversation(
        self,
        session_id: str,
        player_input: str,
        agent_response: str,
        agent_type: str,
        handoff_chain: list,
        metadata: dict,
        db_session: AsyncSession
    ):
        """Store conversation in database"""

        from sqlalchemy import select, func

        # Get next sequence number
        stmt = select(func.max(ChatMessage.sequence_number)).where(ChatMessage.session_id == session_id)
        result = await db_session.execute(stmt)
        max_seq = result.scalar() or 0

        # Store player message
        player_message = ChatMessage(
            session_id=session_id,
            content=player_input,
            sender=MessageSender.PLAYER,
            sequence_number=max_seq + 1,
            agent_context={
                "processed_by_agents": True,
                "handoff_chain": handoff_chain,
                "final_agent": agent_type
            }
        )
        db_session.add(player_message)

        # Store agent response
        agent_sender = self._map_agent_to_sender(agent_type)
        agent_message = ChatMessage(
            session_id=session_id,
            content=agent_response,
            sender=agent_sender,
            sequence_number=max_seq + 2,
            agent_context={
                "agent_type": agent_type,
                "handoff_chain": handoff_chain,
                "metadata": metadata
            }
        )
        db_session.add(agent_message)

        await db_session.commit()

    def _map_agent_to_sender(self, agent_type: str) -> MessageSender:
        """Map agent type to message sender enum"""
        mapping = {
            "triage": MessageSender.TRIAGE_AGENT,
            "narrator": MessageSender.NARRATOR_AGENT,
            "rules_keeper": MessageSender.RULES_KEEPER_AGENT,
            "npc_interaction": MessageSender.NPC_INTERACTION_AGENT,
            "lore_keeper": MessageSender.LORE_KEEPER_AGENT
        }
        return mapping.get(agent_type, MessageSender.GM)

    async def _update_game_state(
        self,
        session_id: str,
        agent_result: Dict[str, Any],
        db_session: AsyncSession
    ):
        """Update game state based on agent interactions"""

        # Get game session
        from sqlalchemy import select
        stmt = select(GameSession).where(GameSession.id == session_id)
        result = await db_session.execute(stmt)
        game_session = result.scalar_one_or_none()

        if not game_session:
            return

        # Update based on agent metadata
        metadata = agent_result.get("metadata", {})

        # Update location if narrator changed it
        if agent_result["agent"] == "narrator" and "new_location" in metadata:
            game_session.current_location = metadata["new_location"]

        # Update character stats if rules keeper modified them
        if agent_result["agent"] == "rules_keeper" and "stat_changes" in metadata:
            # This would update character stats in the database
            # Implementation depends on specific stat change format
            pass

        # Update world state variables
        if "world_state_changes" in metadata:
            current_world_state = game_session.world_state or {}
            current_world_state.update(metadata["world_state_changes"])
            game_session.world_state = current_world_state

        await db_session.commit()

# Global service instance
agent_service = AgentService()