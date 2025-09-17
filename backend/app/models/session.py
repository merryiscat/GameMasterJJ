"""
Game session and chat message models
"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class SessionStatus(str, enum.Enum):
    """Game session status enumeration"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

class MessageSender(str, enum.Enum):
    """Chat message sender enumeration"""
    PLAYER = "player"
    GM = "gm"
    TRIAGE_AGENT = "triage_agent"
    NARRATOR_AGENT = "narrator_agent"
    RULES_KEEPER_AGENT = "rules_keeper_agent"
    NPC_INTERACTION_AGENT = "npc_interaction_agent"
    LORE_KEEPER_AGENT = "lore_keeper_agent"

class GameSession(BaseModel):
    """Game session model"""
    __tablename__ = "game_sessions"

    # Basic session info
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False)

    # Session configuration
    story_id = Column(String, nullable=False)  # References storylet collection
    difficulty = Column(String(20), default="normal", nullable=False)
    voice_enabled = Column(Boolean, default=True, nullable=False)
    auto_save = Column(Boolean, default=True, nullable=False)

    # Game state
    current_location = Column(String(100), nullable=True)
    game_state = Column(JSON, nullable=True)  # Dynamic game state
    world_state = Column(JSON, nullable=True)  # World variables and flags
    active_storylets = Column(JSON, nullable=True)  # Currently available storylets

    # Session statistics
    play_time_minutes = Column(Integer, default=0, nullable=False)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    save_count = Column(Integer, default=0, nullable=False)

    # Relationships
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    character_id = Column(String, ForeignKey("characters.id"), nullable=True)

    user = relationship("User", back_populates="game_sessions")
    character = relationship("Character", back_populates="game_sessions")
    chat_messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GameSession(id={self.id}, title={self.title}, status={self.status})>"

class ChatMessage(BaseModel):
    """Chat message model for session history"""
    __tablename__ = "chat_messages"

    # Message content
    content = Column(Text, nullable=False)
    sender = Column(Enum(MessageSender), nullable=False)
    message_type = Column(String(50), default="text", nullable=False)  # text, voice, action, system

    # Voice-related fields
    voice_text = Column(Text, nullable=True)  # Original voice transcription
    audio_url = Column(String(500), nullable=True)  # Generated audio file URL
    voice_duration = Column(Integer, nullable=True)  # Duration in seconds

    # Game context
    agent_context = Column(JSON, nullable=True)  # Agent processing context
    game_state_snapshot = Column(JSON, nullable=True)  # Game state at message time
    dice_results = Column(JSON, nullable=True)  # Dice roll results if any

    # Message metadata
    is_visible = Column(Boolean, default=True, nullable=False)
    is_system_message = Column(Boolean, default=False, nullable=False)
    sequence_number = Column(Integer, nullable=False)  # Order in session

    # Relationships
    session_id = Column(String, ForeignKey("game_sessions.id"), nullable=False)
    session = relationship("GameSession", back_populates="chat_messages")

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, sender={self.sender}, type={self.message_type})>"