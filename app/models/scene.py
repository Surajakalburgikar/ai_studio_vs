from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


scene_characters = Table(
    "scene_characters",
    Base.metadata,
    Column("scene_id", Integer, ForeignKey("scenes.id"), primary_key=True),
    Column("character_id", Integer, ForeignKey("characters.id"), primary_key=True),
)


class Scene(Base):
    """SQLAlchemy model for scenes."""

    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("episodes.id"), nullable=False
    )
    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    narration: Mapped[str | None] = mapped_column(Text, nullable=True)
    camera_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    episode = relationship("Episode", back_populates="scenes")
    characters = relationship("Character", secondary=scene_characters, back_populates="scenes")
