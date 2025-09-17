"""
Storylet and narrative content models
"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class StoryletType(str, enum.Enum):
    """Storylet type enumeration"""
    MAIN_STORY = "main_story"
    SIDE_QUEST = "side_quest"
    ENCOUNTER = "encounter"
    DIALOGUE = "dialogue"
    EXPLORATION = "exploration"
    COMBAT = "combat"

class ConditionOperator(str, enum.Enum):
    """Condition operator enumeration"""
    EQUALS = "equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    HAS_ITEM = "has_item"
    HAS_SKILL = "has_skill"
    COMPLETED_STORYLET = "completed_storylet"

class ActionType(str, enum.Enum):
    """Action type enumeration"""
    SET_VARIABLE = "set_variable"
    ADD_ITEM = "add_item"
    REMOVE_ITEM = "remove_item"
    GAIN_EXPERIENCE = "gain_experience"
    MODIFY_STAT = "modify_stat"
    TRIGGER_COMBAT = "trigger_combat"
    HEAL_CHARACTER = "heal_character"

class Storylet(BaseModel):
    """Storylet model - modular narrative content"""
    __tablename__ = "storylets"

    # Basic storylet info
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    story_type = Column(Enum(StoryletType), nullable=False)

    # Content and narrative
    content = Column(Text, nullable=False)  # Main narrative text
    choices = Column(JSON, nullable=True)  # Available player choices

    # Story progression
    is_repeatable = Column(Boolean, default=False, nullable=False)
    is_starting_point = Column(Boolean, default=False, nullable=False)
    weight = Column(Integer, default=100, nullable=False)  # Selection weight

    # Requirements and unlocks
    required_level = Column(Integer, default=1, nullable=False)
    required_items = Column(JSON, nullable=True)  # Required inventory items
    required_skills = Column(JSON, nullable=True)  # Required skill levels

    # Narrative context
    location = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)  # Content tags for filtering
    mood = Column(String(50), nullable=True)  # atmospheric, tense, mysterious, etc.

    # DLC and content management
    dlc_id = Column(String, ForeignKey("dlcs.id"), nullable=True)
    is_premium = Column(Boolean, default=False, nullable=False)

    # Relationships
    conditions = relationship("StoryletCondition", back_populates="storylet", cascade="all, delete-orphan")
    actions = relationship("AbstractAction", back_populates="storylet", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Storylet(id={self.id}, title={self.title}, type={self.story_type})>"

class StoryletCondition(BaseModel):
    """Conditions that must be met to access a storylet"""
    __tablename__ = "storylet_conditions"

    # Condition definition
    variable_name = Column(String(100), nullable=False)
    operator = Column(Enum(ConditionOperator), nullable=False)
    target_value = Column(String(255), nullable=False)  # Can be string, number, or item ID

    # Logic grouping
    condition_group = Column(Integer, default=0, nullable=False)  # For AND/OR logic
    is_required = Column(Boolean, default=True, nullable=False)

    # Description for debugging
    description = Column(Text, nullable=True)

    # Relationships
    storylet_id = Column(String, ForeignKey("storylets.id"), nullable=False)
    storylet = relationship("Storylet", back_populates="conditions")

    def __repr__(self):
        return f"<StoryletCondition(storylet={self.storylet_id}, {self.variable_name} {self.operator} {self.target_value})>"

class AbstractAction(BaseModel):
    """Actions that occur when a storylet choice is selected"""
    __tablename__ = "abstract_actions"

    # Action definition
    action_type = Column(Enum(ActionType), nullable=False)
    target = Column(String(100), nullable=False)  # What to modify (stat name, item ID, etc.)
    value = Column(String(255), nullable=False)  # Value to apply

    # Execution order and conditions
    execution_order = Column(Integer, default=0, nullable=False)
    is_conditional = Column(Boolean, default=False, nullable=False)
    condition_data = Column(JSON, nullable=True)  # Conditions for this specific action

    # Narrative feedback
    success_message = Column(Text, nullable=True)
    failure_message = Column(Text, nullable=True)

    # Choice association
    choice_index = Column(Integer, nullable=True)  # Which choice triggers this action

    # Relationships
    storylet_id = Column(String, ForeignKey("storylets.id"), nullable=False)
    storylet = relationship("Storylet", back_populates="actions")

    def __repr__(self):
        return f"<AbstractAction(storylet={self.storylet_id}, type={self.action_type})>"