"""
Character and equipment models
"""

from sqlalchemy import Column, String, Integer, Text, JSON, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class CharacterClassType(str, enum.Enum):
    """Character class enumeration"""
    FIGHTER = "fighter"
    WIZARD = "wizard"
    ROGUE = "rogue"
    CLERIC = "cleric"
    RANGER = "ranger"
    PALADIN = "paladin"
    BARBARIAN = "barbarian"
    BARD = "bard"

class Character(BaseModel):
    """Character model"""
    __tablename__ = "characters"

    # Basic character info
    name = Column(String(100), nullable=False)
    character_class = Column(Enum(CharacterClassType), nullable=False)
    level = Column(Integer, default=1, nullable=False)
    experience = Column(Integer, default=0, nullable=False)

    # Core stats (D&D style)
    strength = Column(Integer, default=10, nullable=False)
    dexterity = Column(Integer, default=10, nullable=False)
    constitution = Column(Integer, default=10, nullable=False)
    intelligence = Column(Integer, default=10, nullable=False)
    wisdom = Column(Integer, default=10, nullable=False)
    charisma = Column(Integer, default=10, nullable=False)

    # Derived stats
    hit_points_max = Column(Integer, nullable=False)
    hit_points_current = Column(Integer, nullable=False)
    armor_class = Column(Integer, default=10, nullable=False)
    speed = Column(Integer, default=30, nullable=False)
    proficiency_bonus = Column(Integer, default=2, nullable=False)

    # Skills and proficiencies
    skills = Column(JSON, nullable=True)  # Skill modifiers
    proficiencies = Column(JSON, nullable=True)  # Tool/weapon proficiencies
    languages = Column(JSON, nullable=True)  # Known languages

    # Character description
    background = Column(String(100), nullable=True)
    personality_traits = Column(Text, nullable=True)
    ideals = Column(Text, nullable=True)
    bonds = Column(Text, nullable=True)
    flaws = Column(Text, nullable=True)

    # Character appearance
    appearance = Column(Text, nullable=True)
    portrait_url = Column(String(500), nullable=True)

    # Status effects and conditions
    status_effects = Column(JSON, nullable=True)
    temporary_hp = Column(Integer, default=0, nullable=False)

    # Relationships
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="characters")
    game_sessions = relationship("GameSession", back_populates="character")
    equipment = relationship("Equipment", back_populates="character", cascade="all, delete-orphan")
    inventory = relationship("Inventory", back_populates="character", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Character(id={self.id}, name={self.name}, class={self.character_class}, level={self.level})>"

class EquipmentSlot(str, enum.Enum):
    """Equipment slot enumeration"""
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    ARMOR = "armor"
    HELMET = "helmet"
    GLOVES = "gloves"
    BOOTS = "boots"
    RING_1 = "ring_1"
    RING_2 = "ring_2"
    NECKLACE = "necklace"
    CLOAK = "cloak"

class Equipment(BaseModel):
    """Equipment worn by character"""
    __tablename__ = "equipment"

    # Equipment identification
    item_id = Column(String(100), nullable=False)  # References item template
    item_name = Column(String(200), nullable=False)
    slot = Column(Enum(EquipmentSlot), nullable=False)

    # Item properties
    item_type = Column(String(50), nullable=False)  # weapon, armor, accessory
    rarity = Column(String(20), default="common", nullable=False)
    properties = Column(JSON, nullable=True)  # Item-specific properties
    bonuses = Column(JSON, nullable=True)  # Stat bonuses

    # Condition and usage
    durability_current = Column(Integer, nullable=True)
    durability_max = Column(Integer, nullable=True)
    is_attuned = Column(Boolean, default=False, nullable=False)
    is_cursed = Column(Boolean, default=False, nullable=False)

    # Relationships
    character_id = Column(String, ForeignKey("characters.id"), nullable=False)
    character = relationship("Character", back_populates="equipment")

    def __repr__(self):
        return f"<Equipment(id={self.id}, item_name={self.item_name}, slot={self.slot})>"

class Inventory(BaseModel):
    """Character inventory items"""
    __tablename__ = "inventory"

    # Item identification
    item_id = Column(String(100), nullable=False)  # References item template
    item_name = Column(String(200), nullable=False)
    item_type = Column(String(50), nullable=False)

    # Quantity and organization
    quantity = Column(Integer, default=1, nullable=False)
    stack_size = Column(Integer, default=1, nullable=False)
    weight = Column(Integer, default=0, nullable=False)  # In pounds

    # Item properties
    description = Column(Text, nullable=True)
    rarity = Column(String(20), default="common", nullable=False)
    properties = Column(JSON, nullable=True)
    value_gp = Column(Integer, default=0, nullable=False)  # Value in gold pieces

    # Special flags
    is_consumable = Column(Boolean, default=False, nullable=False)
    is_quest_item = Column(Boolean, default=False, nullable=False)
    is_tradeable = Column(Boolean, default=True, nullable=False)

    # Relationships
    character_id = Column(String, ForeignKey("characters.id"), nullable=False)
    character = relationship("Character", back_populates="inventory")

    def __repr__(self):
        return f"<Inventory(id={self.id}, item_name={self.item_name}, quantity={self.quantity})>"

class CharacterClass(BaseModel):
    """Character class definitions and abilities"""
    __tablename__ = "character_classes"

    # Class info
    class_type = Column(Enum(CharacterClassType), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    hit_die = Column(String(10), default="d8", nullable=False)  # e.g., "d10", "d6"

    # Starting stats
    primary_abilities = Column(JSON, nullable=False)  # ["strength", "constitution"]
    saving_throw_proficiencies = Column(JSON, nullable=False)
    skill_choices = Column(JSON, nullable=False)  # Available skills to choose from
    starting_equipment = Column(JSON, nullable=False)

    # Level progression
    level_progression = Column(JSON, nullable=False)  # Abilities gained per level
    spell_progression = Column(JSON, nullable=True)  # For spellcasting classes

    # DLC information
    dlc_id = Column(String, ForeignKey("dlcs.id"), nullable=True)
    is_base_class = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<CharacterClass(class_type={self.class_type}, name={self.name})>"