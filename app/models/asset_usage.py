from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class AssetUsage(Base):
    __tablename__ = "asset_usages"

    usage_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    episode_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scene_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. VIDEO, TRAILER, etc.
    reference_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    asset = relationship("Asset")
    project = relationship("Project")


