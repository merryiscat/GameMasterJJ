"""
Database configuration and session management
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
import os

from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()

async def init_db():
    """Initialize database - create tables"""
    async with engine.begin() as conn:
        # Import models to register them
        from app.models import user, session, character, storylet, dlc

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncSession:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Utility functions
async def execute_sql(query: str, params: dict = None):
    """Execute raw SQL query"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, params or {})
        await session.commit()
        return result

async def fetch_one(query: str, params: dict = None):
    """Fetch single row"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, params or {})
        return result.fetchone()

async def fetch_all(query: str, params: dict = None):
    """Fetch all rows"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, params or {})
        return result.fetchall()