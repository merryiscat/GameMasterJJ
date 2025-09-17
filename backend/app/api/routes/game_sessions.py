"""
Game session management routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from pydantic import BaseModel
from ...core.database import get_db
from ...services.agent_service import agent_service

router = APIRouter(prefix="/sessions", tags=["game-sessions"])

class PlayerMessageRequest(BaseModel):
    content: str
    user_id: str

@router.post("/")
async def create_game_session(
    session: AsyncSession = Depends(get_db)
):
    """Create a new game session"""
    return {"message": "Create game session endpoint - to be implemented"}

@router.get("/")
async def get_user_sessions(
    session: AsyncSession = Depends(get_db)
):
    """Get all game sessions for current user"""
    return {"message": "Get user sessions endpoint - to be implemented"}

@router.get("/{session_id}")
async def get_game_session(
    session_id: str,
    session: AsyncSession = Depends(get_db)
):
    """Get specific game session details"""
    return {"message": f"Get game session {session_id} endpoint - to be implemented"}

@router.put("/{session_id}")
async def update_game_session(
    session_id: str,
    session: AsyncSession = Depends(get_db)
):
    """Update game session details"""
    return {"message": f"Update game session {session_id} endpoint - to be implemented"}

@router.delete("/{session_id}")
async def delete_game_session(
    session_id: str,
    session: AsyncSession = Depends(get_db)
):
    """Delete a game session"""
    return {"message": f"Delete game session {session_id} endpoint - to be implemented"}

@router.post("/{session_id}/messages")
async def send_message(
    session_id: str,
    request: PlayerMessageRequest,
    session: AsyncSession = Depends(get_db)
):
    """Send message to game session (triggers AI agents)"""
    try:
        result = await agent_service.process_player_input(
            session_id=session_id,
            player_input=request.content,
            db_session=session,
            user_id=request.user_id
        )

        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "agent": result["agent"],
                "processing_info": result.get("processing_info", {})
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Agent processing failed")
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )

@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    session: AsyncSession = Depends(get_db)
):
    """Get chat history for game session"""
    return {"message": f"Get messages for session {session_id} endpoint - to be implemented"}

@router.get("/{session_id}/agents/status")
async def get_session_agent_status(
    session_id: str,
    session: AsyncSession = Depends(get_db)
):
    """Get agent status for game session"""
    try:
        result = await agent_service.get_session_status(session_id, session)

        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to get agent status")
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent status: {str(e)}"
        )

@router.post("/{session_id}/agents/reset")
async def reset_session_agents(
    session_id: str,
    session: AsyncSession = Depends(get_db)
):
    """Reset agent memories for game session"""
    try:
        result = await agent_service.reset_session_agents(session_id)

        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to reset agents")
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset agents: {str(e)}"
        )