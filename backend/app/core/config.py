"""
Application configuration settings
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Project Information
    PROJECT_NAME: str = "GameMasterJJ"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # OpenAI Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./gamemaster.db"

    # Redis (for caching)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Audio Processing
    WHISPER_MODEL: str = "whisper-1"
    TTS_VOICE: str = "nova"
    TTS_SPEED: float = 1.0

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:19006",  # Expo dev server
        "http://localhost:8081"    # React Native dev
    ]

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: str = "50MB"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10

    # Agent Configuration
    MAX_AGENT_ITERATIONS: int = 10
    AGENT_TIMEOUT: int = 30

    # Game Configuration
    MAX_CONCURRENT_SESSIONS: int = 100
    SESSION_TIMEOUT_MINUTES: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()