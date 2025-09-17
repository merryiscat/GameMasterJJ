#!/usr/bin/env python3
"""
Test script for multi-agent system
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.agents.agent_coordinator import AgentCoordinator

async def test_agent_system():
    """Test the multi-agent system"""

    print("🤖 Testing GameMasterJJ Multi-Agent System")
    print("=" * 50)

    coordinator = AgentCoordinator()

    # Test context
    test_context = {
        "session_id": "test-session-001",
        "character": {
            "name": "Thorin",
            "character_class": "fighter",
            "level": 3,
            "strength": 16,
            "dexterity": 12,
            "intelligence": 10,
            "wisdom": 13,
            "charisma": 8,
            "proficiency_bonus": 2
        },
        "game_state": {
            "current_location": "Ancient Dungeon Entrance"
        }
    }

    # Test cases
    test_cases = [
        {
            "input": "I want to roll a d20",
            "expected_agent": "rules_keeper",
            "description": "Dice roll request"
        },
        {
            "input": "I look around the dungeon entrance",
            "expected_agent": "narrator",
            "description": "Scene description request"
        },
        {
            "input": "Tell me about the history of this place",
            "expected_agent": "lore_keeper",
            "description": "Lore/history request"
        },
        {
            "input": "I want to talk to the guard",
            "expected_agent": "npc_interaction",
            "description": "NPC interaction request"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['description']}")
        print(f"📝 Input: '{test_case['input']}'")

        try:
            # Note: This will fail without OpenAI API key, but will test routing
            result = await coordinator.process_player_message(
                content=test_case['input'],
                session_id="test-session-001",
                context=test_context
            )

            if result["success"]:
                print(f"✅ Success! Routed to: {result['agent']}")
                print(f"🔄 Handoff chain: {' -> '.join(result['handoff_chain'])}")
                print(f"⏱️  Processing time: {result['processing_time']:.3f}s")

                if result["agent"] == test_case["expected_agent"]:
                    print("✅ Correct agent routing!")
                else:
                    print(f"⚠️  Expected {test_case['expected_agent']}, got {result['agent']}")

            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            if "OpenAI" in str(e) or "API" in str(e):
                print("ℹ️  This is expected without OpenAI API key configured")

    # Test agent status
    print(f"\n📊 Agent Status:")
    status = await coordinator.get_agent_status()
    for agent_type, agent_info in status["agents"].items():
        print(f"  - {agent_type}: {agent_info['usage_count']} uses")

    print(f"\n🎯 Overall Stats:")
    print(f"  - Total conversations: {status['total_conversations']}")
    print(f"  - Total handoff chains: {status['total_handoff_chains']}")
    print(f"  - Average handoffs: {status['average_handoffs']:.2f}")
    print(f"  - Success rate: {status['success_rate']:.2%}")

    print("\n✅ Multi-agent system test completed!")

if __name__ == "__main__":
    try:
        asyncio.run(test_agent_system())
    except KeyboardInterrupt:
        print("\n\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()