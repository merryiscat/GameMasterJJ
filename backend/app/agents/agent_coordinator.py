"""
Agent Coordinator - Manages multi-agent system and handoffs
"""

import asyncio
from typing import Dict, Any, List, Optional
from .base_agent import AgentMessage, AgentResponse
from .triage_agent import TriageAgent
from .narrator_agent import NarratorAgent
from .rules_keeper_agent import RulesKeeperAgent
from .npc_interaction_agent import NPCInteractionAgent
from .lore_keeper_agent import LoreKeeperAgent

class AgentCoordinator:
    """Coordinates multiple agents and manages handoffs"""

    def __init__(self):
        # Initialize all agents
        self.agents = {
            "triage": TriageAgent(),
            "narrator": NarratorAgent(),
            "rules_keeper": RulesKeeperAgent(),
            "npc_interaction": NPCInteractionAgent(),
            "lore_keeper": LoreKeeperAgent()
        }

        # Handoff tracking
        self.conversation_history: List[Dict[str, Any]] = []
        self.current_session_id: Optional[str] = None

        # Performance tracking
        self.response_times = {}
        self.handoff_chains = []
        self.agent_usage_stats = {agent_type: 0 for agent_type in self.agents.keys()}

    async def process_player_message(
        self,
        content: str,
        session_id: str,
        context: Dict[str, Any],
        max_handoffs: int = 3
    ) -> Dict[str, Any]:
        """Process a player message through the multi-agent system"""

        self.current_session_id = session_id
        message = AgentMessage(content=content, sender="player")

        # Start with triage agent
        current_agent = "triage"
        handoff_count = 0
        handoff_chain = [current_agent]

        start_time = asyncio.get_event_loop().time()

        try:
            while handoff_count < max_handoffs:
                # Process message with current agent
                agent = self.agents[current_agent]
                self.agent_usage_stats[current_agent] += 1

                response = await agent.process_message(message, context)

                # Add to conversation history
                agent.add_to_history(message)
                agent.add_to_history(AgentMessage(
                    content=response.content,
                    sender=current_agent,
                    metadata=response.metadata
                ))

                # Check if handoff is needed
                if response.needs_handoff and response.handoff_target:
                    if response.handoff_target not in self.agents:
                        # Invalid handoff target, end processing
                        break

                    # Perform handoff
                    current_agent = response.handoff_target
                    handoff_count += 1
                    handoff_chain.append(current_agent)

                    # Update message for next agent (preserve original but add context)
                    if handoff_count == 1:  # First handoff from triage
                        # Use original player message for specialized agent
                        continue
                    else:
                        # Subsequent handoffs may need modified context
                        message = AgentMessage(
                            content=content,  # Keep original player message
                            sender="player",
                            metadata={"previous_agent_response": response.content}
                        )
                        continue

                else:
                    # No handoff needed, we have final response
                    end_time = asyncio.get_event_loop().time()
                    total_time = end_time - start_time

                    # Record handoff chain
                    self.handoff_chains.append({
                        "session_id": session_id,
                        "chain": handoff_chain,
                        "final_agent": current_agent,
                        "handoff_count": handoff_count,
                        "total_time": total_time,
                        "success": True
                    })

                    # Update conversation history
                    self._add_to_conversation_history({
                        "session_id": session_id,
                        "player_message": content,
                        "handoff_chain": handoff_chain,
                        "final_response": response.content,
                        "final_agent": current_agent,
                        "metadata": response.metadata,
                        "processing_time": total_time
                    })

                    return {
                        "success": True,
                        "response": response.content,
                        "agent": current_agent,
                        "handoff_chain": handoff_chain,
                        "handoff_count": handoff_count,
                        "processing_time": total_time,
                        "confidence": response.confidence,
                        "metadata": response.metadata
                    }

            # Max handoffs reached - return last response
            end_time = asyncio.get_event_loop().time()
            total_time = end_time - start_time

            self.handoff_chains.append({
                "session_id": session_id,
                "chain": handoff_chain,
                "final_agent": current_agent,
                "handoff_count": handoff_count,
                "total_time": total_time,
                "success": False,
                "error": "max_handoffs_reached"
            })

            return {
                "success": False,
                "error": "Maximum handoffs reached",
                "response": "I'm having trouble processing your request. Please try rephrasing it.",
                "agent": current_agent,
                "handoff_chain": handoff_chain,
                "handoff_count": handoff_count,
                "processing_time": total_time
            }

        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            total_time = end_time - start_time

            self.handoff_chains.append({
                "session_id": session_id,
                "chain": handoff_chain,
                "final_agent": current_agent,
                "handoff_count": handoff_count,
                "total_time": total_time,
                "success": False,
                "error": str(e)
            })

            return {
                "success": False,
                "error": f"Agent processing error: {str(e)}",
                "response": "I encountered an error while processing your request. Please try again.",
                "agent": current_agent,
                "handoff_chain": handoff_chain,
                "handoff_count": handoff_count,
                "processing_time": total_time
            }

    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        return {
            "agents": {
                agent_type: {
                    "type": agent_type,
                    "conversation_length": len(agent.conversation_history),
                    "usage_count": self.agent_usage_stats[agent_type]
                }
                for agent_type, agent in self.agents.items()
            },
            "total_conversations": len(self.conversation_history),
            "total_handoff_chains": len(self.handoff_chains),
            "average_handoffs": self._calculate_average_handoffs(),
            "most_used_agent": self._get_most_used_agent(),
            "success_rate": self._calculate_success_rate()
        }

    def reset_session(self, session_id: str):
        """Reset conversation history for a specific session"""
        # Clear agent histories
        for agent in self.agents.values():
            agent.conversation_history = []

        # Clear session-specific conversation history
        self.conversation_history = [
            conv for conv in self.conversation_history
            if conv.get("session_id") != session_id
        ]

    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        session_history = [
            conv for conv in self.conversation_history
            if conv.get("session_id") == session_id
        ]

        # Return most recent conversations first
        return list(reversed(session_history[-limit:]))

    def get_handoff_analytics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get analytics on handoff patterns"""
        relevant_chains = self.handoff_chains
        if session_id:
            relevant_chains = [
                chain for chain in self.handoff_chains
                if chain.get("session_id") == session_id
            ]

        if not relevant_chains:
            return {"error": "No handoff data available"}

        # Analyze handoff patterns
        handoff_patterns = {}
        for chain_data in relevant_chains:
            chain = chain_data.get("chain", [])
            if len(chain) > 1:
                for i in range(len(chain) - 1):
                    from_agent = chain[i]
                    to_agent = chain[i + 1]
                    pattern = f"{from_agent} -> {to_agent}"
                    handoff_patterns[pattern] = handoff_patterns.get(pattern, 0) + 1

        return {
            "total_chains": len(relevant_chains),
            "successful_chains": len([c for c in relevant_chains if c.get("success", False)]),
            "average_handoffs": sum(c.get("handoff_count", 0) for c in relevant_chains) / len(relevant_chains),
            "average_processing_time": sum(c.get("total_time", 0) for c in relevant_chains) / len(relevant_chains),
            "common_handoff_patterns": dict(sorted(handoff_patterns.items(), key=lambda x: x[1], reverse=True)[:10]),
            "agent_usage": self.agent_usage_stats.copy()
        }

    def _add_to_conversation_history(self, conversation_data: Dict[str, Any]):
        """Add conversation to history"""
        self.conversation_history.append(conversation_data)

        # Keep only last 1000 conversations to manage memory
        if len(self.conversation_history) > 1000:
            self.conversation_history = self.conversation_history[-1000:]

    def _calculate_average_handoffs(self) -> float:
        """Calculate average number of handoffs per conversation"""
        if not self.handoff_chains:
            return 0.0

        total_handoffs = sum(chain.get("handoff_count", 0) for chain in self.handoff_chains)
        return total_handoffs / len(self.handoff_chains)

    def _get_most_used_agent(self) -> str:
        """Get the most frequently used agent"""
        if not self.agent_usage_stats:
            return "none"

        return max(self.agent_usage_stats.items(), key=lambda x: x[1])[0]

    def _calculate_success_rate(self) -> float:
        """Calculate success rate of agent processing"""
        if not self.handoff_chains:
            return 0.0

        successful = len([chain for chain in self.handoff_chains if chain.get("success", False)])
        return successful / len(self.handoff_chains) if self.handoff_chains else 0.0