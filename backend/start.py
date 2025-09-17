#!/usr/bin/env python3
"""
GameMasterJJ Backend Startup Script
"""

import uvicorn
import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

async def check_dependencies():
    """Check if all required dependencies are available"""
    print("Checking dependencies...")

    try:
        import fastapi
        print(f"[OK] FastAPI {fastapi.__version__}")
    except ImportError:
        print("[ERROR] FastAPI not found. Run: pip install -r requirements.txt")
        return False

    try:
        import openai
        print(f"[OK] OpenAI Python SDK {openai.__version__}")
    except ImportError:
        print("[ERROR] OpenAI SDK not found. Run: pip install -r requirements.txt")
        return False

    try:
        import sqlalchemy
        print(f"[OK] SQLAlchemy {sqlalchemy.__version__}")
    except ImportError:
        print("[ERROR] SQLAlchemy not found. Run: pip install -r requirements.txt")
        return False

    # Check environment file
    env_file = backend_dir / ".env"
    if env_file.exists():
        print("[OK] Environment file found")
    else:
        print("[WARN] .env file not found. Using default configuration.")
        print("   Copy .env.example to .env and configure your settings.")

    return True

def check_openai_key():
    """Check OpenAI API key configuration"""
    print("\nChecking OpenAI configuration...")

    from app.core.config import settings

    if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-test"):
        print("[OK] OpenAI API key configured")
        return True
    else:
        print("[WARN] OpenAI API key not configured or using test key")
        print("   Set OPENAI_API_KEY in your .env file to enable AI responses")
        print("   The system will work with fallback responses for testing")
        return False

async def initialize_database():
    """Initialize the database"""
    print("\nInitializing database...")

    try:
        from app.core.database import init_db
        await init_db()
        print("[OK] Database initialized successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {str(e)}")
        return False

async def test_agent_system():
    """Quick test of the agent system"""
    print("\nTesting agent system...")

    try:
        from app.agents.agent_coordinator import AgentCoordinator

        coordinator = AgentCoordinator()

        # Quick routing test
        test_context = {
            "session_id": "startup-test",
            "character": {"name": "Test Character", "level": 1},
            "game_state": {"current_location": "Test Location"}
        }

        # Test triage routing (won't call OpenAI, just routing logic)
        print("   Testing message routing...")

        test_result = await coordinator.process_player_message(
            content="I want to roll a d20",
            session_id="startup-test",
            context=test_context,
            max_handoffs=1  # Just test triage
        )

        if test_result.get("success"):
            print(f"[OK] Agent routing working - routed to: {test_result.get('agent', 'unknown')}")
        else:
            print(f"[WARN] Agent test completed with fallback: {test_result.get('error', 'unknown')}")

        return True

    except Exception as e:
        print(f"[ERROR] Agent system test failed: {str(e)}")
        return False

def main():
    """Main startup function"""
    print("Starting GameMasterJJ Backend")
    print("=" * 50)

    # Check dependencies
    if not asyncio.run(check_dependencies()):
        print("\n[ERROR] Dependency check failed. Please install requirements.")
        sys.exit(1)

    # Check OpenAI configuration
    openai_configured = check_openai_key()

    # Initialize database
    if not asyncio.run(initialize_database()):
        print("\n[ERROR] Database initialization failed.")
        sys.exit(1)

    # Test agent system
    if not asyncio.run(test_agent_system()):
        print("\n[ERROR] Agent system test failed.")
        sys.exit(1)

    print("\n[OK] All systems ready!")
    print("\nAPI Documentation will be available at:")
    print("   http://localhost:8000/docs (Swagger UI)")
    print("   http://localhost:8000/redoc (ReDoc)")

    print("\nTest the system:")
    print("   POST http://localhost:8000/api/v1/sessions/{session_id}/messages")
    print("   Body: {\"content\": \"I want to roll a d20\", \"user_id\": \"test-user\"}")

    if not openai_configured:
        print("\n[WARN] Running with fallback responses (OpenAI not configured)")

    print("\n" + "=" * 50)
    print("Starting FastAPI server...")

    # Start the server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[STOP] Server stopped by user")
    except Exception as e:
        print(f"\n[ERROR] Startup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)