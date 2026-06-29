from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.scene import scene_characters


class Character(Base):
    """SQLAlchemy model for characters."""

    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    story_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stories.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    age: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gender: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[str | None] = mapped_column(String(100), nullable=True)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hair_color: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hair_style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    eye_color: Mapped[str | None] = mapped_column(String(100), nullable=True)
    skin_tone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    face_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    clothing: Mapped[str | None] = mapped_column(Text, nullable=True)
    accessories: Mapped[str | None] = mapped_column(Text, nullable=True)
    personality: Mapped[str | None] = mapped_column(Text, nullable=True)
    art_style_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    consistency_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    story = relationship("Story", back_populates="characters")
    scenes = relationship("Scene", secondary=scene_characters, back_populates="characters")
