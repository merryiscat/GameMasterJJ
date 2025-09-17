"""
GameMasterJJ Backend Application
AI-powered TRPG Game Master system with multi-agent architecture
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from dotenv import load_dotenv

from app.core.config import settings
from app.core.database import init_db
from app.api.main import api_router

# Load environment variables
load_dotenv()

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered TRPG Game Master with multi-agent system",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    print(f"[START] Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"[DEBUG] Debug mode: {settings.DEBUG}")

    # Initialize database
    await init_db()
    print("[OK] Database initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    print("[STOP] Shutting down GameMasterJJ backend")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "GameMasterJJ API",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": {}
            },
            "timestamp": "2025-09-17T10:30:00Z",
            "requestId": "uuid-placeholder"
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )