"""
Main API router combining all route modules
"""

from fastapi import APIRouter
from .routes import auth, game_sessions, characters, dlc

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include all route modules
api_router.include_router(auth.router)
api_router.include_router(game_sessions.router)
api_router.include_router(characters.router)
api_router.include_router(dlc.router)

# Health check endpoint
@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "GameMasterJJ API",
        "version": "1.0.0"
    }