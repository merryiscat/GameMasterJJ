"""
DLC and monetization models
"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class DLCType(str, enum.Enum):
    """DLC type enumeration"""
    STORY_PACK = "story_pack"
    CHARACTER_PACK = "character_pack"
    SYSTEM_PACK = "system_pack"
    COSMETIC_PACK = "cosmetic_pack"
    EXPANSION = "expansion"

class DLCStatus(str, enum.Enum):
    """DLC status enumeration"""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    MAINTENANCE = "maintenance"

class PurchaseStatus(str, enum.Enum):
    """Purchase status enumeration"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class PlatformType(str, enum.Enum):
    """Platform type enumeration"""
    APP_STORE = "app_store"
    GOOGLE_PLAY = "google_play"
    DIRECT = "direct"
    STRIPE = "stripe"

class DLC(BaseModel):
    """DLC content package model"""
    __tablename__ = "dlcs"

    # Basic DLC info
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    dlc_type = Column(Enum(DLCType), nullable=False)
    status = Column(Enum(DLCStatus), default=DLCStatus.DRAFT, nullable=False)

    # Pricing and monetization
    price_usd = Column(Float, nullable=False)
    currency_code = Column(String(3), default="USD", nullable=False)
    is_free = Column(Boolean, default=False, nullable=False)

    # Content metadata
    content_version = Column(String(20), default="1.0.0", nullable=False)
    required_base_version = Column(String(20), default="1.0.0", nullable=False)
    download_size_mb = Column(Integer, nullable=True)

    # Store listing info
    store_title = Column(String(100), nullable=False)
    store_description = Column(Text, nullable=False)
    store_screenshots = Column(JSON, nullable=True)  # URLs to screenshot images
    store_tags = Column(JSON, nullable=True)  # Store category tags

    # Content information
    included_storylets_count = Column(Integer, default=0, nullable=False)
    included_characters_count = Column(Integer, default=0, nullable=False)
    included_items_count = Column(Integer, default=0, nullable=False)
    estimated_playtime_hours = Column(Float, nullable=True)

    # Release and availability
    release_date = Column(DateTime(timezone=True), nullable=True)
    is_early_access = Column(Boolean, default=False, nullable=False)
    regional_availability = Column(JSON, nullable=True)  # Country codes

    # Content ratings and classification
    content_rating = Column(String(10), nullable=True)  # ESRB, PEGI ratings
    content_warnings = Column(JSON, nullable=True)  # Violence, language, etc.

    # Analytics and performance
    total_purchases = Column(Integer, default=0, nullable=False)
    total_revenue = Column(Float, default=0.0, nullable=False)
    average_rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0, nullable=False)

    # Relationships
    purchases = relationship("DLCPurchase", back_populates="dlc", cascade="all, delete-orphan")
    reviews = relationship("DLCReview", back_populates="dlc", cascade="all, delete-orphan")
    storylets = relationship("Storylet", backref="dlc")
    character_classes = relationship("CharacterClass", backref="dlc")

    def __repr__(self):
        return f"<DLC(id={self.id}, name={self.name}, type={self.dlc_type}, price=${self.price_usd})>"

class DLCPurchase(BaseModel):
    """DLC purchase transaction model"""
    __tablename__ = "dlc_purchases"

    # Purchase details
    status = Column(Enum(PurchaseStatus), default=PurchaseStatus.PENDING, nullable=False)
    platform = Column(Enum(PlatformType), nullable=False)

    # Transaction info
    transaction_id = Column(String(255), nullable=False, index=True)  # Platform transaction ID
    receipt_data = Column(Text, nullable=True)  # Platform receipt for verification
    purchase_price = Column(Float, nullable=False)
    currency_code = Column(String(3), default="USD", nullable=False)

    # Timestamps
    purchased_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)

    # Purchase metadata
    ip_address = Column(String(45), nullable=True)  # For fraud detection
    user_agent = Column(String(500), nullable=True)
    device_info = Column(JSON, nullable=True)  # Device type, OS version, etc.

    # Refund information
    refund_reason = Column(Text, nullable=True)
    refund_amount = Column(Float, nullable=True)

    # Relationships
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    dlc_id = Column(String, ForeignKey("dlcs.id"), nullable=False)

    user = relationship("User", back_populates="dlc_purchases")
    dlc = relationship("DLC", back_populates="purchases")

    def __repr__(self):
        return f"<DLCPurchase(id={self.id}, user={self.user_id}, dlc={self.dlc_id}, status={self.status})>"

class DLCReview(BaseModel):
    """DLC user review model"""
    __tablename__ = "dlc_reviews"

    # Review content
    rating = Column(Integer, nullable=False)  # 1-5 stars
    title = Column(String(200), nullable=True)
    review_text = Column(Text, nullable=True)

    # Review metadata
    is_verified_purchase = Column(Boolean, default=False, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    is_hidden = Column(Boolean, default=False, nullable=False)

    # Moderation
    reported_count = Column(Integer, default=0, nullable=False)
    is_moderated = Column(Boolean, default=False, nullable=False)
    moderation_notes = Column(Text, nullable=True)

    # Engagement metrics
    helpful_votes = Column(Integer, default=0, nullable=False)
    total_votes = Column(Integer, default=0, nullable=False)

    # Platform info
    platform = Column(Enum(PlatformType), nullable=True)
    device_type = Column(String(50), nullable=True)  # iOS, Android, etc.

    # Relationships
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    dlc_id = Column(String, ForeignKey("dlcs.id"), nullable=False)

    user = relationship("User", back_populates="dlc_reviews")
    dlc = relationship("DLC", back_populates="reviews")

    def __repr__(self):
        return f"<DLCReview(id={self.id}, dlc={self.dlc_id}, rating={self.rating})>"