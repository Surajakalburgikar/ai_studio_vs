from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, String, Text, func, Integer, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class VideoType(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    SERIES = "series"


class AspectRatio(str, Enum):
    NINE_TO_SIXTEEN = "9:16"
    SIXTEEN_TO_NINE = "16:9"
    ONE_TO_ONE = "1:1"


class ArtStyle(str, Enum):
    ANIME = "anime"
    MANHWA = "manhwa"
    MANGA = "manga"
    SEMI_REALISTIC = "semi_realistic"


class NarrationStyle(str, Enum):
    THIRD_PERSON = "third_person"
    FIRST_PERSON = "first_person"


class VoiceGender(str, Enum):
    MALE = "male"
    FEMALE = "female"


class Project(Base):
    """SQLAlchemy model for projects."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Configuration fields
    video_type: Mapped[VideoType] = mapped_column(
        SQLEnum(VideoType, values_callable=lambda x: [e.value for e in x], native_enum=False), default=VideoType.MEDIUM, nullable=False
    )
    target_duration_seconds: Mapped[int] = mapped_column(
        Integer, default=180, nullable=False
    )
    aspect_ratio: Mapped[AspectRatio] = mapped_column(
        SQLEnum(AspectRatio, values_callable=lambda x: [e.value for e in x], native_enum=False), default=AspectRatio.SIXTEEN_TO_NINE, nullable=False
    )
    language: Mapped[str] = mapped_column(
        String(100), default="English", nullable=False
    )
    art_style: Mapped[ArtStyle] = mapped_column(
        SQLEnum(ArtStyle, values_callable=lambda x: [e.value for e in x], native_enum=False), default=ArtStyle.ANIME, nullable=False
    )
    narration_style: Mapped[NarrationStyle] = mapped_column(
        SQLEnum(NarrationStyle, values_callable=lambda x: [e.value for e in x], native_enum=False), default=NarrationStyle.THIRD_PERSON, nullable=False
    )
    subtitle_language: Mapped[str] = mapped_column(
        String(100), default="English", nullable=False
    )
    voice_gender: Mapped[VoiceGender] = mapped_column(
        SQLEnum(VoiceGender, values_callable=lambda x: [e.value for e in x], native_enum=False), default=VoiceGender.MALE, nullable=False
    )

    stories = relationship("Story", back_populates="project")
    production_plan = relationship("ProductionPlan", back_populates="project", uselist=False, cascade="all, delete-orphan")

