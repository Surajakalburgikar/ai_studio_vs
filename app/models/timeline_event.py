from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Float, String, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

class TimelineEvent(Base):
    """SQLAlchemy model for timeline events."""

    __tablename__ = "timeline_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    scene_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False
    )
    shot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    scene = relationship("Scene", back_populates="timeline_events")
