from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, func, Integer, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

class AnimationProfile(str, Enum):
    BASIC = "basic"
    STANDARD = "standard"
    HIGH = "high"
    CINEMA = "cinema"

class ProductionProfile(str, Enum):
    SHORTS = "shorts"
    REEL = "reel"
    LONG_FORM = "long_form"
    SERIES = "series"

class QualityProfile(str, Enum):
    DRAFT = "draft"
    STANDARD = "standard"
    HIGH = "high"
    ULTRA = "ultra"

class ProductionPlan(Base):
    """SQLAlchemy model for production plans."""

    __tablename__ = "production_plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    
    animation_profile: Mapped[AnimationProfile] = mapped_column(
        SQLEnum(AnimationProfile, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=AnimationProfile.STANDARD,
        nullable=False
    )
    
    production_profile: Mapped[ProductionProfile] = mapped_column(
        SQLEnum(ProductionProfile, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=ProductionProfile.LONG_FORM,
        nullable=False
    )
    
    quality_profile: Mapped[QualityProfile] = mapped_column(
        SQLEnum(QualityProfile, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=QualityProfile.STANDARD,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project = relationship("Project", back_populates="production_plan")
