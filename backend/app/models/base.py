"""
Base model with common fields and utilities
"""

from sqlalchemy import Column, Integer, DateTime, String
from sqlalchemy.sql import func
from app.core.database import Base as DatabaseBase
import uuid

Base = DatabaseBase

class BaseModel(Base):
    """Base model with common fields"""
    __abstract__ = True

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }